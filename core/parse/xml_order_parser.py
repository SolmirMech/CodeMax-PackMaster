"""
Модуль парсинга XML заказов.
Поддерживает новый формат (с <ОперацииЗаказа>) и старый формат.
"""

import xml.etree.ElementTree as ET
import re
from typing import Dict, List, Optional, Any


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
    
    def __init__(self):
        self.format_type = None  # 'NEW_FORMAT' или 'OLD_FORMAT'
    
    def detect_format(self, xml_content: str) -> str:
        """Определяет формат XML."""
        if "<ОперацииЗаказа>" in xml_content:
            return "NEW_FORMAT"
        else:
            return "OLD_FORMAT"
    
    def parse(self, xml_content: str) -> Dict[str, Any]:
        """
        Главный метод парсинга XML.
        """
        self.format_type = self.detect_format(xml_content)
        
        if self.format_type == "NEW_FORMAT":
            return self._parse_new_format(xml_content)
        else:
            return self._parse_old_format(xml_content)
    
    def _parse_new_format(self, xml_content: str) -> Dict[str, Any]:
        """Парсит новый формат XML (с <ОперацииЗаказа>)."""
        try:
            root = ET.fromstring(xml_content)
            
            # Базовые данные заказа
            customer = self._get_text(root, './/Заказчик')
            
            # Общая дата эмиссии - ДОЛЖНА БЫТЬ ОПРЕДЕЛЕНА ДО ИСПОЛЬЗОВАНИЯ
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
                    parent_sheet_date,  # ← ТЕПЕРЬ ОПРЕДЕЛЕНА
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
        Ищет ТОЛЬКО в операциях с идентификаторами 31 и 62.
        
        Returns:
            tuple: (operations_dict, comments_dict)
        """
        operations = {}
        comments = {}
        
        try:
            # Ищем только операции с нужными идентификаторами
            for operation in root.findall('.//ОперацииЗаказа//Операция'):
                op_id = operation.get('ВнутреннийИдентификатор', '')
                
                # Пропускаем операции не с теми идентификаторами
                if op_id not in ['31', '62']:
                    continue
                
                # 1. Парсим комментарии (свойство 65000)
                if op_id == '31':
                    comment_key = 'cutting_comment'
                elif op_id == '62':
                    comment_key = 'packaging_comment'
                else:
                    continue
                
                comment_prop = operation.find(f'.//Свойство[@Код="{self.COMMENT_PROPERTY_CODE}"]')
                if comment_prop is not None:
                    comment = comment_prop.get('Значение', '')
                    if comment:
                        comments[comment_key] = comment
                
                # 2. Парсим технические свойства
                for prop in operation.findall('.//Свойство'):
                    code = prop.get('Код', '')
                    value = prop.get('Значение', '')
                    
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
            
            # Индивидуальная дата эмиссии из продукта
            individual_date = self._get_text(product_elem, 'ДатаЭмиссии')
            
            # Приоритет: 1) индивидуальная, 2) родительская, 3) пустая
            date_emission = individual_date if individual_date else parent_sheet_date
            
            quantity = self._get_text(product_elem, 'ТиражДетали')
            
            if not product_name:  # Если нет названия - продукт невалиден
                return None
            
            # ВАЖНО: Берем stream из тега КолвоРучьев внутри product, а не из операции!
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
                'full_name': full_name,  # Для отображения в UI
                'gtin': gtin,
                'date_emission': date_emission,  # С приоритетом
                'quantity': quantity,  # ТиражДетали
                'sheet_number': sheet_number,  # Только цифры из тиража (57043, 57044 и т.д.)
                'stream': stream  # количество ручьёв для этого вида
            }
        except Exception as e:
            print(f"Ошибка парсинга продукта: {e}")
            return None             
    
    def _parse_old_format(self, xml_content: str) -> Dict[str, Any]:
        """
        Парсит старый формат XML.
        """
        try:
            root = ET.fromstring(xml_content)
            
            # Проверяем, является ли это форматом с атрибутами (5208.xml)
            if self._is_attributes_format(root):
                return self._parse_attributes_format(root)
                
            general_date_emission = self._get_text(root, './/date_emission')
            
            # ищем customer в другом месте
            customer = ""
            # Сначала попробуем найти в элементе <order_num>
            order_num_elem = root.find('.//order_num')
            if order_num_elem is not None and order_num_elem.text:
                # Может содержать информацию о заказчике
                pass
            
            products = []
            # Ищем <object> внутри <id_man_factjob>
            for obj_elem in root.findall('.//object'):
                detail_num_elem = obj_elem.find('detail_num')
                detail_name_elem = obj_elem.find('detail_name')
                gtin_elem = obj_elem.find('GTIN')
                stream_elem = obj_elem.find('stream')
                tirazh_elem = obj_elem.find('tirazh_product')
                
                detail_num = self._get_text(detail_num_elem)
                product_name = self._get_text(detail_name_elem)
                
                if product_name:
                    # Объединяем detail_name и сокращенный GTIN
                    if gtin_elem is not None and gtin_elem.text:
                        gtin = gtin_elem.text.strip()
                        if gtin and len(gtin) >= 4:
                            short_gtin = gtin[-4:]
                            full_name = f"{product_name} джит{short_gtin}"
                        else:
                            full_name = product_name
                    else:
                        full_name = product_name
                        
                    stream = self._get_text(stream_elem) or "1"
                    
                    products.append({
                        'detail_number': detail_num,
                        'product_name': product_name,
                        'full_name': full_name,
                        'gtin': self._get_text(gtin_elem),
                        'date_emission': general_date_emission,
                        'quantity': self._get_text(tirazh_elem),
                        'sheet_name': self._get_text(root, './/sheet_name'),
                        'stream': stream
                    })
            
            # Для старого формата операции извлекаются из других мест
            operations = {}
            # В старом формате нет операций с кодами
            
            # Извлекаем sheet_number для поиска
            sheet_name = self._get_text(root, './/sheet_name')
            sheet_number = ""
            if sheet_name:
                match = re.search(r'[A-Za-zА-Яа-я]-?(\d+)', sheet_name)
                if match:
                    sheet_number = match.group(1)
            
            return {
                'format': 'OLD_FORMAT',
                'customer': customer,  # Будет пустым в этом формате
                'products': products,
                'operations': operations,
                'sheet_number': sheet_number,
                'sheet_name': sheet_name
            }
            
        except Exception as e:
            print(f"Ошибка парсинга старого формата: {e}")
            return {
                'format': 'OLD_FORMAT',
                'customer': '',
                'products': [],
                'operations': {},
                'sheet_number': '',
                'sheet_name': ''
            }
    
    def _is_attributes_format(self, root: ET.Element) -> bool:
        """Проверяет, является ли XML форматом с данными в атрибутах (5208.xml)."""
        try:
            if root.tag.endswith('Report'):
                attributes = root.attrib
                if 'Textbox1' in attributes and 'Textbox5' in attributes:
                    return True
        except:
            pass
        return False
    
    def _parse_attributes_format(self, root: ET.Element) -> Dict[str, Any]:
        """Парсит XML формат с данными в атрибутах корневого элемента (5208.xml)."""
        try:
            attributes = root.attrib
            
            product_name = attributes.get('Textbox5', '').strip()
            customer = attributes.get('Textbox1', '').strip()
            winding_scheme = attributes.get('заказчик14', '').strip()
            sleeve_diameter = attributes.get('заказчик13', '').strip().replace(' мм', '')
            
            if product_name:
                products = [{
                    'detail_number': '',
                    'product_name': product_name,
                    'full_name': product_name,
                    'gtin': '',
                    'quantity': attributes.get('заказчик20', '').strip(),
                    'sheet_name': ''
                }]
            else:
                products = []
            
            operations = {}
            if winding_scheme:
                operations['winding_scheme'] = winding_scheme
            if sleeve_diameter:
                operations['sleeve_diameter'] = sleeve_diameter
            
            return {
                'format': 'ATTRIBUTES_FORMAT',
                'customer': customer,
                'products': products,
                'operations': operations,
                'sheet_number': '',
                'sheet_name': ''
            }
            
        except Exception as e:
            print(f"Ошибка парсинга атрибутного формата: {e}")
            return {
                'format': 'ATTRIBUTES_FORMAT',
                'customer': '',
                'products': [],
                'operations': {},
                'sheet_number': '',
                'sheet_name': ''
            }
    
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
    
    def extract_search_data(self, parsed_data: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Извлекает данные для поиска.
        """
        result = {
            'detail_numbers': [],
            'sheet_names': [],
            'full_names': []
        }
        
        for product in parsed_data.get('products', []):
            if product.get('detail_number'):
                result['detail_numbers'].append(product['detail_number'])
            if product.get('full_name'):
                result['full_names'].append(product['full_name'])
            if product.get('sheet_name'):
                result['sheet_names'].append(product['sheet_name'])
        
        return result


# Фабричная функция для удобства использования
def parse_xml(xml_content: str) -> Dict[str, Any]:
    """Упрощенный интерфейс для парсинга XML."""
    parser = XMLOrderParser()
    return parser.parse(xml_content)