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
    OPERATION_CODES = {
        '11511': 'winding_scheme',       # Схема намотки
        '8518': 'sleeve_diameter',       # Внутренний диаметр втулки
        '8516': 'streams_count',         # Количество ручьев для резки
        '8585': 'label_length_with_gap', # Длина этикетки с учетом зазора
        '8517': 'stream_width'           # Ширина ручья
    }
    
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
        """
        Парсит новый формат XML (с <ОперацииЗаказа>).
        
        Структура нового формата:
        <export>
          <order>
            <Заказчик>...</Заказчик>
            <parent_sheet>
              <product>
                <НомерДетали>...</НомерДетали>
                <НаименДетали>...</НаименДетали>
                <GTIN>...</GTIN>
                <ДатаЭмиссии>...</ДатаЭмиссии>
                <ТиражДетали>...</ТиражДетали>
              </product>
            </parent_sheet>
            <ОперацииЗаказа>
              <Операция>...</Операция> с кодами
            </ОперацииЗаказа>
          </order>
        </export>
        """
        try:
            root = ET.fromstring(xml_content)
            
            # Базовые данные заказа
            customer = self._get_text(root, './/Заказчик')
            
            # Общая дата эмиссии
            parent_sheet_date = self._get_text(root, './/parent_sheet/ДатаЭмиссии')
            
            # Данные продукта/детали
            products = []
            for product_elem in root.findall('.//product'):
                product = self._parse_product(product_elem, parent_sheet_date, root)
                if product:
                    products.append(product)
            
            # Данные из операций
            operations = self._parse_operations_new_format(root)
            comments = self._parse_comments_new_format(root)
            
            # Извлекаем sheet_name для поиска по тиражу
            sheet_name = self._get_text(root, './/НаименОттиска')
            sheet_number = ""
            if sheet_name:
                # Ищем паттерн "буква-цифры" в sheet_name
                match = re.search(r'[A-Za-zА-Яа-я]-?(\d+)', sheet_name)
                if match:
                    sheet_number = match.group(1)
            
            return {
                'format': 'NEW_FORMAT',
                'customer': customer,
                'products': products,
                'operations': operations,
                'comments': comments,
                'sheet_number': sheet_number,
                'sheet_name': sheet_name
            }
            
        except ET.ParseError as e:
            raise ValueError(f"Ошибка парсинга XML: {e}")
        except Exception as e:
            raise ValueError(f"Ошибка обработки XML: {e}")
            
    def _parse_comments_new_format(self, root: ET.Element) -> Dict[str, str]:
        """Извлекает комментарии из операций по ID операций (новый формат)."""
        comments = {}
        
        try:
            # Операции, которые нас интересуют
            target_operations = {
                '31': 'cutting_comment',    # Резка&перемотка
                '62': 'packaging_comment'   # Упаковка Цех-1
            }
            
            for operation in root.findall('.//ОперацииЗаказа//Операция'):
                op_id = operation.get('ВнутреннийИдентификатор', '')
                
                if op_id in target_operations:
                    # Ищем комментарий операции (код 65000)
                    prop = operation.find('.//Свойство[@Код="65000"]')
                    if prop is not None:
                        comment = prop.get('Значение', '')
                        if comment:
                            comments[target_operations[op_id]] = comment
        
        except Exception as e:
            print(f"Ошибка парсинга комментариев: {e}")
        
        return comments
    
    def _parse_product(self, product_elem: ET.Element, parent_sheet_date: str = "", root: ET.Element = None) -> Optional[Dict[str, str]]:
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
            
            # Ищем stream для конкретного вида в операции резки (ВнутреннийИдентификатор="31")
            stream = "1"  # Значение по умолчанию
            
            if root and detail_number:
                # Ищем все операции резки
                for operation in root.findall('.//Операция[@ВнутреннийИдентификатор="31"]'):
                    element_name = operation.get('НаименованиеЭлементаОперации', '')
                    
                    # Проверяем, содержит ли эта операция номер нашей детали
                    if detail_number in element_name:
                        # В этой операции ищем свойство с кодом 8516
                        prop = operation.find('.//Свойство[@Код="8516"]')
                        if prop is not None:
                            value = prop.get('Значение', '')
                            if value:
                                stream = value
                                break  # Нашли - выходим из цикла
            
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
                'sheet_name': self._get_sheet_name(product_elem),  # Для поиска по оттиску
                'stream': stream  # количество ручьёв для этого вида
            }
        except Exception as e:
            print(f"Ошибка парсинга продукта: {e}")
            return None
        
    def _get_sheet_name(self, product_elem: ET.Element) -> str:
        """Получает имя оттиска (НаименОттиска) для поиска."""
        try:
            # Ищем родительский parent_sheet
            parent = product_elem
            for _ in range(3):  # Максимум 3 уровня вверх
                parent = parent.getparent()
                if parent is None:
                    break
                if parent.tag.endswith('parent_sheet') or parent.tag == 'parent_sheet':
                    sheet_name_elem = parent.find('НаименОттиска')
                    if sheet_name_elem is not None and sheet_name_elem.text:
                        return sheet_name_elem.text.strip()
        except Exception:
            pass
        return ""
    
    def _parse_operations_new_format(self, root: ET.Element) -> Dict[str, str]:
        """Извлекает данные из операций по кодам (новый формат)."""
        operations = {}
        
        try:
            # Ищем все свойства во всех операциях
            for prop in root.findall('.//ОперацииЗаказа//Свойство'):
                code = prop.get('Код', '')
                value = prop.get('Значение', '')
                
                if code in self.OPERATION_CODES and value:
                    operations[self.OPERATION_CODES[code]] = value
        except Exception as e:
            print(f"Ошибка парсинга операций: {e}")
        
        return operations
    
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