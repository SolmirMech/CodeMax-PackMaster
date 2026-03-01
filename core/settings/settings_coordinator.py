# settings_coordinator.py
from typing import Callable


class SettingsCoordinator:
    """Координатор настроек цеха и других общих параметров"""

    _instance = None

    def __new__(cls, config_manager=None):
        if cls._instance is None:
            cls._instance = super(SettingsCoordinator, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, config_manager=None):
        if self._initialized:
            return

        self.config_manager = config_manager
        self._subscribers = []
        self._current_workshop = None
        self._current_archive_status = None
        self._has_weight = False

        self._load_initial_settings()
        self._initialized = True
        self.roll_module = None
        self.settings_manager = None
        self.settings_dialog = None

    def set_settings_manager(self, manager):
        """Устанавливает ссылку на менеджера настроек"""
        self.settings_manager = manager

    def get_settings_manager(self):
        """Возвращает менеджер настроек"""
        return self.settings_manager

    def set_roll_module(self, roll_module):
        """Устанавливает ссылку на модуль ролика"""
        self.roll_module = roll_module

    def get_roll_module(self):
        """Возвращает модуль ролика"""
        return self.roll_module

    def set_settings_dialog(self, dialog):
        """Устанавливает ссылку на диалог настроек"""
        self.settings_dialog = dialog

    def _load_initial_settings(self):
        """Загружает начальные настройки"""
        try:
            settings = self.config_manager.load_json_settings("shared_utils.json") or {}
            self._current_workshop = settings.get("workshop", "1")
            self._current_archive_status = settings.get("archive_status", "on")
        except Exception as e:
            print(f"Ошибка загрузки начальных настроек: {e}")

    def check_weight_status(self, roll_module):
        """Проверяет наличие веса и уведомляет подписчиков"""
        has_weight = False
        if roll_module and hasattr(roll_module, 'gross_weight_kg_var'):
            weight_value = roll_module.gross_weight_kg_var.get()
            if weight_value and str(weight_value).strip() and str(weight_value).strip() != '0':
                has_weight = True

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

    def notify_subscribers(self, context=None):
        """Уведомляет всех подписчиков об изменениях"""
        if context is None:
            context = {"type": "settings_changed"}

        for callback in self._subscribers:
            try:
                callback(context)
            except Exception as e:
                print(f"Ошибка уведомления подписчика: {e}")

    def notify_list_changed(self, list_name: str):
        """Уведомляет об изменении списка"""
        context = {"type": "list_changed", "list_name": list_name}
        self.notify_subscribers(context)

    def set_workshop(self, workshop: str):
        """Устанавливает цех"""
        if workshop not in ["1", "2"]:
            raise ValueError("Цех должен быть '1' или '2'")

        if workshop != self._current_workshop:
            self._current_workshop = workshop
            self._save_workshop_setting()
            self.notify_subscribers()

    def get_workshop(self) -> str:
        """Возвращает текущий цех"""
        return self._current_workshop

    def get_archive_status(self) -> str:
        """Возвращает текущий статус архивации"""
        return getattr(self, '_current_archive_status', 'on')

    def refresh_archive_status(self):
        """Обновляет статус архивации из настроек"""
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
            return self.config_manager.save_json_settings("shared_utils.json", settings)
        except Exception as e:
            print(f"Ошибка сохранения цеха: {e}")
            return False