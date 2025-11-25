# apps/preview_export.py
import tkinter as tk
from tkinter import ttk, StringVar
import win32print
import win32ui
from PIL import Image, ImageTk
from core.printer_dia import SettingsDialog, CustomersEditorDialog, SpecialClientsEditorDialog
from core.config_manager import ConfigManager
from core.font_settings_dialog import FontSettingsDialog
from core.excel_exporter import WeightOrdersExporter
from apps.weight_orders_printer import WeightOrdersPrinter
from core.shared_utils import (
    mm_to_pixels,
    get_default_printer,
    create_printer_dc,
)
import os

class PreviewExport:
    """Модуль управления печатью и экспортом"""

    def __init__(self, parent, preview_module):
        self.parent = parent
        self.preview_module = preview_module  # ссылка на RollPreview
        self.config_manager = ConfigManager()
        self.settings_file = "print_settings.json"
        
        self.manufacturer = self.config_manager.get_manufacturer()

        self.default_settings = {
            "printer": get_default_printer(),
            "paper_width_mm": 80,
            "paper_height_mm": 58           
        }
        self.settings = self.default_settings.copy()
        self.load_settings("weight_box_print")
        
        order_settings = self.config_manager.load_json_settings("shared_utils.json").get("order_number", {})
        self.order_prefix = StringVar(value=order_settings.get("prefix", "Ф"))
        self.order_suffix = StringVar(value=order_settings.get("suffix", "/5"))        
        
        self.selected_preview = "roll"  # "roll" или "box"
        self.font_settings = None
        self.load_font_settings()
        self.weight_orders_window = None
        
        # Переменные для коробки
        self.box_size_var = tk.StringVar(value="")
        self.box_weight_var = tk.StringVar(value="0.0")
        # Переменные для поддона
        self.pallet_weight_var = tk.StringVar(value="0.0")
        self.pallet_size_var = tk.StringVar(value="")
        self.boxes_count_var = tk.StringVar(value="")
        # Переменные для пути Эксель
        self.excel_file_path = None
        self.excel_folder_path = ""
        # Переменная для копий
        self.copies_var = tk.StringVar(value="1")
        
        self.connected_roll_module = None
        
        # Переменные для печати тиража
        self.batch_print_data = []  # Список всех видов для печати
        self.current_batch_index = 0  # Текущий индекс печати
        self.is_batch_printing = False  # Флаг массовой печати
        
        self.create_export_ui()
        self.load_box_sizes()
        self.parent.after(100, self.on_box_selected)
        self.load_pallet_sizes()

    def load_box_sizes(self):
        """Загружает список коробок из shared_utils.json (ПЕРЕНЕСЕНО ИЗ ROLL_PREVIEW)"""
        try:
            settings = self.config_manager.load_json_settings("shared_utils.json")
            weight_box = settings.get("weight_box", {})
            box_sizes = list(weight_box.keys())
            
            if hasattr(self, 'box_sizes_combo') and self.box_sizes_combo:
                self.box_sizes_combo['values'] = box_sizes
                if box_sizes and not self.box_size_var.get():
                    self.box_size_var.set(box_sizes[0])
                    self.on_box_selected()
            
            return box_sizes
            
        except Exception as e:
            print(f"Ошибка загрузки списка коробок: {e}")
            return []
    
    def on_box_selected(self, event=None):
        """Обрабатывает выбор коробки"""
        selected_size = self.box_size_var.get()
        if selected_size:
            try:
                settings = self.config_manager.load_json_settings("shared_utils.json")
                weight_box = settings.get("weight_box", {})
                box_weight_g = weight_box.get(selected_size, 0)
                box_weight_kg = box_weight_g / 1000.0
                
                # Устанавливаем вес в поле ввода
                self.box_weight_var.set(f"{box_weight_kg:.2f}")
                
                if hasattr(self, 'connected_roll_module') and self.connected_roll_module:
                    # Обновляем размер коробки
                    if hasattr(self.connected_roll_module, 'box_size_var'):
                        self.connected_roll_module.box_size_var.set(selected_size)
                    
                    # Обновляем вес коробки
                    if hasattr(self.connected_roll_module, 'box_weight_var'):
                        self.connected_roll_module.box_weight_var.set(f"{box_weight_kg:.2f}")
                    
                    # Запускаем пересчет весов в ролике
                    if hasattr(self.connected_roll_module, 'calculate_box_weights'):
                        self.connected_roll_module.calculate_box_weights()
                    
            except Exception as e:
                print(f"Ошибка загрузки веса коробки: {e}")

    def create_export_ui(self):
        """Создает интерфейс управления печатью и экспортом"""
        frame = ttk.Frame(self.parent, padding=5)
        frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Основной фрейм управления - используем grid
        control_frame = ttk.Frame(frame)
        control_frame.grid(row=0, column=0, sticky="nsew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        # Кол-во копий - строка 0
        copies_frame = ttk.Frame(control_frame)
        copies_frame.grid(row=0, column=0, sticky="w", pady=(0, 5))
        ttk.Label(copies_frame, text="Копий:").pack(side=tk.LEFT, padx=(0, 5))
        copies_entry = ttk.Entry(
            copies_frame, 
            width=5,
            textvariable=self.copies_var,
            justify='center'
        )
        copies_entry.pack(side=tk.LEFT)
        copies_entry.bind('<FocusIn>', lambda e: copies_entry.select_range(0, tk.END))

        # Основной фрейм настроек
        settings_frame = ttk.Frame(control_frame)
        settings_frame.grid(row=1, column=0, sticky="w", pady=5, padx=5)

        # Печать - ряд 0
        ttk.Button(
            settings_frame, 
            text="🖨 Печать", 
            command=self.print_label
        ).grid(row=0, column=0, sticky="we", pady=5)

        # Иконки настроек - ряд 1
        ttk.Button(
            settings_frame, 
            text="🔤", 
            command=self.open_font_settings
        ).grid(row=1, column=0, sticky="w", pady=5)

        ttk.Button(
            settings_frame, 
            text="⚙", 
            command=self.open_settings
        ).grid(row=1, column=0, padx=(150, 5), sticky="w", pady=5)
        
        # Кнопка для открытия окна втулки
        ttk.Button(
            settings_frame, 
            text="✓ Ярлык на втулку", 
            command=self.open_weight_orders_window
        ).grid(row=2, column=0, sticky="we", pady=5)
        
        # Печать тиража
        ttk.Button(
            settings_frame, 
            text="📋 Печать тиража", 
            command=self.start_batch_print
        ).grid(row=3, column=0, sticky="we", pady=5, padx=(5, 0))

        # Настройка колонок для растягивания
        settings_frame.columnconfigure(0, weight=1)
        settings_frame.columnconfigure(1, weight=1)
        
        # Excel экспорт на коробку - строка 3
        self.create_excel_section(control_frame, row=2)
        
        # Excel экспорт на поддон - строка 4
        self.create_pallet_section(control_frame, row=3)

        # Статус экспорта - строка 5
        self.excel_status_label = ttk.Label(
            control_frame,
            text="",
            foreground="red",
            wraplength=250,
            font=("Arial", 14)
        )
        self.excel_status_label.grid(row=4, column=0, sticky="w", pady=5)
        
        self.parent.bind("<Visibility>", lambda e: self.update_comboboxes())
        
    def set_order_data_module(self, order_data_module):
        self.order_data_module = order_data_module
        
    def start_batch_print(self):
        """Запускает печать всего тиража из уже распарсенных данных"""
        try:
            # Берем список из order_data_processor через существующие связи
            if (hasattr(self, 'order_data_module') and self.order_data_module):
                names_list = getattr(self.order_data_module, 'parsed_names_list', [])
                
                if not names_list:
                    self.excel_status_label.config(text="Нет данных для печати", foreground="red")
                    return
                    
                # Сохраняем оригинальное название для восстановления
                self.original_product_name = self.preview_module.connected_roll_module.product_text.get("1.0", "end-1c")
                
                # Начинаем печать
                self.batch_print_data = names_list
                self.current_batch_index = 0
                self.is_batch_printing = True
                self.excel_status_label.config(text=f"Печать тиража ({len(names_list)} видов)...", foreground="blue")
                
                self.print_next_in_batch()
            else:
                self.excel_status_label.config(text="Модуль данных не подключен", foreground="red")
                
        except Exception as e:
            self.excel_status_label.config(text=f"Ошибка: {str(e)}", foreground="red")

    def print_next_in_batch(self):
        """Печатает следующий вид в тираже используя существующий метод print_label"""
        if not self.is_batch_printing or self.current_batch_index >= len(self.batch_print_data):
            # Завершение печати - восстанавливаем оригинальное название
            if hasattr(self, 'original_product_name'):
                self.preview_module.connected_roll_module.product_text.delete("1.0", tk.END)
                self.preview_module.connected_roll_module.product_text.insert("1.0", self.original_product_name)
            
            self.is_batch_printing = False
            self.excel_status_label.config(text=f"Печать завершена ({self.current_batch_index} шт)", foreground="green")
            return
            
        try:
            current_product_name = self.batch_print_data[self.current_batch_index]
            
            # Временно подменяем название продукции
            self.preview_module.connected_roll_module.product_text.delete("1.0", tk.END)
            self.preview_module.connected_roll_module.product_text.insert("1.0", current_product_name)
            
            # 🔥 ЖДЕМ обновления данных перед печатью
            self.parent.after(100, lambda: self.print_current_item(current_product_name))
            
        except Exception as e:
            self.excel_status_label.config(text=f"Ошибка печати вида {self.current_batch_index + 1}: {str(e)}", foreground="red")
            self.current_batch_index += 1
            self.parent.after(100, self.print_next_in_batch)

    def print_current_item(self, product_name):
        """Печатает текущий элемент после обновления данных"""
        try:
            # Теперь данные точно обновлены - печатаем
            self.print_label()
            
            # Статус
            product_name_short = product_name[:30] + "..." if len(product_name) > 30 else product_name
            self.excel_status_label.config(text=f"Печатается {self.current_batch_index + 1}/{len(self.batch_print_data)}: {product_name_short}", foreground="blue")
            
            # Следующий вид
            self.current_batch_index += 1
            self.parent.after(100, self.print_next_in_batch)
            
        except Exception as e:
            self.excel_status_label.config(text=f"Ошибка печати вида {self.current_batch_index + 1}: {str(e)}", foreground="red")
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
        
    def update_comboboxes(self):
        """Обновляет все комбобоксы"""
        self.load_box_sizes()
        self.load_pallet_sizes()
        
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
                messagebox.showinfo("Сохранено", "Настройки печати сохранены!")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить настройки:\n{str(e)}")            
        
    def open_settings(self):
        """Открывает единое окно настроек со всеми разделами"""
        dialog = SettingsDialog(self.parent, self)
        dialog.show()        
        
    def update_preview_displays(self):
        """Обновляет превью в preview_module (RollPreview)"""
        if hasattr(self, 'preview_module') and self.preview_module:
            self.preview_module.update_preview_displays()
        
    def load_excel_folder_path(self):
        """Загружает путь к папке с Excel файлом из настроек"""
        try:
            settings = self.config_manager.load_json_settings("shared_utils.json")
            folder_path = settings.get("weight_orders_xlsx", "")
            
            if folder_path and os.path.exists(folder_path):
                self.excel_folder_path = folder_path
                # Формируем полный путь к файлу
                self.excel_file_path = os.path.join(folder_path, "weight_orders.xlsx")
            else:
                self.excel_folder_path = ""
                self.excel_file_path = ""
                
        except Exception as e:
            print(f"Ошибка загрузки пути к папке Excel: {e}")
            self.excel_folder_path = ""
            self.excel_file_path = ""

    def export_to_excel(self):
        """Экспортирует данные в Excel через подключенный модуль ролика"""
        try:
            result = self.call_roll_module_method('export_box_to_excel')
            if result and result.get('success'):
                self.excel_status_label.config(text="Данные отправлены в коробку", foreground="green")
            else:
                error_msg = result.get('error', 'Неизвестная ошибка') if result else 'Ошибка экспорта'
                self.excel_status_label.config(text=f"Ошибка: {error_msg}", foreground="red")
        except Exception as e:
            self.excel_status_label.config(text=f"Ошибка экспорта: {str(e)}", foreground="red")

    def clear_excel_data(self):
        """Очищает данные Excel через подключенный модуль ролика"""
        try:
            success = self.call_roll_module_method('clear_box_excel_data')
            if success:
                self.excel_status_label.config(text="Данные коробки очищены", foreground="green")
            else:
                self.excel_status_label.config(text="Ошибка очистки коробки", foreground="red")
        except Exception as e:
            self.excel_status_label.config(text=f"Ошибка очистки: {str(e)}", foreground="red")

    def export_pallet_to_excel(self):
        """Экспортирует данные поддона в Excel"""
        try:
            # Проверяем, что все необходимые данные заполнены
            if not self.pallet_size_var.get() or not self.boxes_count_var.get():
                self.excel_status_label.config(
                    text="Введите данные для экспорта!", 
                    foreground="orange"
                )
                return

            # Получаем данные для экспорта
            pallet_data = {
                "pallet_type": self.pallet_size_var.get(),
                "pallet_weight": self.pallet_weight_var.get(),
                "boxes_count": self.boxes_count_var.get()
            }

            # Используем excel_file_path
            if not self.excel_file_path:
                self.load_excel_folder_path()
                
            if not self.excel_file_path:
                self.excel_status_label.config(text="Папка для Excel не выбрана", foreground="red")
                return

            if not os.path.exists(self.excel_file_path):
                self.excel_status_label.config(text="Файл Excel не существует", foreground="red")
                return

            # Создаем экспортер и выполняем экспорт
            exporter = WeightOrdersExporter(
                excel_file_path=self.excel_file_path,
                roll_module=self.connected_roll_module,
                preview_module=self
            )
            
            result = exporter.export_data(enable_pallet=True, pallet_data=pallet_data)
            
            if result['success']:
                # Проверяем поместились ли все коробки
                all_fitted = result.get('all_fitted', True)
                if all_fitted:
                    self.excel_status_label.config(
                        text="Данные поддона экспортированы", 
                        foreground="green"
                    )
                else:
                    self.excel_status_label.config(
                        text="Лист переполнен!", 
                        foreground="orange"
                    )
            else:
                self.excel_status_label.config(
                    text="Ошибка при экспорте данных", 
                    foreground="red"
                )
            
        except Exception as e:
            self.excel_status_label.config(
                text=f"Ошибка экспорта: {str(e)}", 
                foreground="red"
            )
            
    def clear_pallet_excel(self):
        """Очищает данные поддона в Excel"""
        try:

            # Используем excel_file_path
            if not self.excel_file_path:
                self.load_excel_folder_path()
                
            if not self.excel_file_path:
                self.excel_status_label.config(text="Папка для Excel не выбрана", foreground="red")
                return

            if not os.path.exists(self.excel_file_path):
                self.excel_status_label.config(text="Файл Excel не существует", foreground="red")
                return

            # Создаем экспортер и выполняем очистку
            exporter = WeightOrdersExporter(
                excel_file_path=self.excel_file_path,
                roll_module=self.connected_roll_module,
                preview_module=self
            )
            
            success = exporter.clear_all_rolls(enable_pallet=True)
            
            if success:
                self.excel_status_label.config(text="Данные поддона очищены", foreground="green")
            else:
                self.excel_status_label.config(text="Ошибка при очистке данных", foreground="red")
            
        except Exception as e:
            self.excel_status_label.config(text=f"Ошибка очистки: {str(e)}", foreground="red")        
        
    def load_pallet_sizes(self):
        """Загружает список поддонов из shared_utils.json"""
        try:
            settings = self.config_manager.load_json_settings("shared_utils.json")
            weight_box = settings.get("weight_box", {})
            pallet_sizes = list(weight_box.keys())
            
            # Проверяем, что комбобокс уже создан
            if hasattr(self, 'pallet_sizes_combo'):
                self.pallet_sizes_combo['values'] = pallet_sizes
                if pallet_sizes:
                    self.pallet_size_var.set(pallet_sizes[0])
                    self.on_pallet_selected()
        except Exception as e:
            print(f"Ошибка загрузки списка поддонов: {e}")
            
    def on_pallet_selected(self, event=None):
        """Обрабатывает выбор поддона из списка"""
        selected_size = self.pallet_size_var.get()
        if selected_size:
            try:
                settings = self.config_manager.load_json_settings("shared_utils.json")
                weight_box = settings.get("weight_box", {})
                pallet_weight_g = weight_box.get(selected_size, 0)
                pallet_weight_kg = pallet_weight_g / 1000.0
                self.pallet_weight_var.set(f"{pallet_weight_kg:.0f}")
            except Exception as e:
                print(f"Ошибка загрузки веса поддона: {e}")        
        
    def create_pallet_section(self, parent, row):
        """Создает секцию Упак.лист на поддон"""
        pallet_frame = ttk.LabelFrame(parent, text="Экспорт поддона", padding=10)
        pallet_frame.grid(row=row, column=0, columnspan=2, sticky="w", pady=(10, 5))
        
        # Конфигурация колонок для равномерного распределения
        pallet_frame.columnconfigure(0, weight=1)
        pallet_frame.columnconfigure(1, weight=1)
        
        # Выбор поддона и вес - строка 0
        self.pallet_sizes_combo = ttk.Combobox(
            pallet_frame,
            textvariable=self.pallet_size_var,
            state="readonly",
            width=20
        )
        self.pallet_sizes_combo.grid(row=0, column=0, padx=(0, 5), pady=5, sticky="w")
        self.pallet_sizes_combo.bind("<<ComboboxSelected>>", self.on_pallet_selected)

        pallet_weight_entry = ttk.Entry(pallet_frame, textvariable=self.pallet_weight_var, 
                                       width=8)
        pallet_weight_entry.grid(row=0, column=1, padx=(5, 0), pady=5, sticky="w")

        # Количество коробок - строка 1
        ttk.Label(pallet_frame, text="Кол-во коробок:").grid(row=1, column=0, padx=(0, 5), pady=5, sticky="w")
        boxes_count_entry = ttk.Entry(pallet_frame, textvariable=self.boxes_count_var, width=8)
        boxes_count_entry.grid(row=1, column=1, padx=(5, 0), pady=5, sticky="w")

        # Кнопки управления Excel для поддона - строка 2
        ttk.Button(pallet_frame, text="🎯 В Excel", 
                  command=self.export_pallet_to_excel
        ).grid(row=2, column=0, padx=(0, 5), pady=10, sticky="w")
        
        pallet_menu = ttk.Menubutton(pallet_frame, text="🧹", width=3)
        pallet_menu.grid(row=2, column=1, padx=(5, 0), pady=10, sticky="w")
        
        pallet_menu.menu = tk.Menu(pallet_menu, tearoff=0)
        pallet_menu["menu"] = pallet_menu.menu
        pallet_menu.menu.add_command(
            label="Очистить поддон", 
            command=self.clear_pallet_excel
        )

        # Загружаем список поддонов
        self.load_pallet_sizes()

    def create_excel_section(self, parent, row):
        """Создает секцию Excel экспорта"""
        box_frame = ttk.LabelFrame(parent, text="Экспорт коробки", padding=10)
        box_frame.grid(row=row, column=0, pady=(10, 5), sticky="w")
        
        # Конфигурация колонок
        box_frame.columnconfigure(0, weight=1)
        box_frame.columnconfigure(1, weight=1)
        
        # Комбобокс выбора коробки - строка 0
        self.box_sizes_combo = ttk.Combobox(
            box_frame,
            textvariable=self.box_size_var,
            state="readonly",
            width=20
        )
        self.box_sizes_combo.grid(row=0, column=0, padx=(0, 5), pady=5, sticky="w")
        self.box_sizes_combo.bind("<<ComboboxSelected>>", self.on_box_selected)
        
        # Поле веса коробки - строка 0, колонка 1
        self.box_weight_entry = ttk.Entry(box_frame, textvariable=self.box_weight_var, width=8)
        self.box_weight_entry.grid(row=0, column=1, padx=(13, 0), pady=5, sticky="w")
        
        # Кнопки управления Excel - строка 2
        ttk.Button(box_frame, text="🎯 В Excel", 
                  command=self.export_to_excel
        ).grid(row=1, column=0, padx=(0, 5), pady=10, sticky="w")
        
        # Меню для очистки - строка 2, колонка 1
        excel_menu = ttk.Menubutton(box_frame, text="🧹", width=3)
        excel_menu.grid(row=1, column=1, padx=(13, 0), pady=10, sticky="w")
        
        excel_menu.menu = tk.Menu(excel_menu, tearoff=0)
        excel_menu["menu"] = excel_menu.menu
        excel_menu.menu.add_command(
            label="Очистить коробку", 
            command=self.clear_excel_data
        )

        # Загружаем список коробок
        self.load_box_sizes()

    def load_box_sizes(self):
        """Загружает список коробок из shared_utils.json"""
        try:
            settings = self.config_manager.load_json_settings("shared_utils.json")
            weight_box = settings.get("weight_box", {})
            box_sizes = list(weight_box.keys())
            
            if hasattr(self, 'box_sizes_combo') and self.box_sizes_combo:
                self.box_sizes_combo['values'] = box_sizes
                if box_sizes and not self.box_size_var.get():
                    self.box_size_var.set(box_sizes[0])
                    self.on_box_selected()
            
            return box_sizes
            
        except Exception as e:
            print(f"Ошибка загрузки списка коробок: {e}")
            return []

    def on_box_selected(self, event=None):
        """Обрабатывает выбор коробки"""
        selected_size = self.box_size_var.get()
        if selected_size:
            try:
                settings = self.config_manager.load_json_settings("shared_utils.json")
                weight_box = settings.get("weight_box", {})
                box_weight_g = weight_box.get(selected_size, 0)
                box_weight_kg = box_weight_g / 1000.0
                
                # Устанавливаем вес в поле ввода
                self.box_weight_var.set(f"{box_weight_kg:.2f}")
                
                if hasattr(self, 'connected_roll_module') and self.connected_roll_module:
                    # Обновляем размер коробки
                    if hasattr(self.connected_roll_module, 'box_size_var'):
                        self.connected_roll_module.box_size_var.set(selected_size)
                    
                    # Обновляем вес коробки
                    if hasattr(self.connected_roll_module, 'box_weight_var'):
                        self.connected_roll_module.box_weight_var.set(f"{box_weight_kg:.2f}")
                    
                    # Запускаем пересчет весов в ролике
                    if hasattr(self.connected_roll_module, 'calculate_box_weights'):
                        self.connected_roll_module.calculate_box_weights()
                    
            except Exception as e:
                print(f"Ошибка загрузки веса коробки: {e}")
        
    def load_font_settings(self):
        """Загружает настройки шрифтов"""
        # Пытаемся загрузить из файла
        loaded_settings = self.config_manager.load_json_settings("label_font_settings.json")
        
        if loaded_settings:
            self.font_settings = loaded_settings
        else:
            # Используем настройки по умолчанию из FontSettingsDialog
            self.font_settings = FontSettingsDialog.get_default_font_settings()
        
    def open_font_settings(self):
        """Открывает окно настроек шрифтов"""
        FontSettingsDialog(self.parent, self.config_manager, self)
        
    def print_label(self):
        """Печатает выбранную этикетку"""
        try:
            copies_text = self.copies_var.get().strip()
            if not copies_text:
                copies = 1
            else:
                copies = int(copies_text)
                
            if copies < 1:
                copies = 1
            
            printer_name = self._find_printer()
            if not printer_name:
                # Используем status_label из preview_module
                self.preview_module.status_label.config(text="Принтер не найден!", foreground="red")
                return
            
            # ИСПОЛЬЗУЕМ preview_module для получения данных и PDF фильлеров
            if self.selected_preview == "roll":
                data_map = self.preview_module._prepare_roll_data_map()
                print_image = self.preview_module.roll_pdf_filler.generate_print_image(data_map)
                label_type = "ролика"
            else:
                data_map = self.preview_module._prepare_box_data_map()
                print_image = self.preview_module.box_pdf_filler.generate_print_image(data_map)
                label_type = "коробки"
            
            # Печатаем указанное количество копий
            for i in range(copies):
                self._print_image_gdi(print_image, printer_name)
            
            self.preview_module.status_label.config(text=f"Печать {label_type} отправлена ({copies} шт)", foreground="green")
            
        except Exception as e:
            self.preview_module.status_label.config(text=f"Ошибка печати: {e}", foreground="red")
            
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

    def update_font_settings(self, new_settings):
        """Обновляет настройки шрифтов в preview_module"""
        self.font_settings = new_settings
        self.preview_module.update_font_settings(new_settings)            