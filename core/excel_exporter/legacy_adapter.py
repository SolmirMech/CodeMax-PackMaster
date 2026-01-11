# core/excel_exporter/legacy_adapter.py
"""
Адаптер для обратной совместимости со старым кодом.
Позволяет постепенно мигрировать на новую архитектуру.
"""
import os
from typing import Dict, Any, Optional

from .data_provider import ExportDataProvider
from .cell_mappers import CellMappingRegistry, SheetMapping
from .exporter_core import SmartExporter
from core.config_manager import ConfigManager


class LegacyExporterAdapter:
    """
    Адаптер, имитирующий старый WeightOrdersExporter.
    """
    
    def __init__(self, excel_file_path, roll_module, preview_module, coordinator=None):
        self.original_excel_path = excel_file_path
        self.roll_module = roll_module
        self.preview_module = preview_module
        self.coordinator = coordinator
        self.config_manager = ConfigManager()
        self.has_weight = True
        if coordinator and hasattr(coordinator, 'subscribe'):
            # Подписываемся на уведомления координатора
            coordinator.subscribe(self.on_settings_changed)        
        
        # Создаем провайдер и экспортер новой архитектуры
        self.data_provider = ExportDataProvider(roll_module, self.config_manager)
        self.exporter = SmartExporter(self.data_provider, self.config_manager)
        
        # Внутреннее состояние
        self.wb = None
        self.ws = None
    
    @staticmethod
    def create_exporter(excel_file_path, roll_module, preview_module, coordinator=None):
        """
        Фабричный метод - полная совместимость со старым конструктором.
        Просто создает экземпляр LegacyExporterAdapter.
        """
        return LegacyExporterAdapter(excel_file_path, roll_module, preview_module, coordinator)
    
    def export_data(self, enable_pallet=False, pallet_data=None, multitype_mode=False):
        """
        Интерфейс, совместимый со старым WeightOrdersExporter.export_data
        Теперь с автоматическим выбором между pallet и noweight
        """
        # Обновляем статус веса перед каждым экспортом
        self.on_settings_changed()
        
        # Определяем цех
        workshop = self._determine_workshop()
        
        # Определяем тип листа
        if multitype_mode:
            sheet_type = "multitype"
        elif enable_pallet:
            # Автоматический выбор на основе веса
            if self.has_weight:
                sheet_type = "pallet"    # Лист для паллеты (с весом)
            else:
                sheet_type = "noweight"  # Лист БезВеса (без веса)
        else:
            sheet_type = "box"      
        
        # Получаем маппинг
        try:
            mapping = CellMappingRegistry.get_mapping(workshop, sheet_type, 
                                                     "box" if not enable_pallet else ("pallet" if self.has_weight else "noweight"))
        except ValueError as e:
            # Если маппинг не найден, используем fallback
            print(f"Маппинг не найден, используем старый экспорт: {e}")
            return self._legacy_fallback_export(enable_pallet, pallet_data, multitype_mode)
        
        # Получаем путь к файлу
        file_path = self._get_excel_file_path(workshop)
        
        # Выполняем экспорт
        try:
            result = self.exporter.export_to_sheet(
                file_path=file_path,
                mapping=mapping,
                mode="pallet" if enable_pallet else "box",
                pallet_data=pallet_data
            )
            
            # Отправляем уведомление через координатор
            if result['success'] and self.coordinator and hasattr(self.coordinator, 'notify'):
                self.coordinator.notify("excel_exported", {
                    'file_path': result['file_path'],
                    'sheet_name': result['sheet_name'],
                    'enable_pallet': enable_pallet,
                    'multitype_mode': multitype_mode,
                    'workshop': workshop,
                    'has_weight': self.has_weight  # Добавляем информацию о весе
                })          
            
            return result
            
        except Exception as e:
            print(f"Ошибка в новом экспортере: {e}")
            return self._legacy_fallback_export(enable_pallet, pallet_data, multitype_mode)
    
    def clear_all_rolls(self, enable_pallet=False, multitype_mode=False):
        """Очистка листа (обратная совместимость)"""
        try:
            workshop = self._determine_workshop()
            
            if multitype_mode:
                return self._legacy_multitype_clear(workshop, enable_pallet)
            
            # Обновляем статус веса перед очисткой
            self.on_settings_changed()
            
            # Определяем тип листа (Как в export_data!)
            if enable_pallet:
                # Автоматический выбор на основе веса
                if self.has_weight:
                    sheet_type = "pallet"    # Лист для паллеты (с весом)
                    mode = "pallet"
                else:
                    sheet_type = "noweight"  # Лист БезВеса (без веса)
                    mode = "noweight"
            else:
                sheet_type = "box"
                mode = "box"
            
            try:
                mapping = CellMappingRegistry.get_mapping(workshop, sheet_type, mode)
                file_path = self._get_excel_file_path(workshop)
                
                success = self.exporter.clear_sheet(file_path, mapping)
                
                if success and self.coordinator and hasattr(self.coordinator, 'notify'):
                    self.coordinator.notify("excel_cleared", {
                        'file_path': file_path,
                        'enable_pallet': enable_pallet,
                        'multitype_mode': multitype_mode,
                        'workshop': workshop,
                        'has_weight': self.has_weight  # Добавляем информацию о весе
                    })
                
                return success
                
            except ValueError as e:
                print(f"Маппинг не найден, используем старую очистку: {e}")
                return self._legacy_fallback_clear(enable_pallet, multitype_mode)
            
        except Exception as e:
            print(f"Ошибка в новом очистителе: {e}")
            return self._legacy_fallback_clear(enable_pallet, multitype_mode)
    
    # ==================== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ====================
    
    def _determine_workshop(self) -> str:
        """Определяет цех из координатора или по умолчанию"""
        if self.coordinator and hasattr(self.coordinator, 'get_workshop'):
            return self.coordinator.get_workshop()
        return "1"  # По умолчанию цех 1
    
    def _get_excel_file_path(self, workshop: str) -> str:
        """Определяет путь к файлу Excel"""
        # Копируем логику из старого get_excel_file_path
        try:
            # Получаем путь из настроек
            settings = self.config_manager.load_json_settings("shared_utils.json")
            excel_folder = settings.get("weight_orders_xlsx", "")
            
            if not excel_folder:
                excel_folder = os.path.dirname(self.original_excel_path)
            
            # Определяем имя файла
            filename = "weight_orders.xlsx" if workshop == "1" else "weight_orders_2.xlsx"
            full_path = os.path.join(excel_folder, filename)
            
            # Проверяем существование файла
            if not os.path.exists(full_path):
                # Копируем из assets
                assets_file = self.config_manager.get_asset_path(filename)
                if os.path.exists(assets_file):
                    import shutil
                    shutil.copy2(assets_file, full_path)
                    print(f"Файл {filename} скопирован в {full_path}")
                else:
                    raise FileNotFoundError(f"Файл {filename} не найден в assets")
            
            return full_path
            
        except Exception as e:
            print(f"Ошибка получения пути к Excel файлу: {e}")
            return self.original_excel_path
    
    def _legacy_multitype_export(self, workshop: str, pallet_data: Optional[Dict]) -> Dict[str, Any]:
        """Экспорт в много-видовой лист (временно через старый код)"""
        # TODO: Перевести на новую архитектуру позже
        print("Много-видовой экспорт пока через старый код")
        return self._legacy_fallback_export(False, pallet_data, True)
    
    def _legacy_multitype_clear(self, workshop: str, enable_pallet: bool) -> bool:
        """Очистка много-видового листа"""
        print("Очистка много-видового листа пока через старый код")
        return self._legacy_fallback_clear(enable_pallet, True)
    
    def _legacy_fallback_export(self, enable_pallet=False, pallet_data=None, multitype_mode=False):
        """Fallback на старую реализацию экспорта"""
        # Импортируем старый экспортер только при необходимости
        from .excel_exporter import WeightOrdersExporter as OldExporter
        
        old_exporter = OldExporter(
            excel_file_path=self.original_excel_path,
            roll_module=self.roll_module,
            preview_module=self.preview_module,
            coordinator=self.coordinator
        )
        
        return old_exporter.export_data(enable_pallet, pallet_data, multitype_mode)
    
    def _legacy_fallback_clear(self, enable_pallet=False, multitype_mode=False):
        """Fallback на старую очистку"""
        from .excel_exporter import WeightOrdersExporter as OldExporter
        
        old_exporter = OldExporter(
            excel_file_path=self.original_excel_path,
            roll_module=self.roll_module,
            preview_module=self.preview_module,
            coordinator=self.coordinator
        )
        
        return old_exporter.clear_all_rolls(enable_pallet, multitype_mode)
    
    # ==================== МЕТОДЫ ДЛЯ СОВМЕСТИМОСТИ ====================
    
    # Эти методы могут вызываться старым кодом, но не используются в новой архитектуре
    
    def get_excel_file_path(self):
        """Для совместимости со старым кодом"""
        workshop = self._determine_workshop()
        return self._get_excel_file_path(workshop)
    
    def _is_second_file(self):
        """Для совместимости"""
        workshop = self._determine_workshop()
        return workshop == "2"
    
    def on_settings_changed(self):
        """Обработчик изменения настроек от координатора"""
        # Обновляем статус веса (как в excel_preview_module)
        if self.coordinator and hasattr(self.coordinator, 'get_weight_status'):
            self.has_weight = self.coordinator.get_weight_status()
