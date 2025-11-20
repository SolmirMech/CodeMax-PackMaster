# main.py
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
import configparser
from datetime import datetime

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

class WeightOrdersApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Упаковка")
        self.root.geometry("1450x860")
        
        # Установка стилей как в оригинале
        self.setup_styles()
        
        # Инициализация ConfigManager
        from core.config_manager import ConfigManager
        self.config_manager = ConfigManager()
        
        self.create_ui()
        self.center_window()

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
        """Создает интерфейс только с вкладкой Ролик/коробка"""
        # Создаем вкладки
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Создаем фрейм для вкладки ролика
        roll_preview_frame = ttk.Frame(notebook, padding=5)

        # Создаем объединенный интерфейс для ролика и предпросмотра
        self.create_roll_preview_interface(roll_preview_frame)

        # Добавляем только одну вкладку
        notebook.add(roll_preview_frame, text="Ролик/коробка")

    def create_roll_preview_interface(self, parent):
        """Создает объединенный интерфейс для ролика и предпросмотра"""
        container = ttk.Frame(parent)
        container.pack(fill=tk.BOTH, expand=True)
        
        # Настраиваем пропорции колонок
        container.columnconfigure(0, weight=1)  # Левая часть - 1/3
        container.columnconfigure(1, weight=2)  # Правая часть - 2/3
        container.rowconfigure(0, weight=1)     # Одна строка

        # Левая часть
        left_frame = ttk.Frame(container)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(0, weight=1)    # RollLabelPrinter
        left_frame.rowconfigure(1, weight=1)    # OrderDataProcessor

        # Правая часть
        right_frame = ttk.Frame(container)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        right_frame.columnconfigure(0, weight=4)  # Превью
        right_frame.columnconfigure(1, weight=1)  # Экспорт
        right_frame.rowconfigure(0, weight=1)     # Одна строка

        # Верх - RollLabelPrinter
        roll_frame = ttk.Frame(left_frame)
        roll_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 5))
        self.roll_module = RollLabelPrinter(roll_frame)

        # Низ - OrderDataProcessor
        order_data_frame = ttk.Frame(left_frame)
        order_data_frame.grid(row=1, column=0, sticky="nsew", pady=(5, 0))
        self.order_data_module = OrderDataProcessor(order_data_frame)

        # Правая часть - RollPreview (слева)
        preview_frame = ttk.Frame(right_frame)
        preview_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        self.preview_module = RollPreview(preview_frame)
        
        # Правая часть - PreviewExport (справа)
        export_frame = ttk.Frame(right_frame)
        export_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        self.export_module = PreviewExport(export_frame, self.preview_module)

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
        
        # Связь между модулем экспорта и ролика
        self.export_module.set_roll_module(self.roll_module)
        
        # Связь между preview и export для статуса Excel
        self.preview_module.export_module = self.export_module
        self.order_data_module.export_module = self.export_module

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
        
    from apps.order_data_processor import OrderDataProcessor
    from apps.weight_roll_printer import RollLabelPrinter
    from apps.roll_preview import RollPreview
    from apps.preview_export import PreviewExport

    root = tk.Tk()
    app = WeightOrdersApp(root)
    root.mainloop()