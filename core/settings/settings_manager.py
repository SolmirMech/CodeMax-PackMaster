# core/settings/settings_manager.py
import tkinter as tk
from tkinter import ttk
from .settings_dialog import SettingsDialog
from .font_settings_dialog import FontSettingsDialog


class SettingsManager:
    def __init__(self, parent, preview_export_module):
        self.parent = parent
        self.preview_export_module = preview_export_module
        self.window = None
        self.status_callback = None
        self.general_dialog = None
        self.font_dialog = None
        
    def set_status_callback(self, callback):
        """Устанавливает колбэк для обновления статуса"""
        self.status_callback = callback
        
    def update_status(self, message, color="green"):
        """Обновляет статус через колбэк"""
        if self.status_callback:
            self.status_callback(message, color)
            
    def show(self):
        if self.window and self.window.winfo_exists():
            self.window.lift()
            return
            
        self.window = tk.Toplevel(self.parent)
        self.window.title("Настройки")
        self.window.geometry("1100x770")
        self.window.grab_set()
        
        # Центрирование
        self.center_window()
        
        # Создаем вкладки
        notebook = ttk.Notebook(self.window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Вкладка 1: Общие настройки
        general_frame = ttk.Frame(notebook)
        notebook.add(general_frame, text="Общие настройки")
        
        # Вкладка 2: Настройки шрифтов  
        font_frame = ttk.Frame(notebook)
        notebook.add(font_frame, text="Настройки шрифтов")
        
        # Инициализируем диалоги
        self.general_dialog = SettingsDialog(general_frame, self.preview_export_module)
        self.general_dialog.set_parent_manager(self)
        self.general_dialog.create_ui()
        
        self.font_dialog = FontSettingsDialog(
            font_frame, 
            self.preview_export_module.config_manager,
            self.preview_export_module.preview_module,
            self.preview_export_module
        )
        self.font_dialog.set_parent_manager(self)
        self.font_dialog.create_ui()
        
        # Привязки клавиш на главное окно
        self.window.bind('<Return>', self.save_all_and_close)
        self.window.bind('<Escape>', self.close)
        self.window.focus_set()
        
    def save_all_and_close(self, event=None):
        """Сохраняет настройки из активной вкладки"""
        # Получаем активную вкладку из notebook
        notebook = None
        for child in self.window.winfo_children():
            if isinstance(child, ttk.Notebook):
                notebook = child
                break
        
        if notebook:
            current_tab = notebook.index(notebook.select())
            
            if current_tab == 0:  # Общие настройки
                success = self.general_dialog.save_settings()
                if success:
                    self.update_status("✅ Общие настройки сохранены!", "green")
                    self.close()
                else:
                    self.update_status(self.general_dialog.last_status, "red")
            else:  # Настройки шрифтов
                success = self.font_dialog.save_settings()
                if success:
                    self.update_status("✅ Настройки шрифтов сохранены!", "green")
                else:
                    self.update_status(self.font_dialog.last_status, "red")
            
    def close(self, event=None):
        """Закрывает окно настроек"""
        if self.window:
            self.window.destroy()
            self.window = None
            
    def center_window(self):
        """Центрирует окно"""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"+{x}+{y}")