import tkinter as tk
from tkinter import ttk, StringVar

import win32print
import win32ui
from PIL import Image

from core.settings.font_settings_dialog import FontSettingsDialog


def get_default_printer():
    return win32print.GetDefaultPrinter()


# noinspection PyNoneFunctionAssignment,PyProtectedMember, SpellCheckingInspection
class PrintModule:
    """Модуль управления печатью этикеток"""
    
    def __init__(self, parent, preview_module, coordinator=None, config_manager=None):
        self.original_product_name = None
        self.order_data_module = None
        self._settings_manager = None
        self.print_status_label = None
        self.parent = parent
        self.preview_module = preview_module
        self.coordinator = coordinator
        self.settings_file = "print_settings.json"
        self.config_manager = config_manager

        self.default_settings = {
            "printer_roll": get_default_printer(),
            "printer_box": get_default_printer(),
            "paper_width_mm": 90,
            "paper_height_mm": 72
        }
        self.settings = self.default_settings.copy()
        self.load_settings("weight_box_print")
        
        order_settings = self.config_manager.load_json_settings("shared_utils.json").get("order_number", {})
        self.order_prefix = StringVar(value=order_settings.get("prefix", "Ф"))
        self.order_suffix = StringVar(value=order_settings.get("suffix", "/5"))        
        
        self.selected_preview = "roll"
        self.font_settings = None
        self.load_font_settings()
        self.weight_orders_window = None
        
        # Переменные
        self.copies_var = tk.StringVar(value="1")
        self.connected_roll_module = None
        
        # Переменные для печати тиража
        self.batch_print_data = []
        self.current_batch_index = 0
        self.is_batch_printing = False
        
        self.create_print_ui()
        if self.coordinator and hasattr(self.coordinator, 'subscribe'):
            self.coordinator.subscribe(self.on_settings_changed)

    def receive_status(self, message, color="green"):
        """Получает статус из диалога настроек"""
        self.set_status(message, color)

    # noinspection PyTypeChecker
    def create_print_ui(self):
        """Создает компактный интерфейс управления печатью"""
        frame = ttk.Frame(self.parent, padding=5)
        frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Используем grid для компактного размещения
        frame.grid_columnconfigure(0, weight=1)
        
        # Копий и Печать
        row1_frame = ttk.Frame(frame)
        row1_frame.grid(row=0, column=0, sticky="ew", pady=5)
        row1_frame.grid_columnconfigure(1, weight=1)
        
        ttk.Label(row1_frame, text="Копий:").grid(row=0, column=0, padx=(0, 5), sticky="w")
        copies_entry = ttk.Entry(
            row1_frame, 
            width=7,
            textvariable=self.copies_var,
            justify='center'
        )
        copies_entry.grid(row=0, column=1, padx=(0, 30), sticky="w")
        copies_entry.bind('<FocusIn>', lambda e: copies_entry.select_range(0, tk.END))
        copies_entry.bind('<Return>', lambda e: self.print_rolls_with_box())
        
        ttk.Button(
            row1_frame, 
            text="🖨 Печать", 
            command=self.print_label
        ).grid(row=0, column=2, sticky="w")
        row1_frame.grid_columnconfigure(2, weight=1)
        
        # Настройки
        row2_frame = ttk.Frame(frame)
        row2_frame.grid(row=1, column=0, sticky="ew", pady=7)
        row2_frame.grid_columnconfigure(0, weight=1, uniform="row2")
        row2_frame.grid_columnconfigure(1, weight=1, uniform="row2")      
        
        # Печать тиража
        ttk.Button(
            row2_frame, 
            text="📋 Печать тиража", 
            command=self.start_batch_print
        ).grid(row=0, column=0, sticky="w", pady=5)
        
        ttk.Button(
            row2_frame, 
            text="⚙ Настройки", 
            command=self.open_settings_manager
        ).grid(row=0, column=1, padx=5, sticky="w", pady=5)        
        
        # Статус печати
        self.print_status_label = ttk.Label(
            frame,
            text="",
            foreground="red",
            wraplength=250,
            font=("Arial", 12)
        )
        self.print_status_label.grid(row=2, column=0, sticky="w", pady=(7, 0))
        
    def update_preview_displays(self):
        """Обновляет превью в preview_module (RollPreview)"""
        if self.preview_module is not None:
            self.preview_module.update_preview_displays()

    # noinspection PyUnusedLocal
    def on_settings_changed(self, context=None):
        """Обработчик изменений настроек от координатора"""
        try:
            # Загружаем свежие настройки из JSON
            settings = self.config_manager.load_json_settings("shared_utils.json")
            
            # Обновляем префикс/суффикс номера заказа
            order_settings = settings.get("order_number", {})
            self.order_prefix.set(order_settings.get("prefix", "Ф"))
            self.order_suffix.set(order_settings.get("suffix", "/5"))
            
            # Обновляем настройки печати
            print_settings = self.config_manager.load_json_settings("print_settings.json")
            weight_settings = print_settings.get("weight_box_print", {})
            if weight_settings:
                self.settings.update(weight_settings)
                
        except Exception as e:
            print(f"Ошибка в on_settings_changed PrintModule: {e}")

    def open_settings_manager(self):
        """Открывает единое окно настроек с вкладками"""
        if self.coordinator:
            self._settings_manager = self.coordinator.get_settings_manager()
            if self._settings_manager:
                self._settings_manager.set_status_callback(self.receive_status)
                self._settings_manager.show()

    def set_status(self, message, color="green"):
        """Универсальный метод установки статуса"""
        if self.print_status_label is not None:
            self.print_status_label.config(text=message, foreground=color)
            self.parent.after(5000, lambda: self.print_status_label.config(text=""))
            
    def set_order_data_module(self, order_data_module):
        self.order_data_module = order_data_module

    def start_batch_print(self):
        """Запускает печать всего тиража из уже распарсенных данных"""
        try:
            # Берем список из order_data_processor через существующие связи
            if self.order_data_module is not None:
                filtered_data = getattr(self.order_data_module, 'filtered_parsed_data', [])
                
                if not filtered_data:
                    self.print_status_label.config(text="Нет данных для печати", foreground="red")
                    return
                
                # === Проверка необходимых полей ===
                required_fields = [
                    (self.connected_roll_module.quantity_var, "Количество"),
                    (self.connected_roll_module.product_text, "Название продукции", self.connected_roll_module.product_text),
                    (self.connected_roll_module.customer_var, "Заказчик", None),
                ]

                empty_fields = self._validate_required_fields(required_fields)
                if empty_fields:
                    self.preview_module.status_label.config(
                        text=f"❌ Заполните поля: {', '.join(empty_fields)}", 
                        foreground="red"
                    )
                    self.parent.after(5000, lambda: self.preview_module.status_label.config(text=""))
                    return
                
                # Сохраняем оригинальное название для восстановления
                self.original_product_name = self.preview_module.connected_roll_module.product_text.get("1.0", "end-1c")
                
                # Начинаем печать
                self.batch_print_data = filtered_data
                self.current_batch_index = 0
                self.is_batch_printing = True
                
                self.print_next_in_batch()
            else:
                self.print_status_label.config(text="Модуль данных не подключен", foreground="red")
                
        except Exception as e:
            self.print_status_label.config(text=f"Ошибка: {str(e)}", foreground="red")

    def print_next_in_batch(self):
        """Печатает следующий вид в тираже с учетом количества stream"""
        if not self.is_batch_printing or self.current_batch_index >= len(self.batch_print_data):
            # Завершение печати
            if self.original_product_name is not None:
                self.preview_module.connected_roll_module.product_text.delete("1.0", tk.END)
                self.preview_module.connected_roll_module.product_text.insert("1.0", self.original_product_name)          
            
            self.copies_var.set("1")
            self.is_batch_printing = False
            self.set_status(f"Печать завершена ({self.current_batch_index} шт)", "green")
            return
            
        try:
            current_product_data = self.batch_print_data[self.current_batch_index]
            current_product_name = current_product_data['name']
            stream_count = int(current_product_data.get('stream', 1))
            date_emission = current_product_data.get('date_emission', '')
            
            # Временно подменяем название продукции
            self.preview_module.connected_roll_module.product_text.delete("1.0", tk.END)
            self.preview_module.connected_roll_module.product_text.insert("1.0", current_product_name)
            
            # Устанавливаем дату эмиссии (если есть)
            if date_emission:
                self.preview_module.connected_roll_module.date_emission_var.set(date_emission)
            else:
                # Если у вида нет даты - очищаем поле
                self.preview_module.connected_roll_module.date_emission_var.set("")          
            
            # Ждем обновления данных перед печатью
            self.parent.after(100, lambda: self.print_current_item(stream_count))
            
        except Exception as e:
            self.print_status_label.config(text=f"Ошибка печати вида {self.current_batch_index + 1}: {str(e)}", foreground="red")
            self.current_batch_index += 1
            self.parent.after(100, self.print_next_in_batch)

    def print_current_item(self, stream_count):
        """Печатает текущий элемент после обновления данных"""
        try:
            # Получаем множитель из copies_var (то, что ввел пользователь)
            copies_var_value = self.copies_var.get().strip()
            copies_multiplier = int(copies_var_value) if copies_var_value else 1

            # Умножаем на stream_count
            total_copies = stream_count * copies_multiplier

            # Получаем принтер в зависимости от типа этикетки
            if self.selected_preview == "roll":
                printer_name = self._get_printer("roll")
            else:  # box
                printer_name = self._get_printer("box")

            if not printer_name:
                self.print_status_label.config(text="Принтер не найден!", foreground="red")
                return

            if self.selected_preview == "roll":
                data_map = self.preview_module._prepare_roll_data_map()
                print_image = self.preview_module.roll_pdf_filler.generate_print_image(data_map)
                pdf_filler = self.preview_module.roll_pdf_filler
            else:
                data_map = self.preview_module._prepare_box_data_map()
                print_image = self.preview_module.box_pdf_filler.generate_print_image(data_map)
                pdf_filler = self.preview_module.box_pdf_filler

            for i in range(total_copies):
                self._print_image_gdi(print_image, printer_name, pdf_filler)

            # Следующий вид
            self.current_batch_index += 1
            self.parent.after(100, self.print_next_in_batch)

        except Exception as e:
            self.print_status_label.config(text=f"Ошибка печати вида {self.current_batch_index + 1}: {str(e)}",
                                           foreground="red")
            self.current_batch_index += 1
            self.parent.after(100, self.print_next_in_batch)

    def load_settings(self, settings_key):
        """Загружает настройки печати из JSON-файла для конкретного ключа"""
        try:
            all_settings = self.config_manager.load_json_settings(self.settings_file)
            if settings_key in all_settings:
                self.settings = {**self.default_settings, **all_settings[settings_key]}
        except Exception as e:
            print(f"Ошибка загрузки настроек печати: {e}")
            self.settings = self.default_settings.copy()
            
    def load_font_settings(self):
        """Загружает настройки шрифтов"""
        # Пытаемся загрузить из файла
        loaded_settings = self.config_manager.load_json_settings("label_font_settings.json")
        
        if loaded_settings:
            self.font_settings = loaded_settings
        else:
            # Используем настройки по умолчанию из FontSettingsDialog
            self.font_settings = FontSettingsDialog.get_default_font_settings()

    def update_font_settings(self, new_settings):
        """Обновляет настройки шрифтов в preview_module"""
        self.font_settings = new_settings
        self.preview_module.update_font_settings(new_settings)

    def print_rolls_with_box(self):
        """Печатает N копий ролика и одну коробку с N роликами"""
        original_rolls_count = None
        try:
            # === Проверка полей ===
            required_fields = [
                (self.connected_roll_module.quantity_var, "Количество"),
                (self.connected_roll_module.product_text, "Название продукции",
                 self.connected_roll_module.product_text),
                (self.connected_roll_module.customer_var, "Заказчик", None),
            ]

            empty_fields = self._validate_required_fields(required_fields)
            if empty_fields:
                self.preview_module.status_label.config(
                    text=f"❌ Заполните поля: {', '.join(empty_fields)}",
                    foreground="red"
                )
                self.parent.after(5000, lambda: self.preview_module.status_label.config(text=""))
                return

            # === Получение данных ===
            copies_text = self.copies_var.get().strip()
            copies = int(copies_text) if copies_text else 1

            if copies < 1:
                copies = 1

            # Сохраняем оригинальное количество роликов
            original_rolls_count = self.connected_roll_module.rolls_count_var.get()

            # Получаем принтеры
            roll_printer = self._get_printer("roll")
            box_printer = self._get_printer("box")

            if not roll_printer or not box_printer:
                self.print_status_label.config(text="Принтеры не найдены!", foreground="red")
                return

            # === печать роликов (rolls_count = 1) ===
            # Временно ставим 1 ролик для печати этикеток роликов
            self.connected_roll_module.rolls_count_var.set("1")
            self.connected_roll_module.calculate_total_quantity()

            # Принудительно обновляем данные в preview_module
            self.preview_module._update_from_connected_roll_module()

            # Готовим данные для ролика (rolls_count = 1)
            data_map = self.preview_module._prepare_roll_data_map()
            print_image = self.preview_module.roll_pdf_filler.generate_print_image(data_map)

            # Печатаем N копий ролика на принтере для роликов
            for i in range(copies):
                self._print_image_gdi(print_image, roll_printer, self.preview_module.roll_pdf_filler)

            # === Печать коробки (rolls_count = copies) ===
            # Меняем rolls_count на copies для коробки
            self.connected_roll_module.rolls_count_var.set(str(copies))
            # Пересчитываем общее количество мимо таймера
            self.connected_roll_module.force_recalculate_total()

            # Принудительно обновляем данные в preview_module
            self.preview_module._update_from_connected_roll_module()

            # Готовим данные для коробки (rolls_count = copies)
            box_data_map = self.preview_module._prepare_box_data_map()
            box_print_image = self.preview_module.box_pdf_filler.generate_print_image(box_data_map)

            # Печатаем одну коробку на принтере для коробок
            self._print_image_gdi(box_print_image, box_printer, self.preview_module.box_pdf_filler)

            # === Восстанавливаем оригинальное значение ===
            self.connected_roll_module.rolls_count_var.set(original_rolls_count)
            self.connected_roll_module.calculate_total_quantity()
            self.preview_module._update_from_connected_roll_module()

            # === Статус завершения ===
            self.set_status(f"✅ Печать завершена: {copies} роликов + 1 коробка", "green")

        except Exception as e:
            # Восстанавливаем в случае ошибки
            if self.connected_roll_module is not None and 'original_rolls_count' in locals():
                self.connected_roll_module.rolls_count_var.set(original_rolls_count)
                self.connected_roll_module.calculate_total_quantity()
                if self.preview_module is not None:
                    self.preview_module._update_from_connected_roll_module()

            self.print_status_label.config(text=f"Ошибка печати: {str(e)}", foreground="red")

    def print_label(self):
        """Печатает выбранную этикетку с поддержкой автогенерации"""
        try:
            
            # === Проверка необходимых полей ===
            required_fields = [
                (self.connected_roll_module.quantity_var, "Количество"),
                (self.connected_roll_module.product_text, "Название продукции", self.connected_roll_module.product_text),
                (self.connected_roll_module.customer_var, "Заказчик", None),
            ]

            empty_fields = self._validate_required_fields(required_fields)
            if empty_fields:
                self.preview_module.status_label.config(
                    text=f"❌ Заполните поля: {', '.join(empty_fields)}", 
                    foreground="red"
                )
                self.parent.after(5000, lambda: self.preview_module.status_label.config(text=""))
                return
            
            # Получаем данные из roll_module
            roll_module = self.connected_roll_module
            batch_num = roll_module.batch_num_var.get().strip()
            roll_num = roll_module.roll_num_var.get().strip()  
            streams = roll_module.streams_var.get().strip()
            copies_text = self.copies_var.get().strip()
            
            copies = int(copies_text) if copies_text else 1
            if copies < 1:
                copies = 1
            
            # Определяем режим печати
            if batch_num and roll_num and not streams:
                # Ручной режим - одна конкретная комбинация
                self._print_single_combination(batch_num, roll_num, copies)
                
            elif streams and batch_num:
                # Авторежим - генерируем все комбинации
                self._print_auto_combinations(streams, batch_num, copies)
                
            else:
                # Обычный режим - как раньше
                self._print_standard_label(copies)
                
        except Exception as e:
            self.preview_module.status_label.config(text=f"Ошибка печати: {e}", foreground="red")

    def _print_single_combination(self, batch_num, roll_num, copies):
        """Печатает одну комбинацию съём/ролик"""
        # Сохраняем оригинальные данные
        original_batch = self.connected_roll_module.batch_num_var.get()
        original_roll = self.connected_roll_module.roll_num_var.get()
        
        try:
            # Временно устанавливаем нужные номера
            self.connected_roll_module.batch_num_var.set(batch_num)
            self.connected_roll_module.roll_num_var.set(roll_num)
            
            # Обновляем превью и печатаем
            self.preview_module.update_preview_displays()
            self._print_standard_label(copies)
            
        finally:
            # Восстанавливаем оригинальные данные
            self.connected_roll_module.batch_num_var.set(original_batch)
            self.connected_roll_module.roll_num_var.set(original_roll)
            self.preview_module.update_preview_displays()

    def _print_auto_combinations(self, streams, batch_range, copies):
        """Печатает все комбинации по автогенерации"""
        try:
            # Парсим диапазон съёмов
            batch_numbers = self._parse_range(batch_range)
            stream_count = int(streams)
            
            # Генерируем все комбинации
            combinations = []
            for batch in batch_numbers:
                for stream in range(1, stream_count + 1):
                    combinations.append((str(batch), str(stream)))
            
            # Сохраняем оригинальные данные
            original_batch = self.connected_roll_module.batch_num_var.get()
            original_roll = self.connected_roll_module.roll_num_var.get()
            
            # Печатаем каждую комбинацию
            total_combinations = len(combinations)
            for i, (batch, roll) in enumerate(combinations):
                # Устанавливаем текущую комбинацию
                self.connected_roll_module.batch_num_var.set(batch)
                self.connected_roll_module.roll_num_var.set(roll)
                
                # Обновляем превью и печатаем
                self.preview_module._update_from_connected_roll_module()
                self._print_standard_label(copies)             
            
            # Восстанавливаем оригинальные данные
            self.connected_roll_module.batch_num_var.set(original_batch)
            self.connected_roll_module.roll_num_var.set(original_roll)
            self.preview_module.update_preview_displays()
            
            self.preview_module.status_label.config(
                text=f"Автопечать завершена: {total_combinations} комбинаций × {copies} копий", 
                foreground="green"
            )
            self.parent.after(5000, lambda: self.preview_module.status_label.config(text=""))
            
        except Exception as e:
            self.preview_module.status_label.config(text=f"Ошибка автопечати: {e}", foreground="red")

    def _print_standard_label(self, copies):
        """Стандартная печать без изменений"""
        # Выбираем принтер в зависимости от типа этикетки
        if self.selected_preview == "roll":
            printer_name = self._get_printer("roll")
        else:  # box
            printer_name = self._get_printer("box")

        if not printer_name:
            self.preview_module.status_label.config(text="Принтер не найден!", foreground="red")
            self.parent.after(5000, lambda: self.preview_module.status_label.config(text=""))
            return

        if self.selected_preview == "roll":
            data_map = self.preview_module._prepare_roll_data_map()
            print_image = self.preview_module.roll_pdf_filler.generate_print_image(data_map)
            pdf_filler = self.preview_module.roll_pdf_filler
        else:
            data_map = self.preview_module._prepare_box_data_map()
            print_image = self.preview_module.box_pdf_filler.generate_print_image(data_map)
            pdf_filler = self.preview_module.box_pdf_filler

        for i in range(copies):
            self._print_image_gdi(print_image, printer_name, pdf_filler)

    @staticmethod
    def _parse_range(range_str):
        """Парсит диапазон типа '1-5' в список чисел [1,2,3,4,5]"""
        try:
            if '-' in range_str:
                start, end = map(int, range_str.split('-'))
                return list(range(start, end + 1))
            else:
                return [int(range_str)]
        except:
            raise ValueError(f"Неверный формат диапазона: {range_str}")

    def _get_printer(self, printer_type="roll"):
        """Возвращает принтер для указанного типа"""
        try:
            # Загружаем настройки печати
            print_settings = self.config_manager.load_json_settings("print_settings.json")
            weight_settings = print_settings.get("weight_box_print", {})

            if printer_type == "roll":
                saved_printer = weight_settings.get("printer_roll", "")
            else:  # box
                saved_printer = weight_settings.get("printer_box", "")

            # Если принтер сохранен в настройках, проверяем его доступность
            if saved_printer:
                printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)
                available_printers = [printer[2] for printer in printers]

                if saved_printer in available_printers:
                    return saved_printer
                else:
                    print(f"Сохраненный принтер '{saved_printer}' недоступен")

            # Fallback: ищем принтер с "big" в названии
            printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)
            big_printers = []
            for printer in printers:
                printer_name = printer[2]
                if printer_name.lower().startswith('big'):
                    big_printers.append(printer_name)

            if big_printers:
                return big_printers[0]
            else:
                # Возвращаем первый доступный принтер
                available_printers = [printer[2] for printer in printers]
                if available_printers:
                    return available_printers[0]
                return None

        except Exception as e:
            print(f"Ошибка поиска принтера: {e}")
            return None

    @staticmethod
    def _print_image_gdi(img: Image.Image, printer_name: str, pdf_filler):
        """печатает изображение через GDI с размерами из PDF шаблона"""
        try:
            # создаём контекст устройства для принтера
            hdc = win32ui.CreateDC()
            hdc.CreatePrinterDC(printer_name)

            if not hdc:
                raise Exception(f"не удалось создать контекст устройства для: {printer_name}")

            # получаем разрешение принтера в dpi
            printer_dpi_x = hdc.GetDeviceCaps(88)  # LOGPIXELSX
            printer_dpi_y = hdc.GetDeviceCaps(90)  # LOGPIXELSY

            # получаем размер этикетки из PDF шаблона
            width_mm, height_mm = pdf_filler.get_template_size_mm()
            if width_mm <= 0 or height_mm <= 0:
                raise Exception(f"не удалось получить размер из PDF шаблона")

            # конвертируем миллиметры в пиксели с учётом DPI принтера
            paper_width_pixels = int(width_mm / 25.4 * printer_dpi_x)
            paper_height_pixels = int(height_mm / 25.4 * printer_dpi_y)

            # рассчитываем масштаб для вписывания изображения в размер этикетки
            img_width, img_height = img.size
            scale_x = paper_width_pixels / img_width
            scale_y = paper_height_pixels / img_height
            scale = min(scale_x, scale_y)

            new_width = int(img_width * scale)
            new_height = int(img_height * scale)

            # центрируем изображение на листе
            x_offset = (paper_width_pixels - new_width) // 2
            y_offset = (paper_height_pixels - new_height) // 2

            # отправляем на печать
            doc_name = "Label Print"
            hdc.StartDoc(doc_name)
            hdc.StartPage()

            from PIL import ImageWin
            dib = ImageWin.Dib(img)
            dib.draw(hdc.GetHandleOutput(), (x_offset, y_offset, x_offset + new_width, y_offset + new_height))

            hdc.EndPage()
            hdc.EndDoc()

        except Exception as e:
            raise Exception(f"ошибка печати GDI: {str(e)}")

    def call_roll_module_method(self, method_name, *args, **kwargs):
        """Универсальный метод для вызовов методов подключенного модуля ролика"""
        if self.connected_roll_module and hasattr(self.connected_roll_module, method_name):
            method = getattr(self.connected_roll_module, method_name)
            return method(*args, **kwargs)
        else:
            print(f"Метод {method_name} не найден в подключенном модуле")
            return None

    def set_roll_module(self, roll_module):
        """Устанавливает связь с модулем ролика"""
        self.connected_roll_module = roll_module

    # noinspection PyUnusedLocal
    @staticmethod
    def _validate_required_fields(field_vars):
        """
        Проверяет список полей на пустоту.
        field_vars: список кортежей (var, field_name, widget)
                    где var - StringVar/Tkinter var,
                    field_name - название поля для сообщения,
                    widget - виджет Text (если нужно) или None
        """
        empty_fields = []
        
        for item in field_vars:
            if len(item) == 3:
                var, field_name, widget = item
                # Для Text виджета
                if widget:
                    value = widget.get("1.0", "end-1c").strip()
                else:
                    value = var.get().strip()
            else:
                var, field_name = item
                value = var.get().strip()
                widget = None
                
            if not value:
                empty_fields.append(field_name)
        
        return empty_fields