# core/archive/archive_manager.py
import os
import re
from datetime import datetime
from openpyxl import load_workbook
from openpyxl.styles import Alignment
from core.config_manager import ConfigManager

class ArchiveManager:
    """Менеджер архива поддонов: поиск, восстановление, управление"""
    
    def __init__(self, config_manager=None):
        self.config = config_manager or ConfigManager()
        self.excel_path = self._get_excel_path()
        
    def _get_excel_path(self):
        """Получает путь к Excel файлу из настроек"""
        settings = self.config.load_json_settings("shared_utils.json")
        excel_folder = settings.get("weight_orders_xlsx", "")
        filename = "weight_orders_2.xlsx"  # для цеха 2
        return os.path.join(excel_folder, filename)
        
    def extract_pallet_data(self, excel_file_path):
        """Извлекает данные поддона для архивации"""
        workbook = load_workbook(excel_file_path)
        pallet_sheet = workbook["Поддон"]
        archive_data = self._extract_all_data_for_archive(pallet_sheet)
        workbook.close()
        return archive_data
        
    def _extract_all_data_for_archive(self, sheet):
        """Извлекает ВСЕ данные из листа 'Поддон' для архивации"""
        from datetime import datetime
        
        # Базовые поля из листа
        basic_fields = {
            "A1": sheet['A1'].value,  # Изготовитель
            "D7": sheet['D7'].value,  # Заказчик
            "D3": sheet['D3'].value,  # Тип упаковки
            "D6": sheet['D6'].value,  # Номер заказа
            "D8": sheet['D8'].value,  # Изделие (может быть многострочным)
            "D37": sheet['D37'].value,  # Дата упаковки
            "E41": sheet['E41'].value,  # Упаковщик
            "H3": sheet['H3'].value,  # Вес поддона
            "D4": sheet['D4'].value,  # Вес втулки (кг)
            "G4": sheet['G4'].value,  # Диаметр втулки
            "E39": sheet['E39'].value,  # Тип продукта
            "A39": sheet['A39'].value,  # TU номер
            "D5": sheet['D5'].value   # Текущий номер поддона
        }
        
        # Извлекаем данные роликов
        rolls = self._extract_rolls_data_from_sheet(sheet)
        
        # Собираем полные данные для архива
        archive_data = {
            "workshop": "2",
            "basic_fields": basic_fields,
            "rolls": rolls,
            "extraction_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        return archive_data
        
    def _extract_rolls_data_from_sheet(self, sheet):
        """Извлекает данные роликов из листа"""
        rolls = []
        
        # Пары колонок и соответствующие смещения для длины в L
        column_pairs = [
            ('B', 'C', 0),   # B,C - длина в L с тем же номером строки
            ('E', 'F', 20),  # E,F - длина в L со смещением +20
            ('H', 'I', 40)   # H,I - длина в L со смещением +40
        ]
        
        for weight_col, qty_col, l_offset in column_pairs:
            for row in range(10, 30):  # строки 10-29
                weight = sheet[f'{weight_col}{row}'].value
                quantity = sheet[f'{qty_col}{row}'].value
                
                if weight is not None or quantity is not None:
                    # Получаем длину из столбца L
                    length_row = row + l_offset
                    length = sheet[f'L{length_row}'].value
                    
                    rolls.append({
                        'position': f'{weight_col}{row}',
                        'weight_col': weight_col,
                        'quantity_col': qty_col,
                        'row': row,
                        'weight': weight,
                        'quantity': quantity,
                        'length': length,
                        'length_position': f'L{length_row}'
                    })
        
        return rolls        
    
    def get_all_pallets(self):
        """Возвращает все поддоны из архива в формате для отображения"""
        archive = self.config.get_pallet_archive()
        pallets = archive.get("pallets", [])
        
        result = []
        for pallet in pallets:
            basic_fields = pallet.get("basic_fields", {})
            
            # Извлекаем данные для отображения
            pallet_num = basic_fields.get("D5", "—")
            order_num = basic_fields.get("D6", "—")
            date = basic_fields.get("D37", "—")
            packer = basic_fields.get("E41", "—")
            product = basic_fields.get("D8", "—")
            
            # Обрезаем название продукции до 30 символов
            product_preview = str(product)[:50] + "..." if len(str(product)) > 50 else str(product)
            
            # Формируем строку для отображения
            display_text = f"№{pallet_num} | {order_num} | {date} | {packer} | {product_preview}"
            
            result.append({
                "display": display_text,
                "pallet_data": pallet,  # полные данные
                "pallet_number": pallet_num,
                "order": order_num,
                "date": date,
                "packer": packer,
                "product_preview": product_preview
            })
        
        return result
    
    def search_pallets(self, order_number="", pallet_number="", product_part=""):
        """
        Ищет поддоны по критериям (регистронезависимый поиск)
        """
        all_pallets = self.get_all_pallets()
        
        if not any([order_number, pallet_number, product_part]):
            return all_pallets  # возвращаем все если нет критериев
        
        filtered = []
        
        for pallet in all_pallets:
            matches = []
            
            # Поиск по номеру заказа (D6)
            if order_number:
                order = str(pallet.get("order", "")).lower()
                if order_number.lower() in order:
                    matches.append(True)
            
            # Поиск по номеру поддона (D5)
            if pallet_number:
                p_num = str(pallet.get("pallet_number", "")).lower()
                if pallet_number.lower() in p_num:
                    matches.append(True)
            
            # Поиск по части названия (D8)
            if product_part:
                product = str(pallet.get("product_preview", "")).lower()
                if product_part.lower() in product:
                    matches.append(True)
            
            # Если были критерии и все совпали (или критерий один и совпал)
            criteria_count = sum([bool(order_number), bool(pallet_number), bool(product_part)])
            if matches and len(matches) >= min(1, criteria_count):
                filtered.append(pallet)
        
        return filtered
    
    def restore_pallet_to_excel(self, pallet_data, excel_path=None):
        """Восстанавливает поддон из архива в Excel файл"""
        try:
            if excel_path is None:
                excel_path = self.excel_path
            
            if not os.path.exists(excel_path):
                return {"success": False, "error": f"Файл не найден: {excel_path}"}
            
            workbook = load_workbook(excel_path)  # ← открываем
            
            if "Поддон" not in workbook.sheetnames:
                workbook.close()
                return {"success": False, "error": "Лист 'Поддон' не найден"}
            
            sheet = workbook["Поддон"]
            self._clear_pallet_sheet(sheet)
            
            # 2. Заполняем базовые поля
            basic_fields = pallet_data.get("basic_fields", {})
            for cell_address, value in basic_fields.items():
                if cell_address and value is not None:
                    sheet[cell_address] = value
                    # Добавить выравнивание:
                    sheet[cell_address].alignment = Alignment(
                        horizontal='center', 
                        vertical='center'
                    )
                # Отдельно для D8 Изделие:
                if "D8" in basic_fields and basic_fields["D8"] is not None:
                    sheet["D8"] = basic_fields["D8"]
                    sheet["D8"].alignment = Alignment(
                        horizontal='left',
                        vertical='top',
                        wrap_text=True
                    )
                # Отдельно для A1 Изготовитель:
                if "A1" in basic_fields and basic_fields["D8"] is not None:
                    sheet["A1"] = basic_fields["A1"]
                    sheet["A1"].alignment = Alignment(
                        horizontal='center',
                        vertical='top',
                        wrap_text=True
                    )                    
            
            # 3. Заполняем ролики
            rolls = pallet_data.get("rolls", [])
            for roll in rolls:
                # Вес
                if roll.get("weight") is not None:
                    position = roll.get("position")
                    if position:
                        sheet[position] = roll["weight"]
                
                # Количество
                if roll.get("quantity") is not None:
                    qty_col = roll.get("quantity_col")
                    row = roll.get("row")
                    if qty_col and row:
                        sheet[f"{qty_col}{row}"] = roll["quantity"]
                
                # Длина
                if roll.get("length") is not None:
                    length_pos = roll.get("length_position")
                    if length_pos:
                        sheet[length_pos] = roll["length"]
            
            # 4. Обновляем производителя (A1) если есть
            manufacturer = basic_fields.get("A1")
            if manufacturer:
                sheet["A1"] = manufacturer
            
            # 5. Сохраняем
            workbook.save(excel_path)
            workbook.close()
            
            return {
                "success": True,
                "pallet_number": basic_fields.get("D5", "неизвестно"),
                "order": basic_fields.get("D6", "неизвестно")
            }
            
        except PermissionError as e:
            return {
                "success": False,
                "error": f"Файл открыт в Excel. Закройте его и попробуйте снова."
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Ошибка восстановления: {str(e)}"
            }
    
    def _clear_pallet_sheet(self, sheet):
        """Очищает лист 'Поддон' перед восстановлением"""
        # Очищаем ролики (B,C,E,F,H,I) строки 10-29
        for row in range(10, 30):
            for col in ['B', 'C', 'E', 'F', 'H', 'I']:
                cell = sheet[f'{col}{row}']
                cell.value = None
                cell.alignment = Alignment(horizontal='general', vertical='center')
        
        # Очищаем длины L (строки 10-69)
        for row in range(10, 70):
            cell = sheet[f'L{row}']
            cell.value = None
            cell.alignment = Alignment(horizontal='general', vertical='center')
        
        # Очищаем базовые поля
        basic_cells = ['D7', 'D3', 'D6', 'D8', 'D37', 'E41', 'H3', 
                      'D4', 'G4', 'E39', 'A39', 'D5']
        for cell_address in basic_cells:
            cell = sheet[cell_address]
            cell.value = None
            cell.alignment = Alignment(horizontal='general', vertical='center')
        
        # Производитель (A1) - не очищаем, может быть настройка
        
        return True
    
    def delete_pallet_from_archive(self, pallet_data):
        """Удаляет поддон из архива"""
        try:
            archive = self.config.get_pallet_archive()
            pallets = archive.get("pallets", [])
            
            # Находим и удаляем поддон
            basic_to_remove = pallet_data.get("basic_fields", {})
            d5_to_remove = basic_to_remove.get("D5")
            d6_to_remove = basic_to_remove.get("D6")
            
            new_pallets = []
            deleted = False
            
            for pallet in pallets:
                basic = pallet.get("basic_fields", {})
                d5 = basic.get("D5")
                d6 = basic.get("D6")
                
                # Сравниваем по D5 и D6
                if str(d5) == str(d5_to_remove) and str(d6) == str(d6_to_remove):
                    deleted = True
                    continue  # пропускаем (удаляем)
                
                new_pallets.append(pallet)
            
            if deleted:
                archive["pallets"] = new_pallets
                self.config.save_pallet_archive(archive)
                return True
            else:
                return False
                
        except Exception as e:
            print(f"Ошибка удаления поддона: {e}")
            return False