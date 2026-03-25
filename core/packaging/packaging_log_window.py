# core/packaging/packaging_log_window.py
import os
import re
import time
import tkinter as tk
from tkinter import colorchooser
from tkinter import ttk, StringVar, filedialog

from core.packaging.packaging_manager import PackagingManager


# noinspection PyTypeChecker
class PackagingLogWindow:
    """Окно журнала учёта упаковки"""

    # Конфигурация колонок таблицы
    COLUMN_CONFIG = {
        "date": {"width": 88, "anchor": "center", "wrap": False},
        "order_number": {"width": 65, "anchor": "center", "wrap": False},
        "customer": {"width": 200, "anchor": "w", "wrap": True, "wrap_len": 18},
        "product_name": {"width": 250, "anchor": "w", "wrap": True, "wrap_len": 25},
        "quantity_labels": {"width": 65, "anchor": "center", "wrap": False},
        "packer_name": {"width": 80, "anchor": "center", "wrap": True, "wrap_len": 10},
        "note": {"width": 25, "anchor": "w", "wrap": False},
    }

    # Для col_* динамически
    DEFAULT_COL_CONFIG = {"width": 45, "anchor": "center", "wrap": False}
    
    def __init__(self, parent, config_manager, order_processor=None, coordinator=None):
        self.status_menu = None
        self.rare_button = None
        self.only_first_sheet_var = tk.BooleanVar(value=True)
        self.packaging_log_file = None
        self.status_label = None
        self.entries = []
        self.tree = None
        self.window = None
        self.parent = parent
        self.config_manager = config_manager
        self.order_processor = order_processor
        self.coordinator = coordinator
        # Получаем текущий цех и маппинг
        self.current_workshop = None
        self.current_mapping = None
        self._update_mapping()
        
        # Переменные для полей поиска
        self.date_var = StringVar()
        self.order_var = StringVar()
        self.customer_var = StringVar()
        self.product_var = StringVar()
        
        # Менеджер
        self.manager = PackagingManager(config_manager)
        
        self.create_window()
        if self.coordinator and hasattr(self.coordinator, 'subscribe'):
            self.coordinator.subscribe(self.on_settings_changed)

    def _get_column_config(self, field):
        """Возвращает конфигурацию для колонки"""
        if field.startswith("col_"):
            return self.COLUMN_CONFIG.get(field, self.DEFAULT_COL_CONFIG)
        return self.COLUMN_CONFIG.get(field, {"width": 85, "anchor": "center", "wrap": False})

    # noinspection PyUnusedLocal
    def on_settings_changed(self, context=None):
        """Обработчик изменений настроек от координатора"""
        workshop = self.coordinator.get_workshop()

        # Если цех изменился — обновляем маппинг и перестраиваем таблицу
        if self.current_workshop != workshop:
            self._update_mapping()
            self._rebuild_table_columns()  # пересоздаём колонки таблицы
            self.load_recent()  # перезагружаем данные

    def _update_mapping(self):
        from core.packaging.packaging_mapping import PACKAGING_MAPPINGS

        if self.coordinator:
            workshop = str(self.coordinator.get_workshop())  # "1" или "2"
        else:
            workshop = "1"

        self.current_workshop = workshop
        self.current_mapping = PACKAGING_MAPPINGS.get(workshop, PACKAGING_MAPPINGS["1"])

    # noinspection SpellCheckingInspection
    def create_window(self):
        """Создаёт окно журнала упаковки"""
        self.window = tk.Toplevel(self.parent)
        self.window.title("📦 Журнал учёта упаковки")
        self.window.geometry("1500x800")
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
            text="🔄 Обновить Excel",
            command=self.export_to_excel,
            width=17
        ).pack(side=tk.LEFT, padx=(10, 0))

        # Кнопка "Редкие функции"
        self.rare_button = ttk.Menubutton(
            buttons_frame,
            text="⚙️ Редкие функции",
            width=18
        )
        self.rare_button.pack(side=tk.LEFT, padx=(10, 0))

        # Создаем меню для редких функций
        rare_menu = tk.Menu(self.rare_button, tearoff=0, font=("Segoe UI", 15))
        self.rare_button.configure(menu=rare_menu)

        # Добавляем пункты в меню
        rare_menu.add_command(
            label="📥 Импорт из Excel",
            command=self.import_from_excel
        )

        # Подменю для импорта с галочкой
        import_submenu = tk.Menu(rare_menu, tearoff=0, font=("Segoe UI", 14))
        self.only_first_sheet_var = tk.BooleanVar(value=True)
        import_submenu.add_checkbutton(
            label="Только первый лист",
            variable=self.only_first_sheet_var
        )
        rare_menu.add_cascade(label="Настройки импорта", menu=import_submenu)

        rare_menu.add_separator()

        rare_menu.add_command(
            label="🗑️ Удалить электронный журнал",
            command=self.clear_database
        )

        rare_menu.add_command(
            label="🔄 Восстановить Excel журнал",
            command=self.restore_journal
        )

        rare_menu.add_command(
            label="🎨 Сбросить цвет выбранной строки",
            command=self.reset_row_color
        )

        ttk.Button(
            buttons_frame,
            text="🔍 Узнать о записи",
            command=self.check_selected_entry,
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
        # Контекстное меню для статусной строки
        self.status_menu = tk.Menu(self.window, tearoff=0)
        self.status_menu.add_command(label="Скопировать", command=self.copy_status_text)

        self.status_label.bind("<Button-3>", self.show_status_menu)

        # Таблица
        table_frame = ttk.LabelFrame(self.window, text="Записи", padding=5)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # Получаем маппинг
        self._update_mapping()

        # Строим колонки из display_names (только те, что нужно показывать)
        columns = list(self.current_mapping["display_names"].keys())

        style = ttk.Style()
        style.configure("PackagingLog.Treeview", rowheight=70)
        style.configure("Treeview.Heading", font=("Segoe UI", 11, "bold"), padding=(0, 20))
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
            style="PackagingLog.Treeview"
        )

        # Настраиваем заголовки и ширину колонок
        for field in columns:
            display_name = self._get_display_name(field)
            self.tree.heading(field, text=display_name)

            config = self._get_column_config(field)
            self.tree.column(field, width=config["width"], anchor=config["anchor"])

        # Скроллбар
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Привязка событий
        self.tree.bind("<Double-Button-1>", self.on_double_click)
        self.tree.bind("<Button-3>", self.on_right_click)

        # Загружаем последние записи
        self.load_recent()
        self.update_status_with_file_path()

    def _rebuild_table_columns(self):
        """Перестраивает колонки таблицы при смене цеха"""
        if not self.tree:
            return

        # Очищаем существующие колонки
        for col in self.tree["columns"]:
            self.tree.heading(col, text="")
            self.tree.column(col, width=0)

        # Получаем новые колонки из display_names
        new_columns = list(self.current_mapping["display_names"].keys())

        # Меняем колонки Treeview
        self.tree["columns"] = new_columns

        # Настраиваем каждую колонку
        for field in new_columns:
            display_name = self._get_display_name(field)
            self.tree.heading(field, text=display_name)

            config = self._get_column_config(field)
            self.tree.column(field, width=config["width"], anchor=config["anchor"])

    def _get_display_name(self, field):
        """Возвращает отображаемое имя поля для заголовка"""
        return self.current_mapping["display_names"].get(field, field)

    def show_status_menu(self, event):
        """Показывает контекстное меню для статусной строки"""
        self.status_menu.post(event.x_root, event.y_root)

    def copy_status_text(self):
        """Копирует текст статусной строки в буфер обмена"""
        text = self.status_label.cget("text")
        if text:
            self.window.clipboard_clear()
            self.window.clipboard_append(text)
            # Временное подтверждение
            original_text = text
            self.status_label.config(text=f"📋 Скопировано: {text}", foreground="green")
            self.window.after(2000, lambda: self.status_label.config(text=original_text, foreground="blue"))

    def check_selected_entry(self):
        """Выводит информацию о выделенной записи в понятном виде"""
        selection = self.tree.selection()
        if not selection:
            self.set_status("❌ Не выбрана запись", "orange")
            return

        entry_id = int(selection[0])
        entries = self.manager.search_entries(id=entry_id)
        if not entries:
            self.set_status(f"❌ Запись #{entry_id} не найдена", "red")
            return

        entry = entries[0]

        exported_status = "Да" if entry.get('exported') else "Нет"
        excel_row = entry.get('source_row') if entry.get('source_row') else "НЕТ"
        excel_sheet = entry.get('source_sheet') if entry.get('source_sheet') else "НЕТ"
        source_type = "Импортирована" if entry.get('source_type') == 'excel' else "Добавлена вручную"

        info = (f"ID: {entry['id']} | Экспортирована: {exported_status} | "
                f"Строка Excel: {excel_row} | Лист Excel: {excel_sheet} | "
                f"Источник: {source_type}")

        self.set_status(info, "blue")

    def reset_row_color(self):
        """Сбрасывает цвет выбранной строки"""
        selection = self.tree.selection()
        if not selection:
            self.set_status("❌ Не выбрана строка для сброса цвета", "orange")
            return

        entry_id = int(selection[0])

        # Сохраняем пустой цвет в БД
        self.manager.update_row_color(entry_id, None)

        # Обновляем отображение
        self.load_recent()
        self.set_status(f"✅ Цвет строки #{entry_id} сброшен", "green")

    def on_right_click(self, event):
        """Обработчик правого клика по строке - выбор цвета"""
        item = self.tree.identify_row(event.y)
        if not item:
            return

        entry_id = int(item)

        # Открываем диалог выбора цвета
        color = colorchooser.askcolor(title="Выберите цвет для строки", parent=self.window)

        if color and color[1]:  # color[1] - это hex
            hex_color = color[1].lstrip('#')

            # Сохраняем в БД
            self.manager.update_row_color(entry_id, hex_color)

            # Обновляем отображение
            self.load_recent()
            self.set_status(f"✅ Цвет строки #{entry_id} сохранён", "green")

    def restore_journal(self):
        """Восстанавливает журнал из БД в новый Excel файл"""
        entries_by_sheet = self.manager.get_restorable_entries()
        if not entries_by_sheet:
            self.set_status("📭 Нет записей для восстановления", "blue")
            return

        new_file = self.config_manager.create_restored_log_path()
        if self.current_workshop == "2":
            template = self.config_manager.get_packaging_log_template_2()
        else:
            template = self.config_manager.get_packaging_log_template()

        if not os.path.exists(template):
            self.set_status("❌ Шаблон журнала не найден", "red")
            return

        # Создаём окно прогресса
        progress_window = tk.Toplevel(self.window)
        progress_window.title("Восстановление журнала")
        progress_window.geometry("400x120")
        progress_window.transient(self.window)
        progress_window.grab_set()

        # Центрируем
        progress_window.update_idletasks()
        x = self.window.winfo_x() + (self.window.winfo_width() - 400) // 2
        y = self.window.winfo_y() + (self.window.winfo_height() - 120) // 2
        progress_window.geometry(f"+{x}+{y}")

        ttk.Label(progress_window, text="Восстановление записей в Excel", font=("Arial", 10, "bold")).pack(pady=10)

        progress_bar = ttk.Progressbar(progress_window, mode='indeterminate')
        progress_bar.pack(pady=10, padx=20, fill=tk.X)
        progress_bar.start(10)

        status_label = ttk.Label(progress_window, text="Подготовка...")
        status_label.pack(pady=5)

        progress_window.update()

        try:
            # Запускаем восстановление
            exported = self.manager.export_entries_to_excel(
                entries_by_sheet,
                template,
                new_file,
                mapping=self.current_mapping
            )

            progress_window.destroy()

            if exported > 0:
                self.set_status(f"✅ Журнал восстановлен: {new_file}", "green")
                # Открываем папку с восстановленным файлом
                path = self.config_manager.get_packaging_log_path()
                folder_to_open = os.path.dirname(path)
                os.startfile(folder_to_open)
            else:
                self.set_status("❌ Ошибка при восстановлении", "red")

        except Exception as e:
            progress_window.destroy()
            self.set_status(f"❌ Ошибка: {str(e)}", "red")

    def clear_database(self):
        """Очищает содержимое базы данных журнала упаковки"""
        # Создаём окно подтверждения
        confirm = tk.Toplevel(self.window)
        confirm.title("Подтверждение")
        confirm.geometry("500x300")
        confirm.transient(self.window)
        confirm.grab_set()

        # Центрируем
        confirm.update_idletasks()
        x = self.window.winfo_x() + (self.window.winfo_width() - 500) // 2
        y = self.window.winfo_y() + (self.window.winfo_height() - 200) // 2
        confirm.geometry(f"+{x}+{y}")

        # Предупреждение
        ttk.Label(
            confirm,
            text="⚠️ ВНИМАНИЕ ⚠️",
            font=("Arial", 14, "bold"),
            foreground="red"
        ).pack(pady=(20, 10))

        ttk.Label(
            confirm,
            text="Это действие не затрагивает файл Excel,\nа очищает Базу Данных электронного журнала.",
            font=("Arial", 11),
            justify="center"
        ).pack(pady=10)

        ttk.Label(
            confirm,
            text="Вы уверены, что хотите продолжить?",
            font=("Arial", 10, "bold")
        ).pack(pady=10)

        # Кнопки
        btn_frame = ttk.Frame(confirm)
        btn_frame.pack(pady=20)

        def do_clear():
            try:
                self.manager.data_manager.clear_database()
                self.entries = []
                self.refresh_table()
                self.set_status("✅ База данных журнала очищена", "green")
                confirm.destroy()
            except Exception as e:
                self.set_status(f"❌ Ошибка: {str(e)}", "red")
                confirm.destroy()

        ttk.Button(
            btn_frame,
            text="Да, очистить",
            command=do_clear,
            width=15
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            btn_frame,
            text="Отмена",
            command=confirm.destroy,
            width=15
        ).pack(side=tk.LEFT, padx=5)

    def update_status_with_file_path(self):
        """Обновляет статусную строку с полным путём к файлу"""
        if self.packaging_log_file:
            self.status_label.config(
                text=f"📁 Текущий файл: {self.packaging_log_file}",
                foreground="blue"
            )
        else:
            self.status_label.config(
                text="📁 Файл журнала не настроен",
                foreground="orange"
            )

    # noinspection SpellCheckingInspection
    def set_status(self, message, color="green"):
        """Устанавливает статусное сообщение с цветом и автоочисткой через 5 секунд"""
        self.status_label.config(text=message, foreground=color)
        self.status_label.update()  # принудительное обновление
        self.window.after(5000, self.update_status_with_file_path)

    def import_from_excel(self):
        """Импорт данных из Excel"""
        # Получаем путь из настроек
        settings = self.config_manager.load_json_settings("shared_utils.json")
        file_path = settings.get("packaging_log_file", "")

        # Если путь есть и файл существует - используем его без диалога
        if file_path and os.path.exists(file_path):
            self._do_import(file_path)
            return

        # Если нет - показываем диалог выбора
        file_path = filedialog.askopenfilename(
            title="Выберите файл для импорта",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
        )

        if not file_path:
            return

        self._do_import(file_path)

    def _do_import(self, file_path):
        """Внутренний метод импорта с прогрессом"""
        # Создаём окно прогресса
        progress_window = tk.Toplevel(self.window)
        progress_window.title("Импорт из Excel")
        progress_window.geometry("400x150")
        progress_window.transient(self.window)
        progress_window.grab_set()

        # Центрируем
        progress_window.update_idletasks()
        x = self.window.winfo_x() + (self.window.winfo_width() - 400) // 2
        y = self.window.winfo_y() + (self.window.winfo_height() - 150) // 2
        progress_window.geometry(f"+{x}+{y}")

        # Элементы прогресса
        ttk.Label(progress_window, text="Импорт данных из Excel", font=("Arial", 10, "bold")).pack(pady=5)

        status_label = ttk.Label(progress_window, text="Подготовка...")
        status_label.pack(pady=5)

        progress_bar = ttk.Progressbar(progress_window, mode='indeterminate')
        progress_bar.pack(pady=5, padx=20, fill=tk.X)
        progress_bar.start(10)

        # Метка для счётчика
        counter_label = ttk.Label(progress_window, text="")
        counter_label.pack(pady=5)

        progress_window.update()

        # Функция обновления прогресса
        def update_progress(message, count):
            if message == "complete":
                sheets, total = count
                progress_window.destroy()
                self.set_status(f"✅ Импорт завершён: {sheets} листов, {total} записей", "green")
                self.load_recent()
            elif message == "error":
                progress_window.destroy()
                self.set_status(f"❌ Ошибка импорта: {count}", "red")
            elif count is None:
                # Начало обработки листа
                status_label.config(text=message)
                counter_label.config(text="")
            else:
                # Завершён лист
                status_label.config(text=message)
                counter_label.config(text=f"➕ Добавлено записей: {count}")
            progress_window.update()

        try:
            imported, errors = self.manager.import_from_excel(
                file_path,
                progress_callback=update_progress,
                only_first_sheet=self.only_first_sheet_var.get(),
                mapping=self.current_mapping
            )

            # Если окно ещё не закрыто (например, при ошибке)
            if progress_window.winfo_exists():
                progress_window.destroy()

            if imported > 0:
                self.set_status(f"✅ Импортировано записей: {imported}. Ошибок: {len(errors)}", "green")
                self.load_recent()
            else:
                error_msg = "\n".join(errors) if errors else "Не удалось импортировать данные"
                self.set_status(f"❌ {error_msg}", "red")

        except Exception as e:
            if progress_window.winfo_exists():
                progress_window.destroy()
            self.set_status(f"❌ Ошибка: {str(e)}", "red")

    def export_to_excel(self):
        """Экспорт новых записей в Excel"""
        # Получаем путь из настроек
        settings = self.config_manager.load_json_settings("shared_utils.json")
        file_path = settings.get("packaging_log_file", "")

        # Если путь есть и файл существует - используем его без диалога
        if file_path and os.path.exists(file_path):
            # Проверяем блокировку файла
            lock_file = file_path + ".lock"
            if os.path.exists(lock_file):
                lock_age = time.time() - os.path.getmtime(lock_file)
                if lock_age < 60:  # Менее минуты - возможно, другой экземпляр пишет
                    self.set_status("⚠️ Файл занят другим процессом, попробуйте позже", "orange")
                    return
                else:
                    # Старый lock-файл (больше минуты) - удаляем
                    try:
                        os.remove(lock_file)
                    except:
                        pass

            # Проверяем, не открыт ли файл в Excel
            try:
                with open(file_path, 'r+b'):
                    pass  # Файл доступен
            except (PermissionError, OSError):
                self.set_status("⚠️ Внимание: файл открыт в Excel, экспорт прерван", "orange")
                return

            self.set_status("⏳ Экспорт...")
            self.window.update()

            try:
                exported = self.manager.export_unexported_to_excel(file_path, mapping=self.current_mapping)

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

            exported = self.manager.export_unexported_to_excel(file_path, mapping=self.current_mapping)

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
        """Обновляет отображение таблицы с поддержкой цветных строк"""
        # Очищаем
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Собираем уникальные цвета для создания тегов
        color_tags = {}

        for i, entry in enumerate(self.entries):
            # Формируем значения по порядку колонок из маппинга
            values = []
            for field in self.tree["columns"]:
                value = entry.get(field, "")
                if value is None:
                    value = ""

                # Спецобработка для даты
                if field == "date" and value and len(str(value)) == 10 and str(value)[4] == '-':
                    try:
                        y, m, d = str(value).split('-')
                        value = f"{d}.{m}.{y}"
                    except:
                        pass

                # Спецобработка для полей с переносом
                config = self._get_column_config(field)
                if config.get("wrap", False):
                    wrap_len = config.get("wrap_len", 30)
                    value = self._wrap_text(value, wrap_len)

                values.append(value)

            # Определяем теги
            tags = []
            row_color = entry.get("row_color")

            if row_color:
                color_tag = f"color_{row_color}"
                if color_tag not in color_tags:
                    self.tree.tag_configure(color_tag, background=f"#{row_color}")
                    color_tags[color_tag] = True
                tags.append(color_tag)
            else:
                tags.append('even' if i % 2 == 0 else 'odd')

            self.tree.insert("", "end", values=values, iid=entry["id"], tags=tags)

        # Настраиваем цвета для чередования
        self.tree.tag_configure('even', background='white')
        self.tree.tag_configure('odd', background='#f0f0f0')

    @staticmethod
    def _wrap_text(text, length):
        """Вставляет переносы строк в длинный текст"""
        if len(text) <= length:
            return text

        words = text.split(' ')
        lines = []
        current_line = ""

        for word in words:
            if len(current_line + word) <= length:
                current_line += (word + " ")
            else:
                # Если слово длиннее length, ищем дефис
                if len(word) > length:
                    parts = []
                    remaining = word
                    while len(remaining) > length:
                        # Ищем дефис в пределах length
                        hyphen_pos = remaining[:length].rfind('-')
                        if hyphen_pos > 0:
                            parts.append(remaining[:hyphen_pos + 1])
                            remaining = remaining[hyphen_pos + 1:]
                        else:
                            parts.append(remaining[:length])
                            remaining = remaining[length:]
                    parts.append(remaining)

                    # Добавляем текущую линию
                    if current_line.strip():
                        lines.append(current_line.strip())

                    # Добавляем части
                    for part in parts[:-1]:
                        lines.append(part)
                    current_line = parts[-1] + " "
                else:
                    lines.append(current_line.strip())
                    current_line = word + " "

        if current_line:
            lines.append(current_line.strip())

        return "\n".join(lines)

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
                # Создаём словарь со всеми полями БД
                defaults = {
                    'date': '',
                    'order_number': '',
                    'customer': '',
                    'product_name': '',
                    'quantity_labels': None,
                    'packer_name': '',
                    'note': ''
                }
                # Добавляем все col_1..col_10
                for i in range(1, 11):
                    defaults[f'col_{i}'] = None

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