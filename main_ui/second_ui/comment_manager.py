"""
Модуль управления комментариями и их отображением.
"""

import re
import tkinter as tk


class CommentManager:
    """Управление комментариями и их визуализацией."""
    
    def __init__(self, parent, comment_button=None, config_manager=None, customer_var=None):
        """Инициализация менеджера комментариев."""
        self.parent = parent
        self.config_manager = config_manager
        self.comment_button = comment_button  # Может быть None
        self.customer_var = customer_var
        self.blinking_active = False
        self.blink_after_id = None
        
        # Переменные
        self.cutting_comment_var = tk.StringVar(value="")
        self.packaging_comment_var = tk.StringVar(value="")
        self.aggregation_status_var = tk.StringVar(value="")      
        
    def get_special_requirements(self):
        """Получает особые требования для текущего заказчика."""
        if not self.customer_var:
            return ""
        
        current_customer = self.customer_var.get().strip()
        if not current_customer:
            return ""
        
        try:
            if self.config_manager:
                settings = self.config_manager.load_json_settings("shared_utils.json")
                special_clients = settings.get("special_clients", {})
                
                # 1. Точное совпадение
                if current_customer in special_clients:
                    return special_clients[current_customer]
                
                # 2. Ищем по частичному совпадению (если имя из словаря содержится в имени заказчика)
                current_lower = current_customer.lower()
                
                for client_name, requirements in special_clients.items():
                    if not client_name:
                        continue
                        
                    client_name_lower = client_name.lower()
                    
                    # Если имя клиента из словаря содержится в текущем имени заказчика
                    if client_name_lower in current_lower:
                        return requirements
                    
                    # Или наоборот - если текущий заказчик содержится в имени из словаря
                    # (на случай, если в словаре полное имя, а в поле - сокращенное)
                    if current_lower in client_name_lower:
                        return requirements
                
                # 3. Ищем по очищенным названиям (убираем ООО, ОАО, ЗАО и т.д.)
                cleaned_current = self._clean_company_name(current_customer)
                cleaned_current_lower = cleaned_current.lower()
                
                for client_name, requirements in special_clients.items():
                    if not client_name:
                        continue
                        
                    cleaned_client = self._clean_company_name(client_name)
                    cleaned_client_lower = cleaned_client.lower()
                    
                    # Сравниваем очищенные названия
                    if (cleaned_client_lower in cleaned_current_lower or 
                        cleaned_current_lower in cleaned_client_lower):
                        return requirements
                
                return ""
            return ""
        except Exception as e:
            print(f"Ошибка загрузки особых требований: {e}")
            return ""

    @staticmethod
    def _clean_company_name(name):
        """Очищает название компании от организационно-правовых форм и лишних символов."""
        if not name:
            return name
        
        # Убираем ООО, ОАО, ЗАО, ИП и т.д.
        patterns_to_remove = [
            r'ООО\s*["«]?|["»]?\s*ООО',
            r'ОАО\s*["«]?|["»]?\s*ОАО', 
            r'ЗАО\s*["«]?|["»]?\s*ЗАО',
            r'ИП\s*["«]?|["»]?\s*ИП',
            r'АО\s*["«]?|["»]?\s*АО',
            r'ПАО\s*["«]?|["»]?\s*ПАО',
            r'НКО\s*["«]?|["»]?\s*НКО',
            r'ТОО\s*["«]?|["»]?\s*ТОО',
            r'\([^)]*\)',  # Убираем всё в скобках
            r'["«»]',      # Убираем кавычки
        ]
        
        cleaned = name
        for pattern in patterns_to_remove:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        # Убираем лишние пробелы
        cleaned = ' '.join(cleaned.split())
        
        return cleaned.strip()
        
    def set_comments(self, cutting_comment="", packaging_comment="", aggregation_status=""):
        """Устанавливает комментарии и статус агрегации."""
        self.cutting_comment_var.set(cutting_comment)
        self.packaging_comment_var.set(packaging_comment)
        self.aggregation_status_var.set(aggregation_status)
        
        # Проверяем наличие особых требований
        special_requirements = self.get_special_requirements()
        
        # Проверяем, есть ли статус агрегации и он ли "Да"
        has_aggregation_yes = aggregation_status and aggregation_status.strip().lower() == "да"
        
        # Старая логика для кнопки (если она существует)
        if self.comment_button:
            if cutting_comment or packaging_comment or special_requirements or has_aggregation_yes:
                self.comment_button.grid()
                self.comment_button.config(state="normal")
            else:
                self.comment_button.grid_remove()
                self.comment_button.config(state="disabled")
        
        # Возвращаем информацию о наличии комментариев
        return {
            'has_comments': bool(cutting_comment or packaging_comment or special_requirements),
            'has_aggregation': has_aggregation_yes
        }
        
    def get_comments(self):
        """
        Возвращает текущие комментарии.
        
        Returns:
            dict: Словарь с комментариями
        """
        return {
            'cutting': self.cutting_comment_var.get(),
            'packaging': self.packaging_comment_var.get()
        }      
            
