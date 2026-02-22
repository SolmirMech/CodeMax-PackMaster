import os
import tkinter as tk
from tkinter import ttk


# noinspection PyUnboundLocalVariable
class ExcelPreviewModule:
    """Модуль предпросмотра Excel файла"""
    
    def __init__(self, parent, coordinator=None, config_manager=None):
        self.zoom_var = None
        self.top_offset_var = None
        self.tk_image = None
        self.status_label = None
        self.parent = parent
        self.coordinator = coordinator
        self.config_manager = config_manager
        
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
            # Инициализация статуса архивации
            coordinator.subscribe(self.on_settings_changed)
            # Получаем текущий статус
            self.archive_enabled = (coordinator.get_archive_status() == "on")
        else:
            self.archive_enabled = True  # по умолчанию включено
            
    def _ensure_excel_files_exist(self):
        """Проверяет наличие Excel файлов и копирует из assets при необходимости"""
        try:
            # Загружаем настройки
            settings = self.config_manager.load_json_settings("shared_utils.json")
            excel_folder = settings.get("weight_orders_xlsx", "")
            
            # Если путь не указан - используем папку data
            if not excel_folder or not os.path.exists(excel_folder):
                excel_folder = str(self.config_manager.data_dir)
                settings["weight_orders_xlsx"] = excel_folder
                self.config_manager.save_json_settings("shared_utils.json", settings)
            
            # Проверяем наличие обоих файлов
            files_to_check = [
                ("weight_orders.xlsx", "weight_orders.xlsx"),
                ("weight_orders_2.xlsx", "weight_orders_2.xlsx")
            ]
            
            files_copied = False
            for assets_filename, target_filename in files_to_check:
                target_file = os.path.join(excel_folder, target_filename)
                
                # Если файл отсутствует - копируем из assets
                if not os.path.exists(target_file):
                    assets_file = self.config_manager.get_asset_path(assets_filename)
                    if os.path.exists(assets_file):
                        import shutil
                        shutil.copy2(assets_file, target_file)
                        files_copied = True
            
            if files_copied:
                # Обновляем статус в интерфейсе если окно открыто
                if self.status_label is not None:
                    self.status_label.config(
                        text="✓ Файлы Excel восстановлены", 
                        foreground="green"
                    )
                    
        except Exception as e:
            print(f"[ERROR] Ошибка проверки Excel файлов: {e}")
            
    def get_sheet_for_preview(self, workshop, enable_pallet=False, multitype_mode=False):
        """Определяет лист для предпросмотра на основе контекста"""
        if workshop == "1":
            if multitype_mode:
                return "Лист много видов"
            elif enable_pallet:
                # Проверяем наличие веса через координатор
                has_weight = True
                if self.coordinator is not None:
                    has_weight = self.coordinator.get_weight_status()
                
                # Если нет веса и включен режим паллеты - показываем лист "БезВеса"
                if not has_weight and enable_pallet:
                    return "БезВеса"
                else:
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
            
    @staticmethod
    def _get_system_printers():
        try:
            import win32print
            printers = win32print.EnumPrinters(2)
            printer_names = [p[2] for p in printers]         
            
            return printer_names
        except Exception as e:
            print(f"[ERROR] Ошибка получения принтеров: {e}")
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
            if self.coordinator is not None:
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
        if self.preview_window is not None and self.preview_window.winfo_exists():
            
            self.preview_window.destroy()
            self.show_preview_window()
    
    def on_excel_exported(self, event_type=None, data=None):
        """Обработчик событий от координатора для всех режимов предпросмотра"""
        if event_type == "excel_exported":
            # Получаем параметры из данных события
            workshop = data.get('workshop', '1')
            enable_pallet = data.get('enable_pallet', False)
            multitype_mode = data.get('multitype_mode', False)
            
            # Определяем лист
            self.sheet_name = self.get_sheet_for_preview(
                workshop, enable_pallet, multitype_mode
            )
            
            # Обновляем заголовок окна если оно открыто
            if self.preview_window is not None and self.preview_window.winfo_exists():
                
                self.preview_window.title(f"Предпросмотр Excel - {self.sheet_name}")
                self.update_preview()
        
        elif event_type == "excel_cleared":
            # Тоже обновляем для события очистки
            workshop = data.get('workshop', '1')
            enable_pallet = data.get('enable_pallet', False)
            multitype_mode = data.get('multitype_mode', False)
            
            self.sheet_name = self.get_sheet_for_preview(
                workshop, enable_pallet, multitype_mode
            )

            if self.preview_window is not None and self.preview_window.winfo_exists():
                
                self.preview_window.title(f"Предпросмотр Excel - {self.sheet_name}")
                self.update_preview()

    # noinspection PyUnusedLocal
    def on_settings_changed(self, context=None):
        """Обработчик изменения любых настроек от координатора"""
        if self.coordinator and hasattr(self.coordinator, 'get_archive_status'):
            status = self.coordinator.get_archive_status()
            self.archive_enabled = (status == "on")
            has_weight = self.coordinator.get_weight_status()

    # noinspection PyPackageRequirements,PyUnusedImports
    def excel_to_image_simple(self, excel_path, sheet_name):
        """Скриншот области печати Excel"""
        import win32com.client
        import pythoncom
        from PIL import ImageGrab
        import time
        import win32gui
        import win32api
        # все эти импорты нужны для вызываемых функций
        pythoncom_initialized = False
        excel = None
        try:
            pythoncom.CoInitialize()
            pythoncom_initialized = True
            
            # Основной процесс
            excel = self._open_excel_for_preview(excel_path, sheet_name)
            if not excel:
                return None
                
            screenshot = self._capture_excel_screenshot(excel, sheet_name)
            
            return screenshot
                
        except Exception as e:
            print(f"Ошибка скриншота: {e}")
            import traceback
            traceback.print_exc()
            return None
            
        finally:
            # Гарантированное освобождение
            if excel:
                try:
                    self._close_excel(excel)
                except:
                    pass
            
            # Принудительное завершение Excel процессов
            self._kill_excel_processes()
            
            if pythoncom_initialized:
                try:
                    pythoncom.CoUninitialize()
                except:
                    pass

    def _open_excel_for_preview(self, excel_path, sheet_name):
        """Открывает Excel и подготавливает лист"""
        try:
            import win32com.client         
            
            excel = win32com.client.DispatchEx("Excel.Application")
            excel.Visible = True
            excel.DisplayAlerts = False
            
            wb = excel.Workbooks.Open(excel_path)
            
            try:
                ws = wb.Sheets(sheet_name)
            except:
                ws = wb.Sheets(1)
            
            ws.Activate()
            
            # Настраиваем область печати
            self._setup_print_area(excel, ws)
            
            return excel
            
        except Exception as e:
            print(f"Ошибка открытия Excel: {e}")
            return None

    def _setup_print_area(self, excel, worksheet):
        """Настраивает область печати и зум"""
        try:
            print_area_str = worksheet.PageSetup.PrintArea
            
            if not print_area_str:
                print_area = worksheet.Range("A1:I45")
            else:
                print_area = worksheet.Range(print_area_str)         
            
            # Прокручиваем к началу области
            excel.ActiveWindow.ScrollRow = print_area.Row
            excel.ActiveWindow.ScrollColumn = print_area.Column
            
            # Выделяем область
            print_area.Select()
            
            # Настраиваем зум
            self._set_excel_zoom(excel)
            
        except Exception as e:
            print(f"Ошибка настройки области печати: {e}")

    def _set_excel_zoom(self, excel):
        """Устанавливает зум для Excel"""
        try:
            import win32api
            
            # Получаем высоту экрана
            screen_height = win32api.GetSystemMetrics(1)
            
            # Загружаем настройки
            settings = self.config_manager.load_json_settings("shared_utils.json")
            preview_settings = settings.get("preview_settings", {})
            
            # Если зум не задан в настройках - подбираем автоматически по высоте экрана
            zoom_level = preview_settings.get("zoom_level")
            if zoom_level is None:
                # Автоматический подбор
                if screen_height >= 1080:
                    zoom_level = 90
                elif screen_height >= 900:
                    zoom_level = 80
                elif screen_height >= 768:
                    zoom_level = 70
                else:
                    zoom_level = 60
            
            # Устанавливаем зум
            excel.ActiveWindow.Zoom = zoom_level
            
        except Exception:
            excel.ActiveWindow.Zoom = 90  # fallback

    # noinspection PyPackageRequirements,PyUnusedLocal
    def _capture_excel_screenshot(self, excel, sheet_name):
        """Делает скриншот окна Excel"""
        try:
            import time
            import win32gui
            from PIL import ImageGrab
            
            time.sleep(0.3)
            
            # Сворачиваем Excel для получения HWND
            excel.WindowState = -4140  # xlMinimized
            time.sleep(0.1)
            
            # Получаем HWND
            excel_hwnd = excel.Hwnd
            if not excel_hwnd or not win32gui.IsWindow(excel_hwnd):
                print("Окно Excel не найдено")
                return None
            
            # Получаем активный лист
            ws = excel.ActiveSheet
            
            # Восстанавливаем окно
            excel.WindowState = -4137  # xlNormal
            time.sleep(0.3)
            
            # Получаем границы области печати
            print_area_bounds = self._get_print_area_pixel_bounds(excel, ws, excel_hwnd)
            
            if print_area_bounds:
                table_left, table_top, table_right, table_bottom = print_area_bounds
            else:
                # Fallback: старый метод
                print_area_bounds = self._calculate_screenshot_coordinates(excel_hwnd)
                if not print_area_bounds:
                    return None
                table_left, table_top, table_right, table_bottom = print_area_bounds
            
            # Делаем скриншот
            screenshot = ImageGrab.grab(bbox=(
                max(0, table_left),
                max(0, table_top),
                table_right,
                table_bottom
            ))         
            
            return screenshot
            
        except Exception as e:
            print(f"Ошибка захвата скриншота: {e}")
            return None

    # noinspection PyPackageRequirements,PyUnusedLocal
    def _get_print_area_pixel_bounds(self, excel, worksheet, excel_hwnd):
        """Возвращает границы области печати в пикселях экрана"""
        try:
            import win32com.client
            import win32gui
            import win32print
            import win32con
            
            # Получаем область печати
            print_area_str = worksheet.PageSetup.PrintArea
            if not print_area_str:
                print_area = worksheet.Range("A1:I45")
            else:
                print_area = worksheet.Range(print_area_str)
            
            # Получаем DPI экрана
            hdc = win32gui.GetDC(0)
            dpi_x = win32print.GetDeviceCaps(hdc, win32con.LOGPIXELSX)  # DPI по горизонтали
            dpi_y = win32print.GetDeviceCaps(hdc, win32con.LOGPIXELSY)  # DPI по вертикали
            win32gui.ReleaseDC(0, hdc)
            
            # Конвертируем точки в пиксели
            # В Excel: 1 point = 1/72 дюйма
            # Пиксели = (points / 72) * DPI
            
            left_points = print_area.Left
            top_points = print_area.Top
            width_points = print_area.Width
            height_points = print_area.Height
            
            # Конвертация
            left_px = int((left_points / 72) * dpi_x)
            top_px = int((top_points / 72) * dpi_y)
            width_px = int((width_points / 72) * dpi_x)
            height_px = int((height_points / 72) * dpi_y)         
            
            # Получаем положение окна Excel
            screen_rect = win32gui.GetWindowRect(excel_hwnd)
            client_rect = win32gui.GetClientRect(excel_hwnd)
            
            # Рассчитываем рамки
            frame_width = (screen_rect[2] - screen_rect[0] - client_rect[2]) // 2
            title_height = (screen_rect[3] - screen_rect[1] - client_rect[3]) - frame_width
            
            # Получаем отступ из настроек
            settings = self.config_manager.load_json_settings("shared_utils.json")
            preview_settings = settings.get("preview_settings", {})
            top_offset = preview_settings.get("top_offset", 0)
            
            # Рассчитываем абсолютные координаты на экране
            # Сейчас координаты relative to client area
            # Нужно добавить сдвиг ленты Excel (около 150px)
            excel_ribbon_height = 150  # Приблизительная высота ленты Excel
            
            table_left = screen_rect[0] + frame_width + left_px
            table_top = screen_rect[1] + title_height + top_offset + top_px + excel_ribbon_height
            table_right = table_left + width_px
            table_bottom = table_top + height_px         
            
            return table_left, table_top, table_right, table_bottom
            
        except Exception as e:
            print(f"Ошибка расчета границ области печати: {e}")
            import traceback
            traceback.print_exc()
            return None

    # noinspection PyPackageRequirements
    def _calculate_screenshot_coordinates(self, excel_hwnd):
        """Рассчитывает координаты для скриншота"""
        try:
            import win32gui
            import win32api
            
            # Получаем размеры экрана
            screen_width = win32api.GetSystemMetrics(0)
            screen_height = win32api.GetSystemMetrics(1)
            
            # Получаем размеры окна Excel
            screen_rect = win32gui.GetWindowRect(excel_hwnd)
            client_rect = win32gui.GetClientRect(excel_hwnd)
            
            # Рассчитываем ширину рамок окна
            frame_width = (screen_rect[2] - screen_rect[0] - client_rect[2]) // 2
            
            # Рассчитываем высоту заголовка и ленты Excel
            title_height = (screen_rect[3] - screen_rect[1] - client_rect[3]) - frame_width
            
            # Получаем настраиваемый отступ из настроек
            settings = self.config_manager.load_json_settings("shared_utils.json")
            preview_settings = settings.get("preview_settings", {})
            top_offset = preview_settings.get("top_offset", 160)
            
            # Рассчитываем координаты
            table_left = screen_rect[0] + frame_width + 20
            table_top = screen_rect[1] + title_height + top_offset
            table_right = table_left + 565  # фиксированная ширина
            
            # Высота скриншота адаптируется под экран
            available_height = screen_height - table_top - 50
            table_bottom = table_top + min(1000, available_height)
            
            # Корректируем границы
            table_right = min(screen_width, table_right)
            table_bottom = min(screen_height, table_bottom)
                        
            return table_left, table_top, table_right, table_bottom
            
        except Exception:
            return None

    def _close_excel(self, excel):
        """Закрывает Excel и принудительно завершает процесс"""
        import time
        
        try:
            # Стандартное закрытие
            try:
                excel.DisplayAlerts = False
                excel.ScreenUpdating = False
                
                # Закрываем все книги
                while excel.Workbooks.Count > 0:
                    try:
                        excel.Workbooks(1).Close(SaveChanges=False)
                    except:
                        break
                
                # Закрываем Excel
                excel.Quit()
                time.sleep(0.5)
                
            except Exception as e:
                print(f"Ошибка при стандартном закрытии Excel: {e}")
            
        finally:
            # Пытаемся удалить объект
            try:
                del excel
            except:
                pass
            
            # Принудительное завершение процессов
            self._kill_excel_processes()
            
    @staticmethod
    def _kill_excel_processes():
        """Принудительно завершает процессы Excel"""
        try:
            import psutil
            import os
            
            # Ищем процессы Excel
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'] and 'excel.exe' in proc.info['name'].lower():
                        # Если процесс запущен нашим пользователем
                        if proc.username() == os.getlogin():
                            proc.kill()
                            print(f"Завершен процесс Excel (PID: {proc.info['pid']})")
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
        except ImportError:
            # Если psutil не установлен, используем taskkill
            try:
                import subprocess
                subprocess.run(['taskkill', '/F', '/IM', 'excel.exe'], 
                              capture_output=True, timeout=5)
                print("Excel процессы завершены через taskkill")
            except:
                print("Не удалось завершить Excel процессы")
        except Exception as e:
            print(f"Ошибка при завершении Excel: {e}")
            
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
            settings["preview_settings"]["zoom_level"] = self.zoom_var.get()
            
            # Сохраняем обратно в shared_utils
            success = self.config_manager.save_json_settings("shared_utils.json", settings)
            
            if success:
                self.status_label.config(
                    text="✓ Настройки сохранены", 
                    foreground="green"
                )
                # Возвращаем исходный статус через 2 секунды
                self.preview_window.after(3000, self._restore_status)
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

    # noinspection PyUnusedLocal
    def show_preview_window(self):
        """Открывает окно предпросмотра"""
        # Если окно уже открыто - поднимаем его
        if self.preview_window is not None and self.preview_window.winfo_exists():
            
            self.preview_window.lift()
            self.preview_window.focus_force()
            self.update_preview()  # Обновляем данные
            return
        
        # Определяем текущий цех
        workshop = "1"
        if self.coordinator and hasattr(self.coordinator, 'get_workshop'):
            workshop = self.coordinator.get_workshop()
        
        # Создаем новое окно предпросмотра
        self.preview_window = tk.Toplevel(self.parent)
        self.preview_window.title(f"Предпросмотр Excel - {self.sheet_name}")
        
        # ======== Размеры ========
        window_width = 670
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
        copies_spinbox.grid(row=0, column=3, padx=5, sticky='w')
        
        btn_archive = ttk.Button(
            control_frame,
            text="⏳ В архив",
            command=self.archive_current_sheet,
            width=10
        )
        btn_archive.grid(row=1, column=2, columnspan=2, padx=5, sticky='w')        
        
        # Отступ и зум
        ttk.Label(control_frame, text="Отступ").grid(row=0, column=4, padx=(0, 5), sticky='w')       
        settings = self.config_manager.load_json_settings("shared_utils.json")
        preview_settings = settings.get("preview_settings", {})
        default_offset = preview_settings.get("top_offset", 160)
        
        self.top_offset_var = tk.IntVar(value=default_offset)
        
        top_offset_entry = ttk.Entry(
            control_frame,
            textvariable=self.top_offset_var,
            width=5
        )
        top_offset_entry.grid(row=0, column=5, sticky='w')
        
        # Привязываем изменение
        top_offset_entry.bind("<FocusOut>", lambda e: self._save_preview_settings())
        
        default_zoom = preview_settings.get("zoom_level", 90)  # По умолчанию 90%
        self.zoom_var = tk.IntVar(value=default_zoom)
        
        ttk.Label(control_frame, text="Зум (%)").grid(row=1, column=4, padx=(0, 5), sticky='w')
        zoom_entry = ttk.Entry(
            control_frame,
            textvariable=self.zoom_var,
            width=5
        )
        zoom_entry.grid(row=1, column=5, sticky='w')
        zoom_entry.bind("<FocusOut>", lambda e: self._save_preview_settings())        
        
        # Метка статуса
        self.status_label = ttk.Label(control_frame, text="", foreground="blue")
        self.status_label.grid(row=2, column=0, columnspan=6, padx=10, sticky='w')      
        
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
            
    @staticmethod
    def _get_context_from_sheet_name(sheet_name):
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
                     
            # Сохраняем через ConfigManager
            success = self.config_manager.save_preview_printers(printer1, printer2)
            
            if success:
                # Временно показываем статус
                if self.status_label is not None:
                    self.status_label.config(
                        text="Настройки печати сохранены", 
                        foreground="green"
                    )
                    # Возвращаем исходный статус через 3 секунды
                    self.preview_window.after(3000, self._restore_status)
            else:
                if self.status_label is not None:
                    self.status_label.config(
                        text="Ошибка сохранения настроек", 
                        foreground="red"
                    )
                    
        except Exception as e:
            print(f"Ошибка сохранения принтеров: {e}")
            if self.status_label is not None:
                self.status_label.config(
                    text=f"Ошибка: {str(e)[:30]}", 
                    foreground="red"
                )
    
    def _restore_status(self):
        """Восстанавливает исходный статус если нет ошибок"""
        if self.status_label is not None:
            current_text = self.status_label.cget("text")
            # Восстанавливаем только если это был временный статус сохранения
            if "Настройки печати сохранены" in current_text:
                self.status_label.config(
                    text="Готово", 
                    foreground="green"
                )
    
    def _on_print_clicked(self):
        printer1 = self.printer1_var.get().strip()
        printer2 = self.printer2_var.get().strip()
        copies = self.copies_var.get()
        
        # Проверка: хотя бы один принтер должен быть выбран (не пустая строка)
        if not printer1 and not printer2:
            self.status_label.config(
                text="Выберите хотя бы один принтер", 
                foreground="red"
            )
            return
            
        # Запускаем печать
        self._start_printing(printer1, printer2, copies)      
    
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
        pythoncom_initialized = False
        excel = None
        wb = None
        
        try:
            import win32com.client
            import pythoncom
            import win32print
            import time
            
            pythoncom.CoInitialize()
            pythoncom_initialized = True
            
            # 1. Запоминаем текущий принтер по умолчанию
            original_printer = win32print.GetDefaultPrinter()
            
            # 2. Список принтеров для печати
            printers_to_use = []
            if printer1:
                printers_to_use.append(printer1)
            if printer2 and printer2 != printer1:
                printers_to_use.append(printer2)
            
            # 3. Печать на каждый принтер
            for i, printer_name in enumerate(printers_to_use, 1):
                self.preview_window.after(0, lambda p=printer_name: self.status_label.config(
                    text=f"Печать на {p[:20]}...", 
                    foreground="blue"
                ))
                                
                # Устанавливаем принтер по умолчанию
                try:
                    win32print.SetDefaultPrinter(printer_name)
                    time.sleep(1)  # Дать системе время на применение
                except Exception as e:
                    print(f"[ERROR] Не удалось установить принтер по умолчанию: {e}")
                    continue
                
                # Создаем новый экземпляр Excel для каждого принтера
                try:
                    excel = win32com.client.DispatchEx("Excel.Application")
                    excel.Visible = False
                    excel.DisplayAlerts = False
                    excel.ScreenUpdating = False
                    
                    wb = excel.Workbooks.Open(self.excel_path)
                    
                    try:
                        ws = wb.Sheets(self.sheet_name)
                    except:
                        ws = wb.Sheets(1)
                    
                    ws.Activate()
                    
                    # Настраиваем область печати
                    # noinspection PyUnusedLocal
                    print_area = None
                    try:
                        print_area_str = ws.PageSetup.PrintArea
                        if print_area_str:
                            print_area = ws.Range(print_area_str)
                        else:
                            print_area = ws.Range("A1:I45")
                    except:
                        print_area = ws.Range("A1:I45")
                    
                    print_area.Select()
                    time.sleep(0.5)

                    # Печатаем на текущем принтере по умолчанию
                    import time
                    for copy_num in range(copies):
                        ws.PrintOut(ActivePrinter=printer_name)
                        if copy_num < copies - 1:
                            time.sleep(0.5)
                    
                    # Закрываем Excel для этого принтера
                    wb.Close(SaveChanges=False)
                    excel.Quit()
                    time.sleep(0.5)
                    
                    # Принудительно чистим
                    del ws
                    del wb
                    del excel
                    wb = None
                    excel = None
                    
                except Exception as e:
                    print(f"[ERROR] Ошибка при печати на {printer_name}: {e}")
                    continue
                finally:
                    # Гарантированное закрытие
                    if wb is not None:  # теперь безопасно
                        try:
                            wb.Close(SaveChanges=False)
                        except:
                            pass
                    if excel is not None:
                        try:
                            excel.Quit()
                        except:
                            pass
                    
                    # Принудительно убиваем процессы Excel
                    self._kill_excel_processes()
            
            # 4. Возвращаем оригинальный принтер по умолчанию
            if original_printer:
                try:
                    win32print.SetDefaultPrinter(original_printer)
                except Exception as e:
                    print(f"[ERROR] Не удалось вернуть принтер по умолчанию: {e}")
            
            if self.archive_enabled:
                self.preview_window.after(0, lambda: self.status_label.config(
                    text="✅ Печать завершена", 
                    foreground="green"
                ))
                # Добавить автоматическую архивацию
                self.preview_window.after(100, self.archive_current_sheet)
            else:
                self.preview_window.after(0, lambda: self.status_label.config(
                    text="✅ Печать завершена (архивация отключена)", 
                    foreground="green"
                ))
                
        except Exception as e:
            error_msg = str(e)
            print(f"[ERROR] Ошибка печати: {error_msg}")
            self.preview_window.after(0, lambda: self.status_label.config(
                text=f"❌ Ошибка: {error_msg[:50]}", 
                foreground="red"
            ))
            
        finally:
            # Гарантированное закрытие
            if wb is not None:  # теперь безопасно
                try:
                    wb.Close(SaveChanges=False)
                except:
                    pass
            if excel is not None:
                try:
                    excel.Quit()
                except:
                    pass
            
            # Явно удаляем объекты
            try:
                del wb
            except:
                pass
                
            try:
                del excel
            except:
                pass
            
            # Гарантированное освобождение com
            if pythoncom_initialized:
                try:
                    pythoncom.CoUninitialize()
                except:
                    pass
            
            # Принудительно убиваем процессы Excel
            self._kill_excel_processes()
        
    def load_and_render_preview(self):
        """Загружает Excel и создает точный предпросмотр через win32com"""
        try:
            self.excel_path = self._get_excel_path()
            if not self.excel_path or not os.path.exists(self.excel_path):
                self.show_error_preview("Файл Excel не найден")
                self.status_label.config(text="✗ Файл не найден", foreground="red")
                return
            
            # Конвертируем Excel в изображение
            image = self.excel_to_image_simple(self.excel_path, self.sheet_name)
            
            if image:
                self.display_preview(image)
                self.status_label.config(text="✓ Загружено", foreground="green")
            else:
                self.show_error_preview("Не удалось создать предпросмотр")
                self.status_label.config(text="✗ Ошибка загрузки", foreground="red")
                
        except Exception as e:
            error_msg = str(e)
            self.show_error_preview(error_msg)
            self.status_label.config(text=f"✗ Ошибка: {error_msg[:20]}", foreground="red")
            
    def update_preview(self):
        """Обновляет предпросмотр"""
        # Если sheet_name не установлен, используем лист для коробки цеха 1 как fallback
        if self.sheet_name is None:
            workshop = "1"
            if self.coordinator is not None:
                workshop = self.coordinator.get_workshop()
            self.sheet_name = self.get_sheet_for_preview(workshop, False, False)
        
        # Сбрасываем флаг увеличения
        if hasattr(self, '_already_scaled'):
            del self._already_scaled
        
        # Очищаем канвас перед обновлением
        if self.preview_canvas:
            self.preview_canvas.delete("all")
            self.preview_canvas.config(scrollregion=(0, 0, 1, 1))
            
        self._ensure_excel_files_exist()            
        
        self.excel_path = self._get_excel_path()
        if self.excel_path and os.path.exists(self.excel_path):
            self.load_and_render_preview()
        elif self.preview_canvas:
            # Если файла нет, показываем сообщение
            self.show_error_preview("Файл Excel не найден")

    def on_close_preview(self):
        """Обработчик закрытия окна предпросмотра"""
        if self.preview_window is not None and self.preview_window.winfo_exists():
            
            # Уничтожаем окно
            self.preview_window.destroy()
            
            # Очищаем ссылки
            self.preview_window = None
            self.preview_canvas = None
            
            # Очищаем tk_image, чтобы избежать утечек памяти
            if hasattr(self, 'tk_image'):
                del self.tk_image