# core/excel_exporter/data_provider.py
"""
Модуль обратной совместимости.
Экспортирует класс ExportDataProvider с тем же интерфейсом.
Внутри использует разделённую структуру.
"""

from typing import Dict, Any, Optional
from core.config_manager import ConfigManager
from .data_providers.workshop1_provider import Workshop1DataProvider
from .data_providers.workshop2_provider import Workshop2DataProvider

class ExportDataProvider:
    """
    Полностью совместимый класс с оригинальным интерфейсом.
    Внутри делегирует вызовы соответствующим провайдерам.
    """
    
    def __init__(self, roll_module, config_manager: Optional[ConfigManager] = None, excel_file_path: str = ""):
        self.roll_module = roll_module
        self.config_manager = config_manager or ConfigManager()
        self.original_excel_path = excel_file_path
        
        # Создаём оба провайдера
        self._provider1 = Workshop1DataProvider(roll_module, config_manager, excel_file_path)
        self._provider2 = Workshop2DataProvider(roll_module, config_manager, excel_file_path)
    
    # Проброс методов цеха 1

    def get_data_for_workshop1_box_noweight(self) -> Dict[str, Any]:
        return self._provider1.get_data_for_workshop1_box_noweight()

    def get_data_for_workshop1_box(self) -> Dict[str, Any]:
        return self._provider1.get_data_for_workshop1_box()
    
    def get_data_for_workshop1_pallet(self) -> Dict[str, Any]:
        return self._provider1.get_data_for_workshop1_pallet()
    
    def get_data_for_workshop1_noweight(self) -> Dict[str, Any]:
        return self._provider1.get_data_for_workshop1_noweight()
    
    def get_data_for_workshop1_multitype(self) -> Dict[str, Any]:
        return self._provider1.get_data_for_workshop1_multitype()
    
    def get_data_for_workshop1_multitype_noweight(self) -> Dict[str, Any]:
        return self._provider1.get_data_for_workshop1_multitype_noweight()
    
    # Проброс методов цеха 2
    def get_data_for_workshop2_box(self) -> Dict[str, Any]:
        return self._provider2.get_data_for_workshop2_box()
    
    def get_data_for_workshop2_pallet_list(self) -> Dict[str, Any]:
        return self._provider2.get_data_for_workshop2_pallet_list()
    
    def get_data_for_workshop2_multitype(self) -> Dict[str, Any]:
        return self._provider2.get_data_for_workshop2_multitype()
    
    # Общие методы (можно брать из любого провайдера, они одинаковые)
    def collect_all_data(self) -> Dict[str, Any]:
        return self._provider1.collect_all_data()
    
    def clear_cache(self):
        self._provider1.clear_cache()
        self._provider2.clear_cache()
    
    def get_excel_file_path(self, workshop: str) -> str:
        if workshop == "1":
            return self._provider1.get_excel_file_path(workshop)
        else:
            return self._provider2.get_excel_file_path(workshop)