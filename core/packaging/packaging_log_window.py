# core/packaging/packaging_log_window.py
import os
import re
import tkinter as tk
from tkinter import ttk, StringVar, filedialog

from core.packaging.packaging_manager import PackagingManager


# noinspection PyTypeChecker
class PackagingLogWindow:
    """Окно журнала учёта упаковки"""
    
    def __init__(self, parent, config_manager, order_processor=None):
        self.packaging_log_file = None
        self.status_label = None
        self.entries = []
        self.tree = None
        self.window = None
        self.parent = parent
        self.config_manager = config_manager
        self.order_processor = order_processor
        
        # Переменные для полей поиска
        self.date_var = StringVar()
        self.order_var = StringVar()
        self.customer_var = StringVar()
        self.product_var = StringVar()
        
        # Менеджер
        self.manager = PackagingManager(config_manager)
        
        self.create_window()

    # noinspection SpellCheckingInspection
    def create_window(self):
        """Создаёт окно журнала упаковки"""
        self.window = tk.Toplevel(self.parent)
        self.window.title("📦 Журнал учёта упаковки")
        self.window.geometry("1400x700")
        self.window.minsize(1000, 500)

        # Делаем модальным
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

        # Панель поиска
        search_frame = ttk.LabelFrame(self.window, text="Поиск записей", padding=10)
        search_frame.pack(fill=tk.X, padx=10, pady=10)

        # Поля поиска в одну строку
        fields_frame = ttk.Frame(search_frame)
        fields_frame.pack(fill=tk.X, pady=(0, 10))

        # Дата
        ttk.Label(fields_frame, text="Дата:").grid(row=0, column=0, padx=(0, 5))
        date_entry = ttk.Entry(fields_frame, textvariable=self.date_var, width=10)
        date_entry.grid(row=0, column=1, padx=(0, 15))

        def format_date(event):
            """Форматирует дату при вводе: 22012026 -> 22.01.2026"""
            entry = event.widget
            text = entry.get().replace('.', '')  # убираем существующие точки

            if len(text) > 8:
                text = text[:8]

            formatted = ""
            for i, char in enumerate(text):
                if i in [2, 4]:  # после 2 и 4 символов добавляем точку
                    formatted += "."
                formatted += char

            entry.delete(0, tk.END)
            entry.insert(0, formatted)

        date_entry.bind("<KeyRelease>", format_date)
        date_entry.bind("<Return>", lambda e: self.search())
        date_entry.bind("<Control-KeyPress>", self.control_key_handler)

        # Номер заказа
        ttk.Label(fields_frame, text="№ заказа:").grid(row=0, column=2, padx=(0, 5))
        order_entry = ttk.Entry(fields_frame, textvariable=self.order_var, width=10)
        order_entry.grid(row=0, column=3, padx=(0, 15))
        order_entry.bind("<Return>", lambda e: self.search())
        order_entry.bind("<Control-KeyPress>", self.control_key_handler)

        # Заказчик
        ttk.Label(fields_frame, text="Заказчик:").grid(row=0, column=4, padx=(0, 5))
        customer_entry = ttk.Entry(fields_frame, textvariable=self.customer_var, width=40)
        customer_entry.grid(row=0, column=5, padx=(0, 15))
        customer_entry.bind("<Return>", lambda e: self.search())
        customer_entry.bind("<Control-KeyPress>", self.control_key_handler)

        # Наименование
        ttk.Label(fields_frame, text="Наименование:").grid(row=0, column=6, padx=(0, 5))
        product_entry = ttk.Entry(fields_frame, textvariable=self.product_var, width=40)
        product_entry.grid(row=0, column=7, padx=(0, 15))
        product_entry.bind("<Return>", lambda e: self.search())
        product_entry.bind("<Control-KeyPress>", self.control_key_handler)

        # Кнопки
        buttons_frame = ttk.Frame(search_frame)
        buttons_frame.pack(fill=tk.X)

        if self.config_manager:
            settings = self.config_manager.load_json_settings("shared_utils.json")
            self.packaging_log_file = settings.get("packaging_log_file", "")

        ttk.Button(
            buttons_frame,
            text="➕ Новая запись",
            command=self.add_new_entry,
            width=15
        ).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(
            buttons_frame,
            text="🗑️ Удалить",
            command=self.delete_selected,
            width=15
        ).pack(side=tk.LEFT)

        ttk.Button(
            buttons_frame,
            text="📥 Импорт из Excel",
            command=self.import_from_excel,
            width=18
        ).pack(side=tk.LEFT, padx=(10, 0))

        ttk.Button(
            buttons_frame,
            text="📤 Экспорт в Excel",
            command=self.export_to_excel,
            width=18
        ).pack(side=tk.LEFT, padx=(10, 0))

        # Статусная строка - теперь сверху
        status_frame = ttk.Frame(self.window, height=25)
        status_frame.pack(fill=tk.X, padx=10, pady=(10, 0))
        status_frame.pack_propagate(False)

        self.status_label = ttk.Label(
            status_frame,
            text="",
            anchor=tk.W
        )
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # Таблица
        table_frame = ttk.LabelFrame(self.window, text="Записи", padding=5)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # Создаём Treeview
        columns = (
            "date", "order_number", "customer", "product_name",
            "quantity_labels", "packer_name", "large_boxes", "small_boxes",
            "aquaLife_boxes", "note"
        )

        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            height=35,
            selectmode="browse"
        )
        # Настраиваем заголовки
        self.tree.heading("date", text="Дата")
        self.tree.heading("order_number", text="№ заказа")
        self.tree.heading("customer", text="Заказчик")
        self.tree.heading("product_name", text="Наименование")
        self.tree.heading("quantity_labels", text="Тираж")
        self.tree.heading("packer_name", text="Упаковщик")
        self.tree.heading("large_boxes", text="Боль")
        self.tree.heading("small_boxes", text="Мал")
        self.tree.heading("aquaLife_boxes", text="Aqua")
        self.tree.heading("note", text="Примечание")

        # Ширина колонок
        self.tree.column("date", width=70, anchor="center")
        self.tree.column("order_number", width=65, anchor="center")
        self.tree.column("customer", width=150, anchor="w")
        self.tree.column("product_name", width=200, anchor="w")
        self.tree.column("quantity_labels", width=70, anchor="center")
        self.tree.column("packer_name", width=80, anchor="w")
        self.tree.column("large_boxes", width=20, anchor="center")
        self.tree.column("small_boxes", width=20, anchor="center")
        self.tree.column("aquaLife_boxes", width=20, anchor="center")
        self.tree.column("note", width=50, anchor="w")

        # Скроллбар
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Привязка событий для редактирования
        self.tree.bind("<Double-Button-1>", self.on_double_click)

        # Загружаем последние записи
        self.load_recent()

    # noinspection SpellCheckingInspection
    def set_status(self, message, color="green"):
        """Устанавливает статусное сообщение с цветом и автоочисткой через 5 секунд"""
        self.status_label.config(text=message, foreground=color)
        self.status_label.update()  # принудительное обновление
        self.window.after(5000, lambda: self.status_label.config(text="", foreground="green"))

    def import_from_excel(self):
        """Импорт данных из Excel"""
        # Получаем путь из настроек
        settings = self.config_manager.load_json_settings("shared_utils.json")
        file_path = settings.get("packaging_log_file", "")

        # Если путь есть и файл существует - используем его без диалога
        if file_path and os.path.exists(file_path):
            self.set_status("⏳ Ожидайте, идёт импорт...")
            self.window.update()

            try:
                imported, errors = self.manager.import_from_excel(file_path)

                if imported > 0:
                    self.set_status(f"✅ Импортировано записей: {imported}. Ошибок: {len(errors)}", "green")
                    self.load_recent()
                else:
                    error_msg = "\n".join(errors) if errors else "Не удалось импортировать данные"
                    self.set_status(f"❌ {error_msg}", "red")
            except Exception as e:
                self.set_status(f"❌ Ошибка: {str(e)}", "red")
            return

        # Если нет - показываем диалог выбора
        file_path = filedialog.askopenfilename(
            title="Выберите файл для импорта",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
        )

        if not file_path:
            return

        try:
            self.set_status("⏳ Ожидайте, идёт импорт...")
            self.window.update()

            imported, errors = self.manager.import_from_excel(file_path)

            if imported > 0:
                self.set_status(f"✅ Импортировано записей: {imported}. Ошибок: {len(errors)}", "green")
                self.load_recent()
            else:
                error_msg = "\n".join(errors) if errors else "Не удалось импортировать данные"
                self.set_status(f"❌ {error_msg}", "red")

        except Exception as e:
            self.set_status(f"❌ Ошибка: {str(e)}", "red")

    def export_to_excel(self):
        """Экспорт новых записей в Excel"""
        # Получаем путь из настроек
        settings = self.config_manager.load_json_settings("shared_utils.json")
        file_path = settings.get("packaging_log_file", "")

        # Если путь есть и файл существует - используем его без диалога
        if file_path and os.path.exists(file_path):
            # Проверяем, не открыт ли файл
            try:
                with open(file_path, 'r+b'):
                    pass  # Файл доступен
            except (PermissionError, OSError):
                self.set_status("⚠️ Внимание: файл открыт в Exel, экспорт прерван", "orange")
                return

            self.set_status("⏳ Экспорт...")
            self.window.update()

            try:
                exported = self.manager.export_unexported_to_excel(file_path)

                if exported > 0:
                    self.set_status(f"✅ Экспортировано новых записей: {exported}", "green")
                    self.load_recent()
                else:
                    self.set_status("📭 Нет новых записей для экспорта", "blue")
            except Exception as e:
                self.set_status(f"❌ Ошибка: {str(e)}", "red")
            return

        # Если нет - показываем диалог выбора
        file_path = filedialog.askopenfilename(
            title="Выберите файл Excel для добавления записей",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
        )

        if not file_path:
            return

        try:
            self.set_status("⏳ Экспорт...")
            self.window.update()

            exported = self.manager.export_unexported_to_excel(file_path)

            if exported > 0:
                self.set_status(f"✅ Экспортировано новых записей: {exported}", "green")
                self.load_recent()
            else:
                self.set_status("📭 Нет новых записей для экспорта", "blue")

        except Exception as e:
            self.set_status(f"❌ Ошибка: {str(e)}", "red")

    def load_recent(self):
        """Загружает последние 10 записей"""
        try:
            self.entries = self.manager.get_recent_entries(20)
            self.refresh_table()
        except Exception as e:
            self.set_status(f"Ошибка загрузки: {str(e)}")

    def refresh_table(self):
        """Обновляет отображение таблицы"""
        # Очищаем
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Заполняем с чередованием цветов
        for i, entry in enumerate(self.entries):
            date_str = entry["date"]
            if date_str and len(date_str) == 10 and date_str[4] == '-':
                try:
                    parts = date_str.split('-')
                    date_str = f"{parts[2]}.{parts[1]}.{parts[0]}"
                except:
                    pass
            values = (
                date_str,
                entry["order_number"],
                entry["customer"],
                entry["product_name"],
                entry["quantity_labels"] if entry["quantity_labels"] else "",
                entry["packer_name"],
                entry["large_boxes"] if entry["large_boxes"] else "",
                entry["small_boxes"] if entry["small_boxes"] else "",
                entry["aquaLife_boxes"] if entry["aquaLife_boxes"] else "",
                entry["note"]
            )
            # Чётные строки - белые, нечётные - светло-серые
            if i % 2 == 0:
                self.tree.insert("", "end", values=values, iid=entry["id"], tags=('even',))
            else:
                self.tree.insert("", "end", values=values, iid=entry["id"], tags=('odd',))

        # Настраиваем цвета
        self.tree.tag_configure('even', background='white')
        self.tree.tag_configure('odd', background='#f0f0f0')

    def search(self):
        """Выполняет поиск по заполненным полям"""
        try:
            # Собираем только непустые поля
            filters = {}
            if self.date_var.get().strip():
                date_input = self.date_var.get().strip()
                # Преобразуем DD.MM.YYYY в YYYY-MM-DD для поиска в БД
                date_match = re.search(r'(\d{2})\.(\d{2})\.(\d{4})', date_input)
                if date_match:
                    day, month, year = date_match.groups()
                    filters["date"] = f"{year}-{month}-{day}"
                else:
                    filters["date"] = date_input

            if self.order_var.get().strip():
                order = self.order_var.get().strip()
                # Если введено 4 цифры, ищем частично
                if re.match(r'^\d{4}$', order):
                    filters["order_number"] = f"%{order}%"
                else:
                    filters["order_number"] = order

            if self.customer_var.get().strip():
                filters["customer"] = self.customer_var.get().strip()
            if self.product_var.get().strip():
                filters["product_name"] = self.product_var.get().strip()

            self.set_status("Поиск...")
            self.window.update()

            self.entries = self.manager.search_entries(**filters)
            self.refresh_table()

            count = len(self.entries)
            if count == 0:
                self.set_status("Ничего не найдено")
            else:
                self.set_status(f"Найдено записей: {count}")

        except Exception as e:
            self.set_status(f"Ошибка поиска: {str(e)}")

    def add_new_entry(self):
        """Добавляет новую запись с предзаполненными данными"""
        try:
            # Получаем данные из процессора, если есть
            if self.order_processor:
                defaults = self.order_processor.get_packaging_defaults()
            else:
                defaults = {
                    'date': '',
                    'order_number': '', 'customer': '', 'product_name': '',
                    'packer_name': '', 'quantity_labels': None,
                    'large_boxes': None, 'small_boxes': None,
                    'aquaLife_boxes': None, 'note': ''
                }

            # Сохраняем в БД
            entry_id = self.manager.add_entry(defaults)

            # Добавляем ID в словарь
            defaults['id'] = entry_id

            # Вставляем в начало списка
            self.entries.insert(0, defaults)
            self.refresh_table()

            # Выделяем новую строку
            self.tree.selection_set(entry_id)
            self.tree.focus(entry_id)
            self.tree.see(entry_id)

            self.set_status("✅ Новая запись добавлена")

        except Exception as e:
            self.set_status(f"❌ Ошибка: {str(e)}")
    
    def delete_selected(self):
        """Удаляет выбранную запись"""
        selection = self.tree.selection()
        if not selection:
            self.set_status("❌ Не выбрана запись для удаления")
            return
        
        entry_id = int(selection[0])
        
        # Находим запись для подтверждения
        entry = None
        for e in self.entries:
            if e["id"] == entry_id:
                entry = e
                break
        
        if not entry:
            return
        
        try:
            self.manager.delete_entry(entry_id)
            
            # Удаляем из списка
            self.entries = [e for e in self.entries if e["id"] != entry_id]
            
            # Обновляем таблицу
            self.refresh_table()
            self.set_status("✅ Запись удалена")
            
        except Exception as e:
            self.set_status(f"❌ Ошибка удаления: {str(e)}")
    
    def on_double_click(self, event):
        """Обрабатывает двойной клик по ячейке для редактирования"""
        region = self.tree.identify_region(event.x, event.y)
        if region != "cell":
            return
        
        column = self.tree.identify_column(event.x)
        item = self.tree.identify_row(event.y)
        
        if not item or not column:
            return
        
        # ID колонки (убираем #)
        col_index = int(column.replace("#", "")) - 1
        
        # Не редактируем колонку ID
        if col_index == 0:
            return
        
        # Получаем координаты ячейки
        x, y, width, height = self.tree.bbox(item, column)
        
        # Создаём Entry для редактирования
        entry = ttk.Entry(self.tree)
        entry.place(x=x, y=y, width=width, height=height)
        
        # Текущее значение
        current_value = self.tree.item(item, "values")[col_index]
        entry.insert(0, current_value)
        entry.select_range(0, tk.END)
        entry.focus()

        # noinspection PyUnusedLocal,PyShadowingNames
        def save_edit(event=None):
            new_value = entry.get().strip()
            entry.destroy()
            
            if new_value == current_value:
                return
            
            # Сохраняем в БД
            entry_id = int(item)
            column_name = self.tree["columns"][col_index]
            
            try:
                self.manager.update_cell(entry_id, column_name, new_value)
                
                # Обновляем в памяти
                for e in self.entries:
                    if e["id"] == entry_id:
                        e[column_name] = new_value
                        break
                
                # Обновляем в таблице
                values = list(self.tree.item(item, "values"))
                values[col_index] = new_value
                self.tree.item(item, values=values)
                
                self.set_status(f"✅ Ячейка обновлена")
                
            except Exception as e:
                self.set_status(f"❌ Ошибка сохранения: {str(e)}")
        
        entry.bind("<Return>", save_edit)
        entry.bind("<Control-KeyPress>", self.control_key_handler)
        entry.bind("<FocusOut>", save_edit)
        entry.bind("<Escape>", lambda e: entry.destroy())

    def control_key_handler(self, event):
        """Обработчик горячих клавиш для Entry полей"""
        if event.keycode in (86, 118):  # V key - вставка
            self.paste_text_to_entry(event.widget)
            return "break"
        elif event.keycode in (67, 99):  # C key - копирование
            self.copy_text_from_entry(event.widget)
            return "break"
        return None

    @staticmethod
    def copy_text_from_entry(widget):
        """Копирует текст из поля ввода Entry."""
        try:
            text = widget.get()
            if text:
                widget.clipboard_clear()
                widget.clipboard_append(text)
        except Exception as e:
            print(f"Ошибка копирования: {e}")

    @staticmethod
    def paste_text_to_entry(widget):
        """Вставляет текст в поле ввода Entry."""
        try:
            text = widget.clipboard_get()
            if text:
                widget.delete(0, tk.END)
                widget.insert(0, text)
        except Exception as e:
            print(f"Ошибка вставки: {e}")