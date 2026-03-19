# core/packaging/packaging_manager.py
from core.packaging.packaging_data_manager import PackagingDataManager
from core.packaging.packaging_excel import PackagingExcel
import re
import openpyxl


class PackagingManager:
    """Тонкая обёртка над БД + Excel"""

    def __init__(self, config_manager, coordinator=None):
        self.config = config_manager
        self.coordinator = coordinator
        self.data_manager = PackagingDataManager(config_manager, coordinator)

    # === Методы БД ===
    def get_restorable_entries(self):
        """Возвращает записи для восстановления"""
        return self.data_manager.get_restorable_entries()

    def mark_manual_as_restorable(self, entry_ids):
        """Помечает экспортированные ручные записи"""
        return self.data_manager.mark_manual_as_restorable(entry_ids)

    def get_recent_entries(self, limit=10):
        return self.data_manager.get_recent(limit)

    def search_entries(self, **filters):
        return self.data_manager.search(filters)

    def update_cell(self, entry_id, column, value):
        return self.data_manager.update_entry(entry_id, column, value)

    def add_entry(self, data):
        return self.data_manager.add_entry(data)

    def delete_entry(self, entry_id):
        return self.data_manager.delete_entry(entry_id)

    def get_unexported_entries(self):
        return self.data_manager.get_unexported_entries()

    def mark_as_exported(self, entry_ids):
        return self.data_manager.mark_as_exported(entry_ids)

    # === Методы Excel ===
    # noinspection SpellCheckingInspection
    def import_from_excel(self, file_path, progress_callback=None, only_first_sheet=True):
        """
        Импорт из Excel с валидацией и прогрессом

        Args:
            file_path: путь к файлу
            progress_callback: функция для обновления прогресса
            only_first_sheet: если True - импорт только из первого листа

        Returns:
            tuple: (imported_count, errors_list)
        """
        imported = 0
        all_errors = []
        imported_ids = []

        # Получаем список листов для определения индексов
        wb = openpyxl.load_workbook(file_path, read_only=True)
        sheet_index_map = {name: idx for idx, name in enumerate(wb.sheetnames)}
        wb.close()

        def save_entry(entry, sheet_name):
            nonlocal imported, all_errors, imported_ids
            # Валидируем
            entry_errors = self._validate_entry(entry)
            if entry_errors:
                all_errors.append(f"Запись {imported + 1}: {', '.join(entry_errors)}")
                return

            # ВАЖНО: добавляем source_type и sheet_index
            entry['source_type'] = 'excel'
            entry['source_sheet'] = sheet_name
            entry['sheet_index'] = sheet_index_map.get(sheet_name, 0)  # сохраняем индекс листа

            # Сохраняем
            try:
                entry_id = self.data_manager.add_entry(entry)
                imported_ids.append(entry_id)
                imported += 1
            except Exception as e:
                all_errors.append(f"Ошибка сохранения записи: {str(e)}")

        # Запускаем импорт с callback'ами
        total_found, errors = PackagingExcel.import_from_excel(
            file_path,
            db_callback=save_entry,
            progress_callback=progress_callback,
            only_first_sheet=only_first_sheet
        )

        # Помечаем как экспортированные
        if imported_ids:
            self.data_manager.mark_as_exported(imported_ids)

        all_errors.extend(errors)
        return imported, all_errors

    @staticmethod
    def _validate_entry(entry):
        """
        Валидация одной записи.
        Возвращает список ошибок (пустой список = запись валидна)
        """
        errors = []

        # Обязательные поля (можно настроить)
        required_fields = ['order_number']  # Номер заказа обязателен
        for field in required_fields:
            if not entry.get(field):
                errors.append(f"отсутствует {field}")

        # Валидация даты (если есть)
        date_val = entry.get('date')
        if date_val:
            if not re.match(r'\d{4}-\d{2}-\d{2}', str(date_val)):
                errors.append(f"неверный формат даты: {date_val}")

        # Валидация чисел
        numeric_fields = ['quantity_labels', 'large_boxes', 'small_boxes', 'aquaLife_boxes']
        for field in numeric_fields:
            val = entry.get(field)
            if val is not None:
                try:
                    int_val = int(val)
                    if int_val < 0:
                        errors.append(f"{field} отрицательное значение")
                except (ValueError, TypeError):
                    errors.append(f"{field} не число: {val}")

        return errors

    def export_unexported_to_excel(self, file_path):
        """
        Экспортирует все неэкспортированные записи в Excel.
        Возвращает количество экспортированных записей
        """
        # Получаем неэкспортированные записи
        entries = self.data_manager.get_unexported_entries()
        if not entries:
            return 0

        # Экспортируем
        exported_count = PackagingExcel.export_to_excel(file_path, entries)

        # Помечаем как экспортированные
        if exported_count > 0:
            entry_ids = [e['id'] for e in entries]
            self.data_manager.mark_as_exported(entry_ids)

        return exported_count

    # noinspection PyIncorrectDocstring,PyUnusedLocal,PyMethodMayBeStatic
    def export_entries_to_excel(self, entries_by_sheet, template_path, output_path):
        """
        Экспортирует записи в Excel файл с сохранением структуры листов

        Args:
            entries_by_sheet: словарь {имя_листа: [список_записей]}
            template_path: путь к файлу-шаблону
            output_path: путь для сохранения результата

        Returns:
            int: количество экспортированных записей
        """
        return PackagingExcel.export_entries(entries_by_sheet, template_path, output_path)