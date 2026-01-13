"""
Модуль парсинга XML заказов.
Поддерживает новый формат (с <ОперацииЗаказа>)
"""

import xml.etree.ElementTree as ET
import re
from typing import Dict, List, Optional, Any
from core.parse.name_shortener import NameShortener


class XMLOrderParser:
    """Парсер XML файлов заказов."""   
    
    # Коды операций, которые нас интересуют
    OPERATION_PROPERTIES = {
        '11511': 'winding_scheme',       # Схема намотки
        '8518': 'sleeve_diameter',       # Внутренний диаметр втулки
        '8516': 'streams_count',         # Количество ручьев для резки
        '8585': 'label_length_with_gap', # Длина этикетки с учетом зазора
        '8517': 'stream_width',           # Ширина ручья
        '32543': 'aggregation_status'    # Статус агрегации
    }
    
    # Код свойства для комментариев
    COMMENT_PROPERTY_CODE = '65000'    
    
    def __init__(self, custom_replacements=None):
        self.shortener = NameShortener(custom_replacements) 
    
    def parse(self, xml_content: str) -> Dict[str, Any]:
        """
        Главный метод парсинга XML (только новый формат).
        """
        try:
            return self._parse_new_format(xml_content)
        except Exception as e:
            raise ValueError(f"Ошибка обработки XML: {e}")
    
    def _parse_new_format(self, xml_content: str) -> Dict[str, Any]:
        """Парсит новый формат XML (с <ОперацииЗаказа>)."""
        try:
            root = ET.fromstring(xml_content)
            
            # Базовые данные заказа
            customer = self._get_text(root, './/Заказчик')
            
            executor = self._get_text(root, './/Исполнитель')
            
            tu_number = self._get_text(root, './/ТУ')
            
            # Добавляем парсинг номера заказа
            order_number = self._get_text(root, './/НомерЗаказа')
            order_prefix = ""
            order_suffix = ""
            
            if order_number:
                # Извлекаем префикс (буквы в начале) и суффикс (после цифр)
                prefix_match = re.match(r'^([A-ZА-Я]+)', order_number)
                if prefix_match:
                    order_prefix = prefix_match.group(1)
                
                # Ищем суффикс после цифр (например, /5)
                suffix_match = re.search(r'(\/\d+)$', order_number)
                if suffix_match:
                    order_suffix = suffix_match.group(1)
            
            # Общая дата эмиссии
            parent_sheet_date = self._get_text(root, './/parent_sheet/ДатаЭмиссии')
            
            # Словарь для быстрого поиска: id_order_sheet -> sheet_number
            sheet_mapping = {}
            
            # Сначала собираем все sheet_number для каждого parent_sheet
            for parent_sheet in root.findall('.//parent_sheet'):
                id_elem = parent_sheet.find('id_order_sheet')
                sheet_name_elem = parent_sheet.find('НаименОттиска')
                
                if id_elem is not None and id_elem.text and sheet_name_elem is not None and sheet_name_elem.text:
                    sheet_id = id_elem.text.strip()
                    sheet_name = sheet_name_elem.text.strip()
                    
                    # Извлекаем цифры из НаименОттиска
                    match = re.search(r'(\d+)', sheet_name)
                    if match:
                        sheet_mapping[sheet_id] = match.group(1)
            
            # Теперь парсим продукты
            products = []
            for product_elem in root.findall('.//product'):
                # Получаем id_order_sheet этого продукта
                sheet_id_elem = product_elem.find('id_order_sheet')
                sheet_number = ""
                
                if sheet_id_elem is not None and sheet_id_elem.text:
                    sheet_id = sheet_id_elem.text.strip()
                    sheet_number = sheet_mapping.get(sheet_id, "")
                
                product = self._parse_product(
                    product_elem,
                    parent_sheet_date,
                    root,
                    sheet_number
                )
                if product:
                    products.append(product)
                                
            # Данные из операций
            operations, comments = self._parse_operations_and_comments(root)
            
            return {
                'format': 'NEW_FORMAT',
                'customer': customer,
                'executor': executor,
                'tu_number': tu_number,
                'order_number': order_number,
                'order_prefix': order_prefix,
                'order_suffix': order_suffix,
                'products': products,
                'operations': operations,
                'comments': comments
            }
            
        except ET.ParseError as e:
            raise ValueError(f"Ошибка парсинга XML: {e}")
        except Exception as e:
            raise ValueError(f"Ошибка обработки XML: {e}")
            
    def _parse_operations_and_comments(self, root: ET.Element) -> tuple[Dict[str, str], Dict[str, str]]:
        """
        Единый метод для парсинга операций и комментариев.
        Ищет в операциях резки и упаковки для обоих цехов.
        
        Returns:
            tuple: (operations_dict, comments_dict)
        """
        operations = {}
        comments = {}
        
        try:
            # Ищем операции с нужными идентификаторами (цех 1 и цех 2)
            for operation in root.findall('.//ОперацииЗаказа//Операция'):
                op_id = operation.get('ВнутреннийИдентификатор', '')
                
                # Определяем тип операции по ID
                is_cutting = op_id in ['31', '230']       # Резка (цех 1 и цех 2)
                is_packaging = op_id in ['62', '220']     # Упаковка (цех 1 и цех 2)
                
                if not (is_cutting or is_packaging):
                    continue  # Пропускаем нерелевантные операции
                
                # 1. Парсим комментарии (свойство 65000)
                if is_cutting:
                    comment_key = 'cutting_comment'
                elif is_packaging:
                    comment_key = 'packaging_comment'
                
                comment_prop = operation.find(f'.//Свойство[@Код="{self.COMMENT_PROPERTY_CODE}"]')
                if comment_prop is not None:
                    comment = comment_prop.get('Значение', '')
                    if comment:
                        comments[comment_key] = comment
                
                # 2. Парсим технические свойства (только для операций резки)
                if is_cutting:
                    for prop in operation.findall('.//Свойство'):
                        code = prop.get('Код', '')
                        value = prop.get('Значение', '')
                        
                        # Берем только нужные свойства
                        if code in self.OPERATION_PROPERTIES and value:
                            operations[self.OPERATION_PROPERTIES[code]] = value            
        
        except Exception as e:
            print(f"Ошибка парсинга операций и комментариев: {e}")
        
        return operations, comments
    
    def _parse_product(self, product_elem: ET.Element, parent_sheet_date: str = "", 
                       root: ET.Element = None, sheet_number: str = "") -> Optional[Dict[str, str]]:
        """Парсит элемент <product>."""
        try:
            detail_number = self._get_text(product_elem, 'НомерДетали')
            product_name = self._get_text(product_elem, 'НаименДетали')
            gtin = self._get_text(product_elem, 'GTIN')
            shortened_name = self.shortener.shorten_name(product_name)
            
            # Если GTIN в отдельном теге и его нет в сокращенном имени
            if gtin and len(gtin) >= 4 and f"джит{gtin[-4:]}" not in shortened_name:
                shortened_name = f"{shortened_name} джит{gtin[-4:]}"
            
            # Индивидуальная дата эмиссии из продукта
            individual_date = self._get_text(product_elem, 'ДатаЭмиссии')
            
            # Приоритет: 1) индивидуальная, 2) родительская, 3) пустая
            date_emission = individual_date if individual_date else parent_sheet_date
            
            quantity = self._get_text(product_elem, 'ТиражДетали')
            
            if not product_name:  # Если нет названия - продукт невалиден
                return None
            
            # Берем stream из тега КолвоРучьев внутри product, а не из операции
            stream = self._get_text(product_elem, 'КолвоРучьев')
            if not stream:
                stream = "1"  # Значение по умолчанию
            
            # Формируем полное название с джит
            full_name = product_name
            if gtin and len(gtin) >= 4:
                short_gtin = gtin[-4:]
                full_name = f"{product_name} джит{short_gtin}"        
            
            return {
                'detail_number': detail_number,  # Для поиска
                'product_name': product_name,
                'full_name': shortened_name,  # Для отображения в UI
                'gtin': gtin,
                'date_emission': date_emission,  # С приоритетом
                'quantity': quantity,  # ТиражДетали
                'sheet_number': sheet_number,  # Только цифры из тиража (57043, 57044 и т.д.)
                'stream': stream  # количество ручьёв для этого вида
            }
        except Exception as e:
            print(f"Ошибка парсинга продукта: {e}")
            return None
    
    def _get_text(self, elem: ET.Element, xpath: str = None, default: str = "") -> str:
        """Безопасно получает текст из элемента."""
        try:
            if xpath:
                found = elem.find(xpath)
                if found is not None and found.text:
                    return found.text.strip()
            elif elem is not None and elem.text:
                return elem.text.strip()
        except Exception:
            pass
        return default   
        
# Фабричная функция для удобства использования
def parse_xml(xml_content: str) -> Dict[str, Any]:
    """Упрощенный интерфейс для парсинга XML."""
    parser = XMLOrderParser()
    return parser.parse(xml_content)