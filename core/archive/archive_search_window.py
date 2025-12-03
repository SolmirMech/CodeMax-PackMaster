# core/archive/archive_search_window.py
import tkinter as tk
from tkinter import ttk, StringVar
import os

class ArchiveSearchWindow:
    """Окно поиска и восстановления архивных поддонов"""
    
    def __init__(self, parent, order_processor):
        self.parent = parent
        self.order_processor = order_processor
        
        # Создаём менеджер архива
        from core.archive.archive_manager import ArchiveManager
        from core.config_manager import ConfigManager
        self.archive_manager = ArchiveManager(ConfigManager())
        
        self.selected_pallet = None
        self.create_window()
    
    def create_window(self):
        """Создаёт окно поиска"""
        self.window = tk.Toplevel(self.parent)
        self.window.title("🔍 Поиск и восстановление архивных поддонов")
        self.window.geometry("1100x700")
        self.window.minsize(800, 500)
        
        # Делаем модальным
        self.window.transient(self.parent)
        self.window.grab_set()
        
        # Центрирование окна
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"+{x}+{y}")
        self.window.bind("<Escape>", lambda e: self.window.destroy())        
        
        # Заголовок
        header_frame = ttk.Frame(self.window)
        header_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(
            header_frame, 
            text="Поиск архивных поддонов",
            font=("Arial", 14, "bold")
        ).pack(side=tk.LEFT)
        
        # Панель поиска
        search_frame = ttk.LabelFrame(self.window, text="Критерии поиска", padding=15)
        search_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # Строка 1: Поля поиска
        row1 = ttk.Frame(search_frame)
        row1.pack(fill=tk.X, pady=(0, 10))
        
        # Номер заказа
        ttk.Label(row1, text="Номер заказа:").grid(row=0, column=0, sticky="w", padx=(0, 5))
        self.order_var = StringVar()
        order_entry = ttk.Entry(row1, textvariable=self.order_var, width=20)
        order_entry.grid(row=0, column=1, padx=(0, 20))
        order_entry.bind("<Return>", lambda e: self.search())
        
        # Номер поддона
        ttk.Label(row1, text="Номер поддона:").grid(row=0, column=2, sticky="w", padx=(0, 5))
        self.pallet_var = StringVar()
        pallet_entry = ttk.Entry(row1, textvariable=self.pallet_var, width=15)
        pallet_entry.grid(row=0, column=3, padx=(0, 20))
        pallet_entry.bind("<Return>", lambda e: self.search())
        
        # Название (можно часть)
        ttk.Label(row1, text="Название:").grid(row=0, column=4, sticky="w", padx=(0, 5))
        self.product_var = StringVar()
        product_entry = ttk.Entry(row1, textvariable=self.product_var, width=25)
        product_entry.grid(row=0, column=5, padx=(0, 20))
        product_entry.bind("<Return>", lambda e: self.search())
        
        # Строка 2: Кнопки
        row2 = ttk.Frame(search_frame)
        row2.pack(fill=tk.X)
        
        ttk.Button(
            row2,
            text="🔍 Искать",
            command=self.search,
            width=15
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(
            row2,
            text="🗑️ Очистить",
            command=self.clear_search,
            width=15
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(
            row2,
            text="📋 Показать все",
            command=self.show_all,
            width=15
        ).pack(side=tk.LEFT)
        
        # Таблица результатов
        results_frame = ttk.LabelFrame(self.window, text="Найденные поддоны", padding=10)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # Колонки
        columns = ("display",)
        
        # Treeview с скроллбаром
        tree_frame = ttk.Frame(results_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        self.tree = ttk.Treeview(
            tree_frame, 
            columns=columns, 
            show="headings",
            height=15,
            selectmode="browse"
        )
        
        # Настраиваем колонку
        self.tree.heading("display", text="Поддон | Заказ | Дата | Упаковщик | Изделие")
        self.tree.column("display", width=800, stretch=True)
        
        # Скроллбар
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Привязка событий
        self.tree.bind("<<TreeviewSelect>>", self.on_pallet_selected)
        self.tree.bind("<Double-Button-1>", lambda e: self.restore_selected())
        
        # Панель управления
        control_frame = ttk.Frame(self.window)
        control_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # Кнопка восстановления
        self.restore_btn = ttk.Button(
            control_frame,
            text="📂 Восстановить выбранный поддон",
            command=self.restore_selected,
            state="disabled",
            width=30
        )
        self.restore_btn.pack(side=tk.LEFT, padx=(0, 20))
        
        # Кнопка удаления
        self.delete_btn = ttk.Button(
            control_frame,
            text="🗑️ Удалить из архива",
            command=self.delete_selected,
            state="disabled",
            width=20
        )
        self.delete_btn.pack(side=tk.LEFT, padx=(0, 20))
        
        # Статусная строка
        self.status_var = StringVar(value="Готов к поиску")
        status_label = ttk.Label(
            control_frame,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            padding=5
        )
        status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Загружаем все поддоны при открытии
        self.show_all()
    
    def search(self):
        """Выполняет поиск по критериям"""
        try:
            self.status_var.set("Идёт поиск...")
            self.window.update()
            
            # Получаем критерии
            order = self.order_var.get().strip()
            pallet = self.pallet_var.get().strip()
            product = self.product_var.get().strip()
            
            # Выполняем поиск
            results = self.archive_manager.search_pallets(order, pallet, product)
            
            # Очищаем таблицу
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # Заполняем таблицу
            for i, pallet_info in enumerate(results, 1):
                self.tree.insert(
                    "", 
                    "end", 
                    values=(pallet_info["display"],),
                    tags=(i,)
                )
            
            # Статус
            count = len(results)
            if count == 0:
                self.status_var.set("Ничего не найдено")
            else:
                self.status_var.set(f"Найдено поддонов: {count}")
            
            # Сбрасываем выбор
            self.selected_pallet = None
            self.restore_btn.config(state="disabled")
            self.delete_btn.config(state="disabled")
            
        except Exception as e:
            self.status_var.set(f"Ошибка поиска: {str(e)}")
    
    def show_all(self):
        """Показывает все поддоны"""
        self.order_var.set("")
        self.pallet_var.set("")
        self.product_var.set("")
        self.search()
    
    def clear_search(self):
        """Очищает поля поиска"""
        self.order_var.set("")
        self.pallet_var.set("")
        self.product_var.set("")
        self.status_var.set("Поля очищены")
    
    def on_pallet_selected(self, event):
        """Обрабатывает выбор поддона в таблице"""
        selection = self.tree.selection()
        if not selection:
            return
        
        # Получаем индекс выбранного элемента
        selected_item = selection[0]
        item_index = int(self.tree.item(selected_item, "tags")[0]) - 1
        
        # Получаем все результаты
        order = self.order_var.get().strip()
        pallet = self.pallet_var.get().strip()
        product = self.product_var.get().strip()
        results = self.archive_manager.search_pallets(order, pallet, product)
        
        if 0 <= item_index < len(results):
            self.selected_pallet = results[item_index]
            
            # Активируем кнопки
            self.restore_btn.config(state="normal")
            self.delete_btn.config(state="normal")
            
            # Показываем информацию в статусе
            pallet_num = self.selected_pallet.get("pallet_number", "—")
            order_num = self.selected_pallet.get("order", "—")
            self.status_var.set(f"Выбран поддон №{pallet_num} (заказ: {order_num})")
    
    def restore_selected(self):
        """Восстанавливает выбранный поддон"""
        if not self.selected_pallet:
            self.status_var.set("❌ Не выбран поддон для восстановления")
            return
        
        try:
            # Получаем путь к Excel из order_processor
            excel_path = self.order_processor.excel_file_path
            if not excel_path or not os.path.exists(excel_path):
                # Пробуем загрузить путь
                self.order_processor.load_excel_folder_path()
                excel_path = self.order_processor.excel_file_path
            
            if not excel_path or not os.path.exists(excel_path):
                self.status_var.set("❌ Файл Excel не найден. Проверьте настройки.")
                return
            
            self.status_var.set("Восстанавливаю поддон...")
            self.window.update()
            
            # Восстанавливаем
            result = self.archive_manager.restore_pallet_to_excel(
                self.selected_pallet["pallet_data"]
            )
            
            if result["success"]:
                pallet_num = result.get("pallet_number", "неизвестно")
                order_num = result.get("order", "неизвестно")
                
                self.status_var.set(f"✅ Поддон №{pallet_num} восстановлен (заказ: {order_num})")
                
                # Обновляем статус в основном окне
                if hasattr(self.order_processor, 'multitype_status_label'):
                    self.order_processor.multitype_status_label.config(
                        text=f"Восстановлен поддон №{pallet_num} (заказ: {order_num})",
                        foreground="green"
                    )
                
                # Закрываем окно через 2 секунды
                self.window.after(2000, self.window.destroy)
                
            else:
                error_msg = result.get("error", "Неизвестная ошибка")
                self.status_var.set(f"❌ Ошибка восстановления: {error_msg}")
                
        except Exception as e:
            self.status_var.set(f"❌ Ошибка: {str(e)}")
    
    def delete_selected(self):
        """Удаляет выбранный поддон из архива"""
        if not self.selected_pallet:
            self.status_var.set("❌ Не выбран поддон для удаления")
            return
        
        # Подтверждение
        pallet_num = self.selected_pallet.get("pallet_number", "—")
        order_num = self.selected_pallet.get("order", "—")
        
        confirm = tk.messagebox.askyesno(
            "Подтверждение удаления",
            f"Удалить поддон №{pallet_num} (заказ: {order_num}) из архива?\n\n"
            "Это действие нельзя отменить."
        )
        
        if not confirm:
            return
        
        try:
            success = self.archive_manager.delete_pallet_from_archive(
                self.selected_pallet["pallet_data"]
            )
            
            if success:
                self.status_var.set(f"✅ Поддон №{pallet_num} удалён из архива")
                
                # Обновляем список
                self.search()
                
                # Сбрасываем выбор
                self.selected_pallet = None
                self.restore_btn.config(state="disabled")
                self.delete_btn.config(state="disabled")
                
            else:
                self.status_var.set(f"❌ Не удалось удалить поддон №{pallet_num}")
                
        except Exception as e:
            self.status_var.set(f"❌ Ошибка удаления: {str(e)}")