import tkinter as tk
from tkinter import ttk, messagebox
from core.config_manager import ConfigManager
from core.settings.settings_coordinator import SettingsCoordinator

class FontSettingsDialog:
    """Окно настроек размеров шрифтов"""
    
    @staticmethod
    def get_default_font_settings():
        """Возвращает настройки шрифтов по умолчанию для 1 цеха"""
        return {
            "roll": {
                "customer": {
                    "preview": 20,
                    "print": 36
                },
                "product": {
                    "preview": 16, 
                    "print": 44
                },
                "tu_number": {
                    "preview": 12,
                    "print": 24
                },                
                "other": {
                    "preview": 20,
                    "print": 42
                },
                "multiline_settings": {
                    "line_width_mm": 79,
                    "font_factor": 0.29,
                    "printer_dpi": 203,
                    "max_lines": 4,
                    "font_family": "Arial",
                    "font_style": "normal"
                }
            },
            "box": {
                "manufacturer": {
                    "preview": 16,
                    "print": 40
                },
                "address": {
                    "preview": 9, 
                    "print": 24
                },
                "customer": {
                    "preview": 20,
                    "print": 38
                },
                "product": {
                    "preview": 16,
                    "print": 44
                },
                "total": {
                    "preview": 25,
                    "print": 55
                },
                "tu_number": {
                    "preview": 8,
                    "print": 22
                },
                "packer": {
                    "preview": 16,
                    "print": 36
                },
                "other": {
                    "preview": 14,
                    "print": 36
                },
                "multiline_settings": {
                    "line_width_mm": 79,
                    "font_factor": 0.29,
                    "printer_dpi": 203,
                    "max_lines": 4,
                    "font_family": "Arial",
                    "font_style": "normal"
                }
            }
        }
    
    def __init__(self, parent, config_manager, preview_printer):
        self.parent = parent
        self.config_manager = config_manager
        self.preview_printer = preview_printer
        self.coordinator = SettingsCoordinator()
        
        self.window = tk.Toplevel(parent)
        self.window.title("Настройки шрифтов")
        self.window.geometry("1100x730")
        self.window.resizable(True, True)
        # Центрирование окна
        self.center_window()
        
        # Привязка клавиш
        self.window.bind('<Return>', lambda e: self.save_settings())
        self.window.bind('<Escape>', lambda e: self.window.destroy())
        self.window.focus_set()
        
        self.current_template = self.coordinator.get_font_template()
        
        # Загружаем текущие настройки
        self.font_settings = self.load_font_settings()
        
        self.create_ui()
        
        self.coordinator.subscribe(self._on_coordinator_changed)
        
    def _on_coordinator_changed(self):
        """Обрабатывает изменения от координатора"""
        new_template = self.coordinator.get_font_template()
        if new_template != self.current_template:
            self.current_template = new_template
            self.template_var.set(new_template)
            self.apply_template(silent=True)        
        
    def load_font_settings(self):
        """Загружает настройки шрифтов для текущего шаблона"""
        all_settings = self.config_manager.load_json_settings("label_font_settings.json") or {}
        
        # Если файл пустой, создаем с дефолтным шаблоном
        if not all_settings:
            all_settings = {"1_цех": self.get_default_font_settings()}
            self.config_manager.save_json_settings("label_font_settings.json", all_settings)
        
        # Получаем настройки текущего шаблона
        template_settings = all_settings.get(self.current_template, self.get_default_font_settings())
        
        return self.merge_settings(self.get_default_font_settings(), template_settings)
    
    def merge_settings(self, default, current):
        """Объединяет настройки по умолчанию с текущими"""
        merged = default.copy()
        
        def deep_merge(default_dict, current_dict):
            for key, value in current_dict.items():
                if key in default_dict and isinstance(default_dict[key], dict) and isinstance(value, dict):
                    deep_merge(default_dict[key], value)
                else:
                    default_dict[key] = value
        
        if current:
            deep_merge(merged, current)
        return merged
        
    def create_ui(self):
        """Создает интерфейс настроек"""
        
        self.create_template_panel()
        
        # Основной контейнер с двумя колонками
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Левая колонка - Ролик
        roll_frame = ttk.LabelFrame(main_frame, text="Ролик")
        roll_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        self.create_roll_tab(roll_frame)
        
        # Правая колонка - Коробка
        box_frame = ttk.LabelFrame(main_frame, text="Коробка")
        box_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        self.create_box_tab(box_frame)
        
        # Кнопки сохранения/отмены
        self.create_buttons()
        
    def create_template_panel(self):
        """Создает панель управления шаблонами"""
        template_frame = ttk.Frame(self.window)
        template_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        ttk.Label(template_frame, text="Шаблон:").pack(side=tk.LEFT, padx=(0, 5))
        
        # Combobox шаблонов
        self.template_var = tk.StringVar(value=self.current_template)
        self.template_combo = ttk.Combobox(
            template_frame, 
            textvariable=self.template_var,
            state="readonly",
            width=15
        )
        self.template_combo.pack(side=tk.LEFT, padx=5)
        self.template_combo.bind('<<ComboboxSelected>>', self.on_template_changed)
        
        # Кнопки
        ttk.Button(template_frame, text="🔄", width=3, 
                   command=self.apply_template).pack(side=tk.LEFT, padx=2)
        ttk.Button(template_frame, text="➕", width=3,
                   command=self.save_as_template).pack(side=tk.LEFT, padx=2)
        ttk.Button(template_frame, text="🗑️", width=3,
                   command=self.delete_template).pack(side=tk.LEFT, padx=2)
        
        # Загружаем список шаблонов
        self.update_template_list()
        
    def update_template_list(self):
        """Обновляет список шаблонов в комбобоксе"""
        # Загружаем текущие настройки чтобы получить список шаблонов
        all_settings = self.config_manager.load_json_settings("label_font_settings.json") or {}
        
        # Если файл пустой, создаем дефолтный шаблон
        if not all_settings:
            all_settings = {"1_цех": self.get_default_font_settings()}
            self.config_manager.save_json_settings("label_font_settings.json", all_settings)
        
        templates = list(all_settings.keys())
        self.template_combo['values'] = templates
        
        # Устанавливаем текущий шаблон
        if self.current_template in templates:
            self.template_var.set(self.current_template)
        else:
            self.current_template = "1_цех"
            self.template_var.set("1_цех")
            
    def apply_template(self, silent=False):
        """Применить выбранный шаблон"""
        template_name = self.template_var.get()
        if template_name == self.current_template:
            return  # Уже активен
        
        # Сохраняем текущие настройки перед переключением
        self._save_font_settings()
        
        # Загружаем новый шаблон
        all_settings = self.config_manager.load_json_settings("label_font_settings.json") or {}
        if template_name in all_settings:
            self.current_template = template_name
            template_data = all_settings[template_name]
            
            # Мерджим настройки шаблона с дефолтными
            self.font_settings = self.merge_settings(self.get_default_font_settings(), template_data)
            
            self.update_ui_from_settings()
            
            # Уведомляем координатор только если не silent режим
            if not silent:
                self.coordinator.set_font_template(template_name)
                
            self.show_status(f"Шаблон '{template_name}' применен", "info")
        else:
            self.show_status(f"Шаблон '{template_name}' не найден", "error")
            self.update_template_list()
            
    def save_as_template(self):
        """Сохранить текущие настройки как новый шаблон"""
        # Сначала сохраняем текущие настройки в активный шаблон
        self._save_font_settings()
        
        # Запрашиваем имя шаблона
        template_name = tk.simpledialog.askstring(
            "Новый шаблон", 
            "Введите имя нового шаблона:",
            parent=self.window
        )
        
        if not template_name:
            return
        
        if template_name in ["1_цех", "2_цех"]:
            self.show_status("Недопустимое имя шаблона - зарезервировано системой", "error")
            return
        
        # Загружаем все настройки и добавляем новый шаблон
        all_settings = self.config_manager.load_json_settings("label_font_settings.json") or {}
        
        # Сохраняем КОПИЮ текущих настроек как новый шаблон
        all_settings[template_name] = {
            "roll": self.font_settings["roll"].copy(),
            "box": self.font_settings["box"].copy()
        }
        
        # Сохраняем обновленные настройки
        success = self.config_manager.save_json_settings("label_font_settings.json", all_settings)
        
        if success:
            self.current_template = template_name
            self.update_template_list()
            
            self.coordinator.set_font_template(template_name)
            
            self.show_status(f"Шаблон '{template_name}' сохранен", "info")
        else:
            self.show_status("Не удалось сохранить шаблон", "error")
            
    def on_template_changed(self, event):
        """При изменении выбора шаблона в комбобоксе"""
        new_template = self.template_var.get()
        if new_template != self.current_template:
            self.apply_template()  # Автоматически применяем выбранный шаблон
            
    def delete_template(self):
        """Удалить текущий шаблон"""
        template_name = self.template_var.get()
        
        if template_name in ["1_цех", "2_цех"]:
            self.show_status("Нельзя удалить системные шаблоны '1_цех' и '2_цех'", "error")
            return
        
        if not messagebox.askyesno("Подтверждение", f"Удалить шаблон '{template_name}'?"):
            return
        
        # Загружаем настройки и удаляем шаблон
        all_settings = self.config_manager.load_json_settings("label_font_settings.json") or {}
        if template_name in all_settings:
            del all_settings[template_name]
            
            # Сохраняем обновленные настройки
            success = self.config_manager.save_json_settings("label_font_settings.json", all_settings)
            
            if success:
                workshop = self.coordinator.get_workshop()
                default_template = "1_цех" if workshop == "1" else "2_цех"
                self.coordinator.set_font_template(default_template)               
                
                self.show_status(f"Шаблон '{template_name}' удален", "info")
            else:
                self.show_status("Не удалось удалить шаблон", "error")
                
    def update_ui_from_settings(self):
        """Обновляет UI из текущих настроек"""
        # Обновляем поля ролика
        for key, entries in self.roll_entries.items():
            entries["preview"].set(str(self.font_settings["roll"][key]["preview"]))
            entries["print"].set(str(self.font_settings["roll"][key]["print"]))
        
        # Обновляем поля коробки
        for key, entries in self.box_entries.items():
            entries["preview"].set(str(self.font_settings["box"][key]["preview"]))
            entries["print"].set(str(self.font_settings["box"][key]["print"]))
        
        # Обновляем настройки переноса для ролика
        roll_multiline = self.font_settings["roll"].get("multiline_settings", {})
        for key, var in self.roll_wrap_entries.items():
            if key in roll_multiline:
                var.set(str(roll_multiline[key]))
        
        # Обновляем настройки переноса для коробки
        box_multiline = self.font_settings["box"].get("multiline_settings", {})
        for key, var in self.box_wrap_entries.items():
            if key in box_multiline:
                var.set(str(box_multiline[key]))

    def create_roll_tab(self, parent):
        """Создает вкладку настроек для ролика"""
        # Заголовки
        headers_frame = ttk.Frame(parent)
        headers_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(headers_frame, text="Поле", width=20).pack(side=tk.LEFT)
        ttk.Label(headers_frame, text="Превью", width=10).pack(side=tk.LEFT, padx=5)
        ttk.Label(headers_frame, text="Печать", width=10).pack(side=tk.LEFT, padx=5)
        
        # Разделитель
        ttk.Separator(parent, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=5, pady=5)
        
        # Поля ролика
        self.roll_entries = {}
        roll_fields = [
            ("💼 Заказчик", "customer"),
            ("🏷 Изделие", "product"),
            ("📑 ТУ", "tu_number"),
            ("🔧 Остальные поля", "other")
        ]

        for label, key in roll_fields:
            field_frame = ttk.Frame(parent)
            field_frame.pack(fill=tk.X, padx=5, pady=2)
            
            ttk.Label(field_frame, text=label, width=20).pack(side=tk.LEFT)
            
            # Превью
            preview_var = tk.StringVar(value=str(self.font_settings["roll"][key]["preview"]))
            preview_spin = ttk.Spinbox(field_frame, from_=7, to=72, width=8, textvariable=preview_var)
            preview_spin.pack(side=tk.LEFT, padx=5)
            
            # Печать
            print_var = tk.StringVar(value=str(self.font_settings["roll"][key]["print"]))
            print_spin = ttk.Spinbox(field_frame, from_=7, to=72, width=8, textvariable=print_var)
            print_spin.pack(side=tk.LEFT, padx=(65, 5))
            
            self.roll_entries[key] = {
                "preview": preview_var,
                "print": print_var
            }
            
        # Секция переноса текста - добавляем после обычных полей
        ttk.Separator(parent, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=5, pady=10)
        
        wrap_frame = ttk.LabelFrame(parent, text="📝 Перенос текста для названия на ролике")
        wrap_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Параметры переноса для ролика
        wrap_fields = [
            ("Ширина строки (мм):", "line_width_mm", 85),
            ("Коэффициент шрифта:", "font_factor", 0.47),
            ("DPI принтера:", "printer_dpi", 203),
            ("Макс. строк:", "max_lines", 3),
            ("Шрифт:", "font_family", "Arial"),
            ("Стиль:", "font_style", "normal")
        ]
        
        self.roll_wrap_entries = {}
        
        for i, (label, key, default) in enumerate(wrap_fields):
            field_frame = ttk.Frame(wrap_frame)
            field_frame.pack(fill=tk.X, padx=5, pady=2)
            
            ttk.Label(field_frame, text=label, width=20).pack(side=tk.LEFT)
            
            # Загружаем сохраненное значение или используем по умолчанию
            saved_value = self.font_settings["roll"].get("multiline_settings", {}).get(key, default)
            var = tk.StringVar(value=str(saved_value))
            
            if key == "font_family":
                font_combo = ttk.Combobox(field_frame, values=["Arial", "Times New Roman", "Calibri"], 
                                         width=17, textvariable=var, state="readonly")
                font_combo.pack(side=tk.LEFT, padx=5)
                self.roll_wrap_entries[key] = var
            elif key == "font_style":
                style_combo = ttk.Combobox(field_frame, values=["normal", "bold", "italic"], 
                                          width=8, textvariable=var, state="readonly")
                style_combo.pack(side=tk.LEFT, padx=5)
                self.roll_wrap_entries[key] = var
            else:
                
                if key == "font_factor":
                    entry = ttk.Spinbox(field_frame, from_=0.1, to=1.0, increment=0.01, width=8, textvariable=var)
                elif key == "max_lines":
                    entry = ttk.Spinbox(field_frame, from_=1, to=10, width=8, textvariable=var)
                else:
                    entry = ttk.Spinbox(field_frame, from_=1, to=500, width=8, textvariable=var)
                    
                entry.pack(side=tk.LEFT, padx=5)
                self.roll_wrap_entries[key] = var

    def create_box_tab(self, parent):
        """Создает вкладку настроек для коробки"""
        # Заголовки
        headers_frame = ttk.Frame(parent)
        headers_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(headers_frame, text="Поле", width=20).pack(side=tk.LEFT)
        ttk.Label(headers_frame, text="Превью", width=10).pack(side=tk.LEFT, padx=5)
        ttk.Label(headers_frame, text="Печать", width=10).pack(side=tk.LEFT, padx=5)
        
        # Разделитель
        ttk.Separator(parent, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=5, pady=5)
        
        # Поля коробки
        self.box_entries = {}
        box_fields = [
            ("🏭 Изготовитель", "manufacturer"),
            ("🏠 Адрес", "address"),
            ("💼 Заказчик", "customer"),
            ("🏷 Изделие", "product"),
            ("🔢 Всего этикеток", "total"),
            ("📑 ТУ", "tu_number"),
            ("👷 Упаковщик", "packer"),
            ("🔧 Остальные поля", "other")
        ]

        for label, key in box_fields:
            field_frame = ttk.Frame(parent)
            field_frame.pack(fill=tk.X, padx=5, pady=2)
            
            ttk.Label(field_frame, text=label, width=20).pack(side=tk.LEFT)
            
            # Превью
            preview_var = tk.StringVar(value=str(self.font_settings["box"][key]["preview"]))
            preview_spin = ttk.Spinbox(field_frame, from_=7, to=72, width=8, textvariable=preview_var)
            preview_spin.pack(side=tk.LEFT, padx=5)
            
            # Печать (для ВСЕХ полей теперь редактируемая)
            print_var = tk.StringVar(value=str(self.font_settings["box"][key]["print"]))
            print_spin = ttk.Spinbox(field_frame, from_=7, to=72, width=8, textvariable=print_var)
            print_spin.pack(side=tk.LEFT, padx=(65, 5))
            
            self.box_entries[key] = {
                "preview": preview_var,
                "print": print_var
            }

        # Секция переноса текста - добавляем после обычных полей
        ttk.Separator(parent, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=5, pady=10)
        
        wrap_frame = ttk.LabelFrame(parent, text="📝 Перенос текста для названия на коробке")
        wrap_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Параметры переноса для коробки
        wrap_fields = [
            ("Ширина строки (мм):", "line_width_mm", 80),
            ("Коэффициент шрифта:", "font_factor", 0.47),
            ("DPI принтера:", "printer_dpi", 203),
            ("Макс. строк:", "max_lines", 2),
            ("Шрифт:", "font_family", "Arial"),
            ("Стиль:", "font_style", "normal")
        ]
        
        self.box_wrap_entries = {}
        
        for i, (label, key, default) in enumerate(wrap_fields):
            field_frame = ttk.Frame(wrap_frame)
            field_frame.pack(fill=tk.X, padx=5, pady=2)
            
            ttk.Label(field_frame, text=label, width=20).pack(side=tk.LEFT)
            
            # Загружаем сохраненное значение или используем по умолчанию
            saved_value = self.font_settings["box"].get("multiline_settings", {}).get(key, default)
            var = tk.StringVar(value=str(saved_value))
            
            if key == "font_family":
                font_combo = ttk.Combobox(field_frame, values=["Arial", "Times New Roman", "Calibri"], 
                                         width=17, textvariable=var, state="readonly")
                font_combo.pack(side=tk.LEFT, padx=5)
                self.box_wrap_entries[key] = var
            elif key == "font_style":
                style_combo = ttk.Combobox(field_frame, values=["normal", "bold", "italic"], 
                                          width=8, textvariable=var, state="readonly")
                style_combo.pack(side=tk.LEFT, padx=5)
                self.box_wrap_entries[key] = var
            else:
            
                if key == "font_factor":
                    entry = ttk.Spinbox(field_frame, from_=0.1, to=1.0, increment=0.01, width=8, textvariable=var)
                elif key == "max_lines":
                    entry = ttk.Spinbox(field_frame, from_=1, to=10, width=8, textvariable=var)
                else:
                    entry = ttk.Spinbox(field_frame, from_=1, to=500, width=8, textvariable=var)
                    
                entry.pack(side=tk.LEFT, padx=5)
                self.box_wrap_entries[key] = var

    def open_customers_editor(self):
        """Открывает диалог редактирования списка клиентов без производителя"""
        customers_editor = CustomersEditorDialog(self.window, self.config_manager)
        customers_editor.show()

    def save_settings(self):
        """Сохраняет все настройки через подметоды"""
        try:
            # Сохраняем настройки шрифтов
            self._save_font_settings()
            
            # Сохраняем выбранный шаблон в настройки приложения
            self.coordinator.set_font_template(self.current_template)
            
            # Обновляем превью и закрываем окно
            self.preview_printer.update_font_settings(self.font_settings)
            self.preview_printer.update_preview_displays()
            self.window.destroy()
            
        except ValueError as e:
            self.show_status("Ошибка: Некорректные значения в настройках", "error")
        except Exception as e:
            self.show_status(f"Ошибка сохранения: {e}", "error")

    def _save_font_settings(self):
        """Сохраняет настройки шрифтов"""
        # Сохраняем настройки ролика
        for key, entries in self.roll_entries.items():
            self.font_settings["roll"][key]["preview"] = int(entries["preview"].get())
            self.font_settings["roll"][key]["print"] = int(entries["print"].get())
        
        # Сохраняем настройки переноса для ролика
        if "multiline_settings" not in self.font_settings["roll"]:
            self.font_settings["roll"]["multiline_settings"] = {}
        
        for key, var in self.roll_wrap_entries.items():
            if key == "font_factor":
                self.font_settings["roll"]["multiline_settings"][key] = float(var.get())
            elif key in ["font_family", "font_style"]:
                self.font_settings["roll"]["multiline_settings"][key] = var.get()
            else:
                self.font_settings["roll"]["multiline_settings"][key] = int(var.get())
        
        # Сохраняем настройки коробки
        for key, entries in self.box_entries.items():
            self.font_settings["box"][key]["preview"] = int(entries["preview"].get())
            self.font_settings["box"][key]["print"] = int(entries["print"].get())
        
        # Сохраняем настройки переноса для коробки
        if "multiline_settings" not in self.font_settings["box"]:
            self.font_settings["box"]["multiline_settings"] = {}
            
        for key, var in self.box_wrap_entries.items():
            if key == "font_factor":
                self.font_settings["box"]["multiline_settings"][key] = float(var.get())
            elif key in ["font_family", "font_style"]:
                self.font_settings["box"]["multiline_settings"][key] = var.get()
            else:
                self.font_settings["box"]["multiline_settings"][key] = int(var.get())
        
        # Сохраняем через ConfigManager
        all_settings = self.config_manager.load_json_settings("label_font_settings.json") or {}
        all_settings[self.current_template] = {
            "roll": self.font_settings["roll"].copy(),
            "box": self.font_settings["box"].copy()
        }
        
        success = self.config_manager.save_json_settings("label_font_settings.json", all_settings)
        
        if not success:
            self.show_status("Не удалось сохранить настройки шрифтов", "error")
        else:
            self.show_status("Настройки шрифтов сохранены", "info")

    def create_buttons(self):
        """Создает кнопки сохранения/отмены и строку статуса"""
        # Фрейм для кнопок и статуса
        button_frame = ttk.Frame(self.window)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Левая часть - кнопки
        left_frame = ttk.Frame(button_frame)
        left_frame.pack(side=tk.LEFT)
        
        save_btn = ttk.Button(
            left_frame, 
            text="💾 Сохранить", 
            command=self.save_settings
        )
        save_btn.pack(side=tk.LEFT, padx=5)
        save_btn.configure(default='active')
        self.window.bind('<Return>', lambda e: save_btn.invoke())        
        
        ttk.Button(
            left_frame,
            text="🧹 Сбросить",
            command=self.reset_to_default
        ).pack(side=tk.LEFT, padx=(50, 5))
        
        # Центральная часть - строка статуса
        center_frame = ttk.Frame(button_frame)
        center_frame.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=20)
        
        self.status_var = tk.StringVar(value=f"Шаблон: {self.current_template}")
        self.status_label = ttk.Label(center_frame, textvariable=self.status_var, foreground="green")
        self.status_label.pack(anchor=tk.CENTER)
        
    def show_status(self, message, status_type="info"):
        """Показывает статус в строке состояния"""
        colors = {
            "info": "green",
            "warning": "orange", 
            "error": "red"
        }
        self.status_var.set(message)
        self.status_label.configure(foreground=colors.get(status_type, "green"))
        self.window.update()
        
    def center_window(self):
        """Центрирует окно относительно родительского"""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry('{}x{}+{}+{}'.format(width, height, x, y))

    def reset_to_default(self):
        """Сбрасывает настройки к значениям по умолчанию"""
        if messagebox.askyesno("Сброс", "Сбросить все настройки шрифтов к значениям по умолчанию?"):
            default_settings = self.get_default_font_settings()
            
            # Обновляем UI
            for key, entries in self.roll_entries.items():
                entries["preview"].set(str(default_settings["roll"][key]["preview"]))
                entries["print"].set(str(default_settings["roll"][key]["print"]))
            
            for key, entries in self.box_entries.items():
                entries["preview"].set(str(default_settings["box"][key]["preview"]))
                entries["print"].set(str(default_settings["box"][key]["print"]))
                
            self.show_status("Настройки сброшены к значениям по умолчанию", "info")
                                