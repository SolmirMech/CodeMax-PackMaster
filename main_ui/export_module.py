import tkinter as tk
from tkinter import ttk, StringVar
import os
from core.excel_exporter.legacy_adapter import LegacyExporterAdapter as WeightOrdersExporter


# noinspection PyUnusedLocal,PyTypeChecker, SpellCheckingInspection
class ExportModule:
    """Модуль управления экспортом в Excel"""
    
    def __init__(self, parent, preview_module, coordinator=None, config_manager=None):
        self.multitype_frame = None
        self.excel_preview_module = None
        self.pallet_num_entry = None
        self.pallet_label = None
        self.pallet_sizes_combo = None
        self.box_sizes_combo = None
        self.export_status_label = None
        self.parent = parent
        self.preview_module = preview_module
        self.coordinator = coordinator
        self.config_manager = config_manager
        
        order_settings = self.config_manager.load_json_settings("shared_utils.json").get("order_number", {})
        self.order_prefix = StringVar(value=order_settings.get("prefix", "Ф"))
        self.order_suffix = StringVar(value=order_settings.get("suffix", "/5"))        
        
        # Переменные для коробки
        self.box_size_var = tk.StringVar(value="")
        self.box_weight_var = tk.StringVar(value="0.0")
        
        # Переменные для поддона
        self.pallet_size_var = tk.StringVar(value="")
        self.pallet_weight_var = tk.StringVar(value="0.0")        
        self.boxes_count_var = tk.StringVar(value="1")
        self.pallet_num_var = tk.StringVar(value="1")
        
        # Переменные для пути Excel
        self.excel_file_path = None
        self.excel_folder_path = ""
        
        self.connected_roll_module = None
        self.order_data_module = None
        
        self.box_frame = None
        self.pallet_frame = None
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
        
        # ===== Экспорт в Лист Много видов =====
        self.create_multitype_section(control_frame)
        
        # Статус экспорта
        self.export_status_label = ttk.Label(
            control_frame,
            text="",
            foreground="red",
            wraplength=330,
            font=("Arial", 14)
        )
        self.export_status_label.pack(fill=tk.X, pady=10)
        
        # Инициализируем названия разделов
        self._update_section_titles()
    
    def create_excel_section(self, parent):
        """Создает секцию экспорта коробки"""
        self.box_frame = ttk.LabelFrame(parent, text="", padding=10)
        self.box_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Конфигурация колонок
        self.box_frame.columnconfigure(0, weight=1)
        self.box_frame.columnconfigure(1, weight=1)
        
        # Комбобокс выбора коробки
        ttk.Label(self.box_frame, text="Вес коробки:").grid(row=0, column=0, padx=(0, 5), pady=5, sticky="w")        
        self.box_sizes_combo = ttk.Combobox(
            self.box_frame,
            textvariable=self.box_size_var,
            state="readonly",
            width=20
        )
        self.box_sizes_combo.grid(row=0, column=1, padx=(5, 0), pady=5, sticky="w")
        self.box_sizes_combo.bind("<<ComboboxSelected>>", self.on_box_selected)     
        
        # Кнопки управления Excel
        ttk.Button(self.box_frame, text="🎯 В Excel", 
                  command=self.export_to_excel
        ).grid(row=1, column=0, padx=(0, 5), pady=5, sticky="w")
        
        excel_menu = ttk.Menubutton(self.box_frame, text="🧹", width=3)
        excel_menu.grid(row=1, column=1, padx=(5, 0), pady=5, sticky="w")
        
        excel_menu.menu = tk.Menu(excel_menu, tearoff=0)
        excel_menu["menu"] = excel_menu.menu
        excel_menu.menu.add_command(
            label="Очистить лист коробки", 
            command=self.clear_excel_data
        )
        
        # Кнопка предпросмотра коробки
        btn_preview = ttk.Button(
            self.box_frame,
            text="👀 Просмотр листа",
            width=18,
            command=self.show_box_preview,
            style="Accent.TButton"
        )

        btn_preview.grid(row=2, column=0, pady=5, sticky="w", columnspan=2)
    
    def create_pallet_section(self, parent):
        """Создает секцию экспорта поддона"""
        self.pallet_frame = ttk.LabelFrame(parent, text="", padding=10)
        self.pallet_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Конфигурация колонок
        self.pallet_frame.columnconfigure(0, weight=1)
        self.pallet_frame.columnconfigure(1, weight=1)
        
        # Выбор поддона и вес
        ttk.Label(self.pallet_frame, text="Вес поддона:").grid(row=0, column=0, padx=(0, 5), pady=5, sticky="w")        
        self.pallet_sizes_combo = ttk.Combobox(
            self.pallet_frame,
            textvariable=self.pallet_size_var,
            state="readonly",
            width=20
        )
        self.pallet_sizes_combo.grid(row=0, column=1, padx=(0, 5), pady=5, sticky="w")
        self.pallet_sizes_combo.bind("<<ComboboxSelected>>", self.on_pallet_selected)

        # Количество коробок
        ttk.Label(self.pallet_frame, text="Кол-во коробок:").grid(row=1, column=0, padx=(0, 5), pady=5, sticky="w")
        boxes_count_entry = ttk.Entry(self.pallet_frame, textvariable=self.boxes_count_var, width=8)
        boxes_count_entry.grid(row=1, column=1, padx=(5, 0), pady=5, sticky="w")
        
        # Номер поддона
        self.pallet_label = ttk.Label(self.pallet_frame, text="№ поддона:")
        self.pallet_label.grid(row=2, column=0, padx=(0, 5), pady=5, sticky="w")
        pallet_num_entry = ttk.Entry(self.pallet_frame, textvariable=self.pallet_num_var, width=8)
        pallet_num_entry.grid(row=2, column=1, padx=(5, 0), pady=5, sticky="w")
        self.pallet_num_entry = pallet_num_entry

        # Кнопки управления Excel для поддона
        ttk.Button(self.pallet_frame, text="🎯 В Excel", 
                  command=self.export_pallet_to_excel
        ).grid(row=3, column=0, padx=(0, 5), pady=5, sticky="w")
        
        pallet_menu = ttk.Menubutton(self.pallet_frame, text="🧹", width=3)
        pallet_menu.grid(row=3, column=1, padx=(5, 0), pady=5, sticky="w")
        
        pallet_menu.menu = tk.Menu(pallet_menu, tearoff=0)
        pallet_menu["menu"] = pallet_menu.menu
        pallet_menu.menu.add_command(
            label="Очистить лист поддона", 
            command=self.clear_pallet_excel
        )
        
        # Кнопка предпросмотра поддона
        ttk.Button(
            self.pallet_frame,
            text="👀 Просмотр листа",
            width=18,
            command=self.show_pallet_preview,
            style="Accent.TButton"
        ).grid(row=4, column=0, pady=(5, 0), sticky="w", columnspan=2)
        
    def create_multitype_section(self, parent):
        """Создает секцию экспорта в Лист Много видов"""
        multitype_frame = ttk.LabelFrame(parent, text="Упак.лист Много видов", padding=10)
        multitype_frame.pack(fill=tk.X, pady=(0, 10))
        self.multitype_frame = multitype_frame
        
        # Конфигурация колонок
        multitype_frame.columnconfigure(0, weight=1)
        multitype_frame.columnconfigure(1, weight=1)
        
        # Кнопки управления Excel для много видов
        ttk.Button(multitype_frame, text="🎯 В Excel", 
                  command=self.export_to_multitype_sheet
        ).grid(row=0, column=0, padx=(0, 5), pady=5, sticky="w")
        
        multitype_menu = ttk.Menubutton(multitype_frame, text="🧹", width=3)
        multitype_menu.grid(row=0, column=0, padx=(180, 0), pady=5, sticky="w")
        
        multitype_menu.menu = tk.Menu(multitype_menu, tearoff=0)
        multitype_menu["menu"] = multitype_menu.menu
        multitype_menu.menu.add_command(
            label="Очистить Лист 'Много видов'", 
            command=self.clear_multitype_sheet
        )
        
        # Кнопка предпросмотра листа 'Много видов'
        ttk.Button(
            multitype_frame,
            text="👀 Просмотр листа",
            command=self.show_multitype_preview,
            width=18,
            style="Accent.TButton"
        ).grid(row=1, column=0, pady=(5, 0), sticky="w", columnspan=2)

    def _update_section_titles(self):
        """Обновляет названия разделов в зависимости от цеха и наличия веса"""
        workshop = self.coordinator.get_workshop()

        # Проверяем статус веса через координатор
        has_weight = False
        if hasattr(self.coordinator, 'get_weight_status'):
            has_weight = self.coordinator.get_weight_status()

        if workshop == "1":
            if has_weight:
                box_title = "Упак.лист на коробку"
                pallet_title = "Упак.лист на поддон"
                multitype_title = "Упак.лист Много видов"
            else:
                box_title = "Упак.лист ПоддонРолики"
                pallet_title = "Упак.лист поддон БезВеса"
                multitype_title = "Упак.лист Много видов (без веса)"
        else:  # цех 2
            box_title = "Упак.лист на поддон"
            pallet_title = "Упак.лист Список поддонов"
            multitype_title = "Упак.лист Много видов"

        # Обновляем текст напрямую
        if hasattr(self, 'box_frame'):
            self.box_frame.config(text=box_title)
        if hasattr(self, 'pallet_frame'):
            self.pallet_frame.config(text=pallet_title)
        if hasattr(self, 'multitype_frame'):
            self.multitype_frame.config(text=multitype_title)

    def show_multitype_preview(self):
        """Открывает предпросмотр для листа 'Много видов'"""
        if self.excel_preview_module is None:
            from main_ui.preview.excel_preview_module import ExcelPreviewModule
            self.excel_preview_module = ExcelPreviewModule(
                self.parent, 
                self.coordinator,
                config_manager=self.config_manager
            )
        
        # Определяем текущий цех
        workshop = "1"
        if self.coordinator and hasattr(self.coordinator, 'get_workshop'):
            workshop = self.coordinator.get_workshop()
        
        # Устанавливаем контекст многовидового режима
        self.excel_preview_module.sheet_name = self.excel_preview_module.get_sheet_for_preview(
            workshop, enable_pallet=False, multitype_mode=True
        )
        
        # Обновляем заголовок окна если оно уже открыто
        if (self.excel_preview_module is not None and
                hasattr(self.excel_preview_module, 'preview_window') and
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

    def export_to_multitype_sheet(self):
        """Экспортирует текущий вид продукции в лист много видов"""
        try:
            # Получаем название продукции из roll_module
            if not self.connected_roll_module:
                self.set_status("Модуль ролика не подключен", "red")
                return
            
            product_name = self.connected_roll_module.product_text.get("1.0", "end-1c").strip()
            
            if not product_name:
                self.set_status("Сначала введите название продукции", "orange")
                return
            
            # Используем excel_file_path
            if not self.excel_file_path:
                self.load_excel_folder_path()
                
            if not self.excel_file_path:
                self.set_status("Папка для Excel не выбрана", "red")
                return

            if not os.path.exists(self.excel_file_path):
                self.set_status("Файл Excel не существует", "red")
                return

            # Создаем экспортер и выполняем экспорт в много-видовой лист
            exporter = WeightOrdersExporter.create_exporter(
                excel_file_path=self.excel_file_path,
                roll_module=self.connected_roll_module,
                preview_module=self.preview_module,
                coordinator=self.coordinator
            )
            
            result = exporter.export_data(multitype_mode=True)
            
            if result['success']:
                self.set_status("✅ Вид отправлен в лист 'Много видов'", "green")
            else:
                # Обработка ошибок из экспортера
                error_msg = result.get('error', '')
                self._handle_multitype_export_error(error_msg)
                    
        except Exception as e:
            # Обработка исключений при экспорте
            self._handle_multitype_export_error(str(e))
    
    def _handle_multitype_export_error(self, error_msg):
        """Обрабатывает ошибки экспорта в Лист Много видов"""
        # Проверяем разные варианты ошибок открытого файла
        if any(word in error_msg.lower() for word in ['permission', 'доступ', 'открыт', 'open', 'denied']):
            self.set_status("Внимание, закройте файл Excel перед экспортом!", "red")
        else:
            self.set_status(f"❌ Ошибка: {error_msg}", "red")
    
    def clear_multitype_sheet(self):
        """Очищает лист 'Много видов' в Excel"""
        try:
            # Используем excel_file_path
            if not self.excel_file_path:
                self.load_excel_folder_path()
                
            if not self.excel_file_path:
                self.set_status("Папка для Excel не выбрана", "red")
                return

            if not os.path.exists(self.excel_file_path):
                self.set_status("Файл Excel не существует", "red")
                return

            # Создаем экспортер и выполняем очистку
            exporter = WeightOrdersExporter.create_exporter(
                excel_file_path=self.excel_file_path,
                roll_module=self.connected_roll_module,
                preview_module=self.preview_module,
                coordinator=self.coordinator
            )
            
            success = exporter.clear_all_rolls(multitype_mode=True)
            
            if success:
                self.set_status("Лист 'Много видов' очищен", "green")
            else:
                self.set_status("Ошибка при очистке листа", "red")
            
        except Exception as e:
            self.set_status(f"Ошибка очистки: {str(e)}", "red")        
        
    def show_box_preview(self):
        """Открывает предпросмотр для коробки"""
        if self.excel_preview_module is None:
            from main_ui.preview.excel_preview_module import ExcelPreviewModule
            self.excel_preview_module = ExcelPreviewModule(
                self.parent, 
                self.coordinator,
                config_manager=self.config_manager
            )
        
        # Определяем текущий цех
        workshop = "1"
        if self.coordinator and hasattr(self.coordinator, 'get_workshop'):
            workshop = self.coordinator.get_workshop()
        
        # Устанавливаем контекст коробки перед открытием окна
        self.excel_preview_module.sheet_name = self.excel_preview_module.get_sheet_for_preview(
            workshop, enable_pallet=False, multitype_mode=False
        )
        
        # Обновляем заголовок окна если оно уже открыто
        if (self.excel_preview_module is not None and
                hasattr(self.excel_preview_module, 'preview_window') and
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
        if self.excel_preview_module is None:
            from main_ui.preview.excel_preview_module import ExcelPreviewModule
            self.excel_preview_module = ExcelPreviewModule(
                self.parent, 
                self.coordinator,
                config_manager=self.config_manager
            )
        
        # Определяем текущий цех
        workshop = "1"
        if self.coordinator and hasattr(self.coordinator, 'get_workshop'):
            workshop = self.coordinator.get_workshop()
        
        # Устанавливаем контекст поддона перед открытием окна
        self.excel_preview_module.sheet_name = self.excel_preview_module.get_sheet_for_preview(
            workshop, enable_pallet=True, multitype_mode=False
        )
        
        # Обновляем заголовок окна если оно уже открыто
        if (self.excel_preview_module is not None and
                hasattr(self.excel_preview_module, 'preview_window') and
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

    # noinspection PyUnusedLocal
    def on_settings_changed(self, context=None):
        """Обработчик изменений настроек от координатора"""
        self.load_box_sizes()
        self.load_pallet_sizes()
        self._update_number_visibility()
        self._update_section_titles()
        
    def _update_number_visibility(self):
        """Показывает/скрывает номер поддона в зависимости от цеха"""
        workshop = self.coordinator.get_workshop()
        
        # Управление видимостью
        if self.pallet_label is not None and self.pallet_num_entry is not None:
            if workshop == "1":
                self.pallet_label.grid_remove()
                self.pallet_num_entry.grid_remove()
            else:  # цех 2
                self.pallet_label.grid()
                self.pallet_num_entry.grid()
                      

    def set_status(self, message, color="green"):
        """Универсальный метод установки статуса"""
        self.export_status_label.config(text=message, foreground=color)
        self.parent.after(5000, lambda: self.export_status_label.config(text=""))
        
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

    def load_box_sizes(self):
        """Загружает список коробок из shared_utils.json"""
        try:
            settings = self.config_manager.load_json_settings("shared_utils.json")
            weight_box = settings.get("weight_box", {})
            box_sizes = list(weight_box.keys())
            
            if self.box_sizes_combo is not None:
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
            weight_pallet = settings.get("weight_pallet", {})
            pallet_sizes = list(weight_pallet.keys())
            
            # Проверяем, что комбобокс уже создан
            if self.pallet_sizes_combo is not None:
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
                weight_pallet = settings.get("weight_pallet", {})
                pallet_weight_g = weight_pallet.get(selected_size, 0)
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
            # Проверяем, что все необходимые данные заполнены
            if not self.connected_roll_module.rolls_count_var.get() or not self.connected_roll_module.order_number.get():
                self.set_status("Введите количество роликов и номер заказа", "red")
                return

            # Проверяем путь к Excel файлу
            if not self.excel_file_path:
                self.load_excel_folder_path()
                
            if not self.excel_file_path:
                self.set_status("Папка для Excel не выбрана", "red")
                return

            if not os.path.exists(self.excel_file_path):
                self.set_status("Файл Excel не существует", "red")
                return

            # Создаем экспортер с координатором
            exporter = WeightOrdersExporter.create_exporter(
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
                self.set_status(f"Ошибка: {error_msg}", "red")
                
        except Exception as e:
            self.set_status(f"Ошибка экспорта: {str(e)}", "red")

    def clear_excel_data(self):
        """Очищает данные Excel"""
        try:
            # Проверяем путь к Excel файлу
            if not self.excel_file_path:
                self.load_excel_folder_path()
                
            if not self.excel_file_path:
                self.set_status("Папка для Excel не выбрана", "red")
                return

            if not os.path.exists(self.excel_file_path):
                self.set_status("Файл Excel не существует", "red")
                return

            # Создаем экспортер с координатором
            exporter = WeightOrdersExporter.create_exporter(
                excel_file_path=self.excel_file_path,
                roll_module=self.connected_roll_module,
                preview_module=self.preview_module,
                coordinator=self.coordinator
            )
            
            success = exporter.clear_all_rolls(enable_pallet=False)
            
            if success:
                self.set_status("Данные коробки очищены", "green")
            else:
                self.set_status("Ошибка очистки коробки", "red")
                
        except Exception as e:
            self.set_status(f"Ошибка очистки: {str(e)}", "red")

    def export_pallet_to_excel(self):
        """Экспортирует данные поддона в Excel"""
        try:
            # Проверяем, что все необходимые данные заполнены
            if not self.pallet_size_var.get() or not self.boxes_count_var.get():
                self.set_status("Введите данные для экспорта!", "orange")
                return

            # Используем excel_file_path
            if not self.excel_file_path:
                self.load_excel_folder_path()
                
            if not self.excel_file_path:
                self.set_status("Папка для Excel не выбрана", "red")
                return

            if not os.path.exists(self.excel_file_path):
                self.set_status("Файл Excel не существует", "red")
                return

            # Создаем экспортер и выполняем экспорт
            exporter = WeightOrdersExporter.create_exporter(
                excel_file_path=self.excel_file_path,
                roll_module=self.connected_roll_module,
                preview_module=self.preview_module,
                coordinator=self.coordinator
            )
            
            result = exporter.export_data(enable_pallet=True)
            
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
            self.set_status(f"Ошибка экспорта: {str(e)}", "red")
            
    def clear_pallet_excel(self):
        """Очищает данные поддона в Excel"""
        try:

            # Используем excel_file_path
            if not self.excel_file_path:
                self.load_excel_folder_path()
                
            if not self.excel_file_path:
                self.set_status("Папка для Excel не выбрана", "red")
                return

            if not os.path.exists(self.excel_file_path):
                self.set_status("Файл Excel не существует", "red")
                return

            # Создаем экспортер и выполняем очистку
            exporter = WeightOrdersExporter.create_exporter(
                excel_file_path=self.excel_file_path,
                roll_module=self.connected_roll_module,
                preview_module=self.preview_module,
                coordinator=self.coordinator
            )
            
            success = exporter.clear_all_rolls(enable_pallet=True)
            
            if success:
                self.set_status("Данные поддона очищены", "green")
            else:
                self.set_status("Ошибка при очистке данных", "red")
            
        except Exception as e:
            self.set_status(f"Ошибка очистки: {str(e)}", "red")
            
            