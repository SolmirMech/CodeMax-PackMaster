# cell_mappers_data/workshop2_multitype.py
"""Данные для маппинга Много видов 2 цеха"""

from ..cell_mappers_models import (
    CellMapping, DynamicSection, CellFormat,
    DataType, HorizontalAlignment, VerticalAlignment
)

# ========== СТАТИЧЕСКИЕ ЯЧЕЙКИ ==========
STATIC_CELLS = [
    # Основная информация
    CellMapping(
        cell_reference="D7",
        data_key="customer",
        data_type=DataType.TEXT,
        format=CellFormat(
            horizontal_alignment=HorizontalAlignment.CENTER,
            vertical_alignment=VerticalAlignment.CENTER
        ),
        required=True
    ),
    
    CellMapping(
        cell_reference="A1",
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
        cell_reference="D3",
        data_key="pallet_type",
        data_type=DataType.TEXT,
        format=CellFormat(
            horizontal_alignment=HorizontalAlignment.CENTER,
            vertical_alignment=VerticalAlignment.CENTER
        ),
        required=True
    ),
    
    CellMapping(
        cell_reference="D6",
        data_key="order_number",
        data_type=DataType.TEXT,
        format=CellFormat(
            horizontal_alignment=HorizontalAlignment.CENTER,
            vertical_alignment=VerticalAlignment.CENTER
        ),
        required=True
    ),               
    
    CellMapping(
        cell_reference="D37",
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
    
    CellMapping(
        cell_reference="D4",
        data_key="sleeve_weight_kg",
        data_type=DataType.NUMBER,
        format=CellFormat(
            horizontal_alignment=HorizontalAlignment.CENTER,
            vertical_alignment=VerticalAlignment.CENTER,
            number_format="0.00"
        ),
        required=False
    ),
    
    # Диаметр втулки - G4
    CellMapping(
        cell_reference="G4",
        data_key="sleeve_diameter",
        data_type=DataType.NUMBER,
        format=CellFormat(
            horizontal_alignment=HorizontalAlignment.CENTER,
            vertical_alignment=VerticalAlignment.CENTER,
            number_format="0"
        ),
        required=False
    ),
    
    # Вес поддона - H3
    CellMapping(
        cell_reference="H3",
        data_key="pallet_weight",
        data_type=DataType.NUMBER,
        format=CellFormat(
            horizontal_alignment=HorizontalAlignment.CENTER,
            vertical_alignment=VerticalAlignment.CENTER,
            number_format="0"
        ),
        required=False
    ),
]

# ========== ДИНАМИЧЕСКИЕ СЕКЦИИ ==========
DYNAMIC_SECTIONS = [
    # Динамическая секция для строк (10-29)
    DynamicSection(
        name="multitype_rows",
        start_cell="A10",  # Начинаем с A10
        rows_range=(10, 30),  # Строки 10-29
        columns_config=[
            {
                "column": "A",
                "data_key": "pallets_count",  # Количество поддонов
                "data_type": DataType.INTEGER,
                "format": CellFormat(
                    horizontal_alignment=HorizontalAlignment.CENTER,
                    vertical_alignment=VerticalAlignment.CENTER
                )
            },
            {
                "column": "B",
                "data_key": "product_text",  # Это product_name (наименование продукции)
                "data_type": DataType.TEXT,
                "format": CellFormat(
                    horizontal_alignment=HorizontalAlignment.LEFT,
                    vertical_alignment=VerticalAlignment.CENTER
                )
            },
            {
                "column": "H",
                "data_key": "total_weight",  # Суммарный вес
                "data_type": DataType.NUMBER,
                "format": CellFormat(
                    horizontal_alignment=HorizontalAlignment.CENTER,
                    vertical_alignment=VerticalAlignment.CENTER,
                    number_format="0.00"
                )
            },
            {
                "column": "I",
                "data_key": "total_quantity",  # Суммарное количество
                "data_type": DataType.INTEGER,
                "format": CellFormat(
                    horizontal_alignment=HorizontalAlignment.CENTER,
                    vertical_alignment=VerticalAlignment.CENTER
                )
            },
            {
                "column": "L",
                "data_key": "total_length",  # Суммарная длина
                "data_type": DataType.NUMBER,
                "format": CellFormat(
                    horizontal_alignment=HorizontalAlignment.CENTER,
                    vertical_alignment=VerticalAlignment.CENTER,
                    number_format="0.0"
                )
            }
        ],
        direction="vertical",  # Заполняем по строкам
        max_items=20  # Максимум 20 строк (10-29)
    )
]