import tkinter as tk
from tkinter import ttk, filedialog
import win32print
import win32ui
import os
import sys
import shutil

def get_default_printer():
    return win32print.GetDefaultPrinter()


class SettingsDialog:
    """Диалог настроек"""
    def __init__(self, parent_frame, config_manager=None, coordinator=None):
        self.parent_frame = parent_frame
        self.config_manager = config_manager
        self.coordinator = coordinator
        self.parent_manager = None
        self.last_status = ""
        
        # Инициализация переменных
        self.xml_folder_path = tk.StringVar(value="")
        self.excel_folder_path = ""
        self.status_var = tk.StringVar(value="")
        self.workshop_var = tk.StringVar(value="1")
        self.archive_status_var = tk.StringVar(value="on")
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
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_columnconfigure(1, weight=1)

        # Настройки печати - выбор принтера
        print_frame = ttk.LabelFrame(content_frame, text="Настройки печати", padding=5)
        print_frame.grid(row=0, column=0, columnspan=3, sticky="w", padx=5, pady=(0, 5))

        # Загружаем принтер из JSON
        print_settings = self.config_manager.load_json_settings("print_settings.json")
        weight_settings = print_settings.get("weight_box_print", {})
        saved_printer = weight_settings.get("printer", "")

        # Получаем список доступных принтеров
        try:
            import win32print
            printers = win32print.EnumPrinters(2)
            printer_list = [p[2] for p in printers]
        except:
            printer_list = [saved_printer] if saved_printer else []

        self.printer_var = tk.StringVar(value=saved_printer)
        printer_combo = ttk.Combobox(
            print_frame,
            textvariable=self.printer_var,
            values=printer_list,
            width=25,
        )
        printer_combo.grid(row=0, column=0, padx=5, pady=5, sticky="w")
      
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
        
        # Отображение размера этикетки
        self.size_label = ttk.Label(
            print_frame,
            text=self._get_label_size_text(),
            font=("Arial", 14, "bold"),
            foreground="green"
        )
        self.size_label.grid(row=4, column=0, columnspan=2, sticky="w", padx=(50, 10), pady=(0, 5))

        # РАЗДЕЛ: ИЗГОТОВИТЕЛЬ
        manufacturer_frame = ttk.LabelFrame(content_frame, text="Изготовитель", padding=5)
        manufacturer_frame.grid(row=1, column=0, rowspan=4, sticky="w", padx=(5, 0), pady=(0, 5))

        # Загружаем производителя из JSON
        shared_settings = self.config_manager.load_json_settings("shared_utils.json")
        saved_manufacturer = shared_settings.get("manufacturer", "")

        self.manufacturer_var = tk.StringVar(value=saved_manufacturer)
        manufacturer_entry = ttk.Entry(manufacturer_frame, textvariable=self.manufacturer_var, width=36)
        manufacturer_entry.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky="w")

        # Префикс заказа
        order_settings = shared_settings.get("order_number", {})
        saved_prefix = order_settings.get("prefix", "Ф")
        self.settings_prefix_var = tk.StringVar(value=saved_prefix)

        ttk.Label(manufacturer_frame, text="Префикс заказа:").grid(row=1, column=0, sticky="w", pady=5)
        prefix_entry = ttk.Entry(manufacturer_frame, textvariable=self.settings_prefix_var, width=6)
        prefix_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        # Суффикс заказа
        saved_suffix = order_settings.get("suffix", "/5")
        self.settings_suffix_var = tk.StringVar(value=saved_suffix)

        ttk.Label(manufacturer_frame, text="Суффикс заказа:").grid(row=2, column=0, sticky="w", pady=5)
        suffix_entry = ttk.Entry(manufacturer_frame, textvariable=self.settings_suffix_var, width=6)
        suffix_entry.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        
        # Кнопка открытия втулки
        ttk.Button(
            manufacturer_frame,
            text="✓ Печать на втулку",
            command=self.open_weight_orders_window,
            width=19
        ).grid(row=3, column=0, columnspan=2, padx=5, pady=5, sticky="w")
        
        # Кнопка доступа к папке данных
        ttk.Button(
            manufacturer_frame,
            text="📁 Папка настроек",
            command=self.open_data_folder,
            width=17
        ).grid(row=4, column=0, columnspan=2, padx=5, pady=5, sticky="w")
        
        # Кнопка доступа к папке ассетсов
        ttk.Button(
            manufacturer_frame,
            text="📁 Папка шаблонов",
            command=self.open_assets_folder,
            width=17
        ).grid(row=5, column=0, columnspan=2, padx=5, pady=5, sticky="w")       
        
        # 3. РАЗДЕЛ: Настройки архивации
        archive_frame = ttk.LabelFrame(content_frame, text="Архивация листов при печати", padding=5)
        archive_frame.grid(row=1, column=1, sticky="w", padx=(5, 0), pady=(0, 5))
        
        # Загружаем сохранённый статус
        settings = self.config_manager.load_json_settings("shared_utils.json")
        archive_status = settings.get("archive_status", "on")
        self.archive_status_var.set(archive_status)
        
        ttk.Radiobutton(
            archive_frame, 
            text="Включить", 
            variable=self.archive_status_var, 
            value="on"
        ).pack(side=tk.LEFT, padx=(10, 5))
        
        ttk.Radiobutton(
            archive_frame, 
            text="Выключить", 
            variable=self.archive_status_var, 
            value="off"
        ).pack(side=tk.LEFT, padx=(5, 10))
        
        # 4. РАЗДЕЛ: Дополнительные элементы
        elements_frame = ttk.LabelFrame(content_frame, text="Дата и другие редкие настройки", padding=5)
        elements_frame.grid(row=2, column=1, sticky="w", padx=(5, 0), pady=(0, 5))
        
        # Загружаем сохранённый статус
        settings = self.config_manager.load_json_settings("shared_utils.json")
        elements_status = settings.get("elements_status", "Скрыть")
        self.elements_status_var = tk.StringVar(value=elements_status)      
        
        ttk.Radiobutton(
            elements_frame, 
            text="Скрыть", 
            variable=self.elements_status_var, 
            value="Скрыть"
        ).pack(side=tk.LEFT, padx=(10, 5))
        
        ttk.Radiobutton(
            elements_frame, 
            text="Показать", 
            variable=self.elements_status_var, 
            value="Показать"
        ).pack(side=tk.LEFT, padx=(5, 10))
        
        # --- Строка статуса для сообщений ---
        self.message_status_var = tk.StringVar(value="")
        self.message_status_label = ttk.Label(
            content_frame,
            textvariable=self.message_status_var,
            foreground="blue",
            font=("Arial", 14),
            wraplength=700,
            anchor="w"
        )
        self.message_status_label.grid(row=5, column=0, columnspan=3, sticky="we", padx=5, pady=(5, 0))
        
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
        
    def open_data_folder(self):
        """Открывает папку данных в проводнике"""
        try:
            data_dir = self.config_manager.data_dir
            if os.path.exists(data_dir):
                os.startfile(data_dir)
            else:
                self.show_message(f"Папка данных не найдена: {data_dir}", "red")
        except Exception as e:
            self.show_message(f"Ошибка открытия папки данных: {str(e)}", "red")

    def open_assets_folder(self):
        """Открывает папку ассетсов в проводнике"""
        try:
            # Получаем путь к папке assets
            if hasattr(sys, '_MEIPASS'):
                # Режим бинарника
                base_path = os.path.dirname(sys.executable)
                assets_dir = os.path.join(base_path, "_internal", "assets")
            else:
                # Режим разработки
                current_dir = os.path.dirname(os.path.abspath(__file__))
                project_root = os.path.dirname(os.path.dirname(current_dir))
                assets_dir = os.path.join(project_root, "assets")
            
            if os.path.exists(assets_dir):
                os.startfile(assets_dir)
            else:
                self.show_message(f"Папка шаблонов не найдена: {assets_dir}", "red")
        except Exception as e:
            self.show_message(f"Ошибка открытия папки шаблонов: {str(e)}", "red")        
        
    def clear_message_after_delay(self, delay_ms=5000):
        """Очищает сообщение через указанное время"""
        if hasattr(self, 'message_status_var') and self.message_status_var:
            self.message_status_var.set("")

    def show_message(self, message, color="blue"):
        """Показывает сообщение в строке статуса и очищает через 5 секунд"""
        if hasattr(self, 'message_status_var') and self.message_status_var:
            self.message_status_var.set(message)
            # Настраиваем цвет
            if color == "blue":
                self.message_status_label.configure(foreground="blue")
            elif color == "red":
                self.message_status_label.configure(foreground="red")
            elif color == "green":
                self.message_status_label.configure(foreground="green")
            
            # Очищаем через 5 секунд
            self.main_frame.after(5000, self.clear_message_after_delay)
        
    def open_weight_orders_window(self):
        """Открывает окно для работы с втулками"""
        # Проверяем, есть ли уже открытое окно
        if hasattr(self, 'weight_orders_window') and self.weight_orders_window and self.weight_orders_window.winfo_exists():
            self.weight_orders_window.lift()
            return

        # Создаем новое окно
        self.weight_orders_window = tk.Toplevel(self.parent_frame)
        self.weight_orders_window.title("Втулка")
        self.weight_orders_window.geometry("440x600")
        
        # Перехватываем фокус
        self.weight_orders_window.grab_set()
        
        # Привязка Esc для закрытия
        self.weight_orders_window.bind("<Escape>", lambda e: self.on_weight_orders_close())
        
        # Центрируем окно
        self.weight_orders_window.update_idletasks()
        width = self.weight_orders_window.winfo_width()
        height = self.weight_orders_window.winfo_height()
        x = (self.weight_orders_window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.weight_orders_window.winfo_screenheight() // 2) - (height // 2)
        self.weight_orders_window.geometry(f"+{x}+{y}")
        
        # Создаем модуль втулки, передавая config_manager
        from main_ui.second_ui.weight_orders_printer import WeightOrdersPrinter
        self.weight_orders_module = WeightOrdersPrinter(
            self.weight_orders_window,
            config_manager=self.config_manager
        )
        
        # Устанавливаем обработчик закрытия окна
        self.weight_orders_window.protocol("WM_DELETE_WINDOW", self.on_weight_orders_close)
        
    def on_weight_orders_close(self):
        """Обработчик закрытия окна втулки"""
        if self.weight_orders_window:
            self.weight_orders_window.destroy()
            self.weight_orders_window = None
        
    def _get_label_size_text(self):
        """Возвращает текст с размером этикетки в формате '92x70'"""
        workshop = self.workshop_var.get()
        if workshop == "1":
            return "90x72 мм"
        else:  # workshop == "2"
            return "80x57 мм"

    def _on_save_clicked(self):
        """Обработчик клика по кнопке сохранения"""
        if self.parent_manager:
            self.parent_manager.save_all_and_close()

    def save_settings(self):
        """Сохраняет настройки этой вкладки"""
        try:
            # Сохраняем настройки печати
            print_settings = {
                "printer": self.printer_var.get(),
                "paper_width_mm": int(self.paper_width_var.get()),
                "paper_height_mm": int(self.paper_height_var.get())
            }
            
            all_settings = self.config_manager.load_json_settings("print_settings.json")
            all_settings["weight_box_print"] = print_settings
            self.config_manager.save_json_settings("print_settings.json", all_settings)

            # Сохраняем производителя
            new_manufacturer = self.manufacturer_var.get().strip()
            if new_manufacturer:
                # 1. Сохраняем в JSON
                self.config_manager.save_manufacturer(new_manufacturer)

            # Сохраняем настройки номера заказа
            shared_settings = self.config_manager.load_json_settings("shared_utils.json")
            shared_settings["order_number"] = {
                "prefix": self.settings_prefix_var.get().strip(),
                "suffix": self.settings_suffix_var.get().strip()
            }            
            
            # Сохраняем статус архивации
            shared_settings["archive_status"] = self.archive_status_var.get()
            
            # Сохраняем статус дополнительных элементов
            shared_settings["elements_status"] = self.elements_status_var.get()            

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
            
            # Сохраняем значение номера цеха
            workshop = self.workshop_var.get()
            shared_settings["workshop"] = workshop
            
            # Применяем изменения цеха
            self.coordinator.set_workshop(workshop)

            # Сохраняем все изменения в shared_utils.json
            self.config_manager.save_json_settings("shared_utils.json", shared_settings)

            self.coordinator.refresh_archive_status()
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
            # Уведомляем подписчиков об изменении XML папки
            if hasattr(self, 'coordinator') and self.coordinator:
                self.coordinator._notify_subscribers()            

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
                self.show_message("❌ Ошибка: Не удалось определить принтер по умолчанию", "red")
                return False

            # Используем метод из ConfigManager для обновления принтера
            success = self.config_manager.update_printer_settings(default_printer)

            if success:
                self.show_message(f"✅ Принтер обновлен на '{default_printer}' во всех секциях", "green")
                # Обновляем комбобокс в диалоге
                self.printer_var.set(default_printer)
            else:
                self.show_message(f"❌ Ошибка: Не удалось обновить принтер на '{default_printer}'", "red")

            return success

        except Exception as e:
            self.show_message(f"❌ Ошибка при обновлении принтеров: {str(e)}", "red")
            return False

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
                    self.show_message(f"⚠️ Внимание: Файл {assets_filename} не найден в assets, пропускаем", "blue")
                    continue
                
                target_file = os.path.join(folder_path, target_filename)
                shutil.copy2(assets_file, target_file)
                copied_files.append(target_filename)
            
            if not copied_files:
                self.show_message("❌ Ошибка: Не удалось скопировать ни один файл Excel", "red")
                return
            
            # Сохраняем путь к папке
            self.excel_folder_path = folder_path
            self.save_excel_folder_path()
            
            folder_name = os.path.basename(folder_path)
            if not folder_name:
                folder_name = folder_path.rstrip('/\\')
            
            files_list = ", ".join(copied_files)
            self.show_message(f"✅ Файлы {files_list} скопированы в: {folder_name}", "green")
            
        except Exception as e:
            self.show_message(f"❌ Ошибка копирования: {str(e)}", "red")
        