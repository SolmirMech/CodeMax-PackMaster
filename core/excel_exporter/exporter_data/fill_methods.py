# fill_methods.py
"""
Методы заполнения динамических секций.
"""
from typing import Dict, List, Any
from core.excel_exporter.cell_mappers import DynamicSection, CellFormat, HorizontalAlignment, VerticalAlignment


class FillMethods:
    """Контейнер для методов заполнения"""
    
    def __init__(self, exporter):
        self.exporter = exporter  # для доступа к wb, ws и вспомогательным методам
    
    # ==================== УНИВЕРСАЛЬНЫЙ МЕТОД ====================
    
    def fill_section(self, section: DynamicSection, data: Dict[str, Any], 
                     max_items: int, data_mapper: Dict[str, str]) -> int:
        """Универсальный метод заполнения секции"""
        try:
            ws = self.exporter.ws
            start_row, end_row = section.rows_range
            filled_count = 0
            
            for row in range(start_row, end_row):
                if filled_count >= max_items:
                    break
                
                # Проверка пустоты строки
                is_empty = all(
                    ws[f"{col['column']}{row}"].value is None 
                    for col in section.columns_config
                )
                
                if is_empty:
                    for col_config in section.columns_config:
                        data_key = data_mapper.get(col_config['data_key'])
                        value = data.get(data_key) if data_key else None
                        
                        if value is not None:
                            processed = self.exporter.process_value_by_type(
                                value, col_config['data_type']
                            )
                            self.exporter.set_cell_value(
                                f"{col_config['column']}{row}", 
                                processed, 
                                col_config['format']
                            )
                    
                    filled_count += 1
            
            return filled_count
        except Exception as e:
            print(f"Ошибка заполнения секции {section.name}: {e}")
            return 0

    def fill_box_noweight_section(self, sections: List[DynamicSection], data: Dict[str, Any]) -> bool:
        """
        Заполняет секцию для листа "ПоддонРолики":
        - Находит первую пустую строку в секции
        - Заполняет B{row} значением rolls_count
        - Заполняет C{row} значением quantity_per_roll
        """
        if not sections:
            return False

        section = sections[0]  # только одна секция
        ws = self.exporter.ws
        start_row, end_row = section.rows_range

        rolls_count = data.get('rolls_count')
        quantity = data.get('quantity_per_roll')

        if rolls_count is None or quantity is None:
            return False

        # Ищем первую пустую строку
        for row in range(start_row, end_row):
            # Проверяем, пусты ли обе ячейки
            cell_b = ws[f"B{row}"].value
            cell_c = ws[f"C{row}"].value

            if cell_b is None and cell_c is None:
                # Заполняем
                for col_config in section.columns_config:
                    data_key = col_config['data_key']
                    value = data.get(data_key)

                    if value is not None:
                        processed = self.exporter.process_value_by_type(
                            value, col_config['data_type']
                        )
                        self.exporter.set_cell_value(
                            f"{col_config['column']}{row}",
                            processed,
                            col_config['format']
                        )
                return True

        # Нет свободных строк
        return False
    
    # ==================== МЕТОДЫ ДЛЯ РОЛИКОВ ====================
    
    def fill_rolls_sections_with_distribution(self, sections: List[DynamicSection], 
                                             data: Dict[str, Any], total_rolls: int) -> bool:
        """Распределяет ролики по секциям последовательно"""
        filled_count = 0
        
        for section in sections:
            if filled_count >= total_rolls:
                break
            
            rolls_left = total_rolls - filled_count
            filled_in_section = self.fill_single_rolls_section(section, data, rolls_left)
            filled_count += filled_in_section
        
        return filled_count >= total_rolls
    
    def fill_single_rolls_section(self, section: DynamicSection, data: Dict[str, Any], max_rolls: int) -> int:
        """Заполняет одну секцию роликов"""
        data_mapper = {
            'gross_weight_per_roll': 'gross_weight_per_roll',
            'net_weight_per_roll': 'net_weight_per_roll',
            'quantity_per_roll': 'quantity_per_roll'
        }
        return self.fill_section(section, data, max_rolls, data_mapper)
    
    # Для 2 цеха
    def fill_single_rolls_section_workshop2(self, section: DynamicSection, data: Dict[str, Any], max_rolls: int) -> int:
        """Заполняет одну секцию роликов для 2 цеха (с L колонкой)"""
        # Специфичная логика с L колонкой остаётся здесь
        try:
            ws = self.exporter.ws
            net_weight = data.get('net_weight_per_roll')
            quantity = data.get('quantity_per_roll')
            roll_length = data.get('roll_length')
            
            start_row, end_row = section.rows_range
            filled_count = 0
            
            l_offset = 0
            if section.name == "rolls_column_2":
                l_offset = 20
            elif section.name == "rolls_column_3":
                l_offset = 40
            
            for row in range(start_row, end_row):
                if filled_count >= max_rolls:
                    break
                
                is_empty = all(
                    ws[f"{col['column']}{row}"].value is None 
                    for col in section.columns_config
                )
                
                if is_empty:
                    for col_config in section.columns_config:
                        cell_ref = f"{col_config['column']}{row}"
                        data_key = col_config['data_key']
                        
                        if data_key == 'net_weight_per_roll':
                            value = net_weight
                        elif data_key == 'quantity_per_roll':
                            value = quantity
                        else:
                            value = None
                        
                        if value is not None:
                            processed = self.exporter.process_value_by_type(value, col_config['data_type'])
                            self.exporter.set_cell_value(cell_ref, processed, col_config['format'])
                    
                    if roll_length is not None:
                        l_row = row + l_offset
                        l_format = CellFormat(
                            horizontal_alignment=HorizontalAlignment.CENTER,
                            vertical_alignment=VerticalAlignment.CENTER,
                            number_format="0.0"
                        )
                        self.exporter.set_cell_value(f"L{l_row}", roll_length, l_format)
                    
                    filled_count += 1
            
            return filled_count
        except Exception as e:
            print(f"Ошибка заполнения секции роликов 2 цеха '{section.name}': {e}")
            return 0
    
    def fill_rolls_sections_with_distribution_workshop2(self, sections: List[DynamicSection], 
                                                       data: Dict[str, Any], total_rolls: int) -> bool:
        """Распределяет ролики по секциям для 2 цеха"""
        filled_count = 0
        
        for section in sections:
            if filled_count >= total_rolls:
                break
            
            rolls_left = total_rolls - filled_count
            filled_in_section = self.fill_single_rolls_section_workshop2(section, data, rolls_left)
            filled_count += filled_in_section
        
        return filled_count >= total_rolls
    
    # ==================== МЕТОДЫ ДЛЯ КОРОБОК ====================
    
    def fill_boxes_sections_with_distribution(self, sections: List[DynamicSection], 
                                             data: Dict[str, Any], total_boxes: int) -> bool:
        """Распределяет коробки по секциям"""
        filled_count = 0
        
        for section in sections:
            if filled_count >= total_boxes:
                break
            
            boxes_left = total_boxes - filled_count
            filled_in_section = self.fill_boxes_section(section, data, boxes_left)
            filled_count += filled_in_section
        
        return filled_count >= total_boxes
    
    def fill_boxes_section(self, section: DynamicSection, data: Dict[str, Any], max_boxes: int) -> int:
        """Заполняет одну секцию коробок"""
        data_mapper = {
            'gross_weight_per_box': 'gross_weight_per_box',
            'net_weight_per_box': 'net_weight_per_box',
            'quantity_per_box': 'quantity_per_box'
        }
        return self.fill_section(section, data, max_boxes, data_mapper)
    
    # ==================== МЕТОДЫ ДЛЯ MULTITYPE ====================
    
    def fill_multitype_sections_with_distribution(self, sections: List[DynamicSection], 
                                                 data: Dict[str, Any], max_items: int = 1) -> bool:
        """Распределяет строки по секциям для multitype"""
        filled_count = 0
        
        for section in sections:
            if filled_count >= max_items:
                break
            
            items_left = max_items - filled_count
            filled_in_section = self.fill_single_multitype_section(section, data, items_left)
            filled_count += filled_in_section
        
        return filled_count >= max_items
    
    def fill_single_multitype_section(self, section: DynamicSection, data: Dict[str, Any], max_items: int) -> int:
        """Заполняет одну секцию для multitype"""
        data_mapper = {
            'boxes_count': 'boxes_count',
            'product_text': 'product_text',
            'gross_total': 'gross_total',
            'net_total': 'net_total',
            'labels_total': 'labels_total'
        }
        return self.fill_section(section, data, max_items, data_mapper)
    
    def fill_multitype_sections_workshop2(self, sections: List[DynamicSection], 
                                         data: Dict[str, Any], max_items: int = 1) -> bool:
        """Распределяет строки по секциям для multitype (цех 2)"""
        filled_count = 0
        
        for section in sections:
            if filled_count >= max_items:
                break
            
            items_left = max_items - filled_count
            filled_in_section = self.fill_single_multitype_section_workshop2(section, data, items_left)
            filled_count += filled_in_section
        
        return filled_count >= max_items
    
    def fill_single_multitype_section_workshop2(self, section: DynamicSection, data: Dict[str, Any], max_items: int) -> int:
        """Заполняет одну секцию для multitype (цех 2) - логика с очисткой дублирующихся строк"""
        # Специфичная логика цеха 2 остаётся здесь
        try:
            ws = self.exporter.ws
            pallets_count = data.get('pallets_count', 0)
            product_name = data.get('product_name', '')
            total_weight = data.get('total_weight', 0)
            total_quantity = data.get('total_quantity', 0)
            total_length = data.get('total_length', 0)
            
            if not product_name:
                return 0
            
            start_row, end_row = section.rows_range
            filled_count = 0
            
            # Поиск и очистка дубликата
            for row in range(start_row, end_row):
                if ws[f'B{row}'].value == product_name:
                    for col in ['A', 'B', 'H', 'I', 'L']:
                        self.exporter.set_cell_value(f"{col}{row}", None, CellFormat())
                    break
            
            # Заполнение пустой строки
            for row in range(start_row, end_row):
                if filled_count >= max_items:
                    break
                
                is_empty = all(
                    ws[f"{col}{row}"].value is None 
                    for col in ['A', 'B', 'H', 'I', 'L']
                )
                
                if is_empty:
                    for col_config in section.columns_config:
                        cell_ref = f"{col_config['column']}{row}"
                        data_key = col_config['data_key']
                        
                        if data_key == 'pallets_count':
                            value = pallets_count
                        elif data_key == 'product_text':
                            value = product_name
                        elif data_key == 'total_weight':
                            value = total_weight
                        elif data_key == 'total_quantity':
                            value = total_quantity
                        elif data_key == 'total_length':
                            value = total_length
                        else:
                            value = None
                        
                        if value is not None:
                            processed = self.exporter.process_value_by_type(value, col_config['data_type'])
                            self.exporter.set_cell_value(cell_ref, processed, col_config['format'])
                    
                    filled_count += 1
            
            return filled_count
        except Exception as e:
            print(f"Ошибка заполнения секции multitype цех 2 '{section.name}': {e}")
            return 0
    
    # ==================== МЕТОДЫ ДЛЯ БезВеса ====================
    
    def fill_quantity_sections_with_distribution(self, sections: List[DynamicSection], 
                                               data: Dict[str, Any], total_boxes: int) -> bool:
        """Распределяет количество по секциям для листа БезВеса"""
        filled_count = 0
        
        for section in sections:
            if filled_count >= total_boxes:
                break
            
            boxes_left = total_boxes - filled_count
            filled_in_section = self.fill_quantity_section(section, data, boxes_left)
            filled_count += filled_in_section
        
        return filled_count >= total_boxes
    
    def fill_quantity_section(self, section: DynamicSection, data: Dict[str, Any], max_boxes: int) -> int:
        """Заполняет одну секцию количества для листа БезВеса"""
        data_mapper = {
            'quantity_per_box': 'quantity_per_box'
        }
        return self.fill_section(section, data, max_boxes, data_mapper)
    
    def fill_multitype_noweight_sections(self, sections: List[DynamicSection],
                                        data: Dict[str, Any], max_items: int = 1) -> bool:
        """Распределяет строки по секциям для multitype без веса"""
        filled_count = 0
        
        for section in sections:
            if filled_count >= max_items:
                break
            
            items_left = max_items - filled_count
            filled_in_section = self.fill_single_multitype_noweight_section(section, data, items_left)
            filled_count += filled_in_section
        
        return filled_count >= max_items
    
    def fill_single_multitype_noweight_section(self, section: DynamicSection,
                                              data: Dict[str, Any], max_items: int) -> int:
        """Заполняет одну секцию для multitype без веса"""
        data_mapper = {
            'boxes_count': 'boxes_count',
            'order_number': 'order_number',
            'product_text': 'product_text',
            'labels_total': 'labels_total'
        }
        return self.fill_section(section, data, max_items, data_mapper)
    
    # ==================== МЕТОДЫ ДЛЯ СПИСКА ПОДДОНОВ ====================
    
    def fill_pallet_list_sections(self, sections: List[DynamicSection], data: Dict[str, Any]) -> bool:
        """Заполняет динамические секции для листа 'Список поддонов'."""
        if not sections:
            return True
        
        rolls_count = data.get('rolls_count', 0)
        total_weight = data.get('total_weight', 0)
        total_quantity = data.get('total_quantity', 0)
        total_length = data.get('total_length', 0)
        
        if rolls_count == 0 and total_weight == 0 and total_quantity == 0 and total_length == 0:
            return False
        
        section = sections[0]
        ws = self.exporter.ws
        start_row, end_row = section.rows_range
        
        # Поиск свободной строки
        target_row = None
        for row in range(start_row, end_row):
            is_empty = all(ws[f'{col}{row}'].value is None for col in ['D', 'F', 'H', 'L'])
            if is_empty:
                target_row = row
                break
        
        if target_row is None:
            return False
        
        # Заполнение
        try:
            for col_config in section.columns_config:
                cell_ref = f"{col_config['column']}{target_row}"
                data_key = col_config['data_key']
                
                if data_key == 'rolls_count':
                    value = rolls_count
                elif data_key == 'total_weight':
                    value = total_weight
                elif data_key == 'total_quantity':
                    value = total_quantity
                elif data_key == 'total_length':
                    value = total_length
                else:
                    value = None
                
                if value is not None:
                    processed = self.exporter.process_value_by_type(value, col_config['data_type'])
                    self.exporter.set_cell_value(cell_ref, processed, col_config['format'])
            
            return True
        except Exception as e:
            print(f"Ошибка заполнения строки {target_row}: {e}")
            return False