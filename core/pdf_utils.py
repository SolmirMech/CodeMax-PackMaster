# core/pdf_utils.py
import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont
from typing import Dict, List, Tuple, Optional
import os
import io

class PDFTemplateFiller:
    """Класс для заполнения PDF шаблонов с плейсхолдерами"""
    
    # Сопоставление имен полей плейсхолдеров с настройками
    FIELD_MAPPING = {
        # РОЛИК
        "customer": "customer",      # $customer - заказчик
        "brutto": "other",           # $brutto - вес брутто (группа "other" для ролика)
        "netto": "other",            # $netto - вес нетто (группа "other" для ролика)
        "rol": "other",              # $rol - кол-во этикеток в ролике (группа "other" для ролика)
        "tr": "other",               # $tr - кол-во роликов (группа "other" для ролика)
        "sx": "other",               # $sx - схема намотки (группа "other" для ролика)
        "dia": "other",              # dia - диаметр втулки (группа "other" для ролика)
        "onum": "other",             # $onum - номер заказа (группа "other" для ролика)
        "date": "other",             # $date - дата изготовления (группа "other" для ролика)
        "product": "product",        # $product - изделие
        "packer": "other",           # $packer - упаковщик (группа "other" для ролика)
        "emission": "other",           # $emission - дата эмиссии (группа "other")
        
        # КОРОБКА - отдельные настройки
        "printhouse": "manufacturer",    # $printhouse - изготовитель
        "printaddress": "address",       # $printaddress - адрес изготовителя
        "total": "total",                # $total - всего этикеток в коробке
        "tu_number": "tu_number",        # $tu_number - технические условия
        
        # КОРОБКА - группа "other" (одинаковый размер шрифта)
        # Эти поля в коробке используют настройку "other":
        # "customer": "customer",        # НЕТ! В коробке заказчик отдельно
        # "product": "product",          # НЕТ! В коробке изделие отдельно  
        # "packer": "packer",            # НЕТ! В коробке упаковщик отдельно
        "rol": "other",                  # $rol - в коробке в группе "other"
        "tr": "other",                   # $tr - в коробке в группе "other"
        "onum": "other",                 # $onum - в коробке в группе "other"
        "dia": "other",                  # dia - в коробке в группе "other"
        "date": "other",                 # $date - в коробке в группе "other"
        "sx": "other",                   # $sx - в коробке в группе "other"
        "brutto": "other",               # $brutto - в коробке в группе "other"
        "netto": "other",                # $netto - в коробке в группе "other"
        "box_brut": "other",
        "box_net": "other",
    }    
    
    def __init__(self, template_path: str):
        self.template_path = template_path
        self.doc = None
        self.zoom_level = 1.5
        self.font_settings = None
        
    def set_font_settings(self, font_settings: Dict):
        """Устанавливает настройки шрифтов"""
        self.font_settings = font_settings
        
    def open_template(self):
        """Открывает PDF шаблон"""
        if not os.path.exists(self.template_path):
            raise FileNotFoundError(f"PDF шаблон не найден: {self.template_path}")
        
        self.doc = fitz.open(self.template_path)
        return self.doc
    
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

    def render_page_with_data(self, page_num: int, data_map: Dict[str, str], for_print: bool = False) -> Image.Image:
        """Рендерит страницу PDF с подставленными данными"""
        if not self.doc:
            self.open_template()
            
        page = self.doc[page_num]
        
        # Определяем DPI в зависимости от назначения
        if for_print:
            dpi = 300
            mat = fitz.Matrix(dpi/72, dpi/72)
        else:
            mat = fitz.Matrix(self.zoom_level, self.zoom_level)
            
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("ppm")
        img = Image.open(io.BytesIO(img_data))
        
        draw = ImageDraw.Draw(img)
        
        # Копируем data_map и удаляем служебное поле $d если есть
        data_map_without_d = data_map.copy()
        if '$d' in data_map_without_d:
            del data_map_without_d['$d']
            
        # Очистка статического текста "Изготовитель" если скрываем производителя
        if not data_map.get("$printhouse") or data_map["$printhouse"].strip() == "":
            # Ищем и очищаем текст "Изготовитель"
            manufacturer_instances = page.search_for("Изготовитель:")
            for rect in manufacturer_instances:
                # ФИЛЬТР: пропускаем слишком маленькие прямоугольники (артефакты)
                rect_width = rect.x1 - rect.x0
                rect_height = rect.y1 - rect.y0
                if rect_width < 10 or rect_height < 5:
                    continue
                    
                transformed_rect = rect * mat
                x0, y0 = transformed_rect.x0, transformed_rect.y0
                x1, y1 = transformed_rect.x1, transformed_rect.y1
                draw.rectangle([x0, y0, x1, y1], fill='white')
                
        if not data_map.get("$emission") or data_map["$emission"].strip() == "":
            # Ищем и очищаем текст "Дата эмиссии" (возможные варианты написания)
            emission_texts = ["Дата эмиссии:", "Эмиссия:", "Дата эмиссия:"]
            for emission_text in emission_texts:
                emission_instances = page.search_for(emission_text)
                for rect in emission_instances:
                    # ФИЛЬТР: пропускаем слишком маленькие прямоугольники (артефакты)
                    rect_width = rect.x1 - rect.x0
                    rect_height = rect.y1 - rect.y0
                    if rect_width < 10 or rect_height < 5:
                        continue
                        
                    transformed_rect = rect * mat
                    x0, y0 = transformed_rect.x0, transformed_rect.y0
                    x1, y1 = transformed_rect.x1, transformed_rect.y1
                    draw.rectangle([x0, y0, x1, y1], fill='white')
        
        # Список всех плейсхолдеров для очистки
        all_placeholders = [
            "$customer", "$product", "$onum", "$date", "$packer",
            "$brutto", "$netto", "$rol", "$tr", "$sx", "dia",
            "$printhouse", "$printaddress", "$total", "$tu_number",
            "$box_brut", "$box_net", "$emission"
        ]
        
        # Очищаем области пустых плейсхолдеров
        for placeholder in all_placeholders:
            if placeholder in data_map_without_d and (not data_map_without_d[placeholder] or data_map_without_d[placeholder].strip() == ""):
                instances = page.search_for(placeholder)
                for rect in instances:
                    # ФИЛЬТР: пропускаем слишком маленькие прямоугольники (артефакты)
                    rect_width = rect.x1 - rect.x0
                    rect_height = rect.y1 - rect.y0
                    if rect_width < 10 or rect_height < 5:
                        continue
                        
                    transformed_rect = rect * mat
                    x0, y0 = transformed_rect.x0, transformed_rect.y0
                    x1, y1 = transformed_rect.x1, transformed_rect.y1
                    draw.rectangle([x0, y0, x1, y1], fill='white')
        
        # Обрабатываем ВСЕ плейсхолдеры
        for placeholder, new_text in data_map_without_d.items():
            if not new_text or new_text.strip() == "":
                continue
                
            instances = page.search_for(placeholder)
            for rect in instances:
                # ФИЛЬТР: пропускаем слишком маленькие прямоугольники (артефакты)
                rect_width = rect.x1 - rect.x0
                rect_height = rect.y1 - rect.y0
                
                # Если прямоугольник меньше 10 пикселей по ширине - скорее всего артефакт
                if rect_width < 10 or rect_height < 5:
                    print(f"Пропускаем артефакт: {placeholder} размер {rect_width}x{rect_height}")
                    continue
                    
                # Передаем тип поля без знака $
                field_type = placeholder[1:] if placeholder.startswith('$') else placeholder
                self._replace_text_in_rect(draw, rect, new_text, mat, field_type, for_print)
        
        return img
        
    def _prepare_text_lines(self, text: str, font_size: int, wrap_settings: dict, for_print: bool) -> List[str]:
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

    def _replace_text_in_rect(self, draw: ImageDraw.Draw, rect, text: str, mat, field_type: str = "default", for_print: bool = False):
        """Заменяет текст в указанной области"""
        try:
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
            else:
                # Значения по умолчанию
                if for_print:
                    if field_type in ['customer', 'product']:
                        font_size = 48
                    else:
                        font_size = 42
                else:
                    if field_type in ['customer', 'product']:
                        font_size = 30
                    else:
                        font_size = 18
            
            # Для поля product используем многострочную отрисовку (даже для одной строки)
            if field_type == "product" and self.font_settings:
                wrap_settings = self.font_settings.get("multiline_settings", {})
                
                if wrap_settings:
                    # Разбиваем текст на строки (может вернуть 1, 2, 3 или больше строк)
                    lines = self._prepare_text_lines(text, font_size, wrap_settings, for_print)
                    
                    # Отрисовываем через многострочный метод (работает и для одной строки)
                    self._draw_multiline_text(draw, rect, lines, mat, font_size, for_print)
                    return  # Выходим, так как текст уже отрисован
            
            # Для остальных полей - стандартная однострочная отрисовка
            font = self._get_font(font_size, 'bold' if for_print else 'normal')
            
            x0, y0 = transformed_rect.x0, transformed_rect.y0
            x1, y1 = transformed_rect.x1, transformed_rect.y1
            
            rect_width = x1 - x0
            rect_height = y1 - y0
            
            # Добавляем единицы измерения (только для определенных полей)
            display_text = text
            if field_type == 'brutto' and text:
                display_text = f"Брутто {text} кг"
            elif field_type == 'netto' and text:
                display_text = f"Нетто {text} кг" 
            elif field_type == 'dia' and text:
                display_text = f"{text} мм"
            elif field_type == 'tr' and text:
                display_text = f"{text} шт"
            elif field_type == 'box_brut' and text:
                display_text = f"Брутто {text} кг"
            elif field_type == 'box_net' and text:
                display_text = f"Нетто {text} кг"
            elif field_type == 'emission' and text:
                display_text = f"{text}"
            
            bbox = draw.textbbox((0, 0), display_text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # Выравнивание в зависимости от типа поля
            if field_type in ['customer', 'product']:
                text_x = x0 + 2
            else:
                # Центрирование для всех остальных полей
                text_x = x0 + (rect_width - text_width) / 2
                
            text_y = y0 + (rect_height - text_height) / 2 - 3
            
            # Очищаем область и рисуем новый текст
            draw.rectangle([x0, y0, x1, y1], fill='white')
            draw.text((text_x, text_y), display_text, fill='black', font=font)
            
        except Exception as e:
            print(f"Ошибка замены текста {field_type}: {e}")
            
    def _draw_multiline_text(self, draw: ImageDraw.Draw, rect, lines: List[str], mat, font_size: int, for_print: bool):
        """Рисует многострочный текст"""
        transformed_rect = rect * mat
        x0, y0 = transformed_rect.x0, transformed_rect.y0
        x1, y1 = transformed_rect.x1, transformed_rect.y1
        
        rect_width = x1 - x0
        rect_height = y1 - y0
        
        # Получаем настройки шрифта из wrap_settings
        template_type = "roll" if "roll" in str(self.template_path) else "box"
        wrap_settings = self.font_settings.get("multiline_settings", {})
        
        font_family = wrap_settings.get("font_family", "Arial")
        font_style = wrap_settings.get("font_style", "normal")
        
        font = self._get_font(font_size, font_style, font_family)
        
        # Очищаем область
        draw.rectangle([x0, y0, x1, y1], fill='white')
        
        # Рассчитываем высоту строки
        bbox = draw.textbbox((0, 0), "Test", font=font)
        # Добавляем межстрочный интервал
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
            
        setting_type = "print" if for_print else "preview"
        
        # Ищем настройку для конкретного поля
        if field_type in self.font_settings:
            return self.font_settings[field_type].get(setting_type, 18)
        
        # Если поле не найдено, используем настройку "other"
        return self.font_settings.get("other", {}).get(setting_type, 18)
    
    def _get_font(self, font_size: int, style: str = 'normal', font_family: str = "Arial"):
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
        return self.render_page_with_data(0, data_map, for_print=False)
    
    def generate_print_image(self, data_map: Dict[str, str]) -> Image.Image:
        """Генерирует изображение для печати"""
        return self.render_page_with_data(0, data_map, for_print=True)
    
    def close(self):
        """Закрывает документ"""
        if self.doc:
            self.doc.close()
    
    def __enter__(self):
        self.open_template()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()