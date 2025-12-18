# core/settings/lists_settings_dialog.py
import tkinter as tk
from tkinter import ttk, messagebox
import os
import shutil
from core.config_manager import ConfigManager


class ListsSettingsDialog:
    """Диалог для редактируемых списков"""
    def __init__(self, parent_frame, preview_export_module):
        self.parent_frame = parent_frame
        self.preview_export_module = preview_export_module
        self.config_manager = ConfigManager()
        self.parent_manager = None
        self.last_status = ""
        self.status_var = tk.StringVar(value="")
        
        self.main_frame = None

    def set_parent_manager(self, manager):
        """Устанавливает ссылку на родительский менеджер"""
        self.parent_manager = manager
        
    def create_ui(self):
        """Создает UI в родительском фрейме"""
        self.main_frame = ttk.Frame(self.parent_frame)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        content_frame = ttk.Frame(self.main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)

        # Список коробок
        boxes_frame = ttk.LabelFrame(content_frame, text="🎯 Расстрельные списки", padding=10)
        boxes_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=10)    
        
        open_boxes_btn = ttk.Button(
            boxes_frame,
            text="📦 Список коробок", 
            command=self.open_box_editor,
            width=20
        )
        open_boxes_btn.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        # Кнопка для открытия окна редактирования клиентов
        open_customers_btn = ttk.Button(
            boxes_frame,
            text="📝 Без изготовителя",
            command=self.open_customers_editor
        )
        open_customers_btn.grid(row=1, column=0, padx=5, pady=5, sticky="w")

        # Кнопка для открытия окна особых клиентов
        open_special_btn = ttk.Button(
            boxes_frame,
            text="📋 Особые клиенты", 
            command=self.open_special_clients_editor
        )
        open_special_btn.grid(row=2, column=0, padx=5, pady=5, sticky="w")
        
        # Кнопка для открытия окна ТУ
        open_tu_btn = ttk.Button(
            boxes_frame,
            text="📑 Список ТУ", 
            command=self.open_tu_editor
        )
        open_tu_btn.grid(row=3, column=0, padx=5, pady=5, sticky="w")
        
        # Кнопка для редактирования поддонов
        open_pallets_btn = ttk.Button(
            boxes_frame,
            text="📦 Список поддонов", 
            command=lambda: self.open_box_editor(pallets_mode=True),
            width=20
        )
        open_pallets_btn.grid(row=4, column=0, padx=5, pady=5, sticky="w")        
        
        # Статус-строка
        status_label = ttk.Label(
            self.main_frame,
            textvariable=self.status_var,
            foreground="green",
            wraplength=350,
            font=("Arial", 12)
        )
        status_label.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
        
    def open_box_editor(self, pallets_mode=False):
        """Открывает редактор коробок или поддонов"""
        parent_window = self.parent_frame.winfo_toplevel()
        dialog = BoxEditorDialog(parent_window, self.preview_export_module, pallets_mode=pallets_mode)
        dialog.parent_dialog = self
        dialog.show()
        
    def open_customers_editor(self):
        """Открывает окно редактирования списка клиентов без производителя"""
        parent_window = self.parent_frame.winfo_toplevel()
        dialog = CustomersEditorDialog(parent_window, self.preview_export_module)
        dialog.parent_dialog = self
        dialog.show()

    def open_special_clients_editor(self):
        """Открывает окно редактирования списка особых клиентов"""
        parent_window = self.parent_frame.winfo_toplevel()
        dialog = SpecialClientsEditorDialog(parent_window, self.preview_export_module)
        dialog.parent_dialog = self
        dialog.show()
        
    def open_tu_editor(self):
        """Открывает окно редактирования списка ТУ"""
        parent_window = self.parent_frame.winfo_toplevel()
        dialog = TechnicalSpecificationsDialog(parent_window, self.preview_export_module)
        dialog.parent_dialog = self
        dialog.show()        
        
    def save_settings(self):
        """Сохраняет настройки этой вкладки"""
        # На данный момент этот метод ничего не делает,
        # так как редактирование списков происходит в отдельных окнах
        # которые сами сохраняют изменения
        self.last_status = "✅ Списки успешно сохранены!"
        return True        


class BoxEditorDialog:
    """Диалог редактирования списка коробок"""

    def __init__(self, parent, preview_export_module, pallets_mode=False):
        self.parent = parent
        self.preview_export_module = preview_export_module
        self.pallets_mode = pallets_mode
        self.config_manager = ConfigManager()
        self.window = None
        self.box_size_entries = []
        self.box_weight_entries = []

    def show(self):
        if self.window and self.window.winfo_exists():
            self.window.lift()
            return

        self.window = tk.Toplevel(self.parent)
        self.window.title("Редактирование списка поддонов" if self.pallets_mode else "Редактирование списка коробок")
        self.window.geometry("430x600")
        self.window.grab_set()

        # Центрирование окна
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"+{x}+{y}")
        self.window.bind("<Escape>", lambda e: self.window.destroy())

        frame = ttk.Frame(self.window, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        # Фрейм для прокрутки
        container = ttk.Frame(frame)
        container.pack(fill=tk.BOTH, expand=True)

        # Создаем canvas и scrollbar
        canvas = tk.Canvas(container)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Загружаем текущий список коробок
        current_boxes = self.get_current_boxes()

        # Создаем заголовки
        header_frame = ttk.Frame(scrollable_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(header_frame, text="Название коробки", font=("Arial", 12, "bold")).pack(side=tk.LEFT, padx=(0, 30))
        ttk.Label(header_frame, text="Вес коробки (г)", font=("Arial", 12, "bold")).pack(side=tk.LEFT, padx=(15, 15))

        # Создаем поля ввода
        self.box_size_entries = []
        self.box_weight_entries = []

        for size, weight in current_boxes.items():
            self._create_box_row(scrollable_frame, size, weight)

        # Добавляем пустую строку
        self._create_box_row(scrollable_frame, "", "")

        # Кнопки управления
        button_frame = ttk.Frame(frame)
        button_frame.pack(pady=10)

        ttk.Button(button_frame, text="💾 Сохранить", command=self.save_boxes).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="➕ Добавить строку", 
                  command=lambda: self._create_box_row(scrollable_frame, "", "")).pack(side=tk.LEFT, padx=(5, 30))
        ttk.Button(button_frame, text="❌ Отмена", command=self.window.destroy).pack(side=tk.LEFT, padx=5)

        self.window.bind("<Return>", lambda e: self.save_boxes())

    def _create_box_row(self, parent, size, weight):
        """Создает строку с полями ввода для коробки"""
        row_frame = ttk.Frame(parent)
        row_frame.pack(fill=tk.X, pady=2)

        # Поле для размеров
        size_entry = ttk.Entry(row_frame, width=30)
        size_entry.insert(0, size)
        size_entry.pack(side=tk.LEFT, padx=(0, 10))
        self.box_size_entries.append(size_entry)

        # Поле для веса
        weight_entry = ttk.Entry(row_frame, width=15)
        weight_entry.insert(0, str(weight))
        weight_entry.pack(side=tk.LEFT, padx=(0, 10))
        self.box_weight_entries.append(weight_entry)

        # Кнопка удаления
        ttk.Button(row_frame, text="×", width=2,
                  command=lambda: self._remove_box_row(row_frame, size_entry, weight_entry)).pack(side=tk.RIGHT)

    def _remove_box_row(self, row_frame, size_entry, weight_entry):
        """Удаляет строку с полями ввода"""
        if len(self.box_size_entries) > 1:
            row_frame.destroy()
            self.box_size_entries.remove(size_entry)
            self.box_weight_entries.remove(weight_entry)

    def get_current_boxes(self):
        """Возвращает текущий список коробок ИЛИ поддонов"""
        try:
            settings = self.config_manager.load_json_settings("shared_utils.json")
            if self.pallets_mode:
                return settings.get("weight_pallet", {})  # для поддонов
            else:
                return settings.get("weight_box", {})
        except:
            return {}

    def save_boxes(self):
        """Сохраняет список коробок ИЛИ поддонов в shared_utils.json"""
        try:
            new_boxes = {}
            for size_entry, weight_entry in zip(self.box_size_entries, self.box_weight_entries):
                size = size_entry.get().strip()
                weight_str = weight_entry.get().strip()
                
                if size and weight_str:
                    try:
                        weight = int(weight_str)
                        new_boxes[size] = weight
                    except ValueError:
                        continue

            # Загружаем текущие настройки и обновляем
            settings = self.config_manager.load_json_settings("shared_utils.json")
            
            if self.pallets_mode:
                settings["weight_pallet"] = new_boxes
                key_for_update = "weight_pallet"
            else:
                settings["weight_box"] = new_boxes
                key_for_update = "weight_box"
            
            if self.config_manager.save_json_settings("shared_utils.json", settings):
                # Уведомляем координатора об изменении списка
                if hasattr(self.preview_export_module, 'coordinator'):
                    self.preview_export_module.coordinator.notify_list_changed(key_for_update)
                
                # Статус
                item_name = "поддонов" if self.pallets_mode else "коробок"
                self.parent_dialog.status_var.set(f"✅ Список {item_name} успешно обновлен!")
                
                self.window.destroy()
            else:
                self.parent_dialog.status_var.set("❌ Не удалось сохранить список")
                    
        except Exception as e:
            self.parent_dialog.status_var.set(f"❌ Ошибка сохранения: {str(e)}")
                
                
class CustomersEditorDialog:
    """Диалог редактирования списка клиентов без производителя"""

    def __init__(self, parent, preview_export_module):
        self.parent = parent
        self.preview_export_module = preview_export_module
        self.config_manager = ConfigManager()
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
        current_customers = self.config_manager.get_without_manufacturer_customers()

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
            settings = self.config_manager.load_json_settings("shared_utils.json")
            
            # Обновляем список клиентов без производителя
            settings["without_manufacturer"] = new_customers

            # Сохраняем обратно в файл
            if self.config_manager.save_json_settings("shared_utils.json", settings):
                self.parent_dialog.status_var.set("✅ Список клиентов Без производителя успешно обновлен!")

                if self.window:
                    self.window.destroy()
                    self.window = None

        except Exception as e:
            self.parent_dialog.status_var.set(f"❌ Ошибка сохранения клиентов: {str(e)}")


class SpecialClientsEditorDialog:
    """Диалог редактирования списка особых клиентов"""

    def __init__(self, parent, preview_export_module):
        self.parent = parent
        self.preview_export_module = preview_export_module
        self.config_manager = ConfigManager()
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
            settings = self.config_manager.load_json_settings("shared_utils.json")

            # Обновляем список особых клиентов
            settings["special_clients"] = new_special_clients

            # Сохраняем обратно в файл
            if self.config_manager.save_json_settings("shared_utils.json", settings):
                self.parent_dialog.status_var.set("✅ Список особых клиентов успешно обновлен!")

                if self.window:
                    self.window.destroy()
                    self.window = None

        except Exception as e:
            self.parent_dialog.status_var.set(f"❌ Ошибка сохранения особых клиентов: {str(e)}")
            

class TechnicalSpecificationsDialog:
    """Диалог редактирования списка технических условий (ТУ)"""
    
    def __init__(self, parent, preview_export_module):
        self.parent = parent
        self.preview_export_module = preview_export_module
        self.config_manager = ConfigManager()
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
        self.window.geometry("1200x650")  # Увеличил ширину
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
                 font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=2)
        ttk.Label(header_frame, text="Адрес", width=35,
                 font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=2)
        ttk.Label(header_frame, text="Название продукта", width=25,
                 font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=2)
        ttk.Label(header_frame, text="Номер ТУ", width=20,
                 font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=2)
        
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
        """Создает строку с полями ввода для ТУ"""
        row_frame = ttk.Frame(parent)
        row_frame.pack(fill=tk.X, pady=5)
        
        # Поле для изготовителя
        manufacturer_entry = ttk.Entry(row_frame, width=30)
        manufacturer_entry.insert(0, manufacturer)
        manufacturer_entry.pack(side=tk.LEFT, padx=2)
        self.manufacturer_entries.append(manufacturer_entry)
        
        # Поле для адреса (многострочное)
        address_frame = ttk.Frame(row_frame)
        address_frame.pack(side=tk.LEFT, padx=2)
        
        address_text = tk.Text(address_frame, width=35, height=3, wrap=tk.WORD)
        address_text.insert("1.0", address)
        
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
        
        # Поле для номера ТУ
        tu_entry = ttk.Entry(row_frame, width=35)
        tu_entry.insert(0, tu_number)
        tu_entry.pack(side=tk.LEFT, padx=2)
        self.tu_number_entries.append(tu_entry)
        
        # Кнопка удаления
        ttk.Button(row_frame, text="×", width=2,
                  command=lambda: self._remove_spec_row(
                      row_frame, manufacturer_entry, address_text, 
                      product_entry, tu_entry, address_scrollbar
                  )).pack(side=tk.LEFT, padx=(10, 0))
    
    def _remove_spec_row(self, row_frame, man_entry, addr_widget, prod_entry, tu_entry, addr_scrollbar):
        """Удаляет строку с полями ввода"""
        if len(self.manufacturer_entries) > 1:
            row_frame.destroy()
            self.manufacturer_entries.remove(man_entry)
            self.address_entries.remove(addr_widget)
            self.product_name_entries.remove(prod_entry)
            self.tu_number_entries.remove(tu_entry)
    
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
                if hasattr(self.preview_export_module, 'coordinator'):
                    self.preview_export_module.coordinator.notify_list_changed('tu_list')                
                self.parent_dialog.status_var.set("✅ Список ТУ успешно сохранен!")
                self.window.destroy()
            else:
                self.parent_dialog.status_var.set("❌ Не удалось сохранить список ТУ")
                
        except Exception as e:
            self.parent_dialog.status_var.set(f"❌ Ошибка сохранения ТУ: {str(e)}")
            
                