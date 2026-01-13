# apps/print_module.py
import tkinter as tk
from tkinter import ttk, StringVar
import win32print
import win32ui
from PIL import Image, ImageTk
from core.settings.settings_dialog import SettingsDialog
from core.config_manager import ConfigManager
from core.settings.font_settings_dialog import FontSettingsDialog
from apps.weight_orders_printer import WeightOrdersPrinter
from core.shared_utils import (
    mm_to_pixels,
    get_default_printer,
    create_printer_dc,
)

class PrintModule:
    """Модуль управления печатью этикеток"""
    
    def __init__(self, parent, preview_module, coordinator=None):
        self.parent = parent
        self.preview_module = preview_module
        self.coordinator = coordinator
        self.settings_file = "print_settings.json"
        self.config_manager = ConfigManager()
        self.manufacturer = self.config_manager.get_manufacturer()
        
        self.default_settings = {
            "printer": get_default_printer(),
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
    
    def create_print_ui(self):
        """Создает интерфейс управления печатью"""
        frame = ttk.Frame(self.parent, padding=5)
        frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Основной фрейм управления
        control_frame = ttk.Frame(frame)
        control_frame.pack(fill=tk.BOTH, expand=True)
        
        # Кол-во копий
        copies_frame = ttk.Frame(control_frame)
        copies_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(copies_frame, text="Копий:").pack(side=tk.LEFT, padx=(0, 5))
        copies_entry = ttk.Entry(
            copies_frame, 
            width=5,
            textvariable=self.copies_var,
            justify='center'
        )
        copies_entry.pack(side=tk.LEFT)
        copies_entry.bind('<FocusIn>', lambda e: copies_entry.select_range(0, tk.END))
        
        # Основные кнопки печати
        buttons_frame = ttk.Frame(control_frame)
        buttons_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(
            buttons_frame, 
            text="🖨 Печать", 
            command=self.print_label
        ).pack(fill=tk.X, pady=5)
        
        ttk.Button(
            buttons_frame, 
            text="⚙ Настройки", 
            command=self.open_settings_manager
        ).pack(fill=tk.X, pady=5)
        
        ttk.Button(
            buttons_frame, 
            text="✓ Ярлык на втулку", 
            command=self.open_weight_orders_window
        ).pack(fill=tk.X, pady=5)
        
        ttk.Button(
            buttons_frame, 
            text="📋 Печать тиража", 
            command=self.start_batch_print
        ).pack(fill=tk.X, pady=5)
        
        # Статус печати
        self.print_status_label = ttk.Label(
            control_frame,
            text="",
            foreground="red",
            wraplength=250,
            font=("Arial", 14)
        )
        self.print_status_label.pack(fill=tk.X, pady=10)
        
    def update_preview_displays(self):
        """Обновляет превью в preview_module (RollPreview)"""
        if hasattr(self, 'preview_module') and self.preview_module:
            self.preview_module.update_preview_displays()        
        
    def on_settings_changed(self):
        """Обработчик изменений настроек от координатора"""

    def open_settings_manager(self):
        """Открывает единое окно настроек с вкладками"""
        from core.settings.settings_manager import SettingsManager
        if not hasattr(self, '_settings_manager'):
            self._settings_manager = SettingsManager(self.parent, self)
            # Передаем колбэк для статуса
            self._settings_manager.set_status_callback(self.set_status)
        self._settings_manager.show()

    def set_status(self, message, color="green"):
        """Универсальный метод установки статуса"""
        if hasattr(self, 'print_status_label'):
            self.print_status_label.config(text=message, foreground=color)
            self.parent.after(5000, lambda: self.print_status_label.config(text=""))
            
    def set_order_data_module(self, order_data_module):
        self.order_data_module = order_data_module

    def start_batch_print(self):
        """Запускает печать всего тиража из уже распарсенных данных"""
        try:
            # Берем список из order_data_processor через существующие связи
            if (hasattr(self, 'order_data_module') and self.order_data_module):
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
            if hasattr(self, 'original_product_name'):
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
            self.parent.after(100, lambda: self.print_current_item(current_product_data, stream_count))
            
        except Exception as e:
            self.print_status_label.config(text=f"Ошибка печати вида {self.current_batch_index + 1}: {str(e)}", foreground="red")
            self.current_batch_index += 1
            self.parent.after(100, self.print_next_in_batch)

    def print_current_item(self, product_data, stream_count):
        """Печатает текущий элемент после обновления данных"""
        try:
            # Получаем множитель из copies_var (то, что ввел пользователь)
            copies_var_value = self.copies_var.get().strip()
            copies_multiplier = int(copies_var_value) if copies_var_value else 1
            
            # Умножаем на stream_count
            total_copies = stream_count * copies_multiplier
            
            # Печатаем total_copies копий
            printer_name = self._find_printer()
            if not printer_name:
                self.print_status_label.config(text="Принтер не найден!", foreground="red")
                return
            
            if self.selected_preview == "roll":
                data_map = self.preview_module._prepare_roll_data_map()
                print_image = self.preview_module.roll_pdf_filler.generate_print_image(data_map)
            else:
                data_map = self.preview_module._prepare_box_data_map()
                print_image = self.preview_module.box_pdf_filler.generate_print_image(data_map)
            
            for i in range(total_copies):
                self._print_image_gdi(print_image, printer_name)
            
            # Следующий вид
            self.current_batch_index += 1
            self.parent.after(100, self.print_next_in_batch)
            
        except Exception as e:
            self.print_status_label.config(text=f"Ошибка печати вида {self.current_batch_index + 1}: {str(e)}", foreground="red")
            self.current_batch_index += 1
            self.parent.after(100, self.print_next_in_batch)
        
    def open_weight_orders_window(self):
        """Открывает окно для работы с втулками"""
        if self.weight_orders_window and self.weight_orders_window.winfo_exists():
            self.weight_orders_window.lift()
            return

        # Создаем новое окно
        self.weight_orders_window = tk.Toplevel(self.parent)
        self.weight_orders_window.title("Втулка")
        self.weight_orders_window.geometry("440x600")
        self.weight_orders_window.grab_set()
        
        # Центрируем окно
        self.weight_orders_window.update_idletasks()
        width = self.weight_orders_window.winfo_width()
        height = self.weight_orders_window.winfo_height()
        x = (self.weight_orders_window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.weight_orders_window.winfo_screenheight() // 2) - (height // 2)
        self.weight_orders_window.geometry(f"+{x}+{y}")
        self.weight_orders_window.bind("<Escape>", lambda e: self.on_weight_orders_close())
        
        # Создаем модуль втулки в этом окне
        self.weight_orders_module = WeightOrdersPrinter(self.weight_orders_window)
        
        # Устанавливаем обработчик закрытия окна
        self.weight_orders_window.protocol("WM_DELETE_WINDOW", self.on_weight_orders_close)
        
    def on_weight_orders_close(self):
        """Обработчик закрытия окна втулки"""
        if self.weight_orders_window:
            self.weight_orders_window.destroy()
            self.weight_orders_window = None
            
    def load_settings(self, settings_key):
        """Загружает настройки печати из JSON-файла для конкретного ключа"""
        try:
            all_settings = self.config_manager.load_json_settings(self.settings_file)
            if settings_key in all_settings:
                self.settings = {**self.default_settings, **all_settings[settings_key]}
        except Exception as e:
            print(f"Ошибка загрузки настроек печати: {e}")
            self.settings = self.default_settings.copy()

    def save_settings(self):
        """Сохраняет настройки для weight_box_print"""
        try:
            all_settings = self.config_manager.load_json_settings(self.settings_file)
            all_settings["weight_box_print"] = self.settings

            if self.config_manager.save_json_settings(self.settings_file, all_settings):
                self.set_status("✅ Настройки печати сохранены!", "green")
                
        except Exception as e:
            self.print_status_label.config(
                text=f"❌ Не удалось сохранить настройки: {str(e)}",
                foreground="red"
                )
            
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
                self.preview_module.update_preview_displays()
                self._print_standard_label(copies)             
            
            # Восстанавливаем оригинальные данные
            self.connected_roll_module.batch_num_var.set(original_batch)
            self.connected_roll_module.roll_num_var.set(original_roll)
            self.preview_module.update_preview_displays()
            
            self.preview_module.status_label.config(
                text=f"Автопечать завершена: {total_combinations} комбинаций × {copies} копий", 
                foreground="green"
            )
            
        except Exception as e:
            self.preview_module.status_label.config(text=f"Ошибка автопечати: {e}", foreground="red")

    def _print_standard_label(self, copies):
        """Стандартная печать без изменений"""
        printer_name = self._find_printer()
        if not printer_name:
            self.preview_module.status_label.config(text="Принтер не найден!", foreground="red")
            return
        
        if self.selected_preview == "roll":
            data_map = self.preview_module._prepare_roll_data_map()
            print_image = self.preview_module.roll_pdf_filler.generate_print_image(data_map)
        else:
            data_map = self.preview_module._prepare_box_data_map()
            print_image = self.preview_module.box_pdf_filler.generate_print_image(data_map)
        
        for i in range(copies):
            self._print_image_gdi(print_image, printer_name)

    def _parse_range(self, range_str):
        """Парсит диапазон типа '1-5' в список чисел [1,2,3,4,5]"""
        try:
            if '-' in range_str:
                start, end = map(int, range_str.split('-'))
                return list(range(start, end + 1))
            else:
                return [int(range_str)]
        except:
            raise ValueError(f"Неверный формат диапазона: {range_str}")
            
    def _find_printer(self):
        """Находит принтер из настроек weight_box_print"""
        try:
            # Загружаем настройки печати
            print_settings = self.config_manager.load_json_settings("print_settings.json")
            weight_settings = print_settings.get("weight_box_print", {})
            saved_printer = weight_settings.get("printer", "")
            
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
            
    def update_local_printer(self):
        """Обновляет список принтеров в настройках"""
        try:
            printers = win32print.EnumPrinters(2)
            printer_names = [p[2] for p in printers]
            
            # Загружаем текущие настройки
            print_settings = self.config_manager.load_json_settings("print_settings.json")
            weight_settings = print_settings.get("weight_box_print", {})
            current_printer = weight_settings.get("printer", "")
            
            # Если текущий принтер недоступен, выбираем первый доступный
            if current_printer not in printer_names and printer_names:
                weight_settings["printer"] = printer_names[0]
                print_settings["weight_box_print"] = weight_settings
                self.config_manager.save_json_settings("print_settings.json", print_settings)
                
        except Exception as e:
            print(f"Ошибка обновления принтеров: {e}")

    def _print_image_gdi(self, img: Image.Image, printer_name: str):
        """Печатает изображение через GDI"""
        try:
            hdc = win32ui.CreateDC()
            hdc.CreatePrinterDC(printer_name)

            if not hdc:
                raise Exception(f"Не удалось создать контекст устройства для: {printer_name}")

            printer_dpi_x = hdc.GetDeviceCaps(88)
            printer_dpi_y = hdc.GetDeviceCaps(90)

            # Размер этикетки (пдф-формы)
            paper_width_mm = self.settings.get("paper_width_mm", 80)
            paper_height_mm = self.settings.get("paper_height_mm", 58)

            paper_width_pixels = int(paper_width_mm / 25.4 * printer_dpi_x)
            paper_height_pixels = int(paper_height_mm / 25.4 * printer_dpi_y)

            img_width, img_height = img.size

            scale_x = paper_width_pixels / img_width
            scale_y = paper_height_pixels / img_height
            scale = min(scale_x, scale_y)

            new_width = int(img_width * scale)
            new_height = int(img_height * scale)

            x_offset = (paper_width_pixels - new_width) // 2
            y_offset = (paper_height_pixels - new_height) // 2

            doc_name = "Label Print"
            hdc.StartDoc(doc_name)
            hdc.StartPage()

            from PIL import ImageWin
            dib = ImageWin.Dib(img)
            dib.draw(hdc.GetHandleOutput(), (x_offset, y_offset, x_offset + new_width, y_offset + new_height))

            hdc.EndPage()
            hdc.EndDoc()

        except Exception as e:
            raise Exception(f"Ошибка печати GDI: {str(e)}")
            
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
        
    def _validate_required_fields(self, field_vars):
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