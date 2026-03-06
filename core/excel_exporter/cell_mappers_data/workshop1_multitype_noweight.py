# cell_mappers_data/workshop1_multitype_noweight.py
"""Данные для маппинга Много видов БезВеса 1 цеха"""

from core.excel_exporter.cell_mappers_data.cell_mappers_models import (
    CellMapping, DynamicSection, CellFormat,
    DataType, HorizontalAlignment, VerticalAlignment
)

# ========== СТАТИЧЕСКИЕ ЯЧЕЙКИ ==========
STATIC_CELLS = [
    # Основная информация (как в поддоне, но без product_text)
    CellMapping(
        cell_reference="D5",
        data_key="customer",
        data_type=DataType.TEXT,
        format=CellFormat(
            horizontal_alignment=HorizontalAlignment.LEFT,
            vertical_alignment=VerticalAlignment.CENTER
        ),
        required=True
    ),
    
    CellMapping(
        cell_reference="B1",  # Ячейка для производителя
        data_key="manufacturer_display_text",
        data_type=DataType.MULTILINE_TEXT,
        format=CellFormat(
            horizontal_alignment=HorizontalAlignment.CENTER,
            vertical_alignment=VerticalAlignment.CENTER,
            wrap_text=True
        ),
        required=False,
        is_merged_cell=True  # объединенная ячейка
    ),
    
    CellMapping(
        cell_reference="D6",
        data_key="pallet_type",
        data_type=DataType.TEXT,
        format=CellFormat(
            horizontal_alignment=HorizontalAlignment.LEFT,
            vertical_alignment=VerticalAlignment.CENTER
        ),
        required=True
    ),
    
    CellMapping(
        cell_reference="M1",
        data_key="order_number",
        data_type=DataType.TEXT,
        format=CellFormat(
            horizontal_alignment=HorizontalAlignment.LEFT,
            vertical_alignment=VerticalAlignment.CENTER
        ),
        required=True
    ),
    
    CellMapping(
        cell_reference="F33",
        data_key="date",
        data_type=DataType.DATE,
        format=CellFormat(
            horizontal_alignment=HorizontalAlignment.LEFT,
            vertical_alignment=VerticalAlignment.CENTER
        ),
        required=True
    ),
    
    CellMapping(
        cell_reference="E36",
        data_key="packer",
        data_type=DataType.TEXT,
        format=CellFormat(
            horizontal_alignment=HorizontalAlignment.LEFT,
            vertical_alignment=VerticalAlignment.CENTER
        ),
        required=True
    ),
    
    CellMapping(
        cell_reference="E35",
        data_key="product_type",
        data_type=DataType.TEXT,
        format=CellFormat(
            horizontal_alignment=HorizontalAlignment.LEFT,
            vertical_alignment=VerticalAlignment.CENTER
        ),
        required=True
    ),
    
    CellMapping(
        cell_reference="A35",
        data_key="tu_number",
        data_type=DataType.TEXT,
        format=CellFormat(
            horizontal_alignment=HorizontalAlignment.LEFT,
            vertical_alignment=VerticalAlignment.CENTER
        ),
        required=False
    ),
    
]

# ========== ДИНАМИЧЕСКИЕ СЕКЦИИ ==========
DYNAMIC_SECTIONS = [
    # Динамическая секция для строк (11-28)
    DynamicSection(
        name="multitype_rows",
        start_cell="A11",  # Начинаем с A11
        rows_range=(11, 29),  # Строки 11-28
        columns_config=[
            {
                "column": "A",
                "data_key": "boxes_count",
                "data_type": DataType.INTEGER,
                "format": CellFormat(
                    horizontal_alignment=HorizontalAlignment.CENTER,
                    vertical_alignment=VerticalAlignment.CENTER
                )
            },
            {
                "column": "B",
                "data_key": "order_number",  # новый номер заказа
                "data_type": DataType.TEXT,
                "format": CellFormat(
                    horizontal_alignment=HorizontalAlignment.LEFT,
                    vertical_alignment=VerticalAlignment.CENTER
                )
            },
            {
                "column": "C",
                "data_key": "product_text",  # Это product_name
                "data_type": DataType.MULTILINE_TEXT,
                "format": CellFormat(
                    horizontal_alignment=HorizontalAlignment.LEFT,
                    vertical_alignment=VerticalAlignment.CENTER,
                    wrap_text=True
                )
            },
            {
                "column": "G",
                "data_key": "labels_total",
                "data_type": DataType.INTEGER,
                "format": CellFormat(
                    horizontal_alignment=HorizontalAlignment.CENTER,
                    vertical_alignment=VerticalAlignment.CENTER
                )
            }
        ],
        direction="vertical",  # Заполняем по строкам
        max_items=18  # Максимум 18 строк (11-28)
    )
]