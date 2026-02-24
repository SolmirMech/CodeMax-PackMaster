import tkinter as tk
from tkinter import ttk


# noinspection PyTypeChecker
class SleeveWeightsDialog:
    """Диалог редактирования веса втулок по диаметру и ширине"""

    # Статические данные по умолчанию
    DEFAULT_SLEEVE_WEIGHTS = {
        "76": {
            "50": 100,
            "75": 150,
            "90": 150,
            "100": 200,
            "110": 200,
            "125": 250,
            "150": 300,
            "175": 300,
            "200": 350,
            "225": 400,
            "250": 450,
            "275": 500,
            "290": 550,
            "300": 550,
            "325": 600,
            "350": 650,
            "375": 700,
            "400": 750,
            "425": 800,
            "450": 850,
            "475": 900,
            "500": 950,
            "835": 1550
        },
        "152": {
            "50": 200,
            "75": 250,
            "90": 300,
            "100": 350,
            "110": 400,
            "125": 450
        }
    }

    def __init__(self, parent, config_manager=None, coordinator=None, status_var=None):
        self.parent = parent
        self.config_manager = config_manager
        self.coordinator = coordinator
        self.status_var = status_var
        self.window = None

        # Списки для хранения полей ввода
        self.diameter_76_width_entries = []
        self.diameter_76_weight_entries = []
        self.diameter_152_width_entries = []
        self.diameter_152_weight_entries = []

        # Храним ссылки на фреймы для добавления новых строк
        self.diameter_76_scrollable_frame = None
        self.diameter_152_scrollable_frame = None

    def show(self):
        """Показывает диалог редактирования веса втулок"""
        if self.window and self.window.winfo_exists():
            self.window.lift()
            return

        self.window = tk.Toplevel(self.parent)
        self.window.title("Вес втулок по диаметру и ширине")
        self.window.geometry("900x650")  # Увеличил высоту для кнопок
        self.window.grab_set()

        # Центрирование окна
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"+{x}+{y}")
        self.window.bind("<Escape>", lambda e: self.window.destroy())

        # Основной фрейм
        main_frame = ttk.Frame(self.window, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Фрейм для двух разделов
        sections_frame = ttk.Frame(main_frame)
        sections_frame.pack(fill=tk.BOTH, expand=True)

        # Раздел для диаметра 76 мм (левый)
        diameter_76_container = ttk.LabelFrame(
            sections_frame,
            text="Вес втулок для диаметра 76 мм",
            padding=10
        )
        diameter_76_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        # Раздел для диаметра 152 мм (правый)
        diameter_152_container = ttk.LabelFrame(
            sections_frame,
            text="Вес втулок для диаметра 152 мм",
            padding=10
        )
        diameter_152_container.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

        # Создаем содержимое для обоих разделов
        self._create_diameter_section(diameter_76_container, "76")
        self._create_diameter_section(diameter_152_container, "152")

        # Фрейм для кнопок добавления строк под каждым разделом
        add_buttons_frame = ttk.Frame(main_frame)
        add_buttons_frame.pack(fill=tk.X, pady=(10, 5))

        # Кнопка добавления строки для диаметра 76 мм
        add_76_btn = ttk.Button(
            add_buttons_frame,
            text="➕ Добавить строку (76 мм)",
            command=lambda: self._create_sleeve_row(self.diameter_76_scrollable_frame, "76", "", "")
        )
        add_76_btn.pack(side=tk.LEFT, padx=(50, 10))

        # Кнопка добавления строки для диаметра 152 мм
        add_152_btn = ttk.Button(
            add_buttons_frame,
            text="➕ Добавить строку (152 мм)",
            command=lambda: self._create_sleeve_row(self.diameter_152_scrollable_frame, "152", "", "")
        )
        add_152_btn.pack(side=tk.RIGHT, padx=(10, 50))

        # Кнопки управления
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=10)

        ttk.Button(
            button_frame,
            text="💾 Сохранить",
            command=self.save_sleeve_weights
        ).pack(side=tk.LEFT, padx=20)

        # Загружаем текущие данные
        self.load_sleeve_weights()

        # Добавляем по одной пустой строке в каждый раздел если нет данных
        if not self.diameter_76_width_entries:
            self._create_sleeve_row(self.diameter_76_scrollable_frame, "76", "", "")
        if not self.diameter_152_width_entries:
            self._create_sleeve_row(self.diameter_152_scrollable_frame, "152", "", "")

        self.window.bind("<Return>", lambda e: self.save_sleeve_weights())

    def _create_diameter_section(self, parent_frame, diameter):
        """Создает раздел для одного диаметра втулок"""
        # Фрейм для заголовков
        header_frame = ttk.Frame(parent_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(
            header_frame,
            text="Ширина ручья, мм",
            font=("Arial", 10, "bold"),
            width=18
        ).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(
            header_frame,
            text="Вес втулки, г",
            font=("Arial", 10, "bold"),
            width=18
        ).pack(side=tk.LEFT)

        # Фрейм для прокрутки
        container = ttk.Frame(parent_frame)
        container.pack(fill=tk.BOTH, expand=True)

        # Canvas и scrollbar
        canvas = tk.Canvas(container)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Сохраняем ссылку на scrollable_frame для добавления новых строк
        if diameter == "76":
            self.diameter_76_scrollable_frame = scrollable_frame
        else:
            self.diameter_152_scrollable_frame = scrollable_frame

    def _create_sleeve_row(self, parent_frame, diameter, width, weight):
        """Создает строку с полями ввода для веса втулки"""
        row_frame = ttk.Frame(parent_frame)
        row_frame.pack(fill=tk.X, pady=2)

        # Поле для ширины ручья
        width_entry = ttk.Entry(row_frame, width=15)
        width_entry.insert(0, width)
        width_entry.pack(side=tk.LEFT, padx=(0, 10))

        # Поле для веса
        weight_entry = ttk.Entry(row_frame, width=15)
        weight_entry.insert(0, weight)
        weight_entry.pack(side=tk.LEFT, padx=(35, 10))

        # Кнопка удаления
        ttk.Button(
            row_frame,
            text="×",
            width=2,
            command=lambda: self._remove_sleeve_row(
                row_frame, width_entry, weight_entry, diameter
            )
        ).pack(side=tk.RIGHT)

        # Добавляем в соответствующие списки
        if diameter == "76":
            self.diameter_76_width_entries.append(width_entry)
            self.diameter_76_weight_entries.append(weight_entry)
        else:
            self.diameter_152_width_entries.append(width_entry)
            self.diameter_152_weight_entries.append(weight_entry)

    def _remove_sleeve_row(self, row_frame, width_entry, weight_entry, diameter):
        """Удаляет строку с полями ввода"""
        if diameter == "76":
            if len(self.diameter_76_width_entries) > 1:
                row_frame.destroy()
                self.diameter_76_width_entries.remove(width_entry)
                self.diameter_76_weight_entries.remove(weight_entry)
        else:
            if len(self.diameter_152_width_entries) > 1:
                row_frame.destroy()
                self.diameter_152_width_entries.remove(width_entry)
                self.diameter_152_weight_entries.remove(weight_entry)

    def load_sleeve_weights(self):
        """Загружает текущие веса втулок из настроек, добавляет значения по умолчанию если нет данных"""
        try:
            settings = self.config_manager.load_json_settings("shared_utils.json")
            sleeve_weights = settings.get("sleeve_weights")

            # Если данных нет совсем - используем значения по умолчанию и сохраняем
            if sleeve_weights is None:
                settings["sleeve_weights"] = self.DEFAULT_SLEEVE_WEIGHTS
                self.config_manager.save_json_settings("shared_utils.json", settings)
                sleeve_weights = self.DEFAULT_SLEEVE_WEIGHTS

            # Очищаем существующие записи
            self.diameter_76_width_entries = []
            self.diameter_76_weight_entries = []
            self.diameter_152_width_entries = []
            self.diameter_152_weight_entries = []

            # Очищаем существующие виджеты в scrollable_frame
            if self.diameter_76_scrollable_frame:
                for widget in self.diameter_76_scrollable_frame.winfo_children():
                    widget.destroy()
            if self.diameter_152_scrollable_frame:
                for widget in self.diameter_152_scrollable_frame.winfo_children():
                    widget.destroy()

            # Загружаем для диаметра 76 мм
            diameter_76 = sleeve_weights.get("76", {})
            for width, weight in diameter_76.items():
                self._create_sleeve_row(self.diameter_76_scrollable_frame, "76", width, str(weight))

            # Загружаем для диаметра 152 мм
            diameter_152 = sleeve_weights.get("152", {})
            for width, weight in diameter_152.items():
                self._create_sleeve_row(self.diameter_152_scrollable_frame, "152", width, str(weight))

        except Exception as e:
            print(f"Ошибка загрузки веса втулок: {e}")

    def save_sleeve_weights(self):
        """Сохраняет веса втулок в shared_utils.json"""
        try:
            # Собираем данные для диаметра 76 мм
            diameter_76_data = {}
            for width_entry, weight_entry in zip(
                    self.diameter_76_width_entries,
                    self.diameter_76_weight_entries
            ):
                width = width_entry.get().strip()
                weight_str = weight_entry.get().strip()

                if width and weight_str:
                    try:
                        weight = int(weight_str)
                        diameter_76_data[width] = weight
                    except ValueError:
                        continue

            # Собираем данные для диаметра 152 мм
            diameter_152_data = {}
            for width_entry, weight_entry in zip(
                    self.diameter_152_width_entries,
                    self.diameter_152_weight_entries
            ):
                width = width_entry.get().strip()
                weight_str = weight_entry.get().strip()

                if width and weight_str:
                    try:
                        weight = int(weight_str)
                        diameter_152_data[width] = weight
                    except ValueError:
                        continue

            # Формируем структуру данных
            sleeve_weights = {
                "76": diameter_76_data,
                "152": diameter_152_data
            }

            # Загружаем текущие настройки
            settings = self.config_manager.load_json_settings("shared_utils.json")
            settings["sleeve_weights"] = sleeve_weights

            # Сохраняем обратно
            if self.config_manager.save_json_settings("shared_utils.json", settings):
                # Уведомляем координатора об изменении
                if self.coordinator:
                    self.coordinator.notify_list_changed("sleeve_weights")

                if self.status_var:
                    self.status_var.set("✅ Вес втулок успешно сохранен!")
                self.window.destroy()
            else:
                if self.status_var:
                    self.status_var.set("❌ Не удалось сохранить вес втулок")

        except Exception as e:
            if self.status_var:
                self.status_var.set(f"❌ Ошибка сохранения веса втулок: {str(e)}")