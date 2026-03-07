# core/packaging/packaging_excel.py
import re

import openpyxl

# Маппинг прямо здесь (как в плане)
PACKAGING_EXCEL_MAPPING = {
    "columns": {
        "date": 1,  # колонка A
        "order_number": 2,  # колонка B
        "customer": 3,  # колонка C
        "product_name": 4,  # колонка D
        "quantity_labels": 5,  # колонка E
        "packer_name": 6,  # колонка F
        "large_boxes": 7,  # колонка G
        "small_boxes": 8,  # колонка H
        "aquaLife_boxes": 9,  # колонка I
        "note": 12,  # колонка L
    },
    "start_row": 2,
    "date_format": "%d.%m.%Y"
}


class PackagingExcel:
    """ВСЯ работа с Excel для журнала упаковки"""

    @staticmethod
    def import_from_excel(file_path):
        """
        Импорт данных из Excel.
        Проверяет ВСЕ листы, импортирует с тех, где структура совпадает с БД.

        Returns:
            tuple: (imported_count, errors_list, entries_list)
        """
        errors = []
        all_entries = []
        imported_total = 0
        mapping = PACKAGING_EXCEL_MAPPING

        try:
            wb = openpyxl.load_workbook(file_path, data_only=True)

            # Проверяем каждый лист
            for sheet_name in wb.sheetnames:
                sheet = wb[sheet_name]

                # Проверяем структуру листа
                if not PackagingExcel._validate_sheet_structure(sheet):
                    errors.append(f"Лист '{sheet_name}' пропущен: несоответствие структуры")
                    continue

                # Импортируем данные с листа
                sheet_entries = []

                for row_idx, row in enumerate(sheet.iter_rows(min_row=mapping["start_row"]), mapping["start_row"]):
                    # Пропускаем пустые строки
                    if row[0].value is None:
                        continue

                    try:
                        entry = PackagingExcel._row_to_entry(row, mapping)
                        if entry.get('order_number') or entry.get('date'):  # Хотя бы одно поле заполнено
                            sheet_entries.append(entry)
                    except Exception as e:
                        errors.append(f"Лист '{sheet_name}', строка {row_idx}: {str(e)}")

                if sheet_entries:
                    all_entries.extend(sheet_entries)
                    imported_total += len(sheet_entries)
                    errors.append(f"Лист '{sheet_name}': импортировано {len(sheet_entries)} записей")

            wb.close()

        except Exception as e:
            errors.append(f"Ошибка открытия файла: {str(e)}")

        return imported_total, errors, all_entries

    @staticmethod
    def _validate_sheet_structure(sheet):
        """
        Проверяет, соответствует ли структура листа ожидаемой.
        Проверяет первые 3 непустые строки на наличие данных в нужных колонках.
        """
        mapping = PACKAGING_EXCEL_MAPPING
        start_row = mapping["start_row"]
        sample_rows = 0
        max_samples = 3

        for row in sheet.iter_rows(min_row=start_row, max_row=start_row + 10):
            # Первая ячейка (дата) - основной индикатор
            if row[0].value is None:
                continue

            sample_rows += 1
            if sample_rows > max_samples:
                break

            # Проверяем, что в ключевых колонках есть что-то похожее на данные
            has_data = False
            for field, col in mapping["columns"].items():
                cell_value = row[col - 1].value
                if cell_value not in (None, ""):
                    has_data = True
                    break

            if not has_data:
                return False

        return sample_rows > 0  # Хотя бы одна непустая строка нашлась

    @staticmethod
    def _row_to_entry(row, mapping):
        """Преобразует строку Excel в словарь entry"""
        entry = {}

        # Дата
        date_cell = row[mapping["columns"]["date"] - 1].value
        if date_cell:
            if hasattr(date_cell, 'strftime'):
                entry['date'] = date_cell.strftime('%Y-%m-%d')
            else:
                date_match = re.search(r'(\d{2})[.\-](\d{2})[.\-](\d{4})', str(date_cell))
                if date_match:
                    day, month, year = date_match.groups()
                    entry['date'] = f"{year}-{month}-{day}"
                else:
                    entry['date'] = str(date_cell)[:10]

        # Номер заказа
        order_val = row[mapping["columns"]["order_number"] - 1].value
        entry['order_number'] = str(order_val) if order_val else ""

        # Заказчик
        customer_val = row[mapping["columns"]["customer"] - 1].value
        entry['customer'] = str(customer_val) if customer_val else ""

        # Наименование
        product_val = row[mapping["columns"]["product_name"] - 1].value
        entry['product_name'] = str(product_val) if product_val else ""

        # Тираж
        qty_val = row[mapping["columns"]["quantity_labels"] - 1].value
        try:
            entry['quantity_labels'] = int(float(qty_val)) if qty_val else None
        except (ValueError, TypeError):
            entry['quantity_labels'] = None

        # Упаковщик
        packer_val = row[mapping["columns"]["packer_name"] - 1].value
        entry['packer_name'] = str(packer_val) if packer_val else ""

        # Большие коробки
        large_val = row[mapping["columns"]["large_boxes"] - 1].value
        try:
            entry['large_boxes'] = int(float(large_val)) if large_val else None
        except (ValueError, TypeError):
            entry['large_boxes'] = None

        # Маленькие коробки
        small_val = row[mapping["columns"]["small_boxes"] - 1].value
        try:
            entry['small_boxes'] = int(float(small_val)) if small_val else None
        except (ValueError, TypeError):
            entry['small_boxes'] = None

        # Аквалайф
        aqua_val = row[mapping["columns"]["aquaLife_boxes"] - 1].value
        try:
            entry['aquaLife_boxes'] = int(float(aqua_val)) if aqua_val else None
        except (ValueError, TypeError):
            entry['aquaLife_boxes'] = None

        # Примечание
        note_val = row[mapping["columns"]["note"] - 1].value
        entry['note'] = str(note_val) if note_val else ""

        return entry

    @staticmethod
    def export_to_excel(file_path, entries):
        """
        Экспорт записей в Excel (дозапись в конец активного листа)
        Возвращает количество записанных записей
        """
        if not entries:
            return 0

        mapping = PACKAGING_EXCEL_MAPPING
        wb = None

        try:
            wb = openpyxl.load_workbook(file_path)
            sheet = wb.active

            # Находим первую пустую строку
            row = mapping["start_row"]
            while sheet.cell(row=row, column=1).value:
                row += 1

            # Записываем
            for entry in entries:
                for field, col in mapping["columns"].items():
                    value = entry.get(field, "")

                    # Спецобработка даты: YYYY-MM-DD -> DD.MM.YYYY
                    if field == "date" and value and len(str(value)) == 10 and str(value)[4] == '-':
                        y, m, d = str(value).split('-')
                        value = f"{d}.{m}.{y}"

                    sheet.cell(row=row, column=col).value = value

                row += 1

            wb.save(file_path)
            wb.close()

            return len(entries)

        except Exception as e:
            if wb:
                try:
                    wb.close()
                except:
                    pass
            raise Exception(f"Ошибка экспорта: {str(e)}")