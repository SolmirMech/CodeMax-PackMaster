# core/packaging/packaging_manager.py
from core.packaging.packaging_data_manager import PackagingDataManager
from core.packaging.packaging_excel import PackagingExcel
import re


class PackagingManager:
    """Тонкая обёртка над БД + Excel"""

    def __init__(self, config_manager, coordinator=None):
        self.config = config_manager
        self.coordinator = coordinator
        self.data_manager = PackagingDataManager(config_manager, coordinator)

    # === Методы БД ===
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
    def import_from_excel(self, file_path):
        """
        Импорт из Excel с валидацией.
        В БД попадают ТОЛЬКО полностью валидные записи.

        Returns:
            tuple: (imported_count, errors_list)
        """
        # Получаем все записи из Excel (включая потенциально ошибочные)
        total_found, errors, all_entries = PackagingExcel.import_from_excel(file_path)

        if not all_entries:
            return 0, errors or ["Нет данных для импорта"]

        # Фильтруем только валидные записи
        valid_entries = []
        validation_errors = []

        for idx, entry in enumerate(all_entries, 1):
            entry_errors = self._validate_entry(entry)
            if entry_errors:
                validation_errors.append(f"Запись {idx}: {', '.join(entry_errors)}")
            else:
                valid_entries.append(entry)

        # Сохраняем только валидные
        imported = 0
        for entry in valid_entries:
            try:
                self.data_manager.add_entry(entry)
                imported += 1
            except Exception as e:
                validation_errors.append(f"Ошибка сохранения записи: {str(e)}")

        # Объединяем все ошибки
        all_errors = errors + validation_errors

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

    def export_unexported_to_excel(self, file_path, sheet_name="янв 26"):
        """
        Экспортирует все неэкспортированные записи в Excel.
        Возвращает количество экспортированных записей
        """
        # Получаем неэкспортированные записи
        entries = self.data_manager.get_unexported_entries()
        if not entries:
            return 0

        # Экспортируем
        exported_count = PackagingExcel.export_to_excel(file_path, entries, sheet_name)

        # Помечаем как экспортированные
        if exported_count > 0:
            entry_ids = [e['id'] for e in entries]
            self.data_manager.mark_as_exported(entry_ids)

        return exported_count