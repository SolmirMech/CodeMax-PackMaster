# main.py
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
import configparser
from datetime import datetime
from core.settings.settings_coordinator import SettingsCoordinator

def check_demo_mode():
    """Проверяет, не истек ли демо-период"""
    if getattr(sys, 'frozen', False):
        # Если программа собрана в EXE
        application_path = os.path.dirname(sys.executable)
        demo_file = os.path.join(application_path, '_internal', '_tkinter.ini')
    else:
        # Если запуск из Python
        application_path = os.path.dirname(__file__)
        demo_file = os.path.join(application_path, '_internal', '_tkinter.ini')
    
    # Если файла нет - это полная версия
    if not os.path.exists(demo_file):
        return True
    
    try:
        config = configparser.ConfigParser()
        config.read(demo_file, encoding='utf-8')
        
        if 'Demo' not in config:
            return True
            
        install_date = datetime.strptime(config['Demo']['InstallDate'], '%Y-%m-%d')
        expire_days = int(config['Demo']['ExpireDays'])
        
        days_passed = (datetime.now() - install_date).days
        if days_passed > expire_days:
            messagebox.showerror(
                "Демо-период истек", 
                f"Демо-версия активна {days_passed} из {expire_days} дней.\n\n"
                "Для приобретения полной версии обратитесь к разработчику."
            )
            return False
        else:
            days_left = expire_days - days_passed
            if days_left <= 1:
                messagebox.showwarning(
                    "Скоро истекает демо", 
                    f"Демо-период истекает через {days_left} день!\n"
                    "Свяжитесь с разработчиком для покупки."
                )
    except Exception as e:
        messagebox.showerror("Ошибка демо-режима", f"Невозможно проверить лицензию: {str(e)}")
        return False
    
    return True


# noinspection PyTypeChecker
class WeightOrdersApp:
    def __init__(self, parent):
        self.root = parent
        self.root.title("Мастер упаковки CodeMax-PackMaster")
        self.root.geometry("1500x950")

        # Объявляем все атрибуты модулей
        self.roll_module = None
        self.order_data_module = None
        self.preview_module = None
        self.print_module = None
        self.export_module = None
        self.style = None
        self.coordinator = None
        self.config_manager = None
        self.data_manager = None
        self.settings_manager = None
        
        # Инициализация ConfigManager (менеджер настроек)
        from core.config_manager import ConfigManager
        self.config_manager = ConfigManager()
        # Инициализация SettingsCoordinator (координатор настроек)
        self.coordinator = SettingsCoordinator(self.config_manager)
        # Инициализация XMLDataManager (менеджер создания БД)
        from core.data_manager import XMLDataManager
        self.data_manager = XMLDataManager(
            self.config_manager,
            coordinator=self.coordinator,
            root=self.root
        )

        # Установка стилей
        self.setup_styles()
        
        self.create_ui()
        self.center_window()
        self.root.after(200, self.data_manager.initial_scan) # Запуск фонового сканирования
        # noinspection PyArgumentList,PyTypeChecker
        root.after(100, self.set_initial_focus)

    def set_initial_focus(self):
        """Устанавливает фокус на поле номера заказа при запуске"""
        if hasattr(self, 'roll_module'):
            # Находим поле order_number в roll_module
            if hasattr(self.roll_module, 'order_entry'):
                self.roll_module.order_entry.focus_set()        

    def setup_styles(self):
        """Настройка стилей"""
        self.style = ttk.Style()
        self.style.configure(".", font=("Arial", 16))
        self.style.configure("Bold.TLabel", font=("Arial", 16, "bold"))
        self.style.configure("Large.TLabel", font=("Arial", 24))
        self.style.configure(
            "LargeGreen.TLabel", font=("Arial", 24), foreground="green"
        )
        self.style.configure("LargeBlue.TLabel", font=("Arial", 24), foreground="blue")
        self.style.configure("LargeRed.TLabel", font=("Arial", 24), foreground="red")
        self.style.configure("Validation.TLabel", font=("Arial", 14))
        self.style.configure("ValidationGreen.TLabel", font=("Arial", 14), foreground="green")
        self.style.configure("ValidationRed.TLabel", font=("Arial", 14), foreground="red")  
        self.style.configure("ValidationOrange.TLabel", font=("Arial", 14), foreground="orange")

    def create_ui(self):
        """Создает интерфейс с вкладками"""
        # Создаем вкладки
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Создаем фрейм для вкладки ролика
        roll_preview_frame = ttk.Frame(notebook, padding=5)

        # Создаем объединенный интерфейс для ролика и предпросмотра
        self.create_roll_preview_interface(roll_preview_frame)

        # Добавляем вкладку
        notebook.add(roll_preview_frame, text="Основное окно упаковки")

    def create_roll_preview_interface(self, parent):
        """Создает объединенный интерфейс для ролика и предпросмотра"""
        container = ttk.Frame(parent)
        container.pack(fill=tk.BOTH, expand=True)
        
        # Настраиваем пропорции колонок
        container.columnconfigure(0, weight=1)  # Левая часть
        container.columnconfigure(1, weight=1)  # Правая часть
        container.rowconfigure(0, weight=1)     # Одна строка

        # Левая часть
        left_frame = ttk.Frame(container)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 2))
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(0, weight=1)    # RollLabelPrinter
        left_frame.rowconfigure(1, weight=1)    # OrderDataProcessor

        # Правая часть
        right_frame = ttk.Frame(container)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        right_frame.columnconfigure(0, weight=2)  # Превью
        right_frame.columnconfigure(1, weight=1)  # Экспорт
        right_frame.rowconfigure(0, weight=1)     # Одна строка

        # Верх - RollLabelPrinter
        roll_frame = ttk.Frame(left_frame)
        roll_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 2))
        self.roll_module = RollLabelPrinter(roll_frame, self.coordinator, self.data_manager, self.config_manager)

        # Низ - OrderDataProcessor
        order_data_frame = ttk.Frame(left_frame)
        order_data_frame.grid(row=1, column=0, sticky="nsew", pady=(2, 0))
        self.order_data_module = OrderDataProcessor(
            order_data_frame, 
            self.coordinator, 
            self.data_manager,
            self.config_manager
)

        # Правая часть - RollPreview (слева от печати и экспорта)
        preview_frame = ttk.Frame(right_frame)
        preview_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 2))
        self.preview_module = RollPreview(preview_frame, self.coordinator, self.config_manager)
        
        # Правая часть - PrintModule и ExportModule (справа от предпросмотра)
        print_export_frame = ttk.Frame(right_frame)
        print_export_frame.grid(row=0, column=1, sticky="nsew", padx=(2, 0))

        # Вертикальное разделение Печать/Экспорт
        print_export_frame.columnconfigure(0, weight=1)
        print_export_frame.rowconfigure(0, weight=1)  # Печать (верх)
        print_export_frame.rowconfigure(1, weight=1)  # Экспорт (низ)

        # Модуль Печати (верх)
        print_frame = ttk.Frame(print_export_frame)
        print_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 2))
        self.print_module = PrintModule(print_frame, self.preview_module, self.coordinator, self.config_manager)

        # Модуль Экспорта (низ)
        export_frame = ttk.Frame(print_export_frame)
        export_frame.grid(row=1, column=0, sticky="nsew", pady=(2, 0))
        self.export_module = ExportModule(export_frame, self.preview_module, self.coordinator, self.config_manager)

        self.setup_module_connections()

    def setup_module_connections(self):
        """Устанавливает связи между всеми модулями"""        
        # Связи между модулями ролика и данными заказов
        self.order_data_module.set_roll_module(self.roll_module)
        self.roll_module.set_order_data_module(self.order_data_module)

        # Связь между модулем ролика и предпросмотра
        self.preview_module.set_roll_module(self.roll_module)
        self.roll_module.set_preview_module(self.preview_module)
        
        self.order_data_module.set_preview_module(self.preview_module)
        
        # Связи между новыми модулями и роликом
        self.print_module.set_roll_module(self.roll_module)
        self.export_module.set_roll_module(self.roll_module)

        # Связи для данных заказов
        self.print_module.set_order_data_module(self.order_data_module)
        self.export_module.set_order_data_module(self.order_data_module)
        
        # Связь между preview и print_module для обработки Enter
        self.preview_module.print_module = self.print_module

        # Связи для статусов (разделяем по назначению)
        self.preview_module.export_module = self.export_module  # только для экспорта
        self.order_data_module.export_module = self.export_module  # только для экспорта

        # Инициализируем SettingsManager и диалоги сразу
        from core.settings.settings_manager import SettingsManager
        self.settings_manager = SettingsManager(
            self.root,
            self,  # parent_manager
            config_manager=self.config_manager,
            coordinator=self.coordinator
        )
        # Передаем ссылку на roll_module в координатор
        self.coordinator.set_roll_module(self.roll_module)
        self.coordinator.set_settings_manager(self.settings_manager)
        
        # Отложенная инициализация preview_module
        if hasattr(self.preview_module, 'initialize_templates'):
            self.root.after(100, self.preview_module.initialize_templates)

    def center_window(self):
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"+{x}+{y}")

if __name__ == "__main__":
    # Проверяем демо-режим перед запуском
    if not check_demo_mode():
        sys.exit(1)
        
    from main_ui.order_data_processor import OrderDataProcessor
    from main_ui.weight_roll_printer import RollLabelPrinter
    from main_ui.preview.roll_preview import RollPreview
    from main_ui.print_module import PrintModule
    from main_ui.export_module import ExportModule

    root = tk.Tk()
    app = WeightOrdersApp(root)
    root.mainloop()