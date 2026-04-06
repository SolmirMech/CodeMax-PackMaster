# main_ui/order_data/ui_builder.py
"""Модуль построения интерфейса и управления видимостью элементов"""

import tkinter as tk
from tkinter import ttk
from datetime import datetime
import subprocess


# noinspection PyTypeChecker
class OrderUIBuilder:
    """Создание интерфейса и управление видимостью полей"""

    def __init__(self, parent, controller, config_manager, coordinator):
        """
        Args:
            parent: родительский фрейм
            controller: OrderDataController (доступ к переменным)
            config_manager: ConfigManager
            coordinator: SettingsCoordinator
        """
        self.parent = parent
        self.controller = controller
        self.config_manager = config_manager
        self.coordinator = coordinator

    def create_ui(self):
        """Создает интерфейс для ввода данных заказа"""
        frame = ttk.Frame(self.parent, padding=3)
        frame.pack(fill=tk.BOTH, expand=True)

        # Основной контейнер для данных
        data_frame = ttk.LabelFrame(frame, text="Данные для этикетки", padding=5)
        data_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        # Изготовитель и тип продукта
        manufacturer_frame = ttk.Frame(data_frame)
        manufacturer_frame.grid(row=0, column=0, columnspan=2, sticky="w", pady=2)

        ttk.Label(manufacturer_frame, text="Изготовитель:").grid(row=0, column=0, sticky="w", padx=(0, 5), pady=2)
        self.controller.manufacturer_combo = ttk.Combobox(
            manufacturer_frame,
            textvariable=self.controller.manufacturer_var,
            state="readonly",
            width=20
        )
        self.controller.manufacturer_combo.grid(row=0, column=0, sticky="w", padx=(150, 10), pady=2)
        self.controller.manufacturer_combo.bind('<<ComboboxSelected>>', self.controller.on_manufacturer_selected)

        ttk.Label(manufacturer_frame, text="ТУ:").grid(row=0, column=0, sticky="w", padx=(305, 5), pady=2)
        self.controller.product_combo = ttk.Combobox(
            manufacturer_frame,
            textvariable=self.controller.product_type_var,
            state="readonly",
            width=25
        )
        self.controller.product_combo.grid(row=0, column=0, padx=(345, 5), sticky="w", pady=2)
        self.controller.product_combo.bind('<<ComboboxSelected>>', self.controller.on_product_selected)

        # "Без изготовителя"
        ttk.Checkbutton(
            manufacturer_frame,
            text="Без изготовителя",
            variable=self.controller.show_manufacturer_var
        ).grid(row=1, column=0, sticky="w", padx=5, pady=5)

        # Упаковщик
        ttk.Label(manufacturer_frame, text="Упаковка").grid(
            row=1, column=0, sticky="w", padx=(200, 5), pady=5
        )

        packers = self.config_manager.get_packers()
        default_packer = packers[0] if packers else ""
        self.controller.packer_var = tk.StringVar(value=default_packer)

        self.controller.packer_combo = ttk.Combobox(
            manufacturer_frame,
            textvariable=self.controller.packer_var,
            values=packers,
            state="readonly",
            width=15
        )
        self.controller.packer_combo.grid(row=1, column=0, padx=(295, 5), pady=5, sticky="w")

        # Резчик
        self.controller.cutter_label = ttk.Label(manufacturer_frame, text="Резка")
        self.controller.cutter_label.grid(row=1, column=0, sticky="w", padx=(415, 5), pady=5)

        cutters = self.config_manager.get_cutters()
        default_cutter = self.config_manager.get_default_cutter()
        self.controller.cutter_var = tk.StringVar(value=default_cutter)

        self.controller.cutter_combo = ttk.Combobox(
            manufacturer_frame,
            textvariable=self.controller.cutter_var,
            values=cutters,
            state="readonly",
            width=15
        )
        self.controller.cutter_combo.grid(row=1, column=0, padx=(480, 5), pady=5, sticky="w")

        # Заказчик
        ttk.Label(data_frame, text="Заказчик:").grid(row=1, column=0, sticky="w", pady=5)
        customer_entry = ttk.Entry(data_frame, textvariable=self.controller.customer_var, font=("Arial", 12), width=35)
        customer_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        self.add_context_menu(customer_entry)
        customer_entry.bind("<Control-KeyPress>", self.control_key_handler)
        self.controller.customer_var.trace_add("write", self.controller.on_customer_changed)

        # Изделие
        left_frame = ttk.Frame(data_frame)
        left_frame.grid(row=2, column=0, sticky="nw", pady=5)

        ttk.Label(left_frame, text="Изделие:").grid(row=0, column=0, sticky="w")

        # Галочка "Сократить текст"
        self.controller.shorten_checkbutton = ttk.Checkbutton(
            left_frame,
            text="Сократить текст",
            variable=self.controller.shorten_text_var,
            command=self.controller.on_shorten_text_changed
        )
        self.controller.shorten_checkbutton.grid(row=1, column=0, sticky="w", pady=(2, 0))

        # Галочка Росинка
        self.controller.rosinka_checkbutton = ttk.Checkbutton(
            left_frame,
            text="Росинка",
            variable=self.controller.rosinka_var,
            command=self._on_rosinka_toggled
        )
        self.controller.rosinka_checkbutton.grid(row=2, column=0, sticky="w", pady=(3, 0))
        self.controller.rosinka_checkbutton.grid_remove()  # изначально скрыта

        # Многострочное текстовое поле
        self.controller.product_text = tk.Text(data_frame, width=35, height=4, font=("Arial", 12))
        self.controller.product_text.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        self.add_context_menu_to_text(self.controller.product_text)
        self.controller.product_text.bind("<Control-KeyPress>", self.control_key_handler_text)
        self.controller.product_text.bind("<Return>", self.controller.search_in_product_text)

        # Подложка Росинки
        self.controller.podlo_label = ttk.Label(data_frame, text="Подложка:")
        self.controller.podlo_entry = ttk.Entry(data_frame, textvariable=self.controller.ros_podlo_var, width=35)
        self.controller.podlo_label.grid(row=3, column=1, sticky="w", pady=3)
        self.controller.podlo_entry.grid(row=3, column=1, padx=(115, 0), pady=3, sticky="w")
        self.controller.podlo_entry.bind("<Control-KeyPress>", self.control_key_handler)
        self.controller.podlo_label.grid_remove()
        self.controller.podlo_entry.grid_remove()

        # Номер заказа
        ttk.Label(data_frame, text="№ заказа:").grid(row=4, column=0, sticky="w", pady=(5, 5))
        
        entry_prefix = ttk.Entry(data_frame, textvariable=self.controller.order_prefix, width=4)
        entry_prefix.grid(row=4, column=1, padx=(5, 0), pady=(5, 5), sticky="w")

        self.controller.order_entry = ttk.Entry(data_frame, textvariable=self.controller.order_number, width=7)
        self.controller.order_entry.grid(row=4, column=1, padx=(42, 0), pady=(5, 5), sticky="w")
        self.controller.order_entry.bind("<Return>", self.controller.on_order_enter_pressed)
        self.controller.order_entry.bind("<Down>", lambda e: self.controller.quantity_entry.focus_set())
        self.controller.order_entry.bind("<FocusIn>", lambda e: self.controller.order_entry.select_range(0, tk.END))

        # Комбобокс выбора заказа (скрыт)
        self.controller.order_combobox = ttk.Combobox(
            data_frame,
            width=7,
            state="readonly"
        )
        self.controller.order_combobox.grid(row=4, column=1, padx=(42, 0), pady=(5, 5), sticky="w")
        self.controller.order_combobox.bind("<<ComboboxSelected>>", self.controller.on_order_selected)
        self.controller.order_combobox.grid_remove()

        self.controller.entry_suffix = ttk.Entry(data_frame, textvariable=self.controller.order_suffix, width=6)
        self.controller.entry_suffix.grid(row=4, column=1, padx=(95, 0), pady=(5, 5), sticky="w")

        # Обновление даты
        date_update_label = tk.Label(
            data_frame,
            text="🔄",
            font=("Arial", 18),
            cursor="hand2"
        )
        date_update_label.grid(row=4, column=1, sticky="w", padx=(200, 0), pady=(5, 5))
        date_update_label.bind("<Button-1>", lambda e: self.update_date_field())

        # Дата
        self.controller.date_entry = ttk.Entry(data_frame, textvariable=self.controller.date_var, width=12)
        self.controller.date_entry.grid(row=4, column=1, padx=(240, 0), pady=(5, 5), sticky="w")

        # Количество этикеток/роликов
        ttk.Label(data_frame, text="Кол-во этикеток/роликов:", foreground="green").grid(
            row=5, column=0, sticky="w", pady=2
        )
        
        self.controller.quantity_entry = ttk.Entry(data_frame, textvariable=self.controller.quantity_var, width=15)
        self.controller.quantity_entry.grid(row=5, column=1, padx=5, pady=2, sticky="w")
        self.controller.quantity_entry.bind("<Up>", lambda e: self.controller.order_entry.focus_set())
        self.controller.quantity_entry.bind("<FocusIn>", lambda e: self.controller.quantity_entry.select_range(0, tk.END))

        rolls_entry = ttk.Entry(data_frame, textvariable=self.controller.rolls_count_var, width=15)
        rolls_entry.grid(row=5, column=1, padx=(115, 0), pady=2, sticky="w")
        rolls_entry.bind("<KeyRelease>", self.controller.calculate_total_quantity)

        # Галочка "Вес"
        self.controller.weight_checkbutton = ttk.Checkbutton(
            data_frame,
            text="Вес",
            variable=self.controller.show_weight_var,
            command=self.toggle_weight_visibility
        )
        self.controller.weight_checkbutton.grid(row=5, column=1, padx=(240, 10), pady=2, sticky="w")

        # Вес ролика
        self.controller.weight_label = ttk.Label(data_frame, text="Вес ролика брутто, кг:")
        self.controller.weight_label.grid(row=6, column=0, sticky="w", pady=3)
        self.controller.gross_entry = ttk.Entry(data_frame, textvariable=self.controller.gross_weight_kg_var, width=15)
        self.controller.gross_entry.grid(row=6, column=1, padx=(5, 0), pady=3, sticky="w")

        # Вес втулки
        self.controller.sleeve_label = ttk.Label(data_frame, text="Вес втулки, г:")
        self.controller.sleeve_label.grid(row=6, column=1, sticky="w", padx=(115, 0), pady=3)
        self.controller.sleeve_entry = ttk.Entry(data_frame, textvariable=self.controller.sleeve_weight_var, width=7)
        self.controller.sleeve_entry.grid(row=6, column=1, padx=(265, 0), pady=3, sticky="w")

        # Длина ролика
        self.controller.roll_length_label = ttk.Label(data_frame, text="Длина ролика, м:")
        self.controller.roll_length_label.grid(row=7, column=0, sticky="w", pady=2)
        self.controller.roll_length_entry = ttk.Entry(data_frame, textvariable=self.controller.roll_length, width=8)
        self.controller.roll_length_entry.grid(row=7, column=0, padx=(183, 0), pady=2, sticky="w")

        # № съёма
        self.controller.batch_label = ttk.Label(data_frame, text="№ съёма:")
        self.controller.batch_label.grid(row=7, column=1, sticky="w", pady=3)
        self.controller.batch_entry = ttk.Entry(data_frame, textvariable=self.controller.batch_num_var, width=6)
        self.controller.batch_entry.grid(row=7, column=1, padx=(115, 0), pady=3, sticky="w")

        # № ролика
        self.controller.roll_label = ttk.Label(data_frame, text="№ ролика:")
        self.controller.roll_label.grid(row=7, column=1, sticky="w", padx=(160, 0), pady=3)
        self.controller.roll_entry = ttk.Entry(data_frame, textvariable=self.controller.roll_num_var, width=7)
        self.controller.roll_entry.grid(row=7, column=1, padx=(265, 0), pady=3, sticky="w")

        # Ширина ручья
        self.controller.stream_width_label = ttk.Label(data_frame, text="Ширина ручья, мм:")
        self.controller.stream_width_label.grid(row=8, column=0, sticky="w", pady=2)
        self.controller.stream_width_entry = ttk.Entry(data_frame, textvariable=self.controller.stream_width_var, width=8)
        self.controller.stream_width_entry.grid(row=8, column=0, padx=(183, 0), pady=2, sticky="w")

        # Длина этикетки
        self.controller.label_length_label = ttk.Label(data_frame, text="Длина этикетки, мм:")
        self.controller.label_length_label.grid(row=8, column=1, sticky="w", pady=2)
        self.controller.label_length_entry = ttk.Entry(data_frame, textvariable=self.controller.label_length_mm, width=7)
        self.controller.label_length_entry.grid(row=8, column=1, padx=(265, 0), pady=2, sticky="w")

        # Схема намотки
        self.controller.winding_label = ttk.Label(data_frame, text="Схема намотки:")
        self.controller.winding_label.grid(row=9, column=0, sticky="w", pady=3)
        self.controller.winding_entry = ttk.Entry(data_frame, textvariable=self.controller.winding_scheme_var, width=8)
        self.controller.winding_entry.grid(row=9, column=0, padx=(183, 0), pady=3, sticky="w")

        # Диаметр втулки
        self.controller.diameter_label = ttk.Label(data_frame, text="Диаметр втулки, мм:")
        self.controller.diameter_label.grid(row=9, column=1, sticky="w", pady=3)
        self.controller.diameter_entry = ttk.Entry(data_frame, textvariable=self.controller.sleeve_diameter_var, width=7)
        self.controller.diameter_entry.grid(row=9, column=1, padx=(265, 0), pady=3, sticky="w")

        # Кол-во ручьев
        self.controller.streams_label = ttk.Label(data_frame, text="Кол-во ручьев:")
        self.controller.streams_label.grid(row=10, column=0, sticky="w", pady=3)
        self.controller.streams_entry = ttk.Entry(data_frame, textvariable=self.controller.streams_var, width=8)
        self.controller.streams_entry.grid(row=10, column=0, padx=(183, 0), pady=3, sticky="w")

        # Дата эмиссии
        self.controller.emission_label = ttk.Label(data_frame, text="Дата эмиссии:")
        self.controller.emission_label.grid(row=10, column=1, sticky="w", pady=3)
        self.controller.emission_entry = ttk.Entry(data_frame, textvariable=self.controller.date_emission_var, width=10)
        self.controller.emission_entry.grid(row=10, column=1, padx=(150, 0), pady=3, sticky="w")
        self.controller.emission_entry.bind("<KeyRelease>", self._on_date_emission_key_release)

        # Привязываем обработчики
        self.controller.order_prefix.trace_add("write", self.controller.on_order_number_changed)
        self.controller.roll_length.trace_add("write", self.controller.calculate_quantity_from_length)
        self.controller.label_length_mm.trace_add("write", self.controller.calculate_quantity_from_length)
        self.controller.stream_width_var.trace_add("write", self.controller.update_sleeve_weight_from_settings)
        self.controller.sleeve_diameter_var.trace_add("write", self.controller.update_sleeve_weight_from_settings)

        # Начальная видимость
        self.toggle_weight_visibility()
        self.update_elements_visibility()
        self.update_cutter_visibility()

    def _on_date_emission_key_release(self, event=None):
        """Автоматически расставляет точки при вводе даты эмиссии"""
        if event is None or event.widget != self.controller.emission_entry:
            return

        current_text = self.controller.emission_entry.get()
        cursor_pos = self.controller.emission_entry.index(tk.INSERT)

        digits_only = current_text.replace('.', '')
        digits_only = ''.join(filter(str.isdigit, digits_only))

        if len(digits_only) > 8:
            digits_only = digits_only[:8]
            if cursor_pos > len(digits_only):
                cursor_pos = len(digits_only)

        formatted = ""
        if len(digits_only) > 0:
            formatted = digits_only[:2]
            if len(digits_only) >= 3:
                formatted += "." + digits_only[2:4]
                if len(digits_only) >= 5:
                    formatted += "." + digits_only[4:]

        if formatted != current_text:
            self.controller.emission_entry.delete(0, tk.END)
            self.controller.emission_entry.insert(0, formatted)

            if cursor_pos > 0:
                dots_before = formatted[:cursor_pos].count('.') - current_text[:cursor_pos].count('.')
                new_pos = cursor_pos + dots_before
                new_pos = min(new_pos, len(formatted))
                self.controller.emission_entry.icursor(new_pos)

    def _on_rosinka_toggled(self):
        """При включении/выключении галочки Росинка"""
        current_prefix = self.controller.order_prefix.get()
        current_suffix = self.controller.order_suffix.get()

        if self.controller.rosinka_var.get():
            self.controller.podlo_label.grid()
            self.controller.podlo_entry.grid()
            self.controller.extract_label_size_from_db()
        else:
            self.controller.podlo_label.grid_remove()
            self.controller.podlo_entry.grid_remove()
            self.controller.ros_size_var.set("")

        if self.coordinator:
            self.coordinator.notify_list_changed("rosinka")

        self.controller.order_prefix.set(current_prefix)
        self.controller.order_suffix.set(current_suffix)

        if self.controller.preview_module is not None:
            self.controller.preview_module.update_from_connected_roll_module()

    def update_date_field(self):
        """Обновляет поле даты на текущую дату"""
        try:
            if hasattr(self.coordinator, 'notify_list_changed'):
                self.coordinator.notify_list_changed("update_date_request")

            try:
                result = subprocess.run(
                    ["powershell", "-Command", "Get-Date -Format 'dd.MM.yyyy'"],
                    capture_output=True,
                    text=True,
                    shell=True,
                    timeout=2,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                if result.returncode == 0:
                    current_date = result.stdout.strip()
                    if current_date and len(current_date) == 10:
                        self._show_date_message(f"Дата через PowerShell: {current_date}")
                        self.controller.date_var.set(current_date)
                        return
            except Exception:
                pass

            try:
                result = subprocess.run(
                    ['cmd', '/c', 'wmic os get localdatetime /value'],
                    capture_output=True,
                    text=True,
                    shell=True,
                    timeout=2,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                output = result.stdout
                if 'LocalDateTime' in output:
                    for line in output.split('\n'):
                        if line.startswith('LocalDateTime='):
                            dt_str = line.split('=')[1].strip()
                            year = dt_str[0:4]
                            month = dt_str[4:6]
                            day = dt_str[6:8]
                            current_date = f"{day}.{month}.{year}"
                            self._show_date_message(f"Дата через WMIC: {current_date}")
                            self.controller.date_var.set(current_date)
                            return
            except Exception:
                pass

            try:
                result = subprocess.run(
                    ["cmd", "/c", "echo %date%"],
                    capture_output=True,
                    text=True,
                    shell=True,
                    timeout=2,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                if result.returncode == 0:
                    date_str = result.stdout.strip()
                    date_str = date_str.split()[0] if ' ' in date_str else date_str
                    for sep in ['.', '/', '-']:
                        if sep in date_str:
                            parts = date_str.split(sep)
                            if len(parts) == 3:
                                day, month, year = parts[0], parts[1], parts[2]
                                if len(year) == 2:
                                    year = f"20{year}"
                                current_date = f"{day.zfill(2)}.{month.zfill(2)}.{year}"
                                self._show_date_message(f"Дата через CMD: {current_date}")
                                self.controller.date_var.set(current_date)
                                return
            except Exception:
                pass

            current_date = datetime.now().strftime("%d.%m.%Y")
            self._show_date_message(f"Дата через datetime.now(): {current_date}")
            self.controller.date_var.set(current_date)

        except Exception as e:
            print(f"Общая ошибка в update_date_field: {e}")
            self._show_date_message("Ошибка обновления даты", is_error=True)

    def _show_date_message(self, message, is_error=False):
        """Показывает сообщение о дате в preview_module и скрывает через 5 секунд"""
        if self.controller.preview_module is not None:
            foreground = "red" if is_error else "blue"
            self.controller.preview_module.tirazh_label.config(
                text=message,
                foreground=foreground
            )
            self.controller.parent.after(5000, self._clear_date_message)

    def _clear_date_message(self):
        """Очищает сообщение о дате в preview_module"""
        if self.controller.preview_module is not None:
            self.controller.preview_module.tirazh_label.config(
                text="",
                foreground="green"
            )

    def update_elements_visibility(self):
        """Обновляет видимость дополнительных элементов на основе настроек"""
        try:
            settings = self.config_manager.load_json_settings("shared_utils.json")
            elements_status = settings.get("elements_status", "Скрыть")
            show_elements = (elements_status == "Показать")

            if show_elements:
                self.controller.date_entry.grid()
                self.controller.winding_label.grid()
                self.controller.winding_entry.grid()
                self.controller.diameter_label.grid()
                self.controller.diameter_entry.grid()
                self.controller.streams_label.grid()
                self.controller.streams_entry.grid()
                self.controller.stream_width_label.grid()
                self.controller.stream_width_entry.grid()
                self.controller.label_length_label.grid()
                self.controller.label_length_entry.grid()
                self.controller.emission_label.grid()
                self.controller.emission_entry.grid()
                self.controller.roll_label.grid()
                self.controller.roll_entry.grid()
            else:
                self.controller.date_entry.grid_remove()
                self.controller.winding_label.grid_remove()
                self.controller.winding_entry.grid_remove()
                self.controller.diameter_label.grid_remove()
                self.controller.diameter_entry.grid_remove()
                self.controller.streams_label.grid_remove()
                self.controller.streams_entry.grid_remove()
                self.controller.stream_width_label.grid_remove()
                self.controller.stream_width_entry.grid_remove()
                self.controller.label_length_label.grid_remove()
                self.controller.label_length_entry.grid_remove()
                self.controller.emission_label.grid_remove()
                self.controller.emission_entry.grid_remove()
                self.controller.roll_label.grid_remove()
                self.controller.roll_entry.grid_remove()
        except Exception as e:
            print(f"Ошибка обновления видимости элементов: {e}")

    def update_cutter_visibility(self):
        """Показывает/скрывает резчика и поля автогенерации в зависимости от цеха"""
        workshop = self.coordinator.get_workshop() if self.coordinator else "1"

        if hasattr(self.controller, 'cutter_label') and hasattr(self.controller, 'cutter_combo'):
            if workshop == "1":
                self.controller.cutter_label.grid_remove()
                self.controller.cutter_combo.grid_remove()
            else:
                self.controller.cutter_label.grid()
                self.controller.cutter_combo.grid()

        if workshop == "1":
            self.controller.batch_label.grid_remove()
            self.controller.batch_entry.grid_remove()
            self.controller.roll_length_label.grid_remove()
            self.controller.roll_length_entry.grid_remove()
        else:
            self.controller.batch_label.grid()
            self.controller.batch_entry.grid()
            self.controller.roll_length_label.grid()
            self.controller.roll_length_entry.grid()

    def toggle_weight_visibility(self):
        """Показывает/скрывает строку с весом"""
        show_weight = self.controller.show_weight_var.get()

        # Устанавливаем флаг для предотвращения расчетов при программной очистке
        self.controller._skip_weight_calculation = True

        try:
            if show_weight:
                self.controller.weight_label.grid()
                self.controller.gross_entry.grid()
                self.controller.sleeve_label.grid()
                self.controller.sleeve_entry.grid()

                self.controller.gross_weight_kg_var.set("")
                self.controller.net_weight_kg_var.set("")
                self.controller.total_gross_var.set("")
                self.controller.total_net_var.set("")

                self.controller.parent.after(50, lambda: self.controller.gross_entry.focus_set())
            else:
                self.controller.gross_weight_kg_var.set("")
                self.controller.net_weight_kg_var.set("")
                self.controller.total_gross_var.set("")
                self.controller.total_net_var.set("")

                self.controller.weight_label.grid_remove()
                self.controller.gross_entry.grid_remove()
                self.controller.sleeve_label.grid_remove()
                self.controller.sleeve_entry.grid_remove()

                self.controller.calculate_total_quantity()

                if hasattr(self.coordinator, 'check_weight_status'):
                    self.coordinator.check_weight_status(self.controller)
        finally:
            self.controller._skip_weight_calculation = False

    def update_rosinka_visibility(self):
        """Показывает/скрывает галочку Росинка в зависимости от заказчика"""
        customer = self.controller.customer_var.get()
        show_rosinka = customer and "росинка" in customer.lower()

        if hasattr(self.controller, 'rosinka_checkbutton'):
            if show_rosinka:
                self.controller.rosinka_checkbutton.grid()
            else:
                self.controller.rosinka_checkbutton.grid_remove()
                self.controller.rosinka_var.set(False)

    # ========== Методы для работы с буфером обмена ==========

    def add_context_menu(self, widget):
        """Добавляет контекстное меню к виджету"""
        menu = tk.Menu(widget, tearoff=0)
        menu.add_command(label="Копировать", command=lambda: self.copy_text(widget))
        menu.add_command(label="Вставить", command=lambda: self.paste_text(widget))
        widget.bind("<Button-3>", lambda e: menu.tk_popup(e.x_root, e.y_root))

    def add_context_menu_to_text(self, text_widget):
        """Добавляет контекстное меню к текстовому виджету"""
        menu = tk.Menu(text_widget, tearoff=0)
        menu.add_command(label="Копировать", command=lambda: self.copy_text_from_text_widget(text_widget))
        menu.add_command(label="Вставить", command=lambda: self.paste_text_to_text_widget(text_widget))
        text_widget.bind("<Button-3>", lambda e: menu.tk_popup(e.x_root, e.y_root))

    @staticmethod
    def copy_text(widget):
        """Копирует текст в буфер обмена"""
        try:
            text = widget.get()
            if text:
                widget.clipboard_clear()
                widget.clipboard_append(text)
        except Exception as e:
            print(f"Ошибка копирования: {e}")

    @staticmethod
    def paste_text(widget):
        """Вставляет текст из буфера обмена"""
        try:
            text = widget.clipboard_get()
            if text:
                widget.delete(0, tk.END)
                widget.insert(0, text)
        except Exception as e:
            print(f"Ошибка вставки: {e}")

    @staticmethod
    def copy_text_from_text_widget(widget):
        """Копирует текст из текстового виджета"""
        try:
            text = widget.get("1.0", "end-1c")
            if text:
                widget.clipboard_clear()
                widget.clipboard_append(text)
        except Exception as e:
            print(f"Ошибка копирования: {e}")

    @staticmethod
    def paste_text_to_text_widget(widget):
        """Вставляет текст в текстовый виджет"""
        try:
            text = widget.clipboard_get()
            if text:
                widget.delete("1.0", tk.END)
                widget.insert("1.0", text)
        except Exception as e:
            print(f"Ошибка вставки: {e}")

    def control_key_handler(self, event):
        """Обработчик горячих клавиш Ctrl+C и Ctrl+V"""
        if event.keycode == 86 or event.keycode == 118:  # V key
            self.paste_text(event.widget)
            return "break"
        elif event.keycode == 67 or event.keycode == 99:  # C key
            self.copy_text(event.widget)
            return "break"
        return None

    def control_key_handler_text(self, event):
        """Обработчик горячих клавиш для Text виджетов"""
        if event.keycode == 86 or event.keycode == 118:  # V key
            self.paste_text_to_text_widget(event.widget)
            return "break"
        elif event.keycode == 67 or event.keycode == 99:  # C key
            self.copy_text_from_text_widget(event.widget)
            return "break"
        return None