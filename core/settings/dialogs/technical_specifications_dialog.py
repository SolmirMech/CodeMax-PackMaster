import tkinter as tk
from tkinter import ttk


# noinspection PyTypeChecker
class TechnicalSpecificationsDialog:
    """Диалог редактирования списка технических условий (ТУ)"""

    def __init__(self, parent, config_manager=None, coordinator=None, status_var=None):
        self.parent = parent
        self.config_manager = config_manager
        self.coordinator = coordinator
        self.status_var = status_var
        self.window = None
        self.manufacturer_entries = []
        self.address_entries = []
        self.product_name_entries = []
        self.tu_number_entries = []

    def show(self):
        if self.window and self.window.winfo_exists():
            self.window.lift()
            return

        self.window = tk.Toplevel(self.parent)
        self.window.title("Редактирование списка ТУ")
        self.window.geometry("1010x650")
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
        main_frame = ttk.Frame(self.window, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Фрейм для прокрутки
        container = ttk.Frame(main_frame)
        container.pack(fill=tk.BOTH, expand=True)

        # Canvas и scrollbar
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

        # Заголовки
        header_frame = ttk.Frame(scrollable_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(header_frame, text="Изготовитель", width=20,
                  font=("Arial", 12, "bold")).pack(side=tk.LEFT, padx=2)
        ttk.Label(header_frame, text="Адрес изготовителя", width=25,
                  font=("Arial", 12, "bold")).pack(side=tk.LEFT, padx=(5, 2))
        ttk.Label(header_frame, text="Название материала", width=20,
                  font=("Arial", 12, "bold")).pack(side=tk.LEFT, padx=(75, 2))
        ttk.Label(header_frame, text="Номер ТУ", width=20,
                  font=("Arial", 12, "bold")).pack(side=tk.LEFT, padx=(5, 2))

        # Загружаем текущие ТУ
        current_specs = self.get_current_specifications()

        # Создаем поля для каждого ТУ
        for spec in current_specs:
            self._create_spec_row(
                scrollable_frame,
                spec.get("manufacturer", {}).get("name", ""),
                spec.get("manufacturer", {}).get("address", ""),
                spec.get("product", {}).get("name", ""),
                spec.get("product", {}).get("tu_number", "")
            )

        # Добавляем пустую строку
        self._create_spec_row(scrollable_frame, "", "", "", "")

        # Кнопки управления
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=10)

        ttk.Button(button_frame, text="💾 Сохранить",
                   command=self.save_specifications).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="➕ Добавить строку",
                   command=lambda: self._create_spec_row(scrollable_frame, "", "", "", "")
                   ).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="❌ Отмена",
                   command=self.window.destroy).pack(side=tk.LEFT, padx=5)

        self.window.bind("<Return>", lambda e: self.save_specifications())

    def _create_spec_row(self, parent, manufacturer, address, product_name, tu_number):
        """Создает строку с полями ввода ТУ"""
        row_frame = ttk.Frame(parent)
        row_frame.pack(fill=tk.X, pady=5)

        # Поле для изготовителя
        manufacturer_entry = ttk.Entry(row_frame, width=30)
        manufacturer_entry.insert(0, manufacturer)
        manufacturer_entry.pack(side=tk.LEFT, padx=2)
        self.manufacturer_entries.append(manufacturer_entry)
        self.add_context_menu_to_entry(manufacturer_entry)

        # Поле для адреса (многострочное)
        address_frame = ttk.Frame(row_frame)
        address_frame.pack(side=tk.LEFT, padx=2)

        address_text = tk.Text(address_frame, width=35, height=3, wrap=tk.WORD)
        address_text.insert("1.0", address)
        self.add_context_menu_to_text(address_text)

        address_scrollbar = ttk.Scrollbar(address_frame, orient=tk.VERTICAL, command=address_text.yview)
        address_text.configure(yscrollcommand=address_scrollbar.set)

        address_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        address_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.address_entries.append(address_text)

        # Поле для названия продукта
        product_entry = ttk.Entry(row_frame, width=30)
        product_entry.insert(0, product_name)
        product_entry.pack(side=tk.LEFT, padx=2)
        self.product_name_entries.append(product_entry)
        self.add_context_menu_to_entry(product_entry)

        # Поле для номера ТУ
        tu_entry = ttk.Entry(row_frame, width=35)
        tu_entry.insert(0, tu_number)
        tu_entry.pack(side=tk.LEFT, padx=2)
        self.tu_number_entries.append(tu_entry)
        self.add_context_menu_to_entry(tu_entry)

        # Кнопка удаления
        ttk.Button(row_frame, text="×", width=2,
                   command=lambda: self._remove_spec_row(
                       row_frame, manufacturer_entry, address_text,
                       product_entry, tu_entry, address_scrollbar
                   )).pack(side=tk.LEFT, padx=(10, 0))

    # noinspection PyUnusedLocal
    def _remove_spec_row(self, row_frame, man_entry, addr_widget, prod_entry, tu_entry, addr_scrollbar):
        """Удаляет строку с полями ввода"""
        if len(self.manufacturer_entries) > 1:
            row_frame.destroy()
            self.manufacturer_entries.remove(man_entry)
            self.address_entries.remove(addr_widget)
            self.product_name_entries.remove(prod_entry)
            self.tu_number_entries.remove(tu_entry)

    def add_context_menu_to_text(self, text_widget):
        """Добавляет контекстное меню к текстовому виджету."""
        menu = tk.Menu(text_widget, tearoff=0)
        menu.add_command(label="Копировать", command=lambda: self.copy_text_from_text_widget(text_widget))
        menu.add_command(label="Вставить", command=lambda: self.paste_text_to_text_widget(text_widget))
        text_widget.bind("<Button-3>", lambda e: menu.tk_popup(e.x_root, e.y_root))

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
        menu.add_command(label="Копировать", command=lambda: self.copy_text_from_entry(entry_widget))
        menu.add_command(label="Вставить", command=lambda: self.paste_text_to_entry(entry_widget))
        entry_widget.bind("<Button-3>", lambda e: menu.tk_popup(e.x_root, e.y_root))

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

    def get_current_specifications(self):
        """Возвращает текущий список ТУ"""
        try:
            specs = self.config_manager.load_json_settings("packaging_tu.json")
            return specs.get("technical_specifications", [])
        except Exception as e:
            print(f"Ошибка загрузки ТУ: {e}")
            return []

    def save_specifications(self):
        """Сохраняет список ТУ в packaging_tu.json"""
        try:
            new_specs = []
            # Проверяем, что все списки одинаковой длины
            min_length = min(
                len(self.manufacturer_entries),
                len(self.address_entries),
                len(self.product_name_entries),
                len(self.tu_number_entries)
            )

            for i in range(min_length):
                manufacturer = self.manufacturer_entries[i].get().strip()
                address = self.address_entries[i].get("1.0", tk.END).strip()
                product_name = self.product_name_entries[i].get().strip()
                tu_number = self.tu_number_entries[i].get().strip()

                # Добавляем только если есть хотя бы одно поле заполнено
                if manufacturer or address or product_name or tu_number:
                    spec = {
                        "id": i + 1,
                        "manufacturer": {
                            "name": manufacturer,
                            "address": address
                        },
                        "product": {
                            "name": product_name,
                            "tu_number": tu_number
                        }
                    }
                    new_specs.append(spec)

            # Формируем полную структуру
            data = {
                "technical_specifications": new_specs
            }

            # Сохраняем через ConfigManager
            if self.config_manager.save_json_settings("packaging_tu.json", data):
                if self.coordinator:
                    self.coordinator.notify_list_changed('tu_list')
                if self.status_var:
                    self.status_var.set("✅ Список ТУ успешно сохранен!")
                self.window.destroy()
            else:
                if self.status_var:
                    self.status_var.set("❌ Не удалось сохранить список ТУ")

        except Exception as e:
            if self.status_var:
                self.status_var.set(f"❌ Ошибка сохранения ТУ: {str(e)}")