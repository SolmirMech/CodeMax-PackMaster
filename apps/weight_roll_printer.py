import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, StringVar, BooleanVar
from datetime import datetime
from core.excel_exporter import WeightOrdersExporter
from core.config_manager import ConfigManager
from apps.weight_orders_printer import WeightOrdersPrinter

class RollLabelPrinter:
    """Управление заказами с весом"""
    def __init__(self, parent):
        self.parent = parent
        self.config_manager = ConfigManager()

        self.packers_window = None
        self.order_data_module = None
        self.preview_module = None
        self.weight_orders_window = None
        
        # Переменные интерфейса и данных
        self.show_manufacturer_var = BooleanVar(value=False)  # Показывать производителя
        self.show_manufacturer_var.trace_add("write", self._on_producer_visibility_changed)
        self.customer_var = StringVar(value="")  # Наименование заказчика
        self.gross_weight_kg_var = StringVar(value="")  # Вес ролика брутто в кг
        self.net_weight_kg_var = StringVar(value="")  # Вес ролика нетто в кг (авторасчет)
        self.order_prefix = StringVar(value="Ф")  # Префикс номера заказа (например, "Ф")
        self.order_number = StringVar(value="")  # Основной номер заказа
        self.order_suffix = StringVar(value="/5")  # Суффикс номера заказа (например, "/5")
        self.date_var = StringVar(value=datetime.now().strftime("%d.%m.%Y"))  # Дата изготовления
        self.packer_var = StringVar(value="")  # ФИО упаковщика
        self.quantity_var = StringVar(value="")  # Количество этикеток в одном ролике
        self.sleeve_weight_var = StringVar(value="50")  # Вес втулки в граммах
        self.winding_scheme_var = StringVar(value="7")  # Схема намотки
        self.sleeve_diameter_var = StringVar(value="76")  # Диаметр втулки в мм
        self.rolls_count_var = StringVar(value="")  # Количество роликов в коробке
        self.total_quantity_var = StringVar(value="")  # Общее количество этикеток (авторасчет)
        self.total_gross_var = StringVar(value="")  # Общий вес коробки брутто в кг (авторасчет)
        self.total_net_var = StringVar(value="")  # Общий вес коробки нетто в кг (авторасчет)
        self.box_weight_var = StringVar(value="0.0")  # Вес пустой коробки в кг
        self.box_size_var = StringVar(value="")  # Размер коробки (выбирается из списка)
        self.box_editor_window = None  # Ссылка на окно редактора коробок
        self.detail_num_search_var = StringVar(value="")  # Поиск по цифрам кода
        self.date_emission_var = StringVar(value="") # Дата эмиссии кодов
        
        self.create_ui()
        self.load_box_sizes()       
        # Отслеживаем изменения всех переменных, влияющих на расчет веса
        variables_to_track = [
            self.rolls_count_var,
            self.box_weight_var, 
            self.gross_weight_kg_var,
            self.net_weight_kg_var,
            self.net_weight_kg_var
        ]
        
        for var in variables_to_track:
            var.trace_add("write", self.calculate_box_weights)
        self.quantity_var.trace_add("write", self.calculate_total_quantity)
        
    def calculate_box_weights(self, *args):
        """Автоматически рассчитывает вес коробки брутто и нетто"""
        try:
            rolls_count = int(self.rolls_count_var.get() or 0)
            box_weight_kg = self.parse_float(self.box_weight_var.get() or 0)
            
            if rolls_count == 0:
                self.total_gross_var.set("")
                self.total_net_var.set("")
                return
            
            # Бери значения прямо из полей ввода:
            roll_gross_kg = self.parse_float(self.gross_weight_kg_var.get() or 0)
            roll_net_kg = self.parse_float(self.net_weight_kg_var.get() or 0)
            
            if roll_gross_kg == 0:
                self.total_gross_var.set("")
                self.total_net_var.set("")
                return
            
            # Рассчитываем общий вес роликов
            total_rolls_gross = rolls_count * roll_gross_kg
            total_rolls_net = rolls_count * roll_net_kg
            
            # Добавляем вес коробки к брутто (НЕ к нетто!)
            total_gross = total_rolls_gross + box_weight_kg
            total_net = total_rolls_net  # Вес коробки НЕ добавляется к нетто
            
            # Обновляем поля
            self.total_gross_var.set(f"{total_gross:.2f}")
            self.total_net_var.set(f"{total_net:.2f}")
            
        except (ValueError, TypeError) as e:
            print(f"Ошибка расчета весов: {e}")
            
    def _on_producer_visibility_changed(self, *args):
        """Обрабатывает изменение видимости производителя"""
        show_manufacturer = self.show_manufacturer_var.get()

    def create_ui(self):
        """Создает интерфейс для печати этикеток на ролик"""
        frame = ttk.Frame(self.parent, padding=5)
        frame.pack(fill=tk.BOTH, expand=True)

        # Основной контейнер для данных
        data_frame = ttk.LabelFrame(
            frame, text="Данные для этикетки", padding=5
        )
        data_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        # Заказчик
        ttk.Label(data_frame, text="Заказчик:").grid(
            row=1, column=0, sticky="w", pady=5
        )
        customer_entry = ttk.Entry(data_frame, textvariable=self.customer_var, font=("Arial", 12), width=35)
        customer_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        self.add_context_menu(customer_entry)
        customer_entry.bind("<Control-KeyPress>", self.control_key_handler)
        self.customer_var.trace_add("write", self.on_customer_changed)

        # Изделие (многострочное поле)
        ttk.Label(data_frame, text="Изделие:").grid(
            row=2, column=0, sticky="nw", pady=5
        )
        
        # Многострочное текстовое поле
        self.product_text = tk.Text(data_frame, width=35, height=4, font=("Arial", 12))
        self.product_text.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        
        # Контекстное меню для текстового поля
        self.add_context_menu_to_text(self.product_text)
        
        ttk.Label(data_frame, text="Кол-во этикеток/роликов:", foreground="green").grid(
            row=4, column=0, sticky="w", pady=5
        )
        # Кол-во этикеток в одном ролике
        quantity_entry = ttk.Entry(data_frame, textvariable=self.quantity_var, width=15)
        quantity_entry.grid(row=4, column=1, padx=5, pady=5, sticky="w")
        # Кол-во роликов
        rolls_entry = ttk.Entry(data_frame, textvariable=self.rolls_count_var, width=15)
        rolls_entry.grid(row=4, column=1, padx=(115, 0), pady=5, sticky="w")
        rolls_entry.bind("<KeyRelease>", self.calculate_total_quantity)
        # Общее кол-во этикеток - СКРЫТО
        total_entry = ttk.Entry(data_frame, textvariable=self.total_quantity_var, width=15, state="readonly")
        total_entry.grid(row=4, column=1, padx=(225, 0), pady=5, sticky="w")
        total_entry.grid_remove()

        # Вес рулона
        ttk.Label(data_frame, text="Вес ролика брутто, кг:").grid(
            row=5, column=0, sticky="w", pady=5
        )
        gross_entry = ttk.Entry(data_frame, textvariable=self.gross_weight_kg_var, width=15)
        gross_entry.grid(row=5, column=1, padx=(5, 0), pady=5, sticky="w")
        
        # Вес втулки
        ttk.Label(data_frame, text="Вес втулки, г:").grid(
            row=5, column=1, sticky="w", padx=(115, 0), pady=5
        )        
        sleeve_entry = ttk.Entry(data_frame, textvariable=self.sleeve_weight_var, width=10)
        sleeve_entry.grid(row=5, column=1, padx=(270, 0), pady=5, sticky="w")        

        net_entry = ttk.Entry(data_frame, textvariable=self.net_weight_kg_var, width=15, state="readonly")
        net_entry.grid(row=5, column=1, padx=(115, 0), pady=5, sticky="w")
        net_entry.grid_remove()

        # Номер заказа (3 части)
        ttk.Label(data_frame, text="№ заказа:").grid(
            row=7, column=0, sticky="w", pady=5
        )
        entry_prefix = ttk.Entry(data_frame, textvariable=self.order_prefix, width=4)
        entry_prefix.grid(row=7, column=1, padx=(5, 0), pady=5, sticky="w")

        entry_number = ttk.Entry(data_frame, textvariable=self.order_number, width=7)
        entry_number.grid(row=7, column=1, padx=(42, 0), pady=5, sticky="w")

        entry_suffix = ttk.Entry(data_frame, textvariable=self.order_suffix, width=6)
        entry_suffix.grid(row=7, column=1, padx=(95, 0), pady=5, sticky="w")
        
        ttk.Label(data_frame, text="Поиск вида:").grid(
            row=7, column=1, padx=(145, 0), sticky="w", pady=5
        )
        self.detail_num_search_var = StringVar()
        detail_num_entry = ttk.Entry(data_frame, textvariable=self.detail_num_search_var, width=10)
        detail_num_entry.grid(row=7, column=1, padx=(270, 0), pady=5, sticky="w")
        
        # Кнопка редактирования списка упаковщиков
        edit_packers_btn = ttk.Button(
            data_frame,
            text="📝 Список",
            command=self.edit_packers_list
        )
        edit_packers_btn.grid(row=8, column=1, padx=(115, 0), sticky="w", pady=5)        

        # Дата/Упаковщик
        ttk.Label(data_frame, text="Упаковщик/ Дата:").grid(
            row=8, column=0, sticky="w", pady=5
        )
        
        # Создаем меню-кнопку упаковщиков
        packers = self.config_manager.get_packers()
        self.packer_menubutton = ttk.Menubutton(
            data_frame, 
            text="📦",
            width=3
        )
        self.packer_menubutton.grid(row=8, column=0, padx=(190, 0), pady=5, sticky="w")
        
        # Создаем меню
        self.packer_menubutton.menu = tk.Menu(self.packer_menubutton, tearoff=0)
        self.packer_menubutton["menu"] = self.packer_menubutton.menu
        self.packer_menubutton.grid(row=8, column=0, padx=(190, 0), pady=5, sticky="w")
        # Заполняем меню упаковщиками
        self.update_packers_menu()
        # Дата
        date_entry = ttk.Entry(data_frame, textvariable=self.date_var, width=15)
        date_entry.grid(row=8, column=1, padx=5, pady=5, sticky="w")
        # Упаковщик - СКРЫТО
        packers = self.config_manager.get_packers()
        default_packer = packers[0] if packers else ""
        self.packer_var = StringVar(value=default_packer)
        packer_entry = ttk.Entry(data_frame, textvariable=self.packer_var, width=25)
        packer_entry.grid(row=8, column=1, padx=(115, 0), pady=5, sticky="w")
        packer_entry.grid_remove()

        # Вес коробки брутто/нетто - СКРЫТО
        # ttk.Label(data_frame, text="Вес коробки брутто/нетто, кг:").grid(
        #     row=9, column=0, sticky="w", pady=5
        # )
        gross_entry = ttk.Entry(data_frame, textvariable=self.total_gross_var, width=15, state="readonly")
        gross_entry.grid(row=9, column=1, padx=5, pady=5, sticky="w")
        gross_entry.grid_remove()

        net_entry = ttk.Entry(data_frame, textvariable=self.total_net_var, width=15, state="readonly")
        net_entry.grid(row=9, column=1, padx=(115, 0), pady=5, sticky="w")
        net_entry.grid_remove()
        
        # Схема намотки и Диаметр втулки
        ttk.Label(data_frame, text="Схема намотки:").grid(
            row=9, column=0, sticky="w", pady=5
        )
        winding_entry = ttk.Entry(data_frame, textvariable=self.winding_scheme_var, width=5)
        winding_entry.grid(row=9, column=0, padx=(190, 0), pady=5, sticky="w")
        
        ttk.Label(data_frame, text="Диаметр втулки, мм:").grid(
            row=9, column=1, sticky="w", pady=5
        )
        diameter_entry = ttk.Entry(data_frame, textvariable=self.sleeve_diameter_var, width=5)
        diameter_entry.grid(row=9, column=1, padx=(210, 0), pady=5, sticky="w")
        
        # Кнопка для открытия окна втулки
        ttk.Button(
            data_frame, 
            text="✓ Ярлык на втулку", 
            command=self.open_weight_orders_window
        ).grid(row=10, column=0, pady=5, sticky="w")
        
        ttk.Checkbutton(data_frame, 
                       text="Без Производителя", 
                       variable=self.show_manufacturer_var
        ).grid(row=10, column=1, sticky="w", pady=5)        
                           
        self.gross_weight_kg_var.trace_add("write", self.calculate_net_weight)
        self.sleeve_weight_var.trace_add("write", self.calculate_net_weight)
        
    def check_manufacturer_visibility(self, customer_name):
        """Проверяет нужно ли показывать производителя для заказчика"""
        if customer_name:
            # Используем config_manager для поиска в without_manufacturer
            found_customer = self.config_manager.find_customer(customer_name)
            # Если заказчик найден в списке without_manufacturer - ставим чекбокс (True = "Без производителя")
            self.show_manufacturer_var.set(found_customer is not None)
        else:
            # Если заказчик пустой - сбрасываем чекбокс
            self.show_manufacturer_var.set(False)
            
    def on_customer_changed(self, *args):
        """Обрабатывает изменение заказчика и проверяет видимость производителя"""
        customer_name = self.customer_var.get()
        self.check_manufacturer_visibility(customer_name)
        
    def open_weight_orders_window(self):
        """Открывает окно для работы с втулками"""
        if self.weight_orders_window and self.weight_orders_window.winfo_exists():
            self.weight_orders_window.lift()
            return

        # Создаем новое окно
        self.weight_orders_window = tk.Toplevel(self.parent)
        self.weight_orders_window.title("Втулка")
        self.weight_orders_window.geometry("440x600")
        self.weight_orders_window.grab_set()
        
        # Центрируем окно
        self.weight_orders_window.update_idletasks()
        width = self.weight_orders_window.winfo_width()
        height = self.weight_orders_window.winfo_height()
        x = (self.weight_orders_window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.weight_orders_window.winfo_screenheight() // 2) - (height // 2)
        self.weight_orders_window.geometry(f"+{x}+{y}")
        self.weight_orders_window.bind("<Escape>", lambda e: self.on_weight_orders_close())
        
        # Создаем модуль втулки в этом окне
        self.weight_orders_module = WeightOrdersPrinter(self.weight_orders_window)
        
        # Устанавливаем обработчик закрытия окна
        self.weight_orders_window.protocol("WM_DELETE_WINDOW", self.on_weight_orders_close)
        
    def on_weight_orders_close(self):
        """Обработчик закрытия окна втулки"""
        if self.weight_orders_window:
            self.weight_orders_window.destroy()
            self.weight_orders_window = None        
        
    def set_preview_module(self, preview_module):
        """Устанавливает связь с модулем предпросмотра для обратной связи"""
        self.preview_module = preview_module
        
    def parse_float(self, value):
        """Преобразует строку в float, заменяя запятую на точку"""
        if isinstance(value, str):
            return float(value.replace(',', '.'))
        return float(value)        
        
    def load_box_sizes(self):
        """Загружает список коробок из shared_utils.json"""
        try:
            settings = self.config_manager.load_json_settings("shared_utils.json")
            weight_box = settings.get("weight_box", {})
            box_sizes = list(weight_box.keys())
            
            return box_sizes
            
        except Exception as e:
            print(f"Ошибка загрузки списка коробок: {e}")
            return []

    def on_box_selected(self, event=None):
        """Обрабатывает выбор коробки из списка"""
        selected_size = self.box_size_var.get()
        if selected_size:
            try:
                settings = self.config_manager.load_json_settings("shared_utils.json")
                weight_box = settings.get("weight_box", {})
                box_weight_g = weight_box.get(selected_size, 0)
                box_weight_kg = box_weight_g / 1000.0
                self.box_weight_var.set(f"{box_weight_kg:.2f}")
                
                # Запускаем пересчет весов
                self.calculate_box_weights()
                
            except Exception as e:
                print(f"Ошибка загрузки веса коробки: {e}")

    def open_box_editor(self):
        """Открывает редактор коробок"""
        if self.box_editor_window and self.box_editor_window.winfo_exists():
            self.box_editor_window.lift()
            return

        self.box_editor_window = tk.Toplevel(self.parent)
        self.box_editor_window.title("Редактирование списка коробок")
        self.box_editor_window.geometry("430x600")
        self.box_editor_window.grab_set()

        # Центрирование окна
        self.box_editor_window.update_idletasks()
        width = self.box_editor_window.winfo_width()
        height = self.box_editor_window.winfo_height()
        x = (self.box_editor_window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.box_editor_window.winfo_screenheight() // 2) - (height // 2)
        self.box_editor_window.geometry(f"+{x}+{y}")
        self.box_editor_window.bind("<Escape>", lambda e: self.box_editor_window.destroy())

        frame = ttk.Frame(self.box_editor_window, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        # Фрейм для прокрутки
        container = ttk.Frame(frame)
        container.pack(fill=tk.BOTH, expand=True)

        # Создаем canvas и scrollbar
        canvas = tk.Canvas(container)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Загружаем текущий список коробок
        current_boxes = self.get_current_boxes()

        # Создаем заголовки
        header_frame = ttk.Frame(scrollable_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(header_frame, text="Название коробки", font=("Arial", 12, "bold")).pack(side=tk.LEFT, padx=(0, 30))
        ttk.Label(header_frame, text="Вес коробки (г)", font=("Arial", 12, "bold")).pack(side=tk.LEFT, padx=(15, 15))

        # Создаем поля ввода
        self.box_size_entries = []
        self.box_weight_entries = []

        for size, weight in current_boxes.items():
            self._create_box_row(scrollable_frame, size, weight)

        # Добавляем пустую строку
        self._create_box_row(scrollable_frame, "", "")

        # Кнопки управления
        button_frame = ttk.Frame(frame)
        button_frame.pack(pady=10)

        ttk.Button(button_frame, text="💾 Сохранить", command=self.save_boxes).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="➕ Добавить строку", 
                  command=lambda: self._create_box_row(scrollable_frame, "", "")).pack(side=tk.LEFT, padx=(5, 30))

        self.box_editor_window.bind("<Return>", lambda e: self.save_boxes())

    def _create_box_row(self, parent, size, weight):
        """Создает строку с полями ввода для коробки"""
        row_frame = ttk.Frame(parent)
        row_frame.pack(fill=tk.X, pady=2)

        # Поле для размеров
        size_entry = ttk.Entry(row_frame, width=30)
        size_entry.insert(0, size)
        size_entry.pack(side=tk.LEFT, padx=(0, 10))
        self.box_size_entries.append(size_entry)

        # Поле для веса
        weight_entry = ttk.Entry(row_frame, width=15)
        weight_entry.insert(0, str(weight))
        weight_entry.pack(side=tk.LEFT, padx=(0, 10))
        self.box_weight_entries.append(weight_entry)

        # Кнопка удаления
        ttk.Button(row_frame, text="×", width=2,
                  command=lambda: self._remove_box_row(row_frame, size_entry, weight_entry)).pack(side=tk.RIGHT)

    def _remove_box_row(self, row_frame, size_entry, weight_entry):
        """Удаляет строку с полями ввода"""
        if len(self.box_size_entries) > 1:
            row_frame.destroy()
            self.box_size_entries.remove(size_entry)
            self.box_weight_entries.remove(weight_entry)

    def get_current_boxes(self):
        """Возвращает текущий список коробок"""
        try:
            settings = self.config_manager.load_json_settings("shared_utils.json")
            return settings.get("weight_box", {})
        except:
            return {}

    def save_boxes(self):
        """Сохраняет список коробок в shared_utils.json"""
        try:
            new_boxes = {}
            for size_entry, weight_entry in zip(self.box_size_entries, self.box_weight_entries):
                size = size_entry.get().strip()
                weight_str = weight_entry.get().strip()
                
                if size and weight_str:
                    try:
                        weight = int(weight_str)
                        new_boxes[size] = weight
                    except ValueError:
                        continue

            # Загружаем текущие настройки и обновляем weight_box
            settings = self.config_manager.load_json_settings("shared_utils.json")
            settings["weight_box"] = new_boxes
            
            if self.config_manager.save_json_settings("shared_utils.json", settings):
                self.load_box_sizes()  # Обновляем комбобокс
                if hasattr(self, 'preview_module') and self.preview_module:
                    self.preview_module.load_box_sizes()
                self.box_editor_window.destroy()
            else:
                messagebox.showerror("Ошибка", "Не удалось сохранить список коробок")
                
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при сохранении: {str(e)}")        
        
    def calculate_total_quantity(self, *args):
        """Рассчитывает общее количество: ролики × этикетки в ролике"""
        try:
            rolls_count = int(self.rolls_count_var.get() or 0)
            quantity_per_roll = int(self.quantity_var.get() or 0)
            
            if rolls_count == 0 or quantity_per_roll == 0:
                self.total_quantity_var.set("")
                return
                
            total = rolls_count * quantity_per_roll
            self.total_quantity_var.set(str(total))
            
        except (ValueError, TypeError):
            self.total_quantity_var.set("")
        
    def export_box_to_excel(self):
        """Экспортирует данные коробки в Excel"""
        try:
            # Проверяем, что все необходимые данные заполнены
            if not self.rolls_count_var.get() or not self.order_number.get():
                return {'success': False, 'error': 'Введите количество роликов и номер заказа'}

            # Проверяем наличие модуля данных
            if not hasattr(self, 'order_data_module') or not self.order_data_module:
                return {'success': False, 'error': 'Модуль данных не подключен'}
                
            # Загружаем путь к Excel файлу
            self.order_data_module.load_excel_folder_path()
            
            if not self.order_data_module.excel_file_path:
                return {'success': False, 'error': 'Сначала выберите папку для Excel'}

            # Создаем экспортер и выполняем экспорт
            exporter = WeightOrdersExporter(
                excel_file_path=self.order_data_module.excel_file_path,
                roll_module=self,
                preview_module=self.preview_module
            )
            
            result = exporter.export_data()  # enable_pallet=False по умолчанию
            
            return result  # Просто возвращаем результат
                
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def clear_box_excel_data(self):
        """Очищает данные коробки в Excel"""
        try:
            # Проверяем наличие модуля данных
            if not hasattr(self, 'order_data_module') or not self.order_data_module:
                return False
                
            # Загружаем путь к Excel файлу
            self.order_data_module.load_excel_folder_path()
            
            if not self.order_data_module.excel_file_path:
                return False
                
            if not os.path.exists(self.order_data_module.excel_file_path):
                return False

            # Создаем экспортер и выполняем очистку
            exporter = WeightOrdersExporter(
                excel_file_path=self.order_data_module.excel_file_path,
                roll_module=self,
                preview_module=self.preview_module
            )
            
            success = exporter.clear_all_rolls()  # enable_pallet=False по умолчанию
            return success
            
        except Exception as e:
            print(f"Ошибка при очистке Excel: {e}")
            return False
        
    def set_show_manufacturer(self, show):
        """Устанавливает видимость производителя извне"""
        self.show_manufacturer_var.set(show)        

    def set_order_data_module(self, order_data_module):
        """Устанавливает прямую связь с модулем обработки данных заказов"""
        self.order_data_module = order_data_module        
        
    def update_packers_menu(self):
        """Обновляет меню упаковщиков"""
        # Очищаем текущее меню
        self.packer_menubutton.menu.delete(0, tk.END)
        
        # Получаем обновленный список упаковщиков
        packers = self.config_manager.get_packers()
        
        # Заполняем меню заново
        for packer in packers:
            self.packer_menubutton.menu.add_command(
                label=packer,
                command=lambda p=packer: self.packer_var.set(p)
            )
        
    def calculate_net_weight(self, *args):
        """Автоматически рассчитывает вес нетто"""
        try:
            gross_kg = self.parse_float(self.gross_weight_kg_var.get() or 0)
            
            # Если вес брутто 0 - очищаем нетто
            if gross_kg == 0:
                self.net_weight_kg_var.set("")
                self.total_gross_var.set("")
                self.total_net_var.set("")
                return
                
            sleeve_g = self.parse_float(self.sleeve_weight_var.get() or 0)
            sleeve_kg = sleeve_g / 1000
            net_kg = gross_kg - sleeve_kg
            
            # Если результат отрицательный или нулевой - очищаем
            if net_kg <= 0:
                self.net_weight_kg_var.set("")
                self.total_gross_var.set("")
                self.total_net_var.set("")
            else:
                self.net_weight_kg_var.set(f"{net_kg:.2f}")
                
        except (ValueError, TypeError):
            self.net_weight_kg_var.set("")
        
    # Раздел для настройки поля ввода
    def control_key_handler(self, event):
        """Обработчик горячих клавиш Ctrl+C и Ctrl+V"""
        if event.keycode == 86 or event.keycode == 118:  # V key - вставка
            self.paste_text(event.widget)
            return "break"
        elif event.keycode == 67 or event.keycode == 99:  # C key - копирование
            self.copy_text(event.widget)
            return "break"
        return None
        
    def add_context_menu_to_text(self, text_widget):
        """Добавляет контекстное меню к текстовому виджету"""
        menu = tk.Menu(text_widget, tearoff=0)
        menu.add_command(label="Копировать", command=lambda: self.copy_text_from_text_widget(text_widget))
        menu.add_command(label="Вставить", command=lambda: self.paste_text_to_text_widget(text_widget))
        text_widget.bind("<Button-3>", lambda e: menu.tk_popup(e.x_root, e.y_root))

    def copy_text_from_text_widget(self, widget):
        """Копирует текст из текстового виджета"""
        try:
            text = widget.get("1.0", "end-1c")
            if text:
                widget.clipboard_clear()
                widget.clipboard_append(text)
        except Exception as e:
            print(f"Ошибка копирования: {e}")

    def paste_text_to_text_widget(self, widget):
        """Вставляет текст в текстовый виджет"""
        try:
            text = widget.clipboard_get()
            if text:
                widget.delete("1.0", tk.END)
                widget.insert("1.0", text)
        except Exception as e:
            print(f"Ошибка вставки: {e}")        
        
    def add_context_menu(self, widget):
        """Добавляет контекстное меню к виджету"""
        menu = tk.Menu(widget, tearoff=0)
        menu.add_command(label="Копировать", command=lambda: self.copy_text(widget))
        menu.add_command(label="Вставить", command=lambda: self.paste_text(widget))
        widget.bind("<Button-3>", lambda e: menu.tk_popup(e.x_root, e.y_root))

    def copy_text(self, widget):
        """Копирует текст в буфер обмена"""
        try:
            text = widget.get()
            if text:
                widget.clipboard_clear()
                widget.clipboard_append(text)
        except Exception as e:
            print(f"Ошибка копирования: {e}")

    def paste_text(self, widget):
        """Вставляет текст из буфера обмена"""
        try:
            text = widget.clipboard_get()
            if text:
                widget.delete(0, tk.END)
                widget.insert(0, text)
        except Exception as e:
            print(f"Ошибка вставки: {e}")

    def edit_packers_list(self):
        """Открывает окно редактирования списка упаковщиков"""
        if hasattr(self, 'packers_window') and self.packers_window and self.packers_window.winfo_exists():
            self.packers_window.lift()
            return

        self.packers_window = tk.Toplevel(self.parent)
        self.packers_window.title("Редактирование списка")
        self.packers_window.geometry("320x400")
        self.packers_window.grab_set()

        # Центрирование окна
        self.packers_window.update_idletasks()
        width = self.packers_window.winfo_width()
        height = self.packers_window.winfo_height()
        x = (self.packers_window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.packers_window.winfo_screenheight() // 2) - (height // 2)
        self.packers_window.geometry(f"+{x}+{y}")

        self.packers_window.bind("<Escape>", lambda e: self.packers_window.destroy())

        frame = ttk.Frame(self.packers_window, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        # Заголовок
        ttk.Label(frame, text="Список упаковщиков:", font=("Arial", 10, "bold")).pack(
            pady=(0, 10)
        )

        # Фрейм для полей ввода
        input_frame = ttk.Frame(frame)
        input_frame.pack(fill=tk.BOTH, expand=True)

        # Загружаем текущий список упаковщиков
        current_packers = self.config_manager.get_packers()
        self.packer_entries = []

        # Создаем поля ввода для каждого упаковщика
        for packer in current_packers:
            entry = ttk.Entry(input_frame, width=25)
            entry.insert(0, packer)
            entry.pack(pady=2, fill=tk.X)
            self.packer_entries.append(entry)

        # Добавляем пустое поле для нового упаковщика
        new_entry = ttk.Entry(input_frame, width=25)
        new_entry.pack(pady=2, fill=tk.X)
        self.packer_entries.append(new_entry)

        # Кнопки управления
        button_frame = ttk.Frame(frame)
        button_frame.pack(pady=10)

        ttk.Button(button_frame, text="💾 Сохранить", command=self.save_packers).pack(
            side=tk.LEFT, padx=5
        )

        # Привязка Enter к сохранению
        self.packers_window.bind("<Return>", lambda e: self.save_packers())

    def save_packers(self):
        """Сохраняет измененный список упаковщиков"""
        try:
            # Собираем все непустые значения
            new_packers = []
            for entry in self.packer_entries:
                packer_name = entry.get().strip()
                if packer_name:
                    new_packers.append(packer_name)

            if not new_packers:
                messagebox.showwarning("Предупреждение", "Список упаковщиков не может быть пустым")
                return

            # Сохраняем через config_manager
            if self.config_manager.save_packers(new_packers):
                messagebox.showinfo("Сохранено", "Список упаковщиков успешно обновлен!")
                # Обновляем меню упаковщиков
                self.update_packers_menu()
                if self.packers_window:
                    self.packers_window.destroy()
                    self.packers_window = None
            else:
                messagebox.showerror("Ошибка", "Не удалось сохранить список упаковщиков")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при сохранении: {str(e)}")
