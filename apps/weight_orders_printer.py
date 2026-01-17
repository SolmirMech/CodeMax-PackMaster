import tkinter as tk
from tkinter import ttk, StringVar, BooleanVar
from datetime import datetime
import win32print
import win32ui
from core.shared_utils import (
    mm_to_pixels,
    get_default_printer,
    create_printer_dc,
)

class WeightOrdersPrinter:
    """Принтер этикеток для втулок (левая часть интерфейса)."""
    
    def __init__(self, parent, config_manager=None):
        self.parent = parent
        self.config_manager = config_manager
        self.settings_file = "print_settings.json"
        
        # Настройки по умолчанию
        self.default_settings = {
            "printer": get_default_printer(),
            "font_size_pt": 10,
            "margin_left_mm": 2,
            "margin_top_mm": 1,
            "label_height_mm": 17,
            "between_labels_mm": 3,
        }
        
        self.settings = self.default_settings.copy()
        self.load_settings("weight_labels")
        self.settings_window = None
        self.manufacturer = self.config_manager.get_manufacturer()
        
        # Префикс и суффикс номера заказа
        order_settings = self.config_manager.load_json_settings("shared_utils.json").get("order_number", {})
        self.order_prefix = StringVar(value=order_settings.get("prefix", "Ф"))
        self.order_number = StringVar(value="")
        self.order_suffix = StringVar(value=order_settings.get("suffix", "/5"))
        
        # Переменные для веса
        self.gross_weight = StringVar(value="")
        self.net_weight = StringVar(value="")
        self.sleeve_weight = StringVar(value="40")
        self.status_var = StringVar(value="")
        
        # Переменные интерфейса
        self.entries = {}
        self.hide_producer_var = BooleanVar(value=False)
        self.cutter_menubutton = None
        
        self.create_ui()

    def create_ui(self):
        """Создает только левую часть интерфейса (Основные данные и Параметры печати)"""
        # Основной контейнер
        main_container = ttk.Frame(self.parent)
        main_container.pack(fill=tk.BOTH, expand=True, side=tk.LEFT, padx=(0, 10))

        # Верхняя часть: Основные данные
        left_frame = ttk.LabelFrame(main_container, text="Основные данные", padding=10)
        left_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Раздел Основные данные
        fields = [
            ("Дата:", "date", datetime.now().strftime("%d.%m.%Y")),
            ("Кол-во:", "quantity", ""),
        ]

        self.entries = {}
        for row, (label, field, default) in enumerate(fields):
            ttk.Label(left_frame, text=label).grid(row=row, column=0, sticky="w", pady=5, padx=5)
            entry = ttk.Entry(left_frame, width=25)
            entry.insert(0, default)
            entry.grid(row=row, column=1, padx=5, pady=5, sticky="w")
            self.entries[field] = entry

        # Номер заказа (3 части)
        row_order = len(fields)
        ttk.Label(left_frame, text="№ заказа:").grid(row=row_order, column=0, sticky="w", pady=5, padx=5)
        
        order_frame = ttk.Frame(left_frame)
        order_frame.grid(row=row_order, column=1, sticky="w", padx=5, pady=5)
        
        entry_prefix = ttk.Entry(order_frame, textvariable=self.order_prefix, width=4)
        entry_prefix.grid(row=0, column=0, padx=(0, 2))
        
        entry_number = ttk.Entry(order_frame, textvariable=self.order_number, width=7)
        entry_number.grid(row=0, column=1, padx=5)
        
        entry_suffix = ttk.Entry(order_frame, textvariable=self.order_suffix, width=6)
        entry_suffix.grid(row=0, column=2, padx=(2, 0))

        # Вес брутто и нетто
        row_weight = len(fields) + 1
        ttk.Label(left_frame, text="Вес брутто, г:").grid(row=row_weight, column=0, sticky="w", pady=5, padx=5)
        self.entries["gross_weight"] = ttk.Entry(left_frame, textvariable=self.gross_weight, width=25)
        self.entries["gross_weight"].grid(row=row_weight, column=1, padx=5, pady=5, sticky="w")
        self.gross_weight.trace_add("write", self.calculate_net_weight)

        ttk.Label(left_frame, text="Вес нетто, г:").grid(row=row_weight + 1, column=0, sticky="w", pady=5, padx=5)
        net_weight_entry = ttk.Entry(left_frame, textvariable=self.net_weight, width=25, state="readonly")
        net_weight_entry.grid(row=row_weight + 1, column=1, padx=5, pady=5, sticky="w")

        # Исполнитель
        row_res = len(fields) + 3
        ttk.Label(left_frame, text="Резчик:").grid(row=row_res, column=0, sticky="w", pady=5, padx=5)
        
        # Создаем фрейм для размещения поля ввода и кнопки меню
        cutter_container = ttk.Frame(left_frame)
        cutter_container.grid(row=row_res, column=1, sticky="w", padx=5, pady=5)
        
        self.entries["executor"] = ttk.Entry(cutter_container, width=20)
        default_cutter = self.config_manager.get_default_cutter()
        self.entries["executor"].insert(0, default_cutter)
        self.entries["executor"].grid(row=0, column=0, padx=(0, 5))
        
        # Создаем меню-кнопку для резчиков
        self.cutter_menubutton = ttk.Menubutton(
            cutter_container, 
            text="👤",
            width=3
        )
        self.cutter_menubutton.grid(row=0, column=1)
        
        # Создаем меню
        self.cutter_menubutton.menu = tk.Menu(self.cutter_menubutton, tearoff=0)
        self.cutter_menubutton["menu"] = self.cutter_menubutton.menu
        
        # Заполняем меню резчиками
        self.update_cutters_menu()

        # Настройка весов левой колонки
        left_frame.columnconfigure(0, weight=0)
        left_frame.columnconfigure(1, weight=1)

        # Нижняя часть: Параметры печати
        print_frame = ttk.LabelFrame(main_container, text="Параметры печати", padding=10)
        print_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(print_frame, text="Вес втулки, г:").grid(row=0, column=0, sticky="w", pady=12)
        self.entries["sleeve_weight"] = ttk.Entry(print_frame, textvariable=self.sleeve_weight, width=15)
        self.entries["sleeve_weight"].grid(row=0, column=1, padx=5, pady=12, sticky="w")
        self.sleeve_weight.trace_add("write", self.calculate_net_weight)
            
        ttk.Label(print_frame, text="Кол-во копий:").grid(row=1, column=0, sticky="w", pady=5)
        self.entries["copies"] = ttk.Entry(print_frame, width=5)
        self.entries["copies"].insert(0, "1")
        self.entries["copies"].grid(row=1, column=1, padx=5, pady=12, sticky="w")

        ttk.Checkbutton(print_frame, text="Не печатать 'Производитель'", variable=self.hide_producer_var
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=12)

        # Кнопки печати и настроек
        buttons_frame = ttk.Frame(print_frame)
        buttons_frame.grid(row=3, column=0, columnspan=2, sticky="w", pady=10)

        print_btn = ttk.Button(buttons_frame, text="🖨 Печать", command=self.print_labels)
        print_btn.grid(row=0, column=0, padx=(0, 10))

        settings_btn = ttk.Button(buttons_frame, text="⚙️ Настройки", command=self.open_settings)
        settings_btn.grid(row=0, column=1)
        
        # Строка статуса в самом низу основного контейнера
        status_frame = ttk.Frame(main_container)
        status_frame.pack(fill=tk.X, pady=(10, 0))

        self.status_label = ttk.Label(
            status_frame, 
            textvariable=self.status_var,
            foreground="green",
            font=("Arial", 9)
        )
        self.status_label.pack(fill=tk.X)
        
    def show_status(self, message, color="green"):
        """Показывает статусное сообщение с автоочисткой"""
        self.status_var.set(message)
        
        # Устанавливаем цвет
        self.status_label.config(foreground=color)
        
        # Очищаем через 5 секунд
        if hasattr(self, '_status_after_id'):
            self.parent.after_cancel(self._status_after_id)
        self._status_after_id = self.parent.after(5000, lambda: self.status_var.set(""))

        
    def update_cutters_menu(self):
        """Обновляет меню резчиков"""
        if not self.cutter_menubutton:
            return
            
        # Очищаем текущее меню
        self.cutter_menubutton.menu.delete(0, tk.END)
        
        # Получаем обновленный список резчиков
        cutters = self.config_manager.get_cutters()
        
        # Заполняем меню заново
        for cutter in cutters:
            self.cutter_menubutton.menu.add_command(
                label=cutter,
                command=lambda c=cutter: self.set_cutter(c)
            )        
            
    def calculate_net_weight(self, *args):
        """Автоматически рассчитывает вес нетто"""
        try:
            gross = float(self.gross_weight.get() or 0)
            
            # Если брутто пустое, то нетто тоже пустое
            if not self.gross_weight.get():
                self.net_weight.set("")
                return
                
            sleeve = float(self.sleeve_weight.get() or 0)
            net = gross - sleeve
            
            # Не допускаем отрицательные значения и ноль
            if net <= 0:
                self.net_weight.set("")
                self.show_status("⚠️ Вес нетто должен быть положительным", "orange")
                return
                
            self.net_weight.set(str(int(net)) if net.is_integer() else f"{net:.1f}")
            
        except (ValueError, TypeError):
            self.net_weight.set("")
            self.show_status("⚠️ Введите корректные числовые значения", "orange")

    def set_cutter(self, name):
        """Устанавливает выбранного резчика в поле ввода"""
        self.entries["executor"].delete(0, tk.END)
        self.entries["executor"].insert(0, name)
            
    def load_settings(self, settings_key):
        """Загружает настройки печати из JSON-файла для конкретного ключа"""
        try:
            all_settings = self.config_manager.load_json_settings(self.settings_file)
            if settings_key in all_settings:
                self.settings = {**self.default_settings, **all_settings[settings_key]}
        except Exception as e:
            print(f"Ошибка загрузки настроек печати: {e}")
            self.settings = self.default_settings.copy()
        
    def save_settings(self):
        """Сохраняет настройки для WeightOrders принтера"""
        try:
            all_settings = self.config_manager.load_json_settings(self.settings_file)
            all_settings["weight_labels"] = self.settings

            if self.config_manager.save_json_settings(self.settings_file, all_settings):
                self.show_status("✅ Настройки печати сохранены", "green")
        except Exception as e:
            self.show_status(f"❌ Не удалось сохранить настройки: {str(e)}", "red")

    def open_settings(self):
        """Открывает окно настроек печати"""
        if self.settings_window and self.settings_window.winfo_exists():
            self.settings_window.lift()
            return

        self.settings_window = tk.Toplevel(self.parent)
        self.settings_window.title("Настройки печати - Этикетки на втулки")
        self.settings_window.geometry("505x300")
        self.settings_window.grab_set()

        # Центрирование окна
        self.settings_window.update_idletasks()
        width = self.settings_window.winfo_width()
        height = self.settings_window.winfo_height()
        x = (self.settings_window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.settings_window.winfo_screenheight() // 2) - (height // 2)
        self.settings_window.geometry(f"+{x}+{y}")
        self.settings_window.bind("<Escape>", lambda e: self.settings_window.destroy())

        frame = ttk.Frame(self.settings_window, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        # Выбор принтера
        ttk.Label(frame, text="Принтер:").grid(row=0, column=0, sticky="w", pady=2)
        printers = win32print.EnumPrinters(2)
        self.printer_var = StringVar(value=self.settings.get("printer", get_default_printer()))
        printer_combo = ttk.Combobox(
            frame,
            textvariable=self.printer_var,
            values=[p[2] for p in printers],
            width=25,
        )
        printer_combo.grid(row=0, column=1, padx=5, pady=2, sticky="w")

        # Параметры печати
        settings_params = [
            ("Размер шрифта (pt):", "font_size_pt", 10, tk.IntVar),
            ("Отступ слева (мм):", "margin_left_mm", 2, tk.IntVar),
            ("Отступ сверху (мм):", "margin_top_mm", 1, tk.IntVar),
            ("Высота этикетки (мм):", "label_height_mm", 17, tk.IntVar),
            ("Зазор между полосками (мм):", "between_labels_mm", 3, tk.IntVar)
        ]

        self.settings_vars = {}
        for row, (label, key, default, var_type) in enumerate(settings_params, start=1):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", pady=2)
            var = var_type(value=self.settings.get(key, default))
            entry = ttk.Entry(frame, textvariable=var, width=10)
            entry.grid(row=row, column=1, padx=5, pady=2, sticky="w")
            self.settings_vars[key] = var

        # Кнопка сохранения
        ttk.Button(
            frame, text="💾 Сохранить", command=self.update_settings
        ).grid(row=len(settings_params) + 1, columnspan=2, pady=15)
        
        self.settings_window.bind("<Return>", lambda e: self.update_settings())

    def update_settings(self):
        """Обновляет настройки печати"""
        try:
            # Обновляем специфичные настройки
            for key, var in self.settings_vars.items():
                value = var.get()
                if isinstance(value, float) and value.is_integer():
                    self.settings[key] = int(value)
                else:
                    self.settings[key] = value

            # Обновляем принтер
            self.settings["printer"] = self.printer_var.get()
            self.save_settings()

            if self.settings_window:
                self.settings_window.destroy()
                self.settings_window = None

        except Exception as e:
            self.show_status(f"❌ Не удалось обновить настройки: {str(e)}", "red")

    def print_labels(self, data=None):
        """Печать этикеток для Заказов с весом."""
        try:
            data = {
                "date": self.entries["date"].get(),
                "quantity": self.entries["quantity"].get(),
                "order": f"{self.order_prefix.get()}{self.order_number.get()}{self.order_suffix.get()}",
                "executor": self.entries["executor"].get(),
                "gross_weight": self.gross_weight.get(),
                "net_weight": self.net_weight.get(),
                "hide_producer": self.hide_producer_var.get(),
                "copies": int(self.entries["copies"].get()),
            }

            self._print_double_label(data)
            self.show_status("✅ Этикетки отправлены на печать", "green")
        except Exception as e:
            self.show_status(f"❌ Ошибка при печати: {str(e)}", "red")

    def _print_double_label(self, data):
        hdc = create_printer_dc(self.settings["printer"])
        hdc.StartDoc("Этикетки Заказы с весом")

        font_height = int(self.settings["font_size_pt"] * 8 / 2.835)
        font = win32ui.CreateFont(
            {
                "name": "Arial",
                "height": font_height,
                "weight": 400,
            }
        )

        margin_left = mm_to_pixels(self.settings["margin_left_mm"])
        margin_top = mm_to_pixels(self.settings["margin_top_mm"])
        between_labels = mm_to_pixels(self.settings.get("between_labels_mm", 3))
        label_height = mm_to_pixels(self.settings.get("label_height_mm", 17))
        true_between_labels = label_height + between_labels
        line_spacing = font_height + 3

        # Формируем строки для печати
        lines = [
            f"Дата {data['date']}   Кол-во {data['quantity']}",
            f"№ Заказа {data['order']}   {data['executor']}",
        ]

        # Добавляем строку с весом только если есть данные
        if data['gross_weight'] or data['net_weight']:
            lines.append(f"Вес Брутто, г: {data['gross_weight']}   Нетто, г: {data['net_weight']}")
        else:
            lines.append(" ")  # Пустая строка для сохранения позиционирования        

        # Добавляем производителя если не скрыто
        if not data["hide_producer"] and self.order_prefix.get() != "IE":
            lines.append(f"Производитель {self.manufacturer}")
        else:
            lines.append(" ")  # Пустая строка для сохранения позиционирования

        # Печатаем копии
        for _ in range(data["copies"]):
            hdc.StartPage()
            hdc.SelectObject(font)

            # Две полоски на странице
            for copy in range(2):
                y_pos = margin_top + (copy * true_between_labels)

                for line in lines:
                    hdc.TextOut(margin_left, y_pos, line)
                    y_pos += line_spacing

            hdc.EndPage()

        hdc.EndDoc()
        hdc.DeleteDC()