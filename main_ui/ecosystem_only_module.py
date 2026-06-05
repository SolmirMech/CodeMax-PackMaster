from tkinter import ttk


# noinspection PyTypeChecker
class EcosystemOnlyModule(ttk.Frame):
    """Упрощённый модуль экспорта, отображающий только кнопку Экосистема"""

    def __init__(self, parent, preview_module, coordinator=None, config_manager=None):
        super().__init__(parent)
        self.export_status_label = None
        self.ecosystem_btn = None
        self.parent = parent
        self.preview_module = preview_module
        self.coordinator = coordinator
        self.config_manager = config_manager

        self.connected_roll_module = None
        self.ecosystem_window = None
        self.packing_list_window = None

        self.create_ui()

    def create_ui(self):
        """Создаёт интерфейс с одной кнопкой Экосистема"""
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # Секция с заголовком
        section_frame = ttk.LabelFrame(self, text="Экосистема", padding=10)
        section_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        section_frame.columnconfigure(0, weight=1)
        section_frame.rowconfigure(0, weight=1)

        # Кнопка Экосистема
        self.ecosystem_btn = ttk.Button(
            section_frame,
            text="🌿 Упаковочный лист",
            width=20,
            command=self.show_ecosystem_list,
            style="Accent.TButton"
        )
        self.ecosystem_btn.grid(row=0, column=0, pady=20)

        # Статус
        self.export_status_label = ttk.Label(
            self,
            text="",
            foreground="red",
            wraplength=330,
            font=("Arial", 14)
        )
        self.export_status_label.grid(row=1, column=0, pady=10)

    def set_roll_module(self, roll_module):
        """Устанавливает связь с модулем ролика"""
        self.connected_roll_module = roll_module

    def set_order_data_module(self, order_data_module):
        """Заглушка для совместимости с основным модулем экспорта"""
        pass

    def show_ecosystem_list(self):
        """Открывает окно упаковочного листа Экосистема"""
        from core.packing_list.packing_list_window import PackingListWindow

        # Всегда создаём новое окно
        self.packing_list_window = PackingListWindow(
            parent=self,
            config_manager=self.config_manager,
            coordinator=self.coordinator
        )

        # УВЕДОМЛЯЕМ КОНТРОЛЛЕР
        if self.connected_roll_module:
            self.connected_roll_module.packing_list_window = self.packing_list_window

        # ОТСЛЕЖИВАЕМ ЗАКРЫТИЕ ОКНА
        def on_window_close():
            if self.connected_roll_module:
                self.connected_roll_module.packing_list_window = None
            # Вызываем оригинальный метод закрытия
            self.packing_list_window.on_close()
            self.packing_list_window = None

        self.packing_list_window.window.protocol("WM_DELETE_WINDOW", on_window_close)

        # Если есть данные из XML — заполняем шапку
        if self.connected_roll_module and hasattr(self.connected_roll_module, 'ecosystem_xml_data'):
            data = self.connected_roll_module.ecosystem_xml_data
            if data and hasattr(self.packing_list_window, 'fill_from_xml'):
                self.packing_list_window.fill_from_xml(data)

    def set_status(self, message, color="green"):
        """Универсальный метод установки статуса"""
        if hasattr(self, 'export_status_label'):
            self.export_status_label.config(text=message, foreground=color)
            self.after(5000, lambda: self.export_status_label.config(text=""))