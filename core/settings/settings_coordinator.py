# settings_coordinator.py
import os
from typing import Callable
from core.config_manager import ConfigManager

class SettingsCoordinator:
    """Координатор настроек цеха и шаблонов шрифтов"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SettingsCoordinator, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.config_manager = ConfigManager()
        self._subscribers = []
        
        # Инициализируем статус веса
        self._has_weight = False
        
        self._load_initial_settings()
        self._initialized = True       
    
    def _load_initial_settings(self):
        """Загружает начальные настройки"""
        try:
            settings = self.config_manager.load_json_settings("shared_utils.json") or {}
            
            # Загружаем цех
            workshop = settings.get("workshop", "1")
            self._current_workshop = workshop
            
            # Загружаем шаблон шрифтов
            font_template = settings.get("last_font_template", "1_цех")
            self._current_font_template = font_template
            
            # Загружаем статус архивации
            archive_status = settings.get("archive_status", "on")
            self._current_archive_status = archive_status            
            
            if not self._is_template_synced_with_workshop():
                self._auto_sync_template_with_workshop()
                self._save_font_template_setting()
                
        except Exception as e:
            print(f"Ошибка загрузки начальных настроек: {e}") 

    def _save_font_template_setting(self):
        """Сохраняет настройку шаблона шрифтов"""
        try:
            settings = self.config_manager.load_json_settings("shared_utils.json") or {}
            settings["last_font_template"] = self._current_font_template
            success = self.config_manager.save_json_settings("shared_utils.json", settings)
        except Exception as e:
            print(f"Ошибка сохранения шаблона шрифтов: {e}")
            
    def check_weight_status(self, roll_module):
        """Проверяет наличие веса и уведомляет подписчиков"""
        has_weight = False
        if roll_module and hasattr(roll_module, 'gross_weight_kg_var'):
            weight_value = roll_module.gross_weight_kg_var.get()
            if weight_value and str(weight_value).strip() and str(weight_value).strip() != '0':
                has_weight = True
        
        # Сохраняем статус и уведомляем подписчиков
        self._has_weight = has_weight
        self._notify_subscribers()
        
    def get_weight_status(self):
        """Возвращает статус наличия веса"""
        return getattr(self, '_has_weight', False)
    
    def subscribe(self, callback: Callable):
        """Подписывает компонент на уведомления об изменениях"""
        if callback not in self._subscribers:
            self._subscribers.append(callback)
    
    def unsubscribe(self, callback: Callable):
        """Отписывает компонент от уведомлений"""
        if callback in self._subscribers:
            self._subscribers.remove(callback)
    
    def _notify_subscribers(self):
        """Уведомляет всех подписчиков об изменениях"""
        for callback in self._subscribers:
            try:
                callback()
            except Exception as e:
                print(f"Ошибка уведомления подписчика: {e}")
                
    def notify_list_changed(self, list_name: str):
        """Уведомляет об изменении списка"""
        print(f"Список {list_name} изменен")
        # Пока просто уведомляем всех подписчиков
        self._notify_subscribers()                
    
    def set_workshop(self, workshop: str):
        if workshop not in ["1", "2"]:
            raise ValueError("Цех должен быть '1' или '2'")
        
        if workshop != self._current_workshop:
            self._current_workshop = workshop
            self._auto_sync_template_with_workshop()
            
            # Синхронизируем шаблон с цехом
            if not self._is_template_synced_with_workshop():
                self._auto_sync_template_with_workshop()
            
            self._save_workshop_setting()
            self._notify_subscribers()
            
    def _is_template_synced_with_workshop(self) -> bool:
        """Проверяет синхронизацию шаблона с цехом"""
        expected_template = "1_цех" if self._current_workshop == "1" else "2_цех"
        return self._current_font_template == expected_template            
            
    def _auto_sync_template_with_workshop(self):
        """Автоматически синхронизирует шаблон с цехом"""
        new_template = "1_цех" if self._current_workshop == "1" else "2_цех"
        self._current_font_template = new_template
    
    def set_font_template(self, template: str):
        """Устанавливает шаблон шрифтов"""
        if template != self._current_font_template:
            self._current_font_template = template
            
            # Сохраняем настройки
            self._save_font_template_setting()
            self._notify_subscribers()
    
    def get_workshop(self) -> str:
        """Возвращает текущий цех"""
        return self._current_workshop
    
    def get_font_template(self) -> str:
        """Возвращает текущий шаблон шрифтов"""
        return self._current_font_template
    
    def get_workshop_template_mapping(self) -> dict:
        """Возвращает соответствие цехов и шаблонов"""
        return {
            "1": "1_цех",
            "2": "2_цех"
        }
        
    def get_archive_status(self) -> str:
        """Возвращает текущий статус архивации"""
        return getattr(self, '_current_archive_status', 'on')
    
    def refresh_archive_status(self):
        """Обновляет статус архивации из настроек и уведомляет подписчиков"""
        try:
            settings = self.config_manager.load_json_settings("shared_utils.json") or {}
            new_status = settings.get("archive_status", "on")
            
            if new_status != getattr(self, '_current_archive_status', 'on'):
                self._current_archive_status = new_status
                self._notify_subscribers()
        except Exception as e:
            print(f"Ошибка обновления статуса архивации: {e}")                       
    
    def _save_workshop_setting(self):
        """Сохраняет настройку цеха"""
        try:
            settings = self.config_manager.load_json_settings("shared_utils.json") or {}
            settings["workshop"] = self._current_workshop
            success = self.config_manager.save_json_settings("shared_utils.json", settings)
        except Exception as e:
            print(f"Ошибка сохранения цеха: {e}")
    
    def apply_workshop_changes(self, preview_module):
        """Применяет изменения цеха ко всем компонентам"""
        try:          
            # Уведомляем подписчиков
            self._notify_subscribers()
            
            # Перезагружаем превью модуль
            if hasattr(preview_module, 'reload_for_workshop_change'):
                preview_module.reload_for_workshop_change()
                
        except Exception as e:
            print(f"Ошибка применения изменений цеха: {e}")