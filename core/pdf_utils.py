# core/pdf_utils.py
import hashlib
import io
import json
import os
import threading
import time
import weakref
from collections import OrderedDict
from typing import Dict, List, Optional

import fitz  # PyMuPDF
# noinspection PyPackageRequirements
import qrcode
from PIL import Image, ImageDraw, ImageFont

try:
    # noinspection PyPackageRequirements
    from qrcode.image.styledpil import StyledPilImage
    # noinspection PyPackageRequirements
    from qrcode.image.styles.moduledrawers import SquareModuleDrawer
    # noinspection PyPackageRequirements
    from qrcode.image.styles.colormasks import SolidFillColorMask
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False
    print("Библиотека qrcode не установлена. Установите: pip install qrcode[pil]")

try:
    import barcode
    from barcode import Code128
    from barcode.writer import ImageWriter
    HAS_BARCODE = True
except ImportError:
    HAS_BARCODE = False
    print("Библиотека python-barcode не установлена. Установите: pip install python-barcode")

# Добавляем конфигурацию форматирования полей
FIELD_FORMATTING = {
    'brutto': {
        'unit': ' кг',
        'align': 'center',
        'add_unit': True
    },
    'netto': {
        'unit': ' кг',
        'align': 'center',
        'add_unit': True
    },
    'dia': {
        'unit': '',
        'align': 'center',
        'add_unit': False
    },
    'tr': {
        'unit': ' шт',
        'align': 'center',
        'add_unit': True
    },
    'rol': {
        'unit': ' шт',
        'align': 'center',
        'add_unit': True
    },
    'total': {
        'unit': ' шт',
        'align': 'center',
        'add_unit': True
    },
    'box_brut': {
        'unit': ' кг',
        'align': 'center',
        'add_unit': True,
        'prefix': 'Брутто '
    },
    'box_net': {
        'unit': ' кг',
        'align': 'center',
        'add_unit': True,
        'prefix': 'Нетто '
    },
    'rll_length': {
        'unit': ' м',
        'align': 'center',
        'add_unit': True
    },
    'customer': {
        'unit': '',
        'align': 'left',
        'add_unit': False
    },
    'product': {
        'unit': '',
        'align': 'left',
        'add_unit': False
    },
    'default': {
        'unit': '',
        'align': 'center',
        'add_unit': False
    }
}

# Добавляем список всех плейсхолдеров в начало класса
# noinspection SpellCheckingInspection
ALL_PLACEHOLDERS = [
    "$customer", "$product", "$onum", "$date", "$packer",
    "$brutto", "$netto", "$rol", "$tr", "$sx", "dia",
    "$printhouse", "$printaddress", "$total", "$tu_number",
    "$box_brut", "$box_net", "$cutter", "$rll_length", "$emission",
    "$batch_num", "$roul_num", "$ros_podlo", "$ros_size", "$gtin",
    "$box_qr",
]

# noinspection SpellCheckingInspection
class PDFTemplateFiller:
    """Класс для заполнения PDF шаблонов с плейсхолдерами"""
    
    # Сопоставление имен полей плейсхолдеров с настройками
    FIELD_MAPPING = {
        # Общие поля для ролика и коробки
        "customer": "customer",      # Заказчик
        "product": "product",        # Изделие
        "ros_podlo": "product",        # Подложка Росинки
        "ros_size": "product",        # Размер Росинки
        "packer": "packer",           # Упаковщик
        "onum": "order_number",      # Номер заказа
        
        # Поля ролика и коробки (группа "other")
        "brutto": "other",           # Вес брутто
        "netto": "other",            # Вес нетто  
        "rol": "other",              # Этикеток в ролике
        "tr": "other",               # Количество роликов
        "sx": "other",               # Схема намотки
        "dia": "other",              # Диаметр втулки
        "date": "other",             # Дата изготовления
        
        # Поля только для коробки
        "printhouse": "manufacturer",    # Изготовитель
        "printaddress": "address",       # Адрес изготовителя
        "total": "total",                # Всего этикеток
        "tu_number": "tu_number",        # Технические условия
        
        # Новые поля коробки
        "box_brut": "other",             # Вес коробки брутто
        "box_net": "other",              # Вес коробки нетто
        "cutter": "other",               # Резчик
        "rll_length": "other",           # Длина ролика
        "emission": "other",             # Дата эмиссии
        "batch_num": "customer",             # № съёма
        "roul_num": "customer",             # № ролика
    }
    
    # Сопоставление статического текста с плейсхолдерами для очистки
    STATIC_TEXT_MAPPING = {
        # статический_текст: плейсхолдер
        "Изготовитель:": "$printhouse",
        "Заказчик:": "$customer",
        "Дата эмиссии:": "$emission", 
        "Длина ролика:": "$rll_length",
        "№ съема/№ ролика :": "$batch_num",
        "Брутто:": "$brutto",
        "Нетто:": "$netto",
        "Кол-во этикеток:": "$rol",
        "—": "$roul_num",
        "№ съема /№ ролика:": "$batch_num",
    }    
    
    def __init__(self, template_path: str):
        self._cached_print_image = None
        self._cached_page_image = None
        self.template_path = template_path
        self.doc = None
        self.zoom_level = 1.5
        self.font_settings = None
        self._current_printer_dpi = None
        
        # Кэш для оптимизации
        self._preview_cache = OrderedDict()  # ключ -> (weakref, timestamp)
        self._print_cache = OrderedDict()    # ключ -> (weakref, timestamp)
        self._max_cache_size = 3
        self._cache_ttl = 300  # 5 минут TTL (опционально)
        self._lock = threading.Lock()

        self._cached_mat = None             # Матрица трансформации
        self._placeholder_positions = {}    # Кэш позиций плейсхолдеров {placeholder: [rects]}
        self._static_text_positions = {}    # Кэш позиций статического текста
        self._page_loaded = False           # Флаг загрузки страницы
        # добавляем версионность
        self._cache_version = 0
        self._current_version = 0

    # noinspection PyMethodMayBeStatic
    def _draw_barcode(self, draw, rect, data: str, mat):
        """Рисует штрих-код Code128 в указанной области"""
        if not data:
            transformed_rect = rect * mat
            draw.rectangle([transformed_rect.x0, transformed_rect.y0, transformed_rect.x1, transformed_rect.y1],
                           fill='white')
            return

        try:
            from barcode import Code128
            from barcode.writer import ImageWriter

            barcode_obj = Code128(data, writer=ImageWriter())
            barcode_bytes = io.BytesIO()
            barcode_obj.write(barcode_bytes, options={"write_text": False, "dpi": 200})
            barcode_img = Image.open(barcode_bytes)

            transformed_rect = rect * mat
            rect_width = transformed_rect.x1 - transformed_rect.x0
            rect_height = transformed_rect.y1 - transformed_rect.y0

            # Желаемая ширина в мм (40 мм для этикетки 90x72)
            target_width_mm = 40
            target_width_pixels = int(target_width_mm * (mat.a / 25.4 * 72))

            # Масштабируем до нужной ширины
            aspect = barcode_img.height / barcode_img.width
            target_height_pixels = int(target_width_pixels * aspect)
            barcode_img = barcode_img.resize((target_width_pixels, target_height_pixels), Image.Resampling.LANCZOS)

            img_w, img_h = barcode_img.size
            x = transformed_rect.x0 + (rect_width - img_w) / 2
            y = transformed_rect.y0 + (rect_height - img_h) / 2

            draw.rectangle([transformed_rect.x0, transformed_rect.y0, transformed_rect.x1, transformed_rect.y1],
                           fill='white')
            # noinspection PyProtectedMember
            draw._image.paste(barcode_img, (int(x), int(y)))

        except ImportError:
            print("Библиотека python-barcode не установлена")
            transformed_rect = rect * mat
            draw.rectangle([transformed_rect.x0, transformed_rect.y0, transformed_rect.x1, transformed_rect.y1],
                           fill='white')
        except Exception as e:
            print(f"Ошибка генерации штрих-кода: {e}")
            transformed_rect = rect * mat
            draw.rectangle([transformed_rect.x0, transformed_rect.y0, transformed_rect.x1, transformed_rect.y1],
                           fill='white')

    def get_template_size_mm(self) -> tuple[float, float]:
        """Возвращает размер первой страницы шаблона в миллиметрах"""
        if not self.doc:
            try:
                self.open_template()
            except Exception as e:
                print(f"Ошибка открытия PDF для получения размера: {e}")
                return 0, 0

        if self.doc and len(self.doc) > 0:
            page = self.doc[0]
            # Размер в пунктах (1/72 дюйма)
            width_pt = page.rect.width
            height_pt = page.rect.height
            # Конвертируем в мм (1 пункт = 1/72 дюйма, 1 дюйм = 25.4 мм)
            width_mm = width_pt * 25.4 / 72
            height_mm = height_pt * 25.4 / 72
            return round(width_mm, 1), round(height_mm, 1)
        return 0, 0

    def _generate_cache_key(self, data_map: Dict[str, str], for_print: bool) -> str:
        """Генерирует уникальный ключ кэша на основе данных и версии"""
        # Сортируем словарь для стабильности ключа
        sorted_data = {k: v for k, v in sorted(data_map.items()) if k != '$d'}
        
        # Создаем строку для хеширования
        data_str = json.dumps(sorted_data, sort_keys=True)
        
        # Добавляем версию кэша и флаг печати
        key_data = f"{self._cache_version}:{for_print}:{data_str}"
        
        # Возвращаем хеш
        return hashlib.md5(key_data.encode()).hexdigest()

    def _get_from_cache(self, key: str, for_print: bool) -> Optional[Image.Image]:
        """Получает изображение из кэша если оно есть и не устарело"""
        cache = self._print_cache if for_print else self._preview_cache
        
        if key not in cache:
            return None
        
        weak_ref, timestamp = cache[key]
        img = weak_ref()
        
        # Проверяем, жива ли еще ссылка и не истек ли TTL
        if img is None or (time.time() - timestamp) > self._cache_ttl:
            # Удаляем мертвую или устаревшую запись
            del cache[key]
            return None
        
        # Перемещаем в конец (LRU)
        cache.move_to_end(key)
        return img.copy()  # ВАЖНО: возвращаем копию!

    def _put_in_cache(self, key: str, image: Image.Image, for_print: bool):
        """Сохраняет изображение в кэш с контролем размера"""
        cache = self._print_cache if for_print else self._preview_cache
        
        # Если кэш полон - удаляем самую старую запись
        if len(cache) >= self._max_cache_size:
            oldest_key, _ = next(iter(cache.items()))
            del cache[oldest_key]
        
        # Сохраняем слабую ссылку на изображение и timestamp
        cache[key] = (weakref.ref(image), time.time())
        
        # Перемещаем в конец (LRU)
        cache.move_to_end(key)

    def _cleanup_dead_refs(self, for_print: bool = None):
        """Очищает мертвые ссылки из кэша"""
        caches = [(self._preview_cache, False), (self._print_cache, True)]
        
        for cache, is_print in caches:
            if for_print is not None and for_print != is_print:
                continue
                
            dead_keys = []
            for key, (weak_ref, timestamp) in cache.items():
                if weak_ref() is None:
                    dead_keys.append(key)
            
            for key in dead_keys:
                del cache[key]
        
    def set_font_settings(self, font_settings: Dict):
        """Устанавливает настройки шрифтов"""
        self.font_settings = font_settings
        
    def open_template(self):
        """Открывает PDF шаблон и кэширует все необходимые данные"""
        if not os.path.exists(self.template_path):
            raise FileNotFoundError(f"PDF шаблон не найден: {self.template_path}")
        
        # Открываем документ
        self.doc = fitz.open(self.template_path)
        
        # Кэшируем все позиции при первой загрузке
        self._cache_all_positions()
        
        # Предварительно рендерим страницу для превью
        self._precache_page_image(for_print=False)
        self._current_version = self._cache_version
        
        return self.doc      
        
    def _cache_all_positions(self):
        """Находит и кэширует позиции ВСЕХ плейсхолдеров и статического текста"""
        if not self.doc:
            return
        
        # Берем первую страницу (у нас всегда одна страница в шаблоне)
        page = self.doc[0]
        
        # Очищаем старые кэши
        self._placeholder_positions.clear()
        self._static_text_positions.clear()
        
        # 1. Кэшируем все плейсхолдеры
        for placeholder in ALL_PLACEHOLDERS:
            instances = page.search_for(placeholder)
            
            # Фильтруем артефакты (слишком маленькие прямоугольники)
            valid_instances = []
            for rect in instances:
                width = rect.x1 - rect.x0
                height = rect.y1 - rect.y0
                if width >= 8 and height >= 4:  # Эмпирические значения
                    valid_instances.append(rect)
            
            if valid_instances:
                self._placeholder_positions[placeholder] = valid_instances
        
        # 2. Кэшируем статический текст для очистки
        for static_text in self.STATIC_TEXT_MAPPING.keys():
            instances = page.search_for(static_text)
            
            valid_instances = []
            for rect in instances:
                width = rect.x1 - rect.x0
                height = rect.y1 - rect.y0
                if width >= 15 and height >= 5:  # Статический текст обычно больше
                    valid_instances.append(rect)
            
            if valid_instances:
                self._static_text_positions[static_text] = valid_instances
        
        self._page_loaded = True
    
    def find_placeholder_positions(self, placeholders: List[str]) -> Dict[str, List[Dict]]:
        """Находит позиции всех плейсхолдеров в PDF"""
        if not self.doc:
            self.open_template()
            
        positions = {}
        
        for placeholder in placeholders:
            positions[placeholder] = []
            
            for page_num in range(len(self.doc)):
                page = self.doc[page_num]
                text_instances = page.search_for(placeholder)
                
                for inst in text_instances:
                    positions[placeholder].append({
                        "page": page_num,
                        "bbox": inst,
                        "text": placeholder
                    })
        
        return positions

    def render_page_with_data(self, data_map: Dict[str, str], for_print: bool = False, printer_dpi: int = 300) -> Image.Image:
        """Рендерит страницу PDF с подставленными данными (оптимизированная версия)"""
        with self._lock:
            self._current_printer_dpi = printer_dpi if for_print else None
            if not self.doc:
                self.open_template()
            
            # ВСЕГДА увеличиваем версию при каждом рендеринге с новыми данными
            # Это гарантирует, что кэш будет пересоздан
            self._cache_version += 1
            
            # проверяем версию кэша
            if self._cache_version != self._current_version:
                self._cached_page_image = None
                self._cached_print_image = None
                self._current_version = self._cache_version
            
            # Генерируем ключ кэша
            cache_key = self._generate_cache_key(data_map, for_print)
            
            # Пытаемся получить из кэша
            base_img = self._precache_page_image(for_print=for_print, printer_dpi=printer_dpi)
            
            if base_img is None:
                # Очищаем мертвые ссылки
                self._cleanup_dead_refs(for_print)
                
                # Рендерим базовое изображение
                base_img = self._precache_page_image(for_print=for_print)
                
                # Сохраняем в кэш (копию!)
                self._put_in_cache(cache_key, base_img.copy(), for_print)
            else:
                # Мы уже получили копию из _get_from_cache
                pass
            
            # Если нет кэша позиций - создаем его
            if not self._placeholder_positions:
                self._cache_all_positions()
            
            draw = ImageDraw.Draw(base_img)
            mat = self._cached_mat
            
            # Копируем data_map и удаляем служебное поле $d если есть
            data_map_without_d = data_map.copy()
            if '$d' in data_map_without_d:
                del data_map_without_d['$d']
            
            # 1. Очистка статического текста для пустых плейсхолдеров (используем кэш)
            for static_text, placeholder in self.STATIC_TEXT_MAPPING.items():
                if not data_map.get(placeholder) and static_text in self._static_text_positions:
                    for rect in self._static_text_positions[static_text]:
                        transformed_rect = rect * mat
                        draw.rectangle(
                            [transformed_rect.x0, transformed_rect.y0, 
                             transformed_rect.x1, transformed_rect.y1], 
                            fill='white'
                        )
            
            # 2. Очистка пустых плейсхолдеров (используем кэш)
            for placeholder, rects in self._placeholder_positions.items():
                if placeholder in data_map_without_d and not data_map_without_d[placeholder]:
                    for rect in rects:
                        transformed_rect = rect * mat
                        draw.rectangle(
                            [transformed_rect.x0, transformed_rect.y0,
                             transformed_rect.x1, transformed_rect.y1], 
                            fill='white'
                        )
            
            # 3. Замена заполненных плейсхолдеров
            for placeholder, new_text in data_map_without_d.items():
                if not new_text or placeholder not in self._placeholder_positions:
                    continue
                
                for rect in self._placeholder_positions[placeholder]:
                    field_type = placeholder[1:] if placeholder.startswith('$') else placeholder
                    # Вызываем оптимизированную версию замены (без поиска)
                    self._replace_text_in_rect(draw, rect, new_text, mat, field_type, for_print)
            
            return base_img
        
    def _precache_page_image(self, for_print=False, printer_dpi=300):
        """Предварительно рендерит страницу и кэширует изображение"""
        if not self.doc:
            return None
        
        page = self.doc[0]
        
        if for_print:
            dpi = printer_dpi
            mat = fitz.Matrix(dpi/72, dpi/72)
        else:
            # Для превью используем увеличение, как в оригинале
            mat = fitz.Matrix(self.zoom_level, self.zoom_level)
        
        self._cached_mat = mat
        
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("ppm")
        img = Image.open(io.BytesIO(img_data))
        
        # Создаем копию для кэша, чтобы избежать наложения при множественных вызовах
        img_copy = img.copy()
        
        if for_print:
            self._cached_print_image = img_copy
        else:
            self._cached_page_image = img_copy
        
        return img
    
    def _replace_text_in_rect(self, draw: ImageDraw.Draw, rect, text: str, mat, field_type: str = "default", for_print: bool = False):
        """Заменяет текст в указанной области"""
        try:
            # Если это qr-код - обрабатываем особо
            if field_type == "box_qr":
                self._draw_qr_code(draw, rect, text, mat)
                return

            # Штрих-код для $ros_podlo
            if field_type == "ros_podlo":
                if getattr(self, '_draw_as_barcode', False):
                    self._draw_barcode(draw, rect, text, mat)
                    return

            # Если текст пустой - очищаем область и выходим
            if not text or text.strip() == "":
                transformed_rect = rect * mat
                x0, y0 = transformed_rect.x0, transformed_rect.y0
                x1, y1 = transformed_rect.x1, transformed_rect.y1
                draw.rectangle([x0, y0, x1, y1], fill='white')
                return

            transformed_rect = rect * mat

            setting_field_type = self.FIELD_MAPPING.get(field_type, field_type)

            # Определяем размер шрифта из настроек или используем значения по умолчанию
            if self.font_settings:
                font_size = self._get_font_size_from_settings(setting_field_type, for_print)
                font_style = self._get_font_style_from_settings(setting_field_type)
            else:
                # Значения по умолчанию
                if field_type in ['customer', 'product']:
                    font_size = 30
                else:
                    font_size = 18
                font_style = 'normal'

            # Для поля product используем многострочную отрисовку
            if field_type == "product" and self.font_settings:
                wrap_settings = self.font_settings.get("multiline_settings", {})
                if wrap_settings:
                    lines = self._prepare_text_lines(text, font_size, wrap_settings)
                    self._draw_multiline_text(draw, rect, lines, mat, font_size)
                    return

            # Для остальных полей - стандартная однострочная отрисовка
            # font_style = 'bold' if for_print else 'normal'
            font = self._get_font(font_size, font_style)

            x0, y0 = transformed_rect.x0, transformed_rect.y0
            x1, y1 = transformed_rect.x1, transformed_rect.y1

            rect_width = x1 - x0
            rect_height = y1 - y0

            # Форматирование текста на основе конфигурации
            display_text = self._format_display_text(field_type, text)

            bbox = draw.textbbox((0, 0), display_text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            # Выравнивание на основе конфигурации
            text_x = self._get_text_alignment_x(field_type, x0, rect_width, text_width)

            text_y = y0 + (rect_height - text_height) / 2 - 3

            # Очищаем область и рисуем новый текст
            draw.rectangle([x0, y0, x1, y1], fill='white')
            draw.text((text_x, text_y), display_text, fill='black', font=font)

        except Exception as e:
            print(f"Ошибка замены текста {field_type}: {e}")
            
    def _get_font_style_from_settings(self, field_type: str) -> str:
        """Получает стиль шрифта из настроек"""
        if not self.font_settings:
            return 'normal'
        
        # Для конкретного поля может быть свой стиль
        if field_type in self.font_settings:
            return self.font_settings[field_type].get('font_style', 'normal')
        
        return 'normal'
            
    @staticmethod
    def _draw_qr_code(draw, rect, qr_data_str, mat):
        """Рисует QR-код в указанной области если есть GTIN и total"""
        try:
            if not qr_data_str or not HAS_QRCODE:
                # Очищаем область и выходим
                transformed_rect = rect * mat
                x0, y0 = transformed_rect.x0, transformed_rect.y0
                x1, y1 = transformed_rect.x1, transformed_rect.y1
                draw.rectangle([x0, y0, x1, y1], fill='white')
                return
            
            # Парсим строку
            gtin = ""
            total = ""
            parts = qr_data_str.split(',')
            for part in parts:
                if 'GTIN:' in part:
                    gtin = part.replace('GTIN:', '').strip()
                elif 'TOTAL:' in part:
                    total = part.replace('TOTAL:', '').strip()
            
            # Проверяем наличие GTIN
            if not gtin:
                transformed_rect = rect * mat
                x0, y0 = transformed_rect.x0, transformed_rect.y0
                x1, y1 = transformed_rect.x1, transformed_rect.y1
                draw.rectangle([x0, y0, x1, y1], fill='white')
                return
            
            # Удаляем первый ноль из GTIN если он есть
            if gtin.startswith('0'):
                gtin = gtin[1:]
            
            # Формируем total в формате 8 цифр с ведущими нулями
            total_padded = total.zfill(8)
            
            # Формируем строку для QR: ZZ + GTIN + # + total (8 цифр)
            qr_string = f"ZZ{gtin}#{total_padded}"
            
            # Создаём QR-код
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_string)
            qr.make(fit=True)
            
            # Генерируем изображение QR
            qr_img = qr.make_image(
                fill_color="black",
                back_color="white"
            )
            
            # Фиксированный размер в PDF-пунктах
            qr_size_pdf_units = 52
            qr_size_pixels = int(qr_size_pdf_units * mat.a)
            
            # Масштабируем QR
            qr_img = qr_img.resize(
                (qr_size_pixels, qr_size_pixels), 
                Image.Resampling.LANCZOS
            )
            
            # Получаем координаты плейсхолдера
            transformed_rect = rect * mat
            x0, y0 = transformed_rect.x0, transformed_rect.y0
            x1, y1 = transformed_rect.x1, transformed_rect.y1
            
            # Рассчитываем область для QR (центрируем)
            rect_width = x1 - x0
            rect_height = y1 - y0
            qr_x = x0 + (rect_width - qr_size_pixels) // 2
            qr_y = y0 + (rect_height - qr_size_pixels) // 2
            
            # Вставляем QR-код
            # noinspection PyProtectedMember
            draw._image.paste(qr_img, (int(qr_x), int(qr_y)))
            
        except Exception as e:
            print(f"Ошибка генерации QR: {e}")
            try:
                transformed_rect = rect * mat
                x0, y0 = transformed_rect.x0, transformed_rect.y0
                x1, y1 = transformed_rect.x1, transformed_rect.y1
                draw.rectangle([x0, y0, x1, y1], fill='white')
            except:
                pass
            
    @staticmethod
    def _format_display_text(field_type: str, text: str) -> str:
        """Форматирует текст для отображения с учетом настроек поля"""
        formatting = FIELD_FORMATTING.get(field_type, FIELD_FORMATTING['default'])
        
        display_text = text
        
        # Добавляем префикс если есть
        if 'prefix' in formatting and text:
            display_text = f"{formatting['prefix']}{display_text}"
            
        # Добавляем единицы измерения
        if formatting.get('add_unit', False) and text:
            display_text = f"{display_text}{formatting['unit']}"
            
        return display_text
    
    @staticmethod
    def _get_text_alignment_x(field_type: str, x0: float, rect_width: float, text_width: float) -> float:
        """Возвращает X-координату для выравнивания текста"""
        formatting = FIELD_FORMATTING.get(field_type, FIELD_FORMATTING['default'])
        align = formatting.get('align', 'center')
        
        if align == 'left' or field_type in ['customer', 'product']:
            return x0 + 2
        elif align == 'right':
            return x0 + rect_width - text_width - 2
        else:  # center
            return x0 + (rect_width - text_width) / 2
        
    def _clear_empty_static_text(self, draw: ImageDraw.Draw, page, mat, data_map: Dict[str, str]):
        """Очищает статический текст, если соответствующий плейсхолдер пустой"""
        for static_text, placeholder in self.STATIC_TEXT_MAPPING.items():
            if not data_map.get(placeholder) or data_map[placeholder].strip() == "":
                instances = page.search_for(static_text)
                for rect in instances:
                    # Фильтр артефактов
                    rect_width = rect.x1 - rect.x0
                    rect_height = rect.y1 - rect.y0
                    if rect_width < 10 or rect_height < 5:
                        continue
                        
                    transformed_rect = rect * mat
                    x0, y0 = transformed_rect.x0, transformed_rect.y0
                    x1, y1 = transformed_rect.x1, transformed_rect.y1
                    draw.rectangle([x0, y0, x1, y1], fill='white')
        
    @staticmethod
    def _prepare_text_lines(text: str, font_size: int, wrap_settings: dict) -> List[str]:
        """Разбивает текст на строки с учетом настроек переноса"""
        # Получаем настройки
        dpi = wrap_settings.get("printer_dpi", 203)
        proportionality_factor = wrap_settings.get("font_factor", 0.3)
        label_width = wrap_settings.get("line_width_mm", 79)
        max_lines = wrap_settings.get("max_lines", 3)

        base_font_size = 20  # Размер шрифта превью, для которого настроен proportionality_factor
        
        # Большие шрифты имеют МЕНЬШУЮ пропорциональную ширину символов
        size_correction = base_font_size / font_size
        effective_factor = proportionality_factor * size_correction

        # Конвертируем в пиксели
        pixels_per_mm = dpi / 25.4
        points_per_pt = dpi / 72

        # Расчет доступной ширины
        available_width_pixels = label_width * pixels_per_mm

        # Расчет средней ширины символа в пикселях
        avg_char_width_pixels = (font_size * points_per_pt) * effective_factor

        # Максимальное количество символов в строке
        max_chars = int(available_width_pixels / avg_char_width_pixels)

        # Защита от крайних значений
        if max_chars < 5:
            max_chars = 5
        elif max_chars > 80:
            max_chars = 80

        # Разбиение текста на строки
        words = text.split()
        lines = []
        current_line = ""

        for word in words:
            if not current_line:
                current_line = word
            else:
                test_line = current_line + " " + word
                if len(test_line) <= max_chars:
                    current_line = test_line
                else:
                    lines.append(current_line)
                    current_line = word
            
            # Проверяем лимит строк
            if len(lines) >= max_lines:
                break

        # Добавляем последнюю строку
        if current_line and len(lines) < max_lines:
            lines.append(current_line)

        return lines
            
    def _draw_multiline_text(self, draw: ImageDraw.Draw, rect, lines: List[str], mat, font_size: int):
        """Рисует многострочный текст"""
        transformed_rect = rect * mat
        x0, y0 = transformed_rect.x0, transformed_rect.y0
        x1, y1 = transformed_rect.x1, transformed_rect.y1

        rect_width = x1 - x0
        rect_height = y1 - y0

        # Получаем настройки шрифта из wrap_settings
        wrap_settings = self.font_settings.get("multiline_settings", {})

        font_family = wrap_settings.get("font_family", "Arial")
        font_style = wrap_settings.get("font_style", "normal")

        font = self._get_font(font_size, font_style, font_family)

        # Очищаем область
        draw.rectangle([x0, y0, x1, y1], fill='white')

        # Рассчитываем высоту строки
        bbox = draw.textbbox((0, 0), "Test", font=font)
        line_spacing = 1.4
        line_height = (bbox[3] - bbox[1]) * line_spacing
        total_height = line_height * len(lines)

        # Начальная позиция Y (центрируем по вертикали)
        start_y = y0 + (rect_height - total_height) / 2

        # Рисуем каждую строку
        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            text_x = x0 + (rect_width - text_width) / 2  # Центрируем по горизонтали
            text_y = start_y + (i * line_height)

            draw.text((text_x, text_y), line, fill='black', font=font)

    def _get_font_size_from_settings(self, field_type: str, for_print: bool) -> int:
        """Получает размер шрифта из настроек"""
        if not self.font_settings:
            return 18

        if for_print:
            # Получаем preview размер
            preview_size = self._get_preview_size_from_settings(field_type)
            # Используем сохраненный DPI принтера или значение по умолчанию
            printer_dpi = getattr(self, '_current_printer_dpi', 300)
            preview_dpi = 72 * self.zoom_level  # 108
            # Пересчитываем размер для печати
            return int(preview_size * (printer_dpi / preview_dpi))
        else:
            return self._get_preview_size_from_settings(field_type)

    def _get_preview_size_from_settings(self, field_type: str) -> int:
        """Получает размер шрифта для предпросмотра из настроек"""
        if not self.font_settings:
            return 18

        # Ищем в настройках поля
        if field_type in self.font_settings:
            return self.font_settings[field_type].get("preview", 18)

        # Если поле не найдено, используем "other"
        return self.font_settings.get("other", {}).get("preview", 18)
    
    @staticmethod
    def _get_font(font_size: int, style: str = 'normal', font_family: str = "Arial"):
        """Создает шрифт с настраиваемыми параметрами"""
        try:
            font_files = {
                "Arial": {
                    "normal": "arial.ttf",
                    "bold": "arialbd.ttf", 
                    "italic": "ariali.ttf",
                    "bold_italic": "arialbi.ttf"
                },
                "Times New Roman": {
                    "normal": "times.ttf", 
                    "bold": "timesbd.ttf",
                    "italic": "timesi.ttf", 
                    "bold_italic": "timesbi.ttf"
                },
                "Calibri": {
                    "normal": "calibri.ttf",
                    "bold": "calibrib.ttf",
                    "italic": "calibrii.ttf",
                    "bold_italic": "calibriz.ttf"
                }
            }
            
            # Используем переданный шрифт или Arial по умолчанию
            if font_family not in font_files:
                font_family = "Arial"
                
            font_file = font_files[font_family].get(style, font_files[font_family]["normal"])
            
            font_paths = [
                font_file,
                f"C:\\Windows\\Fonts\\{font_file}",
            ]
            
            for font_path in font_paths:
                try:
                    return ImageFont.truetype(font_path, font_size)
                except:
                    continue
            
            return ImageFont.load_default()
        except:
            return ImageFont.load_default()
    
    def generate_preview(self, data_map: Dict[str, str]) -> Image.Image:
        """Генерирует изображение для предпросмотра"""
        return self.render_page_with_data(data_map, for_print=False)

    def generate_print_image(self, data_map: Dict[str, str], printer_dpi: int = 300) -> Image.Image:
        """Генерирует изображение для печати с указанным DPI"""
        return self.render_page_with_data(data_map, for_print=True, printer_dpi=printer_dpi)
    
    def close(self):
        """Закрывает документ"""
        if self.doc:
            self.doc.close()
    
    def __enter__(self):
        self.open_template()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        
    def invalidate_cache(self):
        """Сбрасывает кэш с увеличением версии"""
        with self._lock:
            self._cache_version += 1
            self._preview_cache.clear()
            self._print_cache.clear()