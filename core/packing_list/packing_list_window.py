# core/packing_list/packing_list_window.py

import os
import tkinter as tk
from tkinter import ttk, StringVar

from core.packing_list.packing_list_excel import PackingListExcel
from core.packing_list import packing_list_mapping as mapping


# noinspection PyTypeChecker
class PackingListWindow:
    """Окно упаковочного листа Экосистема"""

    def __init__(self, parent, config_manager, coordinator=None):
        self.parent = parent
        self.config_manager = config_manager
        self.coordinator = coordinator
        self.current_workshop = coordinator.get_workshop() if coordinator else "1"

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

        self.create_window()
        self._init_empty_data()
        self._load_defaults()

    def _load_defaults(self):
        """Загружает значения по умолчанию из настроек или координатора"""
        # Поставщик — можно взять из настроек
        self.supplier_var.set('Общество с ограниченной ответственностью "НПО Экосистема"')

    def _init_empty_data(self):
        """Инициализирует пустые данные для таблиц (5 строк)"""
        # Таблица мест
        self.places_data = []
        for i in range(5):
            self.places_data.append({
                "place_number": str(i + 1),
                "net_weight": "",
                "gross_weight": "",
                "length": "",
                "width": "",
                "height": "",
                "storage_type": "",
            })

        # Таблица товаров
        self.items_data = []
        for i in range(5):
            self.items_data.append({
                "item_number": str(i + 1),
                "order_request": "",
                "article_vn": "",
                "name": "",
                "unit": "",
                "quantity": "",
                "article_vn_product": "",
                "product": "",
            })

    def create_window(self):
        """Создаёт окно упаковочного листа"""
        self.window = tk.Toplevel(self.parent)
        self.window.title("📋 Упаковочный лист Экосистема")
        self.window.geometry("1400x900")
        self.window.minsize(1200, 700)

        self.window.transient(self.parent)
        self.window.grab_set()

        # Центрирование
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"+{x}+{y}")
        self.window.bind("<Escape>", lambda e: self.window.destroy())

        # Основной контейнер с прокруткой
        canvas = tk.Canvas(self.window)
        scrollbar = ttk.Scrollbar(self.window, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # === Шапка ===
        header_frame = ttk.LabelFrame(scrollable_frame, text="Данные упаковочного листа", padding=10)
        header_frame.pack(fill=tk.X, padx=10, pady=10)

        # Сетка для полей шапки
        fields = [
            ("Номер листа:", self.list_number_var),
            ("Поставщик:", self.supplier_var),
            ("Заказчик:", self.customer_var),
            ("Грузополучатель:", self.consignee_var),
            ("Договор:", self.contract_var),
            ("Проект:", self.project_var),
            ("Наименование оборудования:", self.equipment_name_var),
        ]

        for i, (label_text, var) in enumerate(fields):
            row = i // 2
            col = (i % 2) * 2

            ttk.Label(header_frame, text=label_text, width=22, anchor="e").grid(
                row=row, column=col, padx=(0, 5), pady=5, sticky="e"
            )
            entry = ttk.Entry(header_frame, textvariable=var, width=50)
            entry.grid(row=row, column=col + 1, padx=(0, 20), pady=5, sticky="w")
            entry.bind("<Control-KeyPress>", self.control_key_handler)

        # Кнопки управления
        buttons_frame = ttk.Frame(header_frame)
        buttons_frame.grid(row=4, column=0, columnspan=4, pady=(15, 5))

        ttk.Button(
            buttons_frame,
            text="📄 Обновить Excel",
            command=self.export_to_excel,
            width=18
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            buttons_frame,
            text="🖨️ Распечатать лист",
            command=self.print_sheet,
            width=18
        ).pack(side=tk.LEFT, padx=5)

        # === Таблица 1: Места ===
        places_frame = ttk.LabelFrame(scrollable_frame, text="Грузовые места (5 строк)", padding=10)
        places_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        self._create_places_table(places_frame)

        # === Таблица 2: Товары ===
        items_frame = ttk.LabelFrame(scrollable_frame, text="В грузовом месте находятся (5 строк)", padding=10)
        items_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        self._create_items_table(items_frame)

        # === Статусная строка ===
        status_frame = ttk.Frame(scrollable_frame, height=25)
        status_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.status_label = ttk.Label(
            status_frame,
            text="",
            anchor=tk.W,
            font=("Segoe UI", 10)
        )
        self.status_label.pack(fill=tk.X)

        # Заполняем таблицы данными
        self._refresh_places_table()
        self._refresh_items_table()

        self.window.protocol("WM_DELETE_WINDOW", self.on_close)

    def _create_places_table(self, parent):
        """Создаёт таблицу мест"""
        columns = list(mapping.PLACES_COLUMNS.keys())
        display_columns = [mapping.PLACES_COLUMNS[f]["header"] for f in columns]

        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        self.places_tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            height=5,
            selectmode="browse"
        )

        # Настройка колонок
        widths = [80, 80, 80, 80, 80, 80, 150]  # примерные ширины
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

    def _create_items_table(self, parent):
        """Создаёт таблицу товаров"""
        columns = list(mapping.ITEMS_COLUMNS.keys())
        display_columns = [mapping.ITEMS_COLUMNS[f]["header"] for f in columns]

        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        self.items_tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            height=5,
            selectmode="browse"
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

    def _refresh_places_table(self):
        """Обновляет таблицу мест"""
        for item in self.places_tree.get_children():
            self.places_tree.delete(item)

        for i, place in enumerate(self.places_data):
            values = [place.get(field, "") or " " for field in mapping.PLACES_COLUMNS.keys()]
            self.places_tree.insert("", "end", iid=str(i), values=values)

    def _refresh_items_table(self):
        """Обновляет таблицу товаров"""
        for item in self.items_tree.get_children():
            self.items_tree.delete(item)

        for i, item in enumerate(self.items_data):
            values = [item.get(field, "") or " " for field in mapping.ITEMS_COLUMNS.keys()]
            self.items_tree.insert("", "end", iid=str(i), values=values)

    def _edit_tree_cell(self, tree, data_list, columns_dict, refresh_callback, event):
        """Универсальный метод редактирования ячейки Treeview"""
        region = tree.identify_region(event.x, event.y)
        if region != "cell":
            return

        column = tree.identify_column(event.x)
        item = tree.identify_row(event.y)

        if not item or not column:
            return

        col_index = int(column.replace("#", "")) - 1
        fields = list(columns_dict.keys())
        field_name = fields[col_index]

        # item — это наш iid (индекс строки)
        row_index = int(item)

        # Координаты ячейки
        x, y, width, height = tree.bbox(item, column)

        # Создаём Entry
        entry = ttk.Entry(tree)
        entry.place(x=x, y=y, width=width, height=height)

        current_value = data_list[row_index].get(field_name, "")
        entry.insert(0, str(current_value) if current_value else "")
        entry.select_range(0, tk.END)
        entry.focus()

        def save_edit(_=None):
            new_value = entry.get().strip()
            entry.destroy()

            if new_value != str(current_value):
                data_list[row_index][field_name] = new_value
                refresh_callback()

        entry.bind("<Return>", save_edit)
        entry.bind("<Control-KeyPress>", self.control_key_handler)
        entry.bind("<FocusOut>", save_edit)
        entry.bind("<Escape>", lambda e: entry.destroy())

    def on_place_double_click(self, event):
        """Редактирование ячейки в таблице мест"""
        self._edit_tree_cell(self.places_tree, self.places_data, mapping.PLACES_COLUMNS,
                             self._refresh_places_table, event)

    def on_item_double_click(self, event):
        """Редактирование ячейки в таблице товаров"""
        self._edit_tree_cell(self.items_tree, self.items_data, mapping.ITEMS_COLUMNS,
                             self._refresh_items_table, event)
        
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
            "equipment_name": self.equipment_name_var.get(),
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
        try:
            # Сначала экспортируем
            work_path = self.config_manager.create_ecosystem_list_work_copy()

            header_data = self._collect_header_data()

            PackingListExcel.fill_template(
                work_path,
                header_data,
                self.places_data,
                self.items_data
            )

            # Отправляем на печать
            os.startfile(work_path, "print")
            self.set_status("🖨️ Документ отправлен на печать", "green")

        except Exception as e:
            self.set_status(f"❌ Ошибка печати: {str(e)}", "red")

    def set_status(self, message, color="green"):
        """Устанавливает статусное сообщение"""
        self.status_label.config(text=message, foreground=color)
        self.window.after(5000, lambda: self.status_label.config(text=""))

    def on_close(self):
        """Закрытие окна"""
        self.window.destroy()