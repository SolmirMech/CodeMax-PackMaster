import json
import os
import sys
from pathlib import Path
import shutil


# noinspection SpellCheckingInspection,PyTypeChecker
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

    def get_packaging_log_path(self):
        """Возвращает текущий путь к журналу из настроек"""
        settings = self.load_json_settings("shared_utils.json")
        return settings.get("packaging_log_file", "")

    def get_packaging_log_template(self):
        """Возвращает путь к шаблону журнала упаковки"""
        return self.get_asset_path("packaging_log_template.xlsx")

    def create_restored_log_path(self):
        """Создаёт путь для восстановленного журнала"""
        from datetime import datetime
        date_str = datetime.now().strftime("%d.%m.%Y")

        # Пробуем использовать папку из настроек
        settings_path = self.get_packaging_log_path()
        if settings_path and os.path.exists(os.path.dirname(settings_path)):
            target_dir = os.path.dirname(settings_path)
        else:
            target_dir = self.data_dir

        filename = f"packaging_log_восстановлено_{date_str}.xlsx"
        return os.path.join(target_dir, filename)

    @staticmethod
    def get_asset_path(filename):
        """Возвращает полный путь к файлу в папке assets для бинарника и исходника"""
        if hasattr(sys, '_MEIPASS'):
            # Режим бинарника - путь: CodeMax-CutMaster\_internal\assets
            base_path = os.path.dirname(sys.executable)
            assets_file = os.path.join(base_path, "_internal", "assets", filename)
        else:
            # Режим разработки - assets в той же папке, что и проект
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # Поднимаемся на один уровень вверх от core к корню проекта
            project_root = os.path.dirname(current_dir)
            assets_file = os.path.join(project_root, "assets", filename)

        return assets_file

    def ensure_excel_file_exists(self, filename: str, target_folder: str = None) -> str:
        """
        Проверяет существование Excel файла в целевой папке,
        при необходимости копирует из assets

        Args:
            filename: Имя файла (weight_orders.xlsx, no_weight_orders.xlsx, weight_orders_2.xlsx)
            target_folder: Папка назначения (обычно weight_orders_xlsx из настроек)

        Returns:
            Полный путь к файлу
        """
        if not target_folder:
            # Если папка не указана, берём из настроек
            settings = self.load_json_settings("shared_utils.json")
            target_folder = settings.get("weight_orders_xlsx", "")

        target_path = os.path.join(target_folder, filename)

        # Если файл уже существует - возвращаем путь
        if os.path.exists(target_path):
            return target_path

        # Пробуем скопировать из assets
        asset_path = self.get_asset_path(filename)
        if os.path.exists(asset_path):
            import shutil
            # Создаём целевую папку, если её нет
            os.makedirs(target_folder, exist_ok=True)
            shutil.copy2(asset_path, target_path)
            print(f"Файл {filename} скопирован из assets в {target_path}")
            return target_path

        # Если файла нет ни в target, ни в assets - ошибка
        raise FileNotFoundError(f"Файл {filename} не найден в {target_folder} и в assets")

    def get_preview_printers(self):
        """Возвращает сохраненные принтеры для предпросмотра Excel"""
        settings = self.load_json_settings("print_settings.json")
        printers = settings.get("preview_printers", {"printer1": "", "printer2": ""})
        
        # Гарантируем что возвращаем строки, а не None
        return {
            "printer1": printers.get("printer1") or "",  # None → ""
            "printer2": printers.get("printer2") or ""   # None → ""
        }

    def save_preview_printers(self, printer1, printer2):
        """Сохраняет принтеры для предпросмотра"""
        try:
            # Нормализуем: None → ""
            printer1 = printer1 or ""
            printer2 = printer2 or ""
            
            settings = self.load_json_settings("print_settings.json")
            
            if "preview_printers" not in settings:
                settings["preview_printers"] = {}
                
            settings["preview_printers"]["printer1"] = printer1
            settings["preview_printers"]["printer2"] = printer2
            
            return self.save_json_settings("print_settings.json", settings)
            
        except Exception as e:
            print(f"Ошибка сохранения принтеров: {e}")
            return False

    @staticmethod
    def get_system_printers():
        """Возвращает список системных принтеров"""
        try:
            import win32print
            printers = win32print.EnumPrinters(2)
            return [p[2] for p in printers]
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

    def ensure_templates_list_exists(self):
        """Обеспечивает наличие templates_list.json в data/, копирует из assets если нужно"""
        settings_path = self.get_settings_path("templates_list.json")

        # Если файл уже существует - ок
        if os.path.exists(settings_path):
            return True

        # Пробуем скопировать из assets
        try:
            asset_path = self.get_asset_path("templates_list.json")

            if os.path.exists(asset_path):
                # noinspection PyTypeChecker
                shutil.copy2(asset_path, settings_path)
                print(f"Файл templates_list.json скопирован из {asset_path} в {settings_path}")
                return True
            else:
                # Создаём начальный файл
                initial_templates = {
                    "roll_templates": {
                        "Обычный ролик 1 цех 90x72": "roll.pdf",
                        "Маленький ролик 1 цех 70x50": "1_cex_small_roll.pdf",
                        "Обычный ролик 2 цех 80x57": "2_cex_roll.pdf",
                        "Росинка 71х89": "rosinka_roll.pdf",
                        "Пермалко ролик 90х72": "permalko_roll.pdf",
                        "Пермалко малый ролик 70х50": "permalko_small_roll.pdf"
                    },
                    "box_templates": {
                        "Обычная коробка 98х72": "box.pdf",
                        "Пермалко коробка 98х72": "permalko_box.pdf"
                    }
                }
                self.save_json_settings("templates_list.json", initial_templates)
                print(f"Создан начальный файл templates_list.json в {settings_path}")
                return True

        except Exception as e:
            print(f"Ошибка при создании templates_list.json: {e}")
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
        
    def get_weight_data_base_path(self):
        """Возвращает путь к базе данных из настроек"""
        settings = self.load_json_settings("shared_utils.json")
        return settings.get("weight_data_base", "")        

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

        # Для templates_list.json обеспечиваем наличие
        if filename == "templates_list.json":
            self.ensure_templates_list_exists()
            
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
