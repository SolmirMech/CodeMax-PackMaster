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
        self.sheet_name = "Лист для коробки"  # начальный лист
        
        # GUI элементы
        self.preview_canvas = None
        self.scrollbar = None
        
        # Подписка на координатор
        if coordinator and hasattr(coordinator, 'subscribe'):
            coordinator.subscribe(self.on_excel_exported)
    
    def _get_excel_path(self):
        """Получает путь к Excel файлу из настроек"""
        settings = self.config_manager.load_json_settings("shared_utils.json")
        excel_folder = settings.get("weight_orders_xlsx", "")
        filename = "weight_orders.xlsx"
        return os.path.join(excel_folder, filename)
    
    def on_excel_exported(self, event_type=None, data=None):
        """Обработчик событий от координатора"""
        if event_type == "excel_exported" and data.get('sheet_name') == "Лист для коробки":
            self.update_preview()  # Только для коробки
        elif event_type == "excel_cleared" and data.get('sheet_name') == "Лист для коробки":
            self.update_preview()  # Только для коробки
    
    def update_preview(self):
        """Обновляет предпросмотр"""
        self.excel_path = self._get_excel_path()
        if self.excel_path and os.path.exists(self.excel_path):
            self.load_and_render_preview()
    
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
            else:
                self.show_error_preview("Не удалось создать предпросмотр")
                
        except Exception as e:
            self.show_error_preview(f"Ошибка: {str(e)}")

    def excel_to_image_simple(self, excel_path, sheet_name):
        """Скриншот ТОЛЬКО области печати Excel"""
        try:
            # Импорты
            import win32com.client
            import pythoncom
            from PIL import ImageGrab
            import time
            import win32gui
            
            # Инициализация COM
            pythoncom.CoInitialize()
            
            # 1. ОТКРЫВАЕМ EXCEL
            excel = win32com.client.DispatchEx("Excel.Application")
            excel.Visible = True
            excel.DisplayAlerts = False
            
            wb = excel.Workbooks.Open(excel_path)
            
            # Получаем нужный лист
            try:
                ws = wb.Sheets(sheet_name)
            except:
                ws = wb.Sheets(1)  # Первый лист если не найден
            
            ws.Activate()  # Активируем лист
            
            # 2. ПОЛУЧАЕМ ОБЛАСТЬ ПЕЧАТИ
            if ws.PageSetup.PrintArea:
                # Используем заданную область печати
                print_area = ws.Range(ws.PageSetup.PrintArea)
                print(f"[DEBUG] Используем область печати: {print_area.Address}")
            else:
                # Фиксированная область для "Лист для коробки"
                print_area = ws.Range("A1:K45")
                print(f"[DEBUG] Используем фиксированную область: {print_area.Address}")
            
            # 3. НАСТРАИВАЕМ ВИД В EXCEL
            # Прокручиваем к началу области
            excel.ActiveWindow.ScrollRow = print_area.Row
            excel.ActiveWindow.ScrollColumn = print_area.Column
            
            # Выделяем область
            print_area.Select()
            
            # Настраиваем зум в зависимости от размера области
            rows_count = print_area.Rows.Count
            cols_count = print_area.Columns.Count
            
            if rows_count > 40 or cols_count > 12:
                excel.ActiveWindow.Zoom = 80
            elif rows_count > 30 or cols_count > 10:
                excel.ActiveWindow.Zoom = 90
            else:
                excel.ActiveWindow.Zoom = 100
            
            # Авто-размер колонок для читаемости
            print_area.Columns.AutoFit()
            
            # Ждем отрисовки
            time.sleep(0.8)
            
            # 4. ПОЛУЧАЕМ ОКНО EXCEL
            excel_hwnd = None
            
            def find_excel_window(hwnd, results):
                """Функция поиска окна Excel"""
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if title and ('Excel' in title or '.xlsx' in title):
                        results.append(hwnd)
                return True
            
            excel_windows = []
            win32gui.EnumWindows(find_excel_window, excel_windows)
            
            if not excel_windows:
                print("[DEBUG] Окно Excel не найдено")
                wb.Close(SaveChanges=False)
                excel.Quit()
                pythoncom.CoUninitialize()
                return None
            
            excel_hwnd = excel_windows[0]
            win32gui.SetForegroundWindow(excel_hwnd)
            time.sleep(0.3)
            
            # 5. ВЫЧИСЛЯЕМ КООРДИНАТЫ ОКНА
            client_rect = win32gui.GetClientRect(excel_hwnd)      # Клиентская область (без рамок)
            screen_rect = win32gui.GetWindowRect(excel_hwnd)      # Экранные координаты
            
            # Рассчитываем ширину рамок окна
            frame_width = (screen_rect[2] - screen_rect[0] - client_rect[2]) // 2
            
            # Рассчитываем высоту заголовка и ленты Excel
            title_height = (screen_rect[3] - screen_rect[1] - client_rect[3]) - frame_width
            
            # 6. ДЕЛАЕМ СКРИНШОТ ОБЛАСТИ ТАБЛИЦЫ
            # Начинаем ниже заголовка окна, но выше ленты Excel
            table_top = screen_rect[1] + title_height + 50  # 50px от заголовка
            
            # Заканчиваем выше нижней границы окна
            table_bottom = screen_rect[1] + title_height + client_rect[3] - 100  # Отрезаем 100px снизу
            
            # Скриншот области таблицы
            screenshot = ImageGrab.grab(bbox=(
                screen_rect[0] + frame_width,      # Левый край (после рамки)
                table_top,                         # Верхний край (после заголовка)
                screen_rect[0] + frame_width + client_rect[2],  # Правый край
                table_bottom                       # Нижний край (обрезан)
            ))
            
            print(f"[DEBUG] Размер скриншота: {screenshot.width}x{screenshot.height}")
            
            # 7. АВТОМАТИЧЕСКАЯ ОБРЕЗКА ТАБЛИЦЫ
            # Обрезаем ПРАВУЮ часть где нет данных
            right_cut = screenshot.width
            
            # Сканируем справа налево для поиска границы таблицы
            for x in range(screenshot.width - 1, screenshot.width - 400, -1):
                column_empty = True
                
                # Проверяем несколько точек в колонке
                check_points = [
                    screenshot.height // 4,    # 25% высоты
                    screenshot.height // 2,    # 50% высоты
                    screenshot.height * 3 // 4 # 75% высоты
                ]
                
                for y in check_points:
                    pixel = screenshot.getpixel((x, y))
                    # Если цвет не белый/светло-серый (фон)
                    if not (pixel[0] > 240 and pixel[1] > 240 and pixel[2] > 240):
                        column_empty = False
                        break
                
                if column_empty:
                    right_cut = x + 10  # Оставляем небольшой отступ
                else:
                    break  # Нашли данные, останавливаемся
            
            # Обрезаем НИЖНЮЮ часть где нет данных
            bottom_cut = screenshot.height
            
            # Сканируем снизу вверх
            for y in range(screenshot.height - 1, screenshot.height - 300, -1):
                row_empty = True
                
                # Проверяем несколько точек в строке
                check_points = [
                    screenshot.width // 4,     # 25% ширины
                    screenshot.width // 2,     # 50% ширины  
                    screenshot.width * 3 // 4  # 75% ширины
                ]
                
                for x in check_points:
                    pixel = screenshot.getpixel((x, y))
                    if not (pixel[0] > 240 and pixel[1] > 240 and pixel[2] > 240):
                        row_empty = False
                        break
                
                if row_empty:
                    bottom_cut = y + 10  # Отступ
                else:
                    break
            
            # 8. ПРИМЕНЯЕМ ОБРЕЗКУ
            if right_cut < screenshot.width - 50 or bottom_cut < screenshot.height - 50:
                # Обрезаем пустые области справа и снизу
                cropped = screenshot.crop((0, 0, right_cut, bottom_cut))
                print(f"[DEBUG] Обрезано до: {cropped.width}x{cropped.height}")
                image = cropped
            else:
                image = screenshot
            
            # 9. ЗАКРЫВАЕМ EXCEL
            wb.Close(SaveChanges=False)
            excel.Quit()
            pythoncom.CoUninitialize()
            
            return image
            
        except Exception as e:
            print(f"Ошибка скриншота: {e}")
            import traceback
            traceback.print_exc()
            
            # Всегда очищаем COM
            try:
                pythoncom.CoUninitialize()
            except:
                pass
                
            return None
        
    def display_preview(self, image):
        """Отображает PIL Image с качественным увеличением"""
        if not self.preview_canvas:
            return
        
        try:
            from PIL import ImageTk
            
            print(f"[DEBUG] Оригинальный размер: {image.width}x{image.height}")
            
            # УВЕЛИЧИВАЕМ ТОЛЬКО ЕСЛИ МАЛЕНЬКОЕ
            if image.width < 1200 or image.height < 1000:
                # Рассчитываем коэффициент для достижения мин. 1200px
                target_min = 1200
                scale = max(target_min / image.width, target_min / image.height)
                
                # Ограничиваем максимальное увеличение
                scale = min(scale, 3.0)
                
                # Качественное увеличение с антиалиасингом
                new_size = (int(image.width * scale), int(image.height * scale))
                
                # Используем LANCZOS (качественный ресамплинг)
                image = image.resize(new_size, Image.Resampling.LANCZOS)
                print(f"[DEBUG] Увеличено в {scale:.2f} раза до: {new_size[0]}x{new_size[1]}")
            
            self.tk_image = ImageTk.PhotoImage(image)
            
            self.preview_canvas.delete("all")
            self.preview_canvas.create_image(10, 10, anchor='nw', image=self.tk_image)
            
            self.preview_canvas.config(
                scrollregion=(0, 0, image.width + 20, image.height + 20)
            )
            
        except Exception as e:
            print(f"Ошибка отображения: {e}")
        
    def on_window_resize(self, event=None):
        """При изменении размера окна обновляем предпросмотр"""
        if hasattr(self, 'original_image') and self.original_image:
            # Перерисовываем с новым масштабом
            self.display_preview(self.original_image.copy())
    
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
    
    def create_preview_button(self, parent_frame):
        """Создает кнопку и окно предпросмотра"""
        # Кнопка для открытия предпросмотра
        btn_preview = ttk.Button(
            parent_frame,
            text="👁️ Просмотр Excel",
            command=self.show_preview_window,
            width=15
        )
        
        return btn_preview
    
    def show_preview_window(self):
        """Открывает окно предпросмотра"""
        # Если окно уже открыто - поднимаем его
        if hasattr(self, 'preview_window') and self.preview_window and self.preview_window.winfo_exists():
            self.preview_window.lift()
            self.preview_window.focus_force()
            self.preview_window.update_idletasks()
            self.update_preview()
            return
        
        # Создаем окно предпросмотра
        self.preview_window = tk.Toplevel(self.parent)
        self.preview_window.title("Предпросмотр Excel - Лист для коробки")
        
        # ======== РАЗМЕРЫ A4 (чуть больше) ========
        # A4 в пикселях при 96 DPI: 794 × 1123
        # Делаем чуть больше: 850 × 650 (ширина больше для таблиц)
        window_width = 850
        window_height = 650
        
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
        
        # Кнопка обновления
        btn_refresh = ttk.Button(
            control_frame,
            text="🔄 Обновить",
            command=self.update_preview,
            width=12
        )
        btn_refresh.pack(side=tk.LEFT, padx=(0, 10))
        
        # Метка статуса
        self.status_label = ttk.Label(control_frame, text="Готово", foreground="green")
        self.status_label.pack(side=tk.LEFT)
        
        # Кнопка закрытия справа
        btn_close = ttk.Button(
            control_frame,
            text="Закрыть",
            command=self.preview_window.destroy,
            width=10
        )
        btn_close.pack(side=tk.RIGHT)
        
        # Обработка закрытия окна
        self.preview_window.protocol("WM_DELETE_WINDOW", self.on_close_preview)
        
        # Загружаем предпросмотр
        self.update_preview()
        self.preview_window.bind("<Configure>", self.on_window_resize)
        
    def on_close_preview(self):
        """Обработчик закрытия окна предпросмотра"""
        if hasattr(self, 'preview_window') and self.preview_window:
            self.preview_window.destroy()
            self.preview_window = None
            self.preview_canvas = None