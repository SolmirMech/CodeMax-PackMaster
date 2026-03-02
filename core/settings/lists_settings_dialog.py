import tkinter as tk
from tkinter import ttk
from .dialogs import (
    BoxEditorDialog,
    CustomersEditorDialog,
    SpecialClientsEditorDialog,
    TechnicalSpecificationsDialog,
    SleeveWeightsDialog,
    ShorteningRulesDialog,
    CuttersEditorDialog,
    PackersEditorDialog,
    TemplatesListDialog
)

# noinspection PyTypeChecker
class ListsSettingsDialog:
    """Диалог для редактируемых списков"""
    def __init__(self, parent_frame, config_manager=None, coordinator=None):
        self.parent_frame = parent_frame
        self.config_manager = config_manager
        self.coordinator = coordinator
        self.parent_manager = None
        self.last_status = ""
        self.status_var = tk.StringVar(value="")
        
        self.main_frame = None

    def set_parent_manager(self, manager):
        """Устанавливает ссылку на родительский менеджер"""
        self.parent_manager = manager
        
    def create_ui(self):
        """Создает UI в родительском фрейме"""
        self.main_frame = ttk.Frame(self.parent_frame)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        content_frame = ttk.Frame(self.main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)

        # Список коробок
        boxes_frame = ttk.LabelFrame(content_frame, text="🎯 Списки для редактирования", padding=10)
        boxes_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=10)    
        
        open_boxes_btn = ttk.Button(
            boxes_frame,
            text="📦 Список коробок", 
            command=self.open_box_editor,
            width=20
        )
        open_boxes_btn.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        # Кнопка для открытия окна редактирования клиентов
        open_customers_btn = ttk.Button(
            boxes_frame,
            text="📝 Без изготовителя",
            command=self.open_customers_editor
        )
        open_customers_btn.grid(row=1, column=0, padx=5, pady=5, sticky="w")

        # Кнопка для открытия окна особых клиентов
        open_special_btn = ttk.Button(
            boxes_frame,
            text="📋 Особые клиенты", 
            command=self.open_special_clients_editor
        )
        open_special_btn.grid(row=2, column=0, padx=5, pady=5, sticky="w")
        
        # Кнопка для открытия окна ТУ
        open_tu_btn = ttk.Button(
            boxes_frame,
            text="📑 Список ТУ", 
            command=self.open_tu_editor
        )
        open_tu_btn.grid(row=3, column=0, padx=5, pady=5, sticky="w")
        
        # Кнопка для редактирования поддонов
        open_pallets_btn = ttk.Button(
            boxes_frame,
            text="📦 Список поддонов", 
            command=lambda: self.open_box_editor(pallets_mode=True),
            width=20
        )
        open_pallets_btn.grid(row=4, column=0, padx=5, pady=5, sticky="w")
        
        # Кнопка для редактирования веса втулок
        open_sleeve_weights_btn = ttk.Button(
            boxes_frame,
            text="📊 Список втулок (вес)",
            command=self.open_sleeve_weights_editor,
            width=20
        )
        open_sleeve_weights_btn.grid(row=5, column=0, padx=5, pady=5, sticky="w")
        
        # Список сокращений
        open_shortening_btn = ttk.Button(
            boxes_frame,
            text="🔤 Список сокращений", 
            command=self.open_shortening_rules_editor,
            width=20
        )
        open_shortening_btn.grid(row=6, column=0, padx=5, pady=5, sticky="w")

        # Кнопка для редактирования резчиков
        open_cutters_btn = ttk.Button(
            boxes_frame,
            text="🔪 Список резчиков",
            command=self.open_cutters_editor,
            width=20
        )
        open_cutters_btn.grid(row=7, column=0, padx=5, pady=5, sticky="w")

        # Кнопка для редактирования упаковщиков
        open_packers_btn = ttk.Button(
            boxes_frame,
            text="📦 Список упаковщиков",
            command=self.open_packers_editor,
            width=20
        )
        open_packers_btn.grid(row=8, column=0, padx=5, pady=5, sticky="w")

        # Список шаблонов
        open_templates_btn = ttk.Button(
            boxes_frame,
            text="📄 Список шаблонов",
            command=self.open_templates_editor,
            width=20
        )
        open_templates_btn.grid(row=9, column=0, padx=5, pady=5, sticky="w")
        
        # Статус-строка
        status_label = ttk.Label(
            self.main_frame,
            textvariable=self.status_var,
            foreground="green",
            wraplength=350,
            font=("Arial", 12)
        )
        status_label.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
        
    def open_box_editor(self, pallets_mode=False):
        """Открывает редактор коробок или поддонов"""
        parent_window = self.parent_frame.winfo_toplevel()
        dialog = BoxEditorDialog(
            parent_window,
            pallets_mode=pallets_mode,
            config_manager=self.config_manager,
            coordinator=self.coordinator,
            status_var=self.status_var
        )
        dialog.show()
        
    def open_customers_editor(self):
        """Открывает окно редактирования списка клиентов без производителя"""
        parent_window = self.parent_frame.winfo_toplevel()
        dialog = CustomersEditorDialog(
            parent_window,
            config_manager=self.config_manager,
            coordinator=self.coordinator,
            status_var=self.status_var
        )
        dialog.show()

    def open_special_clients_editor(self):
        """Открывает окно редактирования списка особых клиентов"""
        parent_window = self.parent_frame.winfo_toplevel()
        dialog = SpecialClientsEditorDialog(
            parent_window,
            config_manager=self.config_manager,
            coordinator=self.coordinator,
            status_var=self.status_var
        )
        dialog.show()
        
    def open_tu_editor(self):
        """Открывает окно редактирования списка ТУ"""
        parent_window = self.parent_frame.winfo_toplevel()
        dialog = TechnicalSpecificationsDialog(
            parent_window,
            config_manager=self.config_manager,
            coordinator=self.coordinator,
            status_var=self.status_var
        )
        dialog.show()
        
    def open_sleeve_weights_editor(self):
        """Открывает окно редактирования веса втулок"""
        parent_window = self.parent_frame.winfo_toplevel()
        dialog = SleeveWeightsDialog(
            parent_window,
            config_manager=self.config_manager,
            coordinator=self.coordinator,
            status_var=self.status_var
        )
        dialog.show()
        
    def open_shortening_rules_editor(self):
        """Открывает редактор списка сокращений"""
        parent_window = self.parent_frame.winfo_toplevel()
        dialog = ShorteningRulesDialog(
            parent_window,
            config_manager=self.config_manager,
            coordinator=self.coordinator,
            status_var=self.status_var
        )
        dialog.show()

    def open_cutters_editor(self):
        """Открывает окно редактирования списка резчиков"""
        parent_window = self.parent_frame.winfo_toplevel()
        dialog = CuttersEditorDialog(
            parent_window,
            config_manager=self.config_manager,
            coordinator=self.coordinator,
            status_var=self.status_var
        )
        dialog.show()

    def open_packers_editor(self):
        """Открывает окно редактирования списка упаковщиков"""
        parent_window = self.parent_frame.winfo_toplevel()
        dialog = PackersEditorDialog(
            parent_window,
            config_manager=self.config_manager,
            coordinator=self.coordinator,
            status_var=self.status_var
        )
        dialog.show()

    def open_templates_editor(self):
        """Открывает окно редактирования списка шаблонов"""
        parent_window = self.parent_frame.winfo_toplevel()
        dialog = TemplatesListDialog(
            parent_window,
            config_manager=self.config_manager,
            coordinator=self.coordinator,
            status_var=self.status_var
        )
        dialog.show()
        
    def save_settings(self):
        """Сохраняет настройки этой вкладки"""
        # На данный момент этот метод ничего не делает,
        # так как редактирование списков происходит в отдельных окнах
        # которые сами сохраняют изменения
        self.last_status = "✅ Списки успешно сохранены!"
        return True
