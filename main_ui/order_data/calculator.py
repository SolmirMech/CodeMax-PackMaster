# main_ui/order_data/calculator.py
"""Модуль расчётов весов, количества и длины для заказа"""

import math


class OrderCalculator:
    """Калькулятор для расчётов, связанных с заказом (не зависит от tkinter)"""
    
    @staticmethod
    def parse_float(value) -> float:
        """Преобразует строку в число с плавающей точкой."""
        if not value:
            return 0.0
        
        if isinstance(value, (int, float)):
            return float(value)
        
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return 0.0
            
            if ',' in value:
                value = value.replace(',', '.', 1)
            
            try:
                return float(value)
            except ValueError:
                return 0.0
        
        return 0.0
    
    @staticmethod
    def parse_int(value) -> int:
        """Преобразует строку в целое число."""
        if not value:
            return 0
        
        if isinstance(value, int):
            return value
        
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return 0
            
            try:
                return int(float(value))
            except ValueError:
                return 0
        
        return 0
    
    @staticmethod
    def calculate_weights(
        gross_kg_str: str,
        sleeve_g_str: str,
        rolls_count_str: str,
        box_weight_kg_str: str
    ) -> dict:
        """Рассчитывает веса на основе входных данных."""
        result = {
            'net_kg': '',
            'total_gross': '',
            'total_net': ''
        }
        
        gross_kg = OrderCalculator.parse_float(gross_kg_str)
        if gross_kg <= 0:
            return result
        
        sleeve_g = OrderCalculator.parse_float(sleeve_g_str)
        sleeve_kg = sleeve_g / 1000
        
        net_kg = max(gross_kg - sleeve_kg, 0)
        if net_kg > 0:
            result['net_kg'] = f"{net_kg:.2f}"
        
        rolls_count = OrderCalculator.parse_int(rolls_count_str)
        if rolls_count > 0:
            box_weight_kg = OrderCalculator.parse_float(box_weight_kg_str)
            
            total_gross = (rolls_count * gross_kg) + box_weight_kg
            total_net = rolls_count * net_kg
            
            result['total_gross'] = f"{total_gross:.2f}"
            result['total_net'] = f"{total_net:.2f}"
        
        return result
    
    @staticmethod
    def calculate_total_quantity(rolls_count_str: str, quantity_per_roll_str: str) -> str:
        """Рассчитывает общее количество: ролики × этикеток в ролике."""
        rolls = OrderCalculator.parse_int(rolls_count_str)
        per_roll = OrderCalculator.parse_int(quantity_per_roll_str)
        
        if rolls == 0 or per_roll == 0:
            return ""
        
        return str(rolls * per_roll)

    @staticmethod
    def calculate_quantity_from_length(
            roll_length_m_str: str,
            label_length_mm_str: str,
            rounding_up: bool = True
    ) -> str:
        """
        Рассчитывает количество этикеток из длины ролика и длины этикетки.

        Args:
            roll_length_m_str: длина ролика в метрах
            label_length_mm_str: длина этикетки в мм
            rounding_up: True - округление вверх (math.ceil), False - вниз (math.floor)
        """
        roll_m = OrderCalculator.parse_float(roll_length_m_str)
        label_mm = OrderCalculator.parse_float(label_length_mm_str)

        if roll_m <= 0 or label_mm <= 0:
            return ""

        label_m = label_mm / 1000
        if rounding_up:
            quantity = math.ceil(roll_m / label_m)
        else:
            quantity = math.floor(roll_m / label_m)

        return str(quantity)