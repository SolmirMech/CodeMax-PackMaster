import os
import sys
import re
import tkinter as tk
from tkinter import ttk, messagebox, StringVar, BooleanVar
import math
from datetime import datetime


class RollLabelPrinter:
    """Управление заказами с весом"""
    def __init__(self, parent, coordinator=None, data_manager=None, config_manager=None):
        self.parent = parent
        self.config_manager = config_manager
        self.data_manager = data_manager
        self.config_manager.ensure_packaging_tu_exists()
        self.coordinator = coordinator

        self.order_data_module = None
        self.preview_module = None
        
        order_settings = self.config_manager.load_json_settings("shared_utils.json").get("order_number", {})
        self.order_prefix = StringVar(value=order_settings.get("prefix", "Ф"))
        self.order_suffix = StringVar(value=order_settings.get("suffix", "/5"))        
        
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
        self.order_number = StringVar(value="")  # Основной номер заказа
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
        # Раздел 2 цеха
        self.cutter_var = StringVar(value="") # Резчик
        self.roll_length = StringVar(value="") # Длина ролика
        self.label_length_mm = StringVar(value="") # Длина этикетки
        self.batch_num_var = StringVar(value="")  # № съёма
        self.roll_num_var = StringVar(value="")   # № ролика  
        self.streams_var = StringVar(value="")    # Кол-во ручьёв
        self.stream_width_var = StringVar(value="")  # Ширина ручья в мм
        self.xml_tu_number = ""
        self.cached_order_data = None
        self.cached_order_number = ""
        # Флаг для оптимизации
        self._skip_weight_calculation = False
        self._weight_timer = None
        self._quantity_timer = None
        self._length_timer = None
        self._normalize_cache = {}
        self.manufacturer_full_data_map = {}  # Новая структура загрузки производителей
        # Росинка
        self.rosinka_var = BooleanVar(value=False)
        self.ros_podlo_var = StringVar(value="")  # Подложка для Росинки
        self.ros_size_var = StringVar(value="")  # Размер этикетки для Росинки
                    
        self.create_ui()
        self.load_box_sizes()
        if self.coordinator and hasattr(self.coordinator, 'subscribe'):
            self.coordinator.subscribe(self.on_settings_changed)
            self._update_cutter_visibility()
            self.load_sleeve_weights()
        # Отслеживаем изменения всех переменных, влияющих на расчет веса
        # Оставляем только одну подписку на каждую переменную
        self.gross_weight_kg_var.trace_add("write", self._on_weight_changed)
        self.sleeve_weight_var.trace_add("write", self._on_weight_changed)
        self.rolls_count_var.trace_add("write", self._on_weight_changed)
        self.box_weight_var.trace_add("write", self._on_weight_changed)
        
        # Отдельно для quantity
        self.quantity_var.trace_add("write", self.calculate_total_quantity)
        
    def _on_weight_changed(self, *args):
        """Единый обработчик изменений веса"""
        # ПРОВЕРКА 1: Пропускаем если это программная очистка
        if hasattr(self, '_skip_weight_calculation') and self._skip_weight_calculation:
            return
        
        # ПРОВЕРКА 2: Пропускаем если вес отключен
        if not self.show_weight_var.get():
            return
        
        # ПРОВЕРКА 3: Дебаунсинг - безопасно отменяем предыдущий таймер
        if hasattr(self, '_weight_timer') and self._weight_timer is not None:
            try:
                self.parent.after_cancel(self._weight_timer)
            except (ValueError, TypeError):
                # Игнорируем ошибки отмены (таймер уже сработал или недействителен)
                pass
        
        # Устанавливаем новый таймер на 70ms
        self._weight_timer = self.parent.after(70, self._calculate_all_weights)

    def _calculate_all_weights(self):
        """Вычисляет все веса"""
        # Двойная проверка флагов (на всякий случай)
        if hasattr(self, '_skip_weight_calculation') and self._skip_weight_calculation:
            return
        if not self.show_weight_var.get():
            return
        
        try:
            # Локальные ссылки на часто используемые переменные
            gross_var = self.gross_weight_kg_var
            sleeve_var = self.sleeve_weight_var
            rolls_var = self.rolls_count_var
            box_var = self.box_weight_var
            net_var = self.net_weight_kg_var
            total_gross_var = self.total_gross_var
            total_net_var = self.total_net_var
            
            # 1. Быстрый парсинг значений
            gross_str = gross_var.get().strip()
            if not gross_str:
                # Если поле пустое - очищаем все и выходим
                net_var.set("")
                total_gross_var.set("")
                total_net_var.set("")
                return
            
            # Пробуем быстро распарсить
            try:
                gross_kg = float(gross_str.replace(',', '.'))
            except ValueError:
                # Если не число - очищаем все
                net_var.set("")
                total_gross_var.set("")
                total_net_var.set("")
                return
            
            # 2. Парсим остальные значения только если gross_kg > 0
            if gross_kg <= 0:
                net_var.set("")
                total_gross_var.set("")
                total_net_var.set("")
                return
            
            # Парсим вес втулки
            sleeve_str = sleeve_var.get().strip()
            sleeve_g = float(sleeve_str.replace(',', '.')) if sleeve_str else 0
            
            # Рассчитываем нетто
            sleeve_kg = sleeve_g / 1000
            net_kg = max(gross_kg - sleeve_kg, 0)
            
            # Устанавливаем нетто
            if net_kg > 0:
                net_var.set(f"{net_kg:.2f}")
            else:
                net_var.set("")
            
            # 3. Рассчитываем вес коробки (если нужно)
            rolls_str = rolls_var.get().strip()
            if rolls_str:
                try:
                    rolls_count = int(rolls_str)
                    if rolls_count > 0:
                        # Парсим вес коробки
                        box_str = box_var.get().strip()
                        box_weight_kg = float(box_str.replace(',', '.')) if box_str else 0
                        
                        # Рассчитываем
                        total_rolls_gross = rolls_count * gross_kg
                        total_rolls_net = rolls_count * net_kg
                        
                        total_gross = total_rolls_gross + box_weight_kg
                        total_net = total_rolls_net
                        
                        total_gross_var.set(f"{total_gross:.2f}")
                        total_net_var.set(f"{total_net:.2f}")
                    else:
                        total_gross_var.set("")
                        total_net_var.set("")
                except ValueError:
                    total_gross_var.set("")
                    total_net_var.set("")
            else:
                total_gross_var.set("")
                total_net_var.set("")         
                
        except Exception:
            # При любой ошибке очищаем расчетные поля
            net_var.set("")
            total_gross_var.set("")
            total_net_var.set("")
            
        if hasattr(self, 'coordinator') and self.coordinator:
            self.coordinator.check_weight_status(self)
        if hasattr(self, 'preview_module') and self.preview_module:
            # Обновляем данные в preview_module
            self.preview_module._update_from_connected_roll_module()
            
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

        ttk.Label(manufacturer_frame, text="ТУ:").grid(row=0, column=0, sticky="w", padx=(305, 5), pady=2)
        self.product_combo = ttk.Combobox(
            manufacturer_frame, 
            textvariable=self.product_type_var,
            state="readonly", 
            width=25
        )
        self.product_combo.grid(row=0, column=0, padx=(345, 5), sticky="w", pady=2)
        self.product_combo.bind('<<ComboboxSelected>>', self.on_product_selected)
        
        # "Без изготовителя"
        ttk.Checkbutton(
            manufacturer_frame, 
            text="Без изготовителя", 
            variable=self.show_manufacturer_var
        ).grid(row=1, column=0, sticky="w", padx=5, pady=5)
        
        # Упаковщик
        ttk.Label(manufacturer_frame, text="Упаковка").grid(
            row=1, column=0, sticky="w", padx=(200, 5), pady=5
        )
        
        packers = self.config_manager.get_packers()
        default_packer = packers[0] if packers else ""
        self.packer_var = StringVar(value=default_packer)
        
        self.packer_combo = ttk.Combobox(
            manufacturer_frame, 
            textvariable=self.packer_var,
            values=packers,
            state="readonly",
            width=15
        )
        self.packer_combo.grid(row=1, column=0, padx=(295, 5), pady=5, sticky="w")
        
        # Резчик
        self.cutter_label = ttk.Label(manufacturer_frame, text="Резка")
        self.cutter_label.grid(row=1, column=0, sticky="w", padx=(415, 5), pady=5)
        
        cutters = self.config_manager.get_cutters()
        default_cutter = self.config_manager.get_default_cutter()
        self.cutter_var = StringVar(value=default_cutter)
        
        self.cutter_combo = ttk.Combobox(
            manufacturer_frame, 
            textvariable=self.cutter_var,
            values=cutters,
            state="readonly", 
            width=15
        )
        self.cutter_combo.grid(row=1, column=0, padx=(480, 5), pady=5, sticky="w")        

        # Загружаем опции
        self.load_manufacturer_options()        

        # Заказчик: Начало данных
        ttk.Label(data_frame, text="Заказчик:").grid(
            row=1, column=0, sticky="w", pady=5
        )
        customer_entry = ttk.Entry(data_frame, textvariable=self.customer_var, font=("Arial", 12), width=35)
        customer_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        self.add_context_menu(customer_entry)
        customer_entry.bind("<Control-KeyPress>", self.control_key_handler)
        self.customer_var.trace_add("write", self.on_customer_changed)

        # Изделие
        # Фрейм для левой колонки (Изделие и галочка)
        left_frame = ttk.Frame(data_frame)
        left_frame.grid(row=2, column=0, sticky="nw", pady=5)
        
        # Изделие (вверху фрейма)
        ttk.Label(left_frame, text="Изделие:").pack(anchor="w")
        
        # Галочка "Сократить текст" (под надписью)
        self.shorten_text_var = BooleanVar(value=False)
        self.shorten_checkbutton = ttk.Checkbutton(
            left_frame,
            text="Сократить текст",
            variable=self.shorten_text_var,
            command=self._on_shorten_text_changed
        )
        self.shorten_checkbutton.pack(anchor="w", pady=(5, 0))
        
        # Галочка Росинка
        self.rosinka_checkbutton = ttk.Checkbutton(
            left_frame,
            text="Росинка",
            variable=self.rosinka_var,
            command=self._on_rosinka_toggled  # Используем существующий механизм уведомлений
        )
        self.rosinka_checkbutton.pack(anchor="w", pady=(5, 0))
    
        # Многострочное текстовое поле
        self.product_text = tk.Text(data_frame, width=35, height=4, font=("Arial", 12))
        self.product_text.grid(row=2, column=1, padx=5, pady=5, sticky="w")        
        # Контекстное меню для текстового поля
        self.add_context_menu_to_text(self.product_text)
        self.product_text.bind("<Control-KeyPress>", self.control_key_handler_text)
        self.product_text.bind("<Return>", self.search_in_product_text)
        
        # Подложка Росинки
        self.podlo_label = ttk.Label(data_frame, text="Подложка:")
        self.podlo_entry = ttk.Entry(data_frame, textvariable=self.ros_podlo_var, width=35)
        # Сразу скрываем, т.к. показываться будет только при включении галочки Росинка
        self.podlo_label.grid(row=3, column=1, sticky="w", pady=3)
        self.podlo_entry.grid(row=3, column=1, padx=(115, 0), pady=3, sticky="w")
        self.podlo_entry.bind("<Control-KeyPress>", self.control_key_handler)
        self.podlo_label.grid_remove()
        self.podlo_entry.grid_remove()        
        
        # Основные поля ввода
        
        # Номер заказа (3 части)
        ttk.Label(data_frame, text="№ заказа:").grid(
            row=4, column=0, sticky="w", pady=5
        )
        entry_prefix = ttk.Entry(data_frame, textvariable=self.order_prefix, width=4)
        entry_prefix.grid(row=4, column=1, padx=(5, 0), pady=5, sticky="w")

        entry_number = ttk.Entry(data_frame, textvariable=self.order_number, width=7)
        entry_number.grid(row=4, column=1, padx=(42, 0), pady=5, sticky="w")
        entry_number.bind("<Return>", lambda e: self.on_order_enter_pressed(e))
        entry_number.bind("<Down>", lambda e: self.quantity_entry.focus_set())
        entry_number.bind("<FocusIn>", lambda e: entry_number.select_range(0, tk.END))
        self.order_entry = entry_number
        
        # Добавляем комбобокс выбора заказа (скрыт изначально)
        self.order_combobox = ttk.Combobox(
            data_frame, 
            width=7,
            state="readonly"
        )
        self.order_combobox.grid(row=4, column=1, padx=(42, 0), pady=5, sticky="w")
        self.order_combobox.bind("<<ComboboxSelected>>", self.on_order_selected)
        self.order_combobox.grid_remove()  # Скрываем изначально

        entry_suffix = ttk.Entry(data_frame, textvariable=self.order_suffix, width=6)
        entry_suffix.grid(row=4, column=1, padx=(95, 0), pady=5, sticky="w")
        self.entry_suffix = entry_suffix     
        
        
        date_update_label = tk.Label(
            data_frame,
            text="🔄",
            font=("Arial", 18),
            cursor="hand2"
        )
        date_update_label.grid(row=4, column=1, sticky="w", padx=(200, 0), pady=5)
        date_update_label.bind("<Button-1>", lambda e: self.update_date_field())
        # Дата
        self.date_entry = ttk.Entry(data_frame, textvariable=self.date_var, width=12)
        self.date_entry.grid(row=4, column=1, padx=(240, 0), pady=5, sticky="w")        
        
        ttk.Label(data_frame, text="Кол-во этикеток/роликов:", foreground="green").grid(
            row=5, column=0, sticky="w", pady=2
        )
        # Кол-во этикеток в одном ролике
        quantity_entry = ttk.Entry(data_frame, textvariable=self.quantity_var, width=15)
        quantity_entry.grid(row=5, column=1, padx=5, pady=2, sticky="w")
        quantity_entry.bind("<Up>", lambda e: self.order_entry.focus_set())
        quantity_entry.bind("<FocusIn>", lambda e: quantity_entry.select_range(0, tk.END))
        self.quantity_entry = quantity_entry
        
        # Кол-во роликов
        rolls_entry = ttk.Entry(data_frame, textvariable=self.rolls_count_var, width=15)
        rolls_entry.grid(row=5, column=1, padx=(115, 0), pady=2, sticky="w")
        rolls_entry.bind("<KeyRelease>", self.calculate_total_quantity)
        
        # Добавляем галочку "Вес"
        self.show_weight_var = BooleanVar(value=False)
        self.weight_checkbutton = ttk.Checkbutton(
            data_frame,
            text="Вес",
            variable=self.show_weight_var,
            command=self.toggle_weight_visibility
        )
        self.weight_checkbutton.grid(row=5, column=1, padx=(240, 10), pady=2, sticky="w")
        
        # Дополнительные поля:
        
        # Вес рулона
        self.weight_label = ttk.Label(data_frame, text="Вес ролика брутто, кг:")
        self.weight_label.grid(row=6, column=0, sticky="w", pady=3)
        
        self.gross_entry = ttk.Entry(data_frame, textvariable=self.gross_weight_kg_var, width=15)
        self.gross_entry.grid(row=6, column=1, padx=(5, 0), pady=3, sticky="w")
        
        # Вес втулки
        self.sleeve_label = ttk.Label(data_frame, text="Вес втулки, г:")
        self.sleeve_label.grid(row=6, column=1, sticky="w", padx=(115, 0), pady=3)
        self.sleeve_entry = ttk.Entry(data_frame, textvariable=self.sleeve_weight_var, width=7)
        self.sleeve_entry.grid(row=6, column=1, padx=(265, 0), pady=3, sticky="w")
        
        # Длина ролика
        self.roll_length_label = ttk.Label(data_frame, text="Длина ролика, м:")
        self.roll_length_label.grid(row=7, column=0, sticky="w", pady=2)
        self.roll_length_entry = ttk.Entry(data_frame, textvariable=self.roll_length, width=8)
        self.roll_length_entry.grid(row=7, column=0, padx=(183, 0), pady=2, sticky="w")
        
        # № съёма
        self.batch_label = ttk.Label(data_frame, text="№ съёма:")
        self.batch_label.grid(row=7, column=1, sticky="w", pady=3)
        self.batch_entry = ttk.Entry(data_frame, textvariable=self.batch_num_var, width=6)
        self.batch_entry.grid(row=7, column=1, padx=(100, 0), pady=3, sticky="w")

        # № ролика
        self.roll_label = ttk.Label(data_frame, text="№ ролика:")
        self.roll_label.grid(row=7, column=1, sticky="w", padx=(160, 0), pady=3)
        self.roll_entry = ttk.Entry(data_frame, textvariable=self.roll_num_var, width=7)
        self.roll_entry.grid(row=7, column=1, padx=(265, 0), pady=3, sticky="w")               
        
        # Ширина ручья
        self.stream_width_label = ttk.Label(data_frame, text="Ширина ручья, мм:")
        self.stream_width_label.grid(row=8, column=0, sticky="w", pady=2)
        self.stream_width_entry = ttk.Entry(data_frame, textvariable=self.stream_width_var, width=8)
        self.stream_width_entry.grid(row=8, column=0, padx=(183, 0), pady=2, sticky="w")
        
        # Длина этикетки
        self.label_length_label = ttk.Label(data_frame, text="Длина этикетки, мм:")
        self.label_length_label.grid(row=8, column=1, sticky="w", pady=2)
        self.label_length_entry = ttk.Entry(data_frame, textvariable=self.label_length_mm, width=7)
        self.label_length_entry.grid(row=8, column=1, padx=(265, 0), pady=2, sticky="w")         
        
        # Схема намотки
        self.winding_label = ttk.Label(data_frame, text="Схема намотки:")
        self.winding_label.grid(row=9, column=0, sticky="w", pady=3)       
        self.winding_entry = ttk.Entry(data_frame, textvariable=self.winding_scheme_var, width=8)
        self.winding_entry.grid(row=9, column=0, padx=(183, 0), pady=3, sticky="w")
        
        # Диаметр втулки
        self.diameter_label = ttk.Label(data_frame, text="Диаметр втулки, мм:")
        self.diameter_label.grid(row=9, column=1, sticky="w", pady=3)       
        self.diameter_entry = ttk.Entry(data_frame, textvariable=self.sleeve_diameter_var, width=7)
        self.diameter_entry.grid(row=9, column=1, padx=(265, 0), pady=3, sticky="w")
        
        # Кол-во ручьев      
        self.streams_label = ttk.Label(data_frame, text="Кол-во ручьев:")
        self.streams_label.grid(row=10, column=0, sticky="w", pady=3)
        self.streams_entry = ttk.Entry(data_frame, textvariable=self.streams_var, width=8)
        self.streams_entry.grid(row=10, column=0, padx=(183, 0), pady=3, sticky="w")
        
        self.order_prefix.trace_add("write", self.on_order_number_changed)
        self.roll_length.trace_add("write", self.calculate_quantity_from_length)
        self.label_length_mm.trace_add("write", self.calculate_quantity_from_length)
        self.stream_width_var.trace_add("write", lambda *args: self.update_sleeve_weight_from_settings())
        self.sleeve_diameter_var.trace_add("write", lambda *args: self.update_sleeve_weight_from_settings())
        self.toggle_weight_visibility()
        self.update_elements_visibility()
        self.update_rosinka_visibility()
        
    def _on_rosinka_toggled(self):
        """При включении/выключении галочки Росинка"""
        # Сохраняем текущие значения префикса и суффикса
        current_prefix = self.order_prefix.get()
        current_suffix = self.order_suffix.get()
        
        if self.coordinator:
            if self.rosinka_var.get():
                # Включаем - ставим шаблон "Росинка"
                self.coordinator.set_font_template("Росинка")
                # Показываем поле Подложка
                self.podlo_label.grid()
                self.podlo_entry.grid()
                # Извлекаем размер этикетки из БД
                self.extract_label_size_from_db()
            else:
                # Выключаем - возвращаем стандартный по цеху
                workshop = self.coordinator.get_workshop()
                default_template = "1_цех" if workshop == "1" else "2_цех"
                self.coordinator.set_font_template(default_template)
                # Скрываем поле Подложка
                self.podlo_label.grid_remove()
                self.podlo_entry.grid_remove()
                # Очищаем размер этикетки
                self.ros_size_var.set("")
            
            # Уведомляем всех
            self.coordinator.notify_list_changed("rosinka")
            
            # Восстанавливаем сохраненные значения
            self.order_prefix.set(current_prefix)
            self.order_suffix.set(current_suffix)
            
    def extract_label_size_from_db(self):
        """Извлекает размер этикетки из order_name для Росинки из кэша"""
        # Проверяем order_data_module
        if not hasattr(self, 'order_data_module') or not self.order_data_module:
            self.ros_size_var.set("")
            return
        
        # Проверяем кэш в order_data_module
        if not hasattr(self.order_data_module, 'cached_order_data') or not self.order_data_module.cached_order_data:
            self.ros_size_var.set("")
            return
        
        # Берем первый заказ из кэша order_data_module
        order_data = self.order_data_module.cached_order_data[0]
        order_name = order_data.get('order_name', '')
        
        if not order_name:
            self.ros_size_var.set("")
            return
        
        # Ищем паттерн размеров
        match = re.search(r'(\d+)\s*[хxХX\*]\s*(\d+)', order_name, re.IGNORECASE)
        
        if match:
            width = match.group(1)
            height = match.group(2)
            self.ros_size_var.set(f"{width}х{height} мм")
        else:
            self.ros_size_var.set("")            
        
    def _on_shorten_text_changed(self):
        """Обрабатывает изменение галочки сокращения текста"""
        if hasattr(self, 'order_data_module') and self.order_data_module:
            # Перезагружаем продукты с учетом новой настройки
            self.order_data_module.get_product_name()
        
    def update_date_field(self):
        """Обновляет поле даты на текущую дату"""
        try:
            # Запускаем фоновую проверку XML после обновления даты
            if hasattr(self, 'coordinator') and self.coordinator:
                self.coordinator.notify_list_changed("update_date_request")
            
            # Способ 1: PowerShell (наиболее надёжный)
            import subprocess
            try:
                result = subprocess.run(
                    ["powershell", "-Command", "Get-Date -Format 'dd.MM.yyyy'"],
                    capture_output=True,
                    text=True,
                    shell=True,
                    timeout=2,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                if result.returncode == 0:
                    current_date = result.stdout.strip()
                    if current_date and len(current_date) == 10:
                        # Отправляем сообщение в preview_module
                        self._show_date_message(f"Дата через PowerShell: {current_date}")
                        self.date_var.set(current_date)
                        return
            except Exception as e:
                print(f"PowerShell не сработал: {e}")
            
            # Способ 2: WMIC (универсальный для Windows)
            try:
                result = subprocess.run(
                    ['cmd', '/c', 'wmic os get localdatetime /value'],
                    capture_output=True,
                    text=True,
                    shell=True,
                    timeout=2,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                
                output = result.stdout
                if 'LocalDateTime' in output:
                    for line in output.split('\n'):
                        if line.startswith('LocalDateTime='):
                            dt_str = line.split('=')[1].strip()
                            year = dt_str[0:4]
                            month = dt_str[4:6]
                            day = dt_str[6:8]
                            current_date = f"{day}.{month}.{year}"
                            
                            # Отправляем сообщение в preview_module
                            self._show_date_message(f"Дата через WMIC: {current_date}")
                            self.date_var.set(current_date)
                            return
            except Exception as e:
                print(f"WMIC не сработал: {e}")
            
            # Способ 3: CMD %date% (последний шанс)
            try:
                result = subprocess.run(
                    ["cmd", "/c", "echo %date%"],
                    capture_output=True,
                    text=True,
                    shell=True,
                    timeout=2,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                if result.returncode == 0:
                    date_str = result.stdout.strip()
                    # Убираем лишние символы
                    date_str = date_str.split()[0] if ' ' in date_str else date_str
                    
                    # Пытаемся распарсить разные форматы
                    for sep in ['.', '/', '-']:
                        if sep in date_str:
                            parts = date_str.split(sep)
                            if len(parts) == 3:
                                day, month, year = parts[0], parts[1], parts[2]
                                # Если год короткий (YY) → расширяем
                                if len(year) == 2:
                                    year = f"20{year}"
                                current_date = f"{day.zfill(2)}.{month.zfill(2)}.{year}"
                                
                                # Отправляем сообщение в preview_module
                                self._show_date_message(f"Дата через CMD: {current_date}")
                                self.date_var.set(current_date)
                                return
            except Exception as e:
                print(f"CMD не сработал: {e}")
            
            # Способ 4: datetime.now() (аварийный вариант)
            try:
                current_date = datetime.now().strftime("%d.%m.%Y")
                # Отправляем сообщение в preview_module
                self._show_date_message(f"Дата через datetime.now(): {current_date}")
                self.date_var.set(current_date)
            except Exception as e:
                print(f"Все способы не сработали: {e}")
                self.date_var.set("Ошибка даты")
                self._show_date_message("Ошибка получения даты", is_error=True)
                
        except Exception as e:
            print(f"Общая ошибка в update_date_field: {e}")
            self._show_date_message("Ошибка обновления даты", is_error=True)        

    def _show_date_message(self, message, is_error=False):
        """Показывает сообщение о дате в preview_module и скрывает через 5 секунд"""
        if hasattr(self, 'preview_module') and self.preview_module:
            foreground = "red" if is_error else "blue"
            self.preview_module.tirazh_label.config(
                text=message,
                foreground=foreground
            )
            # Очищаем сообщение через 5 секунд
            self.parent.after(5000, lambda: self._clear_date_message())

    def _clear_date_message(self):
        """Очищает сообщение о дате в preview_module"""
        if hasattr(self, 'preview_module') and self.preview_module:
            self.preview_module.tirazh_label.config(
                text="",
                foreground="green"
            )
        
    def _scan_gtin_in_product_text(self, event):
        """Сканирует GTIN при вводе в поле product_text"""
        text = self.product_text.get("1.0", "end-1c").strip()
        if not text or not self.order_data_module:
            return
        
        gtin = self.order_data_module._extract_gtin_from_input(text)
        if gtin:
            self.product_text.delete("1.0", tk.END)
            self.order_data_module._process_scanned_gtin(gtin)
        
    def search_in_product_text(self, event=None):
        """Ищет продукты по тексту в поле изделия"""
        search_text = self.product_text.get("1.0", "end-1c").strip()
        
        if not search_text or not hasattr(self, 'cached_order_data'):
            self.order_data_module.parse_status.config(
                text="Сначала загрузите заказ", 
                foreground="orange"
            )
            return
            
        # Проверяем GTIN
        gtin = self.order_data_module._extract_gtin_from_input(search_text)
        if gtin:
            # Это GTIN - обрабатываем сканирование
            self.product_text.delete("1.0", tk.END)
            self.order_data_module._process_scanned_gtin(gtin)
            return "break"
        
        found_products = []
        
        for order_data in self.cached_order_data:
            for product in order_data.get('products', []):
                product_name = product.get('product_name', '')
                detail_number = product.get('detail_number', '')
                
                if (search_text.lower() in product_name.lower() or 
                    search_text in detail_number):
                    found_products.append(product)
        
        if found_products:
            self.order_data_module.show_product_results(found_products, search_text)
        else:
            self.order_data_module.parse_status.config(
                text=f"Не найдено видов по запросу '{search_text}'", 
                foreground="red"
            )
    
    def load_sleeve_weights(self):
        """Загружает данные о весе втулок из настроек"""
        try:
            settings = self.config_manager.load_json_settings("shared_utils.json")
            self.sleeve_weights = settings.get("sleeve_weights", {})
            # Парсим ширины как числа для сравнения
            self.parsed_sleeve_weights = {}
            for diameter, widths in self.sleeve_weights.items():
                self.parsed_sleeve_weights[diameter] = {}
                for width_str, weight in widths.items():
                    try:
                        width = int(width_str)
                        self.parsed_sleeve_weights[diameter][width] = weight
                    except ValueError:
                        continue
        except Exception as e:
            print(f"Ошибка загрузки веса втулок: {e}")
            self.sleeve_weights = {}
            self.parsed_sleeve_weights = {}
            
    def update_sleeve_weight_from_settings(self):
        """Автоматически выбирает вес втулки на основе ширины ручья и диаметра"""
        try:
            # Получаем ширину ручья
            width_str = self.stream_width_var.get().strip()
            if not width_str:
                return
                
            # Получаем диаметр втулки
            diameter_str = self.sleeve_diameter_var.get().strip()
            if not diameter_str:
                return
                
            # Парсим ширину
            try:
                width = int(width_str)
            except ValueError:
                return
                
            # Ищем ближайшую ширину в настройках
            if diameter_str in self.parsed_sleeve_weights:
                diameter_data = self.parsed_sleeve_weights[diameter_str]
                
                # Ищем точное совпадение
                if width in diameter_data:
                    self.sleeve_weight_var.set(str(diameter_data[width]))
                    return
                    
                # Ищем ближайшую меньшую ширину
                available_widths = sorted(diameter_data.keys())
                if available_widths:
                    # Ищем первое значение, которое <= нашей ширине
                    closest = None
                    for w in available_widths:
                        if w <= width:
                            closest = w
                        else:
                            break
                    
                    if closest is not None:
                        self.sleeve_weight_var.set(str(diameter_data[closest]))
        except Exception as e:
            print(f"Ошибка выбора веса втулки: {e}")
    
    def on_order_enter_pressed(self, event=None):
        """Запускает поиск заказа в БД при нажатии Энтер"""
        self.xml_tu_number = ""
        self.quantity_var.set("")
        self.customer_var.set("")
        self.rolls_count_var.set("1")
        self.product_text.delete("1.0", tk.END)
        self.product_text.insert("1.0", "")
        
        # Скрываем комбобокс выбора заказа если есть
        if hasattr(self, 'order_combobox'):
            self.order_combobox.set('')
            self.order_combobox['values'] = []
            self.order_combobox.grid_remove()
        
        self.cached_order_data = None
        self.cached_order_number = ""
        if hasattr(self, 'preview_module') and self.preview_module:
            self.preview_module.set_product_gtin("")
            self.preview_module.cancel_update_timer()
        
        # Получаем номер заказа
        order_num = self.order_number.get().strip()
        if not order_num:
            self.order_data_module.parse_status.config(text="Введите номер заказа", foreground="red")
            return
        
        # Ищем заказы
        results = self.data_manager.search_combined(order_num)
        
        if not results:
            self.order_data_module.parse_status.config(text="Заказ не найден", foreground="red")
            return
        
        if len(results) == 1:
            # Существующая логика
            cached_data = self.auto_fill_from_xml()
            self.order_data_module.cached_order_data = cached_data
            self.order_data_module.cached_order_number = order_num
            self.order_data_module.get_product_name()
            
        else:
            # обработка нескольких заказов
            self._show_multiple_orders(results)
            
    def _show_multiple_orders(self, results):
        """Показывает выбор при нескольких найденных заказах"""
        self.order_entry.grid_remove()  # Скрываем поле ввода
        self.entry_suffix.grid_remove()  # Скрываем суффикс
        
        # Сохраняем данные заказов
        self.multiple_orders_data = results
        
        # Собираем варианты для комбобокса
        order_options = []
        for order_data in results:
            order_full = order_data.get('order_number', '')
            order_options.append(order_full)
        
        # Устанавливаем значения в комбобокс
        self.order_combobox['values'] = order_options
        self.order_combobox.set(order_options[0])
        self.order_combobox.grid()  # Показываем комбобокс
        self.order_combobox_visible = True
        self.parent.after(100, lambda: self.order_combobox.focus_set())
        self.parent.after(120, lambda: self.order_combobox.event_generate('<Down>'))
        
        # Информируем пользователя
        self.order_data_module.parse_status.config(
            text=f"Найдено {len(results)} заказов. Выберите нужный:", 
            foreground="orange"
        )
        
    def on_order_selected(self, event=None):
        """Обрабатывает выбор заказа из комбобокса"""
        selected_index = self.order_combobox.current()
        if selected_index >= 0 and hasattr(self, 'multiple_orders_data'):
            # Получаем выбранный заказ
            selected_order_data = self.multiple_orders_data[selected_index]
            
            # Восстанавливаем обычные поля ввода
            self.order_combobox.grid_remove()
            self.order_entry.grid()
            self.entry_suffix.grid()
            self.order_combobox_visible = False  # ← Скрыли комбобокс
            
            # Автозаполняем поля из выбранного заказа
            self._fill_technical_fields_only(selected_order_data)
            
            # Сохраняем в кэш order_data_module
            self.order_data_module.cached_order_data = [selected_order_data]
            self.order_data_module.cached_order_number = self.order_number.get().strip()
            
            # Получаем виды из выбранного заказа
            self.order_data_module.get_product_name()
            
            # Сбрасываем временные данные
            delattr(self, 'multiple_orders_data')
            
            # Сбрасываем статус
            self.order_data_module.parse_status.config(text="Заказ выбран", foreground="green")
        
    def auto_fill_from_xml(self):
        """Автоматически заполняет ТОЛЬКО технические поля"""
        order_number = self.order_number.get().strip()
        if not order_number:
            return
        
        try:
            # Ищем заказ через DataManager
            results = self.data_manager.search_combined(order_number)
            
            if not results:
                print(f"Файлы для заказа {order_number} не найдены")
                return
                
            # Берём первый найденный заказ
            parsed_result = results[0]
            self._fill_technical_fields_only(parsed_result)
            
            # Сохраняем в локальный кэш
            self.cached_order_data = results
            self.cached_order_number = order_number
            
            return results
            
        except Exception as e:
            print(f"Ошибка автозаполнения из XML: {e}")

    def _fill_technical_fields_only(self, parsed_data: dict):
        """Заполняет только технические поля (НЕ product_text!)."""
        # Заказчик
        customer = parsed_data.get('customer', '')
        if customer:
            self.customer_var.set(customer)
            self.check_manufacturer_visibility(customer)
            
        # Изготовитель и ТУ
        executor = parsed_data.get('executor', '')
        tu_number = parsed_data.get('tu_number', '')
        
        # Просто сохраняем данные из XML
        if executor:
            # Нормализуем executor для поиска в списке производителей
            normalized_executor = self._normalize_string(executor)
            
            # Ищем совпадение в списке производителей
            found_manufacturer = None
            for manufacturer in self.manufacturer_options:
                if self._normalize_string(manufacturer) == normalized_executor:
                    found_manufacturer = manufacturer
                    break
            
            # Устанавливаем найденного производителя или оригинальный executor
            if found_manufacturer:
                self.manufacturer_var.set(found_manufacturer)
            else:
                # Если производитель не найден в списке - устанавливаем первого из packaging_tu
                if hasattr(self, 'manufacturer_options') and self.manufacturer_options:
                    self.manufacturer_var.set(self.manufacturer_options[0])  # id: 1
            
            # Обновляем список продуктов после установки производителя
            self.update_product_options()
            
        if tu_number and tu_number.strip() not in ["—", "-", ""]:
            self.xml_tu_number = tu_number.strip()
        
        # Префикс и суффикс заказа
        order_prefix = parsed_data.get('order_prefix', '')
        order_suffix = parsed_data.get('order_suffix', '')
        
        if order_prefix:
            self.order_prefix.set(order_prefix)
        if order_suffix:
            self.order_suffix.set(order_suffix)
        
        # Дата эмиссии (берём из первого продукта если есть)
        products = parsed_data.get('products', [])
        if products:
            date_emission = products[0].get('date_emission', '')
            if date_emission:
                self.date_emission_var.set(date_emission)
        
        # Данные из операций
        operations = parsed_data.get('operations', {})
        
        if operations.get('winding_scheme'):
            self.winding_scheme_var.set(operations['winding_scheme'])
        
        if operations.get('sleeve_diameter'):
            self.sleeve_diameter_var.set(operations['sleeve_diameter'])
        
        if operations.get('streams_count'):
            self.streams_var.set(operations['streams_count'])
        
        if operations.get('label_length_with_gap'):
        # Форматируем до 2 знаков после запятой
            try:
                length_value = float(operations['label_length_with_gap'])
                formatted_length = f"{length_value:.2f}"
                self.label_length_mm.set(formatted_length)
            except ValueError:
                self.label_length_mm.set(operations['label_length_with_gap'])
            
        # Ширина ручья
        if operations.get('stream_width'):
            self.stream_width_var.set(operations['stream_width'])
            
        # Комментарии
        comments = parsed_data.get('comments', {})
        operations = parsed_data.get('operations', {})
        self.order_data_module._display_comments(comments, operations)
        
    def get_manufacturer_full_data(self):
        """Возвращает готовые данные производителя для preview"""
        result = {
            'name': '',
            'address': '',
            'tu_number': self.xml_tu_number or '',  # Берем ТУ из XML если есть
            'product': ''
        }
        
        manufacturer = self.manufacturer_var.get()  # Оригинальное имя из UI
        product = self.product_type_var.get()
        
        if not manufacturer:
            return result
        
        # Нормализуем для поиска в нашей структуре
        normalized_manufacturer = self._normalize_string(manufacturer)
        
        # Ищем в структуре по НОРМАЛИЗОВАННОМУ имени
        if normalized_manufacturer in self.manufacturer_full_data_map:
            manufacturer_data = self.manufacturer_full_data_map[normalized_manufacturer]
            
            # Берём ОРИГИНАЛЬНОЕ имя для отображения
            result['name'] = manufacturer_data['original_name']
            result['address'] = manufacturer_data.get('address', '')
            
            # Ищем выбранный продукт
            if product and manufacturer_data['products']:
                for prod_data in manufacturer_data['products']:
                    if prod_data['name'] == product:
                        result['tu_number'] = prod_data['tu_number']
                        result['product'] = prod_data['name']
                        return result
            
            # Если продукт не выбран или не найден - берём первый
            if manufacturer_data['products']:
                first_product = manufacturer_data['products'][0]
                result['tu_number'] = first_product['tu_number']
                result['product'] = first_product['name']
        
        return result
        
    def _normalize_string(self, text: str) -> str:
        """Нормализация с кэшированием"""
        if not text:
            return ""
        
        if text in self._normalize_cache:
            return self._normalize_cache[text]
        
        # оригинальная логика
        normalized = text.lower()
        normalized = normalized.replace('ooo', '').replace('ооо', '')
        normalized = normalized.replace('"', '').replace("'", "")
        normalized = normalized.replace(' ', '').strip()
        
        self._normalize_cache[text] = normalized
        return normalized
        
    def calculate_quantity_from_length(self, *args):
        """Автоматически рассчитывает количество этикеток на основе длины ролика и длины этикетки"""
        # Дебаунсинг для оптимизации
        if hasattr(self, '_length_timer') and self._length_timer is not None:
            try:
                self.parent.after_cancel(self._length_timer)
            except (ValueError, TypeError):
                pass
        
        # Устанавливаем новый таймер
        self._length_timer = self.parent.after(70, self._calculate_quantity_from_length_actual)

    def _calculate_quantity_from_length_actual(self):
        """Фактический расчет количества из длины"""
        try:
            roll_length_m = self.parse_float(self.roll_length.get() or 0)
            label_length_mm = self.parse_float(self.label_length_mm.get() or 0)
            
            if roll_length_m > 0 and label_length_mm > 0:
                # Переводим мм в метры и рассчитываем количество
                label_length_m = label_length_mm / 1000
                quantity = math.ceil(roll_length_m / label_length_m)
                self.quantity_var.set(str(quantity))
            # Если одно из полей очищено - не меняем количество
        except (ValueError, TypeError, ZeroDivisionError):
            # В случае ошибки не изменяем значение quantity_var
            pass
        
    def on_settings_changed(self, context=None):
        """Обработчик изменений настроек от координатора"""
        # Если это уведомление о списке - игнорируем
        if context and context.get("type") == "list_changed":
            if context.get("list_name") == "rosinka":
                return  # не реагируем на Росинку
        try:
            settings = self.config_manager.load_json_settings("shared_utils.json")
            # 1. Обновляем префикс/суффикс номера заказа
            order_settings = settings.get("order_number", {})
            self.order_prefix.set(order_settings.get("prefix", "Ф"))
            self.order_suffix.set(order_settings.get("suffix", "/5"))
            
            # 2. Обновляем производителя
            self.manufacturer = settings.get("manufacturer", "")            
            self.config_manager.reload_settings()
            self.update_packers_list()
            self.update_cutters_list()
            self._update_cutter_visibility()
            self.load_manufacturer_options()
            self.load_sleeve_weights()
            self.update_elements_visibility()
        except Exception as e:
            print(f"Ошибка обновления списков после изменения настроек: {e}")
            
    def _update_cutter_visibility(self):
        """Показывает/скрывает резчика и поля автогенерации в зависимости от цеха"""
        workshop = self.coordinator.get_workshop()
        
        # Управление видимостью резчика
        if hasattr(self, 'cutter_label') and hasattr(self, 'cutter_combo'):
            if workshop == "1":
                self.cutter_label.grid_remove()
                self.cutter_combo.grid_remove()
            else:  # цех 2
                self.cutter_label.grid()
                self.cutter_combo.grid()
                
        # Управление видимостью полей автогенерации и ширины ручья
        if workshop == "1":
            # Цех 1 - скрываем поля
            self.batch_label.grid_remove()
            self.batch_entry.grid_remove()
            self.roll_label.grid_remove()
            self.roll_entry.grid_remove()
            self.roll_length_label.grid_remove()
            self.roll_length_entry.grid_remove()
        else:  # цех 2
            # Цех 2 - показываем все поля
            self.batch_label.grid()
            self.batch_entry.grid()
            self.roll_label.grid()
            self.roll_entry.grid()
            self.roll_length_label.grid()
            self.roll_length_entry.grid()
            
    def toggle_weight_visibility(self):
        """Показывает/скрывает строку с весом"""
        show_weight = self.show_weight_var.get()
        
        # Устанавливаем флаг для предотвращения расчетов при программной очистке
        self._skip_weight_calculation = True
        
        try:
            if show_weight:
                # 1. Сначала показываем элементы (быстрая операция)
                self.weight_label.grid()
                self.gross_entry.grid()
                self.sleeve_label.grid()
                self.sleeve_entry.grid()
                
                # 2. Очищаем переменные (trace временно отключены флагом)
                self.gross_weight_kg_var.set("")
                self.net_weight_kg_var.set("")
                self.total_gross_var.set("")
                self.total_net_var.set("")
                
                # 3. Фокус через небольшой таймаут
                self.parent.after(50, lambda: self.gross_entry.focus_set())
                
            else:
                # 1. Очищаем переменные (trace временно отключены флагом)
                self.gross_weight_kg_var.set("")
                self.net_weight_kg_var.set("")
                self.total_gross_var.set("")
                self.total_net_var.set("")
                
                # 2. Скрываем элементы
                self.weight_label.grid_remove()
                self.gross_entry.grid_remove()
                self.sleeve_label.grid_remove()
                self.sleeve_entry.grid_remove()
                
                # 3. Пересчитываем только количество (отдельный trace, работает)
                self.calculate_total_quantity()
                
                if hasattr(self, 'coordinator') and self.coordinator:
                    self.coordinator.check_weight_status(self)
                
        finally:
            # Всегда снимаем флаг
            self._skip_weight_calculation = False
            
    def update_elements_visibility(self):
        """Обновляет видимость дополнительных элементов на основе настроек"""
        try:
            settings = self.config_manager.load_json_settings("shared_utils.json")
            elements_status = settings.get("elements_status", "Скрыть")
            
            show_elements = (elements_status == "Показать")
            
            # Управляем видимостью даты
            if hasattr(self, 'date_entry'):
                if show_elements:
                    self.date_entry.grid()
                else:
                    self.date_entry.grid_remove()
            
            # Управляем видимостью второстепенных элементов
            if hasattr(self, 'winding_label'):
                if show_elements:
                    self.winding_label.grid()
                    self.winding_entry.grid()
                    self.diameter_label.grid()
                    self.diameter_entry.grid()
                    self.streams_label.grid()
                    self.streams_entry.grid()
                    self.stream_width_label.grid()
                    self.stream_width_entry.grid()
                    self.label_length_label.grid()
                    self.label_length_entry.grid()
                else:
                    self.winding_label.grid_remove()
                    self.winding_entry.grid_remove()
                    self.diameter_label.grid_remove()
                    self.diameter_entry.grid_remove()
                    self.streams_label.grid_remove()
                    self.streams_entry.grid_remove()
                    self.stream_width_label.grid_remove()
                    self.stream_width_entry.grid_remove()
                    self.label_length_label.grid_remove()
                    self.label_length_entry.grid_remove()
                    
                    
        except Exception as e:
            print(f"Ошибка обновления видимости элементов: {e}")
            
    def update_rosinka_visibility(self):
        """Показывает/скрывает галочку Росинка в зависимости от заказчика"""
        customer = self.customer_var.get()
        # Показываем только если заказчик "Росинка" (регистронезависимо)
        show_rosinka = customer and "росинка" in customer.lower()
        
        if hasattr(self, 'rosinka_checkbutton'):
            if show_rosinka:
                self.rosinka_checkbutton.pack(anchor="w", pady=(5, 0))
            else:
                self.rosinka_checkbutton.pack_forget()
                # Если скрываем, выключаем галочку
                self.rosinka_var.set(False)

    def update_packers_list(self):
        """Обновляет список упаковщиков в комбобоксе"""
        try:
            packers = self.config_manager.get_packers()
            self.packer_combo['values'] = packers
            
            # Сохраняем текущее значение, если оно есть в новом списке
            current_packer = self.packer_var.get()
            if current_packer in packers:
                self.packer_var.set(current_packer)
            elif packers:
                self.packer_var.set(packers[0])
                
        except Exception as e:
            print(f"Ошибка обновления списка упаковщиков: {e}")

    def update_cutters_list(self):
        """Обновляет список резчиков в комбобоксе"""
        try:
            cutters = self.config_manager.get_cutters()
            self.cutter_combo['values'] = cutters
            
            # Сохраняем текущее значение, если оно есть в новом списке
            current_cutter = self.cutter_var.get()
            if current_cutter in cutters:
                self.cutter_var.set(current_cutter)
            else:
                # Используем резчика по умолчанию из config_manager
                default_cutter = self.config_manager.get_default_cutter()
                self.cutter_var.set(default_cutter)
                
        except Exception as e:
            print(f"Ошибка обновления списка резчиков: {e}")
        
        
    def load_manufacturer_options(self, event=None):
        """Загружает варианты производителей и продуктов из packaging_tu.json"""
        try:
            # Локальные ссылки
            config_manager = self.config_manager
            manufacturer_combo = self.manufacturer_combo
            product_combo = self.product_combo
            manufacturer_var = self.manufacturer_var
            product_type_var = self.product_type_var
            
            # Проверяем существует ли файл в data_dir
            settings_path = config_manager.get_settings_path("packaging_tu.json")
            if not os.path.exists(settings_path):
                print(f"Файл packaging_tu.json не найден в {settings_path}")
                # Пробуем скопировать из assets
                self._copy_packaging_tu_from_assets()
            
            # Загружаем данные
            packaging_data = config_manager.load_json_settings("packaging_tu.json")
            
            # Если данные пустые или не содержат нужной структуры
            if not packaging_data or "technical_specifications" not in packaging_data:
                print("⚠️ Файл packaging_tu.json поврежден или пуст")
                # Просто очищаем списки и выходим
                manufacturer_combo['values'] = []
                product_combo['values'] = []
                manufacturer_var.set("")
                product_type_var.set("")
                return
            
            technical_specs = packaging_data.get("technical_specifications", [])
            specs_len = len(technical_specs)
            
            # Если список не изменился - не обновляем UI
            if hasattr(self, 'last_tu_count') and self.last_tu_count == specs_len:
                return
            self.last_tu_count = specs_len
            
            # Сортировка ПО ID (id=1 должен быть первым)
            technical_specs.sort(key=lambda x: x.get("id", 999))
            
            # Создаём полную структуру данных за один проход
            manufacturers = []  # Список оригинальных имён производителей для UI
            manufacturer_products_map = {}  # Оригинальное имя → список продуктов
            manufacturer_full_data_map = {}  # Нормализованное имя → полные данные
            seen_manufacturers_normalized = set()  # Для отслеживания уникальности
            
            for spec in technical_specs:
                manufacturer_info = spec["manufacturer"]
                product_info = spec["product"]
                manufacturer_name = manufacturer_info["name"]  # Оригинальное имя
                product_name = product_info["name"]
                
                # Нормализуем для сравнения
                normalized_name = self._normalize_string(manufacturer_name)
                
                # Добавляем оригинальное имя в список для UI (если производитель новый)
                if normalized_name not in seen_manufacturers_normalized:
                    manufacturers.append(manufacturer_name)  # ОРИГИНАЛЬНОЕ имя для UI
                    seen_manufacturers_normalized.add(normalized_name)
                    
                    # Создаём полную запись производителя по НОРМАЛИЗОВАННОМУ имени
                    manufacturer_full_data_map[normalized_name] = {
                        'original_name': manufacturer_name,  # Для UI
                        'address': manufacturer_info.get("address", ""),
                        'products': []  # список словарей продуктов
                    }
                
                # Добавляем продукт в словарь по ОРИГИНАЛЬНОМУ имени (для UI)
                if manufacturer_name not in manufacturer_products_map:
                    manufacturer_products_map[manufacturer_name] = []
                manufacturer_products_map[manufacturer_name].append(product_name)
                
                # Добавляем полные данные продукта в структуру по НОРМАЛИЗОВАННОМУ имени
                manufacturer_full_data_map[normalized_name]['products'].append({
                    'name': product_name,
                    'tu_number': product_info["tu_number"]
                })
            
            # Сохраняем оптимизированные структуры
            self.manufacturer_options = manufacturers  # Оригинальные имена для UI
            self.manufacturer_products_map = manufacturer_products_map  # Оригинальные имена → продукты
            self.manufacturer_full_data_map = manufacturer_full_data_map  # Нормализованные имена → полные данные
            self.sorted_technical_specs = technical_specs  # Для обратной совместимости
            
            # Остальная логика UI без изменений
            current_manufacturer = manufacturer_var.get()
            current_product = product_type_var.get()
            
            manufacturer_combo['values'] = self.manufacturer_options
            
            if current_manufacturer in self.manufacturer_options:
                manufacturer_var.set(current_manufacturer)
                if current_manufacturer in manufacturer_products_map:
                    products = manufacturer_products_map[current_manufacturer]
                    product_combo['values'] = products
                    if current_product in products:
                        product_type_var.set(current_product)
                    elif products:
                        product_type_var.set(products[0])
                else:
                    product_combo['values'] = []
                    product_type_var.set("")
            elif self.manufacturer_options:
                first_manufacturer = self.manufacturer_options[0]
                manufacturer_var.set(first_manufacturer)
                self.update_product_options()
                if first_manufacturer in manufacturer_products_map:
                    products = manufacturer_products_map[first_manufacturer]
                    if products:
                        product_type_var.set(products[0])
            else:
                product_combo['values'] = []
                product_type_var.set("")
                
        except Exception as e:
            print(f"Ошибка загрузки производителей: {e}")
            if hasattr(self, 'manufacturer_combo'):
                manufacturer_combo['values'] = []
                product_combo['values'] = []
                manufacturer_var.set("")
                product_type_var.set("")
                
    def _copy_packaging_tu_from_assets(self):
        """Копирует файл packaging_tu.json из assets в data_dir"""
        try:
            # Получаем путь к файлу в assets
            asset_path = self.config_manager.get_asset_path("packaging_tu.json")
            
            # Получаем путь назначения в data_dir
            dest_path = self.config_manager.get_settings_path("packaging_tu.json")
            
            # Проверяем существует ли файл в assets
            if os.path.exists(asset_path):
                # Копируем файл
                import shutil
                shutil.copy2(asset_path, dest_path)
                print(f"Файл packaging_tu.json скопирован из {asset_path} в {dest_path}")
            else:
                print(f"Файл packaging_tu.json не найден в assets по пути: {asset_path}")
                
        except Exception as e:
            print(f"Ошибка копирования packaging_tu.json: {e}")      

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
        self.xml_tu_number = ""
        self.preview_module._update_from_connected_roll_module()

    def on_order_number_changed(self, *args):
        """Обрабатывает изменение номера заказа"""
        if self.manual_manufacturer_selection:
            return  # Не переопределяем ручной выбор           
        
        # Только сбрасываем стили для всех префиксов
        self.manufacturer_combo.configure(style="TCombobox")
        self.product_combo.configure(style="TCombobox")
        
        # Если производитель НЕ выбран и это НЕ ручной выбор - устанавливаем первого производителя
        if not self.manufacturer_var.get() and not self.manual_manufacturer_selection:
            if hasattr(self, 'manufacturer_options') and self.manufacturer_options:
                self.manufacturer_var.set(self.manufacturer_options[0])
                self.update_product_options()

    def on_manufacturer_selected(self, event=None):
        """Обрабатывает выбор производителя"""
        self.xml_tu_number = ""
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
        self.update_rosinka_visibility()      
        
    def set_preview_module(self, preview_module):
        """Устанавливает связь с модулем предпросмотра для обратной связи"""
        self.preview_module = preview_module
        
    def parse_float(self, value):
        """Сверхоптимизированная версия parse_float"""
        if not value:
            return 0.0
        
        # Быстрая проверка на стандартные случаи
        if isinstance(value, (int, float)):
            return float(value)
        
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return 0.0
            
            # Быстрая замена запятой
            if ',' in value:
                value = value.replace(',', '.', 1)  # Заменяем только первую
            
            try:
                return float(value)
            except ValueError:
                return 0.0
        
        return 0.0
        
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
        # Дебаунсинг для оптимизации
        if hasattr(self, '_quantity_timer') and self._quantity_timer is not None:
            try:
                self.parent.after_cancel(self._quantity_timer)
            except (ValueError, TypeError):
                pass
        
        # Устанавливаем новый таймер
        self._quantity_timer = self.parent.after(70, self._calculate_total_quantity_actual)

    def _calculate_total_quantity_actual(self):
        """Фактический расчет общего количества"""
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
        
    def set_show_manufacturer(self, show):
        """Устанавливает видимость производителя извне"""
        self.show_manufacturer_var.set(show)        

    def set_order_data_module(self, order_data_module):
        """Устанавливает прямую связь с модулем обработки данных заказов"""
        self.order_data_module = order_data_module      
        
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
        
    def control_key_handler_text(self, event):
        """Обработчик горячих клавиш для Text виджетов"""
        widget = event.widget
        if event.keycode == 86 or event.keycode == 118:  # V key - вставка
            self.paste_text_to_text_widget(widget)
            return "break"
        elif event.keycode == 67 or event.keycode == 99:  # C key - копирование
            self.copy_text_from_text_widget(widget)
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

