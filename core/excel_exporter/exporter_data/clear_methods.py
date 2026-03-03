# clear_methods.py
"""
Методы очистки листов и секций.
"""
from typing import List
from core.excel_exporter.cell_mappers import SheetMapping, DynamicSection, CellMapping, CellFormat


class ClearMethods:
    """Контейнер для методов очистки"""
    
    def __init__(self, exporter):
        self.exporter = exporter  # для доступа к wb, ws
    
    def clear_sheet(self, mapping: SheetMapping):
        """Очищает лист согласно маппингу"""
        # 1. Статические ячейки
        self.clear_static_cells(mapping.static_cells)
        
        # 2. Динамические секции
        if mapping.sheet_name == "БезВеса":
            for section in mapping.dynamic_sections:
                self.clear_noweight_section_with_numbers(section)
        else:
            for section in mapping.dynamic_sections:
                self.clear_dynamic_section(section)
    
    def clear_static_cells(self, cell_mappings: List[CellMapping]):
        """Очищает статические ячейки"""
        for cell_mapping in cell_mappings:
            try:
                self.exporter.set_cell_value(
                    cell_mapping.cell_reference,
                    None,
                    CellFormat()
                )
            except Exception as e:
                print(f"Ошибка очистки ячейки {cell_mapping.cell_reference}: {e}")
    
    def clear_dynamic_section(self, section: DynamicSection):
        """Очищает динамическую секцию"""
        start_row, end_row = section.rows_range
        
        for row in range(start_row, end_row):
            for col_config in section.columns_config:
                try:
                    cell_ref = f"{col_config['column']}{row}"
                    self.exporter.set_cell_value(cell_ref, None, CellFormat())
                except Exception as e:
                    print(f"Ошибка очистки ячейки: {e}")
    
    def clear_noweight_section_with_numbers(self, section: DynamicSection):
        """Очищает секцию в БезВеса вместе с номерами"""
        start_row, end_row = section.rows_range
        
        for row in range(start_row, end_row):
            for col_config in section.columns_config:
                try:
                    quantity_col = col_config['column']
                    quantity_cell = f"{quantity_col}{row}"
                    self.exporter.set_cell_value(quantity_cell, None, CellFormat())
                    
                    number_col = chr(ord(quantity_col) - 1)
                    number_cell = f"{number_col}{row}"
                    self.exporter.set_cell_value(number_cell, None, CellFormat())
                except Exception as e:
                    print(f"Ошибка очистки ячейки в БезВеса {row}: {e}")