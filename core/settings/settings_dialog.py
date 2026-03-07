import os
import shutil
import sys
import tkinter as tk
from tkinter import ttk, filedialog, BooleanVar

import win32print


def get_default_printer():
    return win32print.GetDefaultPrinter()


# noinspection SpellCheckingInspection,PyTypeChecker
class SettingsDialog:
    """Диалог настроек"""

    def __init__(self, parent_frame, config_manager=None, coordinator=None):
        self.packaging_log_file = None
        self.parent_frame = parent_frame
        self.config_manager = config_manager
        self.coordinator = coordinator
        self.parent_manager = None
        self.last_status = ""

        # Инициализация UI элементов (будут созданы в create_ui)
        self.main_frame = None
        self.message_status_label = None

        # === НАСТРОЙКИ ПЕЧАТИ ===
        self.printer_roll_var = tk.StringVar(value="")
        self.printer_box_var = tk.StringVar(value="")

        # === НАСТРОЙКИ ЦЕХА И РАЗМЕРОВ ===
        self.workshop_var = tk.StringVar(value="1")  # Выбор цеха

        # === ПУТИ К ПАПКАМ ===
        self.xml_folder_path = tk.StringVar(value="")  # Папка для XML
        self.excel_folder_path = ""  # Папка для Excel

        # === НАСТРОЙКИ НОМЕРА ЗАКАЗА ===
        self.settings_prefix_var = tk.StringVar(value="")  # Префикс (Ф)
        self.settings_suffix_var = tk.StringVar(value="")  # Суффикс (/5)

        # === ДОПОЛНИТЕЛЬНЫЕ ЭЛЕМЕНТЫ ===
        self.elements_status_var = tk.StringVar(value="Скрыть")  # Показать/скрыть доп. элементы
        self.qr_var = tk.BooleanVar(value=True)  # Печать QR-кода

        # === СТАТУСЫ И СООБЩЕНИЯ ===
        self.status_var = tk.StringVar(value="")  # Статусная строка с путями
        self.message_status_var = tk.StringVar(value="")  # Временные сообщения
        self.status_callback = None  # Колбэк для обновления статуса

        # === АРХИВАЦИЯ ===
        self.archive_status_var = tk.StringVar(value="on")  # Вкл/выкл архивацию

        # === ОКНО ВТУЛКИ ===
        self.weight_orders_window = None  # Ссылка на окно втулки
        self.weight_orders_module = None  # Модуль втулки

        # === НАСТРОЙКИ ШАБЛОНОВ ЭТИКЕТОК ===
        self.roll_template_var = tk.StringVar(value="")
        self.box_template_var = tk.StringVar(value="")

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
        content_frame.grid_columnconfigure(2, weight=1)

        # Настройки печати - выбор принтера (первая колонка сверху)
        print_frame = ttk.LabelFrame(content_frame, text="Настройки печати", padding=5)
        print_frame.grid(row=0, column=0, sticky="w", padx=5, pady=(10, 5))

        # Загружаем принтеры из JSON
        print_settings = self.config_manager.load_json_settings("print_settings.json")
        weight_settings = print_settings.get("weight_box_print", {})
        saved_printer_roll = weight_settings.get("printer_roll", "")
        saved_printer_box = weight_settings.get("printer_box", "")

        # Получаем список доступных принтеров
        try:
            import win32print
            printers = win32print.EnumPrinters(2)
            printer_list = [p[2] for p in printers]
        except:
            printer_list = []

        # Принтер для роликов
        ttk.Label(print_frame, text="Принтер для роликов:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.printer_roll_var = tk.StringVar(value=saved_printer_roll)
        printer_roll_combo = ttk.Combobox(
            print_frame,
            textvariable=self.printer_roll_var,
            values=printer_list,
            width=25,
        )
        printer_roll_combo.grid(row=1, column=0, padx=5, pady=(0, 5), sticky="w")

        # Принтер для коробок
        ttk.Label(print_frame, text="Принтер для коробок:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self.printer_box_var = tk.StringVar(value=saved_printer_box)
        printer_box_combo = ttk.Combobox(
            print_frame,
            textvariable=self.printer_box_var,
            values=printer_list,
            width=25,
        )
        printer_box_combo.grid(row=3, column=0, padx=5, pady=(0, 5), sticky="w")

        # Меню настроек папок
        folder_menu_btn = ttk.Menubutton(
            print_frame,
            text="📂 Настройки папок",
            direction="below",
            width=17
        )
        folder_menu_btn.grid(row=4, column=0, padx=5, pady=5, sticky="w")

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
        folder_menu_btn.menu.add_command(
            label="Выбрать файл журнала упаковки",
            command=self.select_packaging_log_file
        )

        # Загружаем текущие пути
        self.load_folder_paths()

        # Переключатель цеха
        workshop_frame = ttk.Frame(print_frame)
        workshop_frame.grid(row=5, column=0, columnspan=2, sticky="w", padx=5, pady=5)

        ttk.Radiobutton(workshop_frame, text="1 цех", variable=self.workshop_var, value="1").pack(side=tk.LEFT,
                                                                                                  padx=(10, 5))
        ttk.Radiobutton(workshop_frame, text="2 цех", variable=self.workshop_var, value="2").pack(side=tk.LEFT,
                                                                                                  padx=(5, 10))

        # Загружаем текущую настройку цеха
        workshop = self.coordinator.get_workshop()
        self.workshop_var.set(workshop)

        # ========== Шаблоны этикеток (вторая колонка сверху) ==========
        templates_frame = ttk.LabelFrame(content_frame, text="Выбор pdf-шаблона", padding=5)
        templates_frame.grid(row=0, column=1, sticky="n", padx=5, pady=(10, 5))

        # Сначала загружаем цех
        workshop = self.coordinator.get_workshop()
        self.workshop_var.set(workshop)

        # Убеждаемся, что файл шаблонов существует
        self.config_manager.ensure_templates_list_exists()

        # Загружаем текущие шаблоны и списки
        templates_data = self.config_manager.load_json_settings("templates_list.json")
        roll_templates = templates_data.get("roll_templates", {})
        box_templates = templates_data.get("box_templates", {})

        # --- Шаблон для ролика ---
        ttk.Label(templates_frame, text="Ролик:").grid(row=0, column=0, sticky="w", padx=5, pady=5)

        # Берём только отображаемые имена для комбобокса
        roll_display_names = list(roll_templates.keys())

        self.roll_template_var = tk.StringVar()
        roll_combo = ttk.Combobox(
            templates_frame,
            textvariable=self.roll_template_var,
            values=roll_display_names,
            width=30,
            state="readonly"
        )
        roll_combo.grid(row=1, column=0, padx=5, pady=5, sticky="w")

        # --- Шаблон для коробки ---
        ttk.Label(templates_frame, text="Коробка:").grid(row=0, column=1, sticky="w", padx=5, pady=5)

        box_display_names = list(box_templates.keys())

        self.box_template_var = tk.StringVar()
        box_combo = ttk.Combobox(
            templates_frame,
            textvariable=self.box_template_var,
            values=box_display_names,
            width=30,
            state="readonly"
        )
        box_combo.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        # Кнопка применения шаблонов
        ttk.Button(
            templates_frame,
            text="✅ Применить шаблоны",
            command=self._apply_templates,
            width=20
        ).grid(row=2, column=0, padx=5, pady=10, columnspan=2, sticky="w")

        # Загружаем сохранённые значения
        self._load_templates_for_workshop(workshop)

        # РАЗДЕЛ: Папки и разное (первая колонка снизу)
        manufacturer_frame = ttk.LabelFrame(content_frame, text="Папки и разное", padding=5)
        manufacturer_frame.grid(row=1, column=0, rowspan=6, sticky="w", padx=(5, 0), pady=(0, 5))

        # Загружаем из JSON
        shared_settings = self.config_manager.load_json_settings("shared_utils.json")

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
        
        # Раздел с кнопками для доступа к разным папкам.
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

        # Кнопка открытия папки с Excel
        ttk.Button(
            manufacturer_frame,
            text="📁 Папка с Excel",
            command=self.open_excel_folder,
            width=17
        ).grid(row=6, column=0, columnspan=2, padx=5, pady=5, sticky="w")
        
        # 3. РАЗДЕЛ: Настройки архивации (вторая колонка снизу)
        archive_frame = ttk.LabelFrame(content_frame, text="Архивация листов при печати", padding=5)
        archive_frame.grid(row=1, column=1, sticky="w", padx=(5, 0), pady=(0, 105))
        
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
        elements_frame.grid(row=2, column=1, sticky="w", padx=(5, 0), pady=5)

        # Загружаем сохранённый статус
        settings = self.config_manager.load_json_settings("shared_utils.json")
        elements_status = settings.get("elements_status", "Скрыть")
        self.elements_status_var = tk.StringVar(value=elements_status)

        # Строка 0: Radiobutton
        ttk.Radiobutton(
            elements_frame, 
            text="Скрыть", 
            variable=self.elements_status_var, 
            value="Скрыть"
        ).grid(row=0, column=0, padx=(10, 5), pady=2, sticky="w")

        ttk.Radiobutton(
            elements_frame, 
            text="Показать", 
            variable=self.elements_status_var, 
            value="Показать"
        ).grid(row=0, column=1, padx=(5, 10), pady=2, sticky="w")

        # Строка 1: Галочка QR-кода
        self.qr_var = BooleanVar(value=settings.get("qr_data", True))

        qr_check = ttk.Checkbutton(
            elements_frame,
            text="Печать QR-кода",
            variable=self.qr_var,
            command=self._on_qr_toggled
        )
        qr_check.grid(row=1, column=0, columnspan=2, sticky="w", padx=10, pady=(5, 5))
        
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
        self.message_status_label.grid(row=7, column=0, columnspan=3, sticky="we", padx=5, pady=(5, 0))
        
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

    def select_packaging_log_file(self):
        """Выбирает файл журнала упаковки"""
        file_path = filedialog.askopenfilename(
            title="Выберите файл журнала упаковки",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
        )
        if not file_path:
            return

        # Сохраняем путь в настройки
        settings = self.config_manager.load_json_settings("shared_utils.json")
        settings["packaging_log_file"] = file_path
        self.packaging_log_file = file_path
        self.config_manager.save_json_settings("shared_utils.json", settings)

        file_name = os.path.basename(file_path)
        self.show_message(f"✅ Выбран файл: {file_name}", "green")

    def get_packaging_log_file(self):
        """Возвращает путь к файлу журнала упаковки"""
        settings = self.config_manager.load_json_settings("shared_utils.json")
        return settings.get("packaging_log_file", "")

    def open_excel_folder(self):
        """Открывает папку с Excel файлами в проводнике"""
        if not self.excel_folder_path or not os.path.exists(self.excel_folder_path):
            self.show_message("⚠️ Папка не выбрана", "orange")
            return

        try:
            os.startfile(self.excel_folder_path)
        except Exception as e:
            self.show_message(f"❌ Ошибка открытия папки: {str(e)}", "red")

    def _load_templates_for_workshop(self, workshop):
        """Загружает шаблоны для указанного цеха из сохранённых настроек"""
        settings = self.config_manager.load_json_settings("shared_utils.json")

        # Загружаем список всех шаблонов
        templates_data = self.config_manager.load_json_settings("templates_list.json")
        roll_templates = templates_data.get("roll_templates", {})
        box_templates = templates_data.get("box_templates", {})

        # Загружаем шаблон ролика
        saved_roll = settings.get(f"selected_roll_template_{workshop}", "roll.pdf")
        # Ищем отображаемое имя по имени файла
        for display_name, filename in roll_templates.items():
            if filename == saved_roll:
                self.roll_template_var.set(display_name)
                break
        else:
            # Если не нашли, берём первый или пустую строку
            if roll_templates:
                self.roll_template_var.set(list(roll_templates.keys())[0])

        # Загружаем шаблон коробки
        saved_box = settings.get(f"selected_box_template_{workshop}", "box.pdf")
        for display_name, filename in box_templates.items():
            if filename == saved_box:
                self.box_template_var.set(display_name)
                break
        else:
            if box_templates:
                self.box_template_var.set(list(box_templates.keys())[0])

    def _apply_templates(self):
        """Сохраняет выбранные шаблоны для текущего цеха"""
        workshop = self.workshop_var.get()

        # Получаем выбранные отображаемые имена
        selected_roll_display = self.roll_template_var.get()
        selected_box_display = self.box_template_var.get()

        # Загружаем список всех шаблонов
        templates_data = self.config_manager.load_json_settings("templates_list.json")
        roll_templates = templates_data.get("roll_templates", {})
        box_templates = templates_data.get("box_templates", {})

        # Получаем имена файлов
        roll_filename = roll_templates.get(selected_roll_display, "roll.pdf")
        box_filename = box_templates.get(selected_box_display, "box.pdf")

        # Сохраняем в настройки
        settings = self.config_manager.load_json_settings("shared_utils.json")
        settings[f"selected_roll_template_{workshop}"] = roll_filename
        settings[f"selected_box_template_{workshop}"] = box_filename
        self.config_manager.save_json_settings("shared_utils.json", settings)

        if self.coordinator:
            self.coordinator.notify_subscribers()

        self.show_message(f"✅ Шаблоны для {workshop} цеха сохранены", "green")

    def _on_qr_toggled(self):
        """Обработчик изменения галочки QR-кода"""
        if self.coordinator is not None:
            self.coordinator.notify_subscribers()
        
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

    # noinspection PyUnusedLocal
    def clear_message_after_delay(self, delay_ms=5000):
        """Очищает сообщение через указанное время"""
        if self.message_status_var is not None:
            self.message_status_var.set("")

    def show_message(self, message, color="blue"):
        """Показывает сообщение в строке статуса и очищает через 5 секунд"""
        if self.message_status_var is not None:
            self.message_status_var.set(message)
            # Настраиваем цвет
            if color == "blue":
                self.message_status_label.configure(foreground="blue")
            elif color == "red":
                self.message_status_label.configure(foreground="red")
            elif color == "green":
                self.message_status_label.configure(foreground="green")
            elif color == "orange":
                self.message_status_label.configure(foreground="orange")
            
            # Очищаем через 5 секунд
            self.main_frame.after(5000, self.clear_message_after_delay)
        
    def open_weight_orders_window(self):
        """Открывает окно для работы с втулками"""
        # Проверяем, есть ли уже открытое окно
        if self.weight_orders_window is not None and self.weight_orders_window.winfo_exists():
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

    @property
    def save_settings(self):
        """Сохраняет настройки этой вкладки"""
        try:
            # Сохраняем настройки печати
            print_settings = {
                "printer_roll": self.printer_roll_var.get(),
                "printer_box": self.printer_box_var.get()
            }

            all_settings = self.config_manager.load_json_settings("print_settings.json")
            all_settings["weight_box_print"] = print_settings
            self.config_manager.save_json_settings("print_settings.json", all_settings)

            # Сохраняем остальные настройки
            shared_settings = self.config_manager.load_json_settings("shared_utils.json")

            # Путь к файлу журнала упаковки
            shared_settings["packaging_log_file"] = self.packaging_log_file

            # Номер заказа
            shared_settings["order_number"] = {
                "prefix": self.settings_prefix_var.get().strip(),
                "suffix": self.settings_suffix_var.get().strip()
            }

            # Статус архивации
            shared_settings["archive_status"] = self.archive_status_var.get()

            # Дополнительные элементы
            shared_settings["elements_status"] = self.elements_status_var.get()
            shared_settings["qr_data"] = self.qr_var.get()

            # Номер цеха
            workshop = self.workshop_var.get()
            shared_settings["workshop"] = workshop
            self.coordinator.set_workshop(workshop)

            # === ДОБАВЛЯЕМ СОХРАНЕНИЕ ПУТЕЙ ===
            shared_settings["weight_data_base"] = self.xml_folder_path.get()
            if self.excel_folder_path:
                shared_settings["weight_orders_xlsx"] = self.excel_folder_path

            # Сохраняем все изменения
            self.config_manager.save_json_settings("shared_utils.json", shared_settings)

            self.coordinator.refresh_archive_status()
            self.coordinator.notify_subscribers()

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
        if self.status_callback is not None:
            self.status_callback(message, color)

    def load_folder_paths(self):
        """Загружает пути к папкам из настроек для отображения"""
        try:
            settings = self.config_manager.load_json_settings("shared_utils.json")

            # Путь для XML - если есть в настройках, используем его, иначе data_dir (как строку)
            xml_path = settings.get("weight_data_base", "")
            if not xml_path:
                xml_path = str(self.config_manager.data_dir)  # конвертируем Path в строку
            self.xml_folder_path.set(xml_path)

            # Путь для Excel - если есть в настройках, используем его, иначе data_dir
            excel_path = settings.get("weight_orders_xlsx", "")
            if not excel_path:
                excel_path = str(self.config_manager.data_dir)
            self.excel_folder_path = excel_path

            self.update_folder_status()

        except Exception as e:
            print(f"Ошибка чтения shared_utils.json: {e}")
            self.xml_folder_path.set(str(self.config_manager.data_dir))
            self.excel_folder_path = str(self.config_manager.data_dir)

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
            if self.coordinator is not None:
                self.coordinator.notify_subscribers()

    def save_excel_folder_path(self):
        """Сохраняет путь к папке с Excel файлом в настройки"""
        try:
            settings = self.config_manager.load_json_settings("shared_utils.json")
            settings["weight_orders_xlsx"] = self.excel_folder_path
            self.config_manager.save_json_settings("shared_utils.json", settings)
            
            # Можно добавить нотификацию
            if self.coordinator is not None:
                self.coordinator.notify_subscribers()
                
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

    def select_excel_folder(self):
        """Выбирает папку для Excel файла"""
        folder_path = filedialog.askdirectory(title="Выберите папку для файла Excel")
        if not folder_path:
            return
        
        try:
            # Копируем все файлы Excel
            files_to_copy = [
                ("weight_orders.xlsx", "weight_orders.xlsx"),
                ("weight_orders_2.xlsx", "weight_orders_2.xlsx"),
                ("no_weight_orders.xlsx", "no_weight_orders.xlsx")
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
        