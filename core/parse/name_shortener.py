"""
Модуль для сокращения названий продуктов.
Содержит логику из dm_processor_right.shorthen_name()
"""

import os
import re
from typing import Dict


class NameShortener:
    def __init__(self, config_manager, coordinator):
        self.config_manager = config_manager
        self.custom_replacements = self._load_shortening_rules()
        
        # Подписываемся на общие уведомления от координатора
        coordinator.subscribe(self._reload_rules)

    # noinspection PyUnusedLocal
    def _reload_rules(self, context=None):
        """Перезагружает правила при любом уведомлении от координатора"""
        self.custom_replacements = self._load_shortening_rules()
        
    def _load_shortening_rules(self) -> Dict[str, str]:
        """
        Загружает правила сокращений из shortening_rules.json
        Если файла нет в data/, копирует из assets/
        """           
        try:
            # Проверяем существует ли файл в data_dir
            settings_path = self.config_manager.get_settings_path("shortening_rules.json")
            
            if not os.path.exists(settings_path):
                # Пробуем скопировать из assets
                self._copy_shortening_rules_from_assets()
            
            # Загружаем данные
            rules = self.config_manager.load_json_settings("shortening_rules.json")
            return rules if rules else {}
            
        except Exception as e:
            print(f"Ошибка загрузки правил сокращений: {e}")
            return {}
            
    def _copy_shortening_rules_from_assets(self):
        """Копирует файл shortening_rules.json из assets в data_dir"""
        try:
            # Получаем путь к файлу в assets
            asset_path = self.config_manager.get_asset_path("shortening_rules.json")
            
            # Получаем путь назначения в data_dir
            dest_path = self.config_manager.get_settings_path("shortening_rules.json")
            
            # Проверяем существует ли файл в assets
            if os.path.exists(asset_path):
                # Копируем файл
                import shutil
                shutil.copy2(asset_path, dest_path)
                print(f"Файл shortening_rules.json скопирован из {asset_path} в {dest_path}")
            else:
                print(f"Файл shortening_rules.json не найден в assets по пути: {asset_path}")
                
        except Exception as e:
            print(f"Ошибка копирования shortening_rules.json: {e}")
    
    def shorten_name(self, text: str) -> str:
        """
        Основной метод сокращения названия.
        Аналогичен dm_processor_right.shorthen_name()
        """
        if not text:
            return ""
            
        # Применяем пользовательские правила замены из JSON
        for original, replacement in self.custom_replacements.items():
            if original in text:
                # Если замена пустая строка - удаляем текст
                if not replacement:
                    text = text.replace(original, "")
                else:
                    text = text.replace(original, replacement)

        # Стандартные замены
        text = re.sub(r"Инд-\d{6}(,?\s*[Ээ]т\.?\s*)?,?\s*", "", text)
        text = re.sub(r"Э-\d{5}(,?\s*[Ээ]т\.?\s*)?,?\s*", "", text)
        text = re.sub(r"\d+[*хx]\d+", "", text)  # Удаляем размеры
        text = text.replace("-", " ")

        # noinspection SpellCheckingInspection
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
        
        # Удаляем лишние пробелы
        result = " ".join(words)
        result = re.sub(r'\s+', ' ', result).strip()
        
        return result