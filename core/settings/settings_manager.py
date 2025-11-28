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
        self.status_callback = None  # Колбэк для статуса
        
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
        self.window.bind("<Escape>", lambda e: self.window.destroy())
        
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
        self.general_dialog = SettingsDialog(self.window, self.preview_export_module)
        self.general_dialog.set_status_callback(self.update_status)
        self.general_dialog.show_in_frame(general_frame)
        
        self.font_dialog = FontSettingsDialog(
            self.window, 
            self.preview_export_module.config_manager,
            self.preview_export_module.preview_module,  # ← preview_printer (RollPreview)
            self.preview_export_module                   # ← preview_export_module (PreviewExport)
        )
        self.font_dialog.show_in_frame(font_frame)
        
    def center_window(self):
        """Центрирует окно"""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"+{x}+{y}")