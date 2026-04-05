# main_ui/order_data/auto_fill.py
"""Модуль автозаполнения заказа из XML и поиска заказов"""
import tkinter as tk


# noinspection PyTypeChecker
class OrderAutoFiller:
    """Обработка поиска заказов в БД и автозаполнение полей"""

    def __init__(self, controller, data_manager, config_manager, coordinator):
        """
        Args:
            controller: OrderDataController (доступ к переменным и UI)
            data_manager: XMLDataManager
            config_manager: ConfigManager
            coordinator: SettingsCoordinator
        """
        self.controller = controller
        self.data_manager = data_manager
        self.config_manager = config_manager
        self.coordinator = coordinator

    # noinspection PyUnusedLocal
    def on_order_enter_pressed(self, event=None):
        """Запускает поиск заказа в БД при нажатии Enter"""
        # Сброс временных данных
        self.controller.xml_tu_number = ""
        self.controller.roll_length.set("")
        self.controller.quantity_var.set("")
        self.controller.customer_var.set("")
        self.controller.rolls_count_var.set("1")
        self.controller.product_text.delete("1.0", tk.END)
        
        # Скрываем комбобокс выбора заказа если есть
        if hasattr(self.controller, 'order_combobox'):
            self.controller.order_combobox.set('')
            self.controller.order_combobox['values'] = []
            self.controller.order_combobox.grid_remove()
        
        self.controller.cached_order_data = None
        self.controller.cached_order_number = ""
        
        if self.controller.preview_module is not None:
            self.controller.preview_module.set_product_gtin("")
            self.controller.preview_module.cancel_update_timer()
        
        # Получаем номер заказа
        order_num = self.controller.order_number.get().strip()
        if not order_num:
            self.controller.order_data_module.parse_status.config(
                text="Введите номер заказа", 
                foreground="red"
            )
            return
        
        # Ищем заказы
        results = self.data_manager.search_combined(order_num)
        
        if not results:
            self.controller.order_data_module.parse_status.config(
                text="Заказ не найден", 
                foreground="red"
            )
            return
        
        if len(results) == 1:
            cached_data = self.auto_fill_from_xml()
            self.controller.order_data_module.cached_order_data = cached_data
            self.controller.order_data_module.cached_order_number = order_num
            self.controller.order_data_module.get_product_name()
        else:
            self._show_multiple_orders(results)

    def auto_fill_from_xml(self) -> list:
        """Автоматически заполняет технические поля из XML"""
        order_number = self.controller.order_number.get().strip()
        if not order_number:
            return None
        
        try:
            results = self.data_manager.search_combined(order_number)
            
            if not results:
                print(f"Файлы для заказа {order_number} не найдены")
                return None
            
            parsed_result = results[0]
            self._fill_technical_fields_only(parsed_result)
            
            self.controller.cached_order_data = results
            self.controller.cached_order_number = order_number
            
            return results
            
        except Exception as e:
            print(f"Ошибка автозаполнения из XML: {e}")
            return None

    def _fill_technical_fields_only(self, parsed_data: dict):
        """Заполняет только технические поля (НЕ product_text!)"""
        # Заказчик
        customer = parsed_data.get('customer', '')
        if customer:
            self.controller.customer_var.set(customer)
            self.controller.check_manufacturer_visibility(customer)
        
        # Изготовитель и ТУ
        executor = parsed_data.get('executor', '')
        tu_number = parsed_data.get('tu_number', '')
        
        if executor:
            normalized_executor = self.controller.normalize_string(executor)
            
            found_manufacturer = None
            for manufacturer in self.controller.manufacturer_options:
                if self.controller.normalize_string(manufacturer) == normalized_executor:
                    found_manufacturer = manufacturer
                    break
            
            if found_manufacturer:
                self.controller.manufacturer_var.set(found_manufacturer)
            elif hasattr(self.controller, 'manufacturer_options') and self.controller.manufacturer_options:
                self.controller.manufacturer_var.set(self.controller.manufacturer_options[0])
            
            self.controller.update_product_options()
        
        if tu_number and tu_number.strip() not in ["—", "-", ""]:
            self.controller.xml_tu_number = tu_number.strip()
        
        # Поиск продукта по ТУ
        found_product = None
        for norm_name, man_data in self.controller.manufacturer_full_data_map.items():
            for prod in man_data['products']:
                if prod['tu_number'] == self.controller.xml_tu_number:
                    found_product = prod['name']
                    break
            if found_product:
                break
        
        if found_product:
            self.controller.product_type_var.set(found_product)
        
        # Префикс и суффикс заказа
        order_prefix = parsed_data.get('order_prefix', '')
        order_suffix = parsed_data.get('order_suffix', '')
        
        if order_prefix:
            self.controller.order_prefix.set(order_prefix)
        if order_suffix:
            self.controller.order_suffix.set(order_suffix)
        
        # Дата эмиссии
        products = parsed_data.get('products', [])
        if products:
            date_emission = products[0].get('date_emission', '')
            if date_emission:
                self.controller.date_emission_var.set(date_emission)
        
        # Данные из операций
        operations = parsed_data.get('operations', {})
        
        if operations.get('winding_scheme'):
            self.controller.winding_scheme_var.set(operations['winding_scheme'])
        
        if operations.get('sleeve_diameter'):
            self.controller.sleeve_diameter_var.set(operations['sleeve_diameter'])
        
        if operations.get('streams_count'):
            self.controller.streams_var.set(operations['streams_count'])
        
        if operations.get('label_length_with_gap'):
            try:
                length_value = float(operations['label_length_with_gap'])
                formatted_length = f"{length_value:.2f}"
                self.controller.label_length_mm.set(formatted_length)
            except ValueError:
                self.controller.label_length_mm.set(operations['label_length_with_gap'])
        
        if operations.get('stream_width'):
            self.controller.stream_width_var.set(operations['stream_width'])
        
        # Комментарии
        comments = parsed_data.get('comments', {})
        if self.controller.order_data_module:
            self.controller.order_data_module.display_comments(comments, operations)

    def _show_multiple_orders(self, results: list):
        """Показывает выбор при нескольких найденных заказах"""
        
        self.controller.order_entry.grid_remove()
        self.controller.entry_suffix.grid_remove()
        
        self.controller.multiple_orders_data = results
        
        order_options = [order_data.get('order_number', '') for order_data in results]
        
        self.controller.order_combobox['values'] = order_options
        self.controller.order_combobox.set(order_options[0])
        self.controller.order_combobox.grid()
        self.controller.order_combobox_visible = True
        
        self.controller.parent.after(100, lambda: self.controller.order_combobox.focus_set())
        self.controller.parent.after(120, lambda: self.controller.order_combobox.event_generate('<Down>'))
        
        self.controller.order_data_module.parse_status.config(
            text=f"Найдено {len(results)} заказов. Выберите нужный:",
            foreground="orange"
        )

    # noinspection PyUnusedLocal
    def on_order_selected(self, event=None):
        """Обрабатывает выбор заказа из комбобокса"""
        selected_index = self.controller.order_combobox.current()
        if selected_index >= 0 and hasattr(self.controller, 'multiple_orders_data'):
            selected_order_data = self.controller.multiple_orders_data[selected_index]
            
            self.controller.order_combobox.grid_remove()
            self.controller.order_entry.grid()
            self.controller.entry_suffix.grid()
            self.controller.order_combobox_visible = False
            
            self._fill_technical_fields_only(selected_order_data)
            
            self.controller.order_data_module.cached_order_data = [selected_order_data]
            self.controller.order_data_module.cached_order_number = self.controller.order_number.get().strip()
            self.controller.order_data_module.get_product_name()
            
            delattr(self.controller, 'multiple_orders_data')
            
            self.controller.order_data_module.parse_status.config(
                text="Заказ выбран",
                foreground="green"
            )