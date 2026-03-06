# core/archive/archive_search_window.py
import tkinter as tk
from tkinter import ttk, StringVar, messagebox

from core.archive.archive_manager import ArchiveManager


# noinspection PyTypeChecker
class ArchiveSearchWindow:
    """Окно поиска и восстановления архивных поддонов"""
    
    def __init__(self, parent, order_processor, config_manager=None):
        self.status_var = None
        self.delete_btn = None
        self.restore_btn = None
        self.tree = None
        self.product_var = None
        self.pallet_var = None
        self.order_var = None
        self.window = None
        self.parent = parent
        self.order_processor = order_processor
        
        self.config_manager = config_manager
        self.archive_manager = ArchiveManager(config_manager)
        
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
        self.tree.heading("display", text="№ Заказа | № Поддона | Дата | Тип | Изделие")
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
            results = self._search_archives(order, pallet, product)
            
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

    # noinspection SpellCheckingInspection
    def _get_all_archives(self):
        """Получает все архивы для отображения"""
        archive = self.archive_manager.config.get_pallet_archive()
        archives = archive.get("pallets", [])

        result = []
        for archive_data in archives:
            basic_fields = archive_data.get("basic_fields", {})
            workshop = archive_data.get("workshop", "1")
            archive_type = archive_data.get("archive_type", "box")
            sheet_name = archive_data.get("sheet_name", "")
            extraction_date = archive_data.get("extraction_date", "")

            # Определяем тип для отображения
            type_display = self._get_archive_type_display(workshop, archive_type)

            # Ищем по стандартным ключам из маппингов
            order_num = basic_fields.get("order_number", "—")
            product = basic_fields.get("product_text", "—")
            date = basic_fields.get("date", "—")
            pallet_num = basic_fields.get("pallet_num", "—")

            # Если даты нет в basic_fields, берём из extraction_date
            if date == "—" and extraction_date:
                date = extraction_date[:10]

            product_preview = str(product)[:50] + "..." if len(str(product)) > 50 else str(product)

            # Формируем строку для отображения
            if pallet_num != "—":
                display = f"{order_num} | №{pallet_num} | {date} | {type_display} | {product_preview}"
            else:
                display = f"{order_num} | {date} | {type_display} | {product_preview}"

            result.append({
                "display": display,
                "archive_data": archive_data,
                "order_number": order_num,
                "pallet_number": pallet_num,
                "product_full": product,
                "archive_type": archive_type,
                "sheet_name": sheet_name,
                "workshop": workshop,
                "type_display": type_display
            })

        return result

    # noinspection SpellCheckingInspection
    @staticmethod
    def _get_archive_type_display(workshop, archive_type):
        """Возвращает понятное название типа архива"""
        if workshop == "1":
            if archive_type == "box":
                return "Коробка (цех 1)"
            elif archive_type == "pallet":
                return "Поддон (цех 1)"
            elif archive_type == "noweight":
                return "Без веса (цех 1)"
            elif archive_type == "multitype":
                return "Много видов (цех 1)"
            elif archive_type == "multitype_noweight":
                return "Много видов без веса (цех 1)"
            elif archive_type == "box_noweight":
                return "Коробка без веса (ПоддонРолики)"
        else:  # workshop == "2"
            if archive_type == "box":
                return "Поддон (цех 2)"
            elif archive_type == "pallet_list":
                return "Список поддонов (цех 2)"
            elif archive_type == "multitype":
                return "Много видов (цех 2)"

        return f"{archive_type} (цех {workshop})"

    def _search_archives(self, order="", pallet="", product=""):
        """Поиск архивов"""
        all_archives = self._get_all_archives()
        
        if not any([order, pallet, product]):
            return all_archives
        
        filtered = []
        for archive in all_archives:
            match_order = not order or order.lower() in str(archive["order_number"]).lower()
            match_pallet = not pallet or (archive["pallet_number"] != "—" and 
                                         pallet.lower() in str(archive["pallet_number"]).lower())
            match_product = not product or product.lower() in str(archive["product_full"]).lower()
            
            if match_order and match_pallet and match_product:
                filtered.append(archive)
        
        return filtered
    
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

    # noinspection PyUnusedLocal
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
        results = self._search_archives(order, pallet, product)
        
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
            # Получаем данные архива
            archive_data = self.selected_pallet["archive_data"]

            # Получаем цех из архива
            workshop = archive_data.get("workshop", "2")

            # Получаем статус веса из архива (если есть)
            has_weight = archive_data.get("has_weight", True)

            # Получаем путь через координатор (он сам проверит существование)
            if self.order_processor and hasattr(self.order_processor, 'coordinator'):
                excel_path = self.order_processor.coordinator.get_excel_file_path(workshop, has_weight)
            else:
                excel_path = self.archive_manager.get_excel_path(workshop, has_weight)

            self.status_var.set("Восстанавливаю поддон...")
            self.window.update()

            # Восстанавливаем
            result = self.archive_manager.restore_to_excel(
                archive_data,
                excel_path
            )

            if result["success"]:
                order_num = result.get("order", "неизвестно")
                pallet_num = result.get("pallet_number", "")

                self.status_var.set(f"✅ Поддон восстановлен (заказ: {order_num})")

                # Обновляем статус в основном окне
                if hasattr(self.order_processor, 'multitype_status_label'):
                    status_text = f"Восстановлен поддон {pallet_num} (заказ: {order_num})" if pallet_num else f"Восстановлен поддон (заказ: {order_num})"
                    self.order_processor.multitype_status_label.config(
                        text=status_text,
                        foreground="green"
                    )

                # Закрываем окно через 2 секунды
                self.window.after(2000, self.window.destroy)
            else:
                error_msg = result.get("error", "Неизвестная ошибка")
                self.status_var.set(f"❌ Ошибка восстановления: {error_msg}")

        except FileNotFoundError as e:
            self.status_var.set(f"❌ Файл не найден: {str(e)}")
        except Exception as e:
            self.status_var.set(f"❌ Ошибка: {str(e)}")

    def _delete_archive(self, archive_data):
        """Удаляет архив из JSON файла"""
        try:
            config = self.archive_manager.config
            archive = config.get_pallet_archive()
            pallets = archive.get("pallets", [])
            
            # Получаем полные данные выбранного архива
            selected_basic = archive_data.get("basic_fields", {})
            selected_workshop = archive_data.get("workshop", "1")
            selected_archive_type = archive_data.get("archive_type", "box")
            selected_sheet_name = archive_data.get("sheet_name", "")
            selected_extraction_date = archive_data.get("extraction_date", "")
            
            new_pallets = []
            deleted = False
            
            for pallet in pallets:
                basic = pallet.get("basic_fields", {})
                workshop = pallet.get("workshop", "1")
                archive_type = pallet.get("archive_type", "box")
                sheet_name = pallet.get("sheet_name", "")
                extraction_date = pallet.get("extraction_date", "")
                
                # Сравниваем ВСЕ ключевые поля для точного совпадения
                # 1. Сравниваем базовые поля (словари)
                basic_match = basic == selected_basic
                
                # 2. Сравниваем остальные атрибуты
                workshop_match = workshop == selected_workshop
                type_match = archive_type == selected_archive_type
                sheet_match = sheet_name == selected_sheet_name
                
                # Для большей точности можно сравнивать дату извлечения
                date_match = extraction_date == selected_extraction_date
                
                # Если все ключевые поля совпадают - это тот самый архив
                if (basic_match and workshop_match and type_match and 
                    sheet_match and date_match):
                    deleted = True
                    continue  # пропускаем (удаляем)
                
                new_pallets.append(pallet)
            
            if deleted:
                archive["pallets"] = new_pallets
                config.save_pallet_archive(archive)
                return True
            else:
                return False
                
        except Exception as e:
            print(f"Ошибка удаления архива: {e}")
            return False
    
    def delete_selected(self):
        """Удаляет выбранный архив"""
        if not self.selected_pallet:
            self.status_var.set("❌ Не выбран архив для удаления")
            return
        
        archive_data = self.selected_pallet["archive_data"]
        order_num = self.selected_pallet.get("order_number", "—")
        pallet_num = self.selected_pallet.get("pallet_number", "—")
        archive_type = self.selected_pallet.get("archive_type", "—")
        sheet_name = self.selected_pallet.get("sheet_name", "—")
        
        # Подтверждение (можно улучшить информацию)
        if pallet_num != "—":
            msg = f"Удалить архив: заказ {order_num}, поддон {pallet_num}?\nТип: {archive_type}, Лист: {sheet_name}"
        else:
            msg = f"Удалить архив: заказ {order_num}?\nТип: {archive_type}, Лист: {sheet_name}"
        
        confirm = tk.messagebox.askyesno("Подтверждение удаления", msg)
        
        if not confirm:
            return
        
        try:
            success = self._delete_archive(archive_data)
            
            if success:
                self.status_var.set(f"✅ Архив удалён")
                self.search()  # Обновляем список
                self.selected_pallet = None
                self.restore_btn.config(state="disabled")
                self.delete_btn.config(state="disabled")
            else:
                self.status_var.set(f"❌ Не удалось удалить архив")
                
        except Exception as e:
            self.status_var.set(f"❌ Ошибка удаления: {str(e)}")