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
        self.has_weight = False
        if coordinator and hasattr(coordinator, 'subscribe'):
            # Подписываемся на уведомления координатора
            coordinator.subscribe(self.on_settings_changed)        
        
        # Создаем провайдер и экспортер новой архитектуры
        self.data_provider = ExportDataProvider(
            roll_module, 
            self.config_manager,
            excel_file_path=self.original_excel_path  # ← передаем excel_file_path
        )
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
    
    def export_data(self, enable_pallet=False, multitype_mode=False):
        """
        Интерфейс, совместимый со старым WeightOrdersExporter.export_data
        Теперь с автоматическим выбором между pallet и noweight
        """
        self.on_settings_changed()
        workshop = getattr(self, 'workshop', '1')
        
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
            print(f"Маппинг не найден, используем старый экспорт: {e}")
        
        # Получаем путь к файлу
        file_path = self.data_provider._get_excel_file_path(workshop)
        
        # Выполняем экспорт
        try:
            result = self.exporter.export_to_sheet(
                file_path=file_path,
                mapping=mapping,
                mode="pallet" if enable_pallet else "box"
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
    
    def clear_all_rolls(self, enable_pallet=False, multitype_mode=False):
        """Очистка листа (обратная совместимость)"""
        try:
            self.on_settings_changed()
            workshop = getattr(self, 'workshop', '1')
            
            # Обновляем логику для multitype
            if multitype_mode:
                # Используем новую архитектуру для multitype тоже!
                sheet_type = "multitype"
                try:
                    mapping = CellMappingRegistry.get_mapping(workshop, sheet_type, "box")
                    file_path = self.data_provider._get_excel_file_path(workshop)
                    success = self.exporter.clear_sheet(file_path, mapping)
                    return success
                except ValueError as e:
                    print(f"Маппинг multitype не найден: {e}")
                    return False         
            
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
                file_path = self.data_provider._get_excel_file_path(workshop)
                
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
    
    def on_settings_changed(self):
        """Один метод для обновления всех настроек из координатора"""
        if not self.coordinator:
            self.has_weight = True
            return
        
        if hasattr(self.coordinator, 'get_workshop'):
            self.workshop = self.coordinator.get_workshop()
        
        if hasattr(self.coordinator, 'get_weight_status'):
            self.has_weight = self.coordinator.get_weight_status()
