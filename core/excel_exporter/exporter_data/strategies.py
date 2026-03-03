# strategies.py
"""
Стратегии обработки динамических секций для разных типов листов.
"""
from typing import Dict

from core.excel_exporter.cell_mappers import SheetMapping


class SheetStrategy:
    """Базовый класс для стратегии обработки листа"""
    def should_apply(self, mapping: SheetMapping, data: Dict) -> bool:
        return False
    
    def process(self, exporter, mapping: SheetMapping, data: Dict) -> bool:
        """Возвращает True, если всё заполнилось"""
        return True


class MultiTypeWorkshop1Strategy(SheetStrategy):
    """Стратегия для "Лист много видов" (цех 1, с весом)"""

    def should_apply(self, mapping: SheetMapping, data: Dict) -> bool:
        return mapping.sheet_name == "Лист много видов" and mapping.workshop == "1"

    def process(self, exporter, mapping, data):
        return exporter.filler.fill_multitype_sections_with_distribution(
            mapping.dynamic_sections, data, max_items=1
        )

class NoWeightStrategy(SheetStrategy):
    """Стратегия для листа БезВеса"""
    def should_apply(self, mapping: SheetMapping, data: Dict) -> bool:
        return mapping.sheet_name == "БезВеса"
    
    def process(self, exporter, mapping, data):
        boxes_count = data.get('boxes_count', 1) or 1
        return exporter.filler.fill_quantity_sections_with_distribution(
            mapping.dynamic_sections, data, boxes_count
        )


class MultiTypeWorkshop2Strategy(SheetStrategy):
    """Стратегия для Много видов (цех 2)"""
    def should_apply(self, mapping: SheetMapping, data: Dict) -> bool:
        return mapping.sheet_name == "Много видов" and mapping.workshop == "2"
    
    def process(self, exporter, mapping, data):
        return exporter.filler.fill_multitype_sections_workshop2(
            mapping.dynamic_sections, data, max_items=1
        )


class MultiTypeNoWeightStrategy(SheetStrategy):
    """Стратегия для Много видов БезВеса"""
    def should_apply(self, mapping: SheetMapping, data: Dict) -> bool:
        return mapping.sheet_name == "Много видов БезВеса"
    
    def process(self, exporter, mapping, data):
        return exporter.filler.fill_multitype_noweight_sections(
            mapping.dynamic_sections, data, max_items=1
        )


class PalletListStrategy(SheetStrategy):
    """Стратегия для Списка поддонов"""
    def should_apply(self, mapping: SheetMapping, data: Dict) -> bool:
        return mapping.sheet_name == "Список поддонов"
    
    def process(self, exporter, mapping, data):
        return exporter.filler.fill_pallet_list_sections(
            mapping.dynamic_sections, data
        )


class DefaultStrategy(SheetStrategy):
    """Стандартная стратегия: коробки и ролики"""
    def process(self, exporter, mapping, data):
        all_fitted = True
        boxes_sections = [s for s in mapping.dynamic_sections if "boxes" in s.name]
        rolls_sections = [s for s in mapping.dynamic_sections if "rolls" in s.name]
        
        if boxes_sections:
            boxes_count = data.get('boxes_count', 1) or 1
            all_fitted = exporter.filler.fill_boxes_sections_with_distribution(
                boxes_sections, data, boxes_count
            ) and all_fitted
        
        if rolls_sections:
            rolls_count = data.get('rolls_count', 1) or 1
            if mapping.workshop == "2":
                all_fitted = exporter.filler.fill_rolls_sections_with_distribution_workshop2(
                    rolls_sections, data, rolls_count
                ) and all_fitted
            else:
                all_fitted = exporter.filler.fill_rolls_sections_with_distribution(
                    rolls_sections, data, rolls_count
                ) and all_fitted
        
        return all_fitted


# Фабрика для получения стратегии
def get_strategy_for_sheet(mapping: SheetMapping, data: Dict) -> SheetStrategy:
    """Возвращает подходящую стратегию для листа"""
    strategies = [
        NoWeightStrategy(),
        MultiTypeWorkshop2Strategy(),
        MultiTypeWorkshop1Strategy(),
        MultiTypeNoWeightStrategy(),
        PalletListStrategy(),
    ]
    
    for strategy in strategies:
        if strategy.should_apply(mapping, data):
            return strategy
    
    return DefaultStrategy()