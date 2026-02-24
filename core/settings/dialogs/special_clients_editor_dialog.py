import tkinter as tk
from tkinter import ttk


# noinspection PyTypeChecker
class SpecialClientsEditorDialog:
    """Диалог редактирования списка особых клиентов"""

    def __init__(self, parent, config_manager=None, coordinator=None, status_var=None):
        self.parent = parent
        self.config_manager = config_manager
        self.coordinator = coordinator
        self.status_var = status_var
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
        self.window.title("Список клиентов с особыми требованиями")
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
        # Добавляем контекстное меню и горячие клавиши к полю ввода имени
        self.add_context_menu_to_entry(name_entry)
        name_entry.bind("<Control-KeyPress>", self.control_key_handler)
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
        # Добавляем контекстное меню и горячие клавиши к текстовому полю
        self.add_context_menu_to_text(text_widget)
        text_widget.bind("<Control-KeyPress>", self.control_key_handler_text)
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

    def control_key_handler(self, event):
        """Обработчик горячих клавиш для Entry полей"""
        widget = event.widget
        if event.keycode in (86, 118):  # V key - вставка
            self.paste_text_to_entry(widget)
            return "break"
        elif event.keycode in (67, 99):  # C key - копирование
            self.copy_text_from_entry(widget)
            return "break"
        return None

    def control_key_handler_text(self, event):
        """Обработчик горячих клавиш для Text виджетов"""
        widget = event.widget
        if event.keycode in (86, 118):  # V key - вставка
            self.paste_text_to_text_widget(widget)
            return "break"
        elif event.keycode in (67, 99):  # C key - копирование
            self.copy_text_from_text_widget(widget)
            return "break"
        return None

    def add_context_menu_to_text(self, text_widget):
        """Добавляет контекстное меню к текстовому виджету."""
        menu = tk.Menu(text_widget, tearoff=0)
        menu.add_command(label="Копировать",
                         command=lambda: self.copy_text_from_text_widget(text_widget))
        menu.add_command(label="Вставить",
                         command=lambda: self.paste_text_to_text_widget(text_widget))
        text_widget.bind("<Button-3>",
                         lambda e: menu.tk_popup(e.x_root, e.y_root))

    @staticmethod
    def copy_text_from_text_widget(widget):
        """Копирует текст из текстового виджета."""
        try:
            text = widget.get("1.0", "end-1c")
            if text:
                widget.clipboard_clear()
                widget.clipboard_append(text)
        except Exception as e:
            print(f"Ошибка копирования: {e}")

    @staticmethod
    def paste_text_to_text_widget(widget):
        """Вставляет текст в текстовый виджет."""
        try:
            text = widget.clipboard_get()
            if text:
                widget.delete("1.0", tk.END)
                widget.insert("1.0", text)
        except Exception as e:
            print(f"Ошибка вставки: {e}")

    def add_context_menu_to_entry(self, entry_widget):
        """Добавляет контекстное меню к полю ввода Entry."""
        menu = tk.Menu(entry_widget, tearoff=0)
        menu.add_command(label="Копировать",
                         command=lambda: self.copy_text_from_entry(entry_widget))
        menu.add_command(label="Вставить",
                         command=lambda: self.paste_text_to_entry(entry_widget))
        entry_widget.bind("<Button-3>",
                          lambda e: menu.tk_popup(e.x_root, e.y_root))

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
                if self.status_var:
                    self.status_var.set("✅ Список особых клиентов успешно обновлен!")

                if self.window:
                    self.window.destroy()
                    self.window = None

        except Exception as e:
            if self.status_var:
                self.status_var.set(f"❌ Ошибка сохранения особых клиентов: {str(e)}")