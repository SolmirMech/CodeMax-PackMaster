# main_ui/order_data/interface_mapper.py
"""Модуль динамического маппинга интерфейса"""

import json
import os


class InterfaceMapper:
    """Управляет видимостью, подписями и состоянием полей на основе контекста"""

    def __init__(self, config_manager, controller, coordinator):
        self.config_manager = config_manager
        self.controller = controller
        self.coordinator = coordinator
        self.rules = self._load_rules()
        self.registered_widgets = {}  # {widget_key: {'widget': widget, 'default_label': str}}

    def _load_rules(self):
        """Загружает правила из interface_mapping.json"""
        try:
            path = self.config_manager.get_settings_path("interface_mapping.json")
            if not os.path.exists(path):
                self._create_default_rules(path)
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Ошибка загрузки маппинга: {e}")
            return {"profiles": {}, "priority": []}

    @staticmethod
    def _create_default_rules(path):
        """Создаёт файл с правилами по умолчанию"""
        default_rules = {
            "profiles": {
                "workshop_1": {
                    "condition": {"type": "workshop", "value": "1"},
                    "mapping": {
                        "cutter_label": {"visible": False},
                        "cutter_combo": {"visible": False},
                        "batch_label": {"visible": False},
                        "batch_entry": {"visible": False},
                        "roll_length_label": {"visible": False},
                        "roll_length_entry": {"visible": False}
                    }
                },
                "workshop_2": {
                    "condition": {"type": "workshop", "value": "2"},
                    "mapping": {
                        "cutter_label": {"visible": True},
                        "cutter_combo": {"visible": True},
                        "batch_label": {"visible": True},
                        "batch_entry": {"visible": True},
                        "roll_length_label": {"visible": True},
                        "roll_length_entry": {"visible": True}
                    }
                },
                "manufacturer_ekosistema": {
                    "condition": {"type": "manufacturer_normalized", "value": ["экосистема"]},
                    "mapping": {
                        "podlo_label": {"label": "Артикул:", "visible": True},
                        "podlo_entry": {"visible": True}
                    }
                },
                "hide_podlo": {
                    "condition": {"type": "not_manufacturer_normalized", "value": ["экосистема"]},
                    "mapping": {
                        "podlo_label": {"label": "Подложка:", "visible": False},
                        "podlo_entry": {"visible": False}
                    }
                },
                "customer_rosinka": {
                    "condition": {"type": "customer_contains", "value": ["росинка"]},
                    "mapping": {
                        "rosinka_checkbutton": {"visible": True}
                    }
                },
                "hide_rosinka": {
                    "condition": {"type": "not_customer_contains", "value": ["росинка"]},
                    "mapping": {
                        "rosinka_checkbutton": {"visible": False}
                    }
                },
                "show_weight": {
                    "condition": {"type": "checkbox", "var": "show_weight_var", "value": True},
                    "mapping": {
                        "weight_label": {"visible": True},
                        "gross_entry": {"visible": True},
                        "sleeve_label": {"visible": True},
                        "sleeve_entry": {"visible": True}
                    }
                },
                "hide_weight": {
                    "condition": {"type": "checkbox", "var": "show_weight_var", "value": False},
                    "mapping": {
                        "weight_label": {"visible": False},
                        "gross_entry": {"visible": False},
                        "sleeve_label": {"visible": False},
                        "sleeve_entry": {"visible": False}
                    }
                },
                "elements_hidden": {
                    "condition": {"type": "settings", "key": "elements_status", "value": "Скрыть"},
                    "mapping": {
                        "date_entry": {"visible": False},
                        "winding_label": {"visible": False},
                        "winding_entry": {"visible": False},
                        "diameter_label": {"visible": False},
                        "diameter_entry": {"visible": False},
                        "streams_label": {"visible": False},
                        "streams_entry": {"visible": False},
                        "stream_width_label": {"visible": False},
                        "stream_width_entry": {"visible": False},
                        "label_length_label": {"visible": False},
                        "label_length_entry": {"visible": False},
                        "emission_label": {"visible": False},
                        "emission_entry": {"visible": False},
                        "roll_label": {"visible": False},
                        "roll_entry": {"visible": False}
                    }
                },
                "elements_shown": {
                    "condition": {"type": "settings", "key": "elements_status", "value": "Показать"},
                    "mapping": {
                        "date_entry": {"visible": True},
                        "winding_label": {"visible": True},
                        "winding_entry": {"visible": True},
                        "diameter_label": {"visible": True},
                        "diameter_entry": {"visible": True},
                        "streams_label": {"visible": True},
                        "streams_entry": {"visible": True},
                        "stream_width_label": {"visible": True},
                        "stream_width_entry": {"visible": True},
                        "label_length_label": {"visible": True},
                        "label_length_entry": {"visible": True},
                        "emission_label": {"visible": True},
                        "emission_entry": {"visible": True},
                        "roll_label": {"visible": True},
                        "roll_entry": {"visible": True}
                    }
                },
                "default_rosinka": {
                    "condition": {"type": "always"},
                    "mapping": {
                        "rosinka_checkbutton": {"visible": False}
                    }
                },
                "default_podlo": {
                    "condition": {"type": "always"},
                    "mapping": {
                        "podlo_label": {"label": "Подложка:", "visible": False},
                        "podlo_entry": {"visible": False}
                    }
                }
            },
            "priority": [
                "workshop_1",
                "workshop_2",
                "manufacturer_ekosistema",
                "hide_podlo",
                "customer_rosinka",
                "hide_rosinka",
                "show_weight",
                "hide_weight",
                "elements_hidden",
                "elements_shown",
                "default_rosinka",
                "default_podlo"
            ]
        }
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(default_rules, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка создания default маппинга: {e}")

    def register_widget(self, key, widget, default_label=None):
        """Регистрирует виджет для управления маппером"""
        self.registered_widgets[key] = {
            'widget': widget,
            'default_label': default_label or self._get_widget_label(widget)
        }

    @staticmethod
    def _get_widget_label(widget):
        """Пытается получить текущий текст лейбла у виджета"""
        try:
            if hasattr(widget, 'cget'):
                return widget.cget('text')
        except:
            pass
        return ""

    def _get_context(self):
        """Формирует текущий контекст из controller и coordinator"""
        context = {
            "workshop": self.coordinator.get_workshop() if self.coordinator else "1",
            "customer": self.controller.customer_var.get().lower(),
            "manufacturer": self.controller.manufacturer_var.get(),
            "manufacturer_normalized": self.controller.normalize_string(self.controller.manufacturer_var.get()),
            "checkbox": {}
        }

        # Собираем все checkbox переменные
        checkbox_vars = ['rosinka_var', 'show_weight_var', 'shorten_text_var']
        for var_name in checkbox_vars:
            if hasattr(self.controller, var_name):
                context["checkbox"][var_name] = getattr(self.controller, var_name).get()

        # Загружаем настройки из shared_utils
        try:
            settings = self.config_manager.load_json_settings("shared_utils.json")
            context["settings"] = settings
        except:
            context["settings"] = {}

        return context

    @staticmethod
    def _check_condition(condition, context):
        """Проверяет, выполняется ли условие"""
        cond_type = condition.get("type")
        cond_value = condition.get("value")

        if cond_type == "workshop":
            return context.get("workshop") == cond_value

        elif cond_type == "manufacturer_normalized":
            normalized = context.get("manufacturer_normalized", "")
            return normalized in cond_value if isinstance(cond_value, list) else normalized == cond_value

        elif cond_type == "not_manufacturer_normalized":
            normalized = context.get("manufacturer_normalized", "")
            keywords = cond_value if isinstance(cond_value, list) else [cond_value]
            return normalized not in keywords

        elif cond_type == "customer_contains":
            customer = context.get("customer", "")
            keywords = cond_value if isinstance(cond_value, list) else [cond_value]
            return any(keyword.lower() in customer for keyword in keywords)

        elif cond_type == "not_customer_contains":
            customer = context.get("customer", "")
            keywords = cond_value if isinstance(cond_value, list) else [cond_value]
            return not any(keyword.lower() in customer for keyword in keywords)

        elif cond_type == "checkbox":
            var_name = condition.get("var")
            return context.get("checkbox", {}).get(var_name) == cond_value

        elif cond_type == "settings":
            key = condition.get("key")
            settings = context.get("settings", {})
            return settings.get(key) == cond_value

        elif cond_type == "always":
            return True

        return False

    def apply(self, force_context=None):
        """Применяет маппинг на основе текущего контекста"""
        context = force_context or self._get_context()
        rules = self.rules
        priority = rules.get("priority", [])
        profiles = rules.get("profiles", {})

        # Собираем все подходящие профили
        active_mappings = []
        default_profile = None

        for profile_name in priority:
            profile = profiles.get(profile_name)
            if not profile:
                continue

            condition = profile.get("condition", {})
            if condition.get("type") == "always":
                default_profile = profile.get("mapping", {})
            elif self._check_condition(condition, context):
                active_mappings.append(profile.get("mapping", {}))

        # Если есть активные маппинги — применяем их
        if active_mappings:
            final_mapping = {}
            for mapping in active_mappings:
                final_mapping.update(mapping)
        else:
            # Если нет активных — применяем default
            final_mapping = default_profile or {}

        # Применяем к зарегистрированным виджетам
        for widget_key, changes in final_mapping.items():
            if widget_key in self.registered_widgets:
                widget_info = self.registered_widgets[widget_key]
                widget = widget_info['widget']

                # Применяем видимость
                if 'visible' in changes:
                    if changes['visible']:
                        widget.grid()
                    else:
                        widget.grid_remove()

                # Применяем текст лейбла
                if 'label' in changes and hasattr(widget, 'config'):
                    try:
                        widget.config(text=changes['label'])
                    except:
                        pass

        return final_mapping

