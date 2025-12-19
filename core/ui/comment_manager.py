"""
Модуль управления комментариями и их отображением.
"""

import tkinter as tk
from tkinter import ttk


class CommentManager:
    """Управление комментариями и их визуализацией."""
    
    def __init__(self, parent, comment_button):
        """
        Инициализация менеджера комментариев.
        
        Args:
            parent: Родительский виджет (для создания Toplevel окон)
            comment_button: Существующая кнопка комментариев
        """
        self.parent = parent  # Сохраняем родительский виджет
        self.comment_button = comment_button
        self.blinking_active = False
        
        # Переменные
        self.cutting_comment_var = tk.StringVar(value="")
        self.packaging_comment_var = tk.StringVar(value="")
        self.aggregation_status_var = tk.StringVar(value="")
        
        # Назначаем обработчик нажатия на кнопку
        self.comment_button.config(command=self.show_comment)
        
    def set_comments(self, cutting_comment="", packaging_comment="", aggregation_status=""):
        """
        Устанавливает комментарии и статус агрегации.
        
        Args:
            cutting_comment: Комментарий резки
            packaging_comment: Комментарий упаковки
            aggregation_status: Статус агрегации ('Да', 'Нет' или '')
        """
        self.cutting_comment_var.set(cutting_comment)
        self.packaging_comment_var.set(packaging_comment)
        self.aggregation_status_var.set(aggregation_status)
        
        # Проверяем, есть ли статус агрегации и он ли "Да"
        has_aggregation_yes = aggregation_status and aggregation_status.strip().lower() == "да"
        
        # Показываем/скрываем кнопку в зависимости от:
        # 1. Наличия комментариев
        # 2. ИЛИ если агрегация = "Да"
        if cutting_comment or packaging_comment or has_aggregation_yes:
            self.comment_button.grid()
            self.comment_button.config(state="normal")
            self.start_blinking()
        else:
            self.comment_button.grid_remove()
            self.comment_button.config(state="disabled")
            self.stop_blinking()
        
    def get_comments(self):
        """
        Возвращает текущие комментарии.
        
        Returns:
            dict: Словарь с комментариями
        """
        return {
            'cutting': self.cutting_comment_var.get(),
            'packaging': self.packaging_comment_var.get()
        }      
            
    def start_blinking(self):
        """Запускает мигание кнопки комментариев."""
        self.blinking_active = True
        
        def blink():
            if self.blinking_active and self.comment_button.winfo_exists():
                current = self.comment_button.cget("foreground")
                new = "#FFFF00" if current == "#FF9900" else "#FF9900"
                self.comment_button.config(foreground=new)
                self.comment_button.after(1000, blink)
                
        blink()
        
    def stop_blinking(self):
        """Останавливает мигание кнопки комментариев."""
        self.blinking_active = False
        if self.comment_button.winfo_exists():
            self.comment_button.config(foreground="#FF9900")
            
    def show_comment(self):
        """Показывает окно с комментариями."""
        cutting_comment = self.cutting_comment_var.get()
        packaging_comment = self.packaging_comment_var.get()
        aggregation_status = self.aggregation_status_var.get()
        
        # Проверяем, есть ли что показывать
        has_comments = cutting_comment or packaging_comment
        has_aggregation_yes = aggregation_status and aggregation_status.strip().lower() == "да"
        
        if not has_comments and not has_aggregation_yes:
            return
        
        # Создаем кастомное окно
        comment_window = tk.Toplevel(self.parent)
        comment_window.title("📝 Комментарии к операциям")
        comment_window.geometry("500x450")
        comment_window.resizable(True, True)
        
        # Центрируем окно относительно главного окна
        self.center_window(comment_window)
        
        # Привязка клавиш
        comment_window.bind('<Return>', lambda e: self.close_comment_window(comment_window))
        comment_window.bind('<Escape>', lambda e: self.close_comment_window(comment_window))
        
        # Фокус на окно
        comment_window.focus_set()
        
        # Жёлтый треугольник слева
        triangle_label = ttk.Label(
            comment_window,
            text="⚠",
            font=("Arial", 24, "bold"),
            foreground="#FF9900"
        )
        triangle_label.pack(side=tk.LEFT, padx=(15, 0), pady=15)
        
        # Основной контент справа
        content_frame = ttk.Frame(comment_window)
        content_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Текстовое поле с полосой прокрутки
        text_frame = ttk.Frame(content_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        text_widget = tk.Text(
            text_frame,
            wrap=tk.WORD,
            font=("Arial", 10),
            height=15,
            width=50,
            background="#FFFFE0"
        )
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Полоса прокрутки
        scrollbar = ttk.Scrollbar(text_frame, command=text_widget.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.config(yscrollcommand=scrollbar.set)
        
        # Формируем текст
        message = ""
        
        if cutting_comment:
            message += "📐 КОММЕНТАРИЙ РЕЗКИ:\n"
            message += f"{cutting_comment}\n\n"
        
        if packaging_comment:
            message += "📦 КОММЕНТАРИЙ УПАКОВКИ:\n"
            message += f"{packaging_comment}\n"
        
        text_widget.insert("1.0", message.strip())
        text_widget.config(state="disabled")
        
        # Добавляем строку статуса агрегации
        if has_aggregation_yes:
            status_frame = ttk.Frame(content_frame)
            status_frame.pack(fill=tk.X, pady=(10, 0))
            
            # Иконка информации
            info_icon = ttk.Label(
                status_frame,
                text="ℹ",
                font=("Arial", 14, "bold"),
                foreground="#0066CC"
            )
            info_icon.pack(side=tk.LEFT, padx=(0, 5))
            
            # Текст статуса агрегации
            status_label = ttk.Label(
                status_frame,
                text="ЕСТЬ АГРЕГАЦИЯ",
                font=("Arial", 11, "bold"),
                foreground="#006600"  # Зеленый цвет для важной информации
            )
            status_label.pack(side=tk.LEFT)        
        
        # Сохраняем ссылку на окно для остановки мигания при закрытии
        comment_window.protocol("WM_DELETE_WINDOW", lambda: self.close_comment_window(comment_window))
        
    def close_comment_window(self, window):
        """
        Закрывает окно комментариев.
        
        Args:
            window: Окно для закрытия
        """
        self.stop_blinking()
        if self.comment_button.winfo_exists():
            self.comment_button.config(foreground="#FF9900")
        window.destroy()
        
    def center_window(self, window):
        """Центрирует окно относительно главного окна приложения."""
        window.update_idletasks()
        
        # Получаем корневое окно
        root_window = self.parent.winfo_toplevel()
        
        # Размеры окна комментариев
        width = window.winfo_width()
        height = window.winfo_height()
        
        # Позиция и размер главного окна
        root_x = root_window.winfo_rootx()
        root_y = root_window.winfo_rooty()
        root_width = root_window.winfo_width()
        root_height = root_window.winfo_height()
        
        # Координаты для центрирования относительно главного окна
        x = root_x + (root_width - width) // 2
        y = root_y + (root_height - height) // 2
        
        window.geometry(f"+{x}+{y}")