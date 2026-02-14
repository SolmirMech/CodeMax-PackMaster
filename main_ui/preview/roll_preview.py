import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from core.pdf_utils import PDFTemplateFiller
from core.settings.font_settings_dialog import FontSettingsDialog
import os
import json
from datetime import datetime
from typing import Dict

TRACKING_CONFIG = {
    # Основные данные (всегда отслеживаются)
    'BASIC': {
        'customer_var': None,
        'order_prefix': None,
        'order_number': None,
        'order_suffix': None,
        'date_var': None,
        'packer_var': None,
        'quantity_var': None,
        'rolls_count_var': None,
        'show_manufacturer_var': None,
    },
    
    # Данные производителя (всегда отслеживаются)
    'MANUFACTURER': {
        'manufacturer_var': None,
        'product_type_var': None,
    },
    
    # Технические параметры (всегда отслеживаются)
    'TECHNICAL': {
        'winding_scheme_var': None,
        'sleeve_diameter_var': None,
        'date_emission_var': None,
        'stream_width_var': None,
    },
    
    # Весовые данные (только при включенном весе)
    'WEIGHT': {
        'gross_weight_kg_var': lambda self: self.weight_enabled,
        'net_weight_kg_var': lambda self: self.weight_enabled,
        'sleeve_weight_var': lambda self: self.weight_enabled,
        'box_weight_var': lambda self: self.weight_enabled,
    },
    
    # Данные для коробки
    'BOX': {
        'total_quantity_var': None,
        'total_gross_var': lambda self: self.weight_enabled,
        'total_net_var': lambda self: self.weight_enabled,
    },
    
    # Специфичные для 2-го цеха
    'WORKSHOP_2': {
        'cutter_var': lambda self: self.coordinator and self.coordinator.get_workshop() == "2",
        'roll_length': lambda self: self.coordinator and self.coordinator.get_workshop() == "2",
        'batch_num_var': lambda self: self.coordinator and self.coordinator.get_workshop() == "2",
        'roll_num_var': lambda self: self.coordinator and self.coordinator.get_workshop() == "2",
        'streams_var': lambda self: self.coordinator and self.coordinator.get_workshop() == "2",
        'label_length_mm': lambda self: self.coordinator and self.coordinator.get_workshop() == "2",
    },
    
    # Специфичные для Росинки
    'ROSINKA': {
        'ros_podlo_var': lambda self: self.rosinka_enabled,
        'ros_size_var': lambda self: self.rosinka_enabled,
    }
}

# Добавляем конфигурацию данных для превью
DATA_MAPPING_CONFIG = {
    # Основные данные
    'BASIC': {
        'customer': {
            'source': lambda rm: rm.customer_var.get(),
            'condition': lambda self: True,
            'placeholder': '$customer'
        },
        'product': {
            'source': lambda rm: rm.product_text.get("1.0", "end-1c").strip(),
            'condition': lambda self: True,
            'placeholder': '$product'
        },
        'order_full': {
            'source': lambda rm: f"{rm.order_prefix.get()}{rm.order_number.get()}{rm.order_suffix.get()}",
            'condition': lambda self: True,
            'placeholder': '$onum'
        },
        'date': {
            'source': lambda rm: rm.date_var.get(),
            'condition': lambda self: True,
            'placeholder': '$date'
        },
        'packer': {
            'source': lambda rm: rm.packer_var.get(),
            'condition': lambda self: True,
            'placeholder': '$packer'
        },
        'quantity': {
            'source': lambda rm: rm.quantity_var.get(),
            'condition': lambda self: True,
            'placeholder': '$rol'
        },
        'rolls_count': {
            'source': lambda rm: rm.rolls_count_var.get(),
            'condition': lambda self: True,
            'placeholder': '$tr'
        },
    },
    
    # Технические параметры
    'TECHNICAL': {
        'winding_scheme': {
            'source': lambda rm: rm.winding_scheme_var.get(),
            'condition': lambda self: True,
            'placeholder': '$sx'
        },
        'sleeve_diameter': {
            'source': lambda rm: rm.sleeve_diameter_var.get(),
            'condition': lambda self: True,
            'placeholder': 'dia'
        },
        'date_emission': {
            'source': lambda rm: rm.date_emission_var.get(),
            'condition': lambda self: True,
            'placeholder': '$emission'
        },
    },
    
    # Данные производителя
    'MANUFACTURER': {
        'manufacturer_name': {
            'source': lambda rm: rm.get_manufacturer_full_data()['name'],
            'condition': lambda self: not self.current_data.get('show_manufacturer', False),
            'placeholder': '$printhouse'
        },
        'manufacturer_address': {
            'source': lambda rm: rm.get_manufacturer_full_data()['address'],
            'condition': lambda self: not self.current_data.get('show_manufacturer', False),
            'placeholder': '$printaddress'
        },
        'tu_number': {
            'source': lambda rm: rm.get_manufacturer_full_data()['tu_number'],
            'condition': lambda self: True,
            'placeholder': '$tu_number'
        },
    },
    
    # Весовые данные (с условием)
    'WEIGHT': {
        'gross_weight_kg': {
            'source': lambda rm: rm.gross_weight_kg_var.get(),
            'condition': lambda self: self.weight_enabled,
            'placeholder': '$brutto'
        },
        'net_weight_kg': {
            'source': lambda rm: rm.net_weight_kg_var.get(),
            'condition': lambda self: self.weight_enabled,
            'placeholder': '$netto'
        },
        'box_brut': {
            'source': lambda rm: rm.total_gross_var.get(),
            'condition': lambda self: self.weight_enabled,
            'placeholder': '$box_brut'
        },
        'box_net': {
            'source': lambda rm: rm.total_net_var.get(),
            'condition': lambda self: self.weight_enabled,
            'placeholder': '$box_net'
        },
    },
    
    # Данные для коробки
    'BOX': {
        'total_quantity': {
            'source': lambda rm: rm.total_quantity_var.get(),
            'condition': lambda self: True,
            'placeholder': '$total'
        },
    },
    
    # Данные для 2-го цеха
    'WORKSHOP_2': {
        'cutter': {
            'source': lambda rm: rm.cutter_var.get(),
            'condition': lambda self: self.coordinator and self.coordinator.get_workshop() == "2",
            'placeholder': '$cutter'
        },
        'roll_length': {
            'source': lambda rm: rm.roll_length.get(),
            'condition': lambda self: self.coordinator and self.coordinator.get_workshop() == "2",
            'placeholder': '$rll_length'
        },
        'batch_num': {
            'source': lambda rm: rm.batch_num_var.get(),
            'condition': lambda self: self.coordinator and self.coordinator.get_workshop() == "2",
            'placeholder': '$batch_num'
        },
        'roll_num': {
            'source': lambda rm: rm.roll_num_var.get(),
            'condition': lambda self: self.coordinator and self.coordinator.get_workshop() == "2",
            'placeholder': '$roul_num'
        },
    },
    
    # Данные для Росинки
    'ROSINKA': {
        'ros_podlo': {
            'source': lambda rm: rm.ros_podlo_var.get(),
            'condition': lambda self: self.rosinka_enabled,
            'placeholder': '$ros_podlo'
        },
        'ros_size': {
            'source': lambda rm: rm.ros_size_var.get(),
            'condition': lambda self: self.rosinka_enabled,
            'placeholder': '$ros_size'
        },
    }
}

class RollPreview:
    """Модуль предпросмотра этикеток ролика и коробки"""

    def __init__(self, parent, coordinator=None, config_manager=None):
        self.parent = parent
        self.config_manager = config_manager
        self.coordinator = coordinator
        self._update_template_paths()
        self.box_template_path = self.config_manager.get_asset_path("box.pdf")
        
        self.current_data = {}
        self.roll_pdf_filler = None
        self.box_pdf_filler = None
        self.selected_preview = "roll"  # "roll" или "box"
        self.font_settings = None
        
        self.connected_roll_module = None
        self._active_tracking_vars = []
        # Инициализируем состояния
        self.rosinka_enabled = False
        self.weight_enabled = False
        self.product_gtin = ""
        self.preview_timer_id = None  # Добавляем таймер
        self.last_total_value = ""    # Для отслеживания изменений        
        
        self.create_preview_ui()
        self.load_font_settings()
        if self.coordinator and hasattr(self.coordinator, 'subscribe'):
            self.coordinator.subscribe(self._on_settings_changed)

    def set_product_gtin(self, gtin):
        """Сохраняет GTIN продукта для QR-кода"""
        self.product_gtin = gtin
        if gtin:
            self.current_data['gtin'] = gtin
        elif 'gtin' in self.current_data:
            del self.current_data['gtin']
        self.update_preview_displays()
            
    def delayed_initialization(self):
        """Вызывается после установки всех связей"""
        self.check_templates()
        
    def _on_settings_changed(self):
        """Обрабатывает изменения от координатора"""
        try:
            # 1. Получаем состояние галочки Росинка из roll_module
            if hasattr(self, 'connected_roll_module') and self.connected_roll_module:
                if hasattr(self.connected_roll_module, 'rosinka_var'):
                    self.rosinka_enabled = self.connected_roll_module.rosinka_var.get()
                else:
                    self.rosinka_enabled = False
            else:
                self.rosinka_enabled = False
            
            # 2. Получаем статус веса из координатора
            if self.coordinator:
                self.weight_enabled = self.coordinator.get_weight_status()
            else:
                self.weight_enabled = False
            
            # 3. Перезагружаем настройки шрифтов и шаблоны
            self.load_font_settings()
            self.reload_for_workshop_change()
            
            # 4. ОБНОВЛЯЕМ ПОДПИСКИ при изменении настроек
            self.refresh_tracking()
            
        except Exception as e:
            print(f"Ошибка в _on_settings_changed: {e}")
            self.rosinka_enabled = False
            self.weight_enabled = False
        
    def create_preview_ui(self):
        """Создает интерфейс предпросмотра"""
        style = ttk.Style()
        style.configure("Selected.TFrame", background="green", bordercolor="blue")
        frame = ttk.Frame(self.parent, padding=5)
        frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Используем grid для расположения (2 колонки: превью и управление)
        frame.columnconfigure(0, weight=1)  # Превью
        frame.rowconfigure(0, weight=1)     # Ролик
        frame.rowconfigure(1, weight=1)     # Коробка
        
        # Превью ролика - строка 0, колонка 0 для 2 цеха width=420, height=420,
        roll_frame = ttk.LabelFrame(frame, text="Ролик", padding=2)
        roll_frame.grid(row=0, column=0, padx=5, pady=(0, 5), sticky="nsew")
        
        self.roll_canvas_frame = ttk.Frame(roll_frame, relief="solid", borderwidth=2)
        self.roll_canvas_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        self.roll_canvas = tk.Canvas(self.roll_canvas_frame, width=416, height=520, bg="white")
        self.roll_canvas.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        self.roll_canvas.bind("<Button-1>", lambda e: self.roll_canvas.focus_set())
        
        # Весь фрейм ролика кликабелен для выбора
        self.roll_canvas_frame.bind("<Button-1>", lambda e: self.select_preview("roll"))
        self.roll_canvas.bind("<Button-1>", lambda e: self.select_preview("roll"))
        self.roll_canvas.bind("<Return>", lambda e: self.print_selected_preview())
        
        # Превью коробки - строка 1, колонка 0
        box_frame = ttk.LabelFrame(frame, text="Коробка", padding=2)
        box_frame.grid(row=1, column=0, padx=5, pady=(5, 5), sticky="nsew")
        
        self.box_canvas_frame = ttk.Frame(box_frame, relief="sunken", borderwidth=1)
        self.box_canvas_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        self.box_canvas = tk.Canvas(self.box_canvas_frame, width=416, height=520, bg="white")
        self.box_canvas.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        self.box_canvas.bind("<Button-1>", lambda e: self.box_canvas.focus_set())
        
        # Весь фрейм коробки кликабелен для выбора
        self.box_canvas_frame.bind("<Button-1>", lambda e: self.select_preview("box"))
        self.box_canvas.bind("<Button-1>", lambda e: self.select_preview("box"))
        self.box_canvas.bind("<Return>", lambda e: self.print_selected_preview())
        
        # Общий Статус
        self.status_label = ttk.Label(
            frame, 
            text="", 
            foreground="gray",
            wraplength=450
        )
        self.status_label.grid(row=2, column=0, pady=5)
        
        # Строка для тиража
        self.tirazh_label = ttk.Label(
            frame,
            text="",
            foreground="green",
            font=("Arial", 16),
            wraplength=450
        )
        self.tirazh_label.grid(row=3, column=0, pady=(0, 5))
        
        # Сразу загружаем PDF и показываем превью
        self.load_and_show_previews()
        
    def _cleanup_tracking(self):
        """Очищает все активные подписки на переменные"""
        if hasattr(self, '_active_tracking_vars'):
            for var_name, var_obj, trace_id in self._active_tracking_vars:
                try:
                    if var_name == 'product_text':
                        # Для Text виджета удаляем bind
                        var_obj.unbind("<<Modified>>")
                    elif trace_id is not None:
                        # Для StringVar удаляем trace
                        var_obj.trace_remove("write", trace_id)
                except (ValueError, AttributeError, TypeError):
                    pass  # Игнорируем ошибки удаления
            self._active_tracking_vars.clear()
        else:
            self._active_tracking_vars = []
    
    def refresh_tracking(self):
        """Пересоздаёт подписки при изменении условий (вес, цех, росинка)"""
        if self.connected_roll_module:
            self._cleanup_tracking()
            self._setup_data_tracking()        
        
    def _update_template_paths(self):
        """Обновляет пути к шаблонам в зависимости от настроек"""
        workshop = self.coordinator.get_workshop()
        
        # Определяем базовый шаблон в зависимости от цеха
        if workshop == "2":
            base_template = "roll_2_cex.pdf"
        else:
            base_template = "roll.pdf"
        
        # Если включена Росинка - используем rosinka.pdf
        if hasattr(self, 'rosinka_enabled') and self.rosinka_enabled:
            self.roll_template_path = self.config_manager.get_asset_path("rosinka.pdf")
        else:
            self.roll_template_path = self.config_manager.get_asset_path(base_template)
        
        # Коробка остается без изменений
        self.box_template_path = self.config_manager.get_asset_path("box.pdf")

    def reload_templates(self):
        """Перезагружает шаблоны при изменении цеха"""
        self._update_template_paths()
        self.check_templates()  # Перезагружаем и проверяем шаблоны      
        
    def print_selected_preview(self):
        """Печатает выбранное превью через print_module"""
        if hasattr(self, 'print_module') and self.print_module:
            self.print_module.print_label()
        else:
            self.status_label.config(text="Модуль печати не подключен", foreground="red")
        
    def load_font_settings(self):
        """Загружает настройки шрифтов через координатор"""
        # Получаем активный шаблон из координатора
        active_template = self.coordinator.get_font_template()
        
        # Загружаем настройки для этого шаблона
        loaded_settings = self.config_manager.load_json_settings("label_font_settings.json")
        
        if loaded_settings and active_template in loaded_settings:
            self.font_settings = loaded_settings[active_template]
            
            # Гарантируем, что все необходимые ключи присутствуют
            default_settings = FontSettingsDialog.get_default_font_settings()
            
            # Для ролика
            for key in default_settings["roll"]:
                if key not in self.font_settings["roll"]:
                    self.font_settings["roll"][key] = default_settings["roll"][key]
            
            # Для коробки  
            for key in default_settings["box"]:
                if key not in self.font_settings["box"]:
                    self.font_settings["box"][key] = default_settings["box"][key]
                    
        else:
            # Используем настройки по умолчанию
            self.font_settings = FontSettingsDialog.get_default_font_settings()
            
        # Применяем настройки к pdf filler'ам
        if self.roll_pdf_filler and self.font_settings:
            self.roll_pdf_filler.set_font_settings(self.font_settings["roll"])
        if self.box_pdf_filler and self.font_settings:
            self.box_pdf_filler.set_font_settings(self.font_settings["box"])
            
    def update_font_settings(self, new_settings):
        """Обновляет настройки шрифтов"""
        # Гарантируем, что все необходимые ключи присутствуют
        default_settings = FontSettingsDialog.get_default_font_settings()
        
        # Для ролика
        for key in default_settings["roll"]:
            if key not in new_settings["roll"]:
                new_settings["roll"][key] = default_settings["roll"][key]
        
        # Для коробки  
        for key in default_settings["box"]:
            if key not in new_settings["box"]:
                new_settings["box"][key] = default_settings["box"][key]
        
        self.font_settings = new_settings
        # Передаем ТОЛЬКО СВОИ секции настроек
        if self.roll_pdf_filler:
            self.roll_pdf_filler.set_font_settings(new_settings["roll"])  # Только roll
        if self.box_pdf_filler:
            self.box_pdf_filler.set_font_settings(new_settings["box"])   # Только box
        # Обновляем превью
        self.update_preview_displays()
        
    def open_font_settings(self):
        """Открывает окно настроек шрифтов"""
        FontSettingsDialog(self.parent, self.config_manager, self)

    def _setup_data_tracking(self):
        """Настраивает отслеживание только активных переменных"""
        if not self.connected_roll_module:
            return
        
        # Инициализируем список активных подписок
        if not hasattr(self, '_active_tracking_vars'):
            self._active_tracking_vars = []
        
        roll_module = self.connected_roll_module
        
        # Проходим по всем категориям конфигурации
        for category, variables in TRACKING_CONFIG.items():
            for var_name, condition in variables.items():
                # Пропускаем product_text - обрабатываем отдельно
                if var_name == 'product_text':
                    continue
                    
                # Проверяем условие (если есть)
                should_track = True
                if condition is not None:
                    try:
                        # Условия проверяются на self (RollPreview), а не на roll_module!
                        should_track = condition(self)
                    except Exception as e:
                        print(f"Ошибка проверки условия для {var_name}: {e}")
                        should_track = False
                
                if should_track:
                    # Получаем объект переменной из roll_module
                    var_obj = getattr(roll_module, var_name, None)
                    if var_obj:
                        try:
                            # Добавляем отслеживание
                            trace_id = var_obj.trace_add("write", self._on_roll_data_changed)
                            # Сохраняем информацию для последующей очистки
                            self._active_tracking_vars.append((var_name, var_obj, trace_id))
                        except Exception as e:
                            print(f"Ошибка добавления отслеживания для {var_name}: {e}")
        
        # Обрабатываем product_text отдельно (это tk.Text, не StringVar)
        try:
            if hasattr(roll_module, 'product_text'):
                # Для Text виджета используем bind, а не trace_add
                roll_module.product_text.bind("<<Modified>>", self._on_product_text_modified)
                # Сохраняем информацию
                self._active_tracking_vars.append(('product_text', roll_module.product_text, None))
        except Exception as e:
            print(f"Ошибка привязки к product_text: {e}")

    def _on_product_text_modified(self, event=None):
        """Обрабатывает изменение текста изделия"""
        if (self.connected_roll_module and 
            self.connected_roll_module.product_text.edit_modified()):
            self.connected_roll_module.product_text.edit_modified(False)
            self._update_from_connected_roll_module()

    def _on_roll_data_changed(self, *args):
        """Универсальный дебаунсинг для любых изменений данных"""
        # Отменяем предыдущий таймер
        if hasattr(self, '_update_timer') and self._update_timer:
            try:
                self.parent.after_cancel(self._update_timer)
            except (ValueError, AttributeError):
                pass
        
        # Устанавливаем новый таймер
        self._update_timer = self.parent.after(300, self._update_from_connected_roll_module)

    def _update_from_connected_roll_module(self):
        """Обновляет данные из подключенного модуля ролика через конфигурацию"""
        self.preview_timer_id = None
        if not self.connected_roll_module:
            return

        try:
            roll_module = self.connected_roll_module
            preview_data = {}
            
            # Сначала собираем базовые данные для условий
            basic_data = {
                'customer': roll_module.customer_var.get(),
                'show_manufacturer': roll_module.show_manufacturer_var.get(),
            }
            preview_data.update(basic_data)
            self.current_data.update(basic_data)
            
            # Проходим по всем категориям конфигурации
            for category, fields in DATA_MAPPING_CONFIG.items():
                for field_name, config in fields.items():
                    # Проверяем условие (если есть)
                    if config['condition'] and not config['condition'](self):
                        continue
                    
                    # Получаем значение из источника
                    try:
                        value = config['source'](roll_module)
                        preview_data[field_name] = value
                    except Exception as e:
                        print(f"Ошибка получения {field_name}: {e}")
                        preview_data[field_name] = ""
            
            # Обновляем текущие данные
            self.current_data = preview_data
            self.update_preview_displays()
            
        except Exception as e:
            print(f"Ошибка обновления предпросмотра: {e}")
            
    def update_from_roll_data(self, roll_data: Dict):
        """Обновляет предпросмотр данными из weight_roll_printer"""
        self.current_data = roll_data
        self.update_preview_displays()
        
    def check_templates(self):
        """Проверяет наличие PDF шаблонов"""
        templates_ok = True
        
        # Проверяем ролик
        if not os.path.exists(self.roll_template_path):
            self.status_label.config(text=f"Файл roll.pdf не найден по пути:\n{self.roll_template_path}", foreground="red")
            templates_ok = False
        else:
            try:
                self.roll_pdf_filler = PDFTemplateFiller(self.roll_template_path)
                self.roll_pdf_filler.open_template()
                # Передаем настройки шрифтов
                if self.font_settings:
                    self.roll_pdf_filler.set_font_settings(self.font_settings["roll"])
            except Exception as e:
                self.status_label.config(text=f"Ошибка загрузки шаблона ролика: {e}", foreground="red")
                templates_ok = False
        
        # Проверяем коробку
        if not os.path.exists(self.box_template_path):
            self.status_label.config(text=f"Файл box.pdf не найден по пути:\n{self.box_template_path}", foreground="red")
            templates_ok = False
        else:
            try:
                self.box_pdf_filler = PDFTemplateFiller(self.box_template_path)
                self.box_pdf_filler.open_template()
                # Передаем настройки шрифтов
                if self.font_settings:
                    self.box_pdf_filler.set_font_settings(self.font_settings["box"])
            except Exception as e:
                self.status_label.config(text=f"Ошибка загрузки шаблона коробки: {e}", foreground="red")
                templates_ok = False
        
        if templates_ok:
            # Сразу запускаем отрисовку превью
            self.load_and_show_previews()
        
        return templates_ok
        
    def reload_for_workshop_change(self):
        """Перезагружает шаблоны и настройки при смене цеха"""
        self._update_template_paths()  # Обновляем пути к PDF шаблонам
        self.load_font_settings()      # Перезагружаем настройки шрифтов
        self.check_templates()         # Перезагружаем PDF filler
        
        # Обновляем превью если есть данные
        if self.current_data:
            self.update_preview_displays()        
        
    def load_and_show_previews(self):
        """Сразу загружает и показывает превью"""
        # Всегда пытаемся обновить превью, даже если нет данных
        self.update_preview_displays()        

    def select_preview(self, preview_type):
        """Выбирает активное превью для печати"""
        self.selected_preview = preview_type
        
        # Синхронизируем выбор с preview_export модулем
        if hasattr(self, 'print_module') and self.print_module:
            self.print_module.selected_preview = preview_type
        
        # Визуальное выделение выбранного превью красной рамкой
        if preview_type == "roll":
            self.roll_canvas_frame.config(relief="solid", borderwidth=2)
            self.roll_canvas_frame.configure(style="Selected.TFrame")
            self.box_canvas_frame.config(relief="sunken", borderwidth=1)
            self.box_canvas_frame.configure(style="TFrame")
        else:
            self.roll_canvas_frame.config(relief="sunken", borderwidth=1)
            self.roll_canvas_frame.configure(style="TFrame")
            self.box_canvas_frame.config(relief="solid", borderwidth=2)
            self.box_canvas_frame.configure(style="Selected.TFrame")
            
            self.box_canvas.focus_set()
            
    def _create_placeholder(self, canvas, text):
        """Создает текст-заглушку на canvas (только для ошибок)"""
        canvas.delete("all")
        canvas.create_text(
            canvas.winfo_width()//2, 
            canvas.winfo_height()//2,
            text=text,
            font=("Arial", 9),
            fill="gray",
            justify=tk.CENTER
        )
    
    def _prepare_roll_data_map(self) -> Dict[str, str]:
        """Подготавливает данные для ролика"""
        data = self.current_data or {}
        
        # Формируем полный номер заказа
        order_prefix = data.get('order_prefix', '')
        order_number = data.get('order_number', '') 
        order_suffix = data.get('order_suffix', '')
        order_full = f"{order_prefix}{order_number}{order_suffix}"
        
        show_manufacturer = not data.get('show_manufacturer', False)
        
        # Карта для ролика
        data_map = {
            # Основные поля
            "$customer": data.get('customer', ''),
            "$product": data.get('product', ''),
            "$onum": data.get('order_full', ''),
            "$date": data.get('date', ''),
            "$packer": data.get('packer', ''),
            "$rol": self._format_number_with_spaces(data.get('quantity', '')),
            "$tr": data.get('rolls_count', ''),
            "$emission": data.get('date_emission', ''),
            
            # Весовые данные
            "$brutto": data.get('gross_weight_kg', ''),
            "$netto": data.get('net_weight_kg', ''),
            
            # Технические параметры
            "$sx": data.get('winding_scheme', ''),
            "dia": data.get('sleeve_diameter', ''),
            
            # Данные производителя - берем из current_data
            "$tu_number": data.get('tu_number', ''),
            "$printhouse": data.get('manufacturer_name', '') if show_manufacturer else "",
            "$printaddress": data.get('manufacturer_address', '') if show_manufacturer else "",
            
            # Специфичные для 2 цеха параметры
            "$cutter": data.get('cutter', ''),
            "$rll_length": data.get('roll_length', ''),
            "$batch_num": data.get('batch_num', ''),
            "$roul_num": data.get('roll_num', ''),
            # Подложка для Росинки
            "$ros_podlo": data.get('ros_podlo', ''),
            "$ros_size": data.get('ros_size', ''),
        }
        
        return data_map
    
    def _prepare_box_data_map(self) -> Dict[str, str]:
        """Подготавливает данные для коробки"""
        # Берем базовые данные из ролика
        data_map = self._prepare_roll_data_map()
        
        data = self.current_data or {}      
        
        # Добавляем специфичные для коробки поля
        data_map.update({
            "$total": self._format_number_with_spaces(data.get('total_quantity', '')),
            "$box_brut": data.get('box_brut', ''),
            "$box_net": data.get('box_net', ''),
        })
        
        # ДОБАВЛЯЕМ ДАННЫЕ ДЛЯ QR-КОДА
        gtin = self.product_gtin
        total_for_qr = data.get('total_quantity', '')  # Без форматирования пробелами!
        
        if gtin and total_for_qr:
            # Формат: "GTIN:1234567890123,TOTAL:1000"
            data_map["$box_qr"] = f"GTIN:{gtin},TOTAL:{total_for_qr}"
        else:
            # Пустая строка = QR не генерируется
            data_map["$box_qr"] = ""
        
        return data_map
        
    def _format_number_with_spaces(self, number_str):
        """Форматирует число с пробелами между тысячами"""
        if not number_str or not str(number_str).strip():
            return ""
        try:
            cleaned = str(number_str).strip().replace(" ", "")
            return f"{int(cleaned):,}".replace(",", " ")
        except (ValueError, TypeError):
            return str(number_str)
    
    def update_preview_displays(self):
        """Обновляет оба превью"""
        try:
            # Обновляем превью ролика
            if self.roll_pdf_filler:
                roll_data_map = self._prepare_roll_data_map()
                roll_preview_image = self.roll_pdf_filler.generate_preview(roll_data_map)
                self._update_canvas_preview(self.roll_canvas, roll_preview_image)
            
            # Обновляем превью коробки
            if self.box_pdf_filler:
                box_data_map = self._prepare_box_data_map()
                box_preview_image = self.box_pdf_filler.generate_preview(box_data_map)
                self._update_canvas_preview(self.box_canvas, box_preview_image)         
            
        except Exception as e:
            self.status_label.config(text=f"Ошибка обновления: {e}", foreground="red")
    
    def _update_canvas_preview(self, canvas, preview_image):
        """Обновляет конкретное превью на canvas"""
        try:
            canvas_width = canvas.winfo_width()
            canvas_height = canvas.winfo_height()
            
            # Если canvas еще не отрисован, откладываем обновление
            if canvas_width <= 1 or canvas_height <= 1:
                self.parent.after(50, lambda: self._update_canvas_preview(canvas, preview_image))
                return
            
            if canvas_width > 1 and canvas_height > 1:
                # Используем ВЕСЬ доступный размер канваса
                img_ratio = preview_image.width / preview_image.height
                canvas_ratio = canvas_width / canvas_height
                
                if img_ratio > canvas_ratio:
                    # Изображение шире - заполняем по ширине
                    display_width = canvas_width
                    display_height = int(canvas_width / img_ratio)
                else:
                    # Изображение выше - заполняем по высоте  
                    display_height = canvas_height
                    display_width = int(canvas_height * img_ratio)
                
                # Убираем уменьшение для отступов - используем максимальный размер
                scaled_image = preview_image.resize((display_width, display_height), Image.Resampling.LANCZOS)
                
                # Обновляем canvas
                photo = ImageTk.PhotoImage(scaled_image)
                canvas.image = photo  # Сохраняем ссылку
                canvas.delete("all")
                canvas.create_image(canvas_width//2, canvas_height//2, image=photo)
                
        except Exception as e:
            print(f"Ошибка обновления canvas: {e}")         
            
    def set_roll_module(self, roll_module):
        """Устанавливает связь с модулем ролика для отслеживания данных"""
        self.connected_roll_module = roll_module
        self._cleanup_tracking()  # Очищаем старые подписки
        self._setup_data_tracking()  # Настраиваем новые