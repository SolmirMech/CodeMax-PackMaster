# main_ui/order_data/controller.py
"""Основной контроллер данных заказа — фасад, объединяющий подмодули"""

import os
import tkinter as tk
from datetime import datetime

from .auto_fill import OrderAutoFiller
from .calculator import OrderCalculator
from .ui_builder import OrderUIBuilder


# noinspection PyUnusedLocal
class OrderDataController:
    """Контроллер данных заказа. Хранит состояние, координирует подмодули."""

    def __init__(self, parent, coordinator=None, data_manager=None, config_manager=None):
        # ========== БАЗОВЫЕ СВЯЗИ ==========
        self.parent = parent
        self.config_manager = config_manager
        self.data_manager = data_manager
        self.coordinator = coordinator

        # ========== ПОДКЛЮЧАЕМЫЕ МОДУЛИ ==========
        self.order_data_module = None
        self.preview_module = None

        # ========== ИНИЦИАЛИЗАЦИЯ ПЕРЕМЕННЫХ ==========
        self._init_variables()

        # ========== ДАННЫЕ И КЭШИ ==========
        self.cached_order_data = None
        self.cached_order_number = ""
        self.multiple_orders_data = None
        self.last_manual_order = ""
        self.order_combobox_visible = False
        self.xml_tu_number = ""

        self.manufacturer_options = []
        self.manufacturer_products_map = {}
        self.manufacturer_full_data_map = {}
        self.sorted_technical_specs = []
        self.manufacturer = ""
        self.last_tu_count = None

        self.sleeve_weights = {}
        self.parsed_sleeve_weights = {}

        self._normalize_cache = {}

        # ========== ФЛАГИ СОСТОЯНИЯ ==========
        self.manual_manufacturer_selection = False
        self.manual_product_selection = False
        self._skip_weight_calculation = False

        # ========== ТАЙМЕРЫ ==========
        self._weight_timer = None
        self._quantity_timer = None
        self._length_timer = None

        # ========== UI ЭЛЕМЕНТЫ (будут созданы в UIBuilder) ==========
        self.manufacturer_combo = None
        self.product_combo = None
        self.packer_combo = None
        self.cutter_combo = None
        self.order_combobox = None
        self.order_entry = None
        self.entry_suffix = None
        self.quantity_entry = None
        self.gross_entry = None
        self.sleeve_entry = None
        self.date_entry = None
        self.batch_entry = None
        self.roll_entry = None
        self.roll_length_entry = None
        self.stream_width_entry = None
        self.label_length_entry = None
        self.winding_entry = None
        self.diameter_entry = None
        self.streams_entry = None
        self.podlo_entry = None
        self.emission_entry = None
        self.product_text = None
        self.weight_label = None
        self.sleeve_label = None
        self.batch_label = None
        self.roll_label = None
        self.roll_length_label = None
        self.stream_width_label = None
        self.label_length_label = None
        self.winding_label = None
        self.diameter_label = None
        self.streams_label = None
        self.cutter_label = None
        self.podlo_label = None
        self.emission_label = None
        self.shorten_checkbutton = None
        self.rosinka_checkbutton = None
        self.weight_checkbutton = None

        # ========== ИНИЦИАЛИЗАЦИЯ ПОДМОДУЛЕЙ ==========
        self.config_manager.ensure_packaging_tu_exists()

        # Загрузка настроек номера заказа
        order_settings = self.config_manager.load_json_settings("shared_utils.json").get("order_number", {})
        self.order_prefix.set(order_settings.get("prefix", ""))
        self.order_suffix.set(order_settings.get("suffix", ""))

        # Создание UI через UIBuilder
        self.ui_builder = OrderUIBuilder(parent, self, config_manager, coordinator)
        # Подписки на изменения контекста для маппера
        self.customer_var.trace_add("write", self._apply_mapping)
        self.manufacturer_var.trace_add("write", self._apply_mapping)
        self.rosinka_var.trace_add("write", self._apply_mapping)
        self.show_weight_var.trace_add("write", self._apply_mapping)

        self.ui_builder.create_ui()
        self.load_manufacturer_options()

        # Инициализация калькулятора и автозаполнение
        self.calculator = OrderCalculator()
        self.auto_filler = OrderAutoFiller(self, data_manager, config_manager, coordinator)

        # Подписка на координатор
        if self.coordinator and hasattr(self.coordinator, 'subscribe'):
            self.coordinator.subscribe(self.on_settings_changed)
            self.ui_builder.update_cutter_visibility()
            self.load_sleeve_weights()

        # ========== ПОДПИСКИ НА ИЗМЕНЕНИЯ ==========
        self.gross_weight_kg_var.trace_add("write", self._on_weight_changed)
        self.sleeve_weight_var.trace_add("write", self._on_weight_changed)
        self.rolls_count_var.trace_add("write", self._on_weight_changed)
        self.box_weight_var.trace_add("write", self._on_weight_changed)
        self.quantity_var.trace_add("write", self.calculate_total_quantity)

    def _init_variables(self):
        """Инициализирует все StringVar и BooleanVar"""
        # Основные
        self.order_prefix = tk.StringVar(value="")
        self.order_suffix = tk.StringVar(value="")
        self.order_number = tk.StringVar(value="")
        self.customer_var = tk.StringVar(value="")
        self.date_var = tk.StringVar(value=datetime.now().strftime("%d.%m.%Y"))
        self.date_emission_var = tk.StringVar(value="")

        # Производитель и продукт
        self.manufacturer_var = tk.StringVar(value="")
        self.product_type_var = tk.StringVar(value="")
        self.show_manufacturer_var = tk.BooleanVar(value=False)

        # Количество и вес
        self.quantity_var = tk.StringVar(value="")
        self.rolls_count_var = tk.StringVar(value="1")
        self.total_quantity_var = tk.StringVar(value="")

        # Вес ролика
        self.gross_weight_kg_var = tk.StringVar(value="")
        self.net_weight_kg_var = tk.StringVar(value="")
        self.sleeve_weight_var = tk.StringVar(value="50")

        # Вес коробки
        self.box_weight_var = tk.StringVar(value="0.0")
        self.box_size_var = tk.StringVar(value="")
        self.total_gross_var = tk.StringVar(value="")
        self.total_net_var = tk.StringVar(value="")

        # Технические параметры
        self.winding_scheme_var = tk.StringVar(value="")
        self.sleeve_diameter_var = tk.StringVar(value="")
        self.streams_var = tk.StringVar(value="")
        self.stream_width_var = tk.StringVar(value="")
        self.label_length_mm = tk.StringVar(value="")

        # Параметры 2 цеха
        self.cutter_var = tk.StringVar(value="")
        self.roll_length = tk.StringVar(value="")
        self.batch_num_var = tk.StringVar(value="")
        self.roll_num_var = tk.StringVar(value="")

        # Росинка
        self.rosinka_var = tk.BooleanVar(value=False)
        self.ros_podlo_var = tk.StringVar(value="")
        self.ros_size_var = tk.StringVar(value="")

        # Упаковщик
        self.packer_var = tk.StringVar(value="")

        # Флаги интерфейса
        self.shorten_text_var = tk.BooleanVar(value=False)
        self.show_weight_var = tk.BooleanVar(value=False)

    # ========== ОБРАБОТЧИКИ СОБЫТИЙ (тонкая прослойка) ==========

    def _apply_mapping(self, *args):
        """Применяет маппинг интерфейса при изменении контекста (заказчик, производитель, галочки)"""
        self.ui_builder.apply_mapping()

    def _on_weight_changed(self, *args):
        """Обработчик изменений веса с дебаунсингом"""
        if self._skip_weight_calculation:
            return
        if not self.show_weight_var.get():
            return

        if self._weight_timer is not None:
            try:
                self.parent.after_cancel(self._weight_timer)
            except (ValueError, TypeError):
                pass

        self._weight_timer = self.parent.after(70, self._calculate_all_weights)

    def _calculate_all_weights(self):
        """Вычисляет все веса через калькулятор"""
        if self._skip_weight_calculation or not self.show_weight_var.get():
            return

        result = self.calculator.calculate_weights(
            self.gross_weight_kg_var.get(),
            self.sleeve_weight_var.get(),
            self.rolls_count_var.get(),
            self.box_weight_var.get()
        )

        self.net_weight_kg_var.set(result['net_kg'])
        self.total_gross_var.set(result['total_gross'])
        self.total_net_var.set(result['total_net'])

        if self.coordinator:
            self.coordinator.check_weight_status(self)
        if self.preview_module is not None:
            self.preview_module.update_from_connected_roll_module()

    def calculate_total_quantity(self, *args):
        """Рассчитывает общее количество с дебаунсингом"""
        if self._quantity_timer is not None:
            try:
                self.parent.after_cancel(self._quantity_timer)
            except (ValueError, TypeError):
                pass
        self._quantity_timer = self.parent.after(70, self._calculate_total_quantity_actual)

    def _calculate_total_quantity_actual(self):
        """Фактический расчет общего количества"""
        result = self.calculator.calculate_total_quantity(
            self.rolls_count_var.get(),
            self.quantity_var.get()
        )
        self.total_quantity_var.set(result)

    def calculate_quantity_from_length(self, *args):
        """Рассчитывает количество этикеток из длины с дебаунсингом"""
        if self._length_timer is not None:
            try:
                self.parent.after_cancel(self._length_timer)
            except (ValueError, TypeError):
                pass
        self._length_timer = self.parent.after(70, self._calculate_quantity_from_length_actual)

    def _calculate_quantity_from_length_actual(self):
        """Фактический расчет количества из длины"""
        result = self.calculator.calculate_quantity_from_length(
            self.roll_length.get(),
            self.label_length_mm.get()
        )
        if result:
            self.quantity_var.set(result)

    def force_recalculate_total(self):
        """Принудительный пересчёт общего количества"""
        result = self.calculator.calculate_total_quantity(
            self.rolls_count_var.get(),
            self.quantity_var.get()
        )
        self.total_quantity_var.set(result)

    # ========== МЕТОДЫ ДЛЯ ВНЕШНИХ МОДУЛЕЙ ==========

    def set_preview_module(self, preview_module):
        """Устанавливает связь с модулем предпросмотра"""
        self.preview_module = preview_module

    def set_order_data_module(self, order_data_module):
        """Устанавливает связь с модулем обработки данных заказов"""
        self.order_data_module = order_data_module

    def get_manufacturer_full_data(self):
        """Возвращает данные производителя для preview"""
        result = {
            'name': '',
            'address': '',
            'tu_number': self.xml_tu_number or '',
            'product': ''
        }

        manufacturer = self.manufacturer_var.get()
        product = self.product_type_var.get()

        if not manufacturer:
            return result

        normalized_manufacturer = self.normalize_string(manufacturer)

        if normalized_manufacturer in self.manufacturer_full_data_map:
            manufacturer_data = self.manufacturer_full_data_map[normalized_manufacturer]
            result['name'] = manufacturer_data['original_name']
            result['address'] = manufacturer_data.get('address', '')

            if product and manufacturer_data['products']:
                for prod_data in manufacturer_data['products']:
                    if prod_data['name'] == product:
                        result['tu_number'] = prod_data['tu_number']
                        result['product'] = prod_data['name']
                        return result

            if manufacturer_data['products']:
                first_product = manufacturer_data['products'][0]
                result['tu_number'] = first_product['tu_number']
                result['product'] = first_product['name']

        return result

    def load_manufacturer_options(self, event=None):
        """Загружает варианты производителей и продуктов из packaging_tu.json"""
        try:
            settings_path = self.config_manager.get_settings_path("packaging_tu.json")
            if not os.path.exists(settings_path):
                self._copy_packaging_tu_from_assets()

            packaging_data = self.config_manager.load_json_settings("packaging_tu.json")

            if not packaging_data or "technical_specifications" not in packaging_data:
                self.manufacturer_combo['values'] = []
                self.product_combo['values'] = []
                self.manufacturer_var.set("")
                self.product_type_var.set("")
                return

            technical_specs = packaging_data.get("technical_specifications", [])
            specs_len = len(technical_specs)

            if self.last_tu_count is not None and self.last_tu_count == specs_len:
                return
            self.last_tu_count = specs_len

            technical_specs.sort(key=lambda x: x.get("id", 999))

            manufacturers = []
            manufacturer_products_map = {}
            manufacturer_full_data_map = {}
            seen_manufacturers_normalized = set()

            for spec in technical_specs:
                manufacturer_info = spec["manufacturer"]
                product_info = spec["product"]
                manufacturer_name = manufacturer_info["name"]
                product_name = product_info["name"]

                normalized_name = self.normalize_string(manufacturer_name)

                if normalized_name not in seen_manufacturers_normalized:
                    manufacturers.append(manufacturer_name)
                    seen_manufacturers_normalized.add(normalized_name)
                    manufacturer_full_data_map[normalized_name] = {
                        'original_name': manufacturer_name,
                        'address': manufacturer_info.get("address", ""),
                        'products': []
                    }

                if manufacturer_name not in manufacturer_products_map:
                    manufacturer_products_map[manufacturer_name] = []
                manufacturer_products_map[manufacturer_name].append(product_name)

                manufacturer_full_data_map[normalized_name]['products'].append({
                    'name': product_name,
                    'tu_number': product_info["tu_number"]
                })

            self.manufacturer_options = manufacturers
            self.manufacturer_products_map = manufacturer_products_map
            self.manufacturer_full_data_map = manufacturer_full_data_map
            self.sorted_technical_specs = technical_specs

            current_manufacturer = self.manufacturer_var.get()
            current_product = self.product_type_var.get()

            self.manufacturer_combo['values'] = self.manufacturer_options

            if current_manufacturer in self.manufacturer_options:
                self.manufacturer_var.set(current_manufacturer)
                if current_manufacturer in manufacturer_products_map:
                    products = manufacturer_products_map[current_manufacturer]
                    self.product_combo['values'] = products
                    if current_product in products:
                        self.product_type_var.set(current_product)
                    elif products:
                        self.product_type_var.set(products[0])
                else:
                    self.product_combo['values'] = []
                    self.product_type_var.set("")
            elif self.manufacturer_options:
                first_manufacturer = self.manufacturer_options[0]
                self.manufacturer_var.set(first_manufacturer)
                self.update_product_options()
                if first_manufacturer in manufacturer_products_map:
                    products = manufacturer_products_map[first_manufacturer]
                    if products:
                        self.product_type_var.set(products[0])
            else:
                self.product_combo['values'] = []
                self.product_type_var.set("")

        except Exception as e:
            print(f"Ошибка загрузки производителей: {e}")
            self.manufacturer_combo['values'] = []
            self.product_combo['values'] = []
            self.manufacturer_var.set("")
            self.product_type_var.set("")

    def _copy_packaging_tu_from_assets(self):
        """Копирует файл packaging_tu.json из assets в data_dir"""
        try:
            import shutil
            asset_path = self.config_manager.get_asset_path("packaging_tu.json")
            dest_path = self.config_manager.get_settings_path("packaging_tu.json")
            if os.path.exists(asset_path):
                shutil.copy2(asset_path, dest_path)
                print(f"Файл packaging_tu.json скопирован")
        except Exception as e:
            print(f"Ошибка копирования packaging_tu.json: {e}")

    def update_product_options(self):
        """Обновляет список продуктов для выбранного производителя"""
        manufacturer = self.manufacturer_var.get()
        if manufacturer in self.manufacturer_products_map:
            products = self.manufacturer_products_map[manufacturer]
            self.product_combo['values'] = products
            if products:
                self.product_type_var.set("Обычная с\\к этикетка")
        else:
            self.product_combo['values'] = []
            self.product_type_var.set("")

    def on_manufacturer_selected(self, event=None):
        """Обрабатывает выбор производителя"""
        self.xml_tu_number = ""
        self.last_manual_order = self.order_number.get()
        self.update_product_options()

        if self.product_combo['values']:
            self.product_type_var.set("Обычная с\\к этикетка")

        if self.preview_module is not None:
            self.preview_module.update_preview_displays()

    def on_product_selected(self, event=None):
        """Обрабатывает выбор типа продукта"""
        self.manual_product_selection = True
        self.xml_tu_number = ""
        if self.preview_module:
            self.preview_module.update_from_connected_roll_module()

    def load_sleeve_weights(self):
        """Загружает данные о весе втулок из настроек"""
        try:
            settings = self.config_manager.load_json_settings("shared_utils.json")
            self.sleeve_weights = settings.get("sleeve_weights", {})
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

    def update_sleeve_weight_from_settings(self, *args):
        """Автоматически выбирает вес втулки на основе ширины ручья и диаметра"""
        try:
            width_str = self.stream_width_var.get().strip()
            diameter_str = self.sleeve_diameter_var.get().strip()

            if not width_str or not diameter_str:
                return

            try:
                width = int(width_str)
            except ValueError:
                return

            if diameter_str not in self.parsed_sleeve_weights:
                return

            diameter_data = self.parsed_sleeve_weights[diameter_str]
            available_widths = sorted(diameter_data.keys())

            if width in diameter_data:
                self.sleeve_weight_var.set(str(diameter_data[width]))
                return

            # Ищем ближайшую меньшую ширину
            closest = None
            for w in available_widths:
                if w <= width:
                    closest = w
                else:
                    break

            if closest is not None:
                self.sleeve_weight_var.set(str(diameter_data[closest]))
            else:
                # Нет меньшей ширины — берём минимальную доступную
                min_width = available_widths[0]
                self.sleeve_weight_var.set(str(diameter_data[min_width]))

        except Exception as e:
            print(f"Ошибка выбора веса втулки: {e}")

    def normalize_string(self, text: str) -> str:
        """Нормализация строки с кэшированием"""
        if not text:
            return ""
        if text in self._normalize_cache:
            return self._normalize_cache[text]
        normalized = text.lower()
        normalized = normalized.replace('ooo', '').replace('ооо', '')
        normalized = normalized.replace('"', '').replace("'", "")
        normalized = normalized.replace(' ', '').strip()
        self._normalize_cache[text] = normalized
        return normalized

    def on_settings_changed(self, context=None):
        """Обработчик изменений настроек от координатора"""
        if context and context.get("type") == "list_changed":
            if context.get("list_name") == "rosinka":
                return

        try:
            self.config_manager.reload_settings()
            self.update_packers_list()
            self.update_cutters_list()
            self.ui_builder.update_cutter_visibility()
            self.load_manufacturer_options()
            self.load_sleeve_weights()
            self.ui_builder.update_elements_visibility()
            self.ui_builder.apply_mapping()
        except Exception as e:
            print(f"Ошибка обновления списков после изменения настроек: {e}")

    def update_packers_list(self):
        """Обновляет список упаковщиков в комбобоксе"""
        try:
            packers = self.config_manager.get_packers()
            self.packer_combo['values'] = packers
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
            current_cutter = self.cutter_var.get()
            if current_cutter in cutters:
                self.cutter_var.set(current_cutter)
            else:
                default_cutter = self.config_manager.get_default_cutter()
                self.cutter_var.set(default_cutter)
        except Exception as e:
            print(f"Ошибка обновления списка резчиков: {e}")

    def on_customer_changed(self, *args):
        """Обрабатывает изменение заказчика"""
        customer_name = self.customer_var.get()
        self.check_manufacturer_visibility(customer_name)
        self.ui_builder.update_rosinka_visibility()

    def check_manufacturer_visibility(self, customer_name):
        """Проверяет нужно ли показывать производителя для заказчика"""
        if customer_name:
            found_customer = self.config_manager.find_customer(customer_name)
            self.show_manufacturer_var.set(found_customer is not None)
        else:
            self.show_manufacturer_var.set(False)

    def on_order_number_changed(self, *args):
        """Обрабатывает изменение номера заказа"""
        if self.manual_manufacturer_selection:
            return

        self.manufacturer_combo.configure(style="TCombobox")
        self.product_combo.configure(style="TCombobox")

        if not self.manufacturer_var.get() and not self.manual_manufacturer_selection:
            if hasattr(self, 'manufacturer_options') and self.manufacturer_options:
                self.manufacturer_var.set(self.manufacturer_options[0])
                self.update_product_options()

    def extract_label_size_from_db(self):
        """Извлекает размер этикетки из order_name для Росинки"""
        if not hasattr(self, 'order_data_module') or not self.order_data_module:
            self.ros_size_var.set("")
            return

        if not hasattr(self.order_data_module, 'cached_order_data') or not self.order_data_module.cached_order_data:
            self.ros_size_var.set("")
            return

        import re
        order_data = self.order_data_module.cached_order_data[0]
        order_name = order_data.get('order_name', '')

        if not order_name:
            self.ros_size_var.set("")
            return

        match = re.search(r'(\d+)\s*[хxХX*]\s*(\d+)', order_name, re.IGNORECASE)
        if match:
            width = match.group(1)
            height = match.group(2)
            self.ros_size_var.set(f"{width}х{height} мм")
        else:
            self.ros_size_var.set("")

    def on_shorten_text_changed(self):
        """Обрабатывает изменение галочки сокращения текста"""
        if hasattr(self, 'order_data_module') and self.order_data_module:
            self.order_data_module.get_product_name()

    def search_in_product_text(self, event=None):
        """Ищет продукты по тексту в поле изделия"""
        search_text = self.product_text.get("1.0", "end-1c").strip()

        if not search_text or not hasattr(self, 'cached_order_data'):
            self.order_data_module.parse_status.config(
                text="Сначала загрузите заказ",
                foreground="orange"
            )
            return None

        gtin = self.order_data_module.extract_gtin_from_input(search_text)
        if gtin:
            self.product_text.delete("1.0", tk.END)
            self.order_data_module.process_scanned_gtin(gtin)
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
            return None
        else:
            self.order_data_module.parse_status.config(
                text=f"Не найдено видов по запросу '{search_text}'",
                foreground="red"
            )
            return None

    # Прокси-методы для OrderAutoFiller (чтобы внешний код не ломался)
    def on_order_enter_pressed(self, event=None):
        """Прокси для auto_filler.on_order_enter_pressed"""
        self.auto_filler.on_order_enter_pressed(event)

    def on_order_selected(self, event=None):
        """Прокси для auto_filler.on_order_selected"""
        self.auto_filler.on_order_selected(event)
