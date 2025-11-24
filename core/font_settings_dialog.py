import tkinter as tk
from tkinter import ttk, messagebox
from .config_manager import ConfigManager

class FontSettingsDialog:
    """Окно настроек размеров шрифтов"""
    
    @staticmethod
    def get_default_font_settings():
        """Возвращает настройки шрифтов по умолчанию"""
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
        
        self.window = tk.Toplevel(parent)
        self.window.title("Настройки шрифтов")
        self.window.geometry("1100x700")
        self.window.resizable(True, True)
        # Центрирование окна
        self.center_window()
        
        # Привязка клавиш
        self.window.bind('<Return>', lambda e: self.save_settings())
        self.window.bind('<Escape>', lambda e: self.window.destroy())
        self.window.focus_set()
        
        # Загружаем текущие настройки
        self.font_settings = self.load_font_settings()
        
        self.create_ui()
        
    def load_font_settings(self):
        """Загружает настройки шрифтов"""
        default_settings = self.get_default_font_settings()
        
        settings = self.config_manager.load_json_settings("label_font_settings.json")
        return self.merge_settings(default_settings, settings)
    
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
            
            # Обновляем превью и закрываем окно
            self.preview_printer.update_font_settings(self.font_settings)
            self.preview_printer.update_preview_displays()
            self.window.destroy()
            
        except ValueError as e:
            messagebox.showerror("Ошибка", "Некорректные значения в настройках")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка сохранения: {e}")

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
        success = self.config_manager.save_json_settings("label_font_settings.json", self.font_settings)
        
        if not success:
            messagebox.showerror("Ошибка", "Не удалось сохранить настройки шрифтов")

    def create_buttons(self):
        """Создает кнопки сохранения и отмены"""
        button_frame = ttk.Frame(self.window)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        save_btn = ttk.Button(
            button_frame, 
            text="💾 Сохранить", 
            command=self.save_settings
        )
        save_btn.pack(side=tk.LEFT, padx=5)
        
        save_btn.configure(default='active')
        self.window.bind('<Return>', lambda e: save_btn.invoke())        
        
        ttk.Button(
            button_frame,
            text="🧹 Сбросить",
            command=self.reset_to_default
        ).pack(side=tk.RIGHT, padx=5)
        
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
                                