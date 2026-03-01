import tkinter as tk
from tkinter import ttk, messagebox

from core.settings.settings_dialog import SettingsDialog


# noinspection SpellCheckingInspection,PyTypeChecker
class FontSettingsDialog:
    """Окно настроек размеров шрифтов"""

    # Константа для пересчёта print → preview
    PRINT_TO_PREVIEW_RATIO = 2.7778  # (300/72) / 1.5

    @staticmethod
    def get_default_font_settings():
        """Возвращает настройки шрифтов по умолчанию для 1 цеха"""
        return {
        "roll": {
            "customer": {
                "print": 40,
                "preview": 14
            },
            "product": {
                "print": 50,
                "preview": 17
            },
            "tu_number": {
                "print": 24,
                "preview": 8
            },
            "other": {
                "print": 40,
                "preview": 14
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
                "print": 26,
                "preview": 9
            }
        },
        "box": {
            "manufacturer": {
                "print": 40,
                "preview": 14
            },
            "address": {
                "print": 26,
                "preview": 9
            },
            "customer": {
                "print": 40,
                "preview": 14
            },
            "product": {
                "print": 50,
                "preview": 17
            },
            "total": {
                "print": 50,
                "preview": 17
            },
            "tu_number": {
                "print": 30,
                "preview": 10
            },
            "packer": {
                "print": 36,
                "preview": 12
            },
            "other": {
                "print": 40,
                "preview": 14
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
                "print": 48,
                "font_family": "Arial",
                "font_style": "bold",
                "preview": 17
            }
        }
    }
        
    def __init__(self, parent_frame, config_manager, preview_printer, preview_export_module, coordinator=None):
        self.roll_status_label = None
        self.roll_status_var = None
        self.box_status_label = None
        self.box_status_var = None
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
        # Получаем шаблон
            
        self.font_settings = self.load_font_settings()
        
        # Основной контейнер с двумя колонками
        self.main_frame = ttk.Frame(self.parent_frame)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
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
                # Обновляем превью
                self.preview_printer.update_font_settings(self.font_settings)
                self.preview_printer.update_preview_displays()

                self.last_status = "✅ Настройки шрифтов сохранены"
                return True
            else:
                self.last_status = "❌ Не удалось сохранить настройки шрифтов"
                return False

        except ValueError:
            self.last_status = "❌ Ошибка: Некорректные значения в настройках"
            return False
        except Exception as _:
            self.last_status = "❌ Ошибка сохранения"
            return False

    def load_font_settings(self):
        """Загружает настройки шрифтов для текущих PDF шаблонов"""
        all_settings = self.config_manager.load_json_settings("label_font_settings.json") or {}

        # Получаем текущие PDF
        workshop = self.coordinator.get_workshop()
        shared = self.config_manager.load_json_settings("shared_utils.json")

        current_roll_pdf = shared.get(f"selected_roll_template_{workshop}", "roll.pdf")
        current_box_pdf = shared.get(f"selected_box_template_{workshop}", "box.pdf")

        # Создаём результат с обоими типами
        result = {
            "roll": {},
            "box": {}
        }

        # Загружаем настройки для ролика
        if current_roll_pdf in all_settings and "roll" in all_settings[current_roll_pdf]:
            result["roll"] = all_settings[current_roll_pdf]["roll"]
        else:
            result["roll"] = self.get_default_font_settings()["roll"]

        # Загружаем настройки для коробки
        if current_box_pdf in all_settings and "box" in all_settings[current_box_pdf]:
            result["box"] = all_settings[current_box_pdf]["box"]
        else:
            result["box"] = self.get_default_font_settings()["box"]

        return result

    def update_ui_from_settings(self):
        """Обновляет UI из текущих настроек"""
        # Обновляем поля ролика - показываем только print
        for key, var in self.roll_entries.items():
            var.set(str(self.font_settings["roll"][key]["print"]))

        # Обновляем поля коробки - показываем только print
        for key, var in self.box_entries.items():
            var.set(str(self.font_settings["box"][key]["print"]))

        # Обновляем настройки переноса (без изменений)
        roll_multiline = self.font_settings["roll"].get("multiline_settings", {})
        for key, var in self.roll_wrap_entries.items():
            if key in roll_multiline:
                var.set(str(roll_multiline[key]))

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
        ttk.Label(headers_frame, text="Размер шрифта(pt)", width=18).pack(side=tk.LEFT, padx=5)
        
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

            # ОДИН спинбокс вместо двух
            size_var = tk.StringVar(value=str(self.font_settings["roll"][key]["print"]))
            size_spin = ttk.Spinbox(field_frame, from_=7, to=72, width=10, textvariable=size_var)
            size_spin.pack(side=tk.LEFT, padx=5)

            self.roll_entries[key] = size_var  # Теперь храним только одну переменную
            
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

        # Информационная строка с текущим PDF
        info_frame = ttk.Frame(parent)
        info_frame.pack(fill=tk.X, padx=5, pady=(10, 5))

        # Получаем отображаемое имя PDF
        workshop = self.coordinator.get_workshop()
        shared = self.config_manager.load_json_settings("shared_utils.json")
        current_pdf = shared.get(f"selected_roll_template_{workshop}", "roll.pdf")

        # Находим отображаемое имя из ROLL_TEMPLATES
        display_name = "Стандартный 1 цех"
        for disp, filename in SettingsDialog.ROLL_TEMPLATES:
            if filename == current_pdf:
                display_name = disp.split(" → ")[0]
                break

        ttk.Label(
            info_frame,
            text=f"Текущий шаблон: {display_name} ({current_pdf})",
            font=("Arial", 12, "bold")
        ).grid(row=0, column=0, sticky="w", padx=5)

        # Кнопка сохранения внизу ролика
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, padx=5, pady=(10, 5))
        button_frame.columnconfigure(0, weight=1)

        save_btn = ttk.Button(
            button_frame,
            text="💾 Сохранить настройки шрифтов",
            command=self._on_save_clicked,
            width=30
        )
        save_btn.grid(row=0, column=0, sticky="w", padx=5)

        # Статус для сообщений
        self.roll_status_var = tk.StringVar()
        self.roll_status_label = ttk.Label(info_frame, textvariable=self.roll_status_var, foreground="green")
        self.roll_status_label.grid(row=1, column=0, sticky="w", padx=5)

    def create_box_tab(self, parent):
        """Создает вкладку настроек для коробки"""
        # Заголовки
        headers_frame = ttk.Frame(parent)
        headers_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(headers_frame, text="Поле", width=20).pack(side=tk.LEFT)
        ttk.Label(headers_frame, text="Размер шрифта(pt)", width=18).pack(side=tk.LEFT, padx=5)
        
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

            # ОДИН спинбокс
            size_var = tk.StringVar(value=str(self.font_settings["box"][key]["print"]))
            size_spin = ttk.Spinbox(field_frame, from_=7, to=72, width=10, textvariable=size_var)
            size_spin.pack(side=tk.LEFT, padx=5)

            self.box_entries[key] = size_var

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

            # Информационная строка с текущим PDF коробки
        info_frame = ttk.Frame(parent)
        info_frame.pack(fill=tk.X, padx=5, pady=(10, 5))

        # Получаем отображаемое имя PDF для коробки
        workshop = self.coordinator.get_workshop()
        shared = self.config_manager.load_json_settings("shared_utils.json")
        current_box_pdf = shared.get(f"selected_box_template_{workshop}", "box.pdf")

        # Находим отображаемое имя из BOX_TEMPLATES
        from core.settings.settings_dialog import SettingsDialog
        box_display = "Стандартная коробка"
        for disp, filename in SettingsDialog.BOX_TEMPLATES:
            if filename == current_box_pdf:
                box_display = disp.split(" → ")[0]
                break

        ttk.Label(
            info_frame,
            text=f"Текущий шаблон: {box_display} ({current_box_pdf})",
            font=("Arial", 12, "bold")
        ).pack(side=tk.LEFT, padx=5)

    def _save_font_settings(self):
        """Сохраняет настройки шрифтов"""
        try:

            # Сохраняем настройки ролика
            for key, var in self.roll_entries.items():
                print_size = int(var.get())
                preview_size = max(7, int(print_size / self.PRINT_TO_PREVIEW_RATIO))
                self.font_settings["roll"][key]["print"] = print_size
                self.font_settings["roll"][key]["preview"] = preview_size

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
            for key, var in self.box_entries.items():
                print_size = int(var.get())
                preview_size = max(7, int(print_size / self.PRINT_TO_PREVIEW_RATIO))
                self.font_settings["box"][key]["print"] = print_size
                self.font_settings["box"][key]["preview"] = preview_size

            # Настройки переноса для коробки
            if "multiline_settings" not in self.font_settings["box"]:
                self.font_settings["box"]["multiline_settings"] = {}

            for key, var in self.box_wrap_entries.items():
                if key == "font_factor":
                    self.font_settings["box"]["multiline_settings"][key] = float(var.get())
                elif key in ["font_family", "font_style"]:
                    self.font_settings["box"]["multiline_settings"][key] = var.get()
                else:
                    self.font_settings["box"]["multiline_settings"][key] = int(var.get())

            # Получаем текущие имена PDF
            workshop = self.coordinator.get_workshop()
            shared = self.config_manager.load_json_settings("shared_utils.json") or {}

            current_roll_pdf = shared.get(f"selected_roll_template_{workshop}", "roll.pdf")
            current_box_pdf = shared.get(f"selected_box_template_{workshop}", "box.pdf")

            # Просто создаём словарь с двумя ключами
            settings_to_save = {
                current_roll_pdf: {"roll": self.font_settings["roll"].copy()},
                current_box_pdf: {"box": self.font_settings["box"].copy()}
            }

            # Сохраняем
            success = self.config_manager.save_json_settings("label_font_settings.json", settings_to_save)

            if success:
                self.show_status("✅ Настройки шрифтов сохранены", "info")
            else:
                self.show_status("❌ Не удалось сохранить", "error")

            return success

        except Exception as e:
            self.show_status(f"❌ Ошибка сохранения: {e}", "error")
            return False

    def show_status(self, message, status_type="info"):
        """Показывает статус в строке состояния"""
        colors = {
            "info": "green",
            "warning": "orange",
            "error": "red"
        }
        # Используем roll_status_var вместо status_var
        if self.roll_status_var:
            self.roll_status_var.set(message)
        if self.roll_status_label:
            self.roll_status_label.configure(foreground=colors.get(status_type, "green"))
        self.main_frame.winfo_toplevel().update()

    def reset_to_default(self):
        """Сбрасывает настройки к значениям по умолчанию"""
        if messagebox.askyesno("Сброс", "Сбросить все настройки шрифтов к значениям по умолчанию?"):
            default_settings = self.get_default_font_settings()

            # Обновляем UI - показываем только print
            for key, var in self.roll_entries.items():
                var.set(str(default_settings["roll"][key]["print"]))

            for key, var in self.box_entries.items():
                var.set(str(default_settings["box"][key]["print"]))

            self.show_status("Настройки сброшены к значениям по умолчанию", "info")
                                