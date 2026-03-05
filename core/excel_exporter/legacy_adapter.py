# core/excel_exporter/legacy_adapter.py
"""
Адаптер для обратной совместимости со старым кодом.
Позволяет постепенно мигрировать на новую архитектуру.
"""

from .cell_mappers import CellMappingRegistry
from .data_provider import ExportDataProvider
from .exporter_core import SmartExporter


# noinspection SpellCheckingInspection
class LegacyExporterAdapter:
    """
    Адаптер, имитирующий старый WeightOrdersExporter.
    """
    
    def __init__(self, excel_file_path, roll_module, preview_module, coordinator=None, config_manager=None):
        self.workshop = None
        self.original_excel_path = excel_file_path
        self.roll_module = roll_module
        self.preview_module = preview_module
        self.coordinator = coordinator
        self.config_manager = config_manager
        self.has_weight = False
        if coordinator and hasattr(coordinator, 'subscribe'):
            # Подписываемся на уведомления координатора
            coordinator.subscribe(self.on_settings_changed)        
        
        # Создаем провайдер и экспортер новой архитектуры
        self.data_provider = ExportDataProvider(
            roll_module, 
            self.config_manager,
            excel_file_path=self.original_excel_path,  # ← передаем excel_file_path
            coordinator=self.coordinator
        )
        self.exporter = SmartExporter(self.data_provider, self.config_manager)
        
        # Внутреннее состояние
        self.wb = None
        self.ws = None
    
    @staticmethod
    def create_exporter(excel_file_path, roll_module, preview_module, coordinator=None, config_manager=None):
        """
        Фабричный метод - полная совместимость со старым конструктором.
        Просто создает экземпляр LegacyExporterAdapter.
        """
        return LegacyExporterAdapter(excel_file_path, roll_module, preview_module, coordinator, config_manager)

    def export_data(self, enable_pallet=False, multitype_mode=False):
        """
        Интерфейс, совместимый со старым WeightOrdersExporter.export_data
        Теперь с поддержкой нового листа 'ПоддонРолики' для цеха 1.

        Args:
            enable_pallet: Флаг режима поддона (True - паллета/без веса, False - коробка)
            multitype_mode: Флаг режима "Много видов"

        Returns:
            Dict с результатом экспорта
        """
        # Обновляем настройки из координатора
        self.on_settings_changed()
        workshop = getattr(self, 'workshop', '1')

        # ========== ЛОГИКА ОПРЕДЕЛЕНИЯ ТИПА ЛИСТА ==========
        # Приоритет: цех 2 > multitype_mode > enable_pallet > box

        # Для цеха 2 с поддонами всегда используем "pallet_list"
        if workshop == "2" and enable_pallet:
            sheet_type = "pallet_list"
            mode = "pallet"

        # Режим "Много видов" (приоритет для обоих цехов)
        elif multitype_mode:
            # Для цеха 1 проверяем наличие веса
            if workshop == "1" and not self.has_weight:
                # НЕТ ВЕСА → используем лист "Много видов БезВеса"
                sheet_type = "multitype_noweight"
                mode = "noweight"
            else:
                # Есть вес или цех 2 → стандартный мультитайп
                sheet_type = "multitype"
                mode = "box" if not enable_pallet else ("pallet" if self.has_weight else "noweight")

        # Режим поддона (только для цеха 1, цех 2 уже отловлен выше)
        elif enable_pallet:
            # Автоматический выбор на основе веса
            if self.has_weight:
                sheet_type = "pallet"  # Лист для паллеты (с весом)
                mode = "pallet"
            else:
                sheet_type = "noweight"  # Лист БезВеса (без веса)
                mode = "noweight"

        # Обычный режим коробки
        else:
            # +++ ИЗМЕНЕНИЕ: для цеха 1 без веса используем новый лист "ПоддонРолики" +++
            if workshop == "1" and not self.has_weight:
                sheet_type = "box_noweight"
                mode = "box_noweight"
            else:
                sheet_type = "box"
                mode = "box"

        # ========== ПОЛУЧЕНИЕ МАППИНГА ==========
        try:
            mapping = CellMappingRegistry.get_mapping(workshop, sheet_type, mode)
        except ValueError as e:
            return {'success': False, 'error': str(e)}

        # ========== ВЫПОЛНЕНИЕ ЭКСПОРТА ==========
        file_path = self.data_provider.get_excel_file_path(workshop, has_weight=self.has_weight)

        try:
            result = self.exporter.export_to_sheet(
                file_path=file_path,
                mapping=mapping,
                mode=mode
            )

            # Отправляем уведомление через координатор
            if result['success'] and self.coordinator and hasattr(self.coordinator, 'notify'):
                self.coordinator.notify("excel_exported", {
                    'file_path': result['file_path'],
                    'sheet_name': result['sheet_name'],
                    'enable_pallet': enable_pallet,
                    'multitype_mode': multitype_mode,
                    'workshop': workshop,
                    'has_weight': self.has_weight,
                    'sheet_type': sheet_type
                })

            return result

        except Exception as e:
            print(f"Ошибка в новом экспортере: {e}")
            return {'success': False, 'error': str(e)}

    def clear_all_rolls(self, enable_pallet=False, multitype_mode=False):
        """
        Очистка листа (обратная совместимость со старым WeightOrdersExporter)
        Теперь с поддержкой нового листа 'ПоддонРолики' для цеха 1.

        Args:
            enable_pallet: Флаг режима поддона
            multitype_mode: Флаг режима "Много видов"

        Returns:
            bool: True если очистка успешна, иначе False
        """
        try:
            # Обновляем настройки из координатора
            self.on_settings_changed()
            workshop = getattr(self, 'workshop', '1')

            # ========== ЛОГИКА ОПРЕДЕЛЕНИЯ ТИПА ЛИСТА ==========
            # (полностью идентична export_data)

            # Для цеха 2 с поддонами всегда используем "pallet_list"
            if workshop == "2" and enable_pallet:
                sheet_type = "pallet_list"
                mode = "pallet"

            # Режим "Много видов" (приоритет для обоих цехов)
            elif multitype_mode:
                # Для цеха 1 проверяем наличие веса
                if workshop == "1" and not self.has_weight:
                    # НЕТ ВЕСА → очищаем лист "Много видов БезВеса"
                    sheet_type = "multitype_noweight"
                    mode = "noweight"
                else:
                    # Есть вес или цех 2 → стандартный мультитайп
                    sheet_type = "multitype"
                    mode = "box"

            # Режим поддона (только для цеха 1, цех 2 уже отловлен выше)
            elif enable_pallet:
                if self.has_weight:
                    sheet_type = "pallet"  # Лист для паллеты (с весом)
                    mode = "pallet"
                else:
                    sheet_type = "noweight"  # Лист БезВеса (без веса)
                    mode = "noweight"

            # Обычный режим коробки
            else:
                # +++ ИЗМЕНЕНИЕ: для цеха 1 без веса очищаем новый лист "ПоддонРолики" +++
                if workshop == "1" and not self.has_weight:
                    sheet_type = "box_noweight"
                    mode = "box_noweight"
                else:
                    sheet_type = "box"
                    mode = "box"

            # ========== ПОЛУЧЕНИЕ МАППИНГА И ОЧИСТКА ==========
            try:
                mapping = CellMappingRegistry.get_mapping(workshop, sheet_type, mode)
                file_path = self.data_provider.get_excel_file_path(workshop, has_weight=self.has_weight)

                success = self.exporter.clear_sheet(file_path, mapping)

                # Отправляем уведомление через координатор
                if success and self.coordinator and hasattr(self.coordinator, 'notify'):
                    self.coordinator.notify("excel_cleared", {
                        'file_path': file_path,
                        'enable_pallet': enable_pallet,
                        'multitype_mode': multitype_mode,
                        'workshop': workshop,
                        'has_weight': self.has_weight,
                        'sheet_type': sheet_type
                    })

                return success

            except ValueError as e:
                print(f"Маппинг не найден для очистки: {e}")
                return False

        except Exception as e:
            print(f"Ошибка в новом очистителе: {e}")
            return False

    # noinspection PyUnusedLocal
    def on_settings_changed(self, context=None):
        """Один метод для обновления всех настроек из координатора"""
        if hasattr(self.coordinator, 'get_workshop'):
            self.workshop = self.coordinator.get_workshop()
        
        if hasattr(self.coordinator, 'get_weight_status'):
            self.has_weight = self.coordinator.get_weight_status()
