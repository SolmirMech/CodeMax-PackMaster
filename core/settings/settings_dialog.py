import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import win32print
import win32ui
import os
import shutil
from core.config_manager import ConfigManager
from core.shared_utils import (
    mm_to_pixels,
    get_default_printer,
    create_printer_dc,
)


class SettingsDialog:
    """Диалог настроек"""
    def __init__(self, parent_frame, preview_export_module):
        self.parent_frame = parent_frame
        self.preview_export_module = preview_export_module
        self.config_manager = ConfigManager()
        self.coordinator = preview_export_module.coordinator
        self.parent_manager = None
        self.last_status = ""
        
        # Инициализация переменных
        self.xml_folder_path = tk.StringVar(value="")
        self.excel_folder_path = ""
        self.status_var = tk.StringVar(value="")
        self.workshop_var = tk.StringVar(value="1")
        self.paper_width_var = tk.StringVar(value="")
        self.paper_height_var = tk.StringVar(value="")
        self.main_frame = None

    def set_parent_manager(self, manager):
        """Устанавливает ссылку на родительский менеджер"""
        self.parent_manager = manager
        
    def create_ui(self):
        """Создает UI в родительском фрейме"""
        self.main_frame = ttk.Frame(self.parent_frame)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        content_frame = ttk.Frame(self.main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)

        # ЛЕВАЯ КОЛОНКА
        left_frame = ttk.Frame(content_frame)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=5)

        # 1.Настройки печати
        print_frame = ttk.LabelFrame(left_frame, text="Настройки печати", padding=5)
        print_frame.pack(fill=tk.X, pady=(0, 5))

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
        
        # Кнопка обновления принтеров
        update_printers_btn = ttk.Button(
            print_frame, text="🔄 Обновить принтеры", command=self.update_printers
        )
        update_printers_btn.grid(row=1, column=0, padx=5, pady=5, sticky="w")        
        
        # Меню настроек папок
        folder_menu_btn = ttk.Menubutton(
            print_frame, 
            text="📂 Настройки папок", 
            direction="below",
            width=17
        )
        folder_menu_btn.grid(row=2, column=0, padx=5, pady=5, sticky="w")
        
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
        
        cutters_label = ttk.Label(print_frame, text="Резчики:")
        cutters_label.grid(row=0, column=1, sticky="w", padx=10, pady=5)

        # Загружаем текущий список резчиков
        current_cutters = self.config_manager.get_cutters()
        self.cutter_entries = []

        # Создаем поля ввода для каждого резчика
        for i, cutter in enumerate(current_cutters):
            entry = ttk.Entry(print_frame, width=20)
            entry.insert(0, cutter)
            entry.grid(row=1+i, column=1, padx=10, pady=5, sticky="w")
            self.cutter_entries.append(entry)

        # Добавляем пустое поле для нового резчика
        new_entry = ttk.Entry(print_frame, width=20)
        new_entry.grid(row=1+len(current_cutters), column=1, padx=10, pady=5, sticky="w")
        self.cutter_entries.append(new_entry)     

        # Список упаковщиков
        packers_label = ttk.Label(print_frame, text="Упаковщики:")
        packers_label.grid(row=0, column=2, sticky="w", padx=10, pady=5)

        # Загружаем текущий список упаковщиков
        current_packers = self.config_manager.get_packers()
        self.packer_entries = []

        # Создаем поля ввода для каждого упаковщика
        for i, packer in enumerate(current_packers):
            entry = ttk.Entry(print_frame, width=20)
            entry.insert(0, packer)
            entry.grid(row=1+i, column=2, padx=10, pady=5, sticky="w")
            self.packer_entries.append(entry)

        # Добавляем пустое поле для нового упаковщика
        new_packer_entry = ttk.Entry(print_frame, width=20)
        new_packer_entry.grid(row=1+len(current_packers), column=2, padx=10, pady=5, sticky="w")
        self.packer_entries.append(new_packer_entry)
        
        # Переключатель цеха
        workshop_frame = ttk.Frame(print_frame)
        workshop_frame.grid(row=3, column=0, columnspan=2, sticky="w", padx=5, pady=5)

        ttk.Radiobutton(workshop_frame, text="1 цех", variable=self.workshop_var, value="1").pack(side=tk.LEFT, padx=(10,5))
        ttk.Radiobutton(workshop_frame, text="2 цех", variable=self.workshop_var, value="2").pack(side=tk.LEFT, padx=(5,10))

        # Привязка изменения цеха к обновлению размеров
        self.workshop_var.trace_add("write", self._on_workshop_changed)

        # Загружаем текущую настройку цеха
        workshop = self.coordinator.get_workshop()
        self.workshop_var.set(workshop)
        self._update_paper_sizes()
        self.coordinator.subscribe(self._on_settings_changed)

        # 2. РАЗДЕЛ: Изготовитель
        manufacturer_frame = ttk.LabelFrame(left_frame, text="Изготовитель", padding=5)
        manufacturer_frame.pack(fill=tk.X, pady=(0, 5))
        self.manufacturer_var = tk.StringVar(value=self.preview_export_module.manufacturer)
        manufacturer_entry = ttk.Entry(manufacturer_frame, textvariable=self.manufacturer_var, width=36)
        manufacturer_entry.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky="w")      

        ttk.Label(manufacturer_frame, text="Префикс заказа:").grid(row=1, column=0, sticky="w", pady=5)
        self.settings_prefix_var = tk.StringVar(value=self.preview_export_module.order_prefix.get())
        prefix_entry = ttk.Entry(manufacturer_frame, textvariable=self.settings_prefix_var, width=6)
        prefix_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(manufacturer_frame, text="Суффикс заказа:").grid(row=2, column=0, sticky="w", pady=5)
        self.settings_suffix_var = tk.StringVar(value=self.preview_export_module.order_suffix.get())
        suffix_entry = ttk.Entry(manufacturer_frame, textvariable=self.settings_suffix_var, width=6)
        suffix_entry.grid(row=2, column=1, padx=5, pady=5, sticky="w")                   
        
        # Статус-бар внизу окна настроек
        status_label = ttk.Label(
            self.main_frame, 
            textvariable=self.status_var,
            foreground="green",
            font=("Arial", 12)
        )
        status_label.pack(side=tk.LEFT, fill=tk.X, padx=10, pady=10)
        
        # Кнопка сохранения
        save_button = ttk.Button(
            self.main_frame, 
            text="💾 Сохранить", 
            command=self._on_save_clicked,
            width=15
        )
        save_button.pack(side=tk.RIGHT, fill=tk.X, padx=10, pady=10)        
        
        self.update_folder_status()

    def _on_save_clicked(self):
        """Обработчик клика по кнопке сохранения"""
        if self.parent_manager:
            self.parent_manager.save_all_and_close()

    def save_settings(self):
        """Сохраняет настройки этой вкладки"""
        try:
            self.preview_export_module.settings["printer"] = self.printer_var.get()
            self.preview_export_module.settings["paper_width_mm"] = int(self.paper_width_var.get())
            self.preview_export_module.settings["paper_height_mm"] = int(self.paper_height_var.get())
            
            # Сохраняем настройки печати
            all_settings = self.preview_export_module.config_manager.load_json_settings(self.preview_export_module.settings_file)
            all_settings["weight_box_print"] = self.preview_export_module.settings
            self.preview_export_module.config_manager.save_json_settings(self.preview_export_module.settings_file, all_settings)

            # Сохраняем производителя
            new_manufacturer = self.manufacturer_var.get().strip()
            if new_manufacturer:
                self.preview_export_module.config_manager.save_manufacturer(new_manufacturer)
                self.preview_export_module.manufacturer = new_manufacturer

            # Сохраняем настройки номера заказа
            shared_settings = self.preview_export_module.config_manager.load_json_settings("shared_utils.json")
            shared_settings["order_number"] = {
                "prefix": self.settings_prefix_var.get().strip(),
                "suffix": self.settings_suffix_var.get().strip()
            }

            # Сохраняем список резчиков
            new_cutters = []
            for entry in self.cutter_entries:
                cutter_name = entry.get().strip()
                if cutter_name:
                    new_cutters.append(cutter_name)
            shared_settings["cutters"] = new_cutters
            
            # Сохраняем список упаковщиков
            new_packers = []
            for entry in self.packer_entries:
                packer_name = entry.get().strip()
                if packer_name:
                    new_packers.append(packer_name)
            shared_settings["packers"] = new_packers
            
            workshop = self.workshop_var.get()
            self.coordinator.set_workshop(workshop)
            shared_settings["workshop"] = workshop
            
            self.coordinator.apply_workshop_changes(self.preview_export_module.preview_module)

            # Сохраняем упаковщиков через config_manager
            self.preview_export_module.config_manager.save_packers(new_packers)

            # Сохраняем все изменения в shared_utils.json
            self.preview_export_module.config_manager.save_json_settings("shared_utils.json", shared_settings)

            # Обновляем текущие значения
            self.preview_export_module.order_prefix.set(shared_settings["order_number"]["prefix"])
            self.preview_export_module.order_suffix.set(shared_settings["order_number"]["suffix"])

            self.coordinator._notify_subscribers()

            self.last_status = "✅ Общие настройки успешно сохранены!"
            return True

        except Exception as e:
            self.last_status = f"❌ Ошибка сохранения общих настроек: {str(e)}"
            return False        
    
    def set_status_callback(self, callback):
        """Устанавливает колбэк для обновления статуса"""
        self.status_callback = callback
        
    def update_status(self, message, color="green"):
        """Обновляет статус через колбэк"""
        if hasattr(self, 'status_callback') and self.status_callback:
            self.status_callback(message, color)        
        
    def _on_settings_changed(self):
        """Обрабатывает изменения настроек от координатора"""
        
        # Обновляем UI при внешних изменениях
        workshop = self.coordinator.get_workshop()
        
        if self.workshop_var.get() != workshop:
            self.workshop_var.set(workshop)
            self._update_paper_sizes()

    def _on_workshop_changed(self, *args):
        """Обрабатывает изменение выбора цеха"""
        self._update_paper_sizes()

    def _update_paper_sizes(self):
        """Обновляет размеры бумаги в зависимости от цеха"""
        workshop = self.workshop_var.get()
        if workshop == "1":
            self.paper_width_var.set("90")
            self.paper_height_var.set("72")
        else:  # workshop == "2"
            self.paper_width_var.set("80")
            self.paper_height_var.set("57")
        
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
            # Копируем ОБА файла - для 1 и 2 цеха
            files_to_copy = [
                ("weight_orders.xlsx", "weight_orders.xlsx"),
                ("weight_orders_2.xlsx", "weight_orders_2.xlsx")
            ]
            
            copied_files = []
            
            for assets_filename, target_filename in files_to_copy:
                assets_file = self.config_manager.get_asset_path(assets_filename)
                
                if not os.path.exists(assets_file):
                    messagebox.showwarning("Внимание", 
                        f"Файл {assets_filename} не найден в assets, пропускаем")
                    continue
                
                target_file = os.path.join(folder_path, target_filename)
                shutil.copy2(assets_file, target_file)
                copied_files.append(target_filename)
            
            if not copied_files:
                messagebox.showerror("Ошибка", "Не удалось скопировать ни один файл Excel")
                return
            
            # Сохраняем путь к папке
            self.excel_folder_path = folder_path
            self.save_excel_folder_path()
            
            folder_name = os.path.basename(folder_path)
            if not folder_name:
                folder_name = folder_path.rstrip('/\\')
            
            files_list = ", ".join(copied_files)
            self.status_var.set(f"✅ Файлы {files_list} скопированы в: {folder_name}")
            
        except Exception as e:
            self.status_var.set(f"❌ Ошибка копирования: {str(e)}")

    def save_excel_folder_path(self):
        """Сохраняет путь к папке с Excel файлом в настройки"""
        try:
            settings = self.config_manager.load_json_settings("shared_utils.json")
            settings["weight_orders_xlsx"] = self.excel_folder_path
            self.config_manager.save_json_settings("shared_utils.json", settings)
            
            # Можно добавить нотификацию
            if hasattr(self, 'coordinator') and self.coordinator:
                self.coordinator._notify_subscribers()
                
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
        