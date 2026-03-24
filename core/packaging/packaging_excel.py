# core/packaging/packaging_excel.py
import os
import re
import shutil
import time
from copy import copy

import openpyxl
from openpyxl import load_workbook
from openpyxl.styles import PatternFill
import gc

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

    # core/packaging/packaging_excel.py

    @staticmethod
    def import_from_excel(file_path, db_callback=None, progress_callback=None, only_first_sheet=True):

        errors = []
        imported_total = 0

        try:
            # Используем read_only + keep_links=False для скорости
            wb = load_workbook(file_path, read_only=True, data_only=True, keep_links=False)

            if only_first_sheet:
                sheets_to_process = [wb.sheetnames[0]] if wb.sheetnames else []
            else:
                sheets_to_process = list(reversed(wb.sheetnames))

            for sheet_idx, sheet_name in enumerate(sheets_to_process):
                sheet = wb[sheet_name]

                if progress_callback:
                    progress_callback(f"Обработка листа {sheet_idx + 1}/{len(sheets_to_process)}: {sheet_name}", None)

                sheet_imported = 0

                # Читаем строки
                for row_idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=False), 2):
                    if row[0].value is None:
                        continue

                    try:
                        entry = PackagingExcel._row_to_entry_from_readonly(row, row_idx)
                        if db_callback:
                            db_callback(entry, sheet_name)
                        sheet_imported += 1

                        if sheet_imported % 50 == 0:
                            if progress_callback:
                                progress_callback(f"Лист '{sheet_name}'", sheet_imported)
                            gc.collect()

                    except Exception as e:
                        errors.append(f"Лист '{sheet_name}', строка {row_idx}: {str(e)}")

                if sheet_imported > 0:
                    imported_total += sheet_imported
                    if progress_callback:
                        progress_callback(f"✓ Лист '{sheet_name}' завершён", sheet_imported)
                    errors.append(f"Лист '{sheet_name}': импортировано {sheet_imported} записей")

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
    def _row_to_entry_from_readonly(row, row_index):
        """Преобразование строки из read_only режима с чтением цвета через низкоуровневый доступ"""

        def to_int(value):
            try:
                return int(float(value)) if value else None
            except:
                return None

        def format_date(date_cell):
            if not date_cell:
                return ""
            if hasattr(date_cell, 'strftime'):
                return date_cell.strftime('%Y-%m-%d')
            date_match = re.search(r'(\d{2})[.\-](\d{2})[.\-](\d{4})', str(date_cell))
            if date_match:
                day, month, year = date_match.groups()
                return f"{year}-{month}-{day}"
            return str(date_cell)[:10]

        # Получаем цвет из ячейки (в read_only режиме цвет доступен через parent)
        row_color = None
        try:
            # В read_only режиме нужно получить доступ к стилю через parent
            cell = row[6]  # колонка 7 (большие коробки)
            if cell.fill and cell.fill.start_color:
                color = cell.fill.start_color
                if hasattr(color, 'rgb') and color.rgb:
                    rgb = color.rgb
                    if len(rgb) == 8:
                        rgb = rgb[2:]
                    if rgb.upper() not in ('FFFFFF', '000000'):
                        row_color = rgb
        except:
            pass

        return {
            'source_row': row_index,
            'date': format_date(row[0].value),
            'order_number': str(row[1].value) if row[1].value else "",
            'customer': str(row[2].value) if row[2].value else "",
            'product_name': str(row[3].value) if row[3].value else "",
            'quantity_labels': to_int(row[4].value),
            'packer_name': str(row[5].value) if row[5].value else "",
            'large_boxes': to_int(row[6].value),
            'small_boxes': to_int(row[7].value),
            'aquaLife_boxes': to_int(row[8].value),
            'note': str(row[11].value) if len(row) > 11 and row[11].value else "",
            'row_color': row_color
        }

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
        Экспорт записей в Excel с поддержкой обновления существующих строк.
        Возвращает словарь {entry_id: (row_number, sheet_name)} для обновлённых/вставленных записей.
        """
        if not entries:
            return {}

        mapping = PACKAGING_EXCEL_MAPPING
        lock_file = file_path + ".lock"
        wb = None
        result_coords = {}

        # Блокировка файла
        for attempt in range(max_retries):
            if not os.path.exists(lock_file):
                break
            lock_age = time.time() - os.path.getmtime(lock_file)
            if lock_age > 60:
                try:
                    os.remove(lock_file)
                    break
                except:
                    pass
            if attempt < max_retries - 1:
                time.sleep(1)
            else:
                raise Exception("Файл заблокирован другим процессом")

        try:
            with open(lock_file, 'x') as f:
                f.write(str(os.getpid()))
        except FileExistsError:
            raise Exception("Файл заблокирован другим процессом")

        try:
            wb = openpyxl.load_workbook(file_path)
            active_sheet_name = wb.active.title

            # Группируем записи по листам
            entries_by_sheet = {}
            for entry in entries:
                # Для новых записей (без source_sheet) используем активный лист
                sheet_name = entry.get("source_sheet")
                if not sheet_name:
                    sheet_name = active_sheet_name
                    # Сохраняем sheet_name для будущих обновлений
                    result_coords[entry["id"]] = (None, sheet_name)

                if sheet_name not in entries_by_sheet:
                    entries_by_sheet[sheet_name] = []
                entries_by_sheet[sheet_name].append(entry)

            # Обрабатываем каждый лист
            for sheet_name, sheet_entries in entries_by_sheet.items():
                # Проверяем существование листа
                if sheet_name not in wb.sheetnames:
                    # Если листа нет, используем активный (для новых записей)
                    # или игнорируем (старые записи с несуществующим листом)
                    if sheet_name == active_sheet_name:
                        sheet = wb.active
                    else:
                        # Не создаём новый лист, используем активный
                        sheet = wb.active
                        sheet_name = active_sheet_name
                else:
                    sheet = wb[sheet_name]

                # Определяем максимальный номер строки с данными
                max_row = mapping["start_row"] - 1
                for row in range(mapping["start_row"], sheet.max_row + 2):
                    if sheet.cell(row=row, column=1).value:
                        max_row = row
                    else:
                        break

                # Обрабатываем каждую запись
                for entry in sheet_entries:
                    entry_id = entry["id"]
                    existing_row = entry.get("source_row")
                    existing_sheet = entry.get("source_sheet")

                    # Если запись имеет координаты и они соответствуют текущему листу
                    if existing_row and existing_sheet == sheet_name:
                        row_num = existing_row
                    else:
                        # Новая запись - ищем следующую свободную строку
                        row_num = max_row + 1
                        max_row += 1
                        # Обновляем координаты для новых записей
                        if entry_id in result_coords:
                            result_coords[entry_id] = (row_num, sheet_name)

                    # Заполняем строку
                    row_color = entry.get("row_color")
                    fill = None
                    if row_color:
                        fill = PatternFill(start_color=row_color, end_color=row_color, fill_type="solid")

                    for field, col_mapping in mapping["columns"].items():
                        col = col_mapping.column
                        value = entry.get(field, "")

                        # Форматируем дату
                        if field == "date" and value and len(str(value)) == 10 and str(value)[4] == '-':
                            y, m, d = str(value).split('-')
                            value = f"{d}.{m}.{y}"

                        cell = sheet.cell(row=row_num, column=col, value=value)

                        # Применяем стили
                        if col_mapping.style.font:
                            cell.font = copy(col_mapping.style.font)
                        if col_mapping.style.border:
                            cell.border = copy(col_mapping.style.border)
                        if col_mapping.style.alignment:
                            cell.alignment = copy(col_mapping.style.alignment)
                        if col_mapping.style.number_format:
                            cell.number_format = col_mapping.style.number_format

                        # Применяем заливку для колонок коробок
                        if col in (7, 8, 9, 10, 11, 12):
                            if fill:
                                cell.fill = fill
                            else:
                                cell.fill = PatternFill(fill_type=None)

            wb.save(file_path)
            wb.close()
            wb = None

            return result_coords

        except Exception as e:
            raise Exception(f"Ошибка экспорта: {str(e)}")
        finally:
            if wb:
                try:
                    wb.close()
                except:
                    pass
            if os.path.exists(lock_file):
                try:
                    os.remove(lock_file)
                except:
                    pass
            import gc
            gc.collect()

    @staticmethod
    def export_entries(entries_by_sheet, template_path, output_path):
        """
        Экспортирует записи в Excel с сохранением структуры листов и цветов строк

        Args:
            entries_by_sheet: список кортежей [(имя_листа, [список_записей]), ...]
            template_path: путь к файлу-шаблону
            output_path: путь для сохранения результата

        Returns:
            int: количество экспортированных записей
        """
        wb = None
        try:
            # Копируем шаблон
            shutil.copy2(template_path, output_path)

            # Открываем копию
            wb = load_workbook(output_path)

            mapping = PACKAGING_EXCEL_MAPPING
            start_row = mapping["start_row"]

            total_exported = 0

            # Для каждой группы создаём свой лист
            for sheet_idx, (sheet_name, entries) in enumerate(entries_by_sheet):
                if not entries:
                    continue

                # Копируем структуру из листа-шаблона (который называется "Шаблон")
                ws = wb.copy_worksheet(wb['Шаблон'])
                ws.title = sheet_name[:31]

                # Заполняем данными
                for idx, entry in enumerate(entries):
                    row_num = start_row + idx

                    # Получаем цвет строки
                    row_color = entry.get("row_color")
                    fill = None
                    if row_color:
                        fill = PatternFill(start_color=row_color, end_color=row_color, fill_type="solid")

                    for field, col_map in mapping["columns"].items():
                        value = entry.get(field, "")

                        # Форматируем дату
                        if field == "date" and value and len(str(value)) == 10 and str(value)[4] == '-':
                            y, m, d = str(value).split('-')
                            value = f"{d}.{m}.{y}"

                        cell = ws.cell(row=row_num, column=col_map.column)

                        # Проверяем, не входит ли ячейка в объединённый диапазон
                        skip_cell = False
                        for merged_range in ws.merged_cells.ranges:
                            if cell.coordinate in merged_range:
                                skip_cell = True
                                break

                        if skip_cell:
                            continue

                        cell.value = value

                        # Применяем стили из маппинга
                        if col_map.style.font:
                            cell.font = copy(col_map.style.font)
                        if col_map.style.border:
                            cell.border = copy(col_map.style.border)
                        if col_map.style.alignment:
                            cell.alignment = copy(col_map.style.alignment)
                        if col_map.style.number_format:
                            cell.number_format = col_map.style.number_format

                        # Применяем заливку для всех колонок, если есть цвет строки
                        # Если нужно ограничить только колонками с коробками (7-12)
                        if fill and col_map.column in (7, 8, 9, 10, 11, 12):
                            cell.fill = fill

                total_exported += len(entries)

            # Сохраняем и закрываем
            wb.save(output_path)
            wb.close()
            wb = None

            # Принудительная сборка мусора для освобождения файла
            import gc
            gc.collect()

            return total_exported

        except Exception as e:
            print(f"Ошибка экспорта в Excel: {e}")
            return 0
        finally:
            # Гарантированное закрытие в случае ошибки
            if wb:
                try:
                    wb.close()
                except:
                    pass
