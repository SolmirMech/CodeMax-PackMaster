import tkinter as tk
from tkinter import ttk


# noinspection PyTypeChecker
class BoxEditorDialog:
    """Диалог редактирования списка коробок"""

    def __init__(self, parent, pallets_mode=False, config_manager=None, coordinator=None, status_var=None):
        self.parent = parent
        self.pallets_mode = pallets_mode
        self.config_manager = config_manager
        self.coordinator = coordinator
        self.status_var = status_var
        self.window = None
        self.box_size_entries = []
        self.box_height_entries = []  # Новый список для высот
        self.box_weight_entries = []

    def show(self):
        if self.window and self.window.winfo_exists():
            self.window.lift()
            return

        self.window = tk.Toplevel(self.parent)
        self.window.title("Редактирование списка поддонов" if self.pallets_mode else "Редактирование списка коробок")
        self.window.geometry("600x600" if not self.pallets_mode else "430x600")  # Шире для коробок
        self.window.grab_set()

        # Центрирование окна
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"+{x}+{y}")
        self.window.bind("<Escape>", lambda e: self.window.destroy())

        frame = ttk.Frame(self.window, padding=10)
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
        if self.pallets_mode:
            current_boxes = self.get_current_boxes()
            current_heights = {}
        else:
            current_boxes, current_heights = self.get_current_boxes()

        # Создаем заголовки
        header_frame = ttk.Frame(scrollable_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))

        if not self.pallets_mode:
            # Для коробок: Название, Высота, Вес
            ttk.Label(header_frame, text="Название", font=("Arial", 12, "bold")).pack(side=tk.LEFT, padx=(0, 30))
            ttk.Label(header_frame, text="Высота (мм)", font=("Arial", 12, "bold")).pack(side=tk.LEFT, padx=(0, 30))
            ttk.Label(header_frame, text="Вес (грамм)", font=("Arial", 12, "bold")).pack(side=tk.LEFT)
        else:
            # Для поддонов: Название, Вес
            ttk.Label(header_frame, text="Название", font=("Arial", 12, "bold")).pack(side=tk.LEFT, padx=(0, 30))
            ttk.Label(header_frame, text="Вес (грамм)", font=("Arial", 12, "bold")).pack(side=tk.LEFT, padx=(85, 15))

        # Создаем поля ввода
        self.box_size_entries = []
        self.box_height_entries = []
        self.box_weight_entries = []

        for size, weight in current_boxes.items():  # Исправлено: используем weight из items()
            if self.pallets_mode:
                # Для поддонов: только вес
                self._create_box_row(scrollable_frame, size, "", weight)
            else:
                # Для коробок: высота и вес
                height = current_heights.get(size, "")
                self._create_box_row(scrollable_frame, size, height, weight)

        # Добавляем пустую строку
        self._create_box_row(scrollable_frame, "", "", "")

        # Кнопки управления
        button_frame = ttk.Frame(frame)
        button_frame.pack(pady=10)

        ttk.Button(button_frame, text="💾 Сохранить", command=self.save_boxes).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="➕ Добавить строку",
                   command=lambda: self._create_box_row(scrollable_frame, "", "", "")).pack(side=tk.LEFT, padx=(5, 30))

        self.window.bind("<Return>", lambda e: self.save_boxes())

    def _create_box_row(self, parent, size, height, weight):
        """Создает строку с полями ввода для коробки"""
        row_frame = ttk.Frame(parent)
        row_frame.pack(fill=tk.X, pady=2)

        # Поле для размеров
        size_entry = ttk.Entry(row_frame, width=25 if not self.pallets_mode else 30)
        size_entry.insert(0, size)
        size_entry.pack(side=tk.LEFT, padx=(0, 10))
        self.box_size_entries.append(size_entry)

        # Поле для высоты (только для коробок)
        if not self.pallets_mode:
            height_entry = ttk.Entry(row_frame, width=15)
            height_entry.insert(0, str(height))
            height_entry.pack(side=tk.LEFT, padx=(0, 10))
            self.box_height_entries.append(height_entry)

        # Поле для веса
        weight_entry = ttk.Entry(row_frame, width=15 if not self.pallets_mode else 20)
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
            if not self.pallets_mode and hasattr(self, 'box_height_entries'):
                # Находим и удаляем соответствующий height_entry
                index = self.box_size_entries.index(size_entry) if size_entry in self.box_size_entries else -1
                if 0 <= index < len(self.box_height_entries):
                    self.box_height_entries.pop(index)
            self.box_weight_entries.remove(weight_entry)

    def get_current_boxes(self):
        """Возвращает текущий список коробок ИЛИ поддонов"""
        try:
            settings = self.config_manager.load_json_settings("shared_utils.json")
            if self.pallets_mode:
                return settings.get("weight_pallet", {})  # для поддонов
            else:
                boxes_data = settings.get("weight_box", {})
                # Загружаем высоты из отдельного ключа, если есть
                box_heights = settings.get("box_heights", {})
                return boxes_data, box_heights  # Возвращаем два словаря
        except:
            return {}, {} if not self.pallets_mode else {}

    def save_boxes(self):
        """Сохраняет список коробок ИЛИ поддонов в shared_utils.json"""
        try:
            new_boxes = {}
            new_heights = {}  # Новый словарь для высот

            for i, (size_entry, weight_entry) in enumerate(zip(self.box_size_entries, self.box_weight_entries)):
                size = size_entry.get().strip()
                weight_str = weight_entry.get().strip()

                if size and weight_str:
                    try:
                        weight = int(weight_str)
                        if self.pallets_mode:
                            # Для поддонов: просто вес
                            new_boxes[size] = weight
                        else:
                            # Для коробок: вес и отдельно высота
                            new_boxes[size] = weight
                            if i < len(self.box_height_entries):
                                height_str = self.box_height_entries[i].get().strip()
                                if height_str:
                                    new_heights[size] = int(height_str)
                    except ValueError:
                        continue

            # Загружаем текущие настройки и обновляем
            settings = self.config_manager.load_json_settings("shared_utils.json")

            if self.pallets_mode:
                settings["weight_pallet"] = new_boxes
                key_for_update = "weight_pallet"
            else:
                settings["weight_box"] = new_boxes
                if new_heights:
                    settings["box_heights"] = new_heights
                key_for_update = "weight_box"

            if self.config_manager.save_json_settings("shared_utils.json", settings):
                # Уведомляем координатора об изменении списка
                if self.coordinator:
                    self.coordinator.notify_list_changed(key_for_update)
                    if not self.pallets_mode:
                        self.coordinator.notify_list_changed('box_heights')

                # Статус
                item_name = "поддонов" if self.pallets_mode else "коробок"
                if self.status_var:
                    self.status_var.set(f"✅ Список {item_name} успешно обновлен!")

                self.window.destroy()
            else:
                if self.status_var:
                    self.status_var.set("❌ Не удалось сохранить список")

        except Exception as e:
            if self.status_var:
                self.status_var.set(f"❌ Ошибка сохранения: {str(e)}")