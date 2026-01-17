"""
Модуль управления комментариями и их отображением.
"""

import tkinter as tk
from tkinter import ttk
import re


class CommentManager:
    """Управление комментариями и их визуализацией."""
    
    def __init__(self, parent, comment_button, config_manager=None, customer_var=None):
        """
        Инициализация менеджера комментариев.
        
        Args:
            parent: Родительский виджет (для создания Toplevel окон)
            comment_button: Существующая кнопка комментариев
        """
        self.parent = parent  # Сохраняем родительский виджет
        self.config_manager = config_manager
        self.comment_button = comment_button
        self.customer_var = customer_var
        self.blinking_active = False
        self.blink_after_id = None
        
        # Переменные
        self.cutting_comment_var = tk.StringVar(value="")
        self.packaging_comment_var = tk.StringVar(value="")
        self.aggregation_status_var = tk.StringVar(value="")      
        
        # Назначаем обработчик нажатия на кнопку
        self.comment_button.config(command=self.show_comment)
        
    def _get_special_requirements(self):
        """Получает особые требования для текущего заказчика."""
        if not self.customer_var:
            return ""
        
        current_customer = self.customer_var.get().strip()
        if not current_customer:
            return ""
        
        try:
            if self.config_manager:
                settings = self.config_manager.load_json_settings("shared_utils.json")
                special_clients = settings.get("special_clients", {})
                
                # 1. Точное совпадение
                if current_customer in special_clients:
                    return special_clients[current_customer]
                
                # 2. Ищем по частичному совпадению (если имя из словаря содержится в имени заказчика)
                current_lower = current_customer.lower()
                
                for client_name, requirements in special_clients.items():
                    if not client_name:
                        continue
                        
                    client_name_lower = client_name.lower()
                    
                    # Если имя клиента из словаря содержится в текущем имени заказчика
                    if client_name_lower in current_lower:
                        return requirements
                    
                    # Или наоборот - если текущий заказчик содержится в имени из словаря
                    # (на случай, если в словаре полное имя, а в поле - сокращенное)
                    if current_lower in client_name_lower:
                        return requirements
                
                # 3. Ищем по очищенным названиям (убираем ООО, ОАО, ЗАО и т.д.)
                cleaned_current = self._clean_company_name(current_customer)
                cleaned_current_lower = cleaned_current.lower()
                
                for client_name, requirements in special_clients.items():
                    if not client_name:
                        continue
                        
                    cleaned_client = self._clean_company_name(client_name)
                    cleaned_client_lower = cleaned_client.lower()
                    
                    # Сравниваем очищенные названия
                    if (cleaned_client_lower in cleaned_current_lower or 
                        cleaned_current_lower in cleaned_client_lower):
                        return requirements
                
                return ""
            return ""
        except Exception as e:
            print(f"Ошибка загрузки особых требований: {e}")
            return ""

    def _clean_company_name(self, name):
        """Очищает название компании от организационно-правовых форм и лишних символов."""
        if not name:
            return name
        
        # Убираем ООО, ОАО, ЗАО, ИП и т.д.
        patterns_to_remove = [
            r'ООО\s*["«]?|["»]?\s*ООО',
            r'ОАО\s*["«]?|["»]?\s*ОАО', 
            r'ЗАО\s*["«]?|["»]?\s*ЗАО',
            r'ИП\s*["«]?|["»]?\s*ИП',
            r'АО\s*["«]?|["»]?\s*АО',
            r'ПАО\s*["«]?|["»]?\s*ПАО',
            r'НКО\s*["«]?|["»]?\s*НКО',
            r'ТОО\s*["«]?|["»]?\s*ТОО',
            r'\([^)]*\)',  # Убираем всё в скобках
            r'["«»]',      # Убираем кавычки
        ]
        
        cleaned = name
        for pattern in patterns_to_remove:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        # Убираем лишние пробелы
        cleaned = ' '.join(cleaned.split())
        
        return cleaned.strip()
        
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
        
        # Проверяем наличие особых требований
        special_requirements = self._get_special_requirements()
        
        # Проверяем, есть ли статус агрегации и он ли "Да"
        has_aggregation_yes = aggregation_status and aggregation_status.strip().lower() == "да"
        
        # Показываем/скрываем кнопку в зависимости от:
        # 1. Наличия комментариев
        # 2. Наличия особых требований
        # 3. ИЛИ если агрегация = "Да"
        if cutting_comment or packaging_comment or special_requirements or has_aggregation_yes:
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
        # Останавливаем предыдущее мигание
        self.stop_blinking()
        
        self.blinking_active = True
        
        def blink():
            if self.blinking_active and self.comment_button.winfo_exists():
                current = self.comment_button.cget("foreground")
                new = "#FFFF00" if current == "#FF9900" else "#FF9900"
                self.comment_button.config(foreground=new)
                # Сохраняем ID таймера
                self.blink_after_id = self.comment_button.after(1000, blink)
        
        blink()
        
    def stop_blinking(self):
        """Останавливает мигание кнопки комментариев."""
        self.blinking_active = False
        
        # Отменяем запланированную задачу мигания
        if self.blink_after_id:
            self.comment_button.after_cancel(self.blink_after_id)
            self.blink_after_id = None
        
        if self.comment_button.winfo_exists():
            self.comment_button.config(foreground="#FF9900")
            
    def show_comment(self):
        """Показывает окно с комментариями."""
        cutting_comment = self.cutting_comment_var.get()
        packaging_comment = self.packaging_comment_var.get()
        aggregation_status = self.aggregation_status_var.get()
        
        special_requirements = self._get_special_requirements()
        
        # Проверяем, есть ли что показывать
        has_comments = cutting_comment or packaging_comment or special_requirements
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
            
        # Добавляем особые требования
        if special_requirements:
            message += "🚨 Особые требования:\n"
            message += f"{special_requirements}\n"
        
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