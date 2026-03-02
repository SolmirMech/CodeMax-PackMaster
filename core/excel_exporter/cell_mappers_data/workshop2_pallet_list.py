# cell_mappers_data/workshop2_pallet_list.py
"""Данные для маппинга Списка поддонов 2 цеха"""

from core.excel_exporter.cell_mappers_data.cell_mappers_models import (
    CellMapping, DynamicSection, CellFormat,
    DataType, HorizontalAlignment, VerticalAlignment
)

# ========== СТАТИЧЕСКИЕ ЯЧЕЙКИ ==========
STATIC_CELLS = [
    # Производитель - A1 (но не используется в методе export_to_pallet_list_sheet)
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
    
    # Вес втулки (в кг) - D4
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
    # Секция для строк поддонов (10-29)
    DynamicSection(
        name="pallets_list",
        start_cell="D10",  # Начинаем с D10
        rows_range=(10, 30),  # Строки 10-29
        columns_config=[
            {
                "column": "D",
                "data_key": "rolls_count",
                "data_type": DataType.INTEGER,
                "format": CellFormat(
                    horizontal_alignment=HorizontalAlignment.CENTER,
                    vertical_alignment=VerticalAlignment.CENTER
                )
            },
            {
                "column": "F",
                "data_key": "total_weight",
                "data_type": DataType.NUMBER,
                "format": CellFormat(
                    horizontal_alignment=HorizontalAlignment.CENTER,
                    vertical_alignment=VerticalAlignment.CENTER,
                    number_format="0.00"
                )
            },
            {
                "column": "H",
                "data_key": "total_quantity",
                "data_type": DataType.INTEGER,
                "format": CellFormat(
                    horizontal_alignment=HorizontalAlignment.CENTER,
                    vertical_alignment=VerticalAlignment.CENTER
                )
            },
            {
                "column": "L",
                "data_key": "total_length",
                "data_type": DataType.NUMBER,
                "format": CellFormat(
                    horizontal_alignment=HorizontalAlignment.CENTER,
                    vertical_alignment=VerticalAlignment.CENTER,
                    number_format="0.0"
                )
            }
        ],
        direction="vertical",  # Заполняем по строкам
        max_items=20  # Максимум 20 поддонов (строки 10-29)
    )
]