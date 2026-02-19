# cell_mappers_data/workshop2_box.py
"""Данные для маппинга поддона (технически как коробка) 2 цеха"""

from ..cell_mappers_models import (
    CellMapping, DynamicSection, CellFormat,
    DataType, HorizontalAlignment, VerticalAlignment
)

# ========== СТАТИЧЕСКИЕ ЯЧЕЙКИ ==========
STATIC_CELLS = [
    # Производитель - A1
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
    
    # Тип упаковки - D3
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
    
    # Номер заказа - D6
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
    
    # Заказчик - D7
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
    
    # Наименование продукции - D8
    CellMapping(
        cell_reference="D8",
        data_key="product_text",
        data_type=DataType.MULTILINE_TEXT,
        format=CellFormat(
            horizontal_alignment=HorizontalAlignment.LEFT,
            vertical_alignment=VerticalAlignment.TOP,
            wrap_text=True
        ),
        required=True
    ),
    
    # Вес втулки (в кг) - D4 (конвертация из граммов)
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
    
    # Номер поддона - D5
    CellMapping(
        cell_reference="D5",
        data_key="pallet_num",
        data_type=DataType.NUMBER,
        format=CellFormat(
            horizontal_alignment=HorizontalAlignment.CENTER,
            vertical_alignment=VerticalAlignment.CENTER,
            number_format="0"
        ),
        required=False
    ),                
    
    # Вес коробки - H3
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
    
    # Дата упаковки - D37
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
    # Первая колонка: ролики 1-20 (B10-C29)
    DynamicSection(
        name="rolls_column_1",
        start_cell="B10",
        rows_range=(10, 30),  # Строки 10-29
        columns_config=[
            {
                "column": "B",
                "data_key": "net_weight_per_roll",
                "data_type": DataType.NUMBER,
                "format": CellFormat(
                    horizontal_alignment=HorizontalAlignment.CENTER,
                    vertical_alignment=VerticalAlignment.CENTER,
                    number_format="0.00"
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
        max_items=20  # Максимум 20 роликов в первой колонке
    ),
    
    # Вторая колонка: ролики 21-40 (E10-F29)
    DynamicSection(
        name="rolls_column_2",
        start_cell="E10",
        rows_range=(10, 30),  # Строки 10-29
        columns_config=[
            {
                "column": "E",
                "data_key": "net_weight_per_roll",
                "data_type": DataType.NUMBER,
                "format": CellFormat(
                    horizontal_alignment=HorizontalAlignment.CENTER,
                    vertical_alignment=VerticalAlignment.CENTER,
                    number_format="0.00"
                )
            },
            {
                "column": "F",
                "data_key": "quantity_per_roll",
                "data_type": DataType.INTEGER,
                "format": CellFormat(
                    horizontal_alignment=HorizontalAlignment.CENTER,
                    vertical_alignment=VerticalAlignment.CENTER
                )
            }
        ],
        direction="vertical",
        max_items=20  # Максимум 20 роликов во второй колонке
    ),
    
    # Третья колонка: ролики 41-60 (H10-I29)
    DynamicSection(
        name="rolls_column_3",
        start_cell="H10",
        rows_range=(10, 30),  # Строки 10-29
        columns_config=[
            {
                "column": "H",
                "data_key": "net_weight_per_roll",
                "data_type": DataType.NUMBER,
                "format": CellFormat(
                    horizontal_alignment=HorizontalAlignment.CENTER,
                    vertical_alignment=VerticalAlignment.CENTER,
                    number_format="0.00"
                )
            },
            {
                "column": "I",
                "data_key": "quantity_per_roll",
                "data_type": DataType.INTEGER,
                "format": CellFormat(
                    horizontal_alignment=HorizontalAlignment.CENTER,
                    vertical_alignment=VerticalAlignment.CENTER
                )
            }
        ],
        direction="vertical",
        max_items=20  # Максимум 20 роликов в третьей колонке
    ),
    
    # Колонка длин: L10-L69 (соответствует роликам 1-60)
    DynamicSection(
        name="roll_lengths",
        start_cell="L10",
        rows_range=(10, 70),  # Строки 10-69
        columns_config=[
            {
                "column": "L",
                "data_key": "roll_length",
                "data_type": DataType.NUMBER,
                "format": CellFormat(
                    horizontal_alignment=HorizontalAlignment.CENTER,
                    vertical_alignment=VerticalAlignment.CENTER,
                    number_format="0.0"
                )
            }
        ],
        direction="vertical",
        max_items=60  # Максимум 60 значений длины
    )
]