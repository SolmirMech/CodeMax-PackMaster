"""
Модуль для сокращения названий продуктов.
Содержит логику из dm_processor_right.shorthen_name()
"""

import re
from typing import Dict


class NameShortener:
    def __init__(self, custom_replacements: Dict[str, str] = None):
        """
        Args:
            custom_replacements: словарь пользовательских замен
        """
        self.custom_replacements = custom_replacements or {}
        
    def shorten_name(self, text: str) -> str:
        """
        Основной метод сокращения названия.
        Аналогичен dm_processor_right.shorthen_name()
        """
        # Применяем пользовательские правила замены
        for original, replacement in self.custom_replacements.items():
            text = text.replace(original, replacement)

        # Стандартные замены
        text = re.sub(r"Инд-\d{6}(,?\s*[Ээ]т\.?\s*)?,?\s*", "", text)
        text = re.sub(r"Э-\d{5}(,?\s*[Ээ]т\.?\s*)?,?\s*", "", text)
        text = re.sub(r"\d+[*хx]\d+", "", text)  # Удаляем размеры
        text = text.replace("-", " ")

        replacements = {
            "негазированная": "негаз",
            "газированная": "газ",
            "серебряная": "серебр",
            "групповой код": "ГК",
            "питьевая": "",
            "Дата Матрикс": "",
            "EAN": "",
            "DM код": "",
            "квадратный": "",
            "мм": "",
            "GTIN": "",
            "ЧЕСТНЫЙ ЗНАК": "",
            "ЧЗ": "",
            "(ДМ+EAN-13)": "",
            "Стикер": "",
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        # **КЛЮЧЕВОЕ: Обработка GTIN кодов В ТЕКСТЕ (для Ф0524)**
        for i in range(len(text)):
            if text[i].isdigit():
                temp_code = text[i : i + 14]
                if len(temp_code) == 14 and temp_code.isdigit():
                    last4 = temp_code[-4:]
                    text = text[:i] + "джит" + last4 + text[i + 14 :]
                    break

        # Обработка GTIN в скобках
        code_start = text.find("(")
        code_end = text.find(")")
        if code_start > 0 and code_end > code_start:
            full_code = text[code_start + 1 : code_end]
            if len(full_code) >= 12 and len(full_code) <= 14 and full_code.isdigit():
                last4 = full_code[-4:]
                text = text[:code_start] + "(джит" + last4 + ")" + text[code_end + 1 :]

        text = re.sub(r"\(джит(\d{4})\)", r"джит\1", text)
        text = re.sub(r"\(\s*\)", "", text)
        # Очистка кавычек
        text = re.sub(r'"\s*"', ' ', text)
        text = re.sub(r'^"+', '', text)
        text = re.sub(r'"+$', '', text)
        text = re.sub(r'\s*"\s*$', '', text)
        text = re.sub(r'^\s*"\s*', '', text)
        
        # Преобразование слов в КАПСЕ
        words = text.split()
        for i, word in enumerate(words):
            if word.isupper() and len(word) > 1:
                words[i] = word.capitalize()
        
        return " ".join(words)