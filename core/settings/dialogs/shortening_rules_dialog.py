import os
import tkinter as tk
from tkinter import ttk


# noinspection PyTypeChecker
class ShorteningRulesDialog:
    """Диалог редактирования списка сокращений"""

    def __init__(self, parent, config_manager=None, coordinator=None, status_var=None):
        self.parent = parent
        self.config_manager = config_manager
        self.coordinator = coordinator
        self.status_var = status_var
        self.window = None
        self.original_entries = []
        self.replacement_entries = []

    def show(self):
        """Показывает диалог редактирования сокращений"""
        if self.window and self.window.winfo_exists():
            self.window.lift()
            return

        self.window = tk.Toplevel(self.parent)
        self.window.title("Список сокращений")
        self.window.geometry("670x650")
        self.window.grab_set()

        # Центрирование окна
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"+{x}+{y}")
        self.window.bind("<Escape>", lambda e: self.window.destroy())

        # Основной фрейм
        main_frame = ttk.Frame(self.window, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Фрейм для прокрутки
        container = ttk.Frame(main_frame)
        container.pack(fill=tk.BOTH, expand=True)

        # Создаем canvas и scrollbar
        canvas = tk.Canvas(container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Заголовки
        header_frame = ttk.Frame(scrollable_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(
            header_frame,
            text="Оригинальный текст",
            font=("Arial", 12, "bold"),
            width=40
        ).pack(side=tk.LEFT, padx=(0, 20))

        ttk.Label(
            header_frame,
            text="Замена",
            font=("Arial", 12, "bold"),
            width=25
        ).pack(side=tk.LEFT)

        # Загружаем текущие сокращения
        current_rules = self.load_shortening_rules()

        # Очищаем списки перед заполнением
        self.original_entries.clear()
        self.replacement_entries.clear()

        # Создаем поля ввода для каждого правила
        for original_text, replacement in current_rules.items():
            self._create_rule_row(scrollable_frame, original_text, replacement)

        # Добавляем пустую строку для нового правила
        self._create_rule_row(scrollable_frame, "", "")

        # Кнопки управления
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=10)

        ttk.Button(
            button_frame,
            text="💾 Сохранить",
            command=self.save_shortening_rules
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            button_frame,
            text="➕ Добавить строку",
            command=lambda: self._create_rule_row(scrollable_frame, "", "")
        ).pack(side=tk.LEFT, padx=5)

        # Привязка Enter к сохранению
        self.window.bind("<Return>", lambda e: self.save_shortening_rules())

    def _create_rule_row(self, parent_frame, original_text, replacement):
        """Создает строку с полями ввода для правила сокращения"""
        row_frame = ttk.Frame(parent_frame)
        row_frame.pack(fill=tk.X, pady=2)

        # Поле для оригинального текста
        original_entry = ttk.Entry(row_frame, width=45)
        original_entry.insert(0, original_text)
        original_entry.pack(side=tk.LEFT, padx=(0, 10))

        # Добавляем горячие клавиши
        original_entry.bind("<Control-KeyPress>", self.control_key_handler)
        self.original_entries.append(original_entry)

        # Поле для замены
        replacement_entry = ttk.Entry(row_frame, width=45)
        replacement_entry.insert(0, replacement)
        replacement_entry.pack(side=tk.LEFT, padx=(0, 10))

        # Добавляем горячие клавиши
        replacement_entry.bind("<Control-KeyPress>", self.control_key_handler)
        self.replacement_entries.append(replacement_entry)

        # Кнопка удаления
        ttk.Button(
            row_frame,
            text="×",
            width=2,
            command=lambda f=row_frame, oe=original_entry, re=replacement_entry:
                self._remove_rule_row(f, oe, re)
        ).pack(side=tk.RIGHT)

    def _remove_rule_row(self, row_frame, original_entry, replacement_entry):
        """Удаляет строку с полями ввода"""
        if len(self.original_entries) > 1:
            row_frame.destroy()
            if original_entry in self.original_entries:
                self.original_entries.remove(original_entry)
            if replacement_entry in self.replacement_entries:
                self.replacement_entries.remove(replacement_entry)

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

    def load_shortening_rules(self):
        """Загружает список сокращений, копирует из assets если нет в data"""
        settings_path = self.config_manager.get_settings_path("shortening_rules.json")

        if not os.path.exists(settings_path):
            self._copy_shortening_rules_from_assets()

        return self.config_manager.load_json_settings("shortening_rules.json")

    def _copy_shortening_rules_from_assets(self):
        """Копирует файл shortening_rules.json из assets в data_dir"""
        try:
            asset_path = self.config_manager.get_asset_path("shortening_rules.json")
            dest_path = self.config_manager.get_settings_path("shortening_rules.json")

            if os.path.exists(asset_path):
                import shutil
                shutil.copy2(asset_path, dest_path)
                print(f"Файл shortening_rules.json скопирован из {asset_path} в {dest_path}")
            else:
                print(f"Файл shortening_rules.json не найден в assets по пути: {asset_path}")

        except Exception as e:
            print(f"Ошибка копирования shortening_rules.json: {e}")

    def save_shortening_rules(self):
        """Сохраняет измененный список сокращений"""
        try:
            # Собираем все непустые значения
            new_rules = {}
            for original_entry, replacement_entry in zip(
                    self.original_entries,
                    self.replacement_entries
            ):
                original_text = original_entry.get().strip()
                if original_text:
                    new_rules[original_text] = replacement_entry.get().strip()

            # Сохраняем через ConfigManager
            if self.config_manager.save_json_settings("shortening_rules.json", new_rules):
                if self.status_var:
                    self.status_var.set("✅ Список сокращений успешно сохранен!")

                if self.coordinator:
                    self.coordinator.notify_list_changed('shortening_rules')

                if self.window:
                    self.window.destroy()
                    self.window = None

        except Exception as e:
            if self.status_var:
                self.status_var.set(f"❌ Ошибка сохранения сокращений: {str(e)}")