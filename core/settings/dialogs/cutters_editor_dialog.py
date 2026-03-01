import tkinter as tk
from tkinter import ttk


# noinspection PyTypeChecker
class CuttersEditorDialog:
    """Диалог редактирования списка резчиков"""

    def __init__(self, parent, config_manager=None, coordinator=None, status_var=None):
        self.parent = parent
        self.config_manager = config_manager
        self.coordinator = coordinator
        self.status_var = status_var
        self.window = None
        self.cutter_entries = []

    def show(self):
        if self.window and self.window.winfo_exists():
            self.window.lift()
            return

        self.window = tk.Toplevel(self.parent)
        self.window.title("Список резчиков")
        self.window.geometry("405x450")
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

        # Создаем canvas и scrollbar для списка резчиков
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Загружаем текущий список резчиков
        current_cutters = self.config_manager.get_cutters()

        # Создаем поля ввода для каждого резчика
        for cutter in current_cutters:
            self._create_cutter_row(scrollable_frame, cutter)

        # Добавляем пустое поле для нового резчика
        self._create_cutter_row(scrollable_frame, "")

        # Фрейм для кнопок управления
        button_frame = ttk.Frame(self.window)
        button_frame.pack(fill=tk.X, pady=10, padx=10)

        ttk.Button(
            button_frame,
            text="💾 Сохранить",
            command=self.save_cutters_list
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            button_frame,
            text="➕ Добавить строку",
            command=lambda: self._create_cutter_row(scrollable_frame, "")
        ).pack(side=tk.LEFT, padx=5)

        # Привязка Enter к сохранению
        self.window.bind("<Return>", lambda e: self.save_cutters_list())

    def _create_cutter_row(self, parent, cutter):
        """Создает строку с полем ввода для резчика"""
        row_frame = ttk.Frame(parent)
        row_frame.pack(fill=tk.X, pady=5, padx=5)

        # Поле ввода
        entry = ttk.Entry(row_frame, width=45)
        entry.insert(0, cutter)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        # Добавляем контекстное меню и горячие клавиши
        self.add_context_menu_to_entry(entry)
        entry.bind("<Control-KeyPress>", self.control_key_handler_entry)
        self.cutter_entries.append(entry)

        # Кнопка удаления
        ttk.Button(
            row_frame,
            text="×",
            width=2,
            command=lambda: self._remove_cutter_row(row_frame, entry)
        ).pack(side=tk.RIGHT)

    def _remove_cutter_row(self, row_frame, entry):
        """Удаляет строку с полем ввода"""
        if len(self.cutter_entries) > 1:
            row_frame.destroy()
            self.cutter_entries.remove(entry)

    def control_key_handler_entry(self, event):
        """Обработчик горячих клавиш для Entry полей"""
        widget = event.widget
        if event.keycode in (86, 118):
            self.paste_text_to_entry(widget)
            return "break"
        elif event.keycode in (67, 99):
            self.copy_text_from_entry(widget)
            return "break"
        return None

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

    def save_cutters_list(self):
        """Сохраняет список резчиков"""
        try:
            # Собираем все непустые значения
            new_cutters = []
            for entry in self.cutter_entries:
                cutter_name = entry.get().strip()
                if cutter_name:
                    new_cutters.append(cutter_name)

            # Загружаем текущие настройки
            settings = self.config_manager.load_json_settings("shared_utils.json")

            # Обновляем список резчиков
            settings["cutters"] = new_cutters

            # Сохраняем обратно в файл
            if self.config_manager.save_json_settings("shared_utils.json", settings):
                if self.status_var:
                    self.status_var.set("✅ Список резчиков успешно обновлен!")

                if self.window:
                    self.window.destroy()
                    self.window = None

        except Exception as e:
            if self.status_var:
                self.status_var.set(f"❌ Ошибка сохранения резчиков: {str(e)}")