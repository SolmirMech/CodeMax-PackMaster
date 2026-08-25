# statistics.py
from dataclasses import dataclass, field
from typing import List, Set, Dict, Any
import logging


@dataclass
class OrderStatistics:
    """Контейнер для статистики по заказам"""
    
    emission_orders: Set[str] = field(default_factory=set)
    solmark_orders: Set[str] = field(default_factory=set)
    multi_customer_orders: List[Dict[str, Any]] = field(default_factory=list)
    diameter_orders: Set[str] = field(default_factory=set)
    labels_per_roll_orders: Set[str] = field(default_factory=set)
    aggregation_orders: Set[str] = field(default_factory=set)
    processed_files: int = 0
    
    def add_order(self, parsed_data: Dict[str, Any]) -> None:
        """Добавляет статистику из одного заказа"""
        order_number = parsed_data.get('order_number', '')
        if not order_number:
            return
        
        self.processed_files += 1
        products = parsed_data.get('products', [])
        operations = parsed_data.get('operations', {})
        
        # Дата эмиссии
        if any(p.get('date_emission', '') for p in products):
            self.emission_orders.add(order_number)
        
        # Solmark
        if parsed_data.get('has_solmark', False):
            self.solmark_orders.add(order_number)
        
        # Множественные заказчики
        customer_info = parsed_data.get('_customer_info', {})
        if customer_info.get('has_multiple', False):
            self.multi_customer_orders.append({
                'order_number': order_number,
                'all_customers': customer_info.get('all_customers', []),
                'selected_customer': customer_info.get('customer', ''),
                'selection_method': customer_info.get('selection_method', '')
            })
        
        # Оттиски и параметры
        unique_sheets = {p.get('sheet_number', '') for p in products if p.get('sheet_number')}
        if len(unique_sheets) > 1:
            if operations.get('diameter_mm'):
                self.diameter_orders.add(order_number)
            if operations.get('max_labels_per_roll'):
                self.labels_per_roll_orders.add(order_number)
        
        # Агрегация
        if operations.get('aggregation_status'):
            self.aggregation_orders.add(order_number)
    
    def merge(self, other: 'OrderStatistics') -> None:
        """Объединяет две статистики"""
        self.emission_orders.update(other.emission_orders)
        self.solmark_orders.update(other.solmark_orders)
        self.multi_customer_orders.extend(other.multi_customer_orders)
        self.diameter_orders.update(other.diameter_orders)
        self.labels_per_roll_orders.update(other.labels_per_roll_orders)
        self.aggregation_orders.update(other.aggregation_orders)
        self.processed_files += other.processed_files
    
    def clear(self) -> None:
        """Очищает статистику"""
        self.emission_orders.clear()
        self.solmark_orders.clear()
        self.multi_customer_orders.clear()
        self.diameter_orders.clear()
        self.labels_per_roll_orders.clear()
        self.aggregation_orders.clear()
        self.processed_files = 0
    
    def is_empty(self) -> bool:
        """Проверяет, есть ли данные"""
        return not any([
            self.emission_orders,
            self.solmark_orders,
            self.multi_customer_orders,
            self.diameter_orders,
            self.labels_per_roll_orders,
            self.aggregation_orders
        ])


# statistics.py

class StatisticsLogger:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def log(self, stats: OrderStatistics, context: str = "сканирование",
            customer_map: Dict[str, str] = None) -> None:
        """
        Логирует статистику.

        Args:
            stats: Статистика для логирования
            context: Контекст операции
            customer_map: Словарь {номер_заказа: заказчик} (опционально)
        """
        if stats.is_empty():
            self.logger.info(f"Статистика {context}: изменений не обнаружено")
            return

        self.logger.info("=" * 70)
        self.logger.info(f"ИТОГОВАЯ СТАТИСТИКА ({context.upper()})")
        self.logger.info("=" * 70)

        # Логируем категории с заказчиками
        self._log_list("Заказы с Дата эмиссии", stats.emission_orders, customer_map)
        self._log_list("Solmark заказы (ID 321)", stats.solmark_orders, customer_map)
        self._log_list("Заказы с diameter_mm (оттисков > 1)", stats.diameter_orders, customer_map)
        self._log_list("Заказы с max_labels_per_roll (оттисков > 1)", stats.labels_per_roll_orders, customer_map)
        self._log_list("Заказы с агрегацией", stats.aggregation_orders, customer_map)

        # Множественные заказчики (у них уже есть подробная информация)
        if stats.multi_customer_orders:
            self.logger.info(f"Заказы с множественными заказчиками ({len(stats.multi_customer_orders)}):")
            for item in sorted(stats.multi_customer_orders, key=lambda x: x['order_number']):
                self.logger.info(
                    f"  {item['order_number']}: выбрано '{item['selected_customer']}' "
                    f"из {len(item['all_customers'])} (метод: {item['selection_method']})"
                )
            self.logger.info("")

        # Общая статистика
        self.logger.info(f"Обработано файлов: {stats.processed_files}")
        if stats.emission_orders:
            self.logger.info(f"Заказов с датой эмиссии: {len(stats.emission_orders)}")
        if stats.solmark_orders:
            self.logger.info(f"Solmark заказов: {len(stats.solmark_orders)}")
        if stats.multi_customer_orders:
            self.logger.info(f"Заказов с множественными заказчиками: {len(stats.multi_customer_orders)}")
        if stats.diameter_orders:
            self.logger.info(f"Заказов с diameter_mm: {len(stats.diameter_orders)}")
        if stats.labels_per_roll_orders:
            self.logger.info(f"Заказов с max_labels_per_roll: {len(stats.labels_per_roll_orders)}")
        if stats.aggregation_orders:
            self.logger.info(f"Заказов с агрегацией: {len(stats.aggregation_orders)}")

        self.logger.info("=" * 70)
        self.logger.info("")

    def _log_list(self, title: str, items: Set[str],
                  customer_map: Dict[str, str] = None) -> None:
        """
        Логирует список с заказчиками (если есть).

        Args:
            title: Заголовок
            items: Множество номеров заказов
            customer_map: Словарь {номер_заказа: заказчик}
        """
        if not items:
            return

        sorted_items = sorted(items)
        self.logger.info(f"{title} ({len(items)}):")

        # Форматируем с заказчиками или без
        if customer_map:
            formatted = []
            for order_num in sorted_items:
                customer = customer_map.get(order_num, 'неизвестно')
                # Обрезаем длинные названия для компактности (опционально)
                if len(customer) > 40:
                    customer = customer[:37] + '...'
                formatted.append(f"{order_num} ({customer})")
        else:
            formatted = sorted_items

        # По 5 в строке если есть заказчики, иначе по 10
        items_per_line = 5 if customer_map else 10
        for i in range(0, len(formatted), items_per_line):
            group = formatted[i:i + items_per_line]
            self.logger.info(f"  {', '.join(group)}")

        self.logger.info("")

