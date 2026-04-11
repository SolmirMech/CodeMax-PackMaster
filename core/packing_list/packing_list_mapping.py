# core/packing_list/packing_list_mapping.py

from openpyxl.styles import Font, Border, Side, Alignment

# === Стили ===
CALIBRI_14 = Font(name='Calibri', size=14)

UNDERLINE_BORDER = Border(bottom=Side(style='thin'))  # для E2
THIN_BORDER = Border(
    left=Side(style='thin'),
    right=Side(style='thin'),
    top=Side(style='thin'),
    bottom=Side(style='thin')
)

CENTER_ALIGN = Alignment(horizontal='center', vertical='center')
LEFT_ALIGN = Alignment(horizontal='left', vertical='center')

# === Маппинг шапки (фиксированные ячейки) ===
HEADER_MAPPING = {
    "list_number": {"cell": "E2", "style": {"font": CALIBRI_14, "border": UNDERLINE_BORDER, "alignment": CENTER_ALIGN}},
    "supplier": {"cell": "C4", "style": {"font": CALIBRI_14, "alignment": LEFT_ALIGN}},
    "customer": {"cell": "C5", "style": {"font": CALIBRI_14, "alignment": LEFT_ALIGN}},
    "consignee": {"cell": "C6", "style": {"font": CALIBRI_14, "alignment": LEFT_ALIGN}},
    "contract": {"cell": "C7", "style": {"font": CALIBRI_14, "alignment": LEFT_ALIGN}},
    "project": {"cell": "C8", "style": {"font": CALIBRI_14, "alignment": LEFT_ALIGN}},
    "equipment_name": {"cell": "C9", "style": {"font": CALIBRI_14, "alignment": LEFT_ALIGN}},
}

# === Таблица 1: Места ===
PLACES_START_ROW = 13
PLACES_END_ROW = 17
PLACES_COLUMNS = {
    "place_number": {"col": 1, "header": "Номер места"},           # A
    "net_weight": {"col": 2, "header": "нетто"},                   # B
    "gross_weight": {"col": 3, "header": "брутто"},                # C
    "length": {"col": 4, "header": "длина"},                       # D
    "width": {"col": 5, "header": "ширина"},                       # E
    "height": {"col": 6, "header": "высота"},                      # F
    "storage_type": {"col": 7, "header": "Тип хранения"},          # G
}

# === Таблица 2: Товары ===
ITEMS_START_ROW = 24
ITEMS_END_ROW = 28
ITEMS_COLUMNS = {
    "item_number": {"col": 1, "header": "№п/п"},                   # A
    "order_request": {"col": 2, "header": "Заявка/про-наряд"},     # B
    "article_vn": {"col": 3, "header": "Артикул ВН"},              # C
    "name": {"col": 4, "header": "Наименование"},                  # D
    "unit": {"col": 5, "header": "Ед. изм-я"},                     # E
    "quantity": {"col": 6, "header": "Количество"},                # F
    "article_vn_product": {"col": 7, "header": "Артикул ВН изделия"}, # G
    "product": {"col": 8, "header": "Изделие"},                    # H
}

# Общий стиль для данных в таблицах
TABLE_CELL_STYLE = {
    "font": CALIBRI_14,
    "border": THIN_BORDER,
    "alignment": CENTER_ALIGN,
}