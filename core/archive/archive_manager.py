# core/archive/archive_manager.py
import os
from datetime import datetime

from openpyxl import load_workbook
from openpyxl.styles import Alignment

from core.excel_exporter.cell_mappers import CellMappingRegistry


# noinspection SpellCheckingInspection
class ArchiveManager:
    """Менеджер архива: поиск, восстановление, управление для всех цехов и режимов"""

    def __init__(self, config_manager=None, coordinator=None, exporter=None):
        self.config = config_manager
        self.coordinator = coordinator
        self._exporter = exporter
        self.workshop = "1"  # по умолчанию
        self.has_weight = True  # по умолчанию

        if coordinator and hasattr(coordinator, 'subscribe'):
            coordinator.subscribe(self.on_settings_changed)

        self.on_settings_changed()  # сразу получаем актуальные значения
        self.clean_old_archive_records(3)

    def clean_old_archive_records(self, max_age_years=3):
        """Удаляет записи старше указанного количества лет"""
        try:
            archive = self.config.get_pallet_archive()
            if not archive or "pallets" not in archive:
                return False

            now = datetime.now()
            original_count = len(archive["pallets"])
            archive["pallets"] = [
                pallet for pallet in archive["pallets"]
                if self._is_record_younger_than(pallet, max_age_years, now)
            ]
            new_count = len(archive["pallets"])

            if new_count < original_count:
                self.config.save_pallet_archive(archive)
                print(f"[INFO] Очистка архива: удалено {original_count - new_count} записей старше {max_age_years} лет")

            return True

        except Exception as e:
            print(f"[ERROR] Ошибка очистки архива: {e}")
            return False

    @staticmethod
    def _is_record_younger_than(record, max_age_years, now):
        """Проверяет, что запись не старше max_age_years"""
        extraction_date = record.get("extraction_date")
        if not extraction_date:
            return True

        try:
            record_date = datetime.strptime(extraction_date, "%Y-%m-%d %H:%M:%S")
            age = now - record_date
            return age.days < max_age_years * 365
        except:
            return True

    # noinspection PyUnusedLocal
    def on_settings_changed(self, context=None):
        """Один метод для обновления всех настроек из координатора"""
        if not self.coordinator:
            self.has_weight = False
            self.workshop = "1"
            return

        if hasattr(self.coordinator, 'get_workshop'):
            self.workshop = self.coordinator.get_workshop()

        if hasattr(self.coordinator, 'get_weight_status'):
            self.has_weight = self.coordinator.get_weight_status()

    def get_excel_path(self, workshop=None):
        """Получает путь к Excel файлу из настроек с учетом цеха"""
        if workshop is None and self.coordinator:
            workshop = self.coordinator.get_workshop()
        elif workshop is None:
            workshop = "1"

        settings = self.config.load_json_settings("shared_utils.json")
        excel_folder = settings.get("weight_orders_xlsx", "")

        if workshop == "2":
            filename = "weight_orders_2.xlsx"
        else:
            filename = "weight_orders.xlsx"

        return os.path.join(excel_folder, filename)

    @staticmethod
    def _get_sheet_info(workshop, enable_pallet, multitype_mode, has_weight=True):
        """Возвращает (имя_листа, тип_листа) на основе параметров"""
        if workshop == "1":
            if multitype_mode:
                return "Лист много видов", "multitype"
            elif enable_pallet:
                if has_weight:
                    return "Лист для паллеты", "pallet"
                else:
                    return "БезВеса", "noweight"  # ← исправлено: возвращаем правильный тип
            else:
                return "Лист для коробки", "box"
        else:  # workshop == "2"
            if multitype_mode:
                return "Много видов", "multitype"
            elif enable_pallet:
                return "Список поддонов", "pallet_list"
            else:
                return "Поддон", "box"

    def extract_data_for_archive(self, workshop=None, enable_pallet=False, multitype_mode=False):
        """
        Основной метод архивации с использованием маппингов
        """
        try:
            # Обновляем настройки через существующий метод
            self.on_settings_changed()

            # Определяем цех (если не передан, используем из обновлённых настроек)
            if workshop is None:
                workshop = self.workshop

            # Используем актуальный статус веса из self.has_weight
            has_weight = self.has_weight

            # Определяем путь к файлу
            excel_path = self.get_excel_path(workshop)
            if not os.path.exists(excel_path):
                return {"success": False, "error": f"Файл не найден: {excel_path}"}

            # Определяем лист и тип - передаём has_weight
            sheet_name, archive_type = self._get_sheet_info(workshop, enable_pallet, multitype_mode, has_weight)

            # Получаем маппинг
            mapping = CellMappingRegistry.get_mapping(workshop, archive_type)

            # Извлекаем данные через маппинг
            return self._extract_using_mapping(excel_path, mapping, has_weight)

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _extract_using_mapping(self, excel_path, mapping, has_weight=True):
        """Извлекает данные из Excel используя маппинг"""
        workbook = load_workbook(excel_path)
        sheet = workbook[mapping.sheet_name]

        # Статические поля
        basic_fields = {}
        for cell_mapping in mapping.static_cells:
            cell_addr = cell_mapping.cell_reference
            basic_fields[cell_addr] = sheet[cell_addr].value

        # Динамические секции
        dynamic_data = {}
        for section in mapping.dynamic_sections:
            dynamic_data[section.name] = self._extract_dynamic_section(sheet, section)

        # СПЕЦИАЛЬНАЯ ОБРАБОТКА ДЛЯ ЛИСТА БЕЗВЕСА
        if mapping.sheet_name == "БезВеса":
            # Добавляем номера коробок из колонок B, E, H
            box_numbers = {
                "left": [],
                "center": [],
                "right": []
            }

            # Собираем номера из колонки B
            for row in range(14, 29):
                val = sheet[f"B{row}"].value
                if val is not None:
                    box_numbers["left"].append({"row": row, "value": val})

            # Собираем номера из колонки E
            for row in range(14, 29):
                val = sheet[f"E{row}"].value
                if val is not None:
                    box_numbers["center"].append({"row": row, "value": val})

            # Собираем номера из колонки H
            for row in range(14, 29):
                val = sheet[f"H{row}"].value
                if val is not None:
                    box_numbers["right"].append({"row": row, "value": val})

            # Сохраняем в архив
            dynamic_data["box_numbers"] = box_numbers

        workbook.close()

        return {
            "success": True,
            "archive_data": {
                "workshop": mapping.workshop,
                "archive_type": self._get_type_from_mapping(mapping),
                "sheet_name": mapping.sheet_name,
                "basic_fields": basic_fields,
                "dynamic_data": dynamic_data,
                "has_weight": has_weight,
                "extraction_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }

    @staticmethod
    def _extract_dynamic_section(sheet, section):
        data = []

        for row_offset in range(section.rows_range[1] - section.rows_range[0] + 1):
            current_row = section.rows_range[0] + row_offset
            row_data = {}
            has_data = False

            # columns_config - это список словарей!
            for col_config in section.columns_config:
                col_letter = col_config["column"]
                data_key = col_config["data_key"]

                cell = f"{col_letter}{current_row}"
                value = sheet[cell].value

                if value is not None:
                    row_data[data_key] = value
                    row_data['_row'] = current_row
                    row_data['_cell'] = cell
                    has_data = True

            if has_data:
                data.append(row_data)

        return data

    # noinspection PyMethodMayBeStatic
    def _get_type_from_mapping(self, mapping):
        """Извлекает тип листа из маппинга"""
        if mapping.sheet_name == "БезВеса":
            return "noweight"
        elif mapping.sheet_name == "Лист для паллеты":
            return "pallet"
        elif mapping.sheet_name == "Лист для коробки":
            return "box"
        elif mapping.sheet_name == "Лист много видов":
            return "multitype"
        elif mapping.sheet_name == "Поддон":
            return "box"
        elif mapping.sheet_name == "Список поддонов":
            return "pallet_list"
        elif mapping.sheet_name == "Много видов":
            return "multitype"
        else:
            return "unknown"

    def restore_to_excel(self, archive_data, excel_path=None):
        """Восстанавливает данные из архива в Excel используя маппинг"""
        try:
            workshop = archive_data.get("workshop", "2")
            archive_type = archive_data.get("archive_type")
            sheet_name = archive_data.get("sheet_name")

            if not archive_type or not sheet_name:
                return {"success": False, "error": "Не указан тип архива или лист"}

            # Получаем маппинг
            mapping = CellMappingRegistry.get_mapping(workshop, archive_type)

            # Определяем путь к файлу, если не передан
            if excel_path is None:
                excel_path = self.get_excel_path(workshop)

            # Очистка перед восстановлением через экспортер
            if self._exporter:
                enable_pallet = (archive_type in ["pallet", "noweight", "pallet_list"])
                multitype_mode = (archive_type == "multitype")
                self._exporter.clear_all_rolls(enable_pallet, multitype_mode)

            # Восстанавливаем через маппинг
            return self._restore_using_mapping(archive_data, excel_path, mapping, workshop)

        except Exception as e:
            return {"success": False, "error": f"Ошибка восстановления: {str(e)}"}

    def _restore_using_mapping(self, archive_data, excel_path, mapping, workshop):
        """Восстанавливает данные используя маппинг"""
        try:
            workbook = load_workbook(excel_path)

            if mapping.sheet_name not in workbook.sheetnames:
                workbook.close()
                return {"success": False, "error": f"Лист '{mapping.sheet_name}' не найден"}

            sheet = workbook[mapping.sheet_name]

            # Создаём словарь маппингов по cell_reference для быстрого доступа
            mapping_by_cell = {cm.cell_reference: cm for cm in mapping.static_cells}

            # Восстанавливаем статические поля с форматированием
            basic_fields = archive_data.get("basic_fields", {})
            for cell_addr, value in basic_fields.items():
                if cell_addr and value is not None:
                    sheet[cell_addr] = value

                    # Применяем форматирование из маппинга
                    if cell_addr in mapping_by_cell:
                        cell_mapping = mapping_by_cell[cell_addr]
                        if cell_mapping.format.wrap_text:
                            sheet[cell_addr].alignment = Alignment(
                                wrap_text=True
                            )

            # Восстанавливаем динамические секции
            dynamic_data = archive_data.get("dynamic_data", {})

            # Специальное восстановление для листа БезВеса
            if mapping.sheet_name == "БезВеса" and "box_numbers" in dynamic_data:
                box_numbers = dynamic_data["box_numbers"]

                # Восстанавливаем левые номера (B)
                for item in box_numbers.get("left", []):
                    row = item.get("row")
                    if row:
                        sheet[f"B{row}"] = item.get("value")

                # Восстанавливаем центральные номера (E)
                for item in box_numbers.get("center", []):
                    row = item.get("row")
                    if row:
                        sheet[f"E{row}"] = item.get("value")

                # Восстанавливаем правые номера (H)
                for item in box_numbers.get("right", []):
                    row = item.get("row")
                    if row:
                        sheet[f"H{row}"] = item.get("value")

            # Восстанавливаем обычные динамические секции
            sections_by_name = {section.name: section for section in mapping.dynamic_sections}
            for section_name, section_data in dynamic_data.items():
                if section_name in sections_by_name and section_name != "box_numbers":
                    section = sections_by_name[section_name]
                    self._restore_dynamic_section(sheet, section, section_data)

            workbook.save(excel_path)
            workbook.close()

            # Формируем результат
            if workshop == "1":
                order_num = basic_fields.get("E9" if mapping.sheet_name == "БезВеса" else "D8", "неизвестно")
            else:
                order_num = basic_fields.get("D6", "неизвестно")

            result = {
                "success": True,
                "sheet_name": mapping.sheet_name,
                "order": order_num
            }

            if workshop == "2":
                pallet_num = basic_fields.get("D5", "неизвестно")
                result["pallet_number"] = pallet_num

            return result

        except Exception as e:
            return {"success": False, "error": f"Ошибка восстановления: {str(e)}"}

    @staticmethod
    def _restore_dynamic_section(sheet, section, section_data):
        """Восстанавливает данные в динамическую секцию"""
        for row_data in section_data:
            row = row_data.get('_row')
            if not row:
                continue

            # section.columns_config - это список словарей!
            for col_config in section.columns_config:
                col_letter = col_config["column"]
                data_key = col_config["data_key"]

                if data_key in row_data:
                    cell = f"{col_letter}{row}"
                    sheet[cell] = row_data[data_key]