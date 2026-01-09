# exporter_core.py
"""
Ядро системы экспорта в Excel.
Использует DataProvider для получения данных и CellMappers для маппинга.
Не зависит от конкретного UI или структуры файла.
"""
import os
from typing import Dict, Any, Optional, List, Tuple, Union
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter

from .data_provider import ExportDataProvider
from .cell_mappers import (
    SheetMapping, CellMapping, DynamicSection, DataType,
    HorizontalAlignment, VerticalAlignment, CellFormat
)


class ExcelExportError(Exception):
    """Базовое исключение для ошибок экспорта"""
    pass


class ExcelFileLockedError(ExcelExportError):
    """Файл заблокирован (открыт в Excel)"""
    pass


class SmartExporter:
    """
    Умный экспортер для работы с Excel.
    Использует DataProvider и CellMappers для декларативного экспорта.
    """
    
    def __init__(self, data_provider: ExportDataProvider, config_manager=None):
        """
        Инициализация экспортера.
        
        Args:
            data_provider: Провайдер данных
            config_manager: Менеджер конфигурации (опционально)
        """
        self.data_provider = data_provider
        self.config_manager = config_manager
        self.wb = None
        self.ws = None
        self.current_mapping: Optional[SheetMapping] = None
        
    # ==================== ОСНОВНЫЕ МЕТОДЫ ЭКСПОРТА ====================
    
    def export_to_sheet(self, file_path: str, mapping: SheetMapping, 
                       mode: str = "box", pallet_data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Основной метод экспорта в указанный лист.
        
        Args:
            file_path: Путь к файлу Excel
            mapping: Маппинг листа
            mode: Режим экспорта ('box', 'pallet', etc.)
            pallet_data: Данные поддона (только для режима pallet)
            
        Returns:
            Словарь с результатами экспорта
        """
        try:
            # Проверка файла
            self._validate_file(file_path)
            
            # Загрузка книги
            self.wb = load_workbook(file_path)
            
            # Проверка существования листа
            if mapping.sheet_name not in self.wb.sheetnames:
                raise ExcelExportError(f"Лист '{mapping.sheet_name}' не найден в файле")
            
            self.ws = self.wb[mapping.sheet_name]
            self.current_mapping = mapping
            
            # 1. Заполняем статические ячейки
            all_data = self.data_provider.collect_all_data()
            sheet_specific_data = self._prepare_sheet_data(all_data, mapping.workshop, mapping.sheet_name)
            
            self._fill_static_cells(mapping.static_cells, sheet_specific_data)
            
            # 2. Заполняем динамические секции
            all_fitted = True
            
            # Группируем секции по типу
            rolls_sections = [s for s in mapping.dynamic_sections if "rolls" in s.name]
            other_sections = [s for s in mapping.dynamic_sections if "rolls" not in s.name]
            
            # Заполняем ролики с распределением
            if rolls_sections:
                rolls_count = sheet_specific_data.get('rolls_count', 1)
                if rolls_count == 0:
                    rolls_count = 1
                all_fitted = self._fill_rolls_sections_with_distribution(
                    rolls_sections, sheet_specific_data, rolls_count
                ) and all_fitted
            
            # Заполняем остальные секции (если есть)
            for section in other_sections:
                section_fitted = self._fill_dynamic_section(
                    section, sheet_specific_data, mode, pallet_data
                )
                if not section_fitted:
                    all_fitted = False
            
            # 3. Выполняем пост-обработку
            self._run_post_processing_hooks(mapping.post_processing_hooks, sheet_specific_data)
            
            # 4. Сохраняем файл
            self.wb.save(file_path)
            
            return {
                'success': True,
                'all_fitted': all_fitted,
                'file_path': file_path,
                'sheet_name': mapping.sheet_name,
                'workshop': mapping.workshop
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'file_path': file_path,
                'sheet_name': mapping.sheet_name if mapping else 'Unknown'
            }
            
        finally:
            self._cleanup()
    
    def clear_sheet(self, file_path: str, mapping: SheetMapping) -> bool:
        """
        Очищает указанный лист.
        
        Args:
            file_path: Путь к файлу Excel
            mapping: Маппинг листа для очистки
            
        Returns:
            True если успешно, False если ошибка
        """
        try:
            # Проверка файла
            self._validate_file(file_path, check_lock=True)
            
            # Загрузка книги
            self.wb = load_workbook(file_path)
            
            # Проверка существования листа
            if mapping.sheet_name not in self.wb.sheetnames:
                print(f"Лист '{mapping.sheet_name}' не найден в файле")
                return False
            
            self.ws = self.wb[mapping.sheet_name]
            self.current_mapping = mapping
            
            # 1. Очищаем статические ячейки
            self._clear_static_cells(mapping.static_cells)
            
            # 2. Очищаем динамические секции
            for section in mapping.dynamic_sections:
                self._clear_dynamic_section(section)
            
            # 3. Сохраняем файл
            self.wb.save(file_path)
            
            return True
            
        except Exception as e:
            print(f"Ошибка очистки листа: {e}")
            return False
            
        finally:
            self._cleanup()
    
    # ==================== МЕТОДЫ ЗАПОЛНЕНИЯ ЯЧЕЕК ====================
    
    def _fill_static_cells(self, cell_mappings: List[CellMapping], data: Dict[str, Any]):
        """Заполняет статические ячейки согласно маппингу"""
        for cell_mapping in cell_mappings:
            try:
                # Получаем значение
                value = data.get(cell_mapping.data_key, cell_mapping.default_value)
                
                # Если значение None и ячейка обязательная - пропускаем с предупреждением
                if value is None and cell_mapping.required:
                    print(f"Внимание: отсутствует значение для обязательной ячейки {cell_mapping.cell_reference} "
                          f"(ключ: {cell_mapping.data_key})")
                    continue
                
                # Преобразуем значение согласно типу данных
                processed_value = self._process_value_by_type(value, cell_mapping.data_type)
                
                # Устанавливаем значение в ячейку
                self._set_cell_value(
                    cell_mapping.cell_reference, 
                    processed_value,
                    cell_mapping.format,
                    cell_mapping.is_merged_cell
                )
                
            except Exception as e:
                print(f"Ошибка заполнения ячейки {cell_mapping.cell_reference}: {e}")
                continue
    
    def _fill_rolls_sections_with_distribution(self, sections: List[DynamicSection], 
                                              data: Dict[str, Any], total_rolls: int) -> bool:
        """Распределяет ролики по секциям последовательно"""
        filled_count = 0
        
        for section in sections:
            if filled_count >= total_rolls:
                break
                
            # Сколько осталось заполнить
            rolls_left = total_rolls - filled_count
            filled_in_section = self._fill_single_rolls_section(section, data, rolls_left)
            filled_count += filled_in_section
        
        return filled_count >= total_rolls

    def _fill_single_rolls_section(self, section: DynamicSection, data: Dict[str, Any], max_rolls: int) -> int:
        """Заполняет одну секцию роликов, возвращает сколько заполнил"""
        try:
            # Данные одного ролика
            gross_weight = data.get('gross_weight_per_roll')
            net_weight = data.get('net_weight_per_roll')
            quantity = data.get('quantity_per_roll')
            
            start_row, end_row = section.rows_range
            filled_count = 0
            
            # Ищем пустые строки
            for row in range(start_row, end_row):
                if filled_count >= max_rolls:
                    break
                
                # Проверяем, пуста ли строка
                is_empty = True
                for col_config in section.columns_config:
                    cell_ref = f"{col_config['column']}{row}"
                    if self.ws[cell_ref].value is not None:
                        is_empty = False
                        break
                
                if is_empty:
                    # Заполняем строку
                    for col_config in section.columns_config:
                        cell_ref = f"{col_config['column']}{row}"
                        data_key = col_config['data_key']
                        
                        if data_key == 'gross_weight_per_roll':
                            value = gross_weight
                        elif data_key == 'net_weight_per_roll':
                            value = net_weight
                        elif data_key == 'quantity_per_roll':
                            value = quantity
                        else:
                            value = None
                        
                        if value is not None:
                            processed_value = self._process_value_by_type(value, col_config['data_type'])
                            self._set_cell_value(cell_ref, processed_value, col_config['format'])
                    
                    filled_count += 1
            
            return filled_count
                
        except Exception as e:
            print(f"Ошибка заполнения секции роликов '{section.name}': {e}")
            return 0

    def _fill_dynamic_section(self, section: DynamicSection, data: Dict[str, Any], 
                             mode: str, pallet_data: Optional[Dict]) -> bool:
        """Заполняет НЕ-роликовые секции"""
        # Только для НЕ-роликов
        if "rolls" in section.name:
            # Сюда не должны попадать ролики
            print(f"Внимание: секция '{section.name}' обрабатывается отдельно")
            return True
        
        # TODO: Логика для других типов секций (коробки, поддоны)
        print(f"Внимание: тип секции '{section.name}' не реализован")
        return True
    
    # ==================== МЕТОДЫ ОЧИСТКИ ====================
    
    def _clear_static_cells(self, cell_mappings: List[CellMapping]):
        """Очищает статические ячейки"""
        for cell_mapping in cell_mappings:
            try:
                self._set_cell_value(
                    cell_mapping.cell_reference,
                    None,
                    CellFormat()  # Сбрасываем форматирование
                )
            except Exception as e:
                print(f"Ошибка очистки ячейки {cell_mapping.cell_reference}: {e}")
                continue
    
    def _clear_dynamic_section(self, section: DynamicSection):
        """Очищает динамическую секцию"""
        start_row, end_row = section.rows_range
        
        for row in range(start_row, end_row):
            for col_config in section.columns_config:
                try:
                    cell_ref = f"{col_config['column']}{row}"
                    self._set_cell_value(cell_ref, None, CellFormat())
                except Exception as e:
                    print(f"Ошибка очистки ячейки {cell_ref}: {e}")
                    continue
    
    # ==================== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ====================
    
    def _prepare_sheet_data(self, all_data: Dict[str, Any], workshop: str, sheet_name: str) -> Dict[str, Any]:
        """
        Подготавливает данные для конкретного листа.
        Можно переопределить в дочерних классах для специфичной логики.
        """
        # Базовый вариант - возвращаем плоскую структуру данных
        sheet_data = {}
        
        # Собираем данные из всех категорий в плоский словарь
        for category, category_data in all_data.items():
            if isinstance(category_data, dict):
                sheet_data.update(category_data)
        
        # Добавляем метаданные
        sheet_data['workshop'] = workshop
        sheet_data['sheet_name'] = sheet_name
        
        return sheet_data
    
    def _run_post_processing_hooks(self, hooks: List[str], data: Dict[str, Any]):
        """Выполняет хуки пост-обработки"""
        for hook_name in hooks:
            try:
                method_name = f"_hook_{hook_name}"
                if hasattr(self, method_name):
                    getattr(self, method_name)(data)
                else:
                    print(f"Внимание: хук '{hook_name}' не найден")
            except Exception as e:
                print(f"Ошибка выполнения хука '{hook_name}': {e}")
    
    def _hook_update_manufacturer_info(self, data: Dict[str, Any]):
        """Хук для обновления информации о производителе"""
        # Эта логика уже реализована в _fill_static_cells через маппинг
        # Можно добавить дополнительную логику при необходимости
        pass
    
    def _hook_validate_rolls_count(self, data: Dict[str, Any]):
        """Хук для проверки количества роликов"""
        rolls_count = data.get('rolls_count', 0)
        max_rolls = 30  # Максимум для 1 цеха (15 слева + 15 справа)
        
        if rolls_count > max_rolls:
            print(f"Внимание: количество роликов ({rolls_count}) превышает максимальное ({max_rolls})")
    
    def _process_value_by_type(self, value: Any, data_type: DataType) -> Any:
        """Обрабатывает значение согласно типу данных"""
        if value is None:
            return None
        
        try:
            if data_type == DataType.INTEGER:
                if isinstance(value, (int, float)):
                    return int(value)
                elif isinstance(value, str):
                    try:
                        return int(float(value.replace(',', '.')))
                    except:
                        return value
            elif data_type == DataType.NUMBER:
                if isinstance(value, (int, float)):
                    return float(value)
                elif isinstance(value, str):
                    try:
                        return float(value.replace(',', '.'))
                    except:
                        return value
            elif data_type == DataType.DATE:
                # Дата уже должна быть в правильном формате
                return str(value)
            elif data_type == DataType.MULTILINE_TEXT:
                # Многострочный текст
                return str(value)
            elif data_type == DataType.TEXT:
                # Простой текст
                return str(value)
            elif data_type == DataType.FORMULA:
                # Формулы пока не поддерживаем
                return str(value)
            
            # По умолчанию возвращаем как есть
            return value
            
        except Exception as e:
            print(f"Ошибка обработки значения '{value}' как {data_type}: {e}")
            return value
    
    def _set_cell_value(self, cell_ref: str, value: Any, 
                       format_spec: Optional[CellFormat] = None,
                       is_merged_cell: bool = False):
        """
        Устанавливает значение в ячейку с форматированием.
        Обрабатывает объединенные ячейки.
        """
        try:
            if is_merged_cell:
                # Для объединенных ячеек находим первую ячейку диапазона
                target_cell = self._get_merged_cell_target(cell_ref)
            else:
                target_cell = self.ws[cell_ref]
            
            # Устанавливаем значение
            target_cell.value = value
            
            # Применяем форматирование
            if format_spec:
                alignment = Alignment(
                    horizontal=format_spec.horizontal_alignment.value,
                    vertical=format_spec.vertical_alignment.value,
                    wrap_text=format_spec.wrap_text
                )
                target_cell.alignment = alignment
                
                if format_spec.number_format:
                    target_cell.number_format = format_spec.number_format
                
                if format_spec.bold or format_spec.font_size:
                    font = Font(
                        bold=format_spec.bold,
                        size=format_spec.font_size
                    ) if format_spec.font_size else Font(bold=format_spec.bold)
                    target_cell.font = font
            else:
                # Сбрасываем форматирование
                target_cell.alignment = Alignment(
                    horizontal='general',
                    vertical='center',
                    wrap_text=False
                )
                
        except Exception as e:
            print(f"Ошибка установки значения в ячейку {cell_ref}: {e}")
            raise
    
    def _get_merged_cell_target(self, cell_ref: str):
        """Находит целевую ячейку для объединенного диапазона"""
        cell = self.ws[cell_ref]
        
        # Проверяем, находится ли ячейка в объединенном диапазоне
        for merged_range in self.ws.merged_cells.ranges:
            if cell.coordinate in merged_range:
                # Возвращаем первую ячейку объединенного диапазона
                return self.ws[merged_range.min_row][merged_range.min_col - 1]
        
        # Если не объединенная - возвращаем как есть
        return cell
    
    def _validate_file(self, file_path: str, check_lock: bool = True):
        """Проверяет файл перед работой с ним"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Файл не найден: {file_path}")
        
        if check_lock and self._is_file_locked(file_path):
            raise ExcelFileLockedError(f"Файл {file_path} открыт в Excel. Закройте его и попробуйте снова.")
    
    def _is_file_locked(self, filepath: str) -> bool:
        """Проверяет, открыт ли файл в другом процессе"""
        try:
            with open(filepath, 'a', encoding='utf-8'):
                pass
            return False
        except (IOError, PermissionError):
            return True
        except Exception:
            return False
    
    def _cleanup(self):
        """Очистка ресурсов"""
        if self.wb:
            try:
                self.wb.close()
            except:
                pass
        self.wb = None
        self.ws = None
        self.current_mapping = None


# ==================== ФАБРИКА И АДАПТЕРЫ ====================

class ExporterFactory:
    """Фабрика для создания экспортеров по параметрам"""
    
    @staticmethod
    def create_exporter(workshop: str, sheet_type: str, roll_module, config_manager=None):
        """
        Создает экспортер для указанных параметров.
        
        Args:
            workshop: "1" или "2"
            sheet_type: Тип листа
            roll_module: UI модуль с данными
            config_manager: Менеджер конфигурации
            
        Returns:
            Настроенный SmartExporter
        """
        # Создаем провайдер данных
        data_provider = ExportDataProvider(roll_module, config_manager)
        
        # Создаем экспортер
        exporter = SmartExporter(data_provider, config_manager)
        
        return exporter


class LegacyExporterAdapter:
    """
    Адаптер для обратной совместимости со старым кодом.
    Позволяет постепенно мигрировать на новую архитектуру.
    """
    
    def __init__(self, excel_file_path, roll_module, preview_module, coordinator=None):
        self.original_excel_path = excel_file_path
        self.roll_module = roll_module
        self.coordinator = coordinator
        
        # Создаем провайдер и экспортер новой архитектуры
        self.data_provider = ExportDataProvider(roll_module)
        self.exporter = SmartExporter(self.data_provider)
    
    def export_data(self, enable_pallet=False, pallet_data=None, multitype_mode=False):
        """
        Интерфейс, совместимый со старым WeightOrdersExporter.export_data
        """
        # TODO: Полная реализация с поддержкой всех режимов
        # Пока демонстрация для цеха 1, коробка
        
        # Определяем цех (упрощенно)
        workshop = "1"  # По умолчанию 1 цех
        
        # Определяем тип листа
        if multitype_mode:
            sheet_type = "multitype"
        elif enable_pallet:
            sheet_type = "pallet"
        else:
            sheet_type = "box"
        
        # Получаем маппинг
        try:
            from cell_mappers import get_mapping
            mapping = get_mapping(workshop, sheet_type, "box" if not enable_pallet else "pallet")
        except ValueError:
            # Если маппинг не найден, используем fallback
            return self._legacy_fallback_export(enable_pallet, pallet_data, multitype_mode)
        
        # Получаем путь к файлу
        file_path = self._get_excel_file_path(workshop)
        
        # Выполняем экспорт
        result = self.exporter.export_to_sheet(
            file_path=file_path,
            mapping=mapping,
            mode="pallet" if enable_pallet else "box",
            pallet_data=pallet_data
        )
        
        # Отправляем уведомление через координатор
        if result['success'] and self.coordinator and hasattr(self.coordinator, 'notify'):
            self.coordinator.notify("excel_exported", {
                'file_path': result['file_path'],
                'sheet_name': result['sheet_name'],
                'enable_pallet': enable_pallet,
                'multitype_mode': multitype_mode,
                'workshop': workshop
            })
        
        return result
    
    def clear_all_rolls(self, enable_pallet=False, multitype_mode=False):
        """Очистка листа (обратная совместимость)"""
        # Аналогичная логика определения параметров
        workshop = "1"
        
        if multitype_mode:
            sheet_type = "multitype"
        elif enable_pallet:
            sheet_type = "pallet"
        else:
            sheet_type = "box"
        
        try:
            from cell_mappers import get_mapping
            mapping = get_mapping(workshop, sheet_type, "box" if not enable_pallet else "pallet")
        except ValueError:
            return self._legacy_fallback_clear(enable_pallet, multitype_mode)
        
        file_path = self._get_excel_file_path(workshop)
        
        success = self.exporter.clear_sheet(file_path, mapping)
        
        if success and self.coordinator and hasattr(self.coordinator, 'notify'):
            self.coordinator.notify("excel_cleared", {
                'file_path': file_path,
                'enable_pallet': enable_pallet,
                'multitype_mode': multitype_mode,
                'workshop': workshop
            })
        
        return success
    
    def _get_excel_file_path(self, workshop: str) -> str:
        """Определяет путь к файлу Excel (упрощенно)"""
        # TODO: Полная реализация с учетом настроек и координатора
        import os
        if workshop == "1":
            filename = "weight_orders.xlsx"
        else:
            filename = "weight_orders_2.xlsx"
        
        # Пока возвращаем путь рядом с оригинальным файлом
        return os.path.join(os.path.dirname(self.original_excel_path), filename)
    
    def _legacy_fallback_export(self, *args, **kwargs):
        """Fallback на старую реализацию, если новая не поддерживается"""
        print("Используется fallback на старую реализацию")
        # TODO: Здесь можно вызвать старый WeightOrdersExporter
        return {'success': False, 'error': 'Режим не поддерживается в новой архитектуре'}
    
    def _legacy_fallback_clear(self, *args, **kwargs):
        """Fallback на старую очистку"""
        print("Используется fallback на старую очистку")
        return False