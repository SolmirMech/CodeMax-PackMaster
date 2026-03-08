# core/packaging/packaging_mapping.py
from dataclasses import dataclass
from typing import Optional

from openpyxl.styles import Font, Border, Side, Alignment


@dataclass
class CellStyle:
    """Стиль ячейки"""
    font: Optional[Font] = None
    border: Optional[Border] = None
    alignment: Optional[Alignment] = None
    number_format: Optional[str] = None  # формат чисел


@dataclass
class ColumnMapping:
    """Маппинг колонки"""
    column: int  # номер колонки (1-based)
    style: CellStyle
    data_type: str = "text"  # text, number, date


# Границы (только внешние)
THIN_BORDER = Border(
    left=Side(style='thin'),
    right=Side(style='thin'),
    top=Side(style='thin'),
    bottom=Side(style='thin')
)

# Выравнивание по центру
CENTER_ALIGN = Alignment(horizontal='center', vertical='center')

# Шрифты
CALIBRI_11 = Font(name='Calibri', size=11)
CALIBRI_11_BOLD = Font(name='Calibri', size=11, bold=True)
CALIBRI_15_BOLD = Font(name='Calibri', size=15, bold=True)
CALIBRI_18_BOLD = Font(name='Calibri', size=18, bold=True)

# Маппинг колонок
PACKAGING_EXCEL_MAPPING = {
    "start_row": 2,
    "date_format": "%d.%m.%Y",
    "columns": {
        "date": ColumnMapping(
            column=1,
            data_type="date",
            style=CellStyle(
                font=CALIBRI_11,
                border=THIN_BORDER,
                alignment=CENTER_ALIGN
            )
        ),
        "order_number": ColumnMapping(
            column=2,
            data_type="text",
            style=CellStyle(
                font=CALIBRI_18_BOLD,
                border=THIN_BORDER,
                alignment=CENTER_ALIGN
            )
        ),
        "customer": ColumnMapping(
            column=3,
            data_type="text",
            style=CellStyle(
                font=CALIBRI_11_BOLD,
                border=THIN_BORDER,
                alignment=CENTER_ALIGN
            )
        ),
        "product_name": ColumnMapping(
            column=4,
            data_type="text",
            style=CellStyle(
                font=CALIBRI_11,
                border=THIN_BORDER,
                alignment=Alignment(horizontal='left', vertical='center')  # слева
            )
        ),
        "quantity_labels": ColumnMapping(
            column=5,
            data_type="number",
            style=CellStyle(
                font=CALIBRI_11,
                border=THIN_BORDER,
                alignment=Alignment(horizontal='center', vertical='center'),
                number_format="#,##0"  # формат с разделителями
            )
        ),
        "packer_name": ColumnMapping(
            column=6,
            data_type="text",
            style=CellStyle(
                font=CALIBRI_11_BOLD,
                border=THIN_BORDER,
                alignment=CENTER_ALIGN
            )
        ),
        "large_boxes": ColumnMapping(
            column=7,
            data_type="number",
            style=CellStyle(
                font=CALIBRI_15_BOLD,
                border=THIN_BORDER,
                alignment=CENTER_ALIGN
            )
        ),
        "small_boxes": ColumnMapping(
            column=8,
            data_type="number",
            style=CellStyle(
                font=CALIBRI_15_BOLD,
                border=THIN_BORDER,
                alignment=CENTER_ALIGN
            )
        ),
        "aquaLife_boxes": ColumnMapping(
            column=9,
            data_type="number",
            style=CellStyle(
                font=CALIBRI_15_BOLD,
                border=THIN_BORDER,
                alignment=CENTER_ALIGN
            )
        ),
        "note": ColumnMapping(
            column=12,
            data_type="text",
            style=CellStyle(
                font=CALIBRI_11,
                border=THIN_BORDER,
                alignment=Alignment(horizontal='left', vertical='center', wrap_text=True)
            )
        ),
    }
}