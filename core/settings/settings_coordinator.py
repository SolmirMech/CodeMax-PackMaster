# settings_coordinator.py
from typing import Callable


class SettingsCoordinator:
    """Координатор настроек цеха и шаблонов шрифтов"""
    WORKSHOP_TEMPLATE_MAP = {
        "1": "1_цех",
        "2": "2_цех"
    }
    
    _instance = None
    
    def __new__(cls, config_manager=None):
        if cls._instance is None:
            cls._instance = super(SettingsCoordinator, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config_manager=None):
        self._current_archive_status = None
        self._current_font_template = None
        self._current_workshop = None
        if self._initialized:
            return
            
        self.config_manager = config_manager
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

    def _save_font_template_setting(self) -> bool:
        """Сохраняет настройку шаблона шрифтов"""
        try:
            settings = self.config_manager.load_json_settings("shared_utils.json") or {}
            settings["last_font_template"] = self._current_font_template
            success = self.config_manager.save_json_settings("shared_utils.json", settings)
            return success  # ← возвращаем результат
        except Exception as e:
            print(f"Ошибка сохранения шаблона шрифтов: {e}")
            return False  # ← возвращаем False при ошибке
            
    def check_weight_status(self, roll_module):
        """Проверяет наличие веса и уведомляет подписчиков"""
        has_weight = False
        if roll_module and hasattr(roll_module, 'gross_weight_kg_var'):
            weight_value = roll_module.gross_weight_kg_var.get()
            if weight_value and str(weight_value).strip() and str(weight_value).strip() != '0':
                has_weight = True
        
        # Всегда обновляем и уведомляем (старая логика)
        self._has_weight = has_weight
        self.notify_subscribers()
        
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
    
    def notify_subscribers(self):
        """Уведомляет всех подписчиков об изменениях"""
        context = {"type": "settings_changed"}  # ← обычное изменение настроек
        for callback in self._subscribers:
            try:
                callback(context)
            except Exception as e:
                print(f"Ошибка уведомления подписчика: {e}")
                
    def notify_list_changed(self, list_name: str):
        """Уведомляет об изменении списка"""
        print(f"Список {list_name} изменен")
        # Передаём подписчикам контекст с типом уведомления
        context = {"type": "list_changed", "list_name": list_name}
        for callback in self._subscribers:
            try:
                callback(context)  # ← теперь передаём контекст
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
            self.notify_subscribers()
            
    def _is_template_synced_with_workshop(self) -> bool:
        """Проверяет синхронизацию шаблона с цехом"""
        expected_template = self.WORKSHOP_TEMPLATE_MAP.get(self._current_workshop)
        return self._current_font_template == expected_template            
            
    def _auto_sync_template_with_workshop(self):
        """Автоматически синхронизирует шаблон с цехом"""
        self._current_font_template = self.WORKSHOP_TEMPLATE_MAP.get(self._current_workshop)
    
    def set_font_template(self, template: str):
        """Устанавливает шаблон шрифтов"""
        if template != self._current_font_template:
            self._current_font_template = template
            
            # Сохраняем настройки
            self._save_font_template_setting()
            self.notify_subscribers()
    
    def get_workshop(self) -> str:
        """Возвращает текущий цех"""
        return self._current_workshop
    
    def get_font_template(self) -> str:
        """Возвращает текущий шаблон шрифтов"""
        return self._current_font_template
    
    @staticmethod
    def get_workshop_template_mapping() -> dict:
        """Возвращает соответствие цехов и шаблонов"""
        return SettingsCoordinator.WORKSHOP_TEMPLATE_MAP.copy()
        
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
                self.notify_subscribers()
        except Exception as e:
            print(f"Ошибка обновления статуса архивации: {e}")

    def _save_workshop_setting(self) -> bool:
        """Сохраняет настройку цеха"""
        try:
            settings = self.config_manager.load_json_settings("shared_utils.json") or {}
            settings["workshop"] = self._current_workshop
            success = self.config_manager.save_json_settings("shared_utils.json", settings)
            return success
        except Exception as e:
            print(f"Ошибка сохранения цеха: {e}")
            return False
    