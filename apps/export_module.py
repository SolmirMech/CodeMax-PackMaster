# apps/export_module.py
import tkinter as tk
from tkinter import ttk, StringVar
import os
from core.config_manager import ConfigManager
from core.excel_exporter import WeightOrdersExporter

class ExportModule:
    """Модуль управления экспортом в Excel"""
    
    def __init__(self, parent, preview_module, coordinator=None):
        self.parent = parent
        self.preview_module = preview_module
        self.coordinator = coordinator
        self.config_manager = ConfigManager()
        
        order_settings = self.config_manager.load_json_settings("shared_utils.json").get("order_number", {})
        self.order_prefix = StringVar(value=order_settings.get("prefix", "Ф"))
        self.order_suffix = StringVar(value=order_settings.get("suffix", "/5"))        
        
        # Переменные для коробки
        self.box_size_var = tk.StringVar(value="")
        self.box_weight_var = tk.StringVar(value="0.0")
        
        # Переменные для поддона
        self.pallet_weight_var = tk.StringVar(value="0.0")
        self.pallet_size_var = tk.StringVar(value="")
        self.boxes_count_var = tk.StringVar(value="1")
        
        # Переменные для пути Excel
        self.excel_file_path = None
        self.excel_folder_path = ""
        
        self.connected_roll_module = None
        self.order_data_module = None
        
        self.create_export_ui()
        if self.coordinator and hasattr(self.coordinator, 'subscribe'):
            self.coordinator.subscribe(self.on_settings_changed)        
        self.load_box_sizes()
        self.parent.after(100, self.on_box_selected)
        self.load_pallet_sizes()
        self.load_excel_folder_path()
    
    def create_export_ui(self):
        """Создает интерфейс управления экспортом"""
        frame = ttk.Frame(self.parent, padding=5)
        frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Основной фрейм управления
        control_frame = ttk.Frame(frame)
        control_frame.pack(fill=tk.BOTH, expand=True)
        
        # Секция экспорта коробки
        self.create_excel_section(control_frame)
        
        # Секция экспорта поддона
        self.create_pallet_section(control_frame)
        
        # Статус экспорта
        self.export_status_label = ttk.Label(
            control_frame,
            text="",
            foreground="red",
            wraplength=250,
            font=("Arial", 14)
        )
        self.export_status_label.pack(fill=tk.X, pady=10)
        
        self.parent.bind("<Visibility>", lambda e: self.update_comboboxes())
    
    def create_excel_section(self, parent):
        """Создает секцию экспорта коробки"""
        box_frame = ttk.LabelFrame(parent, text="Экспорт коробки", padding=10)
        box_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Конфигурация колонок
        box_frame.columnconfigure(0, weight=1)
        box_frame.columnconfigure(1, weight=1)
        
        # Комбобокс выбора коробки
        self.box_sizes_combo = ttk.Combobox(
            box_frame,
            textvariable=self.box_size_var,
            state="readonly",
            width=20
        )
        self.box_sizes_combo.grid(row=0, column=0, padx=(0, 5), pady=5, sticky="w")
        self.box_sizes_combo.bind("<<ComboboxSelected>>", self.on_box_selected)
        
        # Поле веса коробки
        self.box_weight_entry = ttk.Entry(box_frame, textvariable=self.box_weight_var, width=8)
        self.box_weight_entry.grid(row=0, column=1, padx=(5, 0), pady=5, sticky="w")
        
        # Кнопки управления Excel
        ttk.Button(box_frame, text="🎯 В Excel", 
                  command=self.export_to_excel
        ).grid(row=1, column=0, padx=(0, 5), pady=10, sticky="w")
        
        excel_menu = ttk.Menubutton(box_frame, text="🧹", width=3)
        excel_menu.grid(row=1, column=1, padx=(5, 0), pady=10, sticky="w")
        
        excel_menu.menu = tk.Menu(excel_menu, tearoff=0)
        excel_menu["menu"] = excel_menu.menu
        excel_menu.menu.add_command(
            label="Очистить коробку", 
            command=self.clear_excel_data
        )
        
        # Кнопка предпросмотра коробки
        btn_preview = ttk.Button(
            box_frame,
            text="👀 Просмотр",
            width=12,
            command=self.show_box_preview,
            style="Accent.TButton"
        )

        btn_preview.grid(row=2, column=0, pady=10, sticky="w")
    
    def create_pallet_section(self, parent):
        """Создает секцию экспорта поддона"""
        pallet_frame = ttk.LabelFrame(parent, text="Экспорт поддона", padding=10)
        pallet_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Конфигурация колонок
        pallet_frame.columnconfigure(0, weight=1)
        pallet_frame.columnconfigure(1, weight=1)
        
        # Выбор поддона и вес
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

        # Количество коробок
        ttk.Label(pallet_frame, text="Кол-во коробок:").grid(row=1, column=0, padx=(0, 5), pady=5, sticky="w")
        boxes_count_entry = ttk.Entry(pallet_frame, textvariable=self.boxes_count_var, width=8)
        boxes_count_entry.grid(row=1, column=1, padx=(5, 0), pady=5, sticky="w")

        # Кнопки управления Excel для поддона
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
        
        # Кнопка предпросмотра поддона
        ttk.Button(
            pallet_frame,
            text="👀 Просмотр",
            width=12,
            command=self.show_pallet_preview,
            style="Accent.TButton"
        ).grid(row=3, column=0, pady=(5, 0), sticky="w")
        
    def show_box_preview(self):
        """Открывает предпросмотр для коробки"""
        if not hasattr(self, 'excel_preview_module'):
            from apps.preview.excel_preview_module import ExcelPreviewModule
            self.excel_preview_module = ExcelPreviewModule(self.parent, self.coordinator)
        
        # Определяем текущий цех
        workshop = "1"
        if self.coordinator and hasattr(self.coordinator, 'get_workshop'):
            workshop = self.coordinator.get_workshop()
        
        # Устанавливаем контекст коробки перед открытием окна
        self.excel_preview_module.sheet_name = self.excel_preview_module._get_sheet_for_preview(
            workshop, enable_pallet=False, multitype_mode=False
        )
        
        # Обновляем заголовок окна если оно уже открыто
        if (hasattr(self.excel_preview_module, 'preview_window') and 
            self.excel_preview_module.preview_window is not None and 
            self.excel_preview_module.preview_window.winfo_exists()):
            
            self.excel_preview_module.preview_window.title(
                f"Предпросмотр Excel - {self.excel_preview_module.sheet_name}"
            )
            self.excel_preview_module.update_preview()
            self.excel_preview_module.preview_window.lift()
            self.excel_preview_module.preview_window.focus_force()
        else:
            # Открываем новое окно
            self.excel_preview_module.show_preview_window()
        
    def show_pallet_preview(self):
        """Открывает предпросмотр для поддона"""
        if not hasattr(self, 'excel_preview_module'):
            from apps.preview.excel_preview_module import ExcelPreviewModule
            self.excel_preview_module = ExcelPreviewModule(self.parent, self.coordinator)
        
        # Определяем текущий цех
        workshop = "1"
        if self.coordinator and hasattr(self.coordinator, 'get_workshop'):
            workshop = self.coordinator.get_workshop()
        
        # Устанавливаем контекст поддона перед открытием окна
        self.excel_preview_module.sheet_name = self.excel_preview_module._get_sheet_for_preview(
            workshop, enable_pallet=True, multitype_mode=False
        )
        
        # Обновляем заголовок окна если оно уже открыто
        if (hasattr(self.excel_preview_module, 'preview_window') and 
            self.excel_preview_module.preview_window is not None and 
            self.excel_preview_module.preview_window.winfo_exists()):
            
            self.excel_preview_module.preview_window.title(
                f"Предпросмотр Excel - {self.excel_preview_module.sheet_name}"
            )
            self.excel_preview_module.update_preview()
            self.excel_preview_module.preview_window.lift()
            self.excel_preview_module.preview_window.focus_force()
        else:
            # Открываем новое окно
            self.excel_preview_module.show_preview_window()
        
    def on_settings_changed(self):
        """Обработчик изменений настроек от координатора"""

    def set_status(self, message, color="green"):
        """Универсальный метод установки статуса"""
        if hasattr(self, 'export_status_label'):
            self.export_status_label.config(text=message, foreground=color)
        
    def set_order_data_module(self, order_data_module):
        self.order_data_module = order_data_module
        
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

    def update_comboboxes(self):
        """Обновляет все комбобоксы"""
        self.load_box_sizes()
        self.load_pallet_sizes()

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
        """Экспортирует данные в Excel"""
        try:
            # 1. Проверяем, что модуль ролика подключен
            if not self.connected_roll_module:
                self.export_status_label.config(text="Модуль ролика не подключен", foreground="red")
                return
                
            # 2. Проверяем, что все необходимые данные заполнены
            if not self.connected_roll_module.rolls_count_var.get() or not self.connected_roll_module.order_number.get():
                self.export_status_label.config(text="Введите количество роликов и номер заказа", foreground="red")
                return

            # 3. Проверяем путь к Excel файлу
            if not self.excel_file_path:
                self.load_excel_folder_path()
                
            if not self.excel_file_path:
                self.export_status_label.config(text="Папка для Excel не выбрана", foreground="red")
                return

            if not os.path.exists(self.excel_file_path):
                self.export_status_label.config(text="Файл Excel не существует", foreground="red")
                return

            # Создаем экспортер с координатором
            exporter = WeightOrdersExporter(
                excel_file_path=self.excel_file_path,
                roll_module=self.connected_roll_module,
                preview_module=self.preview_module,
                coordinator=self.coordinator
            )
            
            result = exporter.export_data(enable_pallet=False)
            
            if result['success']:
                all_fitted = result.get('all_fitted', True)
                if all_fitted:
                    self.set_status("Данные отправлены в коробку", "green")
                else:
                    self.set_status("Лист переполнен! Не все ролики поместились", "orange")
            else:
                error_msg = result.get('error', 'Неизвестная ошибка')
                self.export_status_label.config(text=f"Ошибка: {error_msg}", foreground="red")
                
        except Exception as e:
            self.export_status_label.config(text=f"Ошибка экспорта: {str(e)}", foreground="red")

    def clear_excel_data(self):
        """Очищает данные Excel"""
        try:
            # 1. Проверяем, что модуль ролика подключен
            if not self.connected_roll_module:
                self.export_status_label.config(text="Модуль ролика не подключен", foreground="red")
                return

            # 2. Проверяем путь к Excel файлу
            if not self.excel_file_path:
                self.load_excel_folder_path()
                
            if not self.excel_file_path:
                self.export_status_label.config(text="Папка для Excel не выбрана", foreground="red")
                return

            if not os.path.exists(self.excel_file_path):
                self.export_status_label.config(text="Файл Excel не существует", foreground="red")
                return

            # Создаем экспортер с координатором
            exporter = WeightOrdersExporter(
                excel_file_path=self.excel_file_path,
                roll_module=self.connected_roll_module,
                preview_module=self.preview_module,
                coordinator=self.coordinator
            )
            
            success = exporter.clear_all_rolls(enable_pallet=False)
            
            if success:
                self.export_status_label.config(text="Данные коробки очищены", foreground="green")
            else:
                self.export_status_label.config(text="Ошибка очистки коробки", foreground="red")
                
        except Exception as e:
            self.export_status_label.config(text=f"Ошибка очистки: {str(e)}", foreground="red")

    def export_pallet_to_excel(self):
        """Экспортирует данные поддона в Excel"""
        try:
            # Проверяем, что все необходимые данные заполнены
            if not self.pallet_size_var.get() or not self.boxes_count_var.get():
                self.export_status_label.config(
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
                self.export_status_label.config(text="Папка для Excel не выбрана", foreground="red")
                return

            if not os.path.exists(self.excel_file_path):
                self.export_status_label.config(text="Файл Excel не существует", foreground="red")
                return

            # Создаем экспортер и выполняем экспорт
            exporter = WeightOrdersExporter(
                excel_file_path=self.excel_file_path,
                roll_module=self.connected_roll_module,
                preview_module=self.preview_module,
                coordinator=self.coordinator
            )
            
            result = exporter.export_data(enable_pallet=True, pallet_data=pallet_data)
            
            if result['success']:
                # Проверяем поместились ли все коробки
                all_fitted = result.get('all_fitted', True)
                if all_fitted:
                    self.set_status("Данные поддона экспортированы", "green")
                else:
                    self.set_status("Лист переполнен!", "orange")
            else:
                self.set_status(f"Ошибка: {result.get('error')}", "red")  # Другие ошибки
    
        except Exception as e:
            self.export_status_label.config(
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
                self.export_status_label.config(text="Папка для Excel не выбрана", foreground="red")
                return

            if not os.path.exists(self.excel_file_path):
                self.export_status_label.config(text="Файл Excel не существует", foreground="red")
                return

            # Создаем экспортер и выполняем очистку
            exporter = WeightOrdersExporter(
                excel_file_path=self.excel_file_path,
                roll_module=self.connected_roll_module,
                preview_module=self.preview_module,
                coordinator=self.coordinator
            )
            
            success = exporter.clear_all_rolls(enable_pallet=True)
            
            if success:
                self.export_status_label.config(text="Данные поддона очищены", foreground="green")
            else:
                self.export_status_label.config(text="Ошибка при очистке данных", foreground="red")
            
        except Exception as e:
            self.export_status_label.config(text=f"Ошибка очистки: {str(e)}", foreground="red")
            
            