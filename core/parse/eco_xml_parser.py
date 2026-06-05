# core/parse/eco_xml_parser.py
"""Парсер XML для заполнения упаковочного листа Экосистема"""

import os
# noinspection PyPep8Naming
import xml.etree.ElementTree as ET


class EcosystemXMLParser:
    """Парсер XML-файлов Экосистемы. Извлекает данные для PackingListWindow."""

    # Маппинг тегов XML → ключи словаря
    TAG_MAPPING = {
        "supplier": "supplier",
        "customer": "customer",
        "consignee": "consignee",
        "contract": "contract",
        "project": "project",
        "equipment_name": "equipment_name",
    }

    @staticmethod
    def parse(xml_path: str) -> dict | None:
        """
        Парсит XML-файл и возвращает словарь с данными.
        Возвращает None при ошибке.
        """
        try:
            with open(xml_path, 'r', encoding='windows-1251') as f:
                content = f.read()

            # Убираем BOM и всё до '<'
            bom_pos = content.find('<')
            if bom_pos > 0:
                content = content[bom_pos:]

            # Приводим декларацию к windows-1251
            content = content.replace('encoding="UTF-8"', 'encoding="windows-1251"')
            content = content.replace("encoding='UTF-8'", "encoding='windows-1251'")

            tree = ET.ElementTree(ET.fromstring(content))
            root = tree.getroot()

            result = {}
            for tag, key in EcosystemXMLParser.TAG_MAPPING.items():
                element = root.find(tag)
                result[key] = element.text.strip() if element is not None and element.text else ""

            # Парсим данные товара (одна строка)
            item_elem = root.find('item')
            if item_elem is not None:
                result['item_data'] = {
                    'order_request': item_elem.findtext('order_request', default=""),
                    'article_vn': item_elem.findtext('article_vn', default=""),
                    'name': item_elem.findtext('name', default=""),
                    'unit': item_elem.findtext('unit', default=""),
                    'quantity': item_elem.findtext('quantity', default="0"),
                    'article_vn_product': item_elem.findtext('article_vn_product', default=""),
                    'product': item_elem.findtext('product', default=""),
                }

            # Парсим данные места (одна строка)
            place_elem = root.find('place')
            if place_elem is not None:
                result['place_data'] = {
                    'net_weight': place_elem.findtext('net_weight', default="0"),
                    'gross_weight': place_elem.findtext('gross_weight', default="0"),
                    'length': place_elem.findtext('length', default="0"),
                    'width': place_elem.findtext('width', default="0"),
                    'height': place_elem.findtext('height', default="0"),
                    'storage_type': place_elem.findtext('storage_type', default=" "),
                }

            return result

        except Exception as e:
            print(f"Ошибка парсинга XML {xml_path}: {e}")
            return None

    @staticmethod
    def find_xml(article: str, search_dir: str) -> str | None:
        """
        Ищет XML-файл по артикулу.
        Стратегия поиска:
        1. Точное совпадение: article.xml
        2. По последним 4 цифрам: *XXXX.xml

        Возвращает полный путь к файлу или None.
        """
        if not article or not search_dir or not os.path.isdir(search_dir):
            return None

        article_clean = article.strip()

        # 1. Точное совпадение
        exact_path = os.path.join(search_dir, f"{article_clean}.xml")
        if os.path.isfile(exact_path):
            return exact_path

        # 2. По последним 4 цифрам
        if len(article_clean) >= 4:
            suffix = article_clean[-4:]
            try:
                for fname in os.listdir(search_dir):
                    if fname.endswith(f".xml") and fname[:-4].endswith(suffix):
                        return os.path.join(search_dir, fname)
            except OSError:
                pass

        return None