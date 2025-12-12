import os
import sys
import configparser
import json
from pathlib import Path

class ConfigManager:
    def __init__(self):
        # Базовые пути
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.core_dir = os.path.join(self.base_dir, "core")
        
        # Папка для данных в AppData/Local/CodeMax-CutMaster
        appdata_path = os.getenv('LOCALAPPDATA')
        self.data_dir = Path(appdata_path) / "CodeMax-CutMaster" / "data"

        # Создаем папку data если ее нет
        os.makedirs(self.data_dir, exist_ok=True)

        # Добавляем core в sys.path
        self.add_core_to_path()

        # Список резчиков по умолчанию
        self.default_cutters = ["Некрасов", "Смирнов", "Шамшурин"]
        # Список упаковщиков по умолчанию
        self.default_packers = ["Некрасов", "Арзамасцев", "Малых"]     

    def get_preview_printers(self):
        """Возвращает сохраненные принтеры для предпросмотра Excel"""
        settings = self.load_json_settings("print_settings.json")
        return settings.get("preview_printers", {"printer1": "", "printer2": ""})

    def save_preview_printers(self, printer1, printer2):
        """Сохраняет выбранные принтеры для предпросмотра Excel"""
        settings = self.load_json_settings("print_settings.json")
        settings["preview_printers"] = {
            "printer1": printer1,
            "printer2": printer2
        }
        return self.save_json_settings("print_settings.json", settings)
        
    def get_system_printers(self):
        """Возвращает список системных принтеров"""
        try:
            import win32print
            printers = win32print.EnumPrinters(2)  # PRINTER_ENUM_LOCAL | PRINTER_ENUM_CONNECTIONS
            return [p[2] for p in printers]  # Имя принтера
        except Exception as e:
            print(f"Ошибка получения списка принтеров: {e}")
            return []
        
    # Архивация 2 цех
    def get_pallet_archive(self):
        """Загружает архив поддонов из файла"""
        archive = self.load_json_settings("archive_pallets.json")
        if not archive:
            archive = {
                "workshop": "2",
                "pallets": []
            }

        return archive

    def save_pallet_archive(self, archive_data):
        """Сохраняет архив поддонов в файл"""
        return self.save_json_settings("archive_pallets.json", archive_data)

    def add_pallet_to_archive(self, pallet_data):
        """Просто добавляет данные поддона в архив"""
        try:
            archive = self.get_pallet_archive()         
            
            # Добавляем данные как есть
            archive["pallets"].append(pallet_data)
            
            # Сохраняем
            self.save_pallet_archive(archive)
            
            return True  # Просто успешное завершение
            
        except Exception as e:
            print(f"Ошибка добавления в архив: {e}")
            return False
        
    def get_asset_path(self, filename):
        """Возвращает полный путь к файлу в папке assets для бинарника и исходника"""
        if hasattr(sys, '_MEIPASS'):
            # Режим бинарника - путь: CodeMax-CutMaster\_internal\assets
            base_path = os.path.dirname(sys.executable)
            assets_file = os.path.join(base_path, "_internal", "assets", filename)
        else:
            # Режим разработки - assets в той же папке что и проект
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # Поднимаемся на один уровень вверх от core к корню проекта
            project_root = os.path.dirname(current_dir)
            assets_file = os.path.join(project_root, "assets", filename)
        
        return assets_file
        
    def get_font_settings(self):
        """Загружает настройки шрифтов: сначала из data, если нет - копирует из assets"""
        data_path = self.get_settings_path("label_font_settings.json")
        asset_path = self.get_asset_path("label_font_settings.json")
        
        # Пробуем загрузить из data (пользовательские настройки)
        if os.path.exists(data_path):
            settings = self.load_json_settings("label_font_settings.json")
            if settings:
                return settings
        
        # Если в data нет, копируем из assets
        if os.path.exists(asset_path):
            try:
                with open(asset_path, "r", encoding="utf-8") as f:
                    default_settings = json.load(f)
                # Сохраняем копию в data
                self.save_json_settings("label_font_settings.json", default_settings)
                return default_settings
            except Exception as e:
                print(f"Ошибка копирования настроек шрифтов: {e}")
        
        # Если ничего нет, возвращаем пустой словарь
        return {}
        
    def ensure_packaging_tu_exists(self):
        """Обеспечивает наличие packaging_tu.json в data/"""
        import shutil
        
        data_file = self.data_dir / "packaging_tu.json"
        
        # Если файл уже существует в data - проверяем валидность
        if os.path.exists(data_file):
            try:
                with open(data_file, 'r', encoding='utf-8') as f:
                    json.load(f)
                return True  # Файл существует и валиден
            except json.JSONDecodeError:
                # Файл поврежден - будет пересоздан
                print(f"Файл {data_file} поврежден, пересоздаю...")
        
        # Пробуем найти исходный файл в нескольких местах
        source_paths = [
            self.get_asset_path("packaging_tu.json"),           # assets/
            os.path.join(self.core_dir, "packaging_tu.json"),   # core/
            os.path.join(self.base_dir, "config", "packaging_tu.json"),  # config/
        ]
        
        for source_path in source_paths:
            if os.path.exists(source_path):
                try:
                    shutil.copy2(source_path, data_file)
                    print(f"Скопировано: {source_path} -> {data_file}")
                    return True
                except Exception as e:
                    print(f"Ошибка копирования {source_path}: {e}")
        
        print(f"ВНИМАНИЕ: packaging_tu.json не найден!")
        return False
        
    def reload_settings(self):
        """Перезагружает настройки из файлов"""
        try:
            # Сбрасываем кэш или перечитываем файлы
            if hasattr(self, '_settings_cache'):
                del self._settings_cache
        except Exception as e:
            print(f"Ошибка перезагрузки настроек: {e}")
        
    def get_default_cutter(self):
        """Возвращает первого резчика из списка или пустую строку"""
        cutters = self.get_cutters()
        return cutters[0] if cutters else ""        

    def add_core_to_path(self):
        """Добавляет папку core в sys.path"""
        if self.core_dir not in sys.path:
            sys.path.insert(0, self.core_dir)

    def get_settings_path(self, filename):
        return os.path.join(self.data_dir, filename)
        
    def get_packers(self):
        """Возвращает список упаковщиков из настроек или значение по умолчанию"""
        settings = self.load_json_settings("shared_utils.json")
        return settings.get("packers", self.default_packers)

    def save_packers(self, packers_list):
        """Сохраняет список упаковщиков в настройки"""
        settings = self.load_json_settings("shared_utils.json")
        settings["packers"] = packers_list
        return self.save_json_settings("shared_utils.json", settings)
        
    def get_manufacturer(self):
        """Получает название производителя из shared_utils.json"""
        settings = self.load_json_settings("shared_utils.json")
        return settings.get("manufacturer", "")
    
    def save_manufacturer(self, manufacturer_name):
        """Сохраняет название производителя в shared_utils.json"""
        settings = self.load_json_settings("shared_utils.json")
        settings["manufacturer"] = manufacturer_name
        return self.save_json_settings("shared_utils.json", settings)
        
    def get_data_base_path(self):
        """Возвращает путь к базе данных из настроек"""
        settings = self.load_json_settings("shared_utils.json")
        return settings.get("data_base", "")

    def save_data_base_path(self, path):
        """Сохраняет путь к базе данных в настройки"""
        settings = self.load_json_settings("shared_utils.json")
        settings["data_base"] = path
        return self.save_json_settings("shared_utils.json", settings)

    def get_shortening_rules_path(self):
        """Возвращает путь к базе сокращений из настроек"""
        settings = self.load_json_settings("shared_utils.json")
        return settings.get("shortening_rules", "")

    def save_shortening_rules_path(self, path):
        """Сохраняет путь к базе сокращений в настройки"""
        settings = self.load_json_settings("shared_utils.json")
        settings["shortening_rules"] = path
        return self.save_json_settings("shared_utils.json", settings)

    def get_special_clients(self):
        """Возвращает словарь особых заказчиков из настроек"""
        settings = self.load_json_settings("shared_utils.json")
        return settings.get("special_clients", {})

    def find_special_client(self, search_text):
        """Ищет заказчика в словаре special_clients (регистронезависимый поиск по ключу)"""
        special_clients = self.get_special_clients()
        search_text_lower = search_text.lower().strip()

        for client_name, client_text in special_clients.items():
            if search_text_lower in client_name.lower():
                return client_name, client_text
        return None, None

    # Список заказчиков без производителя
    def get_without_manufacturer_customers(self):
        """Возвращает список заказчиков без производителя"""
        settings = self.load_json_settings("shared_utils.json")
        return settings.get("without_manufacturer", [])

    def find_customer(self, search_text):
        """Ищет заказчика в списке without_manufacturer (регистронезависимый поиск)"""
        customers = self.get_without_manufacturer_customers()
        search_text_lower = search_text.lower().strip()

        for customer in customers:
            if search_text_lower in customer.lower():
                return customer
        return None

    # Настройки принтеров
    def load_json_settings(self, filename):
        # Для packaging_tu.json сначала обеспечиваем его наличие
        if filename == "packaging_tu.json":
            self.ensure_packaging_tu_exists()
            
        path = self.get_settings_path(filename)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Ошибка загрузки настроек {filename}: {e}")
                return {}
        return {}

    def save_json_settings(self, filename, data):
        path = self.get_settings_path(filename)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Ошибка сохранения настроек {filename}: {e}")
            return False

    # Список резчиков
    def get_cutters(self):
        """Возвращает список резчиков из настроек или значение по умолчанию"""
        settings = self.load_json_settings("shared_utils.json")
        return settings.get("cutters", self.default_cutters)

    def save_cutters(self, cutters_list):
        """Сохраняет список резчиков в настройки"""
        settings = self.load_json_settings("shared_utils.json")
        settings["cutters"] = cutters_list
        return self.save_json_settings("shared_utils.json", settings)

    # Коэффициент резки
    def get_waste_coef(self):
        """Возвращает коэффициент из настроек или значение по умолчанию"""
        settings = self.load_json_settings("shared_utils.json")
        return settings.get("waste_coef", "1.0")

    def save_waste_coef(self, waste_coef):
        """Сохраняет коэффициент в настройки"""
        settings = self.load_json_settings("shared_utils.json")
        settings["waste_coef"] = waste_coef
        return self.save_json_settings("shared_utils.json", settings)

    # Настройки натяжения
    def get_taper_settings(self):
        """Возвращает список настроек натяжения из общей базы"""
        settings = self.load_json_settings("taper_settings.json")
        return settings.get("orders", [])

    def save_taper_settings(self, orders_list):
        """Сохраняет список настроек натяжения в общую базу"""
        settings = {"orders": orders_list}
        return self.save_json_settings("taper_settings.json", settings)

    def get_taper_settings_from_folder(self, folder_path):
        """Загружает настройки натяжения из указанной папки"""
        if not folder_path:
            return []
        
        taper_path = Path(folder_path) / "taper_settings.json"
        if taper_path.exists():
            try:
                with open(taper_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("orders", [])
            except Exception as e:
                print(f"Ошибка загрузки настроек из {taper_path}: {e}")
        return []

    def save_taper_settings_to_folder(self, folder_path, orders_list):
        """Сохраняет настройки натяжения в указанную папку"""
        if not folder_path:
            return False
        
        taper_path = Path(folder_path) / "taper_settings.json"
        try:
            with open(taper_path, "w", encoding="utf-8") as f:
                json.dump({"orders": orders_list}, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Ошибка сохранения настроек в {taper_path}: {e}")
            return False

    def get_local_taper_settings(self):
        """Возвращает локальные настройки станка"""
        settings = self.load_json_settings("shared_utils.json")
        return settings.get("taper_machine_settings", {})

    def save_local_taper_settings(self, settings):
        """Сохраняет локальные настройки станка"""
        all_settings = self.load_json_settings("shared_utils.json")
        all_settings["taper_machine_settings"] = settings
        return self.save_json_settings("shared_utils.json", all_settings)

    # Диапазоны
    def load_diapazon_ranges(self):
        """Загружает диапазоны из отдельного файла"""
        return self.load_json_settings("diapazon_ranges.json")

    def save_diapazon_ranges(self, ranges_data):
        """Сохраняет диапазоны в отдельный файл"""
        return self.save_json_settings("diapazon_ranges.json", ranges_data)

    def clear_diapazon_ranges(self):
        """Очищает файл диапазонов"""
        return self.save_json_settings("diapazon_ranges.json", {})
        
    # Добавляем методы для размера диапазона
    def get_diapazon_range_size(self):
        """Возвращает размер диапазона из настроек или значение по умолчанию"""
        settings = self.load_json_settings("shared_utils.json")
        diapazon_settings = settings.get("diapazon_settings", {})
        return diapazon_settings.get("diapazon_range", 321408)

    def save_diapazon_range_size(self, range_size):
        """Сохраняет размер диапазона в настройки"""
        settings = self.load_json_settings("shared_utils.json")
        if "diapazon_settings" not in settings:
            settings["diapazon_settings"] = {}
        settings["diapazon_settings"]["diapazon_range"] = range_size
        return self.save_json_settings("shared_utils.json", settings)

    def get_diapazon_range_streams(self):
        """Возвращает количество ручьёв из настроек или значение по умолчанию 16"""
        settings = self.load_json_settings("shared_utils.json")
        diapazon_settings = settings.get("diapazon_settings", {})
        return diapazon_settings.get("range_streams", 16)

    def save_diapazon_range_streams(self, range_streams):
        """Сохраняет количество ручьёв в настройки"""
        settings = self.load_json_settings("shared_utils.json")
        if "diapazon_settings" not in settings:
            settings["diapazon_settings"] = {}
        settings["diapazon_settings"]["range_streams"] = range_streams
        return self.save_json_settings("shared_utils.json", settings)

    # Обновление принтеров по умолчанию
    def update_printer_settings(self, printer_name):
        """Обновляет принтер во всех секциях настроек"""
        settings = self.load_json_settings("print_settings.json")

        printer_sections = [
            "obc_labels",
            "syc_rolls",
            "syc_register",
            "code_labels",
            "diapazon",
            "technomed",
            "print_set_double",
            "print_set_single",
            "weight_labels",
            "weight_roll_labels",
            "weight_box_print",
        ]
        updated = False

        for section in printer_sections:
            if section in settings:
                if settings[section].get("printer") != printer_name:
                    settings[section]["printer"] = printer_name
                    updated = True
            else:
                # Если секции нет, создаем ее с принтером по умолчанию
                # но сохраняем другие существующие настройки секции
                if section not in settings:
                    settings[section] = {}
                settings[section]["printer"] = printer_name
                updated = True

        # Сохраняем только если были изменения
        if updated:
            return self.save_json_settings("print_settings.json", settings)

        return True
