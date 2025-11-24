import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import win32print
import win32ui
import os
import shutil
from core.config_manager import ConfigManager  # Добавляем импорт
from core.shared_utils import (
    mm_to_pixels,
    get_default_printer,
    create_printer_dc,
)  # Добавляем импорт


class SettingsDialog:
    """Диалог настроек"""

    def __init__(self, parent, preview_export_module):
        self.parent = parent
        self.preview_export_module = preview_export_module
        self.config_manager = ConfigManager()
        self.window = None
        self.xml_folder_path = tk.StringVar(value="")
        # Переменные для Excel
        self.excel_folder_path = ""
        self.status_var = tk.StringVar(value="")        

    def show(self):
        if self.window and self.window.winfo_exists():
            self.window.lift()
            return

        self.window = tk.Toplevel(self.parent)
        self.window.title("Настройки")
        self.window.geometry("835x560")
        self.window.grab_set()

        # Центрирование окна
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"+{x}+{y}")

        self.window.bind("<Escape>", lambda e: self.window.destroy())

        main_frame = ttk.Frame(self.window, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)

        # ЛЕВАЯ КОЛОНКА
        left_frame = ttk.Frame(content_frame)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        # 1.Настройки печати
        print_frame = ttk.LabelFrame(left_frame, text="Настройки печати", padding=10)
        print_frame.pack(fill=tk.X, pady=(0, 10))

        # Выбор принтера
        printers = win32print.EnumPrinters(2)
        self.printer_var = tk.StringVar(value=self.preview_export_module.settings["printer"])
        printer_combo = ttk.Combobox(
            print_frame,
            textvariable=self.printer_var,
            values=[p[2] for p in printers],
            width=25,
        )
        printer_combo.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.settings_vars = {}
        
        # Размеры этикетки
        ttk.Label(print_frame, text="Ширина (мм):").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.paper_width_var = tk.StringVar(value=str(self.preview_export_module.settings.get("paper_width_mm", 80)))
        paper_width_entry = ttk.Entry(print_frame, textvariable=self.paper_width_var, width=8)
        paper_width_entry.grid(row=1, column=1, padx=5, pady=2, sticky="w")

        ttk.Label(print_frame, text="Высота (мм):").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self.paper_height_var = tk.StringVar(value=str(self.preview_export_module.settings.get("paper_height_mm", 58)))
        paper_height_entry = ttk.Entry(print_frame, textvariable=self.paper_height_var, width=8)
        paper_height_entry.grid(row=2, column=1, padx=5, pady=2, sticky="w")
        
        # Редактирование коробок
        open_boxes_btn = ttk.Button(
            print_frame,
            text="📦 Редактор коробок", 
            command=self.open_box_editor,
            width=20
        )
        open_boxes_btn.grid(row=3, column=0, padx=5, pady=2, sticky="w")
        
        # === Добавляем меню настроек папок ===
        folder_menu_btn = ttk.Menubutton(
            print_frame, 
            text="📂 Настройки папок", 
            direction="below",
            width=20
        )
        folder_menu_btn.grid(row=3, column=1, padx=5, pady=2, sticky="w")
        
        folder_menu_btn.menu = tk.Menu(folder_menu_btn, tearoff=0)
        folder_menu_btn["menu"] = folder_menu_btn.menu
        
        folder_menu_btn.menu.add_command(
            label="Выбрать папку для импорта XML", 
            command=self.select_xml_folder
        )
        folder_menu_btn.menu.add_command(
            label="Выбрать папку для экспорта в Excel", 
            command=self.select_excel_folder
        )
        
        # Загружаем текущие пути
        self.load_folder_paths()        
            
        # Кнопка обновления принтеров
        update_printers_btn = ttk.Button(
            print_frame, text="🔄 Обновить принтеры", command=self.update_printers
        )
        update_printers_btn.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        cutters_label = ttk.Label(print_frame, text="Резчики:")
        cutters_label.grid(row=0, column=2, sticky="w", padx=10, pady=(10, 2))

        # Загружаем текущий список резчиков
        current_cutters = self.config_manager.get_cutters()
        self.cutter_entries = []

        # Создаем поля ввода для каждого резчика
        for i, cutter in enumerate(current_cutters):
            entry = ttk.Entry(print_frame, width=20)
            entry.insert(0, cutter)
            entry.grid(row=1+i, column=2, padx=10, pady=2, sticky="w")
            self.cutter_entries.append(entry)

        # Добавляем пустое поле для нового резчика
        new_entry = ttk.Entry(print_frame, width=20)
        new_entry.grid(row=1+len(current_cutters), column=2, padx=10, pady=2, sticky="w")
        self.cutter_entries.append(new_entry)     

        # Список упаковщиков
        packers_label = ttk.Label(print_frame, text="Упаковщики:")
        packers_label.grid(row=0, column=3, sticky="w", padx=10, pady=(10, 2))

        # Загружаем текущий список упаковщиков
        current_packers = self.config_manager.get_packers()
        self.packer_entries = []

        # Создаем поля ввода для каждого упаковщика
        for i, packer in enumerate(current_packers):
            entry = ttk.Entry(print_frame, width=20)
            entry.insert(0, packer)
            entry.grid(row=1+i, column=3, padx=10, pady=2, sticky="w")
            self.packer_entries.append(entry)

        # Добавляем пустое поле для нового упаковщика
        new_packer_entry = ttk.Entry(print_frame, width=20)
        new_packer_entry.grid(row=1+len(current_packers), column=3, padx=10, pady=2, sticky="w")
        self.packer_entries.append(new_packer_entry)

        # 2. РАЗДЕЛ: Производитель
        manufacturer_frame = ttk.LabelFrame(left_frame, text="Производитель", padding=5)
        manufacturer_frame.pack(fill=tk.X, pady=(0, 10))
        self.manufacturer_var = tk.StringVar(value=self.preview_export_module.manufacturer)
        manufacturer_entry = ttk.Entry(manufacturer_frame, textvariable=self.manufacturer_var, width=30)
        manufacturer_entry.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        # Фрейм для кнопок редактирования списков
        lists_frame = ttk.Frame(manufacturer_frame)
        lists_frame.grid(row=0, column=2, columnspan=2, padx=10, pady=5, sticky="w")

        # Кнопка для открытия окна редактирования клиентов
        open_customers_btn = ttk.Button(
            lists_frame,
            text="📝 Список клиентов без Производителя",
            command=self.open_customers_editor
        )
        open_customers_btn.pack(fill=tk.X, pady=5)

        # Кнопка для открытия окна особых клиентов
        open_special_btn = ttk.Button(
            lists_frame,
            text="📋 Список особых клиентов", 
            command=self.open_special_clients_editor
        )
        open_special_btn.pack(fill=tk.X, pady=5)

        # 3. РАЗДЕЛ: Номер заказа
        order_frame = ttk.LabelFrame(left_frame, text="Номер заказа", padding=10)
        order_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(order_frame, text="Префикс:").grid(row=0, column=0, sticky="w", pady=5)
        self.settings_prefix_var = tk.StringVar(value=self.preview_export_module.order_prefix.get())
        prefix_entry = ttk.Entry(order_frame, textvariable=self.settings_prefix_var, width=10)
        prefix_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(order_frame, text="Суффикс:").grid(row=0, column=2, sticky="w", pady=5)
        self.settings_suffix_var = tk.StringVar(value=self.preview_export_module.order_suffix.get())
        suffix_entry = ttk.Entry(order_frame, textvariable=self.settings_suffix_var, width=10)
        suffix_entry.grid(row=0, column=3, padx=5, pady=5, sticky="w")

        # Кнопки сохранения
        save_button = ttk.Button(
            order_frame, 
            text="💾 Сохранить", 
            command=self.save_all_settings,
            width=15
        )
        save_button.grid(row=0, column=4, padx=20, pady=5, sticky="w")
        
        cancel_button = ttk.Button(
            order_frame, 
            text="❌ Отмена", 
            command=self.window.destroy,
            width=15
        )
        cancel_button.grid(row=0, column=5, padx=5, pady=5, sticky="w")
        
        # Статус-бар внизу окна настроек
        status_label = ttk.Label(
            main_frame, 
            textvariable=self.status_var,
            foreground="green",
            font=("Arial", 12)
        )
        status_label.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
        
        self.update_folder_status()

        # Привязка Enter к сохранению
        self.window.bind("<Return>", lambda e: self.save_all_settings())
        
    def load_folder_paths(self):
        try:
            settings = self.config_manager.load_json_settings("shared_utils.json")
            
            # Путь для XML
            xml_path = settings.get("weight_data_base", "")
            self.xml_folder_path.set(xml_path)
            
            # Путь для Excel
            excel_path = settings.get("weight_orders_xlsx", "")
            if excel_path and os.path.exists(excel_path):
                self.excel_folder_path = excel_path
            else:
                self.excel_folder_path = ""
            
            self.update_folder_status()
            
        except Exception as e:
            print(f"Ошибка загрузки путей папок: {e}")
            self.excel_folder_path = ""

    def select_xml_folder(self):
        """Выбирает папку для XML файлов"""
        folder = filedialog.askdirectory(title="Выберите папку с XML файлами")
        if folder:
            self.xml_folder_path.set(folder)
            # Сохраняем в настройки
            settings = self.config_manager.load_json_settings("shared_utils.json")
            settings["weight_data_base"] = folder
            self.config_manager.save_json_settings("shared_utils.json", settings)
            self.update_folder_status()

    def select_excel_folder(self):
        """Выбирает папку для Excel файла"""
        folder_path = filedialog.askdirectory(title="Выберите папку для файла Excel")
        if not folder_path:
            return
        
        try:
            # Используем config_manager для получения пути к файлу
            assets_file = self.config_manager.get_asset_path("weight_orders.xlsx")
            
            # Проверяем существование файла
            if not os.path.exists(assets_file):
                messagebox.showerror("Ошибка", 
                    f"Файл weight_orders.xlsx не найден по пути:\n{assets_file}")
                return
            
            # Путь к целевому файлу
            target_file = os.path.join(folder_path, "weight_orders.xlsx")
            
            # Копируем файл (перезаписываем если существует)
            shutil.copy2(assets_file, target_file)
            
            # Сохраняем путь к папке
            self.excel_folder_path = folder_path
            self.save_excel_folder_path()
            
            self.status_var.set(f"✅ Файл Excel скопирован в: {os.path.basename(folder_path)}")
            
        except Exception as e:
            self.status_var.set(f"❌ Ошибка копирования: {str(e)}")

    def save_excel_folder_path(self):
        """Сохраняет путь к папке с Excel файлом в настройки"""
        try:
            settings = self.config_manager.load_json_settings("shared_utils.json")
            settings["weight_orders_xlsx"] = self.excel_folder_path
            self.config_manager.save_json_settings("shared_utils.json", settings)
        except Exception as e:
            print(f"Ошибка сохранения пути к папке Excel: {e}")

    def update_folder_status(self):
        """Обновляет статусную строку с путями к папкам"""
        xml_text = "Папка XML: " + (os.path.basename(self.xml_folder_path.get()) 
                             if self.xml_folder_path.get() else "не выбрана")
        
        if self.excel_folder_path:
            excel_name = os.path.basename(self.excel_folder_path)
            if not excel_name:
                excel_name = self.excel_folder_path.rstrip('/\\')
            excel_text = "Папка экспорта в Excel: " + excel_name
        else:
            excel_text = "Папка Excel: не выбрана"
        
        status_text = f"{xml_text} | {excel_text}"
        self.status_var.set(status_text)
        
    def update_printers(self):
        """Обновляет принтер во всех секциях настроек печати"""
        try:
            # Получаем текущий принтер по умолчанию из системы
            default_printer = get_default_printer()

            if not default_printer:
                messagebox.showerror(
                    "Ошибка", "Не удалось определить принтер по умолчанию"
                )
                return False

            # Используем метод из ConfigManager для обновления принтера
            success = self.config_manager.update_printer_settings(default_printer)

            if success:
                messagebox.showinfo(
                    "Успех", f"Принтер обновлен на '{default_printer}' во всех секциях"
                )
                # Обновляем комбобокс в диалоге
                self.printer_var.set(default_printer)
            else:
                messagebox.showerror(
                    "Ошибка", f"Не удалось обновить принтер на '{default_printer}'"
                )

            return success

        except Exception as e:
            messagebox.showerror(
                "Ошибка", f"Ошибка при обновлении принтеров:\n{str(e)}"
            )
            return False
        
    def open_customers_editor(self):
        """Открывает окно редактирования списка клиентов без производителя"""
        dialog = CustomersEditorDialog(self.window, self.preview_export_module)
        dialog.parent_dialog = self
        dialog.show()

    def open_special_clients_editor(self):
        """Открывает окно редактирования списка особых клиентов"""
        dialog = SpecialClientsEditorDialog(self.window, self.preview_export_module)
        dialog.parent_dialog = self
        dialog.show()
        
    def open_box_editor(self):
        """Открывает редактор коробок"""
        dialog = BoxEditorDialog(self.window, self.preview_export_module)
        dialog.parent_dialog = self
        dialog.show()

    def save_all_settings(self):
        """Сохраняет все настройки из единого окна (БЕЗ списка клиентов)"""
        try:
            self.preview_export_module.settings["printer"] = self.printer_var.get()
            self.preview_export_module.settings["paper_width_mm"] = int(self.paper_width_var.get())
            self.preview_export_module.settings["paper_height_mm"] = int(self.paper_height_var.get())
            
            # Сохраняем настройки печати
            all_settings = self.preview_export_module.config_manager.load_json_settings(self.preview_export_module.settings_file)
            all_settings["weight_box_print"] = self.preview_export_module.settings
            self.preview_export_module.config_manager.save_json_settings(self.preview_export_module.settings_file, all_settings)

            # 2. Сохраняем производителя
            new_manufacturer = self.manufacturer_var.get().strip()
            if new_manufacturer:
                self.preview_export_module.config_manager.save_manufacturer(new_manufacturer)
                self.preview_export_module.manufacturer = new_manufacturer

            # 3. Сохраняем настройки номера заказа
            shared_settings = self.preview_export_module.config_manager.load_json_settings("shared_utils.json")
            shared_settings["order_number"] = {
                "prefix": self.settings_prefix_var.get().strip(),
                "suffix": self.settings_suffix_var.get().strip()
            }

            # 4. Сохраняем список резчиков (из отдельных полей)
            new_cutters = []
            for entry in self.cutter_entries:
                cutter_name = entry.get().strip()
                if cutter_name:  # Добавляем только непустые имена
                    new_cutters.append(cutter_name)
            shared_settings["cutters"] = new_cutters
            
            # 5. Сохраняем список упаковщиков (из отдельных полей)
            new_packers = []
            for entry in self.packer_entries:
                packer_name = entry.get().strip()
                if packer_name:  # Добавляем только непустые имена
                    new_packers.append(packer_name)
            shared_settings["packers"] = new_packers

            # Сохраняем упаковщиков через config_manager
            self.preview_export_module.config_manager.save_packers(new_packers)

            # Обновляем меню упаковщиков в интерфейсе
            if hasattr(self.preview_export_module, 'update_packers_menu'):
                self.preview_export_module.update_packers_menu()

            # Сохраняем все изменения в shared_utils.json
            self.preview_export_module.config_manager.save_json_settings("shared_utils.json", shared_settings)

            # Обновляем текущие значения
            self.preview_export_module.order_prefix.set(shared_settings["order_number"]["prefix"])
            self.preview_export_module.order_suffix.set(shared_settings["order_number"]["suffix"])

            # Обновляем кнопки резчиков в интерфейсе
            if hasattr(self.preview_export_module, 'update_cutters_menu'):
                self.preview_export_module.update_cutters_menu()

            if self.preview_export_module and hasattr(self.preview_export_module, 'excel_status_label'):
                self.preview_export_module.excel_status_label.config(
                    text="✅ Все настройки успешно сохранены!",
                    foreground="green"
                )
            
            if self.window:
                self.window.destroy()
                self.window = None

        except Exception as e:
            if self.preview_export_module and hasattr(self.preview_export_module, 'excel_status_label'):
                self.preview_export_module.excel_status_label.config(
                    text=f"❌ Ошибка сохранения настроек: {str(e)}",
                    foreground="red"
                )


class CustomersEditorDialog:
    """Диалог редактирования списка клиентов без производителя"""

    def __init__(self, parent, preview_export_module):
        self.parent = parent
        self.preview_export_module = preview_export_module
        self.config_manager = ConfigManager()
        self.window = None
        self.customer_entries = []

    def show(self):
        if self.window and self.window.winfo_exists():
            self.window.lift()
            return

        self.window = tk.Toplevel(self.parent)
        self.window.title("Список клиентов без Производителя")
        self.window.geometry("380x400")
        self.window.grab_set()

        # Центрирование окна
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"+{x}+{y}")

        self.window.bind("<Escape>", lambda e: self.window.destroy())

        main_frame = ttk.Frame(self.window, padding=5)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Создаем canvas и scrollbar для списка клиентов
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.grid(row=1, column=0, sticky="nsew")
        scrollbar.grid(row=1, column=1, sticky="ns")
        
        # Кнопки управления списка
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, pady=5, sticky="w")

        ttk.Button(
            button_frame, 
            text="💾 Сохранить", 
            command=self.save_customers_list
        ).pack(side=tk.LEFT, padx=(100,50))

        # Настраиваем веса для расширения
        main_frame.rowconfigure(2, weight=1)
        main_frame.columnconfigure(0, weight=1)

        # Загружаем текущий список заказчиков
        current_customers = self.config_manager.get_without_manufacturer_customers()

        # Создаем поля ввода для каждого заказчика
        for customer in current_customers:
            entry = ttk.Entry(scrollable_frame, width=55)
            entry.insert(0, customer)
            entry.pack(pady=5, fill=tk.X, padx=5)
            self.customer_entries.append(entry)

        # Добавляем пустое поле для нового заказчика
        new_customer_entry = ttk.Entry(scrollable_frame, width=55)
        new_customer_entry.pack(pady=5, fill=tk.X, padx=5)
        self.customer_entries.append(new_customer_entry)

        # Привязка Enter к сохранению
        self.window.bind("<Return>", lambda e: self.save_customers_list())

    def save_customers_list(self):
        """Сохраняет список клиентов без производителя"""
        try:
            # Собираем все непустые значения
            new_customers = []
            for entry in self.customer_entries:
                customer_name = entry.get().strip()
                if customer_name:  # Добавляем только непустые имена
                    new_customers.append(customer_name)

            # Загружаем текущие настройки
            settings = self.config_manager.load_json_settings("shared_utils.json")
            
            # Обновляем список клиентов без производителя
            settings["without_manufacturer"] = new_customers

            # Сохраняем обратно в файл
            if self.config_manager.save_json_settings("shared_utils.json", settings):
                if hasattr(self, 'parent_dialog') and self.parent_dialog:
                    self.parent_dialog.status_var.set("✅ Список клиентов Без производителя успешно обновлен!")

                if self.window:
                    self.window.destroy()
                    self.window = None

        except Exception as e:
            if hasattr(self, 'parent_dialog') and self.parent_dialog:
                self.parent_dialog.status_var.set(f"❌ Ошибка сохранения клиентов: {str(e)}")


class SpecialClientsEditorDialog:
    """Диалог редактирования списка особых клиентов"""

    def __init__(self, parent, preview_export_module):
        self.parent = parent
        self.preview_export_module = preview_export_module
        self.config_manager = ConfigManager()
        self.window = None
        self.special_name_entries = []
        self.special_text_entries = []

    def show(self):
        if self.window and self.window.winfo_exists():
            self.window.lift()
            return

        # Очищаем списки при каждом открытии окна
        self.special_name_entries = []
        self.special_text_entries = []

        self.window = tk.Toplevel(self.parent)
        self.window.title("Изменить список особых клиентов")
        self.window.geometry("900x650")
        self.window.grab_set()

        # Центрирование окна
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"+{x}+{y}")

        self.window.bind("<Escape>", lambda e: self.window.destroy())

        main_frame = ttk.Frame(self.window, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Фрейм для прокрутки
        container = ttk.Frame(main_frame)
        container.pack(fill=tk.BOTH, expand=True)

        # Создаем canvas и scrollbar
        canvas = tk.Canvas(container)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Загружаем текущий список особых клиентов
        current_special_clients = self.config_manager.get_special_clients()

        # Создаем заголовки колонок
        header_frame = ttk.Frame(scrollable_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(
            header_frame, text="Заказчик", font=("Arial", 14, "bold")
        ).pack(side=tk.LEFT, padx=(0, 45))
        ttk.Label(
            header_frame, text="Текст для отображения особых требований заказчика", font=("Arial", 14, "bold")
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Создаем поля ввода для каждого особого клиента
        for client_name, client_text in current_special_clients.items():
            self._create_special_client_row(scrollable_frame, client_name, client_text)

        # Добавляем пустую строку для нового клиента
        self._create_special_client_row(scrollable_frame, "", "")

        # Кнопки управления
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=10)

        ttk.Button(
            button_frame, text="💾 Сохранить", command=self.save_special_clients
        ).pack(side=tk.LEFT, padx=15)
        ttk.Button(
            button_frame,
            text="➕ Добавить строку",
            command=lambda: self._create_special_client_row(scrollable_frame, "", ""),
        ).pack(side=tk.LEFT, padx=15)
        ttk.Button(
            button_frame, text="❌ Отмена", command=self.window.destroy
        ).pack(side=tk.LEFT, padx=15)

        # Привязка Enter к сохранению
        self.window.bind("<Return>", lambda e: self.save_special_clients())

    def _create_special_client_row(self, parent, name, text):
        """Создает строку с полями ввода для особого клиента"""
        row_frame = ttk.Frame(parent)
        row_frame.pack(fill=tk.X, pady=2)

        # Поле для имени клиента
        name_entry = ttk.Entry(row_frame, width=20)
        name_entry.insert(0, name)
        name_entry.pack(side=tk.LEFT, padx=(0, 10))
        self.special_name_entries.append(name_entry)

        # Фрейм для текстового поля с прокруткой
        text_frame = ttk.Frame(row_frame)
        text_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Текстовое поле с прокруткой
        text_widget = tk.Text(text_frame, width=80, height=3, wrap=tk.WORD)
        text_widget.insert("1.0", text)

        text_scrollbar = ttk.Scrollbar(
            text_frame, orient=tk.VERTICAL, command=text_widget.yview
        )
        text_widget.configure(yscrollcommand=text_scrollbar.set)

        text_widget.pack(side=tk.LEFT, fill=tk.X, expand=True)
        text_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.special_text_entries.append(text_widget)

        # Кнопка удаления строки
        delete_btn = ttk.Button(
            row_frame,
            text="×",
            width=2,
            command=lambda: self._remove_special_client_row(
                row_frame, name_entry, text_widget
            ),
        )
        delete_btn.pack(side=tk.RIGHT, padx=(5, 0))

    def _remove_special_client_row(self, row_frame, name_entry, text_entry):
        """Удаляет строку с полями ввода"""
        if len(self.special_name_entries) > 1:  # Не позволяем удалить последнюю строку
            row_frame.destroy()
            self.special_name_entries.remove(name_entry)
            self.special_text_entries.remove(text_entry)

    def save_special_clients(self):
        """Сохраняет измененный список особых клиентов"""
        try:
            # Собираем все непустые значения
            new_special_clients = {}
            for name_entry, text_widget in zip(
                self.special_name_entries, self.special_text_entries
            ):
                client_name = name_entry.get().strip()
                client_text = text_widget.get("1.0", tk.END).strip()

                if client_name:  # Добавляем только клиентов с непустым именем
                    new_special_clients[client_name] = client_text

            # Загружаем текущие настройки
            settings = self.config_manager.load_json_settings("shared_utils.json")

            # Обновляем список особых клиентов
            settings["special_clients"] = new_special_clients

            # Сохраняем обратно в файл
            if self.config_manager.save_json_settings("shared_utils.json", settings):
                if hasattr(self, 'parent_dialog') and self.parent_dialog:
                    self.parent_dialog.status_var.set("✅ Список особых клиентов успешно обновлен!")

                if self.window:
                    self.window.destroy()
                    self.window = None

        except Exception as e:
            if hasattr(self, 'parent_dialog') and self.parent_dialog:
                self.parent_dialog.status_var.set(f"❌ Ошибка сохранения особых клиентов: {str(e)}")

            
class BoxEditorDialog:
    """Диалог редактирования списка коробок"""

    def __init__(self, parent, preview_export_module):
        self.parent = parent
        self.preview_export_module = preview_export_module
        self.config_manager = ConfigManager()
        self.window = None
        self.box_size_entries = []
        self.box_weight_entries = []

    def show(self):
        if self.window and self.window.winfo_exists():
            self.window.lift()
            return

        self.window = tk.Toplevel(self.parent)
        self.window.title("Редактирование списка коробок")
        self.window.geometry("430x600")
        self.window.grab_set()

        # Центрирование окна
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"+{x}+{y}")
        self.window.bind("<Escape>", lambda e: self.window.destroy())

        frame = ttk.Frame(self.window, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        # Фрейм для прокрутки
        container = ttk.Frame(frame)
        container.pack(fill=tk.BOTH, expand=True)

        # Создаем canvas и scrollbar
        canvas = tk.Canvas(container)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Загружаем текущий список коробок
        current_boxes = self.get_current_boxes()

        # Создаем заголовки
        header_frame = ttk.Frame(scrollable_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(header_frame, text="Название коробки", font=("Arial", 12, "bold")).pack(side=tk.LEFT, padx=(0, 30))
        ttk.Label(header_frame, text="Вес коробки (г)", font=("Arial", 12, "bold")).pack(side=tk.LEFT, padx=(15, 15))

        # Создаем поля ввода
        self.box_size_entries = []
        self.box_weight_entries = []

        for size, weight in current_boxes.items():
            self._create_box_row(scrollable_frame, size, weight)

        # Добавляем пустую строку
        self._create_box_row(scrollable_frame, "", "")

        # Кнопки управления
        button_frame = ttk.Frame(frame)
        button_frame.pack(pady=10)

        ttk.Button(button_frame, text="💾 Сохранить", command=self.save_boxes).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="➕ Добавить строку", 
                  command=lambda: self._create_box_row(scrollable_frame, "", "")).pack(side=tk.LEFT, padx=(5, 30))
        ttk.Button(button_frame, text="❌ Отмена", command=self.window.destroy).pack(side=tk.LEFT, padx=5)

        self.window.bind("<Return>", lambda e: self.save_boxes())

    def _create_box_row(self, parent, size, weight):
        """Создает строку с полями ввода для коробки"""
        row_frame = ttk.Frame(parent)
        row_frame.pack(fill=tk.X, pady=2)

        # Поле для размеров
        size_entry = ttk.Entry(row_frame, width=30)
        size_entry.insert(0, size)
        size_entry.pack(side=tk.LEFT, padx=(0, 10))
        self.box_size_entries.append(size_entry)

        # Поле для веса
        weight_entry = ttk.Entry(row_frame, width=15)
        weight_entry.insert(0, str(weight))
        weight_entry.pack(side=tk.LEFT, padx=(0, 10))
        self.box_weight_entries.append(weight_entry)

        # Кнопка удаления
        ttk.Button(row_frame, text="×", width=2,
                  command=lambda: self._remove_box_row(row_frame, size_entry, weight_entry)).pack(side=tk.RIGHT)

    def _remove_box_row(self, row_frame, size_entry, weight_entry):
        """Удаляет строку с полями ввода"""
        if len(self.box_size_entries) > 1:
            row_frame.destroy()
            self.box_size_entries.remove(size_entry)
            self.box_weight_entries.remove(weight_entry)

    def get_current_boxes(self):
        """Возвращает текущий список коробок"""
        try:
            settings = self.config_manager.load_json_settings("shared_utils.json")
            return settings.get("weight_box", {})
        except:
            return {}

    def save_boxes(self):
        """Сохраняет список коробок в shared_utils.json"""
        try:
            new_boxes = {}
            for size_entry, weight_entry in zip(self.box_size_entries, self.box_weight_entries):
                size = size_entry.get().strip()
                weight_str = weight_entry.get().strip()
                
                if size and weight_str:
                    try:
                        weight = int(weight_str)
                        new_boxes[size] = weight
                    except ValueError:
                        continue

            # Загружаем текущие настройки и обновляем weight_box
            settings = self.config_manager.load_json_settings("shared_utils.json")
            settings["weight_box"] = new_boxes
            
            if self.config_manager.save_json_settings("shared_utils.json", settings):
                # Обновляем комбобоксы через preview_export_module
                if hasattr(self.preview_export_module, 'load_box_sizes'):
                    self.preview_export_module.load_box_sizes()
                
                # Обновляем комбобокс поддонов  
                if hasattr(self.preview_export_module, 'load_pallet_sizes'):
                    self.preview_export_module.load_pallet_sizes()
                
                # Статус
                if hasattr(self, 'parent_dialog') and self.parent_dialog:
                    self.parent_dialog.status_var.set("✅ Список коробок успешно обновлен!")
                
                self.window.destroy()
            else:
                if hasattr(self, 'parent_dialog') and self.parent_dialog:
                    self.parent_dialog.status_var.set("❌ Не удалось сохранить список коробок")
                    
        except Exception as e:
            if hasattr(self, 'parent_dialog') and self.parent_dialog:
                self.parent_dialog.status_var.set(f"❌ Ошибка сохранения коробок: {str(e)}")