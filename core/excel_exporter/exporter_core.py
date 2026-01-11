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

            # ТОЛЬКО для БезВеса
            if mapping.sheet_name == "БезВеса":
                boxes_count = sheet_specific_data.get('boxes_count', 1)
                if boxes_count == 0:
                    boxes_count = 1
                boxes_fitted = self._fill_quantity_sections_with_distribution(
                    mapping.dynamic_sections, sheet_specific_data, boxes_count
                )
                all_fitted = boxes_fitted

            # Для всех остальных листов
            else:
                # Группируем секции по типу
                boxes_sections = [s for s in mapping.dynamic_sections if "boxes" in s.name]
                rolls_sections = [s for s in mapping.dynamic_sections if "rolls" in s.name]
                other_sections = [s for s in mapping.dynamic_sections if "boxes" not in s.name and "rolls" not in s.name]
                
                # Заполняем коробки (для поддона)
                if boxes_sections:
                    boxes_count = sheet_specific_data.get('boxes_count', 1)
                    if boxes_count == 0:
                        boxes_count = 1
                    boxes_fitted = self._fill_boxes_sections_with_distribution(
                        boxes_sections, sheet_specific_data, boxes_count
                    )
                    all_fitted = boxes_fitted and all_fitted
                
                # Заполняем ролики (для коробки)
                if rolls_sections:
                    rolls_count = sheet_specific_data.get('rolls_count', 1)
                    if rolls_count == 0:
                        rolls_count = 1
                    rolls_fitted = self._fill_rolls_sections_with_distribution(
                        rolls_sections, sheet_specific_data, rolls_count
                    )
                    all_fitted = rolls_fitted and all_fitted
                
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
            if mapping.sheet_name == "БезВеса":
                # Очистка для БезВеса: и ячейки с количеством, и номера
                for section in mapping.dynamic_sections:
                    self._clear_noweight_section_with_numbers(section)
            else:
                # Обычная очистка для других листов
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
            
    def _fill_boxes_sections_with_distribution(self, sections: List[DynamicSection], 
                                              data: Dict[str, Any], total_boxes: int) -> bool:
        """Распределяет коробки по секциям последовательно (логика как для роликов)"""
        filled_count = 0
        
        for section in sections:
            if filled_count >= total_boxes:
                break
                
            # Сколько осталось заполнить
            boxes_left = total_boxes - filled_count
            filled_in_section = self._fill_boxes_section(section, data, boxes_left)
            filled_count += filled_in_section
        
        return filled_count >= total_boxes

    def _fill_boxes_section(self, section: DynamicSection, data: Dict[str, Any], max_boxes: int) -> int:
        """Заполняет одну секцию коробок, возвращает сколько заполнил"""
        try:
            # Данные одной коробки
            gross_weight = data.get('gross_weight_per_box')
            net_weight = data.get('net_weight_per_box')
            quantity = data.get('quantity_per_box')
            
            # Если данных нет - пропускаем
            if gross_weight is None and net_weight is None and quantity is None:
                return 0
            
            start_row, end_row = section.rows_range
            filled_count = 0
            
            # Ищем пустые строки
            for row in range(start_row, end_row):
                if filled_count >= max_boxes:
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
                        
                        # Сопоставляем ключи данных
                        if data_key == 'gross_weight_per_box':
                            value = gross_weight
                        elif data_key == 'net_weight_per_box':
                            value = net_weight
                        elif data_key == 'quantity_per_box':
                            value = quantity
                        else:
                            value = None
                        
                        if value is not None:
                            processed_value = self._process_value_by_type(value, col_config['data_type'])
                            self._set_cell_value(cell_ref, processed_value, col_config['format'])
                    
                    filled_count += 1
            
            return filled_count
                
        except Exception as e:
            print(f"Ошибка заполнения секции коробок '{section.name}': {e}")
            return 0
            
    def _fill_quantity_sections_with_distribution(self, sections: List[DynamicSection], 
                                                data: Dict[str, Any], total_boxes: int) -> bool:
        """Распределяет количество по 3 секциям для листа БезВеса"""
        
        filled_count = 0
        
        for i, section in enumerate(sections):
            if filled_count >= total_boxes:
                break
                
            # Сколько осталось заполнить
            boxes_left = total_boxes - filled_count
            filled_in_section = self._fill_quantity_section(section, data, boxes_left)
            filled_count += filled_in_section
        
        return filled_count >= total_boxes

    def _fill_quantity_section(self, section: DynamicSection, data: Dict[str, Any], max_boxes: int) -> int:
        """Заполняет одну секцию количества для листа БезВеса"""
        try:
            # Только количество
            quantity = data.get('quantity_per_box')
            
            # Если данных нет - пропускаем
            if quantity is None:
                return 0
            
            start_row, end_row = section.rows_range
            filled_count = 0
            
            # Ищем пустые строки
            for row in range(start_row, end_row):
                if filled_count >= max_boxes:
                    break
                
                # Проверяем, пуста ли строка (ТА ЖЕ ЛОГИКА)
                is_empty = True
                for col_config in section.columns_config:
                    cell_ref = f"{col_config['column']}{row}"
                    if self.ws[cell_ref].value is not None:
                        is_empty = False
                        break
                
                if is_empty:
                    # Заполняем строку (ПРОЩЕ - только quantity_per_box)
                    for col_config in section.columns_config:
                        cell_ref = f"{col_config['column']}{row}"
                        data_key = col_config['data_key']
                        
                        # В БезВеса только quantity_per_box
                        value = quantity if data_key == 'quantity_per_box' else None
                        
                        if value is not None:
                            processed_value = self._process_value_by_type(value, col_config['data_type'])
                            self._set_cell_value(cell_ref, processed_value, col_config['format'])
                    
                    filled_count += 1
            
            return filled_count
                
        except Exception as e:
            print(f"Ошибка заполнения секции количества '{section.name}': {e}")
            return 0

    
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
                    
    def _clear_noweight_section_with_numbers(self, section: DynamicSection):
        """Очищает секцию в БезВеса вместе с номерами"""
        start_row, end_row = section.rows_range
        
        for row in range(start_row, end_row):
            for col_config in section.columns_config:
                try:
                    # 1. Очищаем ячейку с количеством (C/F/I)
                    quantity_col = col_config['column']  # C, F, I
                    quantity_cell = f"{quantity_col}{row}"
                    self._set_cell_value(quantity_cell, None, CellFormat())
                    
                    # 2. Очищаем соседнюю ячейку с номером
                    number_col = chr(ord(quantity_col) - 1)  # C→B, F→E, I→H
                    number_cell = f"{number_col}{row}"
                    self._set_cell_value(number_cell, None, CellFormat())
                    
                except Exception as e:
                    print(f"Не удалось очистить ячейку в БезВеса {row}: {e}")
    
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
        
        # Специальная обработка для производителя
        if 'manufacturer' in all_data and isinstance(all_data['manufacturer'], dict):
            manufacturer_data = all_data['manufacturer']
            
            # Переносим display_text под нужным ключом
            if 'display_text' in manufacturer_data:
                sheet_data['manufacturer_display_text'] = manufacturer_data['display_text']
            
            # Также добавляем другие поля производителя
            sheet_data['manufacturer_name'] = manufacturer_data.get('manufacturer_name', '')
            sheet_data['show_manufacturer'] = manufacturer_data.get('show_manufacturer', True)
        
        # Добавляем метаданные
        sheet_data['workshop'] = workshop
        sheet_data['sheet_name'] = sheet_name
        
        # Для поддона используем специализированный метод DataProvider
        if sheet_name == "Лист для паллеты" or "паллет" in sheet_name.lower():
            sheet_data = {**sheet_data, **self.data_provider.get_data_for_workshop1_pallet()}
            
        # Для БезВеса используем специализированный метод DataProvider
        if sheet_name == "БезВеса":
            sheet_data = {**sheet_data, **self.data_provider.get_data_for_workshop1_noweight()}
        
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
            
    def _hook_validate_boxes_count(self, data: Dict[str, Any]):
        """Хук для проверки количества коробок"""
        boxes_count = data.get('boxes_count', 0)
        max_boxes = 30  # Максимум для 1 цеха (15 слева + 15 справа)
        
        if boxes_count > max_boxes:
            print(f"Внимание: количество коробок ({boxes_count}) превышает максимальное ({max_boxes})")
            
    def _hook_validate_boxes_count_noweight(self, data: Dict[str, Any]):
        """Хук для проверки количества коробок в листе БезВеса"""
        boxes_count = data.get('boxes_count', 0)
        max_boxes = 45  # Максимум для БезВеса (15 слева + 15 центр + 15 справа)
        
        if boxes_count > max_boxes:
            print(f"Внимание: количество коробок ({boxes_count}) превышает максимальное ({max_boxes}) для листа БезВеса")
            
    def _hook_fill_box_numbers(self, data: Dict[str, Any]):
        """Заполняет номера коробок в листе БезВеса"""
        if self.current_mapping.sheet_name != "БезВеса":
            return
        
        boxes_count = data.get('boxes_count', 0)
        
        # Считаем сколько номеров уже заполнено
        last_number = 0
        
        # Проверяем левые номера (B14-B28)
        for i in range(14, 29):
            value = self.ws[f"B{i}"].value
            if value is not None:
                last_number = max(last_number, int(value))
        
        # Проверяем центральные номера (E14-E28)
        for i in range(14, 29):
            value = self.ws[f"E{i}"].value
            if value is not None:
                last_number = max(last_number, int(value))
        
        # Проверяем правые номера (H14-H28)
        for i in range(14, 29):
            value = self.ws[f"H{i}"].value
            if value is not None:
                last_number = max(last_number, int(value))
        
        # Теперь заполняем пропущенные номера
        current_number = last_number + 1
        boxes_filled = 0
        
        # Левые номера (B14-B28)
        for i in range(14, 29):
            if boxes_filled >= boxes_count:
                break
            if self.ws[f"B{i}"].value is None:
                self._set_cell_value(f"B{i}", current_number, CellFormat(horizontal_alignment=HorizontalAlignment.CENTER))
                current_number += 1
                boxes_filled += 1
        
        # Центральные номера (E14-E28)
        for i in range(14, 29):
            if boxes_filled >= boxes_count:
                break
            if self.ws[f"E{i}"].value is None:
                self._set_cell_value(f"E{i}", current_number, CellFormat(horizontal_alignment=HorizontalAlignment.CENTER))
                current_number += 1
                boxes_filled += 1
        
        # Правые номера (H14-H28)
        for i in range(14, 29):
            if boxes_filled >= boxes_count:
                break
            if self.ws[f"H{i}"].value is None:
                self._set_cell_value(f"H{i}", current_number, CellFormat(horizontal_alignment=HorizontalAlignment.CENTER))
                current_number += 1
                boxes_filled += 1
    
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


