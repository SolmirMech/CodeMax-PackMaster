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
    
    def __init__(self, parent, preview_module, coordinator=None, config_manager=None, app=None):
        self.app = app
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
        self.auto_export_var = tk.BooleanVar(value=False)
        
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

        # Галочка "Автоотправка в Эксель"
        ttk.Checkbutton(
            row2_frame,
            text="Автоотправка в Эксель",
            variable=self.auto_export_var
        ).grid(row=1, column=0, columnspan=2, padx=(20, 0), sticky="w", pady=5)
        
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
        """Обновляет превью в preview_module"""
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
            # === Проверка производителя ===
            is_ecosystem = False
            if self.connected_roll_module and hasattr(self.connected_roll_module, 'manufacturer_var'):
                manufacturer = self.connected_roll_module.manufacturer_var.get().lower()
                is_ecosystem = "экосистема" in manufacturer

            # Берем список из order_data_processor через существующие связи
            if self.order_data_module is not None:
                filtered_data = getattr(self.order_data_module, 'filtered_parsed_data', [])

                if not filtered_data:
                    self.print_status_label.config(text="Нет данных для печати", foreground="red")
                    return

                # === Проверка необходимых полей (только не для экосистемы) ===
                if not is_ecosystem:
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
            # Получаем множитель из copies_var
            copies_var_value = self.copies_var.get().strip()
            copies_multiplier = int(copies_var_value) if copies_var_value else 1

            # Умножаем на stream_count
            total_copies = stream_count * copies_multiplier

            # Получаем принтер в зависимости от типа этикетки
            if self.selected_preview == "roll":
                printer_name = self._get_printer("roll")
            else:
                printer_name = self._get_printer("box")

            if not printer_name:
                self.print_status_label.config(text="Принтер не найден!", foreground="red")
                return

            printer_dpi = self._get_printer_dpi(printer_name)

            if self.selected_preview == "roll":
                data_map = self.preview_module._prepare_roll_data_map()
                print_image = self.preview_module.roll_pdf_filler.generate_print_image(data_map,
                                                                                       printer_dpi=printer_dpi)
                pdf_filler = self.preview_module.roll_pdf_filler
            else:
                data_map = self.preview_module._prepare_box_data_map()
                print_image = self.preview_module.box_pdf_filler.generate_print_image(data_map, printer_dpi=printer_dpi)
                pdf_filler = self.preview_module.box_pdf_filler

            for i in range(total_copies):
                self._print_image_gdi(print_image, printer_name, pdf_filler, printer_dpi)

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
            # === Проверка производителя ===
            is_ecosystem = False
            if self.connected_roll_module and hasattr(self.connected_roll_module, 'manufacturer_var'):
                manufacturer = self.connected_roll_module.manufacturer_var.get().lower()
                is_ecosystem = "экосистема" in manufacturer

            # === Проверка полей (только не для экосистемы) ===
            if not is_ecosystem:
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

            # Получаем DPI принтеров
            roll_printer_dpi = self._get_printer_dpi(roll_printer)
            box_printer_dpi = self._get_printer_dpi(box_printer)

            # === печать роликов (rolls_count = 1) ===
            self.connected_roll_module.rolls_count_var.set("1")
            self.connected_roll_module.calculate_total_quantity()
            self.preview_module.update_from_connected_roll_module()

            data_map = self.preview_module._prepare_roll_data_map()
            print_image = self.preview_module.roll_pdf_filler.generate_print_image(data_map,
                                                                                   printer_dpi=roll_printer_dpi)

            for i in range(copies):
                self._print_image_gdi(print_image, roll_printer, self.preview_module.roll_pdf_filler, roll_printer_dpi)

            # === Печать коробки (rolls_count = copies) ===
            self.connected_roll_module.rolls_count_var.set(str(copies))
            self.connected_roll_module.force_recalculate_total()
            self.preview_module.update_from_connected_roll_module()

            box_data_map = self.preview_module._prepare_box_data_map()
            box_print_image = self.preview_module.box_pdf_filler.generate_print_image(box_data_map,
                                                                                      printer_dpi=box_printer_dpi)

            self._print_image_gdi(box_print_image, box_printer, self.preview_module.box_pdf_filler, box_printer_dpi)

            # === Восстанавливаем оригинальное значение ===
            self.connected_roll_module.rolls_count_var.set(original_rolls_count)
            self.connected_roll_module.calculate_total_quantity()
            self.preview_module.update_from_connected_roll_module()

            self.set_status(f"✅ Печать завершена: {copies} роликов + 1 коробка", "green")

        except Exception as e:
            if self.connected_roll_module is not None and 'original_rolls_count' in locals():
                self.connected_roll_module.rolls_count_var.set(original_rolls_count)
                self.connected_roll_module.calculate_total_quantity()
                if self.preview_module is not None:
                    self.preview_module.update_from_connected_roll_module()
            self.print_status_label.config(text=f"Ошибка печати: {str(e)}", foreground="red")

    def print_label(self):
        """Печатает выбранную этикетку с поддержкой автогенерации"""
        try:
            # === Проверка производителя ===
            is_ecosystem = False
            if self.connected_roll_module and hasattr(self.connected_roll_module, 'manufacturer_var'):
                manufacturer = self.connected_roll_module.manufacturer_var.get().lower()
                is_ecosystem = "экосистема" in manufacturer

            # === Проверка необходимых полей (только не для экосистемы) ===
            if not is_ecosystem:
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

            # Получаем данные из roll_module
            roll_module = self.connected_roll_module
            batch_num = roll_module.batch_num_var.get().strip()
            roll_num = roll_module.roll_num_var.get().strip()
            streams = roll_module.streams_var.get().strip()
            copies_text = self.copies_var.get().strip()

            copies = int(copies_text) if copies_text else 1
            if copies < 1:
                copies = 1

            # Определяем, содержит ли batch_num диапазон (например, "1-5")
            is_range = '-' in batch_num

            # Определяем режим печати
            if batch_num and roll_num and not is_range:
                # Один конкретный съём и конкретный рулон — одиночная печать
                self._print_single_combination(batch_num, roll_num, copies)

            elif batch_num and roll_num and is_range:
                # Диапазон съёмов + конкретный рулон — печатаем все съёмы с одним рулоном
                self._print_auto_combinations(streams, batch_num, copies, roll_specified=True)

            elif batch_num and not roll_num:
                # Указан только съём (или диапазон) — печатаем все ручьи для каждого съёма
                self._print_auto_combinations(streams, batch_num, copies, roll_specified=False)

            else:
                # Обычный режим — без автогенерации
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

    def _print_auto_combinations(self, streams, batch_range, copies, roll_specified=False):
        """Печатает все комбинации по автогенерации.
        Если roll_specified=True — печатает только указанный ручей для каждого съёма.
        """
        try:
            # Парсим диапазон съёмов
            batch_numbers = self._parse_range(batch_range)

            # Сохраняем оригинальные данные
            original_batch = self.connected_roll_module.batch_num_var.get()
            original_roll = self.connected_roll_module.roll_num_var.get()

            # Генерируем комбинации
            if roll_specified:
                # Печатаем только указанный ручей для каждого съёма
                combinations = [(str(batch), original_roll) for batch in batch_numbers]
            else:
                # Печатаем все ручьи × все съёмы
                stream_count = int(streams) if streams else 1
                combinations = []
                for batch in batch_numbers:
                    for stream in range(1, stream_count + 1):
                        combinations.append((str(batch), str(stream)))

            # Печатаем каждую комбинацию
            total_combinations = len(combinations)
            for i, (batch, roll) in enumerate(combinations):
                self.connected_roll_module.batch_num_var.set(batch)
                self.connected_roll_module.roll_num_var.set(roll)

                self.preview_module.update_from_connected_roll_module()
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
        else:
            printer_name = self._get_printer("box")

        if not printer_name:
            self.preview_module.status_label.config(text="Принтер не найден!", foreground="red")
            self.parent.after(5000, lambda: self.preview_module.status_label.config(text=""))
            return

        printer_dpi = self._get_printer_dpi(printer_name)

        if self.selected_preview == "roll":
            data_map = self.preview_module._prepare_roll_data_map()
            print_image = self.preview_module.roll_pdf_filler.generate_print_image(data_map, printer_dpi=printer_dpi)
            pdf_filler = self.preview_module.roll_pdf_filler
        else:
            data_map = self.preview_module._prepare_box_data_map()
            print_image = self.preview_module.box_pdf_filler.generate_print_image(data_map, printer_dpi=printer_dpi)
            pdf_filler = self.preview_module.box_pdf_filler

        for i in range(copies):
            self._print_image_gdi(print_image, printer_name, pdf_filler, printer_dpi)

        # Автоотправка в Excel после печати
        if self.auto_export_var.get() and self.connected_roll_module:
            self._auto_export_to_excel()

    def _auto_export_to_excel(self):
        """Автоматический экспорт в Excel после печати"""
        try:
            if self.app and hasattr(self.app, 'export_module'):
                self.app.export_module.export_to_excel()
        except Exception as e:
            print(f"Ошибка автоэкспорта: {e}")

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
    def _print_image_gdi(img: Image.Image, printer_name: str, pdf_filler, printer_dpi: int = 300):
        """Улучшенная печать с сохранением качества"""
        try:
            hdc = win32ui.CreateDC()
            hdc.CreatePrinterDC(printer_name)

            # Получаем размер этикетки в мм
            width_mm, height_mm = pdf_filler.get_template_size_mm()

            # Рассчитываем целевой размер в пикселях
            target_width = int(width_mm / 25.4 * printer_dpi)
            target_height = int(height_mm / 25.4 * printer_dpi)

            # Если изображение уже имеет нужный размер - используем как есть
            if img.size != (target_width, target_height):
                # Ресайзим с высоким качеством
                img = img.resize(
                    (target_width, target_height),
                    Image.Resampling.LANCZOS
                )

            doc_name = "Label Print"
            hdc.StartDoc(doc_name)
            hdc.StartPage()

            from PIL import ImageWin

            # Конвертируем в режим с высоким качеством
            if img.mode != 'RGB':
                img = img.convert('RGB')

            dib = ImageWin.Dib(img)
            # Печатаем на всю область
            dib.draw(hdc.GetHandleOutput(), (0, 0, target_width, target_height))

            hdc.EndPage()
            hdc.EndDoc()
            hdc.DeleteDC()

        except Exception as e:
            raise Exception(f"Ошибка печати: {str(e)}")

    @staticmethod
    def _get_printer_dpi(printer_name: str) -> int:
        """Получает DPI принтера"""
        try:
            hdc = win32ui.CreateDC()
            hdc.CreatePrinterDC(printer_name)
            dpi_x = hdc.GetDeviceCaps(88)  # LOGPIXELSX
            hdc.DeleteDC()
            return dpi_x
        except:
            return 300

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