import tkinter as tk
from tkinter import ttk


# noinspection PyTypeChecker
class TemplatesListDialog:
    """Диалог редактирования списка шаблонов (ролики и коробки)"""

    def __init__(self, parent, config_manager=None, coordinator=None, status_var=None):
        self.parent = parent
        self.config_manager = config_manager
        self.coordinator = coordinator
        self.status_var = status_var
        self.window = None
        
        # Для роликов
        self.roll_name_entries = []
        self.roll_file_entries = []
        
        # Для коробок
        self.box_name_entries = []
        self.box_file_entries = []

    def show(self):
        """Показывает диалог редактирования шаблонов"""
        if self.window and self.window.winfo_exists():
            self.window.lift()
            return

        self.window = tk.Toplevel(self.parent)
        self.window.title("Редактор шаблонов этикеток")
        self.window.geometry("1000x650")
        self.window.grab_set()

        # Центрирование окна
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"+{x}+{y}")

        self.window.bind("<Escape>", lambda e: self.window.destroy())

        main_frame = ttk.Frame(self.window, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Заголовок
        title_label = ttk.Label(
            main_frame, 
            text="Редактирование шаблонов этикеток", 
            font=("Arial", 16, "bold")
        )
        title_label.pack(pady=(0, 10))

        # Фрейм для двух колонок
        columns_frame = ttk.Frame(main_frame)
        columns_frame.pack(fill=tk.BOTH, expand=True)

        # Левая колонка - Ролики
        left_frame = ttk.LabelFrame(columns_frame, text="Шаблоны для роликов", padding=10)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        # Правая колонка - Коробки
        right_frame = ttk.LabelFrame(columns_frame, text="Шаблоны для коробок", padding=10)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

        columns_frame.grid_columnconfigure(0, weight=1)
        columns_frame.grid_columnconfigure(1, weight=1)
        columns_frame.grid_rowconfigure(0, weight=1)

        # Создаем содержимое для обеих колонок
        self._create_template_section(left_frame, "roll")
        self._create_template_section(right_frame, "box")

        # Кнопки управления внизу
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)

        ttk.Button(
            button_frame, text="💾 Сохранить", command=self.save_templates
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame, text="❌ Отмена", command=self.window.destroy
        ).pack(side=tk.LEFT, padx=5)

        # Привязка Enter к сохранению
        self.window.bind("<Return>", lambda e: self.save_templates())

        # Загружаем данные
        self._load_templates()

    def _create_template_section(self, parent, section_type):
        """Создает секцию с шаблонами для роликов или коробок"""
        # Заголовки колонок
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(
            header_frame, text="Название шаблона", font=("Arial", 10, "bold"), width=25
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(
            header_frame, text="Имя файла (.pdf)", font=("Arial", 10, "bold"), width=20
        ).pack(side=tk.LEFT)

        # Контейнер с прокруткой для записей
        canvas_frame = ttk.Frame(parent)
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(canvas_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Сохраняем ссылки на списки записей
        if section_type == "roll":
            self.roll_container = scrollable_frame
        else:
            self.box_container = scrollable_frame

        # Кнопка добавления строки
        add_btn = ttk.Button(
            parent,
            text="➕ Добавить шаблон",
            command=lambda: self._add_template_row(section_type)
        )
        add_btn.pack(pady=10)

    def _add_template_row(self, section_type, name="", file=""):
        """Добавляет строку с полями для шаблона"""
        if section_type == "roll":
            container = self.roll_container
            name_list = self.roll_name_entries
            file_list = self.roll_file_entries
        else:
            container = self.box_container
            name_list = self.box_name_entries
            file_list = self.box_file_entries

        row_frame = ttk.Frame(container)
        row_frame.pack(fill=tk.X, pady=2)

        # Поле для названия шаблона
        name_entry = ttk.Entry(row_frame, width=30)
        name_entry.insert(0, name)
        name_entry.pack(side=tk.LEFT, padx=(0, 10))
        name_entry.bind("<Control-KeyPress>", self.control_key_handler)
        name_list.append(name_entry)

        # Поле для имени файла
        file_entry = ttk.Entry(row_frame, width=25)
        file_entry.insert(0, file)
        file_entry.pack(side=tk.LEFT, padx=(0, 10))
        file_entry.bind("<Control-KeyPress>", self.control_key_handler)
        file_list.append(file_entry)

        # Кнопка удаления
        delete_btn = ttk.Button(
            row_frame,
            text="×",
            width=2,
            command=lambda: self._remove_template_row(
                row_frame, name_entry, file_entry, name_list, file_list
            ),
        )
        delete_btn.pack(side=tk.RIGHT)

    @staticmethod
    def _remove_template_row(row_frame, name_entry, file_entry, name_list, file_list):
        """Удаляет строку с полями"""
        if len(name_list) > 1:
            row_frame.destroy()
            if name_entry in name_list:
                name_list.remove(name_entry)
            if file_entry in file_list:
                file_list.remove(file_entry)

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

    def _load_templates(self):
        """Загружает шаблоны из JSON"""
        templates = self.config_manager.load_json_settings("templates_list.json")

        # Загружаем ролики
        for name, file in templates.get("roll_templates", {}).items():
            self._add_template_row("roll", name, file)

        # Загружаем коробки
        for name, file in templates.get("box_templates", {}).items():
            self._add_template_row("box", name, file)

        # Добавляем по одной пустой строке, если списки пусты
        if not self.roll_name_entries:
            self._add_template_row("roll", "", "")
        if not self.box_name_entries:
            self._add_template_row("box", "", "")

    def save_templates(self):
        """Сохраняет измененный список шаблонов"""
        try:
            # Собираем шаблоны роликов
            roll_templates = {}
            for name_entry, file_entry in zip(self.roll_name_entries, self.roll_file_entries):
                name = name_entry.get().strip()
                file = file_entry.get().strip()
                if name and file:
                    # Добавляем .pdf если нет расширения
                    if not file.lower().endswith('.pdf'):
                        file += '.pdf'
                    roll_templates[name] = file

            # Собираем шаблоны коробок
            box_templates = {}
            for name_entry, file_entry in zip(self.box_name_entries, self.box_file_entries):
                name = name_entry.get().strip()
                file = file_entry.get().strip()
                if name and file:
                    if not file.lower().endswith('.pdf'):
                        file += '.pdf'
                    box_templates[name] = file

            templates_data = {
                "roll_templates": roll_templates,
                "box_templates": box_templates
            }

            if self.config_manager.save_json_settings("templates_list.json", templates_data):
                if self.status_var:
                    self.status_var.set("✅ Список шаблонов успешно сохранен!")

                if self.coordinator:
                    self.coordinator.notify_list_changed('templates')

                if self.window:
                    self.window.destroy()
                    self.window = None

        except Exception as e:
            if self.status_var:
                self.status_var.set(f"❌ Ошибка сохранения шаблонов: {str(e)}")