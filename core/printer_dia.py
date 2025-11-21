import tkinter as tk
from tkinter import ttk, messagebox
import win32print
import win32ui
from core.config_manager import ConfigManager  # Добавляем импорт
from core.shared_utils import (
    mm_to_pixels,
    get_default_printer,
    create_printer_dc,
)  # Добавляем импорт


class SettingsDialog:
    """Диалог настроек"""

    def __init__(self, parent, main_app):
        self.parent = parent
        self.main_app = main_app
        self.window = None

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
        ttk.Label(print_frame, text="Принтер:").grid(row=0, column=0, sticky="w", pady=2)
        printers = win32print.EnumPrinters(2)
        self.printer_var = tk.StringVar(value=self.main_app.settings["printer"])
        printer_combo = ttk.Combobox(
            print_frame,
            textvariable=self.printer_var,
            values=[p[2] for p in printers],
            width=25,
        )
        printer_combo.grid(row=0, column=1, padx=5, pady=2, sticky="w")

        self.settings_vars = {}
            
        # Кнопка обновления принтеров
        update_printers_btn = ttk.Button(
            print_frame, text="🔄 Обновить принтеры", command=self.main_app.update_printers
        )
        update_printers_btn.grid(row=0, column=3, padx=10, pady=2, sticky="w")
        
        cutters_label = ttk.Label(print_frame, text="Список резчиков:")
        cutters_label.grid(row=1, column=3, sticky="nw", padx=10, pady=(10, 2))

        # Загружаем текущий список резчиков
        current_cutters = self.main_app.config_manager.get_cutters()
        self.cutter_entries = []

        # Создаем поля ввода для каждого резчика
        for i, cutter in enumerate(current_cutters):
            entry = ttk.Entry(print_frame, width=20)
            entry.insert(0, cutter)
            entry.grid(row=2+i, column=3, padx=10, pady=2, sticky="w")
            self.cutter_entries.append(entry)

        # Добавляем пустое поле для нового резчика
        new_entry = ttk.Entry(print_frame, width=20)
        new_entry.grid(row=2+len(current_cutters), column=3, padx=10, pady=2, sticky="w")
        self.cutter_entries.append(new_entry)

        # 2. РАЗДЕЛ: Производитель
        manufacturer_frame = ttk.LabelFrame(left_frame, text="Производитель", padding=10)
        manufacturer_frame.pack(fill=tk.X, pady=(0, 10))
        self.manufacturer_var = tk.StringVar(value=self.main_app.manufacturer)
        manufacturer_entry = ttk.Entry(manufacturer_frame, textvariable=self.manufacturer_var, width=30)
        manufacturer_entry.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        # Кнопка для открытия окна редактирования клиентов
        open_customers_btn = ttk.Button(
            manufacturer_frame,
            text="📝 Открыть список клиентов без Производителя",
            command=self.main_app.open_customers_editor,
            width=40
        )
        open_customers_btn.grid(row=0, column=2, padx=10, pady=5, sticky="w")

        # 3. РАЗДЕЛ: Номер заказа
        order_frame = ttk.LabelFrame(left_frame, text="Номер заказа", padding=10)
        order_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(order_frame, text="Префикс:").grid(row=0, column=0, sticky="w", pady=5)
        self.settings_prefix_var = tk.StringVar(value=self.main_app.order_prefix.get())
        prefix_entry = ttk.Entry(order_frame, textvariable=self.settings_prefix_var, width=10)
        prefix_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(order_frame, text="Суффикс:").grid(row=0, column=2, sticky="w", pady=5)
        self.settings_suffix_var = tk.StringVar(value=self.main_app.order_suffix.get())
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

        # Привязка Enter к сохранению
        self.window.bind("<Return>", lambda e: self.save_all_settings())

    def save_all_settings(self):
        """Сохраняет все настройки из единого окна (БЕЗ списка клиентов)"""
        try:
            self.main_app.settings["printer"] = self.printer_var.get()
            
            # Сохраняем настройки печати
            all_settings = self.main_app.config_manager.load_json_settings(self.main_app.settings_file)
            all_settings["weight_box_print"] = self.main_app.settings
            self.main_app.config_manager.save_json_settings(self.main_app.settings_file, all_settings)

            # 2. Сохраняем производителя
            new_manufacturer = self.manufacturer_var.get().strip()
            if new_manufacturer:
                self.main_app.config_manager.save_manufacturer(new_manufacturer)
                self.main_app.manufacturer = new_manufacturer

            # 3. Сохраняем настройки номера заказа
            shared_settings = self.main_app.config_manager.load_json_settings("shared_utils.json")
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

            # Сохраняем все изменения в shared_utils.json
            self.main_app.config_manager.save_json_settings("shared_utils.json", shared_settings)

            # Обновляем текущие значения
            self.main_app.order_prefix.set(shared_settings["order_number"]["prefix"])
            self.main_app.order_suffix.set(shared_settings["order_number"]["suffix"])

            # Обновляем кнопки резчиков в интерфейсе
            if hasattr(self.main_app, 'update_cutters_menu'):
                self.main_app.update_cutters_menu()

            messagebox.showinfo("Сохранено", "Все настройки успешно сохранены!")
            
            if self.window:
                self.window.destroy()
                self.window = None

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить настройки:\n{str(e)}")


class CustomersEditorDialog:
    """Диалог редактирования списка клиентов без производителя"""

    def __init__(self, parent, main_app):
        self.parent = parent
        self.main_app = main_app
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
        current_customers = self.main_app.config_manager.get_without_manufacturer_customers()

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
            settings = self.main_app.config_manager.load_json_settings("shared_utils.json")
            
            # Обновляем список клиентов без производителя
            settings["without_manufacturer"] = new_customers

            # Сохраняем обратно в файл
            if self.main_app.config_manager.save_json_settings("shared_utils.json", settings):
                messagebox.showinfo(
                    "Сохранено", "Список клиентов успешно обновлен!"
                )

                if self.window:
                    self.window.destroy()
                    self.window = None
            else:
                messagebox.showerror(
                    "Ошибка", "Не удалось сохранить список клиентов"
                )

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при сохранении: {str(e)}")


class SpecialClientsEditorDialog:
    """Диалог редактирования списка особых клиентов"""

    def __init__(self, parent, main_app):
        self.parent = parent
        self.main_app = main_app
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
        current_special_clients = self.main_app.config_manager.get_special_clients()

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
            settings = self.main_app.config_manager.load_json_settings("shared_utils.json")

            # Обновляем список особых клиентов
            settings["special_clients"] = new_special_clients

            # Сохраняем обратно в файл
            if self.main_app.config_manager.save_json_settings("shared_utils.json", settings):
                messagebox.showinfo(
                    "Сохранено", "Список особых клиентов успешно обновлен!"
                )

                if self.window:
                    self.window.destroy()
                    self.window = None
            else:
                messagebox.showerror(
                    "Ошибка", "Не удалось сохранить список особых клиентов"
                )

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при сохранении: {str(e)}")