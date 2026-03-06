# data_providers/base_provider.py
from typing import Dict, Any, Optional, Union

from core.config_manager import ConfigManager


class BaseDataProvider:
    """
    Базовый класс с общими методами сбора данных из UI.
    """
    
    def __init__(self, roll_module, config_manager: Optional[ConfigManager] = None, excel_file_path: str = "", coordinator=None):
        self.roll_module = roll_module
        self.config_manager = config_manager or ConfigManager()
        self.original_excel_path = excel_file_path
        self.coordinator = coordinator
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
            
            # ВАЖНО: Используем готовые данные из модуля производителя
            if hasattr(self.roll_module, 'get_manufacturer_full_data'):
                manufacturer_data = self.roll_module.get_manufacturer_full_data()
                
                if manufacturer_data.get('tu_number') and manufacturer_data['tu_number'].strip() not in ["—", "-", ""]:
                    # Есть TU номер из модуля производителя
                    data['tu_number'] = manufacturer_data['tu_number']
                    data['product_type'] = manufacturer_data.get('product', '')
                elif hasattr(self.roll_module, 'product_type_var') and self.roll_module.product_type_var.get():
                    # Нет TU из XML, но есть выбор в комбобоксе
                    data['product_type'] = self.roll_module.product_type_var.get()
                    data['tu_number'] = self._get_tu_number()
                else:
                    # Ничего нет
                    data['product_type'] = ""
                    data['tu_number'] = "ТУ технические условия"
            else:
                # Fallback на старую логику
                if hasattr(self.roll_module, 'product_type_var'):
                    data['product_type'] = self.roll_module.product_type_var.get()
                    data['tu_number'] = self._get_tu_number()
                else:
                    data['product_type'] = ""
                    data['tu_number'] = "ТУ технические условия"
                
        except Exception as e:
            print(f"Ошибка сбора общих данных: {e}")
            # Возвращаем частично собранные данные
            pass
            
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
            
            pallet_num_str = self.roll_module.preview_module.export_module.pallet_num_var.get()
            data['pallet_num'] = self._convert_to_number(pallet_num_str, force_int=True)            
            
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
            
            # Формируем текст для отображения с адресом из конфигурации
            if data['show_manufacturer'] and data['manufacturer_name']:
                # Ищем производителя в конфигурации для получения адреса
                manufacturer_address = self._get_manufacturer_address(data['manufacturer_name'])
                
                if manufacturer_address:
                    data['display_text'] = f'{data["manufacturer_name"]}, {manufacturer_address}'
                else:
                    # Если адрес не найден, показываем только имя
                    data['display_text'] = data['manufacturer_name']
                        
        except Exception as e:
            print(f"Ошибка сбора данных производителя: {e}")
            
        return data

    def _get_manufacturer_address(self, manufacturer_name: str) -> Optional[str]:
        """Получает адрес производителя из конфигурации packaging_tu.json"""
        try:
            if not manufacturer_name:
                return None
            
            # Ищем в конфигурации
            packaging_data = self.config_manager.load_json_settings("packaging_tu.json")
            technical_specs = packaging_data.get("technical_specifications", [])
            
            # Ищем точное совпадение по имени производителя
            for spec in technical_specs:
                if spec["manufacturer"]["name"] == manufacturer_name:
                    return spec["manufacturer"]["address"]
            
            # Если не нашли точного совпадения, пробуем частичное (на всякий случай)
            for spec in technical_specs:
                if manufacturer_name in spec["manufacturer"]["name"] or spec["manufacturer"]["name"] in manufacturer_name:
                    return spec["manufacturer"]["address"]
                    
        except Exception as e:
            print(f"Ошибка получения адреса производителя: {e}")
        
        return None
    
    @staticmethod
    def _convert_to_number(value: Optional[str], force_int: bool = False) -> Optional[Union[int, float]]:
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

    def get_excel_file_path(self, workshop: str, has_weight: bool = True) -> str:
        """Определяет путь к файлу Excel через координатор"""
        # Координатор всегда должен быть
        return self.coordinator.get_excel_file_path(workshop, has_weight)

                    