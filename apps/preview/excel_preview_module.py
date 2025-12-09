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
        self.preview_window = None
        
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
            
            # Открываем excel
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
            
            # Используем заданную область печати
            print_area = ws.Range(ws.PageSetup.PrintArea)
            
            # Прокручиваем к началу области
            excel.ActiveWindow.ScrollRow = print_area.Row
            excel.ActiveWindow.ScrollColumn = print_area.Column
            
            # Выделяем область
            print_area.Select()
            
            excel.ActiveWindow.Zoom = 90  # Фиксированный зум
            
            # Ждем отрисовки
            time.sleep(1.0)
            
            # Получаем окно excel
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
                wb.Close(SaveChanges=False)
                excel.Quit()
                pythoncom.CoUninitialize()
                return None
            
            excel_hwnd = excel_windows[0]
            win32gui.SetForegroundWindow(excel_hwnd)
            time.sleep(0.3)
            
            # Вычисляем координаты окна
            client_rect = win32gui.GetClientRect(excel_hwnd)      # Клиентская область (без рамок)
            screen_rect = win32gui.GetWindowRect(excel_hwnd)      # Экранные координаты
            
            # Рассчитываем ширину рамок окна
            frame_width = (screen_rect[2] - screen_rect[0] - client_rect[2]) // 2
            
            # Рассчитываем высоту заголовка и ленты Excel
            title_height = (screen_rect[3] - screen_rect[1] - client_rect[3]) - frame_width
            
            # Делаем скриншот области таблицы
            table_top = screen_rect[1] + title_height + 60
            table_bottom = table_top + 870  # небольшой отступ снизу

            # Примерная ширина области печати
            table_left = screen_rect[0] + frame_width + 20 # Небольшой отступ слева
            table_right = table_left + 565 # отступ справа

            screenshot = ImageGrab.grab(bbox=(
                table_left,
                table_top,
                table_right,
                table_bottom
            ))         

            # Закрываем excel
            wb.Close(SaveChanges=False)
            excel.Quit()
            pythoncom.CoUninitialize()

            return screenshot
                
        except Exception as e:
            print(f"Ошибка скриншота: {e}")
            import traceback
            traceback.print_exc()
            
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
    
    def get_preview_function(self):
        """Возвращает функцию для предпросмотра"""
        return self.show_preview_window

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
        
        # Создаем новое окно предпросмотра
        self.preview_window = tk.Toplevel(self.parent)
        self.preview_window.title("Предпросмотр Excel - Лист для коробки")
        
        # ======== РАЗМЕРЫ A4 (чуть больше) ========
        window_width = 650
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
        
        # Кнопка обновления
        btn_refresh = ttk.Button(
            control_frame,
            text="🔄 Обновить",
            command=lambda: [self.preview_window.destroy(), self.show_preview_window()],
            width=12
        )
        btn_refresh.pack(side=tk.LEFT, padx=(0, 10))
        
        # Метка статуса
        self.status_label = ttk.Label(control_frame, text="Загрузка...", foreground="blue")
        self.status_label.pack(side=tk.LEFT)
        
        # Кнопка закрытия справа
        btn_close = ttk.Button(
            control_frame,
            text="Закрыть",
            command=self.on_close_preview,
            width=10
        )
        btn_close.pack(side=tk.RIGHT)
        
        # Обработка закрытия окна
        self.preview_window.protocol("WM_DELETE_WINDOW", self.on_close_preview)
        
        # Привязка горячих клавиш
        self.preview_window.bind('<Escape>', lambda e: self.on_close_preview())
        self.preview_window.bind('<Return>', lambda e: self.reload_window())
        self.preview_window.bind('<F5>', lambda e: self.reload_window())
        
        # Загружаем предпросмотр
        self.update_preview()  # Загружаем данные
        self.preview_window.after(100, lambda: [
            self.preview_window.lift(), 
            self.preview_window.focus_force()
        ])     
        
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