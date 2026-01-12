# apps/roll_preview.py
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from core.pdf_utils import PDFTemplateFiller
from core.config_manager import ConfigManager
from core.settings.font_settings_dialog import FontSettingsDialog
import os
import json
from datetime import datetime
from typing import Dict

class RollPreview:
    """Модуль предпросмотра этикеток ролика и коробки"""

    def __init__(self, parent, coordinator=None):
        self.parent = parent
        self.config_manager = ConfigManager()
        self.coordinator = coordinator
        self._update_template_paths()
        self.box_template_path = self.config_manager.get_asset_path("box.pdf")
        
        self.current_data = {}
        self.roll_pdf_filler = None
        self.box_pdf_filler = None
        self.selected_preview = "roll"  # "roll" или "box"
        self.font_settings = None
        
        self.connected_roll_module = None
        
        self.create_preview_ui()
        self.load_font_settings()
        self.check_templates()
        if self.coordinator and hasattr(self.coordinator, 'subscribe'):
            self.coordinator.subscribe(self._on_settings_changed)        
        
    def _on_settings_changed(self):
        """Обрабатывает изменения от координатора"""
        # Перезагружаем настройки шрифтов и шаблоны
        self.load_font_settings()
        self.reload_for_workshop_change()        
        
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
        self.status_label = ttk.Label(frame, text="Загрузка шаблонов...", foreground="gray")
        self.status_label.grid(row=2, column=0, pady=5)
        
        # Сразу загружаем PDF и показываем превью
        self.load_and_show_previews()
        
    def _update_template_paths(self):
        """Обновляет пути к шаблонам в зависимости от настройки цеха"""
        workshop = self.coordinator.get_workshop()
        
        if workshop == "2":
            self.roll_template_path = self.config_manager.get_asset_path("roll_2_cex.pdf")
        else:  # По умолчанию 1 цех
            self.roll_template_path = self.config_manager.get_asset_path("roll.pdf")
        
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
        """Настраивает отслеживание изменений в модуле ролика"""
        if not self.connected_roll_module:
            return

        # Список переменных для отслеживания
        variables_to_track = [
            self.connected_roll_module.customer_var,
            self.connected_roll_module.gross_weight_kg_var, 
            self.connected_roll_module.net_weight_kg_var,
            self.connected_roll_module.order_prefix,
            self.connected_roll_module.order_number,
            self.connected_roll_module.order_suffix,
            self.connected_roll_module.date_var,
            self.connected_roll_module.packer_var,
            self.connected_roll_module.quantity_var,
            self.connected_roll_module.rolls_count_var,
            self.connected_roll_module.total_quantity_var,
            self.connected_roll_module.total_gross_var,
            self.connected_roll_module.total_net_var,
            self.connected_roll_module.winding_scheme_var,
            self.connected_roll_module.sleeve_diameter_var,
            self.connected_roll_module.show_manufacturer_var,
            self.connected_roll_module.date_emission_var,
            self.connected_roll_module.cutter_var,
            self.connected_roll_module.roll_length,
            self.connected_roll_module.manufacturer_var,
            self.connected_roll_module.product_type_var,
            self.connected_roll_module.batch_num_var,
            self.connected_roll_module.roll_num_var,
        ]
        
        # Устанавливаем отслеживание для каждой переменной
        for var in variables_to_track:
            var.trace_add("write", self._on_roll_data_changed)
        
        # Отслеживаем изменения в текстовом поле изделия
        self.connected_roll_module.product_text.bind("<<Modified>>", self._on_product_text_modified)

    def _on_product_text_modified(self, event=None):
        """Обрабатывает изменение текста изделия"""
        if (self.connected_roll_module and 
            self.connected_roll_module.product_text.edit_modified()):
            self.connected_roll_module.product_text.edit_modified(False)
            self._update_from_connected_roll_module()

    def _on_roll_data_changed(self, *args):
        """Обрабатывает изменение любых данных в модуле ролика"""
        self._update_from_connected_roll_module()

    def _update_from_connected_roll_module(self):
        """Обновляет данные из подключенного модуля ролика"""
        if not self.connected_roll_module:
            return

        try:
            roll_module = self.connected_roll_module
            
            # Получаем текст изделия из текстового поля
            product_text = roll_module.product_text.get("1.0", "end-1c").strip()
            
            # Собираем данные с правильными ключами
            preview_data = {
                "customer": roll_module.customer_var.get(),
                "product_text": product_text,
                "gross_weight_kg": roll_module.gross_weight_kg_var.get(),
                "net_weight_kg": roll_module.net_weight_kg_var.get(),
                "order_prefix": roll_module.order_prefix.get(),
                "order_number": roll_module.order_number.get(),
                "order_suffix": roll_module.order_suffix.get(),
                "date": roll_module.date_var.get(),
                "packer": roll_module.packer_var.get(),
                "quantity": roll_module.quantity_var.get(),
                "show_manufacturer": roll_module.show_manufacturer_var.get(),
                "rolls_count": roll_module.rolls_count_var.get(),
                "total_quantity": roll_module.total_quantity_var.get(),
                "box_brut": roll_module.total_gross_var.get(),
                "box_net": roll_module.total_net_var.get(),
                "winding_scheme": roll_module.winding_scheme_var.get(),
                "sleeve_diameter": roll_module.sleeve_diameter_var.get(),
                "cutter": roll_module.cutter_var.get(),
                "roll_length": roll_module.roll_length.get(),
                "date_emission": roll_module.date_emission_var.get(),
                "batch_num": roll_module.batch_num_var.get(),
                "roll_num": roll_module.roll_num_var.get(),
            }
            
            # Обновляем предпросмотр
            self.update_from_roll_data(preview_data)
            
            # Обновляем статус Excel в export_module если он есть
            if hasattr(self, 'export_module') and self.export_module:
                self.export_module.export_status_label.config(
                    text="",
                    foreground="green"
                )
            
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
            self.status_label.config(text="Шаблоны загружены", foreground="green")
            self.parent.after(5000, lambda: self.status_label.config(text=""))
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
        
    def _get_manufacturer_data(self, order_number: str) -> dict:
        """Получает данные изготовителя: сначала из XML, потом из настроек"""
        try:
            # 1. Пробуем получить ТУ из XML (высший приоритет)
            if (self.connected_roll_module and 
                hasattr(self.connected_roll_module, 'xml_tu_number') and 
                self.connected_roll_module.xml_tu_number):
                
                tu_from_xml = self.connected_roll_module.xml_tu_number
                
                # Если выбран "Без изготовителя"
                if (self.connected_roll_module and 
                    self.connected_roll_module.show_manufacturer_var.get()):
                    return {
                        'name': '',
                        'address': '',
                        'tu_number': tu_from_xml  # ТУ из XML
                    }
                
                # Иначе получаем производителя из комбобокса
                manufacturer_name = self.connected_roll_module.manufacturer_var.get() if self.connected_roll_module else ''
                address = ''
                
                # Ищем адрес в packaging_tu.json
                if manufacturer_name:
                    try:
                        packaging_data = self.config_manager.load_json_settings("packaging_tu.json")
                        technical_specs = packaging_data.get("technical_specifications", [])
                        for spec in technical_specs:
                            if spec["manufacturer"]["name"] == manufacturer_name:
                                address = spec["manufacturer"].get("address", "")
                                break
                    except Exception as e:
                        print(f"Ошибка поиска адреса для {manufacturer_name}: {e}")
                
                return {
                    'name': manufacturer_name,
                    'address': address,  # Теперь с адресом!
                    'tu_number': tu_from_xml  # ТУ из XML
                }
            
            # 2. Если нет XML ТУ - старая логика
            if (self.connected_roll_module and 
                self.connected_roll_module.show_manufacturer_var.get()):
                
                regular_data = self._get_regular_manufacturer_data(order_number)
                return {
                    'name': '',
                    'address': '',
                    'tu_number': regular_data['tu_number']
                }
            
            # Иначе обычная логика
            return self._get_regular_manufacturer_data(order_number)
                        
        except Exception as e:
            print(f"Ошибка загрузки данных изготовителя: {e}")
            return {
                'name': 'Производитель',
                'address': 'Адрес производителя',
                'tu_number': 'ТУ: Номер технических условий'
            }
    
    def _get_regular_manufacturer_data(self, order_number: str) -> dict:
        """Получает данные изготовителя из выпадающих списков или автоматически"""
        try:
            # Если есть подключенный модуль ролика
            if (self.connected_roll_module and 
                self.connected_roll_module.manufacturer_var.get() and 
                self.connected_roll_module.product_type_var.get()):
                
                manufacturer = self.connected_roll_module.manufacturer_var.get()
                product_type = self.connected_roll_module.product_type_var.get()
                
                # Ищем точное соответствие в packaging_tu.json
                packaging_data = self.config_manager.load_json_settings("packaging_tu.json")
                technical_specs = packaging_data.get("technical_specifications", [])
                
                for spec in technical_specs:
                    if (spec["manufacturer"]["name"] == manufacturer and 
                        spec["product"]["name"] == product_type):
                        return {
                            'name': spec["manufacturer"]["name"],
                            'address': spec["manufacturer"].get("address", ""),
                            'tu_number': spec["product"]["tu_number"]
                        }
            
            # Старая логика для автоматического выбора (ie заказы)
            # Эта логика работает ТОЛЬКО если ручной выбор не сделан
            packaging_data = self.config_manager.load_json_settings("packaging_tu.json")
            technical_specs = packaging_data.get("technical_specifications", [])
            
            if order_number.startswith('IE'):
                for spec in technical_specs:
                    if spec.get("id") == 2:  # Зюдин для IE
                        return {
                            'name': spec["manufacturer"]["name"],
                            'address': spec["manufacturer"]["address"],
                            'tu_number': spec["product"]["tu_number"]
                        }
            else:
                for spec in technical_specs:
                    if spec.get("id") == 3:  # Ремас-Флексо по умолчанию
                        return {
                            'name': spec["manufacturer"]["name"],
                            'address': spec["manufacturer"]["address"], 
                            'tu_number': spec["product"]["tu_number"]
                        }
                        
        except Exception as e:
            print(f"Ошибка загрузки данных изготовителя: {e}")
        
        # Fallback
        return {
            'name': 'Производитель',
            'address': 'Адрес производителя',
            'tu_number': 'ТУ: Номер технических условий'
        }

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
    
    def _prepare_roll_data_map(self) -> Dict[str, str]:
        """Подготавливает данные для ролика"""
        data = self.current_data or {}
        
        # Формируем полный номер заказа
        order_prefix = data.get('order_prefix', '')
        order_number = data.get('order_number', '') 
        order_suffix = data.get('order_suffix', '')
        order_full = f"{order_prefix}{order_number}{order_suffix}"
        
        # Получаем данные изготовителя
        manufacturer_data = self._get_manufacturer_data(order_full)
        
        show_manufacturer = not data.get('show_manufacturer', False)
        
        # Карта для ролика
        data_map = {
            # Основные поля
            "$customer": data.get('customer', ''),
            "$product": data.get('product_text', ''),
            "$onum": order_full,
            "$date": data.get('date', ''),
            "$packer": data.get('packer', ''),
            "$rol": data.get('quantity', ''),
            "$tr": data.get('rolls_count', ''),
            "$emission": data.get('date_emission', ''),
            
            # Весовые данные
            "$brutto": data.get('gross_weight_kg', ''),
            "$netto": data.get('net_weight_kg', ''),
            
            # Технические параметры
            "$sx": data.get('winding_scheme', ''),
            "dia": data.get('sleeve_diameter', ''),
            
            # Данные из метода manufacturer_data
            "$tu_number": manufacturer_data['tu_number'],
            "$printhouse": manufacturer_data['name'] if show_manufacturer else "",
            "$printaddress": manufacturer_data['address'] if show_manufacturer else "",
            
            # Специфичные для 2 цеха параметры
            "$cutter": data.get('cutter', ''),
            "$rll_length": data.get('roll_length', ''),
            "$batch_num": data.get('batch_num', ''),
            "$roul_num": data.get('roll_num', ''),
        }
        
        return data_map
    
    def _prepare_box_data_map(self) -> Dict[str, str]:
        """Подготавливает данные для коробки"""
        # Берем базовые данные из ролика
        data_map = self._prepare_roll_data_map()
        
        data = self.current_data or {}
        
        # Форматируем общее количество с разделителем
        total_quantity = data.get('total_quantity', '')
        if total_quantity:
            try:
                # Преобразуем в число и форматируем с разделителем тысяч
                total_quantity_int = int(total_quantity)
                formatted_total = f"{total_quantity_int:,}".replace(",", " ")
            except (ValueError, TypeError):
                formatted_total = total_quantity
        else:
            formatted_total = ''
        
        # Добавляем специфичные для коробки поля
        data_map.update({
            "$total": formatted_total,
            "$box_brut": data.get('box_brut', ''),
            "$box_net": data.get('box_net', ''),
        })
        
        return data_map
    
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
            
            self.status_label.config(text="Превью обновлены", foreground="green")
            self.parent.after(5000, lambda: self.status_label.config(text=""))
            
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
        self._setup_data_tracking()