import os
import re
import tkinter as tk
from tkinter import ttk, StringVar

from core.parse.name_shortener import NameShortener
from main_ui.second_ui.comment_manager import CommentManager


# noinspection PyTypeChecker,SpellCheckingInspection
class OrderDataProcessor:
    """Модуль обработки данных заказов (правая часть интерфейса)."""
    
    def __init__(self, parent, coordinator=None, data_manager=None, config_manager=None):
        self.comment_text = None
        self.comment_label_frame = None
        self.data_manager_status_label = None
        self.name_combobox = None
        self.current_order = None
        self.filtered_parsed_data = None
        self.parse_status = None
        self.parent = parent
        self.config_manager = config_manager
        self.data_manager = data_manager
        self.data_manager.set_status_callback(self.update_status_message)
        self.coordinator = coordinator
        
        # Переменные для парсинга
        self.folder_path = StringVar(value="")
        self.parsed_data = []  # Список данных
        self.parsed_names_list = []
        self.selected_name = StringVar(value="")  # Выбранное название
        self.cached_order_number = ""
        self.cached_order_data = None
        
        # Переменные для Excel
        self.excel_file_path = None
        self.excel_folder_path = ""
        
        # Ссылки на другие модули
        self.roll_module = None
        self.preview_module = None
        
        self.load_initial_settings()
        self.detail_num_search = StringVar(value="")
        self.create_ui()
        # Инициализируем CommentManager
        self.comment_manager = CommentManager(
            parent=self.parent,
            comment_button=None,  # Без кнопки
            config_manager=self.config_manager,
            customer_var=None  # Установим позже в set_roll_module
        )
        self.name_shortener = NameShortener(
            config_manager=self.config_manager,
            coordinator=self.coordinator
        )
        if self.coordinator and hasattr(self.coordinator, 'subscribe'):
            self.coordinator.subscribe(self.on_settings_changed)

        self.comment_popup = None  # Ссылка на всплывающее окно

    # noinspection PyUnusedLocal
    def on_settings_changed(self, context=None):
        """Обработчик изменений настроек от координатора"""
        # Пересчитываем вместимость коробки при изменении настроек
        if self.preview_module is not None:
            # Получаем текущий текст тиража
            current_text = self.preview_module.tirazh_label.cget("text")
            
            # Убираем старую информацию о вместимости если есть
            if "| Влезет в коробку:" in current_text:
                current_text = current_text.split("|")[0].strip()
            
            # Рассчитываем новую вместимость
            capacity = self._calculate_box_capacity()
            
            # Добавляем информацию о вместимости если есть
            if capacity:
                current_text = f"{current_text} | Влезет в коробку: {capacity}"
            
            # Обновляем отображение
            self.preview_module.tirazh_label.config(
                text=current_text,
                foreground="green"
            )
            
        try:
            settings = self.config_manager.load_json_settings("shared_utils.json")
            new_folder_path = settings.get("weight_data_base", "")
            if new_folder_path != self.folder_path.get():
                self.folder_path.set(new_folder_path)
                # Сбрасываем статус папки
                if self.parse_status is not None:
                    if new_folder_path:
                        folder_name = os.path.basename(new_folder_path)
                        self.parse_status.config(text=f"Папка: {folder_name}", foreground="blue")
                    else:
                        self.parse_status.config(text="Папка не выбрана", foreground="red")
        except Exception as e:
            print(f"Ошибка обновления пути XML папки: {e}")            
        
    def load_initial_settings(self):
        """Загружает начальные настройки"""
        try:
            saved_settings = self.config_manager.load_json_settings("shared_utils.json")
            self.folder_path.set(saved_settings.get("weight_data_base", ""))
            self.load_excel_folder_path()
        except Exception as e:
            print(f"Ошибка загрузки настроек: {e}")

    def create_ui(self):
        """Создает правую часть интерфейса (XML парсинг и Excel экспорт)"""
        # Основной контейнер
        main_container = ttk.Frame(self.parent, padding=5)
        main_container.pack(fill=tk.BOTH, expand=True, side=tk.RIGHT)

        # Верхняя часть: Парсинг XML
        xml_frame = ttk.LabelFrame(main_container, text="Получение названия", padding=5)
        xml_frame.pack(fill=tk.BOTH, expand=False, pady=(0, 10))
        
        ttk.Label(xml_frame, text="Поиск вида:").grid(
            row=0, column=0, sticky="w", pady=5
        )
        
        detail_num_entry = ttk.Entry(xml_frame, textvariable=self.detail_num_search, width=12)
        detail_num_entry.grid(row=0, column=0, padx=(125, 0), pady=5, sticky="w")
        # Ручной ввод + сканирование кода
        detail_num_entry.bind("<Return>", self.handle_detail_num_enter)
        
        # Кнопки поиска архива и журнала упаковки
        archive_frame = ttk.Frame(xml_frame)
        archive_frame.grid(row=0, column=0, padx=(210, 0), sticky="w", pady=5)

        ttk.Button(
            archive_frame,
            text="🔍 Найти архив",
            command=self.open_archive_search_window
        ).pack(side=tk.LEFT, padx=(10, 5))

        ttk.Button(
            archive_frame,
            text="📦 Журнал упаковки",
            command=self.open_packaging_log
        ).pack(side=tk.LEFT, padx=5)

        # Строка статуса парсинга
        self.parse_status = ttk.Label(
            xml_frame, 
            text="", 
            foreground="black", 
            font=("Arial", 14), 
            wraplength=500
        )
        self.parse_status.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 5))

        # Выбор названия
        ttk.Label(xml_frame, text="Выбор вида:").grid(row=2, column=0, sticky="w", pady=5)
        self.name_combobox = ttk.Combobox(xml_frame, textvariable=self.selected_name, state="readonly", width=61)
        self.name_combobox.grid(row=2, column=0, padx=(125, 0), sticky="w", pady=5)
        self.name_combobox.bind("<<ComboboxSelected>>", self.on_name_selected)

        # === Строка статуса для data manager ===
        self.data_manager_status_label = tk.Label(
            xml_frame, 
            text="", 
            foreground="blue",
            font=("Arial", 14),
            wraplength=500,
            justify=tk.CENTER,
            height=2
        )
        self.data_manager_status_label.grid(row=3, column=0, columnspan=2, sticky="w", pady=5)

        xml_frame.columnconfigure(0, weight=1)
        xml_frame.columnconfigure(1, weight=1)
        
        # === Секция комментариев ===
        self.comment_label_frame = ttk.LabelFrame(xml_frame, text="Комментарии", padding=5)
        self.comment_label_frame.grid(row=5, column=0, columnspan=2, pady=5, sticky="w")
        self.comment_label_frame.grid_propagate(False)
        self.comment_label_frame.config(width=600, height=200)

        # Text виджет с прокруткой
        self.comment_text = tk.Text(
            self.comment_label_frame,
            height=8,
            wrap=tk.WORD,
            font=("Arial", 12),
            background="#FFFFE0",
            state="disabled"  # Только для чтения
        )
        self.comment_text.grid(row=0, column=0, sticky="ns")

        # Scrollbar
        comment_scrollbar = ttk.Scrollbar(
            self.comment_label_frame,
            command=self.comment_text.yview
        )
        comment_scrollbar.grid(row=0, column=1, sticky="ns")
        self.comment_text.config(yscrollcommand=comment_scrollbar.set)

        self.comment_label_frame.columnconfigure(0, weight=1)
        self.comment_label_frame.rowconfigure(0, weight=1)
        
        # Скрываем по умолчанию
        self.comment_label_frame.grid_remove()
        self.comment_label_frame.bind("<Button-1>", self.toggle_comment_popup)
        
        # Инициализируем статусы
        self.reset_status_messages()

    # noinspection PyUnusedLocal
    def toggle_comment_popup(self, event=None):
        """Открывает или фокусирует всплывающее окно с комментариями"""
        # Проверяем, есть ли комментарии
        if not self.comment_label_frame.winfo_ismapped():
            return

        if self.comment_popup is not None and self.comment_popup.winfo_exists():
            # Окно уже открыто — поднимаем на передний план
            self.comment_popup.lift()
            self.comment_popup.focus_force()
        else:
            # Создаём новое окно
            self._create_comment_popup()

    def _create_comment_popup(self):
        """Создаёт всплывающее окно с полным текстом комментариев"""
        if not self.comment_label_frame.winfo_ismapped():
            return

        # Получаем текущий текст из comment_text
        current_text = self.comment_text.get("1.0", tk.END).strip()
        if not current_text:
            return

        # Создаём окно
        self.comment_popup = tk.Toplevel(self.parent)
        self.comment_popup.title("Комментарии (отдельное окно)")
        self.comment_popup.geometry("605x400")

        # Позиционируем так, чтобы низ окна был на уровне низа xml_frame
        self.comment_popup.update_idletasks()
        x = self.comment_label_frame.winfo_rootx() - 14
        # Вычисляем y: низ xml_frame минус высота окна
        xml_frame_y_bottom = self.comment_label_frame.master.winfo_rooty() + self.comment_label_frame.master.winfo_height()
        window_height = 400  # высота окна
        y = xml_frame_y_bottom - window_height
        self.comment_popup.geometry(f"+{x}+{y}")
        self.comment_popup.bind("<Escape>", lambda e: self._close_comment_popup())

        # Делаем окно перемещаемым
        self.comment_popup.transient(self.parent)

        # Text виджет с прокруткой
        text_widget = tk.Text(
            self.comment_popup,
            wrap=tk.WORD,
            font=("Arial", 12),
            background="#FFFFE0"
        )
        text_widget.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        text_widget.insert("1.0", current_text)
        text_widget.config(state="disabled")

        scrollbar = ttk.Scrollbar(self.comment_popup, command=text_widget.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.config(yscrollcommand=scrollbar.set)

        # Кнопка закрытия
        close_btn = ttk.Button(
            self.comment_popup,
            text="Закрыть",
            command=self._close_comment_popup
        )
        close_btn.pack(pady=5)

        # Закрытие по крестику
        self.comment_popup.protocol("WM_DELETE_WINDOW", self._close_comment_popup)

    def _close_comment_popup(self):
        """Закрывает всплывающее окно"""
        if self.comment_popup is not None and self.comment_popup.winfo_exists():
            self.comment_popup.destroy()
            self.comment_popup = None

    def _update_comment_popup_content(self):
        """Обновляет содержимое всплывающего окна, если оно открыто"""
        if self.comment_popup is None or not self.comment_popup.winfo_exists():
            return

        # Получаем текущий текст
        current_text = self.comment_text.get("1.0", tk.END).strip()

        if not current_text:
            # Нет комментариев — закрываем окно
            self._close_comment_popup()
            return

        # Ищем текстовый виджет в окне
        for child in self.comment_popup.winfo_children():
            if isinstance(child, tk.Text):
                child.config(state="normal")
                child.delete("1.0", tk.END)
                child.insert("1.0", current_text)
                child.config(state="disabled")
                break

    def open_packaging_log(self):
        """Открывает окно журнала упаковки"""
        try:
            from core.packaging.packaging_log_window import PackagingLogWindow
            PackagingLogWindow(
                parent=self.parent,
                config_manager=self.config_manager,
                order_processor=self,
                coordinator=self.coordinator
            )
        except Exception as e:
            self.data_manager_status_label.config(
                text=f"Не удалось открыть журнал упаковки: {str(e)}",
                foreground="red"
            )

    def get_packaging_defaults(self):
        """Возвращает словарь с данными для новой записи в журнале упаковки"""
        defaults = {
            'date': '',
            'order_number': '',
            'customer': '',
            'product_name': '',
            'packer_name': '',
            'quantity_labels': None,
            'large_boxes': None,
            'small_boxes': None,
            'aquaLife_boxes': None,
            'note': ''
        }

        # Номер заказа из roll_module
        if self.roll_module:
            prefix = self.roll_module.order_prefix.get().strip()
            number = self.roll_module.order_number.get().strip()
            suffix = self.roll_module.order_suffix.get().strip()

            full_number = ""
            if prefix:
                full_number += prefix
            if number:
                full_number += number
            if suffix:
                full_number += suffix

            defaults['order_number'] = full_number

            # Заказчик из roll_module
            defaults['customer'] = self.roll_module.customer_var.get().strip()

            # Упаковщик
            if hasattr(self.roll_module, 'packer_var'):
                defaults['packer_name'] = self.roll_module.packer_var.get()

            # Наименование из многострочного поля
            if hasattr(self.roll_module, 'product_text'):
                product_text = self.roll_module.product_text.get("1.0", "end-1c")
                defaults['product_name'] = product_text.strip()

        # Сумма тиражей, если видов больше одного И НЕ ВЫБРАН КОНКРЕТНЫЙ ВИД
        if hasattr(self, 'parsed_data') and self.parsed_data:
            # Проверяем, выбран ли конкретный вид
            selected_name = self.selected_name.get().strip()
            has_selected = bool(selected_name) and selected_name in [p.get('name', '') for p in self.parsed_data]

            if not has_selected:
                # Вид не выбран - суммируем все тиражи
                total_tirazh = 0
                for product in self.parsed_data:
                    tirazh = product.get('tirazh', '')
                    if tirazh:
                        try:
                            total_tirazh += int(tirazh)
                        except:
                            pass
                if total_tirazh > 0:
                    defaults['quantity_labels'] = total_tirazh
            else:
                # Вид выбран - берём тираж выбранного вида
                for product in self.parsed_data:
                    if product.get('name', '') == selected_name:
                        tirazh = product.get('tirazh', '')
                        if tirazh:
                            try:
                                defaults['quantity_labels'] = int(tirazh)
                            except:
                                pass
                        break

        # Дата сегодня
        from datetime import datetime
        defaults['date'] = datetime.now().strftime('%Y-%m-%d')

        return defaults

    def _display_comments(self, comments, operations):
        """Отображает комментарии в интерфейсе"""
        cutting_comment = comments.get('cutting_comment', '')
        packaging_comment = comments.get('packaging_comment', '')
        aggregation_status = operations.get('aggregation_status', '')

        result = self.comment_manager.set_comments(
            cutting_comment=cutting_comment,
            packaging_comment=packaging_comment,
            aggregation_status=aggregation_status
        )

        # Всегда очищаем text widget
        self.comment_text.config(state="normal")
        self.comment_text.delete("1.0", tk.END)

        comment_text = ""
        if cutting_comment:
            comment_text += "📐 КОММЕНТАРИЙ РЕЗКИ:\n"
            comment_text += f"{cutting_comment}\n\n"
        if packaging_comment:
            comment_text += "📦 КОММЕНТАРИЙ УПАКОВКИ:\n"
            comment_text += f"{packaging_comment}\n"

        special_requirements = self.comment_manager.get_special_requirements()
        if special_requirements:
            comment_text += "\n🚨 Особые требования:\n"
            comment_text += f"{special_requirements}\n"

        if result['has_comments'] or result['has_aggregation']:
            self.comment_label_frame.grid()

            title = "Комментарии"
            if result['has_aggregation']:
                title = f"🔄 ЕСТЬ АГРЕГАЦИЯ"
            if result['has_comments']:
                title = f"⚠ {title}"

            self.comment_label_frame.config(text=title)

            if comment_text:
                self.comment_text.insert("1.0", comment_text.strip())

            # Мигаем только если есть комментарии
            if result['has_comments']:
                self._blink_comment_title(blink_count=3)
        else:
            self.comment_label_frame.grid_remove()

        self.comment_text.config(state="disabled")
        self._update_comment_popup_content()

    def _blink_comment_title(self, blink_count=3):
        """Мигает треугольником в заголовке 2-3 раза"""
        current_title = self.comment_label_frame.cget("text")
        
        def blink_sequence(step=0):
            if step < blink_count * 2:
                if step % 2 == 0:
                    # Без треугольника
                    title_without = current_title.replace("⚠ ", "")
                    self.comment_label_frame.config(text=title_without)
                else:
                    # С треугольником
                    self.comment_label_frame.config(text=current_title)
                
                # Следующий шаг через 500ms
                self.parent.after(500, lambda: blink_sequence(step + 1))
        
        blink_sequence()
        
    def show_product_results(self, products, search_text):
        """Показывает найденные продукты в комбобоксе"""
        names_list = []
        self.filtered_parsed_data = []
        
        for product in products:
            name = product.get('full_name', product.get('product_name', ''))
            names_list.append(name)
            product_dict = {
                'name': name,
                'detail_num': product.get('detail_number', ''),
                'sheet_number': product.get('sheet_number', ''),
                'date_emission': product.get('date_emission', ''),
                'gtin': product.get('gtin', ''),
                'tirazh': product.get('quantity', ''),
                'stream': product.get('stream', '1')
            }
            self.filtered_parsed_data.append(product_dict)
        
        if names_list:
            self.name_combobox['values'] = names_list
            self.parse_status.config(
                text=f"Найдено {len(names_list)} видов по '{search_text}'",
                foreground="green"
            )
            self.parent.after(100, lambda: self.name_combobox.focus_set())
            self.parent.after(120, lambda: self.name_combobox.event_generate('<Down>'))
        
    def update_status_message(self, message: str):
        """Обновляет сообщение в data_manager_status_label"""       
        try:
            self.data_manager_status_label.config(text=message)
            if "Идёт создание" in message or "База создана" in message or "База загружена" in message:
                self.data_manager_status_label.config(foreground="blue", font=("Arial", 12, "bold"))
                self.parent.after(9000, lambda: self.data_manager_status_label.config(text=""))
        except Exception as e:
            print(f"UI DEBUG: ошибка обновления UI: {e}")        
        
    def handle_detail_num_enter(self, event=None):
        """Обработчик Enter для поля поиска вида с поддержкой сканирования"""
        # 1. Получаем данные из виджета события ИЛИ из переменной
        if event and hasattr(event, 'widget'):
            # Берем из виджета, который вызвал событие
            input_value = event.widget.get().strip()
        else:
            # Берем из переменной
            input_value = self.detail_num_search.get().strip()
        
        # 2. Проверяем, не сканирование ли это (ищем GTIN)
        gtin = self._extract_gtin_from_input(input_value)
        
        if gtin:
            # 3. Это сканирование - обрабатываем GTIN
            self._process_scanned_gtin(gtin)
            return "break"
        
        # 4. Это обычный ручной ввод
        search_value = input_value
        
        # 5. Проверяем, был ли уже выбран заказ
        current_order = self.roll_module.order_number.get().strip()
        has_cached_data = self.cached_order_data is not None and self.cached_order_data
        
        if not current_order:
            # Если номер заказа пустой - ничего не делаем
            self.parse_status.config(text="Сначала введите номер заказа", foreground="red")
            return "break"
        
        if not has_cached_data or self.cached_order_number is None or self.cached_order_number != current_order:
            # Заказ еще не загружен - запускаем поиск
            if event:
                self.roll_module.on_order_enter_pressed(event)
            else:
                self.roll_module.on_order_enter_pressed()
        
        # 6. Восстанавливаем значение поиска
        def restore_search():
            self.detail_num_search.set(search_value)
        
        self.parent.after(50, restore_search)
        
        # 7. Запускаем поиск продукта
        self.parent.after(100, self.get_product_name)
        
        return "break"
        
    @staticmethod
    def _extract_gtin_from_input(text):
        """Извлекает GTIN из введённого текста"""
        if not text:
            return None
        
        # Паттерны для кодов GS1
        patterns = [
            r'\(01\)(\d{14})',           # (01)04680328050213...
            r'01(\d{14})',               # 0104680328050213...
            r'^\d{14}$',                 # 04680328050213 (чистый GTIN)
            r'GTIN:\s*(\d{14})',         # GTIN: 04680000193177
            r'GTIN\s*(\d{14})',          # GTIN 04680000193177
            r'zz\s+GTIN:\s*(\d{14})',    # zz GTIN: 04680000193177
            r'ZZ(\d{12,13})#\d{8}',      # ZZ4680328050213#00001000
        ]
        
        for i, pattern in enumerate(patterns):
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result = match.group(1) if match.lastindex else match.group(0)
                # Для нового формата ZZ: если длина 13, добавляем ведущий ноль
                if i == 6 and len(result) == 13:
                    result = '0' + result
                return result
        
        return None
    
    def _get_detail_num_by_gtin(self, gtin):
        """
        Находит detail_num по GTIN в parsed_data
        Возвращает последние 3 цифры detail_num или None если не найден
        """
        if not self.parsed_data:
            return None
        
        for product in self.parsed_data:
            product_gtin = product.get('gtin', '')
            if product_gtin == gtin:
                detail_num = product.get('detail_num', '')
                if detail_num:
                    # Ищем цифры в detail_num
                    import re
                    digits = re.findall(r'\d+', detail_num)
                    if digits:
                        # Берём последнюю группу цифр
                        last_digits = digits[-1]
                        # Возвращаем последние 3 цифры
                        return last_digits[-3:] if len(last_digits) >= 3 else last_digits
                return None
        
        return None
        
    def _process_scanned_gtin(self, gtin):
        """Обрабатывает отсканированный GTIN"""
        # Ищем detail_num для этого GTIN
        detail_num_suffix = self._get_detail_num_by_gtin(gtin)
        
        if not detail_num_suffix:
            # GTIN не найден в текущем заказе
            self.parse_status.config(
                text=f"GTIN {gtin} не найден в заказе {self.current_order}", 
                foreground="red"
            )
            self.parent.after(5000, lambda: self.parse_status.config(text=""))
            return
        
        
        # Устанавливаем найденный detail_num в поле поиска
        self.parent.after(100, lambda: self.detail_num_search.set(detail_num_suffix))
        
        # Запускаем поиск продукта по detail_num
        self.parent.after(150, self.get_product_name)                            
        
    def open_archive_search_window(self):
        """Открывает окно поиска архивных поддонов"""
        try:
            from core.archive.archive_search_window import ArchiveSearchWindow
            ArchiveSearchWindow(self.parent, self, config_manager=self.config_manager)
        except Exception as e:
            self.data_manager_status_label.config(text=f"Не удалось открыть окно поиска: {str(e)}", foreground="red")
        
    def set_preview_module(self, preview_module):
        """Устанавливает связь с модулем превью для получения настроек экспорта"""
        self.preview_module = preview_module
        
    def reset_status_messages(self):
        """Сбрасывает статусные сообщения к изначальному состоянию"""
        if self.folder_path.get():
            folder_name = os.path.basename(self.folder_path.get())
            self.parse_status.config(text=f"Папка: {folder_name}", foreground="blue")
        else:
            self.parse_status.config(text="Папка не выбрана", foreground="red")
        
        # Очищаем статус много видов вместо постоянного предупреждения
        self.data_manager_status_label.config(text="", foreground="black")

    def set_roll_module(self, roll_module):
        """Устанавливает связь с модулем ролика"""
        self.roll_module = roll_module
        self.comment_manager.customer_var = self.roll_module.customer_var

    def get_product_name(self):
        """Получает данные продукта из XML файлов с поддержкой поиска по detail_num и номеру тиража"""
        # Показываем статус папки
        if self.folder_path.get():
            folder_name = os.path.basename(self.folder_path.get())
            self.parse_status.config(text=f"Папка: {folder_name}", foreground="blue")
        else:
            self.parse_status.config(text="Папка не выбрана", foreground="red")
            return

        # Сначала очищаем список от предыдущего заказа
        self.parsed_data = []
        self.selected_name.set("")
        self.name_combobox.set('')
        self.name_combobox['values'] = []
        self.roll_module.date_emission_var.set("")      
        
        # Получаем номер заказа из roll_module
        if self.roll_module and hasattr(self.roll_module, 'order_number'):
            order_num = self.roll_module.order_number.get().strip()
                    
        else:
            self.parse_status.config(text="Модуль данных не подключен", foreground="red")
            return
            
        if not order_num:
            self.parse_status.config(text="Введите номер заказа", foreground="red")
            return
            
        if self.current_order is None:
            self.current_order = ""
        
        if order_num != self.current_order:
            # Заказ изменился - сбрасываем поиск вида
            self.detail_num_search.set("")
            self.current_order = order_num

        # Получаем данные продуктов (словари)
        self.parsed_data = self.parse_xml_for_product_names(order_num)
        
        if not self.parsed_data:
            self.parse_status.config(text="Данные не найдены", foreground="red")
            return
        
        # Если найдено больше одного вида - отправляем "Ассортимент" в roll_module
        if len(self.parsed_data) > 1 and self.roll_module:
            # Отправляем "Ассортимент" в поле названия продукции
            self.roll_module.product_text.delete("1.0", tk.END)
            self.roll_module.product_text.insert("1.0", "Ассортимент")
        
        # Ищем конкретный вид или тираж
        search_digits = self.detail_num_search.get().strip()
        
        # проверяем минимальную длину
        if search_digits and len(search_digits) < 3:
            self.parse_status.config(
                text=f"Введите минимум 3 цифры для поиска (введено: {len(search_digits)})", 
                foreground="orange"
            )
            return

        found_products = []
        found_by = ""
        # нужно правильно обработать parsed_data после использования нового парсера
        if search_digits:
            if search_digits:
                
                # Нормализуем поиск (оставляем только цифры)
                search_digits_numeric = re.sub(r'\D', '', search_digits)
                
                for product in self.parsed_data:
                    detail_num = product.get('detail_num', '')
                    sheet_number = product.get('sheet_number', '')  # ← Теперь индивидуальный!
                    
                    # Ищем по detail_num ИЛИ по sheet_number (только цифры)
                    if (search_digits in detail_num or 
                        (search_digits_numeric and search_digits_numeric in sheet_number)):
                        found_products.append(product)
                        if search_digits in detail_num:
                            found_by = f"вид {detail_num}"
                        elif search_digits_numeric in sheet_number:
                            found_by = f"тираж {product.get('sheet_full_name', '')}"
            
            if found_products:
                # Сохраняем отфильтрованные данные
                self.filtered_parsed_data = found_products
                self.parsed_names_list = [item['name'] for item in found_products]
                
                # Всегда заполняем комбобокс
                names_list = [item['name'] for item in found_products]
                self.name_combobox['values'] = names_list

                if len(found_products) == 1:
                    # Если найден один продукт - сразу отправляем
                    selected_data = found_products[0]
                    self.selected_name.set(selected_data['name'])
                    self.send_to_roll_module(selected_data)
                    self.parse_status.config(text=f"Найден {found_by}", foreground="green")
                    self.parent.after(5000, lambda: self.parse_status.config(text=""))
                else:
                    # Если несколько - показываем выбор
                    self.parse_status.config(
                        text=f"Найдено {len(found_products)} вариантов по {found_by}. Всего: {len(names_list)} видов", 
                        foreground="orange"
                    )
                    self.parent.after(5000, lambda: self.parse_status.config(text=""))
    
            else:
                self.parse_status.config(text=f"Код {search_digits} не найден", foreground="red")
                # Показываем все варианты для выбора
                names_list = [item['name'] for item in self.parsed_data]
                self.name_combobox['values'] = names_list
                self.parse_status.config(
                    text=f"Выберите название из списка. Всего: {len(names_list)} видов", 
                    foreground="orange"
                )
                self.parent.after(5000, lambda: self.parse_status.config(text=""))
                self.filtered_parsed_data = self.parsed_data                
        
        else:
            # Если поиск по коду не выполняется
            if len(self.parsed_data) == 1:
                # Если данные одни - сразу отправляем
                selected_data = self.parsed_data[0]
                self.selected_name.set(selected_data['name'])
                self.send_to_roll_module(selected_data)
            else:
                # Если несколько - показываем выбор
                names_list = [item['name'] for item in self.parsed_data]
                self.name_combobox['values'] = names_list
                self.parse_status.config(
                    text=f"Выберите из списка. Всего: {len(names_list)} видов", 
                    foreground="orange"
                )
                self.parent.after(5000, lambda: self.parse_status.config(text=""))
                    
        if self.name_combobox['values']:
            # Откладываем установку фокуса, чтобы UI успел отрендерить комбобокс
            self.parent.after(120, lambda: self.name_combobox.focus_set())
            self.parent.after(140, lambda: self.name_combobox.event_generate('<Down>'))
            
    @staticmethod
    def _add_gtin_suffix(name: str, gtin: str) -> str:
        """
        Добавляет суффикс "джитXXXX" к названию, предварительно очищая его от полного GTIN.      
        
        Args:
            name (str): Оригинальное название продукта
            gtin (str): Полный GTIN (12-14 цифр)
        
        Returns:
            str: Название с суффиксом "джитXXXX" (без дублирования GTIN)
        
        """
        if not name or not gtin:
            return name
        
        # Нормализуем GTIN (оставляем только цифры)
        gtin_digits = re.sub(r'\D', '', gtin)
        
        # Получаем короткий суффикс (последние 4 цифры)
        short_gtin = gtin_digits[-4:] if len(gtin_digits) >= 4 else gtin_digits
        
        # 1. Удаляем ВСЕ варианты полного GTIN из названия
        patterns_to_remove = [
            f"GTIN {gtin}",
            f"GTIN{gtin}",
            gtin,
            f"GTIN {gtin_digits}",
            f"GTIN{gtin_digits}",
            gtin_digits,
            f"({gtin})",
            f"({gtin_digits})"
        ]
        
        for pattern in patterns_to_remove:
            name = name.replace(pattern, '')
        
        # 2. Удаляем лишние пробелы и знаки пунктуации
        name = re.sub(r'\s+', ' ', name).strip()
        name = name.strip(' ,;')
        
        # 3. Проверяем, нет ли уже "джитXXXX" в названии
        # (на случай если суффикс уже был добавлен ранее или есть в оригинале)
        if f"джит{short_gtin}" in name:
            return name
        
        # 4. Добавляем суффикс "джитXXXX"
        return f"{name} джит{short_gtin}"
            
    def parse_xml_for_product_names(self, order_number):
        """Парсит XML файлы для поиска названий продуктов и дополнительных данных"""
        # Используем кэш из roll_module, если данные уже получены
        if (self.cached_order_data is not None and
                self.cached_order_data and
                self.cached_order_number is not None and
                self.cached_order_number == order_number):
            
            results = self.cached_order_data
        else:
            # Иначе получаем данные из DataManager
            results = self.data_manager.search_combined(order_number)
        
        # Проверяем галочку из roll_module
        shorten_enabled = False
        if self.roll_module is not None and hasattr(self.roll_module, 'shorten_text_var'):
            shorten_enabled = self.roll_module.shorten_text_var.get()
        
        product_data = []
        
        for order in results:
            # Преобразуем в старый формат
            for product in order.get('products', []):
                product_name = product.get('product_name', '')
                
                # Сокращаем если включено
                display_name = product_name
                if shorten_enabled and self.name_shortener is not None:
                    display_name = self.name_shortener.shorten_name(product_name)
                
                # Добавляем джит если есть
                gtin = product.get('gtin', '')
                if gtin:
                    display_name = self._add_gtin_suffix(display_name, gtin)
                
                product_dict = {
                    'name': display_name,  # ← Сокращенное или оригинальное имя
                    'detail_num': product.get('detail_number', ''),
                    'sheet_number': product.get('sheet_number', ''),
                    'sheet_full_name': product.get('sheet_full_name', ''),
                    'customer': order.get('customer', ''),
                    'winding_scheme': order.get('operations', {}).get('winding_scheme', ''),
                    'sleeve_diameter': order.get('operations', {}).get('sleeve_diameter', ''),
                    'date_emission': product.get('date_emission', ''),
                    'gtin': gtin,
                    'tirazh': product.get('quantity', ''),
                    'stream': product.get('stream', '1')                   
                }
                
                if not any(item['name'] == product_dict['name'] and 
                          item['detail_num'] == product_dict['detail_num'] 
                          for item in product_data):
                    product_data.append(product_dict)
        
        return product_data

    # noinspection PyUnusedLocal
    def on_name_selected(self, event):
        """Обрабатывает выбор названия из комбобокса и отправляет все данные"""
        selected_name = self.selected_name.get()
        if selected_name and self.parsed_data and self.roll_module:
            # Находим полные данные по выбранному названию
            selected_data = None
            for item in self.parsed_data:
                if item['name'] == selected_name:
                    selected_data = item
                    break
            
            if selected_data:
                self.filtered_parsed_data = [selected_data]
                self.send_to_roll_module(selected_data)
            else:
                self.parse_status.config(text="Ошибка: данные не найдены", foreground="red")

    def send_to_roll_module(self, product_data):
        """Отправляет все данные продукта в модуль ролика"""
        if self.roll_module:
            try:
                # Заполняем название продукции (основное поле)
                self.roll_module.product_text.delete("1.0", tk.END)

                product_name = product_data.get('name', '')
                detail_number = product_data.get('detail_num', '')
                customer = product_data.get('customer', '')

                # Для заказчика Прогресс АО добавляем detail_number полностью
                if customer == "ПРОГРЕСС АО" and detail_number:
                    display_text = f"{detail_number}, {product_name}"
                else:
                    display_text = product_name

                self.roll_module.product_text.insert("1.0", display_text)
                
                # устанавливаем дату эмиссии если она есть в данных
                if 'date_emission' in product_data and product_data['date_emission']:
                    self.roll_module.date_emission_var.set(product_data['date_emission'])
                    
                # Отправляем тираж в preview_module
                tirazh_value = product_data.get('tirazh')
                formatted_tirazh = f"{int(tirazh_value):,}".replace(",", " ")
                
                # Расчёт вместимости коробки
                capacity_info = ""
                capacity = self._calculate_box_capacity()
                if capacity:
                    capacity_info = f" | Влезет в коробку: {capacity}"
                
                self.preview_module.tirazh_label.config(
                    text=f"Тираж: {formatted_tirazh} шт{capacity_info}",
                    foreground="green"
                )
                
                # Передаём GTIN в preview_module для QR-кода
                if self.preview_module is not None:
                    gtin = product_data.get('gtin', '')
                    self.preview_module.set_product_gtin(gtin)
                
                # Сбрасываем статусные сообщения
                self.reset_status_messages()
                
            except Exception as e:
                print(f"Ошибка отправки данных в модуль ролика: {e}")
                    
    def _calculate_box_capacity(self):
        """Рассчитывает, сколько роликов влезет в выбранную коробку"""
        if self.roll_module is None:
            return None
        
        try:
            # Получаем настройки с высотами коробок
            settings = self.config_manager.load_json_settings("shared_utils.json")
            box_heights = settings.get("box_heights", {})
            
            if not box_heights:
                return None
            
            # Получаем ширину ручья из roll_module
            stream_width_str = self.roll_module.stream_width_var.get().strip()
            if not stream_width_str:
                return None
            
            stream_width_mm = float(stream_width_str)
            
            # Получаем выбранную коробку (из roll_module или текущую)
            if hasattr(self.roll_module, 'box_size_var'):
                box_size = self.roll_module.box_size_var.get()
            else:
                return None
            
            if not box_size or box_size not in box_heights:
                return None
            
            box_height_mm = float(box_heights[box_size])
            
            if stream_width_mm <= 0 or box_height_mm <= 0:
                return None
            
            # Рассчитываем сколько роликов поместится по высоте
            rolls_per_height = int(box_height_mm // stream_width_mm)
            
            return rolls_per_height if rolls_per_height > 0 else None
            
        except (ValueError, TypeError) as e:
            print(f"Ошибка расчета вместимости: {e}")
            return None
        
    def load_excel_folder_path(self):
        """Загружает путь к папке с Excel файлом из настроек"""
        try:
            settings = self.config_manager.load_json_settings("shared_utils.json")
            folder_path = settings.get("weight_orders_xlsx", "")
            
            if folder_path and os.path.exists(folder_path):
                self.excel_folder_path = folder_path
                # Формируем полный путь к файлу
                self.excel_file_path = os.path.join(folder_path, "weight_orders.xlsx")
            else:
                self.excel_folder_path = ""
                self.excel_file_path = ""
                
        except Exception as e:
            print(f"Ошибка загрузки пути к папке Excel: {e}")
            self.excel_folder_path = ""
            self.excel_file_path = ""
