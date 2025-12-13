# apps/preview/excel_preview_module.py
import tkinter as tk
from tkinter import ttk
import os
from PIL import Image, ImageDraw
from core.config_manager import ConfigManager

class ExcelPreviewModule:
    """Модуль предпросмотра Excel файла"""
    
    def __init__(self, parent, coordinator=None):
        self.parent = parent
        self.coordinator = coordinator
        self.config_manager = ConfigManager()
        
        # Переменные
        self.excel_path = None
        self.sheet_name = None  # Будет установлено динамически
        
        # GUI элементы
        self.preview_canvas = None
        self.scrollbar = None
        self.preview_window = None
        
        # Переменные для печати
        self.printer1_var = tk.StringVar()
        self.printer2_var = tk.StringVar()
        self.copies_var = tk.IntVar(value=1)
        self.print_status_var = tk.StringVar(value="")
        
        # Подписка на координатор
        if coordinator and hasattr(coordinator, 'subscribe'):
            coordinator.subscribe(self.on_excel_exported)
            
    def _get_sheet_for_preview(self, workshop, enable_pallet=False, multitype_mode=False):
        """Определяет лист для предпросмотра на основе контекста"""
        if workshop == "1":
            if multitype_mode:
                return "Лист много видов"
            elif enable_pallet:
                return "Лист для паллеты"
            else:
                return "Лист для коробки"
        else:  # workshop == "2"
            if multitype_mode:
                return "Много видов"
            elif enable_pallet:
                return "Список поддонов"
            else:
                return "Поддон"
            
    def _get_system_printers(self):
        """Получает список системных принтеров"""
        try:
            import win32print
            printers = win32print.EnumPrinters(2)
            return [p[2] for p in printers]
        except Exception as e:
            print(f"Ошибка получения принтеров: {e}")
            return []
    
    def _get_excel_path(self):
        """Получает путь к Excel файлу из настроек с учетом цеха"""
        try:
            settings = self.config_manager.load_json_settings("shared_utils.json")
            excel_folder = settings.get("weight_orders_xlsx", "")
            
            if not excel_folder:
                return None
            
            # Определяем цех
            workshop = "1"
            if hasattr(self, 'coordinator') and self.coordinator:
                workshop = self.coordinator.get_workshop()
            
            # Выбираем файл в зависимости от цеха
            filename = "weight_orders.xlsx" if workshop == "1" else "weight_orders_2.xlsx"
            full_path = os.path.join(excel_folder, filename)
            
            return full_path
            
        except Exception as e:
            print(f"Ошибка получения пути к Excel файлу: {e}")
            return None
            
    def reload_window(self):
        """Перезагружает окно предпросмотра"""
        if (hasattr(self, 'preview_window') and 
            self.preview_window is not None and 
            self.preview_window.winfo_exists()):
            
            self.preview_window.destroy()
            self.show_preview_window()
    
    def on_excel_exported(self, event_type=None, data=None):
        """Обработчик событий от координатора для всех режимов"""
        if event_type == "excel_exported":
            # Получаем параметры из данных события
            workshop = data.get('workshop', '1')
            enable_pallet = data.get('enable_pallet', False)
            multitype_mode = data.get('multitype_mode', False)
            
            # Определяем лист
            self.sheet_name = self._get_sheet_for_preview(
                workshop, enable_pallet, multitype_mode
            )
            
            # Обновляем заголовок окна если оно открыто
            if (hasattr(self, 'preview_window') and 
                self.preview_window is not None and 
                self.preview_window.winfo_exists()):
                
                self.preview_window.title(f"Предпросмотр Excel - {self.sheet_name}")
                self.update_preview()
        
        elif event_type == "excel_cleared":
            # Тоже обновляем для события очистки
            workshop = data.get('workshop', '1')
            enable_pallet = data.get('enable_pallet', False)
            multitype_mode = data.get('multitype_mode', False)
            
            self.sheet_name = self._get_sheet_for_preview(
                workshop, enable_pallet, multitype_mode
            )
            
            if (hasattr(self, 'preview_window') and 
                self.preview_window is not None and 
                self.preview_window.winfo_exists()):
                
                self.preview_window.title(f"Предпросмотр Excel - {self.sheet_name}")
                self.update_preview()

    def excel_to_image_simple(self, excel_path, sheet_name):
        """Скриншот области печати Excel"""
        try:
            import win32com.client
            import pythoncom
            from PIL import ImageGrab
            import time
            import win32gui
            
            pythoncom.CoInitialize()
            
            # 1. Открываем Excel видимым
            excel = win32com.client.DispatchEx("Excel.Application")
            excel.Visible = True
            excel.DisplayAlerts = False
            
            wb = excel.Workbooks.Open(excel_path)
            
            try:
                ws = wb.Sheets(sheet_name)
            except:
                ws = wb.Sheets(1)
            
            ws.Activate()         
            
            # 2. Используем заданную область печати
            print_area = ws.Range(ws.PageSetup.PrintArea)
            
            # Прокручиваем к началу области
            excel.ActiveWindow.ScrollRow = print_area.Row
            excel.ActiveWindow.ScrollColumn = print_area.Column
            
            # Выделяем область
            print_area.Select()
            
            excel.ActiveWindow.Zoom = 90
            
            # 3. Минимальное время для отрисовки
            time.sleep(0.3)  # Только 300 мс!
            
            # 4. Свернуть окно excel сразу после настройки
            excel.WindowState = -4140  # xlMinimized
            
            # 5. Получаем HWND свернутого окна
            excel_hwnd = None
            excel_windows = []
            
            def find_excel_window(hwnd, results):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if title and ('Excel' in title or '.xlsx' in title):
                        results.append(hwnd)
                return True
            
            # Даем время на сворачивание
            time.sleep(0.2)
            win32gui.EnumWindows(find_excel_window, excel_windows)
            
            if excel_windows:
                excel_hwnd = excel_windows[0]
                
                # 6. Восстанавливаем окно на мгновение
                # Сохраняем текущее положение
                rect = win32gui.GetWindowRect(excel_hwnd)
                # Восстанавливаем
                excel.WindowState = -4137  # xlNormal
                
                # 7. Быстрый скриншот
                time.sleep(0.2)  # Минимум для отрисовки
                
                # Пересчитываем координаты
                screen_rect = win32gui.GetWindowRect(excel_hwnd)
                client_rect = win32gui.GetClientRect(excel_hwnd)
                
                # Рассчитываем ширину рамок окна
                frame_width = (screen_rect[2] - screen_rect[0] - client_rect[2]) // 2
                
                # Рассчитываем высоту заголовка и ленты Excel
                title_height = (screen_rect[3] - screen_rect[1] - client_rect[3]) - frame_width               
                
                # Получаем настраиваемый отступ из shared_utils
                settings = self.config_manager.load_json_settings("shared_utils.json")
                preview_settings = settings.get("preview_settings", {})
                top_offset = preview_settings.get("top_offset", 160)
                
                # Делаем скриншот области таблицы
                table_top = screen_rect[1] + title_height + top_offset
                table_bottom = table_top + 870
                table_left = screen_rect[0] + frame_width + 20
                table_right = table_left + 565

                screenshot = ImageGrab.grab(bbox=(
                    table_left,
                    table_top,
                    table_right,
                    table_bottom
                ))
                
                # 8. Сразу же снова сворачиваем
                excel.WindowState = -4140
                
            else:
                # Fallback: если не нашли окно
                wb.Close(SaveChanges=False)
                excel.Quit()
                pythoncom.CoUninitialize()
                return None
            
            # 9. Закрываем Excel
            wb.Close(SaveChanges=False)
            excel.Quit()
            pythoncom.CoUninitialize()

            return screenshot
                
        except Exception as e:
            print(f"Ошибка скриншота: {e}")
            import traceback
            traceback.print_exc()
            
            try:
                excel.Quit()
            except:
                pass
            
            try:
                pythoncom.CoUninitialize()
            except:
                pass
                
            return None
            
    def _save_preview_settings(self):
        """Сохраняет настройки предпросмотра в shared_utils.json"""
        try:
            # Загружаем текущие настройки shared_utils
            settings = self.config_manager.load_json_settings("shared_utils.json")
            
            # Создаем или обновляем секцию preview_settings
            if "preview_settings" not in settings:
                settings["preview_settings"] = {}
            
            # Сохраняем отступ
            settings["preview_settings"]["top_offset"] = self.top_offset_var.get()
            
            # Сохраняем обратно в shared_utils
            success = self.config_manager.save_json_settings("shared_utils.json", settings)
            
            if success:
                self.status_label.config(
                    text="✓ Отступ сохранен", 
                    foreground="green"
                )
                # Возвращаем исходный статус через 2 секунды
                self.preview_window.after(2000, self._restore_status)
            else:
                self.status_label.config(
                    text="✗ Ошибка сохранения", 
                    foreground="red"
                )
                        
        except Exception as e:
            print(f"Ошибка сохранения настроек предпросмотра: {e}")
            self.status_label.config(
                text=f"✗ Ошибка: {str(e)[:30]}", 
                foreground="red"
            )
        
    def display_preview(self, image):
        """Отображает PIL Image с качественным увеличением"""
        if not self.preview_canvas:
            return
        
        try:
            from PIL import ImageTk
              
            # Удаляем старое изображение
            self.preview_canvas.delete("all")
            
            self.tk_image = ImageTk.PhotoImage(image)
            
            self.preview_canvas.create_image(10, 10, anchor='nw', image=self.tk_image)
            
            self.preview_canvas.config(
                scrollregion=(0, 0, image.width + 20, image.height + 20)
            )
            
        except Exception as e:
            print(f"Ошибка отображения: {e}")
    
    def show_error_preview(self, error_msg):
        """Показывает сообщение об ошибке"""
        if self.preview_canvas:
            self.preview_canvas.delete("all")
            self.preview_canvas.create_text(
                150, 100, 
                text=f"Ошибка загрузки:\n{error_msg}",
                fill='red',
                font=('Arial', 10)
            )

    def show_preview_window(self):
        """Открывает окно предпросмотра"""
        # Если окно уже открыто - поднимаем его
        if (hasattr(self, 'preview_window') and 
            self.preview_window is not None and 
            self.preview_window.winfo_exists()):
            
            self.preview_window.lift()
            self.preview_window.focus_force()
            self.update_preview()  # Обновляем данные
            return
        
        # Определяем текущий цех
        workshop = "1"
        if self.coordinator and hasattr(self.coordinator, 'get_workshop'):
            workshop = self.coordinator.get_workshop()      
        
        # Если sheet_name еще не установлен (например, при прямом вызове из UI)
        if self.sheet_name is None:
            # ТОЛЬКО тогда используем лист для коробки как fallback
            self.sheet_name = self._get_sheet_for_preview(workshop, enable_pallet=False, multitype_mode=False)
        # Иначе используем уже установленный sheet_name (из show_pallet_preview())
        
        # Создаем новое окно предпросмотра
        self.preview_window = tk.Toplevel(self.parent)
        self.preview_window.title(f"Предпросмотр Excel - {self.sheet_name}")
        
        # ======== Размеры ========
        window_width = 800
        window_height = 900
        
        # Центрирование окна на экране
        screen_width = self.preview_window.winfo_screenwidth()
        screen_height = self.preview_window.winfo_screenheight()
        center_x = int((screen_width - window_width) / 2)
        center_y = int((screen_height - window_height) / 2)
        
        self.preview_window.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
        self.preview_window.minsize(600, 400)  # Минимальный размер
        
        # Фрейм с прокруткой
        main_frame = ttk.Frame(self.preview_window, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Canvas для предпросмотра с прокруткой
        canvas_container = ttk.Frame(main_frame)
        canvas_container.pack(fill=tk.BOTH, expand=True)
        
        # Canvas
        self.preview_canvas = tk.Canvas(canvas_container, bg='white', highlightthickness=1, highlightbackground='#ccc')
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(canvas_container, orient='vertical', command=self.preview_canvas.yview)
        h_scrollbar = ttk.Scrollbar(canvas_container, orient='horizontal', command=self.preview_canvas.xview)
        
        self.preview_canvas.configure(
            yscrollcommand=v_scrollbar.set,
            xscrollcommand=h_scrollbar.set
        )
        
        # Grid layout для canvas и скроллбаров
        self.preview_canvas.grid(row=0, column=0, sticky='nsew')
        v_scrollbar.grid(row=0, column=1, sticky='ns')
        h_scrollbar.grid(row=1, column=0, sticky='ew')
        
        canvas_container.grid_rowconfigure(0, weight=1)
        canvas_container.grid_columnconfigure(0, weight=1)
        
        # Панель управления
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Загружаем сохраненные настройки принтеров
        saved_printers = self.config_manager.get_preview_printers()
        self.printer1_var.set(saved_printers.get("printer1", ""))
        self.printer2_var.set(saved_printers.get("printer2", ""))
        
        # Получаем список системных принтеров
        system_printers = self._get_system_printers()
        
        # Кнопка обновления
        btn_refresh = ttk.Button(
            control_frame,
            text="🔄 Обновить",
            command=lambda: [self.preview_window.destroy(), self.show_preview_window()],
            width=12
        )
        btn_refresh.grid(row=0, column=0, padx=(0, 10), sticky='w')
        
        # Кнопка печати
        btn_print = ttk.Button(
            control_frame,
            text="🖨️ Печать",
            command=self._on_print_clicked,
            width=12
        )
        btn_print.grid(row=0, column=1, padx=(0, 10), sticky='w')
        
        # Получаем список системных принтеров + опция "Без принтера"
        system_printers = self._get_system_printers()
        printer_values = [""] + system_printers        
        
        # Принтер 1
        printer1_combo = ttk.Combobox(
            control_frame,
            textvariable=self.printer1_var,
            values=printer_values,
            width=25,
            state='readonly'
        )
        printer1_combo.grid(row=1, column=0, padx=(0, 10), sticky='w')
        printer1_combo.bind('<<ComboboxSelected>>', lambda e: self._save_printer_settings())
        
        # Принтер 2
        printer2_combo = ttk.Combobox(
            control_frame,
            textvariable=self.printer2_var,
            values=printer_values,
            width=25,
            state='readonly'
        )
        printer2_combo.grid(row=1, column=1, padx=(0, 10), sticky='w')
        printer2_combo.bind('<<ComboboxSelected>>', lambda e: self._save_printer_settings())
        
        # Количество копий
        ttk.Label(control_frame, text="Копий:").grid(row=0, column=2, padx=(0, 5), sticky='w')
        copies_spinbox = ttk.Spinbox(
            control_frame,
            from_=1,
            to=10,
            textvariable=self.copies_var,
            width=5
        )
        copies_spinbox.grid(row=0, column=3, padx=(0, 10), sticky='w')
        
        ttk.Label(control_frame, text="Отступ").grid(row=0, column=4, padx=(0, 5), sticky='w')
        # Загружаем сохраненное значение из shared_utils
        settings = self.config_manager.load_json_settings("shared_utils.json")
        preview_settings = settings.get("preview_settings", {})
        default_offset = preview_settings.get("top_offset", 160)
        
        self.top_offset_var = tk.IntVar(value=default_offset)
        
        top_offset_entry = ttk.Entry(
            control_frame,
            textvariable=self.top_offset_var,
            width=5
        )
        top_offset_entry.grid(row=0, column=5, padx=(0, 10), sticky='w')
        
        # Привязываем изменение
        top_offset_entry.bind("<FocusOut>", lambda e: self._save_preview_settings())
        
        btn_archive = ttk.Button(
            control_frame,
            text="⏳ В архив",
            command=self.archive_current_sheet,
            width=10
        )
        btn_archive.grid(row=0, column=6, padx=(10, 10), sticky='w')        
        
        # Метка статуса
        self.status_label = ttk.Label(control_frame, text="", foreground="blue")
        self.status_label.grid(row=1, column=2, padx=(10, 10), sticky='w', columnspan=4)
        
        # Настроить веса колонок для правильного растяжения
        control_frame.columnconfigure(3, weight=1)  # Статус растягивается
        
        # Обработка закрытия окна
        self.preview_window.protocol("WM_DELETE_WINDOW", self.on_close_preview)
        
        # Привязка горячих клавиш
        self.preview_window.bind('<Escape>', lambda e: self.on_close_preview())
        self.preview_window.bind('<Return>', lambda e: self._on_print_clicked())
        self.preview_window.bind('<F5>', lambda e: self.reload_window())
        
        # Загружаем предпросмотр
        self.update_preview()  # Загружаем данные
        self.preview_window.after(100, lambda: [
            self.preview_window.lift(), 
            self.preview_window.focus_force()
        ])
        
    def archive_current_sheet(self):
        """Архивирует текущий лист"""
        if not self.excel_path or not os.path.exists(self.excel_path):
            self.status_label.config(text="❌ Файл не найден", foreground="red")
            return
        
        try:
            # Определяем контекст по sheet_name
            context = self._get_context_from_sheet_name(self.sheet_name)
            
            # Архивируем
            from core.archive.archive_manager import ArchiveManager
            archive_manager = ArchiveManager(self.config_manager, self.coordinator)
            
            result = archive_manager.extract_data_for_archive(
                workshop=context["workshop"],
                enable_pallet=context["enable_pallet"],
                multitype_mode=context["multitype_mode"]
            )
            
            if result["success"]:
                # Сохраняем
                success = self.config_manager.add_pallet_to_archive(result["archive_data"])
                if success:
                    self.status_label.config(text="✅ Архивировано", foreground="green")
                else:
                    self.status_label.config(text="❌ Ошибка сохранения", foreground="red")
            else:
                self.status_label.config(text=f"❌ {result.get('error')}", foreground="red")
                
        except Exception as e:
            self.status_label.config(text=f"❌ {str(e)[:40]}", foreground="red")
            
    def _get_context_from_sheet_name(self, sheet_name):
        """Определяет параметры архивации по названию листа"""
        if sheet_name == "Лист для коробки":
            return {"workshop": "1", "enable_pallet": False, "multitype_mode": False}
        elif sheet_name == "Лист для паллеты":
            return {"workshop": "1", "enable_pallet": True, "multitype_mode": False}
        elif sheet_name == "Лист много видов":
            return {"workshop": "1", "enable_pallet": False, "multitype_mode": True}
        elif sheet_name == "Поддон":
            return {"workshop": "2", "enable_pallet": False, "multitype_mode": False}
        elif sheet_name == "Список поддонов":
            return {"workshop": "2", "enable_pallet": True, "multitype_mode": False}
        elif sheet_name == "Много видов":
            return {"workshop": "2", "enable_pallet": False, "multitype_mode": True}
        else:
            return {"workshop": "1", "enable_pallet": False, "multitype_mode": False}
        
    def _save_printer_settings(self):
        """Сохраняет выбранные принтеры в настройки"""
        try:
            printer1 = self.printer1_var.get().strip()
            printer2 = self.printer2_var.get().strip()
            
            # Проверяем, не пустые ли строки
            if printer1 == "":
                printer1 = None
            if printer2 == "":
                printer2 = None
            
            # Сохраняем через ConfigManager
            success = self.config_manager.save_preview_printers(printer1, printer2)
            
            if success:
                # Временно показываем статус
                if hasattr(self, 'status_label'):
                    self.status_label.config(
                        text="Настройки печати сохранены", 
                        foreground="green"
                    )
                    # Возвращаем исходный статус через 3 секунды
                    self.preview_window.after(3000, self._restore_status)
            else:
                if hasattr(self, 'status_label'):
                    self.status_label.config(
                        text="Ошибка сохранения настроек", 
                        foreground="red"
                    )
                    
        except Exception as e:
            print(f"Ошибка сохранения принтеров: {e}")
            if hasattr(self, 'status_label'):
                self.status_label.config(
                    text=f"Ошибка: {str(e)[:30]}", 
                    foreground="red"
                )
    
    def _restore_status(self):
        """Восстанавливает исходный статус если нет ошибок"""
        if hasattr(self, 'status_label'):
            current_text = self.status_label.cget("text")
            # Восстанавливаем только если это был временный статус сохранения
            if "Настройки печати сохранены" in current_text:
                self.status_label.config(
                    text="Готово", 
                    foreground="green"
                )
    
    def _on_print_clicked(self):
        """Обработчик клика по кнопке печати"""
        printer1 = self.printer1_var.get().strip()
        printer2 = self.printer2_var.get().strip()
        copies = self.copies_var.get()
        
        # Проверка: хотя бы один принтер должен быть выбран
        if not printer1 and not printer2:
            self.status_label.config(
                text="Выберите хотя бы один принтер", 
                foreground="red"
            )
            return
            
        # Проверка существования файла
        if not self.excel_path or not os.path.exists(self.excel_path):
            self.status_label.config(
                text="Файл Excel не найден", 
                foreground="red"
            )
            return
            
        # Запускаем печать в отдельном потоке
        self._start_printing(printer1, printer2, copies)
        
    def _format_printer_for_excel(self, printer_name, excel_app=None):
        """Преобразует имя принтера в формат, который понимает Excel"""
        if not printer_name:
            return ""
        
        # Если передан экземпляр Excel, берем порт из его ActivePrinter
        if excel_app:
            try:
                current = excel_app.ActivePrinter
                print(f"Текущий ActivePrinter для парсинга: '{current}'")
                
                # Парсим: "Xprinter XP-420B (Ne00:)"
                # Находим последнюю открывающую скобку
                bracket_pos = current.rfind(" (")
                if bracket_pos != -1:
                    # Извлекаем все после скобки до конца
                    port_part = current[bracket_pos:]  # " (Ne00:)"
                    return f"{printer_name}{port_part}"
            except Exception as e:
                print(f"Ошибка парсинга ActivePrinter: {e}")
        
        # Запасной вариант
        return f"{printer_name} (Ne00:)"
    
    def _start_printing(self, printer1, printer2, copies):
        """Запускает процесс печати"""
        # Обновляем статус
        self.status_label.config(
            text="Подготовка к печати...", 
            foreground="blue"
        )
        
        # Запускаем в отдельном потоке чтобы не блокировать GUI
        import threading
        thread = threading.Thread(
            target=self._print_excel_area,
            args=(printer1, printer2, copies),
            daemon=True
        )
        thread.start()
        
    def _print_excel_area(self, printer1, printer2, copies):
        """Печатает область печати Excel файла на выбранные принтеры"""
        try:
            self.preview_window.after(0, lambda: self.status_label.config(
                text="Подготовка Excel...", 
                foreground="blue"
            ))
            
            import win32com.client
            import pythoncom
            import time
            import win32print  # Для дебага           
            
            pythoncom.CoInitialize()
            
            excel = win32com.client.DispatchEx("Excel.Application")
            excel.Visible = False
            excel.DisplayAlerts = False
            excel.ScreenUpdating = False
            
            print(f"ActivePrinter до: {excel.ActivePrinter}")
            
            wb = excel.Workbooks.Open(self.excel_path)
            
            try:
                ws = wb.Sheets(self.sheet_name)
            except:
                ws = wb.Sheets(1)
            
            ws.Activate()
            
            print_area = ws.Range(ws.PageSetup.PrintArea)
            print_area.Select()
            
            time.sleep(0.5)
            
            # Печать на принтер 1
            if printer1:
                self.preview_window.after(0, lambda: self.status_label.config(
                    text=f"Печать на {printer1[:20]}...", 
                    foreground="blue"
                ))
                
                excel_printer1 = self._format_printer_for_excel(printer1, excel)
                
                excel.ActivePrinter = excel_printer1
                ws.PrintOut(Copies=copies)
                time.sleep(1)
            
            # Печать на принтер 2
            if printer2 and printer2 != printer1:
                self.preview_window.after(0, lambda: self.status_label.config(
                    text=f"Печать на {printer2[:20]}...", 
                    foreground="blue"
                ))
                
                excel_printer2 = self._format_printer_for_excel(printer2, excel)
                
                excel.ActivePrinter = excel_printer2
                ws.PrintOut(Copies=copies)
            
            wb.Close(SaveChanges=False)
            excel.Quit()
            pythoncom.CoUninitialize()
            
            self.preview_window.after(0, lambda: self.status_label.config(
                text="✅ Печать завершена", 
                foreground="green"
            ))
            
        except Exception as e:
            error_msg = str(e)
            print(f"Ошибка печати: {error_msg}")
            self.preview_window.after(0, lambda: self.status_label.config(
                text=f"❌ Ошибка: {error_msg[:50]}", 
                foreground="red"
            ))
            
            try:
                pythoncom.CoUninitialize()
            except:
                pass
        
    def load_and_render_preview(self):
        """Загружает Excel и создает точный предпросмотр через win32com"""
        try:
            self.excel_path = self._get_excel_path()
            if not self.excel_path or not os.path.exists(self.excel_path):
                self.show_error_preview("Файл Excel не найден")
                return
            
            # Конвертируем Excel в изображение
            image = self.excel_to_image_simple(self.excel_path, self.sheet_name)
            
            if image:
                self.display_preview(image)
                if hasattr(self, 'status_label'):
                    self.status_label.config(text="✓ Загружено", foreground="green")
            else:
                self.show_error_preview("Не удалось создать предпросмотр")
                # Добавить сюда изменение статуса на ошибку
                if hasattr(self, 'status_label'):
                    self.status_label.config(text="✗ Ошибка загрузки", foreground="red")
                    
        except Exception as e:
            self.show_error_preview(f"Ошибка: {str(e)}")
            # Добавить сюда изменение статуса на ошибку
            if hasattr(self, 'status_label'):
                self.status_label.config(text=f"✗ Ошибка: {str(e)[:20]}", foreground="red")
            
    def update_preview(self):
        """Обновляет предпросмотр"""
        # Если sheet_name не установлен, используем лист для коробки цеха 1 как fallback
        if self.sheet_name is None:
            workshop = "1"
            if hasattr(self, 'coordinator') and self.coordinator:
                workshop = self.coordinator.get_workshop()
            self.sheet_name = self._get_sheet_for_preview(workshop, False, False)
        
        # Сбрасываем флаг увеличения
        if hasattr(self, '_already_scaled'):
            del self._already_scaled
        
        # Очищаем канвас перед обновлением
        if self.preview_canvas:
            self.preview_canvas.delete("all")
            self.preview_canvas.config(scrollregion=(0, 0, 1, 1))
        
        self.excel_path = self._get_excel_path()
        if self.excel_path and os.path.exists(self.excel_path):
            self.load_and_render_preview()
        elif self.preview_canvas:
            # Если файла нет, показываем сообщение
            self.show_error_preview("Файл Excel не найден")

    def on_close_preview(self):
        """Обработчик закрытия окна предпросмотра"""
        if (hasattr(self, 'preview_window') and 
            self.preview_window is not None):
            
            # Уничтожаем окно
            self.preview_window.destroy()
            
            # Очищаем ссылки
            self.preview_window = None
            self.preview_canvas = None
            
            # Очищаем tk_image чтобы избежать утечек памяти
            if hasattr(self, 'tk_image'):
                del self.tk_image