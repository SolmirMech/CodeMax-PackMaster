# cell_mappers.py
"""
Модуль маппингов ячеек Excel.
Определяет КАКИЕ данные в КАКИЕ ячейки помещать.
Полностью декларативный, не содержит логики экспорта.
"""
# noinspection PyUnusedImports
# Эти импорты нужны в дальнейших модулях
from typing import Dict, List, Any, Optional, Tuple

# noinspection PyUnusedImports
# Эти импорты нужны в дальнейших модулях
from .cell_mappers_models import (
    DataType, HorizontalAlignment, VerticalAlignment,
    CellFormat, CellMapping, DynamicSection, SheetMapping
)
from .cell_mappers_data import (
    WORKSHOP1_BOX_STATIC,
    WORKSHOP1_BOX_DYNAMIC,
    WORKSHOP1_PALLET_STATIC,
    WORKSHOP1_PALLET_DYNAMIC,
    WORKSHOP1_NOWEIGHT_STATIC,
    WORKSHOP1_NOWEIGHT_DYNAMIC,
    WORKSHOP1_MULTITYPE_STATIC,
    WORKSHOP1_MULTITYPE_DYNAMIC,
    WORKSHOP2_BOX_STATIC,
    WORKSHOP2_BOX_DYNAMIC,
    WORKSHOP2_PALLET_LIST_STATIC,
    WORKSHOP2_PALLET_LIST_DYNAMIC,
    WORKSHOP2_MULTITYPE_STATIC,
    WORKSHOP2_MULTITYPE_DYNAMIC
)


# noinspection GrazieInspection,SpellCheckingInspection
class CellMappingRegistry:
    """
    Реестр всех маппингов по цехам и типам листов.
    Центральное место для определения структуры Excel файлов.
    """
    
    # ==================== МАППИНГИ ДЛЯ ЦЕХА 1 ====================
    
    @staticmethod
    def get_workshop1_box_mapping() -> SheetMapping:
        """
        Маппинг для 1 цеха, лист коробки ('Лист для коробки')
        """
        return SheetMapping(
            sheet_name="Лист для коробки",
            workshop="1",
            description="Этикетка для коробки (цех 1)",
            
            static_cells=WORKSHOP1_BOX_STATIC,
            dynamic_sections=WORKSHOP1_BOX_DYNAMIC,
            
            post_processing_hooks=[
                "update_manufacturer_info",  # Хук для обновления информации о производителе
                "validate_rolls_count"       # Хук для проверки количества роликов
            ]
        )
    
    @staticmethod
    def get_workshop1_pallet_mapping() -> SheetMapping:
        """
        Маппинг для 1 цеха, лист поддона ('Лист для паллеты')
        Структура аналогична коробке, но заполняются коробки вместо роликов
        """
        return SheetMapping(
            sheet_name="Лист для паллеты",
            workshop="1",
            description="Этикетка для поддона (цех 1)",
            
            static_cells=WORKSHOP1_PALLET_STATIC,
            dynamic_sections=WORKSHOP1_PALLET_DYNAMIC,
            
            post_processing_hooks=[
                "update_manufacturer_info",
                "validate_boxes_count"  # Хук для проверки количества коробок
            ]
        )    
    

    @staticmethod
    def get_workshop1_noweight_mapping() -> SheetMapping:
        """
        Маппинг для 1 цеха, лист без веса ('БезВеса')
        """
        return SheetMapping(
            sheet_name="БезВеса",
            workshop="1",
            description="Лист без веса для поддона (цех 1)",
            
            static_cells=WORKSHOP1_NOWEIGHT_STATIC,
            dynamic_sections=WORKSHOP1_NOWEIGHT_DYNAMIC,
            
            post_processing_hooks=[
                "update_manufacturer_info",
                "validate_boxes_count_noweight",
                "fill_box_numbers"
            ]
        )    
    
    @staticmethod
    def get_workshop1_multitype_mapping() -> SheetMapping:
        """
        Маппинг для 1 цеха, лист 'Много видов' ('Лист много видов')
        """
        return SheetMapping(
            sheet_name="Лист много видов",
            workshop="1",
            description="Лист много видов (цех 1)",
            
            static_cells=WORKSHOP1_MULTITYPE_STATIC,
            dynamic_sections=WORKSHOP1_MULTITYPE_DYNAMIC,
            
        )  

    # ==================== МАППИНГИ ДЛЯ ЦЕХА 2 ====================

    @staticmethod
    def get_workshop2_box_mapping() -> SheetMapping:
        """
        Маппинг для 2 цеха, лист 'Поддон' (коробка)
        """
        return SheetMapping(
            sheet_name="Поддон",
            workshop="2",
            description="Этикетка для коробки (цех 2)",
            
            static_cells=WORKSHOP2_BOX_STATIC,
            dynamic_sections=WORKSHOP2_BOX_DYNAMIC,
            
            post_processing_hooks=[
                "update_manufacturer_info",  # Производитель в A1
                "validate_rolls_count_workshop2"
            ]
        )
    
    @staticmethod
    def get_workshop2_pallet_list_mapping() -> SheetMapping:
        """
        Маппинг для 2 цеха, лист 'Список поддонов'
        """
        return SheetMapping(
            sheet_name="Список поддонов",
            workshop="2",
            description="Список поддонов (цех 2)",
            
            static_cells=WORKSHOP2_PALLET_LIST_STATIC,
            dynamic_sections=WORKSHOP2_PALLET_LIST_DYNAMIC,
            
            post_processing_hooks=[
                "update_manufacturer_info",
                "validate_pallet_list_capacity"
            ]
        )
        
    @staticmethod
    def get_workshop2_multitype_mapping() -> SheetMapping:
        """
        Маппинг для 2 цеха, лист 'Много видов'
        """
        return SheetMapping(
            sheet_name="Много видов",
            workshop="2",
            description="Лист много видов (цех 2)",
            
            static_cells=WORKSHOP2_MULTITYPE_STATIC,
            dynamic_sections=WORKSHOP2_MULTITYPE_DYNAMIC,
            
            post_processing_hooks=[
                "update_manufacturer_info"  # Производитель в A1
            ]
        )
    
    # ==================== МЕТОДЫ ДОСТУПА К МАППИНГАМ ====================
    
    @classmethod
    def get_mapping(cls, workshop: str, sheet_type: str, mode: str = "box") -> SheetMapping:
        """
        Получает маппинг по параметрам.
        
        Args:
            workshop: "1" или "2"
            sheet_type: "box", "pallet", "multitype", "noweight", "pallet_list"
            mode: Дополнительный режим (для совместимости)
            
        Returns:
            Соответствующий SheetMapping
            
        Raises:
            ValueError: Если маппинг не найден
        """
        # Словарь доступных маппингов
        mappings = {
            # Цех 1
            ("1", "box"): cls.get_workshop1_box_mapping,           
            ("1", "pallet"): cls.get_workshop1_pallet_mapping,
            ("1", "noweight"): cls.get_workshop1_noweight_mapping,
            ("1", "multitype"): cls.get_workshop1_multitype_mapping,            
            
            # Цех 2
            ("2", "box"): cls.get_workshop2_box_mapping,
            ("2", "pallet_list"): cls.get_workshop2_pallet_list_mapping,
            ("2", "multitype"): cls.get_workshop2_multitype_mapping,
        }
        
        key = (workshop, sheet_type)
        
        if key not in mappings:
            # Пробуем найти по workshop и mode (для обратной совместимости)
            alt_key = (workshop, mode)
            if alt_key in mappings:
                return mappings[alt_key]()
            
            # Если не нашли - пробуем найти по sheet_type (без workshop)
            for (w, s), mapper in mappings.items():
                if s == sheet_type:
                    return mapper()
            
            raise ValueError(f"Маппинг не найден для workshop={workshop}, sheet_type={sheet_type}, mode={mode}")
        
        return mappings[key]()
    
    @classmethod
    def get_available_mappings(cls) -> List[Dict[str, Any]]:
        """Возвращает список всех доступных маппингов"""
        return [
            # Цех 1
            {
                "workshop": "1",
                "sheet_type": "box",
                "sheet_name": "Лист для коробки",
                "description": "Этикетка для коробки (цех 1)"
            },
            {
                "workshop": "1",
                "sheet_type": "pallet",
                "sheet_name": "Лист для паллеты",
                "description": "Этикетка для поддона (цех 1)"
            },
            {
                "workshop": "1",
                "sheet_type": "noweight",
                "sheet_name": "БезВеса",
                "description": "Лист без веса для поддона (цех 1)"
            },
            {
                "workshop": "1",
                "sheet_type": "multitype",
                "sheet_name": "Лист много видов",
                "description": "Лист много видов (цех 1)"
            },
            
            # Цех 2
            {
                "workshop": "2",
                "sheet_type": "box",
                "sheet_name": "Поддон",
                "description": "Этикетка для коробки (цех 2)"
            },
            {
                "workshop": "2",
                "sheet_type": "pallet_list",
                "sheet_name": "Список поддонов",
                "description": "Список поддонов (цех 2)"
            },
            {
                "workshop": "2",
                "sheet_type": "multitype",
                "sheet_name": "Много видов",
                "description": "Лист много видов (цех 2)"
            }
        ]
    
    # ==================== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ====================
    
    @staticmethod
    def parse_cell_reference(cell_ref: str) -> Tuple[str, int]:
        """
        Разбирает ссылку на ячейку на букву колонки и номер строки.
        
        Args:
            cell_ref: Ссылка на ячейку (например, "A1", "BC23")
            
        Returns:
            Кортеж (буква_колонки, номер_строки)
        """
        import re
        match = re.match(r"([A-Z]+)(\d+)", cell_ref)
        if not match:
            raise ValueError(f"Некорректная ссылка на ячейку: {cell_ref}")
        return match.group(1), int(match.group(2))
    
    @staticmethod
    def get_column_letter(column_index: int) -> str:
        """
        Преобразует индекс колонки в букву Excel.
        
        Args:
            column_index: Индекс колонки (начинается с 1)
            
        Returns:
            Буква колонки Excel
        """
        result = ""
        while column_index > 0:
            column_index, remainder = divmod(column_index - 1, 26)
            result = chr(65 + remainder) + result
        return result
    
    @staticmethod
    def get_column_index(column_letter: str) -> int:
        """
        Преобразует букву колонки Excel в индекс.
        
        Args:
            column_letter: Буква колонки Excel
            
        Returns:
            Индекс колонки (начинается с 1)
        """
        result = 0
        for char in column_letter:
            result = result * 26 + (ord(char) - 64)
        return result

# ==================== ШОРТКАТЫ ДЛЯ БЫСТРОГО ДОСТУПА ====================

def get_mapping(workshop: str, sheet_type: str, mode: str = "box") -> SheetMapping:
    """Краткая функция для получения маппинга"""
    return CellMappingRegistry.get_mapping(workshop, sheet_type, mode)

# Цех 1
def get_workshop1_box_mapping() -> SheetMapping:
    """Краткая функция для получения маппинга коробки 1 цеха"""
    return CellMappingRegistry.get_workshop1_box_mapping()

def get_workshop1_pallet_mapping() -> SheetMapping:
    """Краткая функция для получения маппинга поддона 1 цеха"""
    return CellMappingRegistry.get_workshop1_pallet_mapping()


# noinspection SpellCheckingInspection
def get_workshop1_noweight_mapping() -> SheetMapping:
    """Краткая функция для получения маппинга без веса 1 цеха"""
    return CellMappingRegistry.get_workshop1_noweight_mapping()

def get_workshop1_multitype_mapping() -> SheetMapping:
    """Краткая функция для получения много-видового маппинга 1 цеха"""
    return CellMappingRegistry.get_workshop1_multitype_mapping()

# Цех 2
def get_workshop2_box_mapping() -> SheetMapping:
    """Краткая функция для получения маппинга коробки 2 цеха"""
    return CellMappingRegistry.get_workshop2_box_mapping()

def get_workshop2_pallet_list_mapping() -> SheetMapping:
    """Краткая функция для получения маппинга списка поддонов 2 цеха"""
    return CellMappingRegistry.get_workshop2_pallet_list_mapping()

def get_workshop2_multitype_mapping() -> SheetMapping:
    """Краткая функция для получения много-видового маппинга 2 цеха"""
    return CellMappingRegistry.get_workshop2_multitype_mapping()