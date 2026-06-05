# core/packing_list/packing_list_window.py

import threading
import time
import tkinter as tk
from tkinter import ttk, StringVar

import pythoncom
import win32com.client
import win32print

from core.packing_list import packing_list_mapping as mapping
from core.packing_list.packing_list_excel import PackingListExcel
from core.archive.archive_manager import ArchiveManager


# noinspection PyTypeChecker
class PackingListWindow:
    """Окно упаковочного листа Экосистема"""

    def __init__(self, parent, config_manager, coordinator=None):
        self.equipment_text = None
        self.parent = parent
        self.config_manager = config_manager
        self.coordinator = coordinator
        self.current_workshop = coordinator.get_workshop() if coordinator else "1"
        self.archive_manager = ArchiveManager(config_manager, coordinator)

        # Переменные для шапки
        self.list_number_var = StringVar()
        self.supplier_var = StringVar()
        self.customer_var = StringVar()
        self.consignee_var = StringVar()
        self.contract_var = StringVar()
        self.project_var = StringVar()
        self.equipment_name_var = StringVar()

        # Данные таблиц
        self.places_data = []  # список словарей для таблицы мест
        self.items_data = []   # список словарей для таблицы товаров

        # Виджеты
        self.window = None
        self.places_tree = None
        self.items_tree = None
        self.status_label = None

        # Настройки печати
        self.settings_file = "print_settings.json"
        self.default_settings = {
            "printer": self._get_default_printer(),
        }
        self.settings = self.default_settings.copy()
        self.load_settings("packing_list")
        self.printer_var = tk.StringVar(value=self.settings.get("printer", ""))
        self.copies_var = tk.IntVar(value=1)
        self._init_empty_data()
        self.create_window()
        self._load_defaults()

    def fill_from_xml(self, data: dict):
        self.supplier_var.set(data.get("supplier", ""))
        self.customer_var.set(data.get("customer", ""))
        self.consignee_var.set(data.get("consignee", ""))
        self.contract_var.set(data.get("contract", ""))
        self.project_var.set(data.get("project", ""))

        equipment_name = data.get("equipment_name", "")
        if self.equipment_text:
            self.equipment_text.delete("1.0", tk.END)
            self.equipment_text.insert("1.0", equipment_name)
        self.equipment_name_var.set(equipment_name)

    @staticmethod
    def _get_default_printer():
        """Возвращает принтер по умолчанию"""
        try:
            import win32print
            return win32print.GetDefaultPrinter()
        except:
            return ""

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
        """Сохраняет настройки печати"""
        try:
            all_settings = self.config_manager.load_json_settings(self.settings_file)
            all_settings["packing_list"] = self.settings
            self.config_manager.save_json_settings(self.settings_file, all_settings)
        except Exception as e:
            print(f"Ошибка сохранения настроек печати: {e}")

    @staticmethod
    def _get_system_printers():
        """Получает список системных принтеров"""
        try:
            import win32print
            printers = win32print.EnumPrinters(2)
            return [p[2] for p in printers]
        except Exception as e:
            print(f"Ошибка получения принтеров: {e}")
            return []

    def _load_defaults(self):
        """Загружает значения по умолчанию из настроек или координатора"""
        # Поставщик — можно взять из настроек
        self.supplier_var.set('ООО "НПО Экосистема"')

    def create_window(self):
        """Создаёт окно упаковочного листа"""
        self.window = tk.Toplevel(self.parent)
        self.window.title("📋 Упаковочный лист Экосистема")
        self.window.geometry("1400x900")
        self.window.minsize(1200, 700)

        self.window.transient(self.parent)
        # self.window.grab_set()

        # Центрирование
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"+{x}+{y}")
        self.window.bind("<Escape>", lambda e: self.window.destroy())

        # Основной контейнер БЕЗ прокрутки
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # === Шапка ===
        header_frame = ttk.LabelFrame(main_frame, text="Данные упаковочного листа", padding=10)
        header_frame.pack(fill=tk.X, padx=10, pady=10)

        # Поля в левой колонке (друг под другом)
        fields = [
            ("Номер листа:", self.list_number_var),
            ("Поставщик:", self.supplier_var),
            ("Заказчик:", self.customer_var),
            ("Грузополучатель:", self.consignee_var),
            ("Договор:", self.contract_var),
            ("Проект:", self.project_var),
        ]

        for i, (label_text, var) in enumerate(fields):
            ttk.Label(header_frame, text=label_text, width=22, anchor="w").grid(
                row=i, column=0, padx=(0, 5), pady=5, sticky="w"
            )
            entry = ttk.Entry(header_frame, textvariable=var, width=40)
            entry.grid(row=i, column=1, padx=(0, 5), pady=5, sticky="w")
            entry.bind("<Control-KeyPress>", self.control_key_handler)

        # Многострочное поле "Наименование оборудования"
        ttk.Label(header_frame, text="Наименование единицы\nОборудования по Договору:", width=25, anchor="w").grid(
            row=len(fields), column=0, padx=(0, 5), pady=5, sticky="ne"
        )
        equipment_text = tk.Text(header_frame, height=2, width=50)
        equipment_text.grid(row=len(fields), column=1, padx=(0, 20), pady=5, sticky="w")
        equipment_text.insert("1.0", self.equipment_name_var.get())
        equipment_text.bind("<Control-KeyPress>", self.control_key_handler_text)
        self.equipment_text = equipment_text

        # Кнопки в правой колонке
        buttons_frame = ttk.Frame(header_frame)
        buttons_frame.grid(row=0, column=2, rowspan=len(fields)+1, padx=(5, 0), sticky="n")

        ttk.Button(
            buttons_frame,
            text="🔄 Обновить Excel",
            command=self.export_to_excel,
            width=16
        ).pack(pady=(0, 20))

        ttk.Button(
            buttons_frame,
            text="🖨 Распечатать",
            command=self.print_sheet,
            width=16
        ).pack()

        # Выбор принтера
        printer_frame = ttk.Frame(buttons_frame)
        printer_frame.pack(pady=20, fill=tk.X)

        ttk.Label(printer_frame, text="Принтер:").grid(row=0, column=0, padx=(0, 5), sticky="w")

        system_printers = self._get_system_printers()
        printer_values = [""] + system_printers

        printer_combo = ttk.Combobox(
            printer_frame,
            textvariable=self.printer_var,
            values=printer_values,
            state="readonly",
            width=25
        )
        printer_combo.grid(row=0, column=1, sticky="w")
        printer_combo.bind('<<ComboboxSelected>>', self._on_printer_selected)

        # Количество копий
        copies_frame = ttk.Frame(buttons_frame)
        copies_frame.pack(pady=(0, 10), fill=tk.X)

        ttk.Label(copies_frame, text="Копий:").pack(side=tk.LEFT)

        ttk.Spinbox(
            copies_frame,
            from_=1,
            to=10,
            textvariable=self.copies_var,
            width=5
        ).pack(side=tk.LEFT, padx=(5, 0))

        ttk.Button(
            buttons_frame,
            text="📦 В архив",
            command=self.add_to_archive,
            width=16
        ).pack(pady=(10, 0))

        # === Таблица 1: Места ===
        places_frame = ttk.LabelFrame(main_frame, text="Грузовые места", padding=10)
        places_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        self._create_places_table(places_frame)

        # === Таблица 2: Товары ===
        items_frame = ttk.LabelFrame(main_frame, text="В грузовом месте находятся", padding=10)
        items_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        self._create_items_table(items_frame)

        # === Статусная строка ===
        status_frame = ttk.Frame(main_frame, height=25)
        status_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.status_label = ttk.Label(
            status_frame,
            text="",
            anchor=tk.W,
            font=("Segoe UI", 10)
        )
        self.status_label.pack(fill=tk.X)

        self.window.protocol("WM_DELETE_WINDOW", self.on_close)

    def _create_places_table(self, parent):
        """Создаёт таблицу мест"""
        columns = list(mapping.PLACES_COLUMNS.keys())
        display_columns = [mapping.PLACES_COLUMNS[f]["header"] for f in columns]

        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        # Настройка стилей для таблиц
        style = ttk.Style()
        style.configure("PackingList.Treeview", rowheight=35)
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), padding=(0, 10))

        self.places_tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            height=5,
            selectmode="browse",
            style="PackingList.Treeview"
        )

        # Настройка колонок
        widths = [80, 80, 80, 80, 80, 80, 150]
        for i, (field, header) in enumerate(zip(columns, display_columns)):
            self.places_tree.heading(field, text=header)
            self.places_tree.column(field, width=widths[i] if i < len(widths) else 100, anchor="center")

        # Скроллбар
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.places_tree.yview)
        self.places_tree.configure(yscrollcommand=scrollbar.set)

        self.places_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Привязка событий
        self.places_tree.bind("<Double-Button-1>", self.on_place_double_click)

        # СРАЗУ ЗАПОЛНЯЕМ ДАННЫМИ
        self._refresh_places_table()

    def _create_items_table(self, parent):
        """Создаёт таблицу товаров"""
        columns = list(mapping.ITEMS_COLUMNS.keys())
        display_columns = [mapping.ITEMS_COLUMNS[f]["header"] for f in columns]

        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        # Настройка стилей для таблиц
        style = ttk.Style()
        style.configure("PackingList.Treeview", rowheight=35)
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), padding=(0, 10))

        self.items_tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            height=5,
            selectmode="browse",
            style="PackingList.Treeview"
        )

        # Настройка колонок
        widths = [50, 140, 120, 250, 80, 80, 140, 200]
        for i, (field, header) in enumerate(zip(columns, display_columns)):
            self.items_tree.heading(field, text=header)
            self.items_tree.column(field, width=widths[i] if i < len(widths) else 100, anchor="center")

        # Скроллбар
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.items_tree.yview)
        self.items_tree.configure(yscrollcommand=scrollbar.set)

        self.items_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Привязка событий
        self.items_tree.bind("<Double-Button-1>", self.on_item_double_click)

        # СРАЗУ ЗАПОЛНЯЕМ ДАННЫМИ
        self._refresh_items_table()

    def add_item_row(self, item_data: dict):
        """Добавляет новую строку в таблицу товаров"""
        # Ищем первую пустую строку
        for i, row in enumerate(self.items_data):
            if row.get('item_number') == " ":
                self.items_data[i] = {
                    "item_number": str(i + 1),
                    "order_request": item_data.get("order_request", ""),
                    "article_vn": item_data.get("article_vn", ""),
                    "name": item_data.get("name", ""),
                    "unit": item_data.get("unit", ""),
                    "quantity": item_data.get("quantity", "0"),
                    "article_vn_product": item_data.get("article_vn_product", ""),
                    "product": item_data.get("product", ""),
                }
                self._refresh_items_table()
                self.set_status(f"✅ Добавлен товар: {item_data.get('name', '')}", "green")
                return
        self.set_status("❌ Все строки таблицы товаров заняты", "red")

    def add_place_row(self, place_data: dict):
        """Добавляет новую строку в таблицу мест"""
        # Ищем первую пустую строку
        for i, row in enumerate(self.places_data):
            if row.get('place_number') == " ":
                self.places_data[i] = {
                    "place_number": str(i + 1),
                    "net_weight": place_data.get("net_weight", "0"),
                    "gross_weight": place_data.get("gross_weight", "0"),
                    "length": place_data.get("length", "0"),
                    "width": place_data.get("width", "0"),
                    "height": place_data.get("height", "0"),
                    "storage_type": place_data.get("storage_type", " "),
                }
                self._refresh_places_table()
                self.set_status(f"✅ Добавлено место №{i + 1}", "green")
                return
        self.set_status("❌ Все строки таблицы мест заняты", "red")

    def add_to_archive(self):
        """Добавляет текущий упаковочный лист в архив"""
        try:
            # Создаём/обновляем Excel с текущими данными
            work_path = self.config_manager.create_ecosystem_list_work_copy()
            header_data = self._collect_header_data()

            PackingListExcel.fill_template(
                work_path,
                header_data,
                self.places_data,
                self.items_data
            )

            # Архивируем этот же файл
            self.set_status("⏳ Добавление в архив...", "blue")

            result = self.archive_manager.archive_ecosystem_sheet(work_path)

            if result.get("success"):
                self.set_status(f"✅ {result.get('message')}", "green")
            else:
                self.set_status(f"❌ {result.get('error')}", "red")

        except Exception as e:
            self.set_status(f"❌ Ошибка: {str(e)}", "red")

    # noinspection PyUnusedLocal
    def _on_printer_selected(self, event=None):
        """Сохраняет выбранный принтер"""
        self.settings["printer"] = self.printer_var.get()
        self.save_settings()

    def control_key_handler_text(self, event):
        """Обработчик горячих клавиш для Text виджетов"""
        if event.keycode in (86, 118):  # Ctrl+V
            self.paste_text_to_text_widget(event.widget)
            return "break"
        elif event.keycode in (67, 99):  # Ctrl+C
            self.copy_text_from_text_widget(event.widget)
            return "break"
        return None

    @staticmethod
    def copy_text_from_text_widget(widget):
        """Копирует текст из Text виджета"""
        try:
            text = widget.get("1.0", "end-1c")
            if text:
                widget.clipboard_clear()
                widget.clipboard_append(text)
        except Exception:
            pass

    @staticmethod
    def paste_text_to_text_widget(widget):
        """Вставляет текст в Text виджет"""
        try:
            text = widget.clipboard_get()
            if text:
                widget.delete("1.0", tk.END)
                widget.insert("1.0", text)
        except Exception:
            pass

    def _init_empty_data(self):
        """Инициализирует данные для таблиц с нулями вместо пустых строк"""
        # Таблица мест
        self.places_data = []
        for i in range(5):
            self.places_data.append({
                "place_number": " ",
                "net_weight": "0",
                "gross_weight": "0",
                "length": "0",
                "width": "0",
                "height": "0",
                "storage_type": " ",
            })

        # Таблица товаров
        self.items_data = []
        for i in range(5):
            self.items_data.append({
                "item_number": " ",
                "order_request": " ",
                "article_vn": " ",
                "name": " ",
                "unit": " ",
                "quantity": "0",
                "article_vn_product": " ",
                "product": " ",
            })

    def _refresh_places_table(self):
        """Обновляет таблицу мест — заменяет '0' на пробел для отображения"""

        for item in self.places_tree.get_children():
            self.places_tree.delete(item)

        for place in self.places_data:
            values = []
            for field in mapping.PLACES_COLUMNS.keys():
                val = place.get(field, " ")
                # Для отображения заменяем "0" на пробел
                if val == "0":
                    val = " "
                values.append(val)
            self.places_tree.insert("", "end", values=values)

    def _refresh_items_table(self):
        """Обновляет таблицу товаров — заменяет '0' на пробел для отображения"""
        for item in self.items_tree.get_children():
            self.items_tree.delete(item)

        for item_data in self.items_data:
            values = []
            for field in mapping.ITEMS_COLUMNS.keys():
                val = item_data.get(field, " ")
                # Для отображения заменяем "0" на пробел
                if val == "0":
                    val = " "
                values.append(val)
            self.items_tree.insert("", "end", values=values)

    def on_place_double_click(self, event):
        """Редактирование ячейки в таблице мест — как в syc_register_printer"""
        region = self.places_tree.identify_region(event.x, event.y)
        if region != "cell":
            return

        column = self.places_tree.identify_column(event.x)
        item = self.places_tree.identify_row(event.y)

        if not item or not column:
            return

        col_index = int(column.replace("#", "")) - 1
        fields = list(mapping.PLACES_COLUMNS.keys())
        field_name = fields[col_index]

        # Получаем индекс строки
        row_index = self.places_tree.index(item)

        # Координаты ячейки
        x, y, width, height = self.places_tree.bbox(item, column)

        # Создаём Entry
        entry = ttk.Entry(self.places_tree)
        entry.place(x=x, y=y, width=width, height=height)

        current_value = self.places_data[row_index].get(field_name, "")
        # Для отображения в Entry показываем пустую строку если значение "0"
        display_value = "" if current_value == "0" else str(current_value)
        entry.insert(0, display_value)
        entry.select_range(0, tk.END)
        entry.focus()

        def save_edit(_=None):
            new_value = entry.get().strip()
            entry.destroy()

            # Если пусто — сохраняем "0" для числовых полей, пробел для текстовых
            if not new_value:
                if field_name in ["net_weight", "gross_weight", "length", "width", "height"]:
                    new_value = "0"
                else:
                    new_value = " "

            if new_value != current_value:
                self.places_data[row_index][field_name] = new_value
                self._refresh_places_table()

        entry.bind("<Return>", save_edit)
        entry.bind("<FocusOut>", save_edit)
        entry.bind("<Escape>", lambda e: entry.destroy())

    def on_item_double_click(self, event):
        """Редактирование ячейки в таблице товаров — как в syc_register_printer"""
        region = self.items_tree.identify_region(event.x, event.y)
        if region != "cell":
            return

        column = self.items_tree.identify_column(event.x)
        item = self.items_tree.identify_row(event.y)

        if not item or not column:
            return

        col_index = int(column.replace("#", "")) - 1
        fields = list(mapping.ITEMS_COLUMNS.keys())
        field_name = fields[col_index]

        # Получаем индекс строки
        row_index = self.items_tree.index(item)

        # Координаты ячейки
        x, y, width, height = self.items_tree.bbox(item, column)

        # Создаём Entry
        entry = ttk.Entry(self.items_tree)
        entry.place(x=x, y=y, width=width, height=height)

        current_value = self.items_data[row_index].get(field_name, "")
        # Для отображения в Entry показываем пустую строку если значение "0"
        display_value = "" if current_value == "0" else str(current_value)
        entry.insert(0, display_value)
        entry.select_range(0, tk.END)
        entry.focus()

        def save_edit(_=None):
            new_value = entry.get().strip()
            entry.destroy()

            # Если пусто — сохраняем "0" для числовых полей, пробел для текстовых
            if not new_value:
                if field_name == "quantity":
                    new_value = "0"
                else:
                    new_value = " "

            if new_value != current_value:
                self.items_data[row_index][field_name] = new_value
                self._refresh_items_table()

        entry.bind("<Return>", save_edit)
        entry.bind("<FocusOut>", save_edit)
        entry.bind("<Escape>", lambda e: entry.destroy())

    @staticmethod
    def control_key_handler(event):
        """Обработчик горячих клавиш для Entry полей"""
        if event.keycode in (86, 118):  # Ctrl+V
            try:
                text = event.widget.clipboard_get()
                event.widget.delete(0, tk.END)
                event.widget.insert(0, text)
            except:
                pass
            return "break"
        elif event.keycode in (67, 99):  # Ctrl+C
            try:
                text = event.widget.get()
                if text:
                    event.widget.clipboard_clear()
                    event.widget.clipboard_append(text)
            except:
                pass
            return "break"
        return None

    def _collect_header_data(self):
        """Собирает данные шапки"""
        return {
            "list_number": self.list_number_var.get(),
            "supplier": self.supplier_var.get(),
            "customer": self.customer_var.get(),
            "consignee": self.consignee_var.get(),
            "contract": self.contract_var.get(),
            "project": self.project_var.get(),
            "equipment_name": self.equipment_text.get("1.0", tk.END).strip(),
        }

    def export_to_excel(self):
        """Экспорт данных в Excel"""
        try:
            self.set_status("⏳ Создание упаковочного листа...", "blue")

            # Создаём рабочую копию шаблона
            work_path = self.config_manager.create_ecosystem_list_work_copy()

            # Собираем данные
            header_data = self._collect_header_data()

            # Заполняем шаблон
            PackingListExcel.fill_template(
                work_path,
                header_data,
                self.places_data,
                self.items_data
            )

            self.set_status(f"✅ Упаковочный лист создан: {work_path}", "green")

        except Exception as e:
            self.set_status(f"❌ Ошибка: {str(e)}", "red")

    def print_sheet(self):
        """Печать упаковочного листа"""
        printer = self.printer_var.get().strip()

        if not printer:
            self.set_status("❌ Выберите принтер", "red")
            return

        try:
            self.set_status("⏳ Подготовка к печати...", "blue")

            work_path = self.config_manager.create_ecosystem_list_work_copy()
            header_data = self._collect_header_data()

            PackingListExcel.fill_template(
                work_path,
                header_data,
                self.places_data,
                self.items_data
            )

            thread = threading.Thread(
                target=self._print_excel,
                args=(work_path, printer, self.copies_var.get()),
                daemon=True
            )
            thread.start()

        except Exception as e:
            self.set_status(f"❌ Ошибка: {str(e)}", "red")

    def _print_excel(self, excel_path, printer_name, copies):
        """Печать Excel файла"""

        pythoncom.CoInitialize()
        excel = None
        wb = None
        original_printer = None

        try:
            original_printer = win32print.GetDefaultPrinter()
            win32print.SetDefaultPrinter(printer_name)
            time.sleep(0.5)

            excel = win32com.client.DispatchEx("Excel.Application")
            excel.Visible = False
            excel.DisplayAlerts = False

            wb = excel.Workbooks.Open(excel_path)
            ws = wb.Sheets(1)

            for i in range(copies):
                ws.PrintOut()
                if i < copies - 1:
                    time.sleep(0.3)

            self.window.after(0, lambda: self.set_status("✅ Печать завершена", "green"))

        except Exception:
            self.window.after(0, lambda: self.set_status(f"❌ Ошибка печати", "red"))

        finally:
            if original_printer:
                try:
                    win32print.SetDefaultPrinter(original_printer)
                except:
                    pass
            if wb:
                try:
                    wb.Close(SaveChanges=False)
                except:
                    pass
            if excel:
                try:
                    excel.Quit()
                except:
                    pass
            pythoncom.CoUninitialize()

    def set_status(self, message, color="green"):
        """Устанавливает статусное сообщение"""
        self.status_label.config(text=message, foreground=color)
        self.window.after(5000, lambda: self.status_label.config(text=""))

    def on_close(self):
        """Закрытие окна"""
        self.window.destroy()