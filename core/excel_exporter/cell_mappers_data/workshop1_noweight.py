# cell_mappers_data/workshop1_noweight.py
"""Данные для маппинга поддона Без Веса 1 цеха"""

from ..cell_mappers_models import (
    CellMapping, DynamicSection, CellFormat,
    DataType, HorizontalAlignment, VerticalAlignment
)

# ========== СТАТИЧЕСКИЕ ЯЧЕЙКИ ==========
STATIC_CELLS = [
    # Заказчик - D10
    CellMapping(
        cell_reference="D10",
        data_key="customer",
        data_type=DataType.TEXT,
        format=CellFormat(
            horizontal_alignment=HorizontalAlignment.LEFT,
            vertical_alignment=VerticalAlignment.CENTER
        ),
        required=True
    ),
    
    # Номер заказа - E9
    CellMapping(
        cell_reference="E9",
        data_key="order_number",
        data_type=DataType.TEXT,
        format=CellFormat(
            horizontal_alignment=HorizontalAlignment.LEFT,
            vertical_alignment=VerticalAlignment.CENTER
        ),
        required=True
    ),
    
    # Наименование продукции - D11 (многострочный)
    CellMapping(
        cell_reference="D11",
        data_key="product_text",
        data_type=DataType.MULTILINE_TEXT,
        format=CellFormat(
            horizontal_alignment=HorizontalAlignment.LEFT,
            vertical_alignment=VerticalAlignment.TOP,
            wrap_text=True
        ),
        required=True
    ),
    
    # Дата упаковки - E37
    CellMapping(
        cell_reference="E37",
        data_key="date",
        data_type=DataType.DATE,
        format=CellFormat(
            horizontal_alignment=HorizontalAlignment.LEFT,
            vertical_alignment=VerticalAlignment.CENTER
        ),
        required=True
    ),
    
    # Упаковщик - E41
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
    
    # Производитель
    CellMapping(
        cell_reference="C1",
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
    
    # TU номер - A39
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
]

# ========== ДИНАМИЧЕСКИЕ СЕКЦИИ ==========
DYNAMIC_SECTIONS = [
    # ЛЕВАЯ секция (C14-C28) - только количество
    DynamicSection(
        name="boxes_left_section",
        start_cell="C14",
        rows_range=(14, 29),  # Строки 14-28
        columns_config=[
            {
                "column": "C",
                "data_key": "quantity_per_box",
                "data_type": DataType.INTEGER,
                "format": CellFormat(
                    horizontal_alignment=HorizontalAlignment.CENTER,
                    vertical_alignment=VerticalAlignment.CENTER
                )
            }
        ],
        direction="vertical",
        max_items=15  # Максимум 15 коробок
    ),
    
    # ЦЕНТРАЛЬНАЯ секция (F14-F28) - только количество
    DynamicSection(
        name="boxes_center_section",
        start_cell="F14",
        rows_range=(14, 29),  # Строки 14-28
        columns_config=[
            {
                "column": "F",
                "data_key": "quantity_per_box",
                "data_type": DataType.INTEGER,
                "format": CellFormat(
                    horizontal_alignment=HorizontalAlignment.CENTER,
                    vertical_alignment=VerticalAlignment.CENTER
                )
            }
        ],
        direction="vertical",
        max_items=15  # Максимум 15 коробок
    ),
    
    # ПРАВАЯ секция (I14-I28) - только количество
    DynamicSection(
        name="boxes_right_section",
        start_cell="I14",
        rows_range=(14, 29),  # Строки 14-28
        columns_config=[
            {
                "column": "I",
                "data_key": "quantity_per_box",
                "data_type": DataType.INTEGER,
                "format": CellFormat(
                    horizontal_alignment=HorizontalAlignment.CENTER,
                    vertical_alignment=VerticalAlignment.CENTER
                )
            }
        ],
        direction="vertical",
        max_items=15  # Максимум 15 коробок
    )
]