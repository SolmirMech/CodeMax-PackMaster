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
        """Загружает правила: default + user (мерж, приоритет у user)"""
        default_path = self.config_manager.get_asset_path("interface_mapping_default.json")
        user_path = self.config_manager.get_settings_path("interface_mapping_user.json")

        default_rules = self._load_json_file(default_path)
        user_rules = self._load_json_file(user_path)

        # Если нет дефолтного файла — создаём
        if not default_rules:
            self._create_default_rules(default_path)
            default_rules = self._load_json_file(default_path)

        # Мерж: user перезаписывает default
        merged = default_rules.copy()
        if user_rules:
            # Мерж profiles
            if "profiles" in user_rules:
                if "profiles" not in merged:
                    merged["profiles"] = {}
                merged["profiles"].update(user_rules["profiles"])

            # Мерж priority (user может добавить свои профили в приоритет)
            if "priority" in user_rules:
                existing_priority = merged.get("priority", [])
                new_profiles = [p for p in user_rules["priority"] if p not in existing_priority]
                merged["priority"] = existing_priority + new_profiles

        return merged

    @staticmethod
    def _load_json_file(path):
        """Загружает JSON, возвращает пустой dict при ошибке"""
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Ошибка загрузки {path}: {e}")
        return {}

    @staticmethod
    def _create_default_rules(path):
        """Создаёт файл с правилами по умолчанию"""
        default_rules = {
            "profiles": {
                "workshop_2": {
                    "condition": {"type": "eq", "key": "workshop", "value": "2"},
                    "mapping": {
                        "cutter_label": {"visible": True, "label": "Резка"},
                        "cutter_combo": {"visible": True},
                        "batch_label": {"visible": True, "label": "№ съёма:"},
                        "batch_entry": {"visible": True},
                        "roll_label": {"visible": True, "label": "№ ролика:"},
                        "roll_entry": {"visible": True},
                        "roll_length_label": {"visible": True, "label": "Длина ролика, м:"},
                        "roll_length_entry": {"visible": True}
                    },
                    "else_mapping": {
                        "cutter_label": {"visible": False},
                        "cutter_combo": {"visible": False},
                        "batch_label": {"visible": False},
                        "batch_entry": {"visible": False},
                        "roll_label": {"visible": False},
                        "roll_entry": {"visible": False},
                        "roll_length_label": {"visible": False},
                        "roll_length_entry": {"visible": False}
                    }
                },
                "manufacturer_ekosistema": {
                    "condition": {
                        "type": "contains",
                        "target": "manufacturer_normalized",
                        "value": ["экосистема"]
                    },
                    "mapping": {
                        "order_label": {"visible": False},
                        "order_prefix": {"visible": False},
                        "order_entry": {"visible": False},
                        "order_suffix": {"visible": False},
                        "quantity_label": {"visible": False},
                        "quantity_entry": {"visible": False},
                        "rolls_count_entry": {"visible": False},
                        "weight_checkbutton": {"visible": False}
                    },
                    "else_mapping": {
                        "order_label": {"visible": True},
                        "order_prefix": {"visible": True},
                        "order_entry": {"visible": True},
                        "order_suffix": {"visible": True},
                        "quantity_label": {"visible": True},
                        "quantity_entry": {"visible": True},
                        "rolls_count_entry": {"visible": True},
                        "weight_checkbutton": {"visible": True}
                    }
                },
                "customer_rosinka": {
                    "condition": {"type": "contains", "target": "customer", "value": ["росинка"]},
                    "mapping": {
                        "rosinka_checkbutton": {"visible": True}
                    },
                    "else_mapping": {
                        "rosinka_checkbutton": {"visible": False}
                    }
                },
                "show_weight": {
                    "condition": {"type": "eq", "key": "checkbox.show_weight_var", "value": True},
                    "mapping": {
                        "weight_label": {"visible": True, "label": "Вес ролика брутто, кг:"},
                        "gross_entry": {"visible": True},
                        "sleeve_label": {"visible": True, "label": "Вес втулки, г:"},
                        "sleeve_entry": {"visible": True}
                    },
                    "else_mapping": {
                        "weight_label": {"visible": False},
                        "gross_entry": {"visible": False},
                        "sleeve_label": {"visible": False},
                        "sleeve_entry": {"visible": False}
                    }
                },
                "elements_visibility": {
                    "condition": {"type": "eq", "key": "settings.elements_status", "value": "Скрыть"},
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
                        "emission_entry": {"visible": False}
                    },
                    "else_mapping": {
                        "date_entry": {"visible": True},
                        "winding_label": {"visible": True, "label": "Схема намотки:"},
                        "winding_entry": {"visible": True},
                        "diameter_label": {"visible": True, "label": "Диаметр втулки, мм:"},
                        "diameter_entry": {"visible": True},
                        "streams_label": {"visible": True, "label": "Кол-во ручьев:"},
                        "streams_entry": {"visible": True},
                        "stream_width_label": {"visible": True, "label": "Ширина ручья, мм:"},
                        "stream_width_entry": {"visible": True},
                        "label_length_label": {"visible": True, "label": "Длина этикетки, мм:"},
                        "label_length_entry": {"visible": True},
                        "emission_label": {"visible": True, "label": "Дата эмиссии:"},
                        "emission_entry": {"visible": True}
                    }
                },
                "podlo_smart": {
                    "condition": {"type": "or", "conditions": [
                        {"type": "contains", "target": "manufacturer_normalized", "value": ["экосистема"]},
                        {"type": "contains", "target": "customer", "value": ["росинка"]},
                        {"type": "eq", "key": "checkbox.rosinka_var", "value": True}
                    ]},
                    "mapping": {
                        "podlo_label": {
                            "visible": True,
                            "label": {
                                "type": "dynamic_label",
                                "rules": [
                                    {"condition": {"type": "contains", "target": "manufacturer_normalized",
                                                   "value": ["экосистема"]}, "label": "Артикул:"},
                                    {"condition": {"type": "or", "conditions": [
                                        {"type": "contains", "target": "customer", "value": ["росинка"]},
                                        {"type": "eq", "key": "checkbox.rosinka_var", "value": True}
                                    ]}, "label": "Подложка:"}
                                ],
                                "default": "Подложка:"
                            }
                        },
                        "podlo_entry": {"visible": True}
                    },
                    "else_mapping": {
                        "podlo_label": {"visible": False},
                        "podlo_entry": {"visible": False}
                    }
                }
            },
            "priority": [
                "workshop_2",
                "manufacturer_ekosistema",
                "customer_rosinka",
                "show_weight",
                "elements_visibility",
                "podlo_smart"
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

    def _check_condition(self, condition, context):
        """Проверяет условие, возвращает True/False."""
        cond_type = condition.get("type")
        cond_value = condition.get("value")

        if cond_type == "always":
            return True

        elif cond_type == "eq":
            key = condition.get("key")
            if not key:
                return False
            parts = key.split('.')
            val = context
            for part in parts:
                val = val.get(part, {}) if isinstance(val, dict) else getattr(val, part, None)
                if val is None:
                    return False
            return val == cond_value

        elif cond_type == "contains":
            target = condition.get("target", "")
            target_val = context
            for part in target.split('.'):
                target_val = target_val.get(part, {}) if isinstance(target_val, dict) else getattr(target_val, part,
                                                                                                   None)
                if target_val is None:
                    return False
            target_str = str(target_val).lower()
            keywords = cond_value if isinstance(cond_value, list) else [cond_value]
            return any(str(kw).lower() in target_str for kw in keywords)

        elif cond_type == "not_contains":
            target = condition.get("target", "")
            target_val = context
            for part in target.split('.'):
                target_val = target_val.get(part, {}) if isinstance(target_val, dict) else getattr(target_val, part,
                                                                                                   None)
                if target_val is None:
                    return True
            target_str = str(target_val).lower()
            keywords = cond_value if isinstance(cond_value, list) else [cond_value]
            return not any(str(kw).lower() in target_str for kw in keywords)

        elif cond_type == "and":
            conditions = condition.get("conditions", [])
            return all(self._check_condition(c, context) for c in conditions)

        elif cond_type == "or":
            conditions = condition.get("conditions", [])
            return any(self._check_condition(c, context) for c in conditions)

        elif cond_type == "not":
            sub_cond = condition.get("condition", {})
            return not self._check_condition(sub_cond, context)

        return False

    def _get_dynamic_value(self, value_config, context):
        """Возвращает динамическое значение (для label, visible и т.д.)"""
        if not isinstance(value_config, dict):
            return value_config

        value_type = value_config.get("type")

        if value_type == "dynamic_label":
            rules = value_config.get("rules", [])
            for rule in rules:
                rule_condition = rule.get("condition")
                if self._check_condition(rule_condition, context):
                    return rule.get("label")
            return value_config.get("default", "")

        elif value_type == "dynamic_visible":
            rules = value_config.get("rules", [])
            for rule in rules:
                rule_condition = rule.get("condition")
                if self._check_condition(rule_condition, context):
                    return rule.get("visible", True)
            return value_config.get("default", False)

        return value_config

    def apply(self, force_context=None):
        """Применяет маппинг с поддержкой динамических значений"""
        context = force_context or self._get_context()
        rules = self.rules
        priority = rules.get("priority", [])
        profiles = rules.get("profiles", {})

        final_mapping = {}

        for profile_name in priority:
            profile = profiles.get(profile_name)
            if not profile:
                continue

            condition = profile.get("condition", {})
            mapping = profile.get("mapping", {})
            else_mapping = profile.get("else_mapping", {})

            active_mapping = mapping if self._check_condition(condition, context) else else_mapping

            # Применяем изменения с учётом приоритета
            for widget_key, changes in active_mapping.items():
                if widget_key not in final_mapping:
                    final_mapping[widget_key] = {}

                # Обрабатываем каждое изменение
                for change_key, change_value in changes.items():
                    # Если это динамическое значение — вычисляем
                    if isinstance(change_value, dict) and change_value.get("type") in ["dynamic_label",
                                                                                       "dynamic_visible"]:
                        final_mapping[widget_key][change_key] = self._get_dynamic_value(change_value, context)
                    else:
                        final_mapping[widget_key][change_key] = change_value

        # Применяем к зарегистрированным виджетам
        for widget_key, changes in final_mapping.items():
            if widget_key in self.registered_widgets:
                widget_info = self.registered_widgets[widget_key]
                widget = widget_info['widget']

                if 'visible' in changes:
                    if changes['visible']:
                        widget.grid()
                    else:
                        widget.grid_remove()

                if 'label' in changes and hasattr(widget, 'config'):
                    try:
                        widget.config(text=changes['label'])
                    except:
                        pass

        return final_mapping
