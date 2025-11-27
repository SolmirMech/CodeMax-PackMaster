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
        self._current_workshop = "1"
        self._current_font_template = "1_цех"
        
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
                
        except Exception as e:
            print(f"Ошибка загрузки начальных настроек: {e}") 

    def _save_font_template_setting(self):
        """Сохраняет настройку шаблона шрифтов"""
        try:
            settings = self.config_manager.load_json_settings("shared_utils.json") or {}
            settings["last_font_template"] = self._current_font_template
            success = self.config_manager.save_json_settings("shared_utils.json", settings)
        except Exception as e:
            print(f"DEBUG: _save_font_template_setting error: {e}")
    
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
    
    def _save_workshop_setting(self):
        """Сохраняет настройку цеха"""
        try:
            print(f"SAVE WORKSHOP: Сохраняем цех '{self._current_workshop}' в файл")
            import traceback
            traceback.print_stack()  # Покажет кто вызвал этот метод
            
            settings = self.config_manager.load_json_settings("shared_utils.json") or {}
            settings["workshop"] = self._current_workshop
            success = self.config_manager.save_json_settings("shared_utils.json", settings)
            print(f"SAVE WORKSHOP: Успех = {success}")
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