# core/archive/archive_manager.py
import os
import re
from datetime import datetime
from openpyxl import load_workbook
from openpyxl.styles import Alignment
from core.excel_exporter.legacy_adapter import LegacyExporterAdapter as WeightOrdersExporter

class ArchiveManager:
    """Менеджер архива: поиск, восстановление, управление для всех цехов и режимов"""
    # Константа для определения типов архивов
    ARCHIVE_TYPES = {
        ("1", False, False): "box",           # Цех 1, коробка
        ("1", True, False): "pallet",         # Цех 1, поддон  
        ("1", False, True): "multitype",      # Цех 1, много видов
        ("2", False, False): "box",           # Цех 2, коробка
        ("2", True, False): "pallet",         # Цех 2, поддон (список)
        ("2", False, True): "multitype"       # Цех 2, много видов
    }    
    
    def __init__(self, config_manager=None, coordinator=None, exporter=None):
        self.config = config_manager or ConfigManager()
        self.coordinator = coordinator
        self.exporter = exporter
        if coordinator and hasattr(coordinator, 'subscribe'):
            coordinator.subscribe(self.on_settings_changed)
        self.excel_path = None  # Будет определяться динамически
        self.clean_old_archive_records(3)  # автоочистка при запуске
        
    def clean_old_archive_records(self, max_age_years=3):
        """Удаляет записи старше указанного количества лет"""
        try:
            archive = self.config.get_pallet_archive()
            if not archive or "pallets" not in archive:
                return False
            
            # Текущая дата
            now = datetime.now()
            
            # Фильтруем записи
            original_count = len(archive["pallets"])
            archive["pallets"] = [
                pallet for pallet in archive["pallets"] 
                if self._is_record_younger_than(pallet, max_age_years, now)
            ]
            new_count = len(archive["pallets"])
            
            # Если что-то удалили - сохраняем
            if new_count < original_count:
                self.config.save_pallet_archive(archive)
                print(f"[INFO] Очистка архива: удалено {original_count - new_count} записей старше {max_age_years} лет")
                
            return True
            
        except Exception as e:
            print(f"[ERROR] Ошибка очистки архива: {e}")
            return False

    def _is_record_younger_than(self, record, max_age_years, now):
        """Проверяет, что запись не старше max_age_years"""
        extraction_date = record.get("extraction_date")
        if not extraction_date:
            return True  # если нет даты, оставляем
        
        try:
            # Парсим дату из строки
            record_date = datetime.strptime(extraction_date, "%Y-%m-%d %H:%M:%S")
            age = now - record_date
            return age.days < max_age_years * 365
        except:
            return True  # если не удалось распарсить, оставляем
        
    def on_settings_changed(self, event_type=None, data=None):
        """Обработчик событий от координатора для обновления пути к файлу"""
        if event_type == "workshop_changed" or event_type == "excel_path_changed":
            self.excel_path = self._get_excel_path()
    
    def _get_excel_path(self, workshop=None):
        """Получает путь к Excel файлу из настроек с учетом цеха"""
        if workshop is None and self.coordinator:
            workshop = self.coordinator.get_workshop()
        elif workshop is None:
            workshop = "1"  # по умолчанию
        
        settings = self.config.load_json_settings("shared_utils.json")
        excel_folder = settings.get("weight_orders_xlsx", "")
        
        if workshop == "2":
            filename = "weight_orders_2.xlsx"
        else:
            filename = "weight_orders.xlsx"
            
        return os.path.join(excel_folder, filename)
    
    def extract_data_for_archive(self, workshop=None, enable_pallet=False, multitype_mode=False):
        """
        Основной метод архивации с разветвлением по цехам и режимам
        """
        try:
            # 1. Определяем цех
            if workshop is None and self.coordinator:
                workshop = self.coordinator.get_workshop()
            elif workshop is None:
                workshop = "1"
            
            # 2. Определяем путь к файлу
            excel_path = self._get_excel_path(workshop)
            if not os.path.exists(excel_path):
                return {"success": False, "error": f"Файл не найден: {excel_path}"}
            
            # 3. Определяем лист
            sheet_name = self._get_sheet_for_archive(workshop, enable_pallet, multitype_mode)
            
            archive_type = self._get_archive_type(workshop, enable_pallet, multitype_mode)
            
            # 4. Извлекаем данные в зависимости от листа
            if workshop == "1":
                if multitype_mode:
                    return self._extract_multitype_sheet_first_workshop(excel_path, sheet_name)
                elif enable_pallet:
                    return self._extract_pallet_sheet_first_workshop(excel_path, sheet_name)
                else:
                    return self._extract_box_sheet_first_workshop(excel_path, sheet_name)
            else:  # workshop == "2"
                if multitype_mode:
                    return self._extract_multitype_sheet_second_workshop(excel_path, sheet_name)
                elif enable_pallet:
                    return self._extract_pallet_list_sheet_second_workshop(excel_path, sheet_name)
                else:
                    return self._extract_pallet_sheet_second_workshop(excel_path, sheet_name)
                    
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    def _get_archive_type(self, workshop, enable_pallet, multitype_mode):
        """Определяет тип архивации на основе параметров"""
        if multitype_mode:
            return "multitype"
        elif enable_pallet:
            return "pallet"
        else:
            return "box"
    
    def _get_sheet_for_archive(self, workshop, enable_pallet, multitype_mode):
        """Определяет лист для архивации на основе контекста (аналогично предпросмотру)"""
        if workshop == "1":
            if multitype_mode:
                return "Лист много видов"
            elif enable_pallet:
                return "Лист для паллеты"
            else:
                return "Лист для коробки"
        else:  # workshop == "2"
            if multitype_mode:
                return "Много видов"
            elif enable_pallet:
                return "Список поддонов"
            else:
                return "Поддон"
    
    # ==================== МЕТОДЫ ДЛЯ ЦЕХА 1 ====================
    
    def _extract_box_sheet_first_workshop(self, excel_path, sheet_name):
        """Извлекает данные из листа 'Лист для коробки' для цеха 1"""
        workbook = load_workbook(excel_path)
        sheet = workbook[sheet_name]
        
        # Базовые поля для цеха 1, коробка
        basic_fields = {
            "B1": sheet['B1'].value,  # Изготовитель
            "D5": sheet['D5'].value,  # Заказчик
            "D6": sheet['D6'].value,  # Тип упаковки
            "D8": sheet['D8'].value,  # Номер заказа
            "D10": sheet['D10'].value, # Изделие
            "F37": sheet['F37'].value, # Дата упаковки
            "E41": sheet['E41'].value, # Упаковщик
            "K2": sheet['K2'].value,   # Вес коробки
            "E39": sheet['E39'].value, # Тип продукта
            "A39": sheet['A39'].value  # TU номер
        }
        
        # Извлекаем данные роликов (строки 14-28)
        rolls = self._extract_rolls_from_box_sheet_first_workshop(sheet)
        
        archive_data = {
            "workshop": "1",
            "archive_type": "box",
            "sheet_name": sheet_name,
            "basic_fields": basic_fields,
            "rolls": rolls,
            "extraction_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        workbook.close()
        return {"success": True, "archive_data": archive_data}
    
    def _extract_rolls_from_box_sheet_first_workshop(self, sheet):
        """Извлекает данные роликов из листа 'Лист для коробки' (цех 1)"""
        rolls = []
        
        # Левый блок: B,C,D (строки 14-28)
        for row in range(14, 29):
            weight = sheet[f'B{row}'].value
            net_weight = sheet[f'C{row}'].value
            quantity = sheet[f'D{row}'].value
            
            if weight is not None or net_weight is not None or quantity is not None:
                rolls.append({
                    'position': f'B{row}',
                    'row': row,
                    'weight': weight,
                    'net_weight': net_weight,
                    'quantity': quantity,
                    'block': 'left'
                })
        
        # Правый блок: F,G,H (строки 14-28)
        for row in range(14, 29):
            weight = sheet[f'F{row}'].value
            net_weight = sheet[f'G{row}'].value
            quantity = sheet[f'H{row}'].value
            
            if weight is not None or net_weight is not None or quantity is not None:
                rolls.append({
                    'position': f'F{row}',
                    'row': row,
                    'weight': weight,
                    'net_weight': net_weight,
                    'quantity': quantity,
                    'block': 'right'
                })
        
        return rolls
    
    def _extract_pallet_sheet_first_workshop(self, excel_path, sheet_name):
        """Извлекает данные из листа 'Лист для паллеты' для цеха 1"""
        workbook = load_workbook(excel_path)
        sheet = workbook[sheet_name]
        
        # Базовые поля для цеха 1, поддон
        basic_fields = {
            "D5": sheet['D5'].value,  # Заказчик
            "D6": sheet['D6'].value,  # Тип упаковки (поддон)
            "D8": sheet['D8'].value,  # Номер заказа
            "D10": sheet['D10'].value, # Изделие
            "F37": sheet['F37'].value, # Дата упаковки
            "E41": sheet['E41'].value, # Упаковщик
            "K2": sheet['K2'].value,   # Вес поддона
            "E39": sheet['E39'].value, # Тип продукта
            "A39": sheet['A39'].value  # TU номер
        }
        
        # Извлекаем данные коробок (строки 14-28)
        boxes = self._extract_boxes_from_pallet_sheet_first_workshop(sheet)
        
        archive_data = {
            "workshop": "1",
            "archive_type": "pallet",
            "sheet_name": sheet_name,
            "basic_fields": basic_fields,
            "boxes": boxes,
            "extraction_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        workbook.close()
        return {"success": True, "archive_data": archive_data}
    
    def _extract_boxes_from_pallet_sheet_first_workshop(self, sheet):
        """Извлекает данные коробок из листа 'Лист для паллеты' (цех 1)"""
        boxes = []
        
        # Левый блок: B,C,D (строки 14-28)
        for row in range(14, 29):
            gross = sheet[f'B{row}'].value
            net = sheet[f'C{row}'].value
            quantity = sheet[f'D{row}'].value
            
            if gross is not None or net is not None or quantity is not None:
                boxes.append({
                    'position': f'B{row}',
                    'row': row,
                    'gross_weight': gross,
                    'net_weight': net,
                    'quantity': quantity,
                    'block': 'left'
                })
        
        # Правый блок: F,G,H (строки 14-28)
        for row in range(14, 29):
            gross = sheet[f'F{row}'].value
            net = sheet[f'G{row}'].value
            quantity = sheet[f'H{row}'].value
            
            if gross is not None or net is not None or quantity is not None:
                boxes.append({
                    'position': f'F{row}',
                    'row': row,
                    'gross_weight': gross,
                    'net_weight': net,
                    'quantity': quantity,
                    'block': 'right'
                })
        
        return boxes
    
    def _extract_multitype_sheet_first_workshop(self, excel_path, sheet_name):
        """Извлекает данные из листа 'Лист много видов' для цеха 1"""
        workbook = load_workbook(excel_path)
        sheet = workbook[sheet_name]
        
        # Базовые поля для цеха 1, много видов
        basic_fields = {
            "D5": sheet['D5'].value,  # Заказчик
            "D6": sheet['D6'].value,  # Тип упаковки
            "D8": sheet['D8'].value,  # Номер заказа
            "F37": sheet['F37'].value, # Дата упаковки
            "E41": sheet['E41'].value, # Упаковщик
            "K2": sheet['K2'].value,   # Вес
            "E39": sheet['E39'].value, # Тип продукта
            "A39": sheet['A39'].value  # TU номер
        }
        
        # Извлекаем данные продуктов (строки 11-28)
        products = self._extract_products_from_multitype_sheet_first_workshop(sheet)
        
        archive_data = {
            "workshop": "1",
            "archive_type": "multitype",
            "sheet_name": sheet_name,
            "basic_fields": basic_fields,
            "products": products,
            "extraction_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        workbook.close()
        return {"success": True, "archive_data": archive_data}
    
    def _extract_products_from_multitype_sheet_first_workshop(self, sheet):
        """Извлекает данные продуктов из листа 'Лист много видов' (цех 1)"""
        products = []
        
        for row in range(11, 29):
            count = sheet[f'A{row}'].value
            name = sheet[f'B{row}'].value
            gross = sheet[f'F{row}'].value
            net = sheet[f'G{row}'].value
            quantity = sheet[f'H{row}'].value
            
            if count is not None or name is not None or gross is not None or net is not None or quantity is not None:
                products.append({
                    'row': row,
                    'count': count,
                    'name': name,
                    'gross_weight': gross,
                    'net_weight': net,
                    'quantity': quantity
                })
        
        return products
    
    # ==================== МЕТОДЫ ДЛЯ ЦЕХА 2 ====================
    
    def _extract_pallet_sheet_second_workshop(self, excel_path, sheet_name):
        """Извлекает данные из листа 'Поддон' для цеха 2 (коробка)"""
        workbook = load_workbook(excel_path)
        sheet = workbook[sheet_name]
        
        # Базовые поля для цеха 2, коробка
        basic_fields = {
            "A1": sheet['A1'].value,  # Изготовитель
            "D7": sheet['D7'].value,  # Заказчик
            "D3": sheet['D3'].value,  # Тип упаковки
            "D6": sheet['D6'].value,  # Номер заказа
            "D8": sheet['D8'].value,  # Изделие
            "D37": sheet['D37'].value, # Дата упаковки
            "E41": sheet['E41'].value, # Упаковщик
            "H3": sheet['H3'].value,  # Вес коробки
            "D4": sheet['D4'].value,  # Вес втулки (кг)
            "G4": sheet['G4'].value,  # Диаметр втулки
            "E39": sheet['E39'].value, # Тип продукта
            "A39": sheet['A39'].value, # TU номер
            "D5": sheet['D5'].value   # Номер поддона
        }
        
        # Извлекаем данные роликов
        rolls = self._extract_rolls_from_pallet_sheet_second_workshop(sheet)
        
        archive_data = {
            "workshop": "2",
            "archive_type": "box",
            "sheet_name": sheet_name,
            "basic_fields": basic_fields,
            "rolls": rolls,
            "extraction_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        workbook.close()
        return {"success": True, "archive_data": archive_data}
    
    def _extract_rolls_from_pallet_sheet_second_workshop(self, sheet):
        """Извлекает данные роликов из листа 'Поддон' (цех 2)"""
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
    
    def _extract_pallet_list_sheet_second_workshop(self, excel_path, sheet_name):
        """Извлекает данные из листа 'Список поддонов' для цеха 2 (поддон)"""
        workbook = load_workbook(excel_path)
        sheet = workbook[sheet_name]
        
        # Базовые поля для цеха 2, список поддонов
        basic_fields = {
            "D7": sheet['D7'].value,  # Заказчик
            "D3": sheet['D3'].value,  # Тип упаковки
            "D6": sheet['D6'].value,  # Номер заказа
            "D8": sheet['D8'].value,  # Изделие
            "D37": sheet['D37'].value, # Дата упаковки
            "E41": sheet['E41'].value, # Упаковщик
            "H3": sheet['H3'].value,  # Вес поддона
            "D4": sheet['D4'].value,  # Вес втулки (кг)
            "G4": sheet['G4'].value,  # Диаметр втулки
            "E39": sheet['E39'].value, # Тип продукта
            "A39": sheet['A39'].value  # TU номер
        }
        
        # Извлекаем данные поддонов (строки 10-29)
        pallets = self._extract_pallets_from_list_sheet_second_workshop(sheet)
        
        archive_data = {
            "workshop": "2",
            "archive_type": "pallet",
            "sheet_name": sheet_name,
            "basic_fields": basic_fields,
            "pallets": pallets,
            "extraction_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        workbook.close()
        return {"success": True, "archive_data": archive_data}
    
    def _extract_pallets_from_list_sheet_second_workshop(self, sheet):
        """Извлекает данные поддонов из листа 'Список поддонов' (цех 2)"""
        pallets = []
        
        for row in range(10, 30):
            rolls_count = sheet[f'D{row}'].value
            total_weight = sheet[f'F{row}'].value
            total_quantity = sheet[f'H{row}'].value
            total_length = sheet[f'L{row}'].value
            
            if rolls_count is not None or total_weight is not None or total_quantity is not None:
                pallets.append({
                    'row': row,
                    'rolls_count': rolls_count,
                    'total_weight': total_weight,
                    'total_quantity': total_quantity,
                    'total_length': total_length
                })
        
        return pallets
    
    def _extract_multitype_sheet_second_workshop(self, excel_path, sheet_name):
        """Извлекает данные из листа 'Много видов' для цеха 2"""
        workbook = load_workbook(excel_path)
        sheet = workbook[sheet_name]
        
        # Базовые поля для цеха 2, много видов
        basic_fields = {
            "D7": sheet['D7'].value,  # Заказчик
            "D3": sheet['D3'].value,  # Тип упаковки
            "D6": sheet['D6'].value,  # Номер заказа
            "D37": sheet['D37'].value, # Дата упаковки
            "E41": sheet['E41'].value, # Упаковщик
            "H3": sheet['H3'].value,  # Вес
            "D4": sheet['D4'].value,  # Вес втулки (кг)
            "G4": sheet['G4'].value,  # Диаметр втулки
            "E39": sheet['E39'].value, # Тип продукта
            "A39": sheet['A39'].value  # TU номер
        }
        
        # Извлекаем данные продуктов (строки 10-29)
        products = self._extract_products_from_multitype_sheet_second_workshop(sheet)
        
        archive_data = {
            "workshop": "2",
            "archive_type": "multitype",
            "sheet_name": sheet_name,
            "basic_fields": basic_fields,
            "products": products,
            "extraction_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        workbook.close()
        return {"success": True, "archive_data": archive_data}
    
    def _extract_products_from_multitype_sheet_second_workshop(self, sheet):
        """Извлекает данные продуктов из листа 'Много видов' (цех 2)"""
        products = []
        
        for row in range(10, 30):
            count = sheet[f'A{row}'].value
            name = sheet[f'B{row}'].value
            weight = sheet[f'H{row}'].value
            quantity = sheet[f'I{row}'].value
            length = sheet[f'L{row}'].value
            
            if count is not None or name is not None or weight is not None or quantity is not None:
                products.append({
                    'row': row,
                    'count': count,
                    'name': name,
                    'weight': weight,
                    'quantity': quantity,
                    'length': length
                })
        
        return products
        
    def restore_to_excel(self, archive_data, excel_path=None):
        """Восстанавливает данные из архива в Excel с учетом типа"""
        archive_type = archive_data.get("archive_type")
        sheet_name = archive_data.get("sheet_name")
        workshop = archive_data.get("workshop", "2")
        
        if not archive_type or not sheet_name:
            return {"success": False, "error": "Не указан тип архива или лист"}
            
        # Очистка перед восстановлением
        if self.exporter:
            if workshop == "1":
                if archive_type == "box":
                    self.exporter.clear_all_rolls(enable_pallet=False, multitype_mode=False)
                elif archive_type == "pallet":
                    self.exporter.clear_all_rolls(enable_pallet=True, multitype_mode=False)
                elif archive_type == "multitype":
                    self.exporter.clear_all_rolls(enable_pallet=False, multitype_mode=True)
            else:  # workshop == "2"
                if archive_type == "box":
                    self.exporter.clear_all_rolls(enable_pallet=False, multitype_mode=False)
                elif archive_type == "pallet":
                    self.exporter.clear_all_rolls(enable_pallet=True, multitype_mode=False)
                elif archive_type == "multitype":
                    self.exporter.clear_all_rolls(enable_pallet=False, multitype_mode=True)            
        
        # Ветвление по типам
        if archive_type == "box":
            if workshop == "1":
                return self._restore_box_sheet_first_workshop(archive_data, excel_path, sheet_name)
            else:
                return self._restore_pallet_sheet_second_workshop(archive_data, excel_path, sheet_name)
        
        elif archive_type == "pallet":
            if workshop == "1":
                return self._restore_pallet_sheet_first_workshop(archive_data, excel_path, sheet_name)
            else:
                return self._restore_pallet_list_sheet_second_workshop(archive_data, excel_path, sheet_name)
        
        elif archive_type == "multitype":
            if workshop == "1":
                return self._restore_multitype_sheet_first_workshop(archive_data, excel_path, sheet_name)
            else:
                return self._restore_multitype_sheet_second_workshop(archive_data, excel_path, sheet_name)
        
        else:
            return {"success": False, "error": f"Неизвестный тип архива: {archive_type}"}
    
    def _restore_box_sheet_first_workshop(self, archive_data, excel_path, sheet_name):
        """Восстанавливает данные в лист 'Лист для коробки' для цеха 1"""
        try:
            workbook = load_workbook(excel_path)
            
            if sheet_name not in workbook.sheetnames:
                workbook.close()
                return {"success": False, "error": f"Лист '{sheet_name}' не найден"}
            
            sheet = workbook[sheet_name]
            
            # Заполняем базовые поля
            basic_fields = archive_data.get("basic_fields", {})
            for cell_address, value in basic_fields.items():
                if cell_address and value is not None:
                    sheet[cell_address] = value
                    sheet[cell_address].alignment = Alignment(horizontal='center', vertical='center')
            
            # Особые обработки
            if "D10" in basic_fields and basic_fields["D10"] is not None:
                sheet["D10"].alignment = Alignment(horizontal='left', vertical='top', wrap_text=True)
            
            if "B1" in basic_fields and basic_fields["B1"] is not None:
                sheet["B1"].alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            
            # Заполняем ролики
            rolls = archive_data.get("rolls", [])
            for roll in rolls:
                position = roll.get('position')
                if position and roll.get('weight') is not None:
                    sheet[position] = roll["weight"]
                
                # Для net_weight (колонка C)
                if roll.get('net_weight') is not None:
                    row = roll.get('row')
                    if row:
                        sheet[f'C{row}'] = roll["net_weight"]
                
                # Для quantity (колонка D)
                if roll.get('quantity') is not None:
                    row = roll.get('row')
                    if row:
                        sheet[f'D{row}'] = roll["quantity"]
            
            workbook.save(excel_path)
            workbook.close()
            
            return {
                "success": True,
                "sheet_name": sheet_name,
                "order": basic_fields.get("D8", "неизвестно")
            }
            
        except Exception as e:
            return {"success": False, "error": f"Ошибка восстановления цех 1, коробка: {str(e)}"}
            
    def _restore_pallet_sheet_first_workshop(self, archive_data, excel_path, sheet_name):
        """Восстанавливает данные в лист 'Лист для паллеты' для цеха 1"""
        try:
            workbook = load_workbook(excel_path)
            
            if sheet_name not in workbook.sheetnames:
                workbook.close()
                return {"success": False, "error": f"Лист '{sheet_name}' не найден"}
            
            sheet = workbook[sheet_name]
            
            # Заполняем базовые поля
            basic_fields = archive_data.get("basic_fields", {})
            for cell_address, value in basic_fields.items():
                if cell_address and value is not None:
                    sheet[cell_address] = value
                    sheet[cell_address].alignment = Alignment(horizontal='center', vertical='center')
            
            # Особые обработки
            if "D10" in basic_fields and basic_fields["D10"] is not None:
                sheet["D10"].alignment = Alignment(horizontal='left', vertical='top', wrap_text=True)
            
            # Заполняем коробки
            boxes = archive_data.get("boxes", [])
            for box in boxes:
                position = box.get('position')
                if position and box.get('gross_weight') is not None:
                    sheet[position] = box["gross_weight"]
                
                # Для net_weight (колонка C)
                if box.get('net_weight') is not None:
                    row = box.get('row')
                    if row:
                        sheet[f'C{row}'] = box["net_weight"]
                
                # Для quantity (колонка D)
                if box.get('quantity') is not None:
                    row = box.get('row')
                    if row:
                        sheet[f'D{row}'] = box["quantity"]
                
                # Правый блок: F,G,H
                if box.get('block') == 'right':
                    row = box.get('row')
                    if row:
                        if box.get('gross_weight') is not None:
                            sheet[f'F{row}'] = box["gross_weight"]
                        if box.get('net_weight') is not None:
                            sheet[f'G{row}'] = box["net_weight"]
                        if box.get('quantity') is not None:
                            sheet[f'H{row}'] = box["quantity"]
            
            workbook.save(excel_path)
            workbook.close()
            
            return {
                "success": True,
                "sheet_name": sheet_name,
                "order": basic_fields.get("D8", "неизвестно")
            }
            
        except Exception as e:
            return {"success": False, "error": f"Ошибка восстановления цех 1, поддон: {str(e)}"}

    def _restore_multitype_sheet_first_workshop(self, archive_data, excel_path, sheet_name):
        """Восстанавливает данные в лист 'Лист много видов' для цеха 1"""
        try:
            workbook = load_workbook(excel_path)
            
            if sheet_name not in workbook.sheetnames:
                workbook.close()
                return {"success": False, "error": f"Лист '{sheet_name}' не найден"}
            
            sheet = workbook[sheet_name]
            
            # Заполняем базовые поля
            basic_fields = archive_data.get("basic_fields", {})
            for cell_address, value in basic_fields.items():
                if cell_address and value is not None:
                    sheet[cell_address] = value
                    sheet[cell_address].alignment = Alignment(horizontal='center', vertical='center')
            
            # Заполняем продукты
            products = archive_data.get("products", [])
            for product in products:
                row = product.get('row')
                if not row or row < 11 or row > 28:
                    continue
                
                if product.get('count') is not None:
                    sheet[f'A{row}'] = product["count"]
                
                if product.get('name') is not None:
                    sheet[f'B{row}'] = product["name"]
                
                if product.get('gross_weight') is not None:
                    sheet[f'F{row}'] = product["gross_weight"]
                
                if product.get('net_weight') is not None:
                    sheet[f'G{row}'] = product["net_weight"]
                
                if product.get('quantity') is not None:
                    sheet[f'H{row}'] = product["quantity"]
            
            workbook.save(excel_path)
            workbook.close()
            
            return {
                "success": True,
                "sheet_name": sheet_name,
                "order": basic_fields.get("D8", "неизвестно")
            }
            
        except Exception as e:
            return {"success": False, "error": f"Ошибка восстановления цех 1, много видов: {str(e)}"}

    def _restore_pallet_sheet_second_workshop(self, archive_data, excel_path, sheet_name):
        """Восстанавливает данные в лист 'Поддон' для цеха 2 (коробка)"""
        try:
            workbook = load_workbook(excel_path)
            
            if sheet_name not in workbook.sheetnames:
                workbook.close()
                return {"success": False, "error": f"Лист '{sheet_name}' не найден"}
            
            sheet = workbook[sheet_name]
            
            # Заполняем базовые поля
            basic_fields = archive_data.get("basic_fields", {})
            for cell_address, value in basic_fields.items():
                if cell_address and value is not None:
                    sheet[cell_address] = value
                    sheet[cell_address].alignment = Alignment(horizontal='center', vertical='center')
            
            # Особые обработки
            if "D8" in basic_fields and basic_fields["D8"] is not None:
                sheet["D8"].alignment = Alignment(horizontal='left', vertical='top', wrap_text=True)
            
            if "A1" in basic_fields and basic_fields["A1"] is not None:
                sheet["A1"].alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            
            # Заполняем ролики
            rolls = archive_data.get("rolls", [])
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
            
            workbook.save(excel_path)
            workbook.close()
            
            return {
                "success": True,
                "sheet_name": sheet_name,
                "order": basic_fields.get("D6", "неизвестно"),
                "pallet_number": basic_fields.get("D5", "неизвестно")
            }
            
        except Exception as e:
            return {"success": False, "error": f"Ошибка восстановления цех 2, коробка: {str(e)}"}

    def _restore_pallet_list_sheet_second_workshop(self, archive_data, excel_path, sheet_name):
        """Восстанавливает данные в лист 'Список поддонов' для цеха 2"""
        try:
            workbook = load_workbook(excel_path)
            
            if sheet_name not in workbook.sheetnames:
                workbook.close()
                return {"success": False, "error": f"Лист '{sheet_name}' не найден"}
            
            sheet = workbook[sheet_name]
            
            # Заполняем базовые поля
            basic_fields = archive_data.get("basic_fields", {})
            for cell_address, value in basic_fields.items():
                if cell_address and value is not None:
                    sheet[cell_address] = value
                    sheet[cell_address].alignment = Alignment(horizontal='center', vertical='center')
            
            # Особые обработки
            if "D8" in basic_fields and basic_fields["D8"] is not None:
                sheet["D8"].alignment = Alignment(horizontal='left', vertical='top', wrap_text=True)
            
            # Заполняем поддоны
            pallets = archive_data.get("pallets", [])
            for pallet in pallets:
                row = pallet.get('row')
                if not row or row < 10 or row > 29:
                    continue
                
                if pallet.get('rolls_count') is not None:
                    sheet[f'D{row}'] = pallet["rolls_count"]
                
                if pallet.get('total_weight') is not None:
                    sheet[f'F{row}'] = pallet["total_weight"]
                
                if pallet.get('total_quantity') is not None:
                    sheet[f'H{row}'] = pallet["total_quantity"]
                
                if pallet.get('total_length') is not None:
                    sheet[f'L{row}'] = pallet["total_length"]
            
            workbook.save(excel_path)
            workbook.close()
            
            return {
                "success": True,
                "sheet_name": sheet_name,
                "order": basic_fields.get("D6", "неизвестно")
            }
            
        except Exception as e:
            return {"success": False, "error": f"Ошибка восстановления цех 2, список поддонов: {str(e)}"}

    def _restore_multitype_sheet_second_workshop(self, archive_data, excel_path, sheet_name):
        """Восстанавливает данные в лист 'Много видов' для цеха 2"""
        try:
            workbook = load_workbook(excel_path)
            
            if sheet_name not in workbook.sheetnames:
                workbook.close()
                return {"success": False, "error": f"Лист '{sheet_name}' не найден"}
            
            sheet = workbook[sheet_name]
            
            # Заполняем базовые поля
            basic_fields = archive_data.get("basic_fields", {})
            for cell_address, value in basic_fields.items():
                if cell_address and value is not None:
                    sheet[cell_address] = value
                    sheet[cell_address].alignment = Alignment(horizontal='center', vertical='center')
            
            # Заполняем продукты
            products = archive_data.get("products", [])
            for product in products:
                row = product.get('row')
                if not row or row < 10 or row > 29:
                    continue
                
                if product.get('count') is not None:
                    sheet[f'A{row}'] = product["count"]
                
                if product.get('name') is not None:
                    sheet[f'B{row}'] = product["name"]
                
                if product.get('weight') is not None:
                    sheet[f'H{row}'] = product["weight"]
                
                if product.get('quantity') is not None:
                    sheet[f'I{row}'] = product["quantity"]
                
                if product.get('length') is not None:
                    sheet[f'L{row}'] = product["length"]
            
            workbook.save(excel_path)
            workbook.close()
            
            return {
                "success": True,
                "sheet_name": sheet_name,
                "order": basic_fields.get("D6", "неизвестно")
            }
            
        except Exception as e:
            return {"success": False, "error": f"Ошибка восстановления цех 2, много видов: {str(e)}"}            
