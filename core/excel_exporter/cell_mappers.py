# cell_mappers.py
"""
Модуль маппингов ячеек Excel.
Определяет КАКИЕ данные в КАКИЕ ячейки помещать.
Полностью декларативный, не содержит логики экспорта.
"""
from typing import Dict, List, Any, Optional, Tuple

from .cell_mappers_models import (
    DataType, HorizontalAlignment, VerticalAlignment,
    CellFormat, CellMapping, DynamicSection, SheetMapping
)
from .cell_mappers_data import (
    WORKSHOP1_BOX_STATIC,
    WORKSHOP1_BOX_DYNAMIC
)


class CellMappingRegistry:
    """
    Реестр всех маппингов по цехам и типам листов.
    Центральное место для определения структуры Excel файлов.
    """
    
    # ==================== МАППИНГИ ДЛЯ ЦЕХА 1 ====================
    
    @staticmethod
    def get_workshop1_box_mapping() -> SheetMapping:
        """
        Маппинг для 1 цеха, лист коробки ('Лист для коробки')
        """
        return SheetMapping(
            sheet_name="Лист для коробки",
            workshop="1",
            description="Этикетка для коробки (цех 1)",
            
            static_cells=WORKSHOP1_BOX_STATIC,
            dynamic_sections=WORKSHOP1_BOX_DYNAMIC,
            
            post_processing_hooks=[
                "update_manufacturer_info",  # Хук для обновления информации о производителе
                "validate_rolls_count"       # Хук для проверки количества роликов
            ]
        )
    
    @staticmethod
    def get_workshop1_pallet_mapping() -> SheetMapping:
        """
        Маппинг для 1 цеха, лист поддона ('Лист для паллеты')
        Структура аналогична коробке, но заполняются коробки вместо роликов
        """
        return SheetMapping(
            sheet_name="Лист для паллеты",
            workshop="1",
            description="Этикетка для поддона (цех 1)",
            
            static_cells=[
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
                    data_key="pallet_type",
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
                
                # Вес поддона
                CellMapping(
                    cell_reference="K2",
                    data_key="pallet_weight",
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
            ],
            
            dynamic_sections=[
                # Секция для коробок (левая часть: B14-D28)
                DynamicSection(
                    name="boxes_left_section",
                    start_cell="B14",
                    rows_range=(14, 29),  # Строки 14-28
                    columns_config=[
                        {
                            "column": "B",
                            "data_key": "gross_weight_per_box",
                            "data_type": DataType.NUMBER,
                            "format": CellFormat(
                                horizontal_alignment=HorizontalAlignment.CENTER,
                                vertical_alignment=VerticalAlignment.CENTER,
                                number_format="0.00"
                            )
                        },
                        {
                            "column": "C",
                            "data_key": "net_weight_per_box",
                            "data_type": DataType.NUMBER,
                            "format": CellFormat(
                                horizontal_alignment=HorizontalAlignment.CENTER,
                                vertical_alignment=VerticalAlignment.CENTER,
                                number_format="0.00"
                            )
                        },
                        {
                            "column": "D",
                            "data_key": "quantity_per_box",
                            "data_type": DataType.INTEGER,
                            "format": CellFormat(
                                horizontal_alignment=HorizontalAlignment.CENTER,
                                vertical_alignment=VerticalAlignment.CENTER
                            )
                        }
                    ],
                    direction="vertical",
                    max_items=15  # Максимум 15 коробок в левой секции
                ),
                
                # Секция для коробок (правая часть: F14-H28)
                DynamicSection(
                    name="boxes_right_section",
                    start_cell="F14",
                    rows_range=(14, 29),  # Строки 14-28
                    columns_config=[
                        {
                            "column": "F",
                            "data_key": "gross_weight_per_box",
                            "data_type": DataType.NUMBER,
                            "format": CellFormat(
                                horizontal_alignment=HorizontalAlignment.CENTER,
                                vertical_alignment=VerticalAlignment.CENTER,
                                number_format="0.00"
                            )
                        },
                        {
                            "column": "G",
                            "data_key": "net_weight_per_box",
                            "data_type": DataType.NUMBER,
                            "format": CellFormat(
                                horizontal_alignment=HorizontalAlignment.CENTER,
                                vertical_alignment=VerticalAlignment.CENTER,
                                number_format="0.00"
                            )
                        },
                        {
                            "column": "H",
                            "data_key": "quantity_per_box",
                            "data_type": DataType.INTEGER,
                            "format": CellFormat(
                                horizontal_alignment=HorizontalAlignment.CENTER,
                                vertical_alignment=VerticalAlignment.CENTER
                            )
                        }
                    ],
                    direction="vertical",
                    max_items=15  # Максимум 15 коробок в правой секции
                )
            ],
            
            post_processing_hooks=[
                "update_manufacturer_info",
                "validate_boxes_count"  # Хук для проверки количества коробок
            ]
        )    
    

    @staticmethod
    def get_workshop1_noweight_mapping() -> SheetMapping:
        """
        Маппинг для 1 цеха, лист без веса ('БезВеса')
        """
        return SheetMapping(
            sheet_name="БезВеса",
            workshop="1",
            description="Лист без веса для поддона (цех 1)",
            
            static_cells=[
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
            ],
            
            dynamic_sections=[
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
            ],
            
            post_processing_hooks=[
                "update_manufacturer_info",
                "validate_boxes_count_noweight",
                "fill_box_numbers"
            ]
        )    
    
    @staticmethod
    def get_workshop1_multitype_mapping() -> SheetMapping:
        """
        Маппинг для 1 цеха, лист 'Много видов' ('Лист много видов')
        """
        return SheetMapping(
            sheet_name="Лист много видов",
            workshop="1",
            description="Лист много видов (цех 1)",
            
            static_cells=[
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
                
                # Вес поддона
                CellMapping(
                    cell_reference="K2",
                    data_key="pallet_weight",
                    data_type=DataType.NUMBER,
                    format=CellFormat(
                        horizontal_alignment=HorizontalAlignment.CENTER,
                        vertical_alignment=VerticalAlignment.CENTER,
                        number_format="0.00"
                    ),
                    required=False
                ),
            ],
            
            dynamic_sections=[
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
                            "data_key": "product_text",  # Это product_name
                            "data_type": DataType.TEXT,
                            "format": CellFormat(
                                horizontal_alignment=HorizontalAlignment.LEFT,
                                vertical_alignment=VerticalAlignment.CENTER
                            )
                        },
                        {
                            "column": "F",
                            "data_key": "gross_total",
                            "data_type": DataType.NUMBER,
                            "format": CellFormat(
                                horizontal_alignment=HorizontalAlignment.CENTER,
                                vertical_alignment=VerticalAlignment.CENTER,
                                number_format="0.00"
                            )
                        },
                        {
                            "column": "G",
                            "data_key": "net_total",
                            "data_type": DataType.NUMBER,
                            "format": CellFormat(
                                horizontal_alignment=HorizontalAlignment.CENTER,
                                vertical_alignment=VerticalAlignment.CENTER,
                                number_format="0.00"
                            )
                        },
                        {
                            "column": "H",
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
        )  

    # ==================== МАППИНГИ ДЛЯ ЦЕХА 2 ====================

    @staticmethod
    def get_workshop2_box_mapping() -> SheetMapping:
        """
        Маппинг для 2 цеха, лист 'Поддон' (коробка)
        """
        return SheetMapping(
            sheet_name="Поддон",
            workshop="2",
            description="Этикетка для коробки (цех 2)",
            
            static_cells=[
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
            ],
            
            dynamic_sections=[
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
            ],
            
            post_processing_hooks=[
                "update_manufacturer_info",  # Производитель в A1
                "validate_rolls_count_workshop2"
            ]
        )
    
    @staticmethod
    def get_workshop2_pallet_list_mapping() -> SheetMapping:
        """
        Маппинг для 2 цеха, лист 'Список поддонов'
        """
        return SheetMapping(
            sheet_name="Список поддонов",
            workshop="2",
            description="Список поддонов (цех 2)",
            
            static_cells=[
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
            ],
            
            dynamic_sections=[
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
            ],
            
            post_processing_hooks=[
                "update_manufacturer_info",
                "validate_pallet_list_capacity"
            ]
        )
        
    @staticmethod
    def get_workshop2_multitype_mapping() -> SheetMapping:
        """
        Маппинг для 2 цеха, лист 'Много видов'
        """
        return SheetMapping(
            sheet_name="Много видов",
            workshop="2",
            description="Лист много видов (цех 2)",
            
            static_cells=[
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
            ],
            
            dynamic_sections=[
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
            ],
            
            post_processing_hooks=[
                "update_manufacturer_info"  # Производитель в A1
            ]
        )
    
    # ==================== МЕТОДЫ ДОСТУПА К МАППИНГАМ ====================
    
    @classmethod
    def get_mapping(cls, workshop: str, sheet_type: str, mode: str = "box") -> SheetMapping:
        """
        Получает маппинг по параметрам.
        
        Args:
            workshop: "1" или "2"
            sheet_type: "box", "pallet", "multitype", "noweight", "pallet_list"
            mode: Дополнительный режим (для совместимости)
            
        Returns:
            Соответствующий SheetMapping
            
        Raises:
            ValueError: Если маппинг не найден
        """
        # Словарь доступных маппингов
        mappings = {
            # Цех 1
            ("1", "box"): cls.get_workshop1_box_mapping,           
            ("1", "pallet"): cls.get_workshop1_pallet_mapping,
            ("1", "noweight"): cls.get_workshop1_noweight_mapping,
            ("1", "multitype"): cls.get_workshop1_multitype_mapping,            
            
            # Цех 2
            ("2", "box"): cls.get_workshop2_box_mapping,
            ("2", "pallet_list"): cls.get_workshop2_pallet_list_mapping,
            ("2", "multitype"): cls.get_workshop2_multitype_mapping,
        }
        
        key = (workshop, sheet_type)
        
        if key not in mappings:
            # Пробуем найти по workshop и mode (для обратной совместимости)
            alt_key = (workshop, mode)
            if alt_key in mappings:
                return mappings[alt_key]()
            
            # Если не нашли - пробуем найти по sheet_type (без workshop)
            for (w, s), mapper in mappings.items():
                if s == sheet_type:
                    return mapper()
            
            raise ValueError(f"Маппинг не найден для workshop={workshop}, sheet_type={sheet_type}, mode={mode}")
        
        return mappings[key]()
    
    @classmethod
    def get_available_mappings(cls) -> List[Dict[str, Any]]:
        """Возвращает список всех доступных маппингов"""
        return [
            # Цех 1
            {
                "workshop": "1",
                "sheet_type": "box",
                "sheet_name": "Лист для коробки",
                "description": "Этикетка для коробки (цех 1)"
            },
            {
                "workshop": "1",
                "sheet_type": "pallet",
                "sheet_name": "Лист для паллеты",
                "description": "Этикетка для поддона (цех 1)"
            },
            {
                "workshop": "1",
                "sheet_type": "noweight",
                "sheet_name": "БезВеса",
                "description": "Лист без веса для поддона (цех 1)"
            },
            {
                "workshop": "1",
                "sheet_type": "multitype",
                "sheet_name": "Лист много видов",
                "description": "Лист много видов (цех 1)"
            },
            
            # Цех 2
            {
                "workshop": "2",
                "sheet_type": "box",
                "sheet_name": "Поддон",
                "description": "Этикетка для коробки (цех 2)"
            },
            {
                "workshop": "2",
                "sheet_type": "pallet_list",
                "sheet_name": "Список поддонов",
                "description": "Список поддонов (цех 2)"
            },
            {
                "workshop": "2",
                "sheet_type": "multitype",
                "sheet_name": "Много видов",
                "description": "Лист много видов (цех 2)"
            }
        ]
    
    # ==================== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ====================
    
    @staticmethod
    def parse_cell_reference(cell_ref: str) -> Tuple[str, int]:
        """
        Разбирает ссылку на ячейку на букву колонки и номер строки.
        
        Args:
            cell_ref: Ссылка на ячейку (например, "A1", "BC23")
            
        Returns:
            Кортеж (буква_колонки, номер_строки)
        """
        import re
        match = re.match(r"([A-Z]+)(\d+)", cell_ref)
        if not match:
            raise ValueError(f"Некорректная ссылка на ячейку: {cell_ref}")
        return match.group(1), int(match.group(2))
    
    @staticmethod
    def get_column_letter(column_index: int) -> str:
        """
        Преобразует индекс колонки в букву Excel.
        
        Args:
            column_index: Индекс колонки (начинается с 1)
            
        Returns:
            Буква колонки Excel
        """
        result = ""
        while column_index > 0:
            column_index, remainder = divmod(column_index - 1, 26)
            result = chr(65 + remainder) + result
        return result
    
    @staticmethod
    def get_column_index(column_letter: str) -> int:
        """
        Преобразует букву колонки Excel в индекс.
        
        Args:
            column_letter: Буква колонки Excel
            
        Returns:
            Индекс колонки (начинается с 1)
        """
        result = 0
        for char in column_letter:
            result = result * 26 + (ord(char) - 64)
        return result

# ==================== ШОРТКАТЫ ДЛЯ БЫСТРОГО ДОСТУПА ====================

def get_mapping(workshop: str, sheet_type: str, mode: str = "box") -> SheetMapping:
    """Краткая функция для получения маппинга"""
    return CellMappingRegistry.get_mapping(workshop, sheet_type, mode)

# Цех 1
def get_workshop1_box_mapping() -> SheetMapping:
    """Краткая функция для получения маппинга коробки 1 цеха"""
    return CellMappingRegistry.get_workshop1_box_mapping()

def get_workshop1_pallet_mapping() -> SheetMapping:
    """Краткая функция для получения маппинга поддона 1 цеха"""
    return CellMappingRegistry.get_workshop1_pallet_mapping()

def get_workshop1_noweight_mapping() -> SheetMapping:
    """Краткая функция для получения маппинга без веса 1 цеха"""
    return CellMappingRegistry.get_workshop1_noweight_mapping()

def get_workshop1_multitype_mapping() -> SheetMapping:
    """Краткая функция для получения много-видового маппинга 1 цеха"""
    return CellMappingRegistry.get_workshop1_multitype_mapping()

# Цех 2
def get_workshop2_box_mapping() -> SheetMapping:
    """Краткая функция для получения маппинга коробки 2 цеха"""
    return CellMappingRegistry.get_workshop2_box_mapping()

def get_workshop2_pallet_list_mapping() -> SheetMapping:
    """Краткая функция для получения маппинга списка поддонов 2 цеха"""
    return CellMappingRegistry.get_workshop2_pallet_list_mapping()

def get_workshop2_multitype_mapping() -> SheetMapping:
    """Краткая функция для получения много-видового маппинга 2 цеха"""
    return CellMappingRegistry.get_workshop2_multitype_mapping()