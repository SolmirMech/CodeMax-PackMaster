# core/excel_exporter/cell_mappers_data/ecosystem.py
"""Данные для маппинга упаковочного листа Экосистема"""

# noinspection PyUnusedImports
from core.excel_exporter.cell_mappers_data.cell_mappers_models import (
    CellMapping, DynamicSection, CellFormat,
    DataType, HorizontalAlignment, VerticalAlignment
)

# Статические ячейки шапки
STATIC_CELLS = [
    CellMapping("E2", "list_number", DataType.TEXT),
    CellMapping("C4", "supplier", DataType.TEXT),
    CellMapping("C5", "customer", DataType.TEXT),
    CellMapping("C6", "consignee", DataType.TEXT),
    CellMapping("C7", "order_number", DataType.TEXT),      # contract → order_number
    CellMapping("C8", "project", DataType.TEXT),
    CellMapping("C9", "product_text", DataType.MULTILINE_TEXT),  # equipment_name → product_text
]

# Динамические секции
DYNAMIC_SECTIONS = [
    # Секция 1: Грузовые места (строки 13-17, колонки A-G)
    DynamicSection(
        name="places",
        start_cell="A13",
        rows_range=(13, 17),
        columns_config=[
            {"column": "A", "data_key": "place_number", "data_type": DataType.TEXT},
            {"column": "B", "data_key": "net_weight", "data_type": DataType.NUMBER},
            {"column": "C", "data_key": "gross_weight", "data_type": DataType.NUMBER},
            {"column": "D", "data_key": "length", "data_type": DataType.NUMBER},
            {"column": "E", "data_key": "width", "data_type": DataType.NUMBER},
            {"column": "F", "data_key": "height", "data_type": DataType.NUMBER},
            {"column": "G", "data_key": "storage_type", "data_type": DataType.TEXT},
        ],
        direction="vertical",
        max_items=5
    ),
    # Секция 2: Товары (строки 24-28, колонки A-H)
    DynamicSection(
        name="items",
        start_cell="A24",
        rows_range=(24, 28),
        columns_config=[
            {"column": "A", "data_key": "item_number", "data_type": DataType.TEXT},
            {"column": "B", "data_key": "order_request", "data_type": DataType.TEXT},
            {"column": "C", "data_key": "article_vn", "data_type": DataType.TEXT},
            {"column": "D", "data_key": "name", "data_type": DataType.TEXT},
            {"column": "E", "data_key": "unit", "data_type": DataType.TEXT},
            {"column": "F", "data_key": "quantity", "data_type": DataType.INTEGER},
            {"column": "G", "data_key": "article_vn_product", "data_type": DataType.TEXT},
            {"column": "H", "data_key": "product", "data_type": DataType.TEXT},
        ],
        direction="vertical",
        max_items=5
    )
]