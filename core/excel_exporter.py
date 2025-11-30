import tkinter as tk
import os
from openpyxl import load_workbook
from openpyxl.styles import Alignment

class WeightOrdersExporter:
    """Экспортер данных в Excel файл для весовых заказов"""

    def __init__(self, excel_file_path, roll_module, preview_module, coordinator=None):
        self.excel_file_path = excel_file_path
        self.roll_module = roll_module
        self.preview_module = preview_module
        self.coordinator = coordinator       
        # Подписываемся на координатор если он есть
        if self.coordinator and hasattr(self.coordinator, 'subscribe'):
            self.coordinator.subscribe(self.on_settings_changed)
            
        self.wb = None
        self.ws = None
        
    def on_settings_changed(self):
        """Обработчик изменений настроек от координатора"""
        # При изменении цеха можно обновить путь к файлу
        if hasattr(self, 'coordinator') and self.coordinator:
            workshop = self.coordinator.get_workshop()
            print(f"Экспортер: получен цех {workshop}")
            
    def get_excel_file_path(self):
        """Возвращает путь к Excel файлу в зависимости от цеха"""
        if hasattr(self, 'coordinator') and self.coordinator:
            workshop = self.coordinator.get_workshop()
            if workshop == "2":
                # Для цеха 2 используем второй файл
                base_path = self.excel_file_path
                # Берем директорию и меняем имя файла
                directory = os.path.dirname(base_path)
                return os.path.join(directory, "weight_orders_2.xlsx")
        return self.excel_file_path
        
    def _is_second_file(self):
        """Проверяет, используется ли второй файл"""
        file_path = self.get_excel_file_path()
        return "weight_orders_2.xlsx" in file_path
        
    def export_to_multitype_sheet(self, pallet_data):
        """Экспортирует данные в лист 'Много видов' с пересчетом с нуля"""
        try: 
            if not self.excel_file_path or not os.path.exists(self.excel_file_path):
                return {'success': False, 'error': 'Файл не найден'}
            
            workbook = load_workbook(self.excel_file_path)
            pallet_sheet = workbook["Лист для паллеты"]
            
            boxes_count = 0
            gross_total = 0
            net_total = 0
            labels_total = 0
            
            for row in range(14, 29):
                if (pallet_sheet[f'B{row}'].value is not None or 
                    pallet_sheet[f'C{row}'].value is not None or
                    pallet_sheet[f'D{row}'].value is not None):
                    
                    boxes_count += 1
                    gross_total += pallet_sheet[f'B{row}'].value or 0
                    net_total += pallet_sheet[f'C{row}'].value or 0
                    labels_total += pallet_sheet[f'D{row}'].value or 0
            
            for row in range(14, 29):
                if (pallet_sheet[f'F{row}'].value is not None or 
                    pallet_sheet[f'G{row}'].value is not None or
                    pallet_sheet[f'H{row}'].value is not None):
                    
                    boxes_count += 1
                    gross_total += pallet_sheet[f'F{row}'].value or 0
                    net_total += pallet_sheet[f'G{row}'].value or 0
                    labels_total += pallet_sheet[f'H{row}'].value or 0
                        
            if boxes_count == 0:
                workbook.close()
                return {'success': False, 'error': 'Нет данных для экспорта (лист поддона пуст)'}
            
            pallet_weight = self._convert_to_number_if_possible(pallet_data.get("pallet_weight", 0))
            gross_total_with_pallet = gross_total + pallet_weight
                
            multitype_sheet = workbook["Лист много видов"]
            
            product_name = pallet_data.get('product_name', '')
            target_row = None
            
            for row in range(11, 29):
                if multitype_sheet[f'B{row}'].value == product_name:
                    target_row = row
                    break
            
            if target_row is not None:
                multitype_sheet[f'A{target_row}'].value = None
                multitype_sheet[f'F{target_row}'].value = None
                multitype_sheet[f'G{target_row}'].value = None
                multitype_sheet[f'H{target_row}'].value = None
            
            if target_row is None:
                for row in range(11, 29):
                    if multitype_sheet[f'A{row}'].value is None:
                        target_row = row
                        break
            
            if target_row is None:
                workbook.close()
                return {'success': False, 'error': 'Лист переполнен'}
            
            # Временно сохраняем multitype_sheet как self.ws
            original_ws = getattr(self, 'ws', None)
            self.ws = multitype_sheet
            
            # Экспортируем базовую информацию без наименования продукции
            self._export_basic_info(skip_product_name=True)
            
            # Тип упаковки (поддон) и вес поддона
            self._set_cell_value('D6', pallet_data.get("pallet_type", ""))
            self._set_cell_value('K2', pallet_weight)
            
            # Записываем пересчитанные данные
            self._set_cell_value(f'A{target_row}', boxes_count)
            self._set_cell_value(f'B{target_row}', product_name)
            self._set_cell_value(f'F{target_row}', gross_total)
            self._set_cell_value(f'G{target_row}', net_total)
            self._set_cell_value(f'H{target_row}', labels_total)
            
            # Восстанавливаем рабочий лист
            if original_ws:
                self.ws = original_ws
            
            workbook.save(self.excel_file_path)
            workbook.close()
            
            return {'success': True, 'row_used': target_row}
            
        except Exception as e:
            print(f"Ошибка экспорта в много-видовой лист: {e}")
            try:
                workbook.close()
            except:
                pass
            return {'success': False, 'error': str(e)}
            
    def clear_multitype_sheet(self):
        """Очищает ВСЕ данные в листе 'Много видов', которые заполняет export_to_multitype_sheet"""
        try:
            if not os.path.exists(self.excel_file_path):
                return False
                
            self.wb = load_workbook(self.excel_file_path)
            
            if "Лист много видов" not in self.wb.sheetnames:
                return False
                
            self.ws = self.wb["Лист много видов"]
            
            # 1. Очищаем базовую информацию
            basic_info_cells = ['D5', 'D6', 'D8', 'F37', 'E41', 'K2']
            
            for cell_address in basic_info_cells:
                try:
                    cell = self.ws[cell_address]
                    cell.value = None
                    cell.alignment = Alignment(horizontal='general', vertical='center')
                except Exception as e:
                    print(f"Не удалось очистить ячейку {cell_address}: {e}")
            
            # 2. Очищаем данные продуктов (строки 11-28)
            for row in range(11, 29):
                for col in ['A', 'B', 'F', 'G', 'H']:
                    try:
                        cell = self.ws[f'{col}{row}']
                        cell.value = None
                        cell.alignment = Alignment(horizontal='general', vertical='center')
                    except Exception as e:
                        print(f"Не удалось очистить ячейку {col}{row}: {e}")
            
            self.wb.save(self.excel_file_path)
            self.wb.close()
            return True
            
        except Exception as e:
            print(f"Ошибка очистки листа 'Много видов': {e}")
            try:
                if self.wb:
                    self.wb.close()
            except:
                pass
            return False
        
    def export_data(self, enable_pallet=False, pallet_data=None):
        """Основной метод экспорта данных"""
        try:
            # Используем правильный путь к файлу в зависимости от цеха
            actual_file_path = self.get_excel_file_path()
            
            if not os.path.exists(actual_file_path):
                raise FileNotFoundError(f"Файл не найден: {actual_file_path}")
            
            # Загружаем книгу и выбираем лист в зависимости от режима
            self.wb = load_workbook(actual_file_path)
            
            # Проверяем изготовителя
            self._update_manufacturer_info()
            
            # Определяем имя листа в зависимости от файла и режима
            if enable_pallet:
                sheet_name = "Паллета" if self._is_second_file() else "Лист для паллеты"
            else:
                sheet_name = "Коробка" if self._is_second_file() else "Лист для коробки"
                
            if sheet_name not in self.wb.sheetnames:
                raise ValueError(f"Лист '{sheet_name}' не найден в файле")
                
            self.ws = self.wb[sheet_name]
            
            # Экспортируем данные в зависимости от режима
            if enable_pallet:
                all_fitted = self._export_pallet_data(pallet_data)
            else:
                self._export_basic_info()
                self._export_box_data()
                all_fitted = self._export_rolls_to_empty_cells()
            
            # Сохраняем изменения
            self.wb.save(actual_file_path)
            
            # Возвращаем словарь с результатами
            return {
                'success': True,
                'all_fitted': all_fitted
            }
            
        except Exception as e:
            print(f"Ошибка экспорта в Excel: {e}")
            return {'success': False, 'all_fitted': True}
        finally:
            if self.wb:
                self.wb.close()
                
    def _export_box_data(self):
        """Экспортирует данные коробки"""
        if not self.roll_module:
            return True
            
        try:
            is_second_file = self._is_second_file()
            
            # Вес коробки
            box_weight = self._convert_to_number_if_possible(self.roll_module.box_weight_var.get())
            if box_weight:
                box_weight_cell = 'H3' if is_second_file else 'K2'
                self._set_cell_value(box_weight_cell, box_weight)
            
            # Новые поля для второго файла: вес втулки и диаметр втулки
            if is_second_file:
                # Вес втулки (конвертация из граммов в кг)
                sleeve_weight_g = self._convert_to_number_if_possible(self.roll_module.sleeve_weight_var.get())
                if sleeve_weight_g:
                    sleeve_weight_kg = sleeve_weight_g / 1000
                    self._set_cell_value('D4', sleeve_weight_kg)
                
                # Диаметр втулки
                sleeve_diameter = self._convert_to_number_if_possible(self.roll_module.sleeve_diameter_var.get())
                if sleeve_diameter:
                    self._set_cell_value('G4', sleeve_diameter)
            
            return True
            
        except Exception as e:
            print(f"Ошибка при экспорте данных коробки: {e}")
            return True
    
    def _export_pallet_data(self, pallet_data):
        """Экспортирует данные поддона"""
        try:
            # Экспортируем базовую информацию (как для коробки)
            self._export_basic_info()
            
            # Тип упаковки (поддон) в D6
            if pallet_data and pallet_data.get("pallet_type"):
                self._set_cell_value('D6', pallet_data["pallet_type"])
            
            # Вес поддона в K2 - Преобразуем в число
            if pallet_data and pallet_data.get("pallet_weight"):
                pallet_weight = self._convert_to_number_if_possible(pallet_data["pallet_weight"])
                self._set_cell_value('K2', pallet_weight)
            
            # Экспортируем данные коробок и возвращаем информацию о переполнении
            return self._export_boxes_to_empty_cells(pallet_data)
                
        except Exception as e:
            print(f"Ошибка при экспорте данных поддона: {e}")
            return True
            
    def _export_basic_info(self, skip_product_name=False):
        """Экспортирует основную информацию"""
        try:
            is_second_file = self._is_second_file()
            
            # Заказчик
            if self.roll_module and hasattr(self.roll_module, 'customer_var'):
                customer = self.roll_module.customer_var.get()
                customer_cell = 'D7' if is_second_file else 'D5'
                self._set_cell_value(customer_cell, customer)
                
                if is_second_file:
                    cell = self.ws['D7']
                    cell.alignment = Alignment(horizontal='center', vertical='center')                
            
            # Тип упаковки
            if self.roll_module and hasattr(self.roll_module, 'box_size_var'):
                box_type = self.roll_module.box_size_var.get()
                package_type_cell = 'D3' if is_second_file else 'D6'
                self._set_cell_value(package_type_cell, box_type)
                
                if is_second_file:
                    cell = self.ws['D3']
                    cell.alignment = Alignment(horizontal='center', vertical='center')                
            
            # Номер заказа
            if self.roll_module:
                order_prefix = getattr(self.roll_module, 'order_prefix', None).get()
                order_number = getattr(self.roll_module, 'order_number', None).get()
                order_suffix = getattr(self.roll_module, 'order_suffix', None).get()
                
                full_order = f"{order_prefix}{order_number}{order_suffix}"
                order_cell = 'D6' if is_second_file else 'D8'
                self._set_cell_value(order_cell, full_order)
                
                if is_second_file:
                    cell = self.ws['D6']
                    cell.alignment = Alignment(horizontal='center', vertical='center')
            
            # Наименование продукции
            if not skip_product_name and self.roll_module and hasattr(self.roll_module, 'product_text'):
                product_text = self.roll_module.product_text.get("1.0", "end-1c").strip()
                product_cell = 'D8' if is_second_file else 'D10'
                self._set_cell_value(product_cell, product_text)
                cell = self.ws[product_cell]
                cell.alignment = Alignment(horizontal='left', vertical='top', wrap_text=True)
            
            # Дата упаковки
            if self.roll_module and hasattr(self.roll_module, 'date_var'):
                date = self.roll_module.date_var.get()
                date_cell = 'D37' if is_second_file else 'F37'
                self._set_cell_value(date_cell, date)
            
            # Упаковщик
            if self.roll_module and hasattr(self.roll_module, 'packer_var'):
                packer = self.roll_module.packer_var.get()
                packer_cell = 'E41'  # одинаковый для обоих файлов
                self._set_cell_value(packer_cell, packer)
                    
        except Exception as e:
            print(f"Ошибка при экспорте базовой информации: {e}")                   
    
    def _export_boxes_to_empty_cells(self, pallet_data):
        """Экспортирует данные коробок в пустые ячейки для поддона"""
        if not self.roll_module:
            return True
            
        try:
            # Получаем количество коробок из pallet_data
            boxes_count = 0
            if pallet_data and pallet_data.get("boxes_count"):
                try:
                    boxes_count_str = pallet_data["boxes_count"]
                    boxes_count = int(boxes_count_str) if boxes_count_str else 0
                except (ValueError, TypeError):
                    boxes_count = 0
            
            if boxes_count == 0:
                boxes_count = 1
            
            # Получаем данные одной коробки из roll_module
            gross_weight = self._convert_to_number_if_possible(self.roll_module.total_gross_var.get())
            net_weight = self._convert_to_number_if_possible(self.roll_module.total_net_var.get())
            quantity = self._convert_to_number_if_possible(self.roll_module.total_quantity_var.get())
            
            # Находим пустые ячейки и заполняем их (аналогично роликам)
            empty_cells_found = 0
            
            # Заполняем левую часть (B14-B28, C14-C28, D14-D28)
            for row in range(14, 29):
                if empty_cells_found >= boxes_count:
                    break
                    
                # Проверяем, пуста ли строка для записи
                if (self.ws[f'B{row}'].value is None and 
                    self.ws[f'C{row}'].value is None and 
                    self.ws[f'D{row}'].value is None):
                    
                    if gross_weight:
                        self._set_cell_value(f'B{row}', gross_weight)
                    if net_weight:
                        self._set_cell_value(f'C{row}', net_weight)
                    if quantity:
                        self._set_cell_value(f'D{row}', quantity)
                    
                    empty_cells_found += 1
            
            # Если нужно больше - заполняем правую часть (F14-F28, G14-G28, H14-H28)
            for row in range(14, 29):
                if empty_cells_found >= boxes_count:
                    break
                    
                # Проверяем, пуста ли строка для записи
                if (self.ws[f'F{row}'].value is None and 
                    self.ws[f'G{row}'].value is None and 
                    self.ws[f'H{row}'].value is None):
                    
                    if gross_weight:
                        self._set_cell_value(f'F{row}', gross_weight)
                    if net_weight:
                        self._set_cell_value(f'G{row}', net_weight)
                    if quantity:
                        self._set_cell_value(f'H{row}', quantity)
                    
                    empty_cells_found += 1
            
            # Возвращаем True если все коробки поместились, False если нет
            return empty_cells_found >= boxes_count
                
        except Exception as e:
            print(f"Ошибка при экспорте данных коробок: {e}")
            return True

    def _export_rolls_to_empty_cells(self):
        """Экспортирует данные роликов в пустые ячейки"""
        if not self.roll_module:
            return True
            
        try:
            is_second_file = self._is_second_file()
            
            # Получаем количество роликов
            rolls_count = 0
            if self.roll_module and hasattr(self.roll_module, 'rolls_count_var'):
                try:
                    rolls_count_str = self.roll_module.rolls_count_var.get()
                    rolls_count = int(rolls_count_str) if rolls_count_str else 0
                except (ValueError, TypeError):
                    rolls_count = 0
            
            if rolls_count == 0:
                rolls_count = 1
            
            # Получаем данные одного ролика
            gross_weight = self._convert_to_number_if_possible(self.roll_module.gross_weight_kg_var.get())
            net_weight = self._convert_to_number_if_possible(self.roll_module.net_weight_kg_var.get())
            quantity = self._convert_to_number_if_possible(self.roll_module.quantity_var.get())
            
            # Определяем диапазоны ячеек в зависимости от файла
            if is_second_file:
                # Для второго файла: вес нетто и количество в разных колонках
                net_weight_cols = ['B', 'E', 'H']  # вес нетто
                quantity_cols = ['C', 'F', 'I']     # количество
                start_row = 10
                end_row = 29
            else:
                # Для первого файла: стандартные колонки
                gross_weight_cols = ['B', 'F']      # вес брутто
                net_weight_cols = ['C', 'G']        # вес нетто  
                quantity_cols = ['D', 'H']          # количество
                start_row = 14
                end_row = 28
            
            # Находим пустые ячейки и заполняем их
            empty_cells_found = 0
            
            if is_second_file:
                # Заполнение для второго файла (только нетто и количество)
                for row in range(start_row, end_row + 1):
                    if empty_cells_found >= rolls_count:
                        break
                        
                    # Проверяем, пуста ли строка для записи (проверяем первую колонку веса нетто)
                    if self.ws[f'B{row}'].value is None:
                        if net_weight:
                            self._set_cell_value(f'B{row}', net_weight)
                        if quantity:
                            self._set_cell_value(f'C{row}', quantity)
                        
                        empty_cells_found += 1
                
                # Если нужно больше - заполняем следующие колонки
                for col in ['E', 'H']:
                    for row in range(start_row, end_row + 1):
                        if empty_cells_found >= rolls_count:
                            break
                            
                        if self.ws[f'{col}{row}'].value is None:
                            if net_weight:
                                self._set_cell_value(f'{col}{row}', net_weight)
                            if quantity:
                                self._set_cell_value(f'{chr(ord(col) + 1)}{row}', quantity)
                            
                            empty_cells_found += 1
            else:
                # Заполнение для первого файла (стандартное)
                for row in range(start_row, end_row + 1):
                    if empty_cells_found >= rolls_count:
                        break
                        
                    if (self.ws[f'B{row}'].value is None and
                        self.ws[f'C{row}'].value is None and
                        self.ws[f'D{row}'].value is None):
                        
                        if gross_weight:
                            self._set_cell_value(f'B{row}', gross_weight)
                        if net_weight:
                            self._set_cell_value(f'C{row}', net_weight)
                        if quantity:
                            self._set_cell_value(f'D{row}', quantity)
                        
                        empty_cells_found += 1
                
                for row in range(start_row, end_row + 1):
                    if empty_cells_found >= rolls_count:
                        break
                        
                    if (self.ws[f'F{row}'].value is None and 
                        self.ws[f'G{row}'].value is None and 
                        self.ws[f'H{row}'].value is None):
                        
                        if gross_weight:
                            self._set_cell_value(f'F{row}', gross_weight)
                        if net_weight:
                            self._set_cell_value(f'G{row}', net_weight)
                        if quantity:
                            self._set_cell_value(f'H{row}', quantity)
                        
                        empty_cells_found += 1
            
            return empty_cells_found >= rolls_count
                
        except Exception as e:
            print(f"Ошибка при экспорте данных роликов: {e}")
            return True

    def clear_all_rolls(self, enable_pallet=False):
        """Очищает все данные роликов/коробок и базовую информацию в Excel"""
        try:
            actual_file_path = self.get_excel_file_path()
            
            if not os.path.exists(actual_file_path):
                raise FileNotFoundError(f"Файл не найден: {actual_file_path}")
            
            # Проверяем, не открыт ли файл в Excel
            if self._is_file_locked(actual_file_path):
                raise PermissionError(f"Файл {actual_file_path} открыт в Excel. Закройте его и попробуйте снова.")
            
            self.wb = load_workbook(actual_file_path)
            
            is_second_file = self._is_second_file()
            
            if enable_pallet:
                sheet_name = "Паллета" if is_second_file else "Лист для паллеты"
            else:
                sheet_name = "Коробка" if is_second_file else "Лист для коробки"
                
            if sheet_name not in self.wb.sheetnames:
                raise ValueError(f"Лист '{sheet_name}' не найден")
                
            self.ws = self.wb[sheet_name]
            
            # Очищаем данные роликов/коробок
            cleared_items = 0
            
            if is_second_file:
                # Для второго файла
                rows_range = range(10, 30)  # строки 10-29
                cols_to_clear = ['B', 'C', 'E', 'F', 'H', 'I', 'L']  # вес нетто, количество, длина
            else:
                # Для первого файла  
                rows_range = range(14, 29)  # строки 14-28
                cols_to_clear = ['B', 'C', 'D', 'F', 'G', 'H']  # стандартные колонки
            
            for row in rows_range:
                for col in cols_to_clear:
                    try:
                        # Прямой доступ к ячейке как в оригинальном коде
                        cell = self.ws[f'{col}{row}']
                        cell.value = None
                        cell.alignment = Alignment(horizontal='general', vertical='center')
                        cleared_items += 1
                    except Exception as e:
                        print(f"Не удалось очистить ячейку {col}{row}: {e}")
            
            # Очищаем базовую информацию
            if is_second_file:
                basic_info_cells = ['D7', 'D3', 'D6', 'D8', 'D37', 'E41', 'H3', 'D4', 'G4']
            else:
                basic_info_cells = ['D5', 'D6', 'D8', 'D10', 'F37', 'E41', 'K2']
            
            cleared_basic = 0
            for cell_address in basic_info_cells:
                try:
                    # Прямой доступ к ячейке как в оригинальном коде
                    cell = self.ws[cell_address]
                    cell.value = None
                    cell.alignment = Alignment(horizontal='general', vertical='center')
                    cleared_basic += 1
                except Exception as e:
                    print(f"Не удалось очистить ячейку {cell_address}: {e}")
            
            # Сохраняем изменения
            self.wb.save(actual_file_path)
            return True
            
        except PermissionError as e:
            print(f"Ошибка доступа к файлу: {e}")
            return False
        except FileNotFoundError as e:
            print(f"Файл не найден: {e}")
            return False
        except Exception as e:
            print(f"Ошибка очистки Excel: {e}")
            return False
        finally:
            if self.wb:
                self.wb.close()          
            
    def _is_file_locked(self, filepath):
        """Проверяет, открыт ли файл в другом процессе (например, в Excel)"""
        try:
            # Попытка открыть файл в режиме записи
            with open(filepath, 'a', encoding='utf-8'):
                pass
            return False
        except IOError:
            return True
        except Exception:
            return False

    def _set_cell_value(self, cell_address, value):
        """Устанавливает значение ячейки с обработкой ошибок"""
        try:
            # Проверяем, не является ли ячейка частью объединения
            cell = self.ws[cell_address]
            
            # Если ячейка объединенная - находим первую ячейку объединенного диапазона
            for merged_range in self.ws.merged_cells.ranges:
                if cell.coordinate in merged_range:
                    # Для горизонтально объединенных ячеек (B11:E11, B12:E12 и т.д.)
                    # используем первую ячейку объединенного диапазона
                    target_cell = self.ws[merged_range.min_row][merged_range.min_col - 1]
                    target_cell.value = value
                    
                    # Выравнивание
                    if value is None or value == "":
                        target_cell.alignment = Alignment(horizontal='general', vertical='center')
                    elif isinstance(value, (int, float)):
                        target_cell.alignment = Alignment(horizontal='center', vertical='center')
                    else:
                        target_cell.alignment = Alignment(horizontal='left', vertical='center')
                    return
                        
            # Если ячейка не объединенная - работаем как обычно
            self.ws[cell_address] = value
            
            # Выравнивание
            if value is None or value == "":
                self.ws[cell_address].alignment = Alignment(horizontal='general', vertical='center')
            elif isinstance(value, (int, float)):
                self.ws[cell_address].alignment = Alignment(horizontal='center', vertical='center')
            else:
                self.ws[cell_address].alignment = Alignment(horizontal='left', vertical='center')
                
        except Exception as e:
            print(f"Не удалось установить значение {value} в ячейку {cell_address}: {e}")
            
    def _update_manufacturer_info(self):
        """Обновляет информацию об изготовителе только в первом листе"""
        try:
            # Получаем значение Изготовителя
            show_manufacturer = True

            if hasattr(self.roll_module, 'show_manufacturer_var'):
                # ИНВЕРТИРУЕМ логику: True = "Без Производителя" = не показывать
                show_manufacturer = not self.roll_module.show_manufacturer_var.get()

            # Получаем актуального изготовителя из config_manager
            manufacturer_name = ""
            if hasattr(self.roll_module, 'config_manager'):
                manufacturer_name = self.roll_module.config_manager.get_manufacturer()
            
            # Формируем текст для отображения с проверкой на Ремас
            display_text = ""
            if show_manufacturer and manufacturer_name:
                if "Ремас" in manufacturer_name or "Ремас-Флексо" in manufacturer_name:
                    display_text = 'ООО "Ремас-Флексо" , Россия, 426039, Удмуртская Республика, Ижевск, ул.Воткинское шоссе, 186.'
                else:
                    # Для других изготовителей - только название
                    display_text = manufacturer_name
            
            # Обновляем только первый лист
            if "Лист для коробки" in self.wb.sheetnames:
                sheet = self.wb["Лист для коробки"]
                sheet['B1'] = display_text
                
                # Выравнивание по центру и перенос текста
                sheet['B1'].alignment = Alignment(
                    horizontal='center', 
                    vertical='center',
                    wrap_text=True
                )
            
        except Exception as e:
            print(f"Ошибка при обновлении информации об изготовителе: {e}")
                
    def _convert_to_number_if_possible(self, value):
        """Пытается преобразовать строку в число"""
        if value is None:
            return None
            
        if not isinstance(value, str):
            return value
            
        # Убираем лишние пробелы
        value = value.strip()
        
        if not value:
            return None
        
        # Пробуем преобразовать в целое число
        try:
            if value.isdigit():
                return int(value)
        except:
            pass
        
        # Пробуем преобразовать в дробное число
        try:
            # Заменяем запятую на точку для дробных чисел
            normalized_value = value.replace(',', '.')
            # Проверяем, что это число с плавающей точкой
            if normalized_value.replace('.', '').isdigit() and normalized_value.count('.') == 1:
                return float(normalized_value)
        except:
            pass
        
        # Если не получилось - возвращаем как строку
        return value