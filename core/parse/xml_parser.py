# core/parse/xml_parser.py
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
        3. Поиск внутри файлов (штрих-код) — если не найден по имени

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

        # 3. Поиск по содержимому (штрих-код может быть в любом теге)
        try:
            for fname in os.listdir(search_dir):
                if not fname.endswith(".xml"):
                    continue
                full_path = os.path.join(search_dir, fname)
                try:
                    tree = ET.parse(full_path)
                    root = tree.getroot()
                    # Ищем артикул во всём тексте XML
                    xml_text = ET.tostring(root, encoding="unicode").lower()
                    if article_clean.lower() in xml_text:
                        return full_path
                except ET.ParseError:
                    continue
        except OSError:
            pass

        return None