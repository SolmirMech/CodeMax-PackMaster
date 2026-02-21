import tkinter as tk
from tkinter import ttk, messagebox

class FontSettingsDialog:
    """Окно настроек размеров шрифтов"""
    
    @staticmethod
    def get_default_font_settings():
        """Возвращает настройки шрифтов по умолчанию для 1 цеха"""
        return {
            "roll": {
                "customer": {
                    "preview": 14,
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
                    "preview": 16,
                    "print": 36
                },
                "multiline_settings": {
                    "line_width_mm": 79,
                    "font_factor": 0.29,
                    "printer_dpi": 203,
                    "max_lines": 4,
                    "font_family": "Arial",
                    "font_style": "normal"
                },
                "address": {
                    "preview": 9,
                    "print": 26
                }
            },
            "box": {
                "manufacturer": {
                    "preview": 16,
                    "print": 40
                },
                "address": {
                    "preview": 9,
                    "print": 26
                },
                "customer": {
                    "preview": 14,
                    "print": 36
                },
                "product": {
                    "preview": 16,
                    "print": 44
                },
                "total": {
                    "preview": 20,
                    "print": 50
                },
                "tu_number": {
                    "preview": 10,
                    "print": 30
                },
                "packer": {
                    "preview": 12,
                    "print": 30
                },
                "other": {
                    "preview": 14,
                    "print": 38
                },
                "multiline_settings": {
                    "line_width_mm": 79,
                    "font_factor": 0.28,
                    "printer_dpi": 203,
                    "max_lines": 4,
                    "font_family": "Arial",
                    "font_style": "normal"
                },
                "order_number": {
                    "preview": 16,
                    "print": 48,
                    "font_family": "Arial",
                    "font_style": "bold"
                }
            }
        }
        
    def __init__(self, parent_frame, config_manager, preview_printer, preview_export_module, coordinator=None):
        self.main_frame = None
        self.parent_frame = parent_frame
        self.config_manager = config_manager
        self.preview_printer = preview_printer
        self.preview_export_module = preview_export_module
        self.coordinator = coordinator
        self.parent_manager = None
        self.last_status = ""
        
        # Инициализация переменных
        self.current_template = ""
        self.font_settings = {}
        
        # UI переменные
        self.template_var = None
        self.template_combo = None
        self.roll_entries = {}
        self.box_entries = {}
        self.roll_wrap_entries = {}
        self.box_wrap_entries = {}
        self.status_var = None
        self.status_label = None
        self._initialized = False

    def set_parent_manager(self, manager):
        """Устанавливает ссылку на родительский менеджер"""
        self.parent_manager = manager
        
    def create_ui(self):
        """Создает UI в указанном родительском фрейме"""
        # Получаем шаблон из координатора
        if self.coordinator:
            self.current_template = self.coordinator.get_font_template()
            self.coordinator.subscribe(self._on_coordinator_changed)
            
        self.font_settings = self.load_font_settings()
        
        # Основной контейнер с двумя колонками
        self.main_frame = ttk.Frame(self.parent_frame)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Панель шаблонов
        self.create_template_panel()
        
        # Левая колонка - Ролик
        roll_frame = ttk.LabelFrame(self.main_frame, text="Ролик")
        roll_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        self.create_roll_tab(roll_frame)
        
        # Правая колонка - Коробка
        box_frame = ttk.LabelFrame(self.main_frame, text="Коробка")
        box_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        self.create_box_tab(box_frame)
        
        self._initialized = True

    def _on_save_clicked(self):
        """Обработчик клика по кнопке сохранения"""
        if self.parent_manager:
            self.parent_manager.save_all_and_close()

    def save_settings(self):
        """Сохраняет настройки шрифтов"""
        try:
            # Сохраняем настройки шрифтов
            success = self._save_font_settings()
            
            if success:
                # Сохраняем выбранный шаблон в настройки приложения
                self.coordinator.set_font_template(self.current_template)
                
                # Обновляем превью
                self.preview_printer.update_font_settings(self.font_settings)
                self.preview_printer.update_preview_displays()
                
                self.last_status = "✅ Настройки шрифтов сохранены"
                return True
            else:
                self.last_status = "❌ Не удалось сохранить настройки шрифтов"
                return False
                
        except ValueError as e:
            self.last_status = "❌ Ошибка: Некорректные значения в настройках"
            return False
        except Exception as e:
            self.last_status = f"❌ Ошибка сохранения: {e}"
            return False        
        
    def _on_coordinator_changed(self, context=None):
        """Обрабатывает изменения от координатора"""
        if not self._initialized:
            return
            
        new_template = self.coordinator.get_font_template()
        
        if new_template != self.current_template:
            self.current_template = new_template
            self.template_var.set(new_template)
        
    def load_font_settings(self):
        """Загружает настройки шрифтов для текущего шаблона"""
        all_settings = self.config_manager.get_font_settings()
        
        # Получаем настройки текущего шаблона
        template_settings = all_settings.get(self.current_template)
        
        if template_settings:
            # Проверяем и добавляем отсутствующие поля
            default_settings = self.get_default_font_settings()
            
            # Для ролика
            for key in default_settings["roll"]:
                if key not in template_settings["roll"]:
                    template_settings["roll"][key] = default_settings["roll"][key]
            
            # Для коробки
            for key in default_settings["box"]:
                if key not in template_settings["box"]:
                    template_settings["box"][key] = default_settings["box"][key]
            
            return template_settings
        else:
            return self.get_default_font_settings()
        
    def create_template_panel(self):
        """Создает панель управления шаблонами"""
        template_frame = ttk.Frame(self.main_frame)
        template_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        # Левая часть - выбор шаблона
        left_frame = ttk.Frame(template_frame)
        left_frame.pack(side=tk.LEFT)
        
        ttk.Label(left_frame, text="Шаблон:").pack(side=tk.LEFT, padx=(0, 5))
        
        # Combobox шаблонов
        self.template_var = tk.StringVar(value=self.current_template)
        self.template_combo = ttk.Combobox(
            left_frame, 
            textvariable=self.template_var,
            state="readonly",
            width=15
        )
        self.template_combo.pack(side=tk.LEFT, padx=5)
        self.template_combo.bind('<<ComboboxSelected>>', self.on_template_changed)
        
        # Кнопки управления шаблонами
        ttk.Button(left_frame, text="🔄", width=3, 
                   command=self.apply_template).pack(side=tk.LEFT, padx=5)
        ttk.Button(left_frame, text="➕", width=3,
                   command=self.save_as_template).pack(side=tk.LEFT, padx=5)
        ttk.Button(left_frame, text="🗑️", width=3,
                   command=self.delete_template).pack(side=tk.LEFT, padx=(5, 150))
        
        # Правая часть - кнопки сохранения и статус
        right_frame = ttk.Frame(template_frame)
        right_frame.pack(side=tk.LEFT)
        
        # Кнопка сохранения
        save_btn = ttk.Button(
            right_frame, 
            text="💾 Сохранить", 
            command=self._on_save_clicked
        )
        save_btn.pack(side=tk.LEFT, padx=(5, 220))
        
        # Кнопка сброса
        ttk.Button(
            right_frame,
            text="🧹 Сбросить",
            command=self.reset_to_default
        ).pack(side=tk.RIGHT, padx=(0, 5))     
        
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
            
            # Загружаем настройки шаблона БЕЗ мерджа с дефолтными
            self.font_settings = template_data
            
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
            parent=self.main_frame.winfo_toplevel()
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
            ("🏠 Адрес", "address"),
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
                
        status_frame = ttk.Frame(parent)
        status_frame.pack(fill=tk.X, padx=5, pady=(10, 5))
                
        self.status_var = tk.StringVar(value=f"Шаблон: {self.current_template}")
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var, foreground="green")
        self.status_label.pack(side=tk.LEFT, padx=5)

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
            ("📋 Номер заказа", "order_number"),
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

    def _save_font_settings(self):
        """Сохраняет настройки шрифтов"""
        try:
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
                
            return success
            
        except Exception as e:
            self.show_status(f"Ошибка сохранения: {e}", "error")
            return False
        
    def show_status(self, message, status_type="info"):
        """Показывает статус в строке состояния"""
        colors = {
            "info": "green",
            "warning": "orange", 
            "error": "red"
        }
        self.status_var.set(message)
        self.status_label.configure(foreground=colors.get(status_type, "green"))
        self.main_frame.winfo_toplevel().update()       

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
                                