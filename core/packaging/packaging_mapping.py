# core/packaging/packaging_mapping.py
from dataclasses import dataclass
from typing import Optional, Dict, Any

from openpyxl.styles import Font, Border, Side, Alignment


@dataclass
class CellStyle:
    """Стиль ячейки"""
    font: Optional[Font] = None
    border: Optional[Border] = None
    alignment: Optional[Alignment] = None
    number_format: Optional[str] = None


@dataclass
class ColumnMapping:
    """Маппинг колонки"""
    column: int  # номер колонки (1-based)
    style: CellStyle
    data_type: str = "text"  # text, number, date


# === Стили ===
THIN_BORDER = Border(
    left=Side(style='thin'),
    right=Side(style='thin'),
    top=Side(style='thin'),
    bottom=Side(style='thin')
)

CENTER_ALIGN = Alignment(horizontal='center', vertical='center')
LEFT_ALIGN = Alignment(horizontal='left', vertical='center')

CALIBRI_11 = Font(name='Calibri', size=11)
CALIBRI_11_BOLD = Font(name='Calibri', size=11, bold=True)
CALIBRI_15_BOLD = Font(name='Calibri', size=15, bold=True)
CALIBRI_18_BOLD = Font(name='Calibri', size=18, bold=True)


# === Маппинг для ЦЕХА 1 ===
# Структура: Заголовок в 1 строке, данные со 2 строки
# A - Дата
# B - № заказа
# C - Заказчик
# D - Наименование
# E - Тираж
# F - Упаковщик
# G - Большие коробки (col_1)
# H - Маленькие коробки (col_2)
# I - Аквалайф коробки (col_3)
# J - Запасная (col_4)
# K - Запасная (col_5)
# L - Примечание

WORKSHOP_1_MAPPING = {
    "name": "Цех 1",
    "start_row": 2,  # данные начинаются со 2 строки
    "date_format": "%d.%m.%Y",
    "display_names": {
        "date": "Дата",
        "order_number": "№ заказа",
        "customer": "Заказчик",
        "product_name": "Наименование",
        "quantity_labels": "Тираж",
        "packer_name": "Упаковщик",
        "col_1": "Большие коробки",
        "col_2": "Маленькие коробки",
        "col_3": "Аквалайф",
        "note": "Примечание"
    },
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
                alignment=LEFT_ALIGN
            )
        ),
        "quantity_labels": ColumnMapping(
            column=5,
            data_type="number",
            style=CellStyle(
                font=CALIBRI_11,
                border=THIN_BORDER,
                alignment=CENTER_ALIGN,
                number_format="#,##0"
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
        "col_1": ColumnMapping(  # Большие коробки
            column=7,
            data_type="number",
            style=CellStyle(
                font=CALIBRI_15_BOLD,
                border=THIN_BORDER,
                alignment=CENTER_ALIGN
            )
        ),
        "col_2": ColumnMapping(  # Маленькие коробки
            column=8,
            data_type="number",
            style=CellStyle(
                font=CALIBRI_15_BOLD,
                border=THIN_BORDER,
                alignment=CENTER_ALIGN
            )
        ),
        "col_3": ColumnMapping(  # Аквалайф коробки
            column=9,
            data_type="number",
            style=CellStyle(
                font=CALIBRI_15_BOLD,
                border=THIN_BORDER,
                alignment=CENTER_ALIGN
            )
        ),
        "col_4": ColumnMapping(  # Запасная колонка J
            column=10,
            data_type="number",
            style=CellStyle(
                font=CALIBRI_11,
                border=THIN_BORDER,
                alignment=CENTER_ALIGN
            )
        ),
        "col_5": ColumnMapping(  # Запасная колонка K
            column=11,
            data_type="number",
            style=CellStyle(
                font=CALIBRI_11,
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


# === Маппинг для ЦЕХА 2 ===
# Структура: Заголовок в 2 строках, данные с 3 строки
# A - Дата
# B - Упаковщик
# C - № заказа
# D - Заказчик
# E - Наименование
# F - Тираж
# G - Вес, кг (col_1)
# H - Поддоны малые (col_2)
# I - Поддоны евро (col_3)
# J - Поддоны большие (col_4)
# K - Коробки малые (col_5)
# L - Коробки большие (col_6)

# === Маппинг для ЦЕХА 2 ===
WORKSHOP_2_MAPPING = {
    "name": "Цех 2",
    "start_row": 3,
    "date_format": "%d.%m.%Y",
    "display_names": {
        "date": "Дата",
        "packer_name": "Упаковщик",
        "order_number": "№ заказа",
        "customer": "Заказчик",
        "product_name": "Наименование",
        "quantity_labels": "Тираж",
        "col_1": "Вес, кг",
        "col_2": "Поддоны мал.",
        "col_3": "Поддоны евр.",
        "col_4": "Поддоны бол.",
        "col_5": "Коробки мал.",
        "col_6": "Коробки бол.",
        "note": "Примечание"
    },
    "columns": {
        "date": ColumnMapping(
            column=1,
            data_type="date",
            style=CellStyle(
                font=Font(name='Arial Cyr', size=11),
                border=THIN_BORDER,
                alignment=CENTER_ALIGN
            )
        ),
        "packer_name": ColumnMapping(
            column=2,
            data_type="text",
            style=CellStyle(
                font=Font(name='Arial Cyr', size=11),
                border=THIN_BORDER,
                alignment=CENTER_ALIGN
            )
        ),
        "order_number": ColumnMapping(
            column=3,
            data_type="text",
            style=CellStyle(
                font=Font(name='Arial Cyr', size=11, bold=True),
                border=THIN_BORDER,
                alignment=CENTER_ALIGN
            )
        ),
        "customer": ColumnMapping(
            column=4,
            data_type="text",
            style=CellStyle(
                font=Font(name='Arial Cyr', size=11),
                border=THIN_BORDER,
                alignment=LEFT_ALIGN
            )
        ),
        "product_name": ColumnMapping(
            column=5,
            data_type="text",
            style=CellStyle(
                font=Font(name='Arial Cyr', size=11),
                border=THIN_BORDER,
                alignment=LEFT_ALIGN
            )
        ),
        "quantity_labels": ColumnMapping(
            column=6,
            data_type="number",
            style=CellStyle(
                font=Font(name='Calibri', size=11),
                border=THIN_BORDER,
                alignment=Alignment(horizontal='right', vertical='center'),
                number_format="#,##0"
            )
        ),
        "col_1": ColumnMapping(  # Вес, кг
            column=7,
            data_type="number",
            style=CellStyle(
                font=Font(name='Arial Cyr', size=11, bold=True),
                border=THIN_BORDER,
                alignment=CENTER_ALIGN
            )
        ),
        "col_2": ColumnMapping(  # Поддоны малые
            column=8,
            data_type="number",
            style=CellStyle(
                font=Font(name='Arial Cyr', size=11),
                border=THIN_BORDER,
                alignment=CENTER_ALIGN
            )
        ),
        "col_3": ColumnMapping(  # Поддоны евро
            column=9,
            data_type="number",
            style=CellStyle(
                font=Font(name='Arial Cyr', size=11),
                border=THIN_BORDER,
                alignment=CENTER_ALIGN
            )
        ),
        "col_4": ColumnMapping(  # Поддоны большие
            column=10,
            data_type="number",
            style=CellStyle(
                font=Font(name='Arial Cyr', size=11),
                border=THIN_BORDER,
                alignment=CENTER_ALIGN
            )
        ),
        "col_5": ColumnMapping(  # Коробки малые
            column=11,
            data_type="number",
            style=CellStyle(
                font=Font(name='Arial Cyr', size=11),
                border=THIN_BORDER,
                alignment=CENTER_ALIGN
            )
        ),
        "col_6": ColumnMapping(  # Коробки большие
            column=12,
            data_type="number",
            style=CellStyle(
                font=Font(name='Arial Cyr', size=11),
                border=THIN_BORDER,
                alignment=CENTER_ALIGN
            )
        ),
        "col_7": ColumnMapping(
            column=13,
            data_type="number",
            style=CellStyle(
                font=Font(name='Arial Cyr', size=11),
                border=THIN_BORDER,
                alignment=CENTER_ALIGN
            )
        ),
        "col_8": ColumnMapping(
            column=14,
            data_type="number",
            style=CellStyle(
                font=Font(name='Arial Cyr', size=11),
                border=THIN_BORDER,
                alignment=CENTER_ALIGN
            )
        ),
        "col_9": ColumnMapping(
            column=15,
            data_type="number",
            style=CellStyle(
                font=Font(name='Arial Cyr', size=11),
                border=THIN_BORDER,
                alignment=CENTER_ALIGN
            )
        ),
        "col_10": ColumnMapping(
            column=16,
            data_type="number",
            style=CellStyle(
                font=Font(name='Arial Cyr', size=11),
                border=THIN_BORDER,
                alignment=CENTER_ALIGN
            )
        ),
        "note": ColumnMapping(
            column=17,
            data_type="text",
            style=CellStyle(
                font=Font(name='Arial Cyr', size=11),
                border=THIN_BORDER,
                alignment=Alignment(horizontal='left', vertical='center', wrap_text=True)
            )
        ),
    }
}


# Словарь всех маппингов по ключу цеха
PACKAGING_MAPPINGS = {
    "1": WORKSHOP_1_MAPPING,
    "2": WORKSHOP_2_MAPPING,
}


def get_mapping(workshop_name: str) -> Dict[str, Any]:
    """Возвращает маппинг для указанного цеха"""
    return PACKAGING_MAPPINGS.get(workshop_name, WORKSHOP_1_MAPPING)


def get_workshop_names() -> list:
    """Возвращает список доступных цехов"""
    return list(PACKAGING_MAPPINGS.keys())