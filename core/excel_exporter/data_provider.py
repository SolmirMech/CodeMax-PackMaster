# data_provider.py
import os
from core.config_manager import ConfigManager
from typing import Dict, Any, Optional, Union

class ExportDataProvider:
    """
    Единый централизованный сборщик данных из UI.
    Не знает о структуре Excel, только о данных.
    """
    
    def __init__(self, roll_module, config_manager: Optional[ConfigManager] = None):
        """
        Инициализация сборщика данных.
        
        Args:
            roll_module: Модуль UI с данными (должен иметь стандартные атрибуты)
            config_manager: Менеджер конфигурации для TU номеров и настроек
        """
        self.roll_module = roll_module
        self.config_manager = config_manager or ConfigManager()
        self._data_cache: Optional[Dict[str, Any]] = None
        
    def collect_all_data(self) -> Dict[str, Any]:
        """
        Собирает полный набор данных из UI для экспорта.
        Данные кешируются для повторного использования.
        
        Returns:
            Словарь с полными данными, структурированный по категориям
        """
        if self._data_cache is not None:
            return self._data_cache.copy()
            
        self._data_cache = {
            'common': self._get_common_data(),
            'weights': self._get_weight_data(),
            'quantities': self._get_quantity_data(),
            'dimensions': self._get_dimension_data(),
            'metadata': self._get_metadata(),
            'manufacturer': self._get_manufacturer_data()
        }
        
        return self._data_cache.copy()
    
    def clear_cache(self):
        """Очищает кеш данных (например, при изменении данных в UI)"""
        self._data_cache = None
    
    def get_data_for_workshop1_box(self) -> Dict[str, Any]:
        """
        Специализированный метод для 1 цеха, лист коробки.
        Возвращает только нужные для этого листа данные в удобном формате.
        """
        all_data = self.collect_all_data()
        
        return {
            # Основная информация
            'customer': all_data['common'].get('customer'),
            'box_type': all_data['common'].get('box_type'),
            'order_number': all_data['common'].get('order_number'),
            'product_text': all_data['common'].get('product_text'),
            'date': all_data['common'].get('date'),
            'packer': all_data['common'].get('packer'),
            'product_type': all_data['common'].get('product_type'),
            'tu_number': all_data['common'].get('tu_number'),
            
            # Веса
            'box_weight': all_data['weights'].get('box_weight'),
            'gross_weight_per_roll': all_data['weights'].get('gross_weight_per_roll'),
            'net_weight_per_roll': all_data['weights'].get('net_weight_per_roll'),
            
            # Количества
            'rolls_count': all_data['quantities'].get('rolls_count'),
            'quantity_per_roll': all_data['quantities'].get('quantity_per_roll'),
            
            # Производитель
            'show_manufacturer': all_data['manufacturer'].get('show_manufacturer'),
            'manufacturer_name': all_data['manufacturer'].get('manufacturer_name'),
            'manufacturer_display_text': all_data['manufacturer'].get('display_text'),
            
            # Дополнительно
            'workshop': '1',
            'sheet_type': 'box',
            'has_weight': all_data['metadata'].get('has_weight', False)
        }
    
    def get_data_for_workshop1_pallet(self) -> Dict[str, Any]:
        """
        Специализированный метод для 1 цеха, лист поддона.
        Включает данные о поддоне и коробках.
        """
        all_data = self.collect_all_data()
        
        # Получаем количество коробок
        boxes_count = all_data['quantities'].get('boxes_count', 0)
        if boxes_count == 0:
            boxes_count = 1
        
        return {
            # Основная информация (как для коробки)
            'customer': all_data['common'].get('customer'),            
            'order_number': all_data['common'].get('order_number'),
            'product_text': all_data['common'].get('product_text'),
            'date': all_data['common'].get('date'),
            'packer': all_data['common'].get('packer'),
            'product_type': all_data['common'].get('product_type'),
            'tu_number': all_data['common'].get('tu_number'),
            
            # Данные поддона
            'pallet_type': all_data['common'].get('pallet_type'),
            'pallet_weight': all_data['weights'].get('pallet_weight'),
            'boxes_count': boxes_count,
            
            # Данные одной коробки (для заполнения в динамические секции)
            'gross_weight_per_box': all_data['weights'].get('total_gross'),
            'net_weight_per_box': all_data['weights'].get('total_net'),
            'quantity_per_box': all_data['quantities'].get('total_quantity'),
            
            # Производитель
            'show_manufacturer': all_data['manufacturer'].get('show_manufacturer'),
            'manufacturer_name': all_data['manufacturer'].get('manufacturer_name'),
            'manufacturer_display_text': all_data['manufacturer'].get('display_text'),
            
            # Дополнительно
            'workshop': '1',
            'sheet_type': 'pallet',
            'has_weight': all_data['metadata'].get('has_weight', False)
        }
        
    def get_data_for_workshop1_noweight(self) -> Dict[str, Any]:
        """
        Специализированный метод для 1 цеха, лист БезВеса (поддон без веса).
        Только количество, без весовых полей.
        """
        all_data = self.collect_all_data()
        
        # Получаем количество коробок
        boxes_count = all_data['quantities'].get('boxes_count', 0)
        if boxes_count == 0:
            boxes_count = 1
        
        # Получаем общее количество этикеток
        total_quantity = all_data['quantities'].get('total_quantity', 0)
        
        return {
            # Основная информация
            'customer': all_data['common'].get('customer'),
            'order_number': all_data['common'].get('order_number'),
            'product_text': all_data['common'].get('product_text'),
            'date': all_data['common'].get('date'),
            'packer': all_data['common'].get('packer'),
            'product_type': all_data['common'].get('product_type'),
            'tu_number': all_data['common'].get('tu_number'),
            
            # Данные для динамических секций
            'boxes_count': boxes_count,
            'quantity_per_box': total_quantity,  # Только количество
            
            # Производитель
            'show_manufacturer': all_data['manufacturer'].get('show_manufacturer'),
            'manufacturer_name': all_data['manufacturer'].get('manufacturer_name'),
            'manufacturer_display_text': all_data['manufacturer'].get('display_text'),
            
            # Дополнительно
            'workshop': '1',
            'sheet_type': 'noweight',
            'has_weight': False  # Всегда False для этого метода
        }
    
    # ==================== ПРИВАТНЫЕ МЕТОДЫ СБОРА ====================
    
    def _get_common_data(self) -> Dict[str, Any]:
        """Собирает общие данные, общие для всех листов"""
        if not self.roll_module:
            return {}
            
        data = {}
        
        try:
            # Заказчик
            if hasattr(self.roll_module, 'customer_var'):
                data['customer'] = self.roll_module.customer_var.get()
            
            # Название коробки
            if hasattr(self.roll_module, 'box_size_var'):
                data['box_type'] = self.roll_module.box_size_var.get()
                
            # Название паллеты
            data['pallet_type'] = self.roll_module.preview_module.export_module.pallet_size_var.get()
                         
            # Полный номер заказа
            if hasattr(self.roll_module, 'order_prefix'):
                order_prefix = self.roll_module.order_prefix.get()
                order_number = getattr(self.roll_module, 'order_number', '').get()
                order_suffix = getattr(self.roll_module, 'order_suffix', '').get()
                data['order_number'] = f"{order_prefix}{order_number}{order_suffix}"
            
            # Наименование продукции (многострочное)
            if hasattr(self.roll_module, 'product_text'):
                product_text = self.roll_module.product_text.get("1.0", "end-1c").strip()
                data['product_text'] = product_text
            
            # Дата упаковки
            if hasattr(self.roll_module, 'date_var'):
                data['date'] = self.roll_module.date_var.get()
            
            # Упаковщик
            if hasattr(self.roll_module, 'packer_var'):
                data['packer'] = self.roll_module.packer_var.get()
            
            # TU номер из XML (новый источник)
            tu_number = None
            if hasattr(self.roll_module, 'xml_tu_number'):
                tu_number = self.roll_module.xml_tu_number
                if callable(tu_number):
                    tu_number = tu_number()
            
            if tu_number:
                # Есть TU номер из XML - вычисляем product_type
                data['tu_number'] = tu_number
                data['product_type'] = self._get_product_type_by_tu(tu_number)
            else:
                # Нет TU из XML - работаем по старой логике
                if hasattr(self.roll_module, 'product_type_var'):
                    data['product_type'] = self.roll_module.product_type_var.get()
                
                # TU номер вычисляется по product_type
                data['tu_number'] = self._get_tu_number()
                
        except Exception as e:
            print(f"Ошибка сбора общих данных: {e}")
            # Возвращаем частично собранные данные
            pass
            
        return data
    
    def _get_weight_data(self) -> Dict[str, Any]:
        """Собирает все данные, связанные с весом"""
        if not self.roll_module:
            return {}
            
        data = {}
        
        try:
            # Вес коробки
            if hasattr(self.roll_module, 'box_weight_var'):
                weight_str = self.roll_module.box_weight_var.get()
                data['box_weight'] = self._convert_to_number(weight_str)
                
            # Вес паллеты
            weight_str = self.roll_module.preview_module.export_module.pallet_weight_var.get()
            data['pallet_weight'] = self._convert_to_number(weight_str)
            
            # Общий вес брутто
            if hasattr(self.roll_module, 'total_gross_var'):
                weight_str = self.roll_module.total_gross_var.get()
                data['total_gross'] = self._convert_to_number(weight_str)
            
            # Общий вес нетто
            if hasattr(self.roll_module, 'total_net_var'):
                weight_str = self.roll_module.total_net_var.get()
                data['total_net'] = self._convert_to_number(weight_str)
            
            # Вес брутто одного ролика (кг)
            if hasattr(self.roll_module, 'gross_weight_kg_var'):
                weight_str = self.roll_module.gross_weight_kg_var.get()
                data['gross_weight_per_roll'] = self._convert_to_number(weight_str)
            
            # Вес нетто одного ролика (кг)
            if hasattr(self.roll_module, 'net_weight_kg_var'):
                weight_str = self.roll_module.net_weight_kg_var.get()
                data['net_weight_per_roll'] = self._convert_to_number(weight_str)
            
            # Вес втулки (граммы -> преобразуем в кг при необходимости)
            if hasattr(self.roll_module, 'sleeve_weight_var'):
                weight_str = self.roll_module.sleeve_weight_var.get()
                data['sleeve_weight_g'] = self._convert_to_number(weight_str)
                if data['sleeve_weight_g'] is not None:
                    data['sleeve_weight_kg'] = data['sleeve_weight_g'] / 1000
            
        except Exception as e:
            print(f"Ошибка сбора данных веса: {e}")
            
        return data
    
    def _get_quantity_data(self) -> Dict[str, Any]:
        """Собирает данные по количеству"""
        if not self.roll_module:
            return {}
            
        data = {}
        
        try:
            
            boxes_count_str = self.roll_module.preview_module.export_module.boxes_count_var.get()
            data['boxes_count'] = self._convert_to_number(boxes_count_str, force_int=True)
            
            # Количество роликов
            if hasattr(self.roll_module, 'rolls_count_var'):
                count_str = self.roll_module.rolls_count_var.get()
                data['rolls_count'] = self._convert_to_number(count_str, force_int=True)
            
            # Количество этикеток в ролике
            if hasattr(self.roll_module, 'quantity_var'):
                qty_str = self.roll_module.quantity_var.get()
                data['quantity_per_roll'] = self._convert_to_number(qty_str, force_int=True)
            
            # Общее количество этикеток
            if hasattr(self.roll_module, 'total_quantity_var'):
                qty_str = self.roll_module.total_quantity_var.get()
                data['total_quantity'] = self._convert_to_number(qty_str, force_int=True)
            
        except Exception as e:
            print(f"Ошибка сбора данных количества: {e}")
            
        return data
    
    def _get_dimension_data(self) -> Dict[str, Any]:
        """Собирает данные по размерам"""
        if not self.roll_module:
            return {}
            
        data = {}
        
        try:
            # Диаметр втулки
            if hasattr(self.roll_module, 'sleeve_diameter_var'):
                diam_str = self.roll_module.sleeve_diameter_var.get()
                data['sleeve_diameter'] = self._convert_to_number(diam_str)
            
            # Длина ролика
            if hasattr(self.roll_module, 'roll_length'):
                length_str = self.roll_module.roll_length.get()
                data['roll_length'] = self._convert_to_number(length_str)
            
        except Exception as e:
            print(f"Ошибка сбора данных размеров: {e}")
            
        return data
    
    def _get_metadata(self) -> Dict[str, Any]:
        """Собирает метаданные и состояние"""
        data = {}
        
        try:
            # Есть ли вес (определяем по total_gross)
            if hasattr(self.roll_module, 'total_gross_var'):
                weight_value = self.roll_module.total_gross_var.get()
                has_weight = bool(weight_value and str(weight_value).strip() and 
                                str(weight_value).strip() != '0')
                data['has_weight'] = has_weight
            else:
                data['has_weight'] = False
                
        except Exception as e:
            print(f"Ошибка сбора метаданных: {e}")
            data['has_weight'] = False
            
        return data
    
    def _get_manufacturer_data(self) -> Dict[str, Any]:
        """Собирает данные по производителю"""
        data = {
            'show_manufacturer': True,  # По умолчанию показываем
            'manufacturer_name': '',
            'display_text': ''
        }
        
        if not self.roll_module:
            return data
            
        try:
            # Чекбокс "Без изготовителя" (True = отмечен = не показывать)
            if hasattr(self.roll_module, 'show_manufacturer_var'):
                # Инвертируем: True в UI = "Без производителя" = не показывать
                data['show_manufacturer'] = not self.roll_module.show_manufacturer_var.get()
            
            # Имя производителя из комбобокса
            if hasattr(self.roll_module, 'manufacturer_var'):
                data['manufacturer_name'] = self.roll_module.manufacturer_var.get()
            
            # Формируем текст для отображения
            if data['show_manufacturer'] and data['manufacturer_name']:
                address = 'Россия, 426039, Удмуртская Республика, г. Ижевск, ул. Воткинское шоссе, д. 186, офис 1'
                
                if "Ремас" in data['manufacturer_name']:
                    data['display_text'] = f'ООО "Ремас-Флексо", {address}'
                elif "Зюдин" in data['manufacturer_name']:
                    data['display_text'] = f'ИП Зюдин В.Г., {address}'
                else:
                    data['display_text'] = data['manufacturer_name']
                    
        except Exception as e:
            print(f"Ошибка сбора данных производителя: {e}")
            
        return data 
    
    def _get_tu_number(self) -> str:
        """Получает TU номер на основе производителя и типа продукта"""
        try:
            if not self.roll_module:
                return "ТУ технические условия"  # Fallback
                
            manufacturer = self.roll_module.manufacturer_var.get() if hasattr(self.roll_module, 'manufacturer_var') else ""
            
            # Используем уже вычисленный product_type из data, если есть
            product_type = self.roll_module.product_type_var.get() if hasattr(self.roll_module, 'product_type_var') else ""
            
            if not manufacturer or not product_type:
                return "ТУ технические условия"
            
            # Ищем в конфигурации
            packaging_data = self.config_manager.load_json_settings("packaging_tu.json")
            technical_specs = packaging_data.get("technical_specifications", [])
            
            for spec in technical_specs:
                if (spec["manufacturer"]["name"] == manufacturer and 
                    spec["product"]["name"] == product_type):
                    return spec["product"]["tu_number"]
                    
        except Exception as e:
            print(f"Ошибка получения ТУ номера: {e}")
        
        return "ТУ технические условия"  # Fallback
        
    def _get_product_type_by_tu(self, tu_number: str) -> str:
        """Получает тип продукта по TU номеру из конфигурации"""
        try:
            if not tu_number or not self.roll_module:
                return self.roll_module.product_type_var.get() if hasattr(self.roll_module, 'product_type_var') else ""
            
            # Ищем в конфигурации
            packaging_data = self.config_manager.load_json_settings("packaging_tu.json")
            technical_specs = packaging_data.get("technical_specifications", [])
            
            for spec in technical_specs:
                if spec["product"]["tu_number"] == tu_number:
                    return spec["product"]["name"]
                    
        except Exception as e:
            print(f"Ошибка получения типа продукта по ТУ номеру: {e}")
        
        # Fallback - возвращаем текущее значение из UI
        return self.roll_module.product_type_var.get() if hasattr(self.roll_module, 'product_type_var') else ""
    
    def _convert_to_number(self, value: Optional[str], force_int: bool = False) -> Optional[Union[int, float]]:
        """
        Безопасно преобразует строку в число.
        
        Args:
            value: Строка для преобразования
            force_int: Принудительно возвращать целое число
            
        Returns:
            Число (int или float) или None
        """
        if value is None:
            return None
            
        if not isinstance(value, str):
            # Если уже число - возвращаем как есть
            if isinstance(value, (int, float)):
                return int(value) if force_int and value.is_integer() else value
            return None
        
        value = value.strip()
        if not value:
            return None
        
        # Пробуем целое число
        try:
            if value.isdigit():
                return int(value)
        except:
            pass
        
        # Пробуем дробное число
        try:
            normalized = value.replace(',', '.')
            # Проверяем формат числа с плавающей точкой
            if normalized.replace('.', '').isdigit() and normalized.count('.') == 1:
                result = float(normalized)
                return int(result) if force_int and result.is_integer() else result
        except:
            pass
        
        return None