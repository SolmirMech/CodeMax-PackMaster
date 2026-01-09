import tkinter as tk
from tkinter import ttk, StringVar, BooleanVar, filedialog, messagebox
import os
import re
import sys
import shutil
import xml.etree.ElementTree as ET
from core.config_manager import ConfigManager
from core.excel_exporter.excel_exporter import WeightOrdersExporter
from apps.preview.excel_preview_module import ExcelPreviewModule
from core.parse.xml_order_parser import XMLOrderParser

class OrderDataProcessor:
    """Модуль обработки данных заказов (правая часть интерфейса)."""
    
    def __init__(self, parent, coordinator=None):
        self.parent = parent
        self.config_manager = ConfigManager()
        self.coordinator = coordinator
        self.xml_parser = XMLOrderParser()
        
        # Переменные для парсинга
        self.folder_path = StringVar(value="")
        self.parsed_data = []  # Список данных
        self.parsed_names_list = []
        self.selected_name = StringVar(value="")  # Выбранное название
        
        # Переменные для Excel
        self.excel_file_path = None
        self.excel_folder_path = ""
        
        # Ссылки на другие модули
        self.roll_module = None
        self.preview_module = None
        self.excel_preview_module = ExcelPreviewModule(self.parent, self.coordinator)
        
        self.load_initial_settings()
        self.detail_num_search = StringVar(value="")
        self.create_ui()
        if self.coordinator and hasattr(self.coordinator, 'subscribe'):
            self.coordinator.subscribe(self.on_settings_changed)
            
    def on_settings_changed(self):
        """Обработчик изменений настроек от координатора"""
        
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
        main_container = ttk.Frame(self.parent)
        main_container.pack(fill=tk.BOTH, expand=True, side=tk.RIGHT)

        # Верхняя часть: Парсинг XML
        xml_frame = ttk.LabelFrame(main_container, text="Получение названия из xml", padding=5)
        xml_frame.pack(fill=tk.BOTH, expand=False, pady=(0, 10))
        
        ttk.Label(xml_frame, text="Поиск вида:").grid(
            row=0, column=0, sticky="w", pady=5
        )
        
        detail_num_entry = ttk.Entry(xml_frame, textvariable=self.detail_num_search, width=10)
        detail_num_entry.grid(row=0, column=0, padx=(130, 0), pady=5, sticky="w")
        detail_num_entry.bind("<Return>", lambda e: self.get_product_name())
        
        # Кнопка поиска архива
        archive_frame = ttk.Frame(xml_frame)
        archive_frame.grid(row=0, column=1, sticky="w", pady=5)

        ttk.Button(
            archive_frame, 
            text="🔍 Найти архив", 
            command=self.open_archive_search_window
        ).pack(side=tk.LEFT, padx=10)

        # Строка статуса парсинга
        self.parse_status = ttk.Label(xml_frame, text="", foreground="black", font=("Arial", 14))
        self.parse_status.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 15))

        # Выбор названия
        ttk.Label(xml_frame, text="Выберите название:").grid(row=2, column=0, columnspan=2, sticky="w", pady=(0, 5))
        self.name_combobox = ttk.Combobox(xml_frame, textvariable=self.selected_name, state="readonly", width=61)
        self.name_combobox.grid(row=3, column=0, sticky="w", pady=(0, 10))
        self.name_combobox.bind("<<ComboboxSelected>>", self.on_name_selected)

        # Отправка вида в лист много видов
        multitype_frame = ttk.Frame(xml_frame)
        multitype_frame.grid(row=4, column=0, columnspan=2, sticky="w", pady=(10, 5))
        
        ttk.Button(multitype_frame, text="🎯 Отправить вид в Лист 'Много видов'", 
                  command=self.export_current_type_to_excel
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        # Меню для очистки много видов
        multitype_menu = ttk.Menubutton(multitype_frame, text="🧹", width=3)
        multitype_menu.pack(side=tk.LEFT)
        
        multitype_menu.menu = tk.Menu(multitype_menu, tearoff=0)
        multitype_menu["menu"] = multitype_menu.menu
        multitype_menu.menu.add_command(
            label="Очистить Лист 'Много видов'", 
            command=self.clear_multitype_sheet
        )
        
        preview_frame = ttk.Frame(xml_frame)
        preview_frame.grid(row=5, column=0, sticky="w", pady=(5, 5))

        # Кнопка предпросмотра листа 'Много видов'
        ttk.Button(
            preview_frame,
            text="👀 Просмотр",
            command=self.show_multitype_preview,
            width=15
        ).pack(side=tk.LEFT)        

        # Строка статуса для много видов
        self.multitype_status_label = tk.Label(
            xml_frame, 
            text="Внимание, закройте файл Excel перед экспортом!", 
            foreground="red",
            font=("Arial", 14),
            wraplength=500,
            justify=tk.CENTER,
            height=3
        )
        self.multitype_status_label.grid(row=6, column=0, columnspan=2, sticky="w")

        xml_frame.columnconfigure(0, weight=1)
        xml_frame.columnconfigure(1, weight=1)
        
        # Инициализируем статусы
        self.reset_status_messages()
        
    def show_multitype_preview(self):
        """Открывает предпросмотр для листа 'Много видов'"""
        # Определяем текущий цех
        workshop = "1"
        if self.coordinator and hasattr(self.coordinator, 'get_workshop'):
            workshop = self.coordinator.get_workshop()
        
        # Устанавливаем контекст многовидового режима
        self.excel_preview_module.sheet_name = self.excel_preview_module._get_sheet_for_preview(
            workshop, enable_pallet=False, multitype_mode=True
        )
        
        # Открываем окно предпросмотра
        self.excel_preview_module.show_preview_window()
        
    def open_archive_search_window(self):
        """Открывает окно поиска архивных поддонов"""
        try:
            from core.archive.archive_search_window import ArchiveSearchWindow
            ArchiveSearchWindow(self.parent, self)
        except Exception as e:
            self.multitype_status_label.config(text="Не удалось открыть окно поиска: {str(e)}", foreground="red")
        
    def set_preview_module(self, preview_module):
        """Устанавливает связь с модулем превью для получения настроек экспорта"""
        self.preview_module = preview_module
        
    def get_pallet_data(self):
        """Получает данные паллеты из модуля предпросмотра"""
        if hasattr(self, 'export_module') and self.export_module:
            return {
                "pallet_type": getattr(self.export_module, 'pallet_size_var', StringVar()).get(),
                "boxes_count": getattr(self.export_module, 'boxes_count_var', StringVar()).get(),
                "pallet_weight": getattr(self.export_module, 'pallet_weight_var', StringVar()).get()
            }
        return {"pallet_type": "", "boxes_count": "", "pallet_weight": ""}
        
    def auto_clear_excel_data(self):
        """Автоматически очищает данные Excel при смене вида продукции"""
        try:
            if not self.excel_file_path:
                self.load_excel_folder_path()
                
            if self.excel_file_path and os.path.exists(self.excel_file_path):
                # Очищаем оба листа: коробку и поддон
                exporter = WeightOrdersExporter.create_exporter(
                    excel_file_path=self.excel_file_path,
                    roll_module=self.roll_module,
                    preview_module=self.preview_module
                )
                
                # Очищаем коробку
                box_cleared = exporter.clear_all_rolls()  
                # Очищаем поддон  
                pallet_cleared = exporter.clear_all_rolls(enable_pallet=True)
                
                # Показываем статус в UI
                if box_cleared and pallet_cleared:                    
                    self.multitype_status_label.config(
                        text="Данные очищены при смене вида", 
                        foreground="green"
                    )
                else:
                    self.multitype_status_label.config(
                        text="Ошибка очистки (файл открыт?)", 
                        foreground="orange"
                    )
                
        except Exception as e:
            print(f"Ошибка автоматической очистки Excel: {e}")
        
    def clear_multitype_sheet(self):
        """Очищает лист 'Много видов' в Excel"""
        try:
            # Используем excel_file_path
            if not self.excel_file_path:
                self.load_excel_folder_path()
                
            if not self.excel_file_path:
                self.multitype_status_label.config(
                    text="Папка для Excel не выбрана", 
                    foreground="red"
                )
                return

            if not os.path.exists(self.excel_file_path):
                self.multitype_status_label.config(
                    text="Файл Excel не существует", 
                    foreground="red"
                )
                return

            # Создаем экспортер и выполняем очистку
            exporter = WeightOrdersExporter.create_exporter(
                excel_file_path=self.excel_file_path,
                roll_module=self.roll_module,
                preview_module=self.preview_module,
                coordinator=self.coordinator
            )
            
            success = exporter.clear_all_rolls(multitype_mode=True)
            
            if success:
                self.multitype_status_label.config(
                    text="Лист 'Много видов' очищен", 
                    foreground="green"
                )
            else:
                self.multitype_status_label.config(
                    text="Ошибка при очистке листа", 
                    foreground="red"
                )
            
        except Exception as e:
            self.multitype_status_label.config(
                text=f"Ошибка очистки: {str(e)}", 
                foreground="red"
            )
        
    def export_current_type_to_excel(self):
        """Экспортирует текущий вид продукции в лист много видов"""
        try:
            self.multitype_status_label.config(text="", foreground="black")
            # Получаем данные паллеты из модуля предпросмотра
            pallet_data = self.get_pallet_data()
            
            # Проверяем, что все необходимые данные заполнены
            if not pallet_data["pallet_type"] or not pallet_data["boxes_count"]:
                self.multitype_status_label.config(
                    text="Введите данные для экспорта!", 
                    foreground="orange"
                )
                return

            # Получаем название продукции - сначала из выбранного XML, если нет - из поля ролика
            product_name = ""
            if self.selected_name.get():
                product_name = self.selected_name.get()
            elif self.roll_module:
                # Берем название из поля изделия ролика
                product_name = self.roll_module.product_text.get("1.0", "end-1c").strip()
            
            if not product_name:
                self.multitype_status_label.config(
                    text="Сначала выберите или введите название продукции", 
                    foreground="orange"
                )
                return
                
            # Формируем данные для экспорта   
            pallet_data = {
                "pallet_type": pallet_data["pallet_type"],
                "pallet_weight": pallet_data["pallet_weight"],
                "boxes_count": pallet_data["boxes_count"],
                "product_name": product_name
            }

            # Используем excel_file_path
            if not self.excel_file_path:
                self.load_excel_folder_path()
                
            if not self.excel_file_path:
                self.multitype_status_label.config(
                    text="Папка для Excel не выбрана", 
                    foreground="red"
                )
                return

            if not os.path.exists(self.excel_file_path):
                self.multitype_status_label.config(
                    text="Файл Excel не существует", 
                    foreground="red"
                )
                return

            # Создаем экспортер и выполняем экспорт в много-видовой лист
            exporter = WeightOrdersExporter.create_exporter(
                excel_file_path=self.excel_file_path,
                roll_module=self.roll_module,
                preview_module=self.preview_module,
                coordinator=self.coordinator
            )
            
            result = exporter.export_data(multitype_mode=True, pallet_data=pallet_data)
            
            if result['success']:
                self.multitype_status_label.config(
                    text="✅ Вид отправлен в лист 'Много видов'", 
                    foreground="green"
                )
                # Очищаем статус
                self.parent.after(9000, lambda: self.multitype_status_label.config(text=""))
            else:
                # Обработка ошибок из экспортера
                error_msg = result.get('error', '')
                self._handle_export_error(error_msg)
                    
        except Exception as e:
            # Обработка исключений при экспорте
            self._handle_export_error(str(e))
            
    def _handle_export_error(self, error_msg):
        """Обрабатывает ошибки экспорта"""
        # Проверяем разные варианты ошибок открытого файла
        if any(word in error_msg.lower() for word in ['permission', 'доступ', 'открыт', 'open', 'denied']):
            self.multitype_status_label.config(
                text="Внимание, закройте файл Excel перед экспортом!", 
                foreground="red"
            )
        else:
            self.multitype_status_label.config(
                text=f"❌ Ошибка: {error_msg}", 
                foreground="red"
            )
        
    def reset_status_messages(self):
        """Сбрасывает статусные сообщения к изначальному состоянию"""
        if self.folder_path.get():
            folder_name = os.path.basename(self.folder_path.get())
            self.parse_status.config(text=f"Папка: {folder_name}", foreground="blue")
        else:
            self.parse_status.config(text="Папка не выбрана", foreground="red")
        
        # Очищаем статус много видов вместо постоянного предупреждения
        self.multitype_status_label.config(text="", foreground="black")

    def set_roll_module(self, roll_module):
        """Устанавливает связь с модулем ролика"""
        self.roll_module = roll_module       
        
    def parse_xml_for_product_names(self, order_number):
        """Парсит XML файлы для поиска названий продуктов и дополнительных данных"""
        if not self.folder_path.get():
            return []

        folder = self.folder_path.get()
        if not os.path.exists(folder):
            return []

        product_data = []
        
        for filename in os.listdir(folder):
            if not filename.endswith('.xml'):
                continue
                
            file_path = os.path.join(folder, filename)
            try:
                with open(file_path, 'rb') as f:
                    raw_data = f.read()
                
                # Используем общий метод декодирования
                content = self._decode_xml_content(raw_data)
                
                # Ищем номер заказа в XML
                match = re.search(r'<НомерЗаказа>(.*?)</НомерЗаказа>', content)
                if not match:
                    continue
                    
                xml_order_number = match.group(1).strip()
                
                # Извлекаем цифры из номера
                digits_match = re.search(r'(\d+)', xml_order_number)
                if not digits_match:
                    continue
                    
                xml_digits = digits_match.group(1)
                
                # Строгое сравнение как в auto_fill_from_xml
                if xml_digits != order_number:
                    continue  # Пропускаем файлы с другими номерами
                
                # Только если номер совпал - парсим файл
                parsed_result = self.xml_parser.parse(content)
                
                # Преобразуем в старый формат
                for product in parsed_result.get('products', []):
                    sheet_name = product.get('sheet_name', '')
                    sheet_number = ""
                    if sheet_name:
                        match = re.search(r'[A-Za-zА-Яа-я]-?(\d+)', sheet_name)
                        if match:
                            sheet_number = match.group(1)
                    
                    product_dict = {
                        'name': product.get('full_name', product.get('product_name', '')),
                        'detail_num': product.get('detail_number', ''),
                        'sheet_number': product.get('sheet_number', ''),
                        'customer': parsed_result.get('customer', ''),
                        'winding_scheme': parsed_result.get('operations', {}).get('winding_scheme', ''),
                        'sleeve_diameter': parsed_result.get('operations', {}).get('sleeve_diameter', ''),
                        'date_emission': product.get('date_emission', ''),
                        'manufacturer': "",
                        'gtin': product.get('gtin', ''),
                        'tirazh': product.get('quantity', ''),
                        'stream': product.get('stream', '1')
                    }
                    
                    if not any(item['name'] == product_dict['name'] and 
                              item['detail_num'] == product_dict['detail_num'] 
                              for item in product_data):
                        product_data.append(product_dict)
                        
            except Exception as e:
                print(f"Ошибка парсинга файла {filename}: {e}")
                continue

        return product_data
        
    def _decode_xml_content(self, raw_data):
        """Декодирует XML контент с учетом кодировки."""
        if raw_data.startswith(b'\xff\xfe'):  # UTF-16 LE
            return raw_data.decode('utf-16')
        elif raw_data.startswith(b'\xfe\xff'):  # UTF-16 BE
            return raw_data.decode('utf-16')
        else:
            try:
                return raw_data.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    import chardet
                    encoding = chardet.detect(raw_data)['encoding'] or 'utf-8'
                    return raw_data.decode(encoding)
                except:
                    return raw_data.decode('utf-8', errors='ignore')

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
        
        if self.roll_module and hasattr(self.roll_module, 'date_emission_var'):
            self.roll_module.date_emission_var.set("")
        
        # Получаем номер заказа из roll_module
        order_num = ""
        if self.roll_module and hasattr(self.roll_module, 'order_number'):
            order_num = self.roll_module.order_number.get().strip()
                    
        else:
            self.parse_status.config(text="Модуль данных не подключен", foreground="red")
            return
            
        if not order_num:
            self.parse_status.config(text="Введите номер заказа", foreground="red")
            return
            
        if not hasattr(self, 'current_order'):
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
            self.parse_status.config(text="Найдено несколько видов. Установлено 'Ассортимент'", foreground="green")
        
        # Ищем конкретный вид или тираж
        search_digits = self.detail_num_search.get().strip()
        search_digits_numeric = re.sub(r'\D', '', search_digits)  # Убираем всё, кроме цифр
        
        # проверяем минимальную длину
        if search_digits and len(search_digits) < 3:
            self.parse_status.config(
                text=f"Введите минимум 3 цифры для поиска (введено: {len(search_digits)})", 
                foreground="red"
            )
            return
        
        # нужно правильно обработать parsed_data после использования нового парсера
        if search_digits:
            if search_digits:
                found_products = []
                found_by = ""
                
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
                            found_by = f"тираж I-{sheet_number}"
            
            if found_products:
                # Сохраняем отфильтрованные данные
                self.filtered_parsed_data = found_products
                self.parsed_names_list = [item['name'] for item in found_products]
                
                if len(found_products) == 1:
                    # Если найден один продукт - сразу отправляем
                    selected_data = found_products[0]
                    self.selected_name.set(selected_data['name'])
                    self.send_to_roll_module(selected_data)
                    self.parse_status.config(text=f"Найден {found_by}", foreground="green")
                else:
                    # Если несколько - показываем выбор
                    names_list = [item['name'] for item in found_products]
                    self.name_combobox['values'] = names_list
                    self.parse_status.config(
                        text=f"Найдено {len(found_products)} вариантов по {found_by}. Всего: {len(names_list)} видов", 
                        foreground="orange"
                    )
            else:
                self.parse_status.config(text=f"Код {search_digits} не найден", foreground="red")
                # Показываем все варианты для выбора
                names_list = [item['name'] for item in self.parsed_data]
                self.name_combobox['values'] = names_list
                self.parse_status.config(
                    text=f"Выберите название из списка. Всего: {len(names_list)} видов", 
                    foreground="orange"
                )
                self.filtered_parsed_data = self.parsed_data
        
        else:
            # Если поиск по коду не выполняется
            if len(self.parsed_data) == 1:
                # Если данные одни - сразу отправляем
                selected_data = self.parsed_data[0]
                self.selected_name.set(selected_data['name'])
                self.send_to_roll_module(selected_data)
                self.parse_status.config(text="Данные отправлены", foreground="green")
            else:
                # Если несколько - показываем выбор
                names_list = [item['name'] for item in self.parsed_data]
                self.name_combobox['values'] = names_list
                self.parse_status.config(
                    text=f"Выберите название из списка. Всего: {len(names_list)} видов", 
                    foreground="orange"
                )
            
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
                self.send_to_roll_module(selected_data)
                self.parse_status.config(text="Все данные отправлены", foreground="green")
            else:
                self.parse_status.config(text="Ошибка: данные не найдены", foreground="red")

    def send_to_roll_module(self, product_data):
        """Отправляет все данные продукта в модуль ролика"""
        if self.roll_module:
            try:
                # Заполняем название продукции (основное поле)
                self.roll_module.product_text.delete("1.0", tk.END)
                
                # проверяем разные возможные ключи
                product_name = ""
                if 'name' in product_data:
                    product_name = product_data['name']
                elif 'full_name' in product_data:  # Новый формат использует full_name
                    product_name = product_data['full_name']
                elif 'product_name' in product_data:  # Также может быть product_name
                    product_name = product_data['product_name']
                    
                self.roll_module.product_text.insert("1.0", product_name)
                
                # устанавливаем дату эмиссии если она есть в данных
                if 'date_emission' in product_data and product_data['date_emission']:
                    self.roll_module.date_emission_var.set(product_data['date_emission'])
                
                # Автоматически очищаем Excel данные при смене продукции
                self.auto_clear_excel_data()
                
                # Сбрасываем статусные сообщения
                self.reset_status_messages()
                
            except Exception as e:
                print(f"Ошибка отправки данных в модуль ролика: {e}")
                # В случае ошибки пытаемся отправить хотя бы название
                try:
                    self.roll_module.product_text.delete("1.0", tk.END)
                    # Также пытаемся найти название в разных ключах
                    name_to_send = product_data.get('name', 
                                                  product_data.get('full_name', 
                                                                  product_data.get('product_name', '')))
                    self.roll_module.product_text.insert("1.0", name_to_send)
                    print(f"Отправлено только название: {name_to_send}")
                except:
                    print("Критическая ошибка при отправке данных")
        
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
