"""
Модуль парсинга XML заказов.
Поддерживает новый формат (с <ОперацииЗаказа>)
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
        '32543': 'aggregation_status',    # Статус агрегации
        '8519': 'max_labels_per_roll'
    }
    
    # Код свойства для комментариев
    COMMENT_PROPERTY_CODE = '65000'    
    
    def __init__(self, custom_replacements=None):
        pass
        
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
            raw_customer = self._get_text(root, './/Заказчик', '')
            executor = self._get_text(root, './/Исполнитель')
            tu_number = self._get_text(root, './/ТУ')
            order_name = self._get_text(root, './/НаименЗаказа', '').lower()
            
            # Нормализация заказчика
            customer_info = self._normalize_customer(raw_customer, order_name)
            
            # Парсинг номера заказа
            order_number = self._get_text(root, './/НомерЗаказа')
            order_prefix = ""
            order_suffix = ""
            
            if order_number:
                prefix_match = re.match(r'^([A-ZА-Я]+)', order_number)
                if prefix_match:
                    order_prefix = prefix_match.group(1)
                
                suffix_match = re.search(r'(\/\d+)$', order_number)
                if suffix_match:
                    order_suffix = suffix_match.group(1)
            
            # Общая дата эмиссии
            parent_sheet_date = self._get_text(root, './/parent_sheet/ДатаЭмиссии')
            
            # 1. Собираем mapping для оттисков
            sheet_mapping = {}           # id -> sheet_number (только цифры)
            sheet_full_name_mapping = {} # id -> полное название оттиска
            
            for parent_sheet in root.findall('.//parent_sheet'):
                id_elem = parent_sheet.find('id_order_sheet')
                sheet_name_elem = parent_sheet.find('НаименОттиска')
                
                if id_elem is not None and id_elem.text and sheet_name_elem is not None and sheet_name_elem.text:
                    sheet_id = id_elem.text.strip()
                    sheet_full_name = sheet_name_elem.text.strip()
                    sheet_full_name_mapping[sheet_id] = sheet_full_name
                    
                    # Извлекаем цифры из названия оттиска
                    # Пытаемся найти номер оттиска (обычно в конце или после дефиса)
                    match = re.search(r'[-\s](\d{4,6})(?:\D|$)', sheet_full_name)
                    if match:
                        sheet_mapping[sheet_id] = match.group(1)  # Только цифры
                    else:
                        # Альтернативный поиск любых 4-6 цифр
                        match_all = re.search(r'(\d{4,6})', sheet_full_name)
                        if match_all:
                            sheet_mapping[sheet_id] = match_all.group(1)
                        else:
                            sheet_mapping[sheet_id] = ""  # Пусто, если не нашли
            
            # 2. Собираем метраж для каждого оттиска
            sheet_metrage_mapping = {}  # id_order_sheet -> order_metrage
            
            # Ищем все операции резки
            for operation in root.findall('.//ОперацииЗаказа//Операция'):
                op_id = operation.get('ВнутреннийИдентификатор', '')
                if op_id not in ['31', '230']:  # Только операции резки
                    continue
                
                # Название элемента операции
                op_element_name = operation.get('НаименованиеЭлементаОперации', '')
                if not op_element_name:
                    continue
                
                # Ищем, к какому sheet_id относится эта операция
                # Сравниваем с полным названием оттиска
                for sheet_id, sheet_full_name in sheet_full_name_mapping.items():
                    # Проверяем, содержит ли название операции название оттиска
                    # или наоборот, название оттиска содержит часть операции
                    if (sheet_full_name and op_element_name and 
                        (sheet_full_name[:30] in op_element_name or 
                         op_element_name[:30] in sheet_full_name)):
                        output = operation.get('Выработка')
                        if output:
                            try:
                                sheet_metrage_mapping[sheet_id] = float(output)
                            except ValueError:
                                pass
                        break
            
            # 3. Парсим продукты
            products = []
            for product_elem in root.findall('.//product'):
                # Получаем id_order_sheet этого продукта
                sheet_id_elem = product_elem.find('id_order_sheet')
                sheet_number = ""
                sheet_full_name = ""
                order_metrage = ""
                
                if sheet_id_elem is not None and sheet_id_elem.text:
                    sheet_id = sheet_id_elem.text.strip()
                    sheet_number = sheet_mapping.get(sheet_id, "")  # Только цифры
                    sheet_full_name = sheet_full_name_mapping.get(sheet_id, "")  # Полное название
                    order_metrage = sheet_metrage_mapping.get(sheet_id, "")
                
                product = self._parse_product(
                    product_elem=product_elem,
                    parent_sheet_date=parent_sheet_date,
                    root=root,
                    sheet_number=sheet_number,        # ← Только цифры (для совместимости)
                    sheet_full_name=sheet_full_name,   # ← Новое поле: полное название
                    order_metrage=order_metrage
                )
                if product:
                    products.append(product)
                                
            # Данные из операций (технические свойства и комментарии)
            operations, comments, has_solmark = self._parse_operations_and_comments(root)
            
            return {
                'format': 'NEW_FORMAT',
                'customer': customer_info['customer'],
                '_customer_info': customer_info,
                'executor': executor,
                'tu_number': tu_number,
                'order_number': order_number,
                'order_prefix': order_prefix,
                'order_suffix': order_suffix,
                'order_name': order_name,
                'products': products,
                'operations': operations,
                'comments': comments,
                'has_solmark': has_solmark
            }
            
        except ET.ParseError as e:
            raise ValueError(f"Ошибка парсинга XML: {e}")
        except Exception as e:
            raise ValueError(f"Ошибка обработки XML: {e}")
            
    def _normalize_customer(self, raw_customer: str, order_name: str) -> Dict:
        """
        Возвращает словарь с заказчиком(-ами) и информацией для статистики.
        
        Правила:
        1. Если один заказчик — возвращаем его
        2. Если несколько и есть совпадение в названии — выбираем этого
        3. Если несколько и НЕТ совпадений — возвращаем всех через запятую
        """
        # Проверяем входные данные
        if not raw_customer or not isinstance(raw_customer, str):
            return {
                'customer': '',
                'all_customers': [],
                'has_multiple': False,
                'selected_index': -1,
                'selection_method': 'empty'
            }
        
        # Разделяем заказчиков
        customers = [c.strip() for c in raw_customer.split(',') if c.strip()]
        
        # Если один заказчик — просто возвращаем
        if len(customers) <= 1:
            return {
                'customer': raw_customer,
                'all_customers': customers,
                'has_multiple': False,
                'selected_index': 0,
                'selection_method': 'single'
            }
        
        # Если несколько и есть название заказа — пробуем найти совпадение
        selected_customer = None
        selected_index = -1
        method = 'no_match_returns_all'
        
        if order_name:
            order_name_lower = order_name.lower()
            
            # Ищем совпадения
            for i, cust in enumerate(customers):
                cust_lower = cust.lower()
                
                # Разбиваем на слова и ищем частичные совпадения
                words = order_name_lower.split()
                for word in words:
                    if len(word) >= 3 and word in cust_lower:
                        selected_customer = cust
                        selected_index = i
                        method = 'auto_match'
                        break
                
                if selected_customer:
                    break
        
        # Если нашли совпадение — возвращаем этого заказчика
        if selected_customer:
            return {
                'customer': selected_customer,
                'all_customers': customers,
                'has_multiple': True,
                'selected_index': selected_index,
                'selection_method': method
            }
        else:
            # ЕСЛИ НЕТ СОВПАДЕНИЙ — ВОЗВРАЩАЕМ ВСЕХ ЗАКАЗЧИКОВ
            return {
                'customer': raw_customer,  # ← оригинальная строка со всеми
                'all_customers': customers,
                'has_multiple': True,
                'selected_index': -1,  # -1 значит "все"
                'selection_method': 'no_match_returns_all'
            }
            
    def _parse_operations_and_comments(self, root: ET.Element) -> tuple[Dict[str, str], Dict[str, str], bool]:
        """
        Единый метод для парсинга операций, комментариев и выявления Solmark заказов.
        
        Returns:
            tuple: (operations_dict, comments_dict, has_solmark)
        """
        operations = {}
        comments = {}
        has_solmark = False  # Флаг для определения Solmark заказов
        
        try:
            # Ищем операции с нужными идентификаторами (цех 1 и цех 2)
            for operation in root.findall('.//ОперацииЗаказа//Операция'):
                op_id = operation.get('ВнутреннийИдентификатор', '')
                
                # Проверяем на Solmark (ID 321 - Струйная печать DM (Solmark))
                if op_id == '321':
                    has_solmark = True
                
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
                        
                        # Обработка диаметра ролика
                        if code == '8519':  # Внешн. диаметр ролика
                            # Ищем единицу измерения
                            unit_prop = operation.find('.//Свойство[@Код="8522"]')
                            unit = unit_prop.get('Значение', '') if unit_prop is not None else ''
                            
                            if unit == 'шт.':
                                operations['max_labels_per_roll'] = value  # Кол-во в штуках
                            else:
                                operations['diameter_mm'] = value  # Диаметр в мм
                                operations['diameter_unit'] = unit
                        
                        # Остальные свойства
                        elif code in self.OPERATION_PROPERTIES and value:
                            operations[self.OPERATION_PROPERTIES[code]] = value
        
        except Exception as e:
            print(f"Ошибка парсинга операций и комментариев: {e}")
        
        # Добавляем флаг Solmark в operations для удобства
        operations['has_solmark'] = str(has_solmark)
        
        return operations, comments, has_solmark
        
    @staticmethod
    def extract_gtin_from_text(text: str) -> str:
        """
        Извлекает GTIN из текста по тем же правилам, что и shorten_name().
        Возвращает полный GTIN (12-14 цифр) или пустую строку.
        
        Правила (из shorten_name()):
        1. 14 цифр подряд где угодно в тексте
        2. 12-14 цифр в скобках
        """
        if not text or not isinstance(text, str):
            return ""
        
        text = text.strip()
        
        # Способ 1: Ищем 14 цифр подряд (без скобок) - как в shorten_name()
        # Это соответствует: for i in range(len(text)): if text[i].isdigit(): temp_code = text[i:i+14]
        match_14_digits = re.search(r'(\d{14})', text)
        if match_14_digits:
            return match_14_digits.group(1)
        
        # Способ 2: Ищем 12-14 цифр в скобках - как в shorten_name() и find_order()
        # Это соответствует: code_start = text.find("("); full_code = text[code_start+1:code_end]
        match_in_brackets = re.search(r'\((\d{12,14})\)', text)
        if match_in_brackets:
            return match_in_brackets.group(1)
        
        # Способ 3: Ищем 12-14 цифр с границами слова (дополнительная защита)
        # Для случаев типа "Товар 04620039591615 текст"
        match_with_boundaries = re.search(r'\b(\d{12,14})\b', text)
        if match_with_boundaries:
            return match_with_boundaries.group(1)
        
        return ""        
    
    def _parse_product(self, product_elem: ET.Element, parent_sheet_date: str = "",
                       root: ET.Element = None, sheet_number: str = "",
                       sheet_full_name: str = "",
                       order_metrage: Any = None) -> Optional[Dict[str, Any]]:
        """Парсит элемент <product>."""
        try:
            detail_number = self._get_text(product_elem, 'НомерДетали')
            product_name = self._get_text(product_elem, 'НаименДетали')
            if not product_name:  # Если нет названия - продукт невалиден
                return None            
            gtin = self._get_text(product_elem, 'GTIN')
            
            if not gtin and product_name:
                gtin = self.extract_gtin_from_text(product_name)
            
            # Индивидуальная дата эмиссии из продукта
            individual_date = self._get_text(product_elem, 'ДатаЭмиссии')
            
            # Приоритет: 1) индивидуальная, 2) родительская, 3) пустая
            date_emission = individual_date if individual_date else parent_sheet_date
            
            quantity = self._get_text(product_elem, 'ТиражДетали')           
            
            # Берем stream из тега КолвоРучьев внутри product
            stream = self._get_text(product_elem, 'КолвоРучьев')
            if not stream:
                stream = "1"  # Значение по умолчанию
            
            # Формируем полное название с джит
            full_name = product_name
            
            # Создаём словарь продукта
            product_dict = {
                'detail_number': detail_number,
                'product_name': product_name,
                'full_name': full_name,
                'gtin': gtin,
                'date_emission': date_emission,
                'quantity': quantity,
                'sheet_number': sheet_number,        # ← Только цифры (для совместимости)
                'sheet_full_name': sheet_full_name,  # ← Полное название оттиска
                'stream': stream,
                'order_metrage': order_metrage
            }          
            
            return product_dict
            
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