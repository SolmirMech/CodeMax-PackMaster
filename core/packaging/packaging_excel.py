# core/packaging/packaging_excel.py
import re
import os
import time
import openpyxl

from core.packaging.packaging_mapping import PACKAGING_EXCEL_MAPPING
# Старый простой маппинг для импорта
IMPORT_MAPPING = {
    "columns": {
        "date": 1,
        "order_number": 2,
        "customer": 3,
        "product_name": 4,
        "quantity_labels": 5,
        "packer_name": 6,
        "large_boxes": 7,
        "small_boxes": 8,
        "aquaLife_boxes": 9,
        "note": 12,
    },
    "start_row": 2,
    "date_format": "%d.%m.%Y"
}


class PackagingExcel:
    """ВСЯ работа с Excel для журнала упаковки"""

    @staticmethod
    def import_from_excel(file_path, db_callback=None, progress_callback=None, only_first_sheet=True):
        """
        Импорт данных из Excel с поэтапной передачей в БД и прогрессом

        Args:
            file_path: путь к файлу
            db_callback: функция для сохранения записи в БД (принимает entry)
            progress_callback: функция для обновления прогресса (принимает sheet_name, count)
            only_first_sheet: если True - импорт только из первого листа

        Returns:
            tuple: (imported_count, errors_list)
        """
        import gc
        errors = []
        imported_total = 0

        try:
            # Открываем файл
            wb = openpyxl.load_workbook(file_path, data_only=True, read_only=True)  # ← read_only режим!

            if only_first_sheet:
                sheets_to_process = [wb.sheetnames[0]] if wb.sheetnames else []
            else:
                sheets_to_process = wb.sheetnames

            for sheet_idx, sheet_name in enumerate(sheets_to_process):
                # Открываем лист
                sheet = wb[sheet_name]

                if progress_callback:
                    progress_callback(f"Обработка листа {sheet_idx + 1}/{len(sheets_to_process)}: {sheet_name}", None)

                # Простая проверка первой строки с данными
                first_data_row = None
                for row in sheet.iter_rows(min_row=2, max_row=5, values_only=True):
                    if row[0] is not None:
                        first_data_row = row
                        break

                if not first_data_row:
                    errors.append(f"Лист '{sheet_name}' пропущен: нет данных")
                    continue

                # Импортируем данные с листа
                sheet_imported = 0
                for row_idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), 2):
                    if row[0] is None:  # пустая строка
                        continue

                    try:
                        entry = PackagingExcel._row_to_entry_simple(row)
                        if entry.get('order_number') or entry.get('date'):
                            if db_callback:
                                db_callback(entry)
                            sheet_imported += 1

                            # Каждые 50 записей - обновляем прогресс и чистим память
                            if sheet_imported % 50 == 0:
                                if progress_callback:
                                    progress_callback(f"Лист '{sheet_name}'", sheet_imported)
                                import gc
                                gc.collect()

                    except Exception as e:
                        errors.append(f"Лист '{sheet_name}', строка {row_idx}: {str(e)}")

                if sheet_imported > 0:
                    imported_total += sheet_imported
                    if progress_callback:
                        progress_callback(f"✓ Лист '{sheet_name}' завершён", sheet_imported)
                    errors.append(f"Лист '{sheet_name}': импортировано {sheet_imported} записей")

                # Принудительно закрываем лист и чистим память
                # noinspection PyUnusedLocal
                sheet = None
                gc.collect()

            wb.close()

            if progress_callback:
                progress_callback("complete", (len(sheets_to_process), imported_total))

        except Exception as e:
            errors.append(f"Ошибка открытия файла: {str(e)}")
            if progress_callback:
                progress_callback("error", str(e))

        return imported_total, errors

    @staticmethod
    def _row_to_entry_simple(row):
        """Упрощённое преобразование строки для read_only режима"""
        entry = {}

        # Дата
        date_cell = row[0]
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

        # Остальные поля по индексам
        entry['order_number'] = str(row[1]) if row[1] else ""
        entry['customer'] = str(row[2]) if row[2] else ""
        entry['product_name'] = str(row[3]) if row[3] else ""

        # Числовые поля
        try:
            entry['quantity_labels'] = int(float(row[4])) if row[4] else None
        except:
            entry['quantity_labels'] = None

        entry['packer_name'] = str(row[5]) if row[5] else ""

        try:
            entry['large_boxes'] = int(float(row[6])) if row[6] else None
        except:
            entry['large_boxes'] = None

        try:
            entry['small_boxes'] = int(float(row[7])) if row[7] else None
        except:
            entry['small_boxes'] = None

        try:
            entry['aquaLife_boxes'] = int(float(row[8])) if row[8] else None
        except:
            entry['aquaLife_boxes'] = None

        entry['note'] = str(row[11]) if len(row) > 11 and row[11] else ""

        return entry

    @staticmethod
    def _validate_sheet_structure(sheet):
        """
        Проверяет, соответствует ли структура листа ожидаемой.
        Проверяет первые 3 непустые строки на наличие данных в нужных колонках.
        """
        mapping = IMPORT_MAPPING
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
    def export_to_excel(file_path, entries, max_retries=3):
        """
        Экспорт записей в Excel с файловой блокировкой
        """
        if not entries:
            return 0

        mapping = PACKAGING_EXCEL_MAPPING
        lock_file = file_path + ".lock"

        # Ждём освобождения, если файл заблокирован
        for attempt in range(max_retries):
            if not os.path.exists(lock_file):
                break
            lock_age = time.time() - os.path.getmtime(lock_file)
            if lock_age > 60:  # Зависший lock (старше минуты)
                try:
                    os.remove(lock_file)
                    break
                except:
                    pass
            if attempt < max_retries - 1:
                time.sleep(1)
            else:
                raise Exception("Файл заблокирован другим процессом")

        # Пытаемся создать свой lock-файл
        try:
            with open(lock_file, 'x') as f:
                f.write(str(os.getpid()))
        except FileExistsError:
            raise Exception("Файл заблокирован другим процессом")

        # Основная операция
        try:
            wb = openpyxl.load_workbook(file_path)
            sheet = wb.active

            # Находим первую пустую строку
            row = mapping["start_row"]
            while sheet.cell(row=row, column=1).value:
                row += 1

            # Записываем
            for entry in entries:
                for field, col_mapping in mapping["columns"].items():
                    col = col_mapping.column
                    value = entry.get(field, "")

                    if field == "date" and value and len(str(value)) == 10 and str(value)[4] == '-':
                        y, m, d = str(value).split('-')
                        value = f"{d}.{m}.{y}"

                    cell = sheet.cell(row=row, column=col, value=value)

                    if col_mapping.style:
                        if col_mapping.style.font:
                            cell.font = col_mapping.style.font
                        if col_mapping.style.border:
                            cell.border = col_mapping.style.border
                        if col_mapping.style.alignment:
                            cell.alignment = col_mapping.style.alignment
                        if col_mapping.style.number_format:
                            cell.number_format = col_mapping.style.number_format

                row += 1

            # Сохраняем прямо в исходный файл (не через временный)
            wb.save(file_path)
            wb.close()

            return len(entries)

        except Exception as e:
            raise Exception(f"Ошибка экспорта: {str(e)}")
        finally:
            # Всегда удаляем lock
            if os.path.exists(lock_file):
                try:
                    os.remove(lock_file)
                except:
                    pass
