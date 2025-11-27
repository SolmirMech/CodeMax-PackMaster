import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, StringVar, BooleanVar
from datetime import datetime
from core.excel_exporter import WeightOrdersExporter
from core.config_manager import ConfigManager

class RollLabelPrinter:
    """Управление заказами с весом"""
    def __init__(self, parent):
        self.parent = parent
        self.config_manager = ConfigManager()

        self.order_data_module = None
        self.preview_module = None
        
        # Переменные интерфейса и данных
        self.show_manufacturer_var = BooleanVar(value=False)  # Показывать производителя
        self.show_manufacturer_var.trace_add("write", self._on_producer_visibility_changed)
        # Выбор производителя
        self.manufacturer_var = StringVar(value="")
        self.product_type_var = StringVar(value="")
        self.manual_manufacturer_selection = False
        self.manual_product_selection = False
        self.customer_var = StringVar(value="")  # Наименование заказчика
        self.gross_weight_kg_var = StringVar(value="")  # Вес ролика брутто в кг
        self.net_weight_kg_var = StringVar(value="")  # Вес ролика нетто в кг (авторасчет)
        self.order_prefix = StringVar(value="Ф")  # Префикс номера заказа (например, "Ф")
        self.order_number = StringVar(value="")  # Основной номер заказа
        self.order_suffix = StringVar(value="/5")  # Суффикс номера заказа (например, "/5")
        self.date_var = StringVar(value=datetime.now().strftime("%d.%m.%Y"))  # Дата изготовления
        self.packer_var = StringVar(value="")  # ФИО упаковщика
        self.quantity_var = StringVar(value="")  # Количество этикеток в одном ролике
        self.sleeve_weight_var = StringVar(value="50")  # Вес втулки в граммах
        self.winding_scheme_var = StringVar(value="7")  # Схема намотки
        self.sleeve_diameter_var = StringVar(value="76")  # Диаметр втулки в мм
        self.rolls_count_var = StringVar(value="1")  # Количество роликов в коробке
        self.total_quantity_var = StringVar(value="")  # Общее количество этикеток (авторасчет)
        self.total_gross_var = StringVar(value="")  # Общий вес коробки брутто в кг (авторасчет)
        self.total_net_var = StringVar(value="")  # Общий вес коробки нетто в кг (авторасчет)
        self.box_weight_var = StringVar(value="0.0")  # Вес пустой коробки в кг
        self.box_size_var = StringVar(value="")  # Размер коробки (выбирается из списка)
        self.date_emission_var = StringVar(value="") # Дата эмиссии кодов
        self.cutter_var = StringVar(value="")
        self.roll_length = StringVar(value="")
        
        self.create_ui()
        self.load_box_sizes()       
        # Отслеживаем изменения всех переменных, влияющих на расчет веса
        variables_to_track = [
            self.rolls_count_var,
            self.box_weight_var, 
            self.gross_weight_kg_var,
            self.net_weight_kg_var
        ]
        
        for var in variables_to_track:
            var.trace_add("write", self.calculate_box_weights)
        self.quantity_var.trace_add("write", self.calculate_total_quantity)
        
    def calculate_box_weights(self, *args):
        """Автоматически рассчитывает вес коробки брутто и нетто"""
        try:
            rolls_count = int(self.rolls_count_var.get() or 0)
            box_weight_kg = self.parse_float(self.box_weight_var.get() or 0)
            
            if rolls_count == 0:
                self.total_gross_var.set("")
                self.total_net_var.set("")
                return
            
            # Бери значения прямо из полей ввода:
            roll_gross_kg = self.parse_float(self.gross_weight_kg_var.get() or 0)
            roll_net_kg = self.parse_float(self.net_weight_kg_var.get() or 0)
            
            if roll_gross_kg == 0:
                self.total_gross_var.set("")
                self.total_net_var.set("")
                return
            
            # Рассчитываем общий вес роликов
            total_rolls_gross = rolls_count * roll_gross_kg
            total_rolls_net = rolls_count * roll_net_kg
            
            # Добавляем вес коробки к брутто (НЕ к нетто!)
            total_gross = total_rolls_gross + box_weight_kg
            total_net = total_rolls_net  # Вес коробки НЕ добавляется к нетто
            
            # Обновляем поля
            self.total_gross_var.set(f"{total_gross:.2f}")
            self.total_net_var.set(f"{total_net:.2f}")
            
        except (ValueError, TypeError) as e:
            print(f"Ошибка расчета весов: {e}")
            
    def _on_producer_visibility_changed(self, *args):
        """Обрабатывает изменение видимости производителя"""
        show_manufacturer = self.show_manufacturer_var.get()

    def create_ui(self):
        """Создает интерфейс для печати этикеток на ролик"""
        frame = ttk.Frame(self.parent, padding=5)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Добавляем стиль для автоматического выбора
        style = ttk.Style()
        style.configure("AutoSelect.TCombobox", fieldbackground="#fffacd")  # Светло-желтый фон

        # Основной контейнер для данных
        data_frame = ttk.LabelFrame(
            frame, text="Данные для этикетки", padding=5
        )
        data_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        # Изготовитель и тип продукта
        manufacturer_frame = ttk.Frame(data_frame)
        manufacturer_frame.grid(row=0, column=0, columnspan=2, sticky="w", pady=2)

        ttk.Label(manufacturer_frame, text="Изготовитель:").grid(row=0, column=0, sticky="w", padx=(0, 5), pady=2)
        self.manufacturer_combo = ttk.Combobox(
            manufacturer_frame, 
            textvariable=self.manufacturer_var,
            state="readonly",
            width=20
        )
        self.manufacturer_combo.grid(row=0, column=0, sticky="w", padx=(150, 10), pady=2)
        self.manufacturer_combo.bind('<<ComboboxSelected>>', self.on_manufacturer_selected)

        ttk.Label(manufacturer_frame, text="ТУ:").grid(row=0, column=2, sticky="w", padx=(0, 5), pady=2)
        self.product_combo = ttk.Combobox(
            manufacturer_frame, 
            textvariable=self.product_type_var,
            state="readonly", 
            width=25
        )
        self.product_combo.grid(row=0, column=2, padx=(40, 5), sticky="w", pady=2)
        self.product_combo.bind('<<ComboboxSelected>>', self.on_product_selected)
        
        # "Без изготовителя"
        ttk.Checkbutton(
            manufacturer_frame, 
            text="Без изготовителя", 
            variable=self.show_manufacturer_var
        ).grid(row=1, column=0, sticky="w", padx=5, pady=5)

        # Загружаем опции
        self.load_manufacturer_options()

        # Заказчик
        ttk.Label(data_frame, text="Заказчик:").grid(
            row=1, column=0, sticky="w", pady=5
        )
        customer_entry = ttk.Entry(data_frame, textvariable=self.customer_var, font=("Arial", 12), width=35)
        customer_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        self.add_context_menu(customer_entry)
        customer_entry.bind("<Control-KeyPress>", self.control_key_handler)
        self.customer_var.trace_add("write", self.on_customer_changed)

        # Изделие (многострочное поле)
        ttk.Label(data_frame, text="Изделие:").grid(
            row=2, column=0, sticky="nw", pady=5
        )
        
        # Многострочное текстовое поле
        self.product_text = tk.Text(data_frame, width=35, height=4, font=("Arial", 12))
        self.product_text.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        
        # Контекстное меню для текстового поля
        self.add_context_menu_to_text(self.product_text)
        
        ttk.Label(data_frame, text="Кол-во этикеток/роликов:", foreground="green").grid(
            row=4, column=0, sticky="w", pady=5
        )
        # Кол-во этикеток в одном ролике
        quantity_entry = ttk.Entry(data_frame, textvariable=self.quantity_var, width=15)
        quantity_entry.grid(row=4, column=1, padx=5, pady=5, sticky="w")
        # Кол-во роликов
        rolls_entry = ttk.Entry(data_frame, textvariable=self.rolls_count_var, width=15)
        rolls_entry.grid(row=4, column=1, padx=(115, 0), pady=5, sticky="w")
        rolls_entry.bind("<KeyRelease>", self.calculate_total_quantity)

        # Вес рулона
        ttk.Label(data_frame, text="Вес ролика брутто, кг:").grid(
            row=5, column=0, sticky="w", pady=5
        )
        gross_entry = ttk.Entry(data_frame, textvariable=self.gross_weight_kg_var, width=15)
        gross_entry.grid(row=5, column=1, padx=(5, 0), pady=5, sticky="w")
        
        # Вес втулки
        ttk.Label(data_frame, text="Вес втулки, г:").grid(
            row=5, column=1, sticky="w", padx=(115, 0), pady=5
        )        
        sleeve_entry = ttk.Entry(data_frame, textvariable=self.sleeve_weight_var, width=10)
        sleeve_entry.grid(row=5, column=1, padx=(270, 0), pady=5, sticky="w")

        # Номер заказа (3 части)
        ttk.Label(data_frame, text="№ заказа:").grid(
            row=7, column=0, sticky="w", pady=5
        )
        entry_prefix = ttk.Entry(data_frame, textvariable=self.order_prefix, width=4)
        entry_prefix.grid(row=7, column=1, padx=(5, 0), pady=5, sticky="w")

        entry_number = ttk.Entry(data_frame, textvariable=self.order_number, width=7)
        entry_number.grid(row=7, column=1, padx=(42, 0), pady=5, sticky="w")
        entry_number.bind("<Return>", lambda e: self.order_data_module.get_product_name())

        entry_suffix = ttk.Entry(data_frame, textvariable=self.order_suffix, width=6)
        entry_suffix.grid(row=7, column=1, padx=(95, 0), pady=5, sticky="w")     

        # Дата/Упаковщик
        ttk.Label(data_frame, text="Упаковщик/ Дата:").grid(
            row=8, column=0, sticky="w", pady=5
        )
        
        packers = self.config_manager.get_packers()
        default_packer = packers[0] if packers else ""
        self.packer_var = StringVar(value=default_packer)
        
        self.packer_combo = ttk.Combobox(
            data_frame, 
            textvariable=self.packer_var,
            values=packers,
            state="readonly",
            width=15
        )
        self.packer_combo.grid(row=8, column=1, padx=5, pady=5, sticky="w")
        
        # Дата
        date_entry = ttk.Entry(data_frame, textvariable=self.date_var, width=12)
        date_entry.grid(row=8, column=1, padx=(135, 0), pady=5, sticky="w")
        
        ttk.Label(data_frame, text="Резчик:").grid(
            row=9, column=0, sticky="w", pady=5
        )
        
        cutters = self.config_manager.get_cutters()
        default_cutter = self.config_manager.get_default_cutter()
        self.cutter_var = StringVar(value=default_cutter)
        
        self.cutter_combo = ttk.Combobox(
            data_frame, 
            textvariable=self.cutter_var,
            values=cutters,
            state="readonly", 
            width=15
        )
        self.cutter_combo.grid(row=9, column=1, padx=5, pady=5, sticky="w")             
        
        # Схема намотки и Диаметр втулки
        ttk.Label(data_frame, text="Схема намотки:").grid(
            row=10, column=0, sticky="w", pady=5
        )
        winding_entry = ttk.Entry(data_frame, textvariable=self.winding_scheme_var, width=5)
        winding_entry.grid(row=10, column=0, padx=(190, 0), pady=5, sticky="w")
        
        ttk.Label(data_frame, text="Диаметр втулки, мм:").grid(
            row=10, column=1, sticky="w", pady=5
        )
        diameter_entry = ttk.Entry(data_frame, textvariable=self.sleeve_diameter_var, width=5)
        diameter_entry.grid(row=10, column=1, padx=(210, 0), pady=5, sticky="w")                                         
        
        ttk.Label(data_frame, text="Длина ролика, м").grid(
            row=11, column=0, sticky="w", pady=5
        )              
        roll_length_entry = ttk.Entry(data_frame, textvariable=self.roll_length, width=8)
        roll_length_entry.grid(row=11, column=0, padx=(165, 0), pady=5, sticky="w")
        
        self.gross_weight_kg_var.trace_add("write", self.calculate_net_weight)
        self.sleeve_weight_var.trace_add("write", self.calculate_net_weight)
        self.order_prefix.trace_add("write", self.on_order_number_changed)
        
    def load_manufacturer_options(self):
        """Загружает варианты производителей из packaging_tu.json"""
        try:
            packaging_data = self.config_manager.load_json_settings("packaging_tu.json")
            technical_specs = packaging_data.get("technical_specifications", [])
            
            # Собираем уникальных производителей
            manufacturers = set()
            manufacturer_products = {}
            
            for spec in technical_specs:
                manufacturer = spec["manufacturer"]["name"]
                product = spec["product"]["name"]
                manufacturers.add(manufacturer)
                
                if manufacturer not in manufacturer_products:
                    manufacturer_products[manufacturer] = []
                manufacturer_products[manufacturer].append(product)
            
            self.manufacturer_options = sorted(manufacturers)
            self.manufacturer_products_map = manufacturer_products
            
            # Устанавливаем комбобоксы
            self.manufacturer_combo['values'] = self.manufacturer_options
            if self.manufacturer_options:
                self.manufacturer_var.set("ООО \"Ремас-Флексо\"")  # По умолчанию
                self.update_product_options()
                
        except Exception as e:
            print(f"Ошибка загрузки производителей: {e}")

    def update_product_options(self):
        """Обновляет список продуктов для выбранного производителя"""
        manufacturer = self.manufacturer_var.get()
        if manufacturer in self.manufacturer_products_map:
            products = self.manufacturer_products_map[manufacturer]
            self.product_combo['values'] = products
            if products:
                self.product_type_var.set("Обычная с\к этикетка")  # По умолчанию
        else:
            self.product_combo['values'] = []
            self.product_type_var.set("")

    def on_product_selected(self, event=None):
        """Обрабатывает выбор типа продукта"""
        self.manual_product_selection = True

    def on_order_number_changed(self, *args):
        """Автоматически выбирает производителя для IE заказов"""
        if self.manual_manufacturer_selection:
            return  # Не переопределяем ручной выбор
            
        order_prefix = self.order_prefix.get()
        if order_prefix == 'IE':
            # Автоматически выбираем Зюдина
            self.manufacturer_var.set("ИП Зюдин В.Г.")
            self.update_product_options()
            self.product_type_var.set("Обычная с\к этикетка")
            
            # Визуальное выделение автоматического выбора
            self.manufacturer_combo.configure(style="AutoSelect.TCombobox")
            self.product_combo.configure(style="AutoSelect.TCombobox")
        else:
            # Возвращаем ремас-флексо при любом другом префиксе
            self.manufacturer_var.set("ООО \"Ремас-Флексо\"")
            self.update_product_options()
            self.product_type_var.set("Обычная с\к этикетка")
            
            # Сбрасываем стиль для не-IE заказов
            self.manufacturer_combo.configure(style="TCombobox")
            self.product_combo.configure(style="TCombobox")

    def on_manufacturer_selected(self, event=None):
        """Обрабатывает выбор производителя"""
        # Запоминаем, что для текущего заказа сделан ручной выбор
        self.last_manual_order = self.order_number.get()
        self.update_product_options()
        
        # Сбрасываем ручной выбор продукта при смене производителя
        if self.product_combo['values']:
            self.product_type_var.set("Обычная с\к этикетка")
        
        # Обновляем превью при смене производителя
        if hasattr(self, 'preview_module') and self.preview_module:
            self.preview_module.update_preview_displays()

    def update_manufacturer_visibility(self):
        """Обновляет видимость производителя на основе выбора"""
        manufacturer = self.manufacturer_var.get()
        # Показываем производителя если НЕ выбран "Без производителя"
        self.show_manufacturer_var.set(manufacturer == "Без производителя")
        
    def check_manufacturer_visibility(self, customer_name):
        """Проверяет нужно ли показывать производителя для заказчика"""
        if customer_name:
            # Используем config_manager для поиска в without_manufacturer
            found_customer = self.config_manager.find_customer(customer_name)
            # Если заказчик найден в списке without_manufacturer - ставим чекбокс (True = "Без производителя")
            self.show_manufacturer_var.set(found_customer is not None)
        else:
            # Если заказчик пустой - сбрасываем чекбокс
            self.show_manufacturer_var.set(False)
            
    def on_customer_changed(self, *args):
        """Обрабатывает изменение заказчика и проверяет видимость производителя"""
        customer_name = self.customer_var.get()
        self.check_manufacturer_visibility(customer_name)              
        
    def set_preview_module(self, preview_module):
        """Устанавливает связь с модулем предпросмотра для обратной связи"""
        self.preview_module = preview_module
        
    def parse_float(self, value):
        """Преобразует строку в float, заменяя запятую на точку"""
        if isinstance(value, str):
            return float(value.replace(',', '.'))
        return float(value)        
        
    def load_box_sizes(self):
        """Загружает список коробок из shared_utils.json"""
        try:
            settings = self.config_manager.load_json_settings("shared_utils.json")
            weight_box = settings.get("weight_box", {})
            box_sizes = list(weight_box.keys())
            
            return box_sizes
            
        except Exception as e:
            print(f"Ошибка загрузки списка коробок: {e}")
            return []

    def on_box_selected(self, event=None):
        """Обрабатывает выбор коробки из списка"""
        selected_size = self.box_size_var.get()
        if selected_size:
            try:
                settings = self.config_manager.load_json_settings("shared_utils.json")
                weight_box = settings.get("weight_box", {})
                box_weight_g = weight_box.get(selected_size, 0)
                box_weight_kg = box_weight_g / 1000.0
                self.box_weight_var.set(f"{box_weight_kg:.2f}")
                
                # Запускаем пересчет весов
                self.calculate_box_weights()
                
            except Exception as e:
                print(f"Ошибка загрузки веса коробки: {e}")
        
    def calculate_total_quantity(self, *args):
        """Рассчитывает общее количество: ролики × этикетки в ролике"""
        try:
            rolls_count = int(self.rolls_count_var.get() or 0)
            quantity_per_roll = int(self.quantity_var.get() or 0)
            
            if rolls_count == 0 or quantity_per_roll == 0:
                self.total_quantity_var.set("")
                return
                
            total = rolls_count * quantity_per_roll
            self.total_quantity_var.set(str(total))
            
        except (ValueError, TypeError):
            self.total_quantity_var.set("")
        
    def export_box_to_excel(self):
        """Экспортирует данные коробки в Excel"""
        try:
            # Проверяем, что все необходимые данные заполнены
            if not self.rolls_count_var.get() or not self.order_number.get():
                return {'success': False, 'error': 'Введите количество роликов и номер заказа'}

            # Проверяем наличие модуля данных
            if not hasattr(self, 'order_data_module') or not self.order_data_module:
                return {'success': False, 'error': 'Модуль данных не подключен'}
                
            # Загружаем путь к Excel файлу
            self.order_data_module.load_excel_folder_path()
            
            if not self.order_data_module.excel_file_path:
                return {'success': False, 'error': 'Сначала выберите папку для Excel'}

            # Создаем экспортер и выполняем экспорт
            exporter = WeightOrdersExporter(
                excel_file_path=self.order_data_module.excel_file_path,
                roll_module=self,
                preview_module=self.preview_module
            )
            
            result = exporter.export_data()  # enable_pallet=False по умолчанию
            
            return result  # Просто возвращаем результат
                
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def clear_box_excel_data(self):
        """Очищает данные коробки в Excel"""
        try:
            # Проверяем наличие модуля данных
            if not hasattr(self, 'order_data_module') or not self.order_data_module:
                return False
                
            # Загружаем путь к Excel файлу
            self.order_data_module.load_excel_folder_path()
            
            if not self.order_data_module.excel_file_path:
                return False
                
            if not os.path.exists(self.order_data_module.excel_file_path):
                return False

            # Создаем экспортер и выполняем очистку
            exporter = WeightOrdersExporter(
                excel_file_path=self.order_data_module.excel_file_path,
                roll_module=self,
                preview_module=self.preview_module
            )
            
            success = exporter.clear_all_rolls()  # enable_pallet=False по умолчанию
            return success
            
        except Exception as e:
            print(f"Ошибка при очистке Excel: {e}")
            return False
        
    def set_show_manufacturer(self, show):
        """Устанавливает видимость производителя извне"""
        self.show_manufacturer_var.set(show)        

    def set_order_data_module(self, order_data_module):
        """Устанавливает прямую связь с модулем обработки данных заказов"""
        self.order_data_module = order_data_module             
        
    def calculate_net_weight(self, *args):
        """Автоматически рассчитывает вес нетто"""
        try:
            gross_kg = self.parse_float(self.gross_weight_kg_var.get() or 0)
            
            # Если вес брутто 0 - очищаем нетто
            if gross_kg == 0:
                self.net_weight_kg_var.set("")
                self.total_gross_var.set("")
                self.total_net_var.set("")
                return
                
            sleeve_g = self.parse_float(self.sleeve_weight_var.get() or 0)
            sleeve_kg = sleeve_g / 1000
            net_kg = gross_kg - sleeve_kg
            
            # Если результат отрицательный или нулевой - очищаем
            if net_kg <= 0:
                self.net_weight_kg_var.set("")
                self.total_gross_var.set("")
                self.total_net_var.set("")
            else:
                self.net_weight_kg_var.set(f"{net_kg:.2f}")
                
        except (ValueError, TypeError):
            self.net_weight_kg_var.set("")
        
    # Раздел для настройки поля ввода
    def control_key_handler(self, event):
        """Обработчик горячих клавиш Ctrl+C и Ctrl+V"""
        if event.keycode == 86 or event.keycode == 118:  # V key - вставка
            self.paste_text(event.widget)
            return "break"
        elif event.keycode == 67 or event.keycode == 99:  # C key - копирование
            self.copy_text(event.widget)
            return "break"
        return None
        
    def add_context_menu_to_text(self, text_widget):
        """Добавляет контекстное меню к текстовому виджету"""
        menu = tk.Menu(text_widget, tearoff=0)
        menu.add_command(label="Копировать", command=lambda: self.copy_text_from_text_widget(text_widget))
        menu.add_command(label="Вставить", command=lambda: self.paste_text_to_text_widget(text_widget))
        text_widget.bind("<Button-3>", lambda e: menu.tk_popup(e.x_root, e.y_root))

    def copy_text_from_text_widget(self, widget):
        """Копирует текст из текстового виджета"""
        try:
            text = widget.get("1.0", "end-1c")
            if text:
                widget.clipboard_clear()
                widget.clipboard_append(text)
        except Exception as e:
            print(f"Ошибка копирования: {e}")

    def paste_text_to_text_widget(self, widget):
        """Вставляет текст в текстовый виджет"""
        try:
            text = widget.clipboard_get()
            if text:
                widget.delete("1.0", tk.END)
                widget.insert("1.0", text)
        except Exception as e:
            print(f"Ошибка вставки: {e}")        
        
    def add_context_menu(self, widget):
        """Добавляет контекстное меню к виджету"""
        menu = tk.Menu(widget, tearoff=0)
        menu.add_command(label="Копировать", command=lambda: self.copy_text(widget))
        menu.add_command(label="Вставить", command=lambda: self.paste_text(widget))
        widget.bind("<Button-3>", lambda e: menu.tk_popup(e.x_root, e.y_root))

    def copy_text(self, widget):
        """Копирует текст в буфер обмена"""
        try:
            text = widget.get()
            if text:
                widget.clipboard_clear()
                widget.clipboard_append(text)
        except Exception as e:
            print(f"Ошибка копирования: {e}")

    def paste_text(self, widget):
        """Вставляет текст из буфера обмена"""
        try:
            text = widget.clipboard_get()
            if text:
                widget.delete(0, tk.END)
                widget.insert(0, text)
        except Exception as e:
            print(f"Ошибка вставки: {e}")

