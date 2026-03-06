# cell_mappers_data/workshop1_box_noweight.py
"""Данные для маппинга поддона ПоддонРолики 1 цеха"""

from core.excel_exporter.cell_mappers_data.cell_mappers_models import (
    CellMapping, DynamicSection, CellFormat,
    DataType, HorizontalAlignment, VerticalAlignment
)

# ========== СТАТИЧЕСКИЕ ЯЧЕЙКИ ==========
STATIC_CELLS = [
    # Производитель - C1
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
    
    # Номер заказа - E9
    CellMapping(
        cell_reference="E9",
        data_key="order_number",
        data_type=DataType.TEXT,
        format=CellFormat(
            horizontal_alignment=HorizontalAlignment.CENTER,
            vertical_alignment=VerticalAlignment.CENTER
        ),
        required=True
    ),
    
    # Заказчик - D10
    CellMapping(
        cell_reference="D10",
        data_key="customer",
        data_type=DataType.TEXT,
        format=CellFormat(
            horizontal_alignment=HorizontalAlignment.CENTER,
            vertical_alignment=VerticalAlignment.CENTER
        ),
        required=True
    ),
    
    # Наименование продукции - D11
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
    
    # Номер поддона - F5
    CellMapping(
        cell_reference="F5",
        data_key="pallet_num",
        data_type=DataType.NUMBER,
        format=CellFormat(
            horizontal_alignment=HorizontalAlignment.CENTER,
            vertical_alignment=VerticalAlignment.CENTER,
            number_format="0"
        ),
        required=False
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
    
    # Тип продукта - E39
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
    # Первая колонка: ролики 1-15 (B14-C28)
    DynamicSection(
        name="rolls_column_1",
        start_cell="B14",
        rows_range=(14, 29),
        columns_config=[
            {
                "column": "B",
                "data_key": "rolls_count",
                "data_type": DataType.INTEGER,
                "format": CellFormat(
                    horizontal_alignment=HorizontalAlignment.CENTER,
                    vertical_alignment=VerticalAlignment.CENTER
                )
            },
            {
                "column": "C",
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