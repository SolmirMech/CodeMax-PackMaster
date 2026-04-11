# core/packing_list/packing_list_excel.py

from copy import copy

from openpyxl import load_workbook

from core.packing_list import packing_list_mapping as mapping


class PackingListExcel:
    """Работа с Excel для упаковочного листа Экосистема"""

    @staticmethod
    def fill_template(work_path, header_data, places_data, items_data):
        """
        Открывает копию шаблона, заполняет данными, сохраняет.

        Args:
            work_path: путь к копии шаблона
            header_data: dict с полями шапки
            places_data: list[dict] — данные таблицы мест (до 5 строк)
            items_data: list[dict] — данные таблицы товаров (до 5 строк)
        """
        wb = None
        try:
            wb = load_workbook(work_path)
            sheet = wb["Экосистема"]

            # 1. Заполняем шапку (фиксированные ячейки)
            for field, cell_info in mapping.HEADER_MAPPING.items():
                cell = sheet[cell_info["cell"]]
                value = header_data.get(field, "")
                if value is not None:
                    cell.value = value

                # Применяем стили
                style = cell_info.get("style", {})
                if style.get("font"):
                    cell.font = copy(style["font"])
                if style.get("border"):
                    cell.border = copy(style["border"])
                if style.get("alignment"):
                    cell.alignment = copy(style["alignment"])

            # 2. Заполняем таблицу мест (строки 13-17)
            for i, place in enumerate(places_data):
                if i >= 5:  # ограничиваем 5 строками
                    break
                row = mapping.PLACES_START_ROW + i

                for field, col_info in mapping.PLACES_COLUMNS.items():
                    cell = sheet.cell(row=row, column=col_info["col"])
                    value = place.get(field, "")
                    if value is not None:
                        cell.value = value

                    # Применяем стиль таблицы
                    cell.font = copy(mapping.TABLE_CELL_STYLE["font"])
                    cell.border = copy(mapping.TABLE_CELL_STYLE["border"])
                    cell.alignment = copy(mapping.TABLE_CELL_STYLE["alignment"])

            # 3. Заполняем таблицу товаров (строки 24-28)
            for i, item in enumerate(items_data):
                if i >= 5:  # ограничиваем 5 строками
                    break
                row = mapping.ITEMS_START_ROW + i

                for field, col_info in mapping.ITEMS_COLUMNS.items():
                    cell = sheet.cell(row=row, column=col_info["col"])
                    value = item.get(field, "")
                    if value is not None:
                        cell.value = value

                    # Применяем стиль таблицы
                    cell.font = copy(mapping.TABLE_CELL_STYLE["font"])
                    cell.border = copy(mapping.TABLE_CELL_STYLE["border"])
                    cell.alignment = copy(mapping.TABLE_CELL_STYLE["alignment"])

            wb.save(work_path)

        except Exception as e:
            raise Exception(f"Ошибка заполнения шаблона: {str(e)}")
        finally:
            if wb:
                try:
                    wb.close()
                except:
                    pass
            import gc
            gc.collect()