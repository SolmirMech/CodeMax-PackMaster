# main.py
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
import configparser
from datetime import datetime
from core.settings.settings_coordinator import SettingsCoordinator
from main_ui.ecosystem_only_module import EcosystemOnlyModule

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

        self.export_container = None
        self.export_module_normal = None
        self.export_module_ecosystem = None
        self.current_export_module = None
        
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

        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=1)
        container.rowconfigure(0, weight=1)

        # Левая часть
        left_frame = ttk.Frame(container)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 2))
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(0, weight=0, minsize=550)
        left_frame.rowconfigure(1, weight=1)

        # Правая часть
        right_frame = ttk.Frame(container)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        right_frame.columnconfigure(0, weight=2)
        right_frame.columnconfigure(1, weight=1)
        right_frame.rowconfigure(0, weight=1)

        # Верх - OrderDataController
        roll_frame = ttk.Frame(left_frame)
        roll_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 2))
        self.roll_module = OrderDataController(roll_frame, self.coordinator, self.data_manager, self.config_manager)

        # Низ - OrderDetailsController
        order_data_frame = ttk.Frame(left_frame)
        order_data_frame.grid(row=1, column=0, sticky="nsew", pady=(2, 0))
        self.order_data_module = OrderDetailsController(
            order_data_frame,
            self.coordinator,
            self.data_manager,
            self.config_manager
        )

        # Правая часть - MainPreview
        preview_frame = ttk.Frame(right_frame)
        preview_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 2))
        self.preview_module = MainPreview(preview_frame, self.coordinator, self.config_manager)

        # Правая часть - контейнер для модуля печати и экспорта
        print_export_frame = ttk.Frame(right_frame)
        print_export_frame.grid(row=0, column=1, sticky="nsew", padx=(2, 0))

        print_export_frame.columnconfigure(0, weight=1)
        print_export_frame.rowconfigure(0, weight=1)
        print_export_frame.rowconfigure(1, weight=1)

        # Модуль Печати
        print_frame = ttk.Frame(print_export_frame)
        print_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 2))
        self.print_module = PrintModule(print_frame, self.preview_module, self.coordinator, self.config_manager)

        # Контейнер для модуля экспорта - используем pack внутри
        self.export_container = ttk.Frame(print_export_frame)
        self.export_container.grid(row=1, column=0, sticky="nsew", pady=(2, 0))

        # Создаём оба модуля
        self.export_module_normal = ExportModule(
            self.export_container,
            self.preview_module,
            self.coordinator,
            self.config_manager
        )
        self.export_module_ecosystem = EcosystemOnlyModule(
            self.export_container,
            self.preview_module,
            self.coordinator,
            self.config_manager
        )

        # Используем pack для управления видимостью
        self.export_module_normal.pack(fill=tk.BOTH, expand=True)
        self.export_module_ecosystem.pack(fill=tk.BOTH, expand=True)

        # По умолчанию показываем обычный модуль
        self.current_export_module = self.export_module_normal
        self.export_module_ecosystem.pack_forget()

        self.setup_module_connections()

        # Подписываемся на изменения производителя
        if self.coordinator and hasattr(self.coordinator, 'subscribe'):
            self.coordinator.subscribe(self.on_manufacturer_changed)
        self.root.after(100, lambda: self.on_manufacturer_changed({"type": "manufacturer_changed"}))

    # noinspection PyUnusedLocal
    def on_manufacturer_changed(self, context=None):
        """Обработчик изменения производителя — переключает модуль экспорта"""
        if context and context.get("type") != "manufacturer_changed":
            return

        if not hasattr(self, 'roll_module') or not self.roll_module:
            return

        manufacturer = ""
        if hasattr(self.roll_module, 'manufacturer_var'):
            manufacturer = self.roll_module.manufacturer_var.get().lower()

        is_ecosystem = "экосистема" in manufacturer

        # ОБНУЛЯЕМ СТАРЫЕ ССЫЛКИ
        if hasattr(self, 'preview_module') and self.preview_module:
            self.preview_module.export_module = None

        if hasattr(self, 'order_data_module') and self.order_data_module:
            self.order_data_module.export_module = None

        # Очищаем контейнер
        for widget in self.export_container.winfo_children():
            widget.destroy()

        # Создаём нужный модуль заново
        if is_ecosystem:
            from main_ui.ecosystem_only_module import EcosystemOnlyModule
            self.export_module = EcosystemOnlyModule(
                self.export_container,
                self.preview_module,
                self.coordinator,
                self.config_manager
            )
        else:
            from main_ui.export_module import ExportModule
            self.export_module = ExportModule(
                self.export_container,
                self.preview_module,
                self.coordinator,
                self.config_manager
            )

        self.export_module.pack(fill=tk.BOTH, expand=True)
        self.export_module.set_roll_module(self.roll_module)

        # ОБНОВЛЯЕМ ССЫЛКИ НА НОВЫЙ МОДУЛЬ
        if hasattr(self, 'preview_module') and self.preview_module:
            self.preview_module.export_module = self.export_module

        if hasattr(self, 'order_data_module') and self.order_data_module:
            self.order_data_module.export_module = self.export_module

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
        self.export_module_normal.set_roll_module(self.roll_module)
        self.export_module_ecosystem.set_roll_module(self.roll_module)

        # Связи для данных заказов
        self.print_module.set_order_data_module(self.order_data_module)
        self.export_module_normal.set_order_data_module(self.order_data_module)
        # Для экосистемного модуля (если есть метод)
        if hasattr(self.export_module_ecosystem, 'set_order_data_module'):
            self.export_module_ecosystem.set_order_data_module(self.order_data_module)

        # Связь между preview и print_module для обработки Enter
        self.preview_module.print_module = self.print_module

        # Связи для статусов (только для обычного модуля экспорта)
        self.preview_module.export_module = self.export_module_normal
        self.order_data_module.export_module = self.export_module_normal

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
        
    from main_ui.order_data_processor import OrderDetailsController
    from main_ui.order_data.controller import OrderDataController
    from main_ui.preview.main_preview import MainPreview
    from main_ui.print_module import PrintModule
    from main_ui.export_module import ExportModule

    root = tk.Tk()
    app = WeightOrdersApp(root)
    root.mainloop()