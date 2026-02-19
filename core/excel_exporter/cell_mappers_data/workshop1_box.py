# cell_mappers_data/workshop1_box.py
"""Данные для маппинга коробки 1 цеха"""

from ..cell_mappers_models import (  # ← импорт из нового файла
    CellMapping, DynamicSection, CellFormat,
    DataType, HorizontalAlignment, VerticalAlignment
)

# ========== СТАТИЧЕСКИЕ ЯЧЕЙКИ ==========
STATIC_CELLS = [
    # Основная информация
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
        cell_reference="D6",
        data_key="box_type",
        data_type=DataType.TEXT,
        format=CellFormat(
            horizontal_alignment=HorizontalAlignment.LEFT,
            vertical_alignment=VerticalAlignment.CENTER
        ),
        required=True
    ),
    
    CellMapping(
        cell_reference="D8",
        data_key="order_number",
        data_type=DataType.TEXT,
        format=CellFormat(
            horizontal_alignment=HorizontalAlignment.LEFT,
            vertical_alignment=VerticalAlignment.CENTER
        ),
        required=True
    ),
    
    CellMapping(
        cell_reference="D10",
        data_key="product_text",
        data_type=DataType.MULTILINE_TEXT,
        format=CellFormat(
            horizontal_alignment=HorizontalAlignment.LEFT,
            vertical_alignment=VerticalAlignment.TOP,
            wrap_text=True
        ),
        required=True
    ),
    
    CellMapping(
        cell_reference="F37",
        data_key="date",
        data_type=DataType.DATE,
        format=CellFormat(
            horizontal_alignment=HorizontalAlignment.LEFT,
            vertical_alignment=VerticalAlignment.CENTER
        ),
        required=True
    ),
    
    CellMapping(
        cell_reference="E41",
        data_key="packer",
        data_type=DataType.TEXT,
        format=CellFormat(
            horizontal_alignment=HorizontalAlignment.LEFT,
            vertical_alignment=VerticalAlignment.CENTER
        ),
        required=True
    ),
    
    CellMapping(
        cell_reference="E39",
        data_key="product_type",
        data_type=DataType.TEXT,
        format=CellFormat(
            horizontal_alignment=HorizontalAlignment.LEFT,
            vertical_alignment=VerticalAlignment.CENTER
        ),
        required=True
    ),
    
    CellMapping(
        cell_reference="A39",
        data_key="tu_number",
        data_type=DataType.TEXT,
        format=CellFormat(
            horizontal_alignment=HorizontalAlignment.LEFT,
            vertical_alignment=VerticalAlignment.CENTER
        ),
        required=False
    ),
    
    # Вес коробки
    CellMapping(
        cell_reference="K2",
        data_key="box_weight",
        data_type=DataType.NUMBER,
        format=CellFormat(
            horizontal_alignment=HorizontalAlignment.CENTER,
            vertical_alignment=VerticalAlignment.CENTER,
            number_format="0.00"
        ),
        required=False
    ),
    
    # Производитель (в ячейке B1)
    CellMapping(
        cell_reference="B1",
        data_key="manufacturer_display_text",
        data_type=DataType.MULTILINE_TEXT,
        format=CellFormat(
            horizontal_alignment=HorizontalAlignment.CENTER,
            vertical_alignment=VerticalAlignment.CENTER,
            wrap_text=True
        ),
        required=False,
        is_merged_cell=True
    ),
]

# ========== ДИНАМИЧЕСКИЕ СЕКЦИИ ==========
DYNAMIC_SECTIONS = [
    # Секция для роликов (левая часть: B14-D28)
    DynamicSection(
        name="rolls_left_section",
        start_cell="B14",
        rows_range=(14, 29),
        columns_config=[
            {
                "column": "B",
                "data_key": "gross_weight_per_roll",
                "data_type": DataType.NUMBER,
                "format": CellFormat(
                    horizontal_alignment=HorizontalAlignment.CENTER,
                    vertical_alignment=VerticalAlignment.CENTER,
                    number_format="0.00"
                )
            },
            {
                "column": "C",
                "data_key": "net_weight_per_roll",
                "data_type": DataType.NUMBER,
                "format": CellFormat(
                    horizontal_alignment=HorizontalAlignment.CENTER,
                    vertical_alignment=VerticalAlignment.CENTER,
                    number_format="0.00"
                )
            },
            {
                "column": "D",
                "data_key": "quantity_per_roll",
                "data_type": DataType.INTEGER,
                "format": CellFormat(
                    horizontal_alignment=HorizontalAlignment.CENTER,
                    vertical_alignment=VerticalAlignment.CENTER
                )
            }
        ],
        direction="vertical",
        max_items=15
    ),
    
    # Секция для роликов (правая часть: F14-H28)
    DynamicSection(
        name="rolls_right_section",
        start_cell="F14",
        rows_range=(14, 29),
        columns_config=[
            {
                "column": "F",
                "data_key": "gross_weight_per_roll",
                "data_type": DataType.NUMBER,
                "format": CellFormat(
                    horizontal_alignment=HorizontalAlignment.CENTER,
                    vertical_alignment=VerticalAlignment.CENTER,
                    number_format="0.00"
                )
            },
            {
                "column": "G",
                "data_key": "net_weight_per_roll",
                "data_type": DataType.NUMBER,
                "format": CellFormat(
                    horizontal_alignment=HorizontalAlignment.CENTER,
                    vertical_alignment=VerticalAlignment.CENTER,
                    number_format="0.00"
                )
            },
            {
                "column": "H",
                "data_key": "quantity_per_roll",
                "data_type": DataType.INTEGER,
                "format": CellFormat(
                    horizontal_alignment=HorizontalAlignment.CENTER,
                    vertical_alignment=VerticalAlignment.CENTER
                )
            }
        ],
        direction="vertical",
        max_items=15
    )
]