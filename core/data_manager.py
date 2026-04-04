"""
Модуль data_manager.py - кэширующий слой для работы с XML-файлами заказов.
Ускоряет поиск в 100+ раз за счет использования SQLite базы данных.
"""

import hashlib
import json
import logging
import sqlite3
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import chardet

# Импорт существующего парсера
from core.parse.xml_order_parser import parse_xml


# noinspection SpellCheckingInspection,PyTypeChecker
class XMLDataManager:
    """
    Кэширующий менеджер данных для работы с XML-файлами заказов.
    Прозрачно заменяет прямой парсинг XML на поиск из БД.
    """
    
    def __init__(self, config_manager, coordinator=None, root=None):
        """
        Инициализация через существующий ConfigManager.
        
        Args:
            config_manager: Экземпляр ConfigManager для получения путей
        """
        self._background_running = None
        self.config = config_manager
        self.coordinator = coordinator
        self.status_callback = None
        self.root = root
        
        # Получаем путь к XML заказам
        xml_path = config_manager.get_weight_data_base_path()
        self.xml_folder = Path(xml_path)
        
        # Путь к БД в папке data AppData
        self.db_path = config_manager.data_dir / "orders_cache.db"
        
        # Списки для статистики
        self._emission_orders = set()      # Заказы с датой эмиссии
        self._solmark_orders = set()       # Solmark заказы (ID 321)
        self._multi_customer_orders = []       # Заказы с множественными заказчиками
        self._processed_files = 0          # Счетчик обработанных файлов
        self._diameter_orders = set()  # Заказы с diameter_mm и оттисков > 1
        self._labels_per_roll_orders = set()  # Заказы с max_labels_per_roll и оттисков > 1
        self._aggregation_orders = set()
        
        # Атрибуты для управления потоками
        self._readers_count = 0             # Счётчик активных читателей
        self._readers_lock = threading.RLock()  # Блокировка для счётчика
        self._write_lock = threading.RLock()     # Блокировка для записи
        self._update_scheduled = False       # Флаг отложенного обновления
        
        # Настройка логгирования
        self.log_file = config_manager.data_dir / "data_manager.log"
        self._setup_logging()
        
        # Проверяем доступность
        if not self.xml_folder.exists():
            logging.warning(f"XML папка не найдена: {self.xml_folder}")
        
        # Блокировка для потокобезопасности
        self._lock = threading.RLock()
        self._background_lock = threading.Lock()
        
        # Инициализация БД
        self._init_database()
        # Подписываемся на уведомления координатора
        if self.coordinator and hasattr(self.coordinator, 'subscribe'):
            self.coordinator.subscribe(self.on_settings_changed)

        logging.debug(f"DataManager инициализирован. XML папка: {self.xml_folder}")
        logging.debug(f"БД: {self.db_path}")
        
        self._pending_status = None  # ID отложенного сообщения
        self._last_message = ""      # Для дублей
        # Флаг для периодической проверки
        self._periodic_check_running = False
        self._start_periodic_check()

    def on_settings_changed(self, context=None):
        """Обработчик уведомлений от координатора"""
        if context and isinstance(context, dict):
            if context.get("type") == "list_changed" and context.get("list_name") == "update_date_request":
                self.start_background_check(silent=False)

            if context.get("type") == "xml_folder_changed":
                # Обновляем путь к XML папке
                new_path = self.config.get_weight_data_base_path()
                self.xml_folder = Path(new_path)
                # Запускаем пересканирование
                self.start_background_check(silent=False)
            
    def _start_periodic_check(self):
        """Запускает периодическую проверку каждые 5 минут"""
        if self._periodic_check_running:
            return
        
        self._periodic_check_running = True
        
        def periodic_check():
            while self._periodic_check_running:
                time.sleep(900)  # 15 минут
                if self._periodic_check_running:  # Проверяем ещё раз после сна
                    self._start_background_check(silent=True)
        
        thread = threading.Thread(target=periodic_check, daemon=True)
        thread.start()        
        
    def set_status_callback(self, callback):
        """Устанавливает callback для отправки статусных сообщений в UI"""
        self.status_callback = callback

    def _notify_status(self, message: str):
        """Отправляет статусное сообщение в UI"""

        if not self.status_callback:
            return

        # Если в главном потоке - вызываем напрямую
        if threading.current_thread() is threading.main_thread():
            self._do_status_update(message)
            return

        # В фоновом потоке — используем сохраненный root
        if self.root:  # ← используем self.root вместо создания нового
            # Отменяем предыдущее отложенное сообщение
            if self._pending_status:
                try:
                    self.root.after_cancel(self._pending_status)
                except Exception:
                    pass
                self._pending_status = None

            # Ставим новое с задержкой
            self._pending_status = self.root.after(
                500,
                lambda: self._do_status_update(message)
            )
        else:
            # Если root нет - вызываем напрямую (запасной вариант)
            self._do_status_update(message)

    def _do_status_update(self, message):
        """Реальное обновление статуса (всегда в главном потоке)"""
        self._pending_status = None
        
        # Защита от дублей
        if message == self._last_message:
            return
        self._last_message = message
        
        try:
            self.status_callback(message)
        except Exception as e:
            print(f"Ошибка обновления статуса: {e}")
    
    def _setup_logging(self):
        """Настройка логгирования."""
        logging.basicConfig(
            filename=self.log_file,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            encoding='utf-8'
        )
    
    def _init_database(self):
        """Инициализация базы данных, создание таблиц и индексов."""
        with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Таблица orders (основная)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS orders (
                        file_name TEXT PRIMARY KEY,
                        file_path TEXT NOT NULL,
                        order_number TEXT,
                        order_prefix TEXT,
                        order_suffix TEXT,
                        order_name TEXT,
                        order_manager TEXT,
                        customer TEXT,
                        executor TEXT,
                        tu_number TEXT,
                        parsed_data JSON NOT NULL,
                        file_hash TEXT,
                        last_modified REAL NOT NULL,
                        cached_at REAL NOT NULL
                    )
                """)
                
                # Таблица products (для поиска по деталям) - ОБНОВЛЕНА
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS products (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        order_file TEXT NOT NULL,
                        detail_number TEXT NOT NULL,
                        product_name TEXT,
                        short_name TEXT,
                        gtin TEXT,
                        date_emission TEXT,
                        quantity TEXT,
                        sheet_number TEXT,        -- ← Цифры оттиска
                        sheet_full_name TEXT,     -- ← НОВОЕ: полное название оттиска
                        stream TEXT,
                        FOREIGN KEY (order_file) REFERENCES orders(file_name)
                    )
                """)
                
                # Таблица sheets (для поиска по оттискам)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS sheets (
                        order_file TEXT NOT NULL,
                        sheet_number TEXT NOT NULL,
                        sheet_name TEXT,
                        PRIMARY KEY (order_file, sheet_number)
                    )
                """)
                
                # Индексы для скорости
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_number ON orders(order_number)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_detail_number ON products(detail_number)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_sheet_number ON sheets(sheet_number)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_sheet_full_name ON products(sheet_full_name)")  # ← НОВЫЙ индекс
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_order ON products(order_file)")
                
                # Проверяем наличие колонки sheet_full_name и добавляем если нет
                cursor.execute("PRAGMA table_info(products)")
                columns = [col[1] for col in cursor.fetchall()]
                
                if 'sheet_full_name' not in columns:
                    cursor.execute("ALTER TABLE products ADD COLUMN sheet_full_name TEXT")
                    logging.info("Добавлена колонка sheet_full_name в таблицу products")
                    
                # Проверяем наличие колонки order_name и добавляем если нет
                cursor.execute("PRAGMA table_info(orders)")  # ← ИЗМЕНИТЬ С orders!
                columns = [col[1] for col in cursor.fetchall()]
                
                if 'order_name' not in columns:
                    cursor.execute("ALTER TABLE orders ADD COLUMN order_name TEXT")
                    logging.info("Добавлена колонка order_name в таблицу orders")                    
                
                conn.commit()
                
            except sqlite3.Error as e:
                logging.error(f"Ошибка инициализации БД: {e}")
                # Пытаемся восстановить
                self._recreate_database()
            finally:
                if 'conn' in locals():
                    conn.close()
    
    def _recreate_database(self):
        """Пересоздание базы данных в случае повреждения."""
        try:
            if self.db_path.exists():
                backup_path = self.db_path.with_suffix('.db.bak')
                self.db_path.rename(backup_path)
                logging.warning(f"БД повреждена. Создан бэкап: {backup_path}")
            
            # Пересоздаём с нуля
            self._init_database()
            logging.info("База данных пересоздана")
            
            # Запускаем сканирование
            self.initial_scan()
            
        except Exception as e:
            logging.error(f"Критическая ошибка восстановления БД: {e}")
    
    def _parse_xml_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Парсит XML файл и возвращает структурированные данные.
        
        Args:
            file_path: Путь к XML файлу
            
        Returns:
            Словарь с данными или None в случае ошибки
        """
        try:
            # Читаем файл с определением кодировки
            raw_data = file_path.read_bytes()
            
            # Определяем кодировку
            if raw_data.startswith(b'\xff\xfe'):  # UTF-16 LE
                content = raw_data.decode('utf-16')
            elif raw_data.startswith(b'\xfe\xff'):  # UTF-16 BE
                content = raw_data.decode('utf-16')
            else:
                try:
                    content = raw_data.decode('utf-8')
                except UnicodeDecodeError:
                    # Пробуем другие кодировки
                    try:
                        encoding = chardet.detect(raw_data)['encoding'] or 'windows-1251'
                        content = raw_data.decode(encoding)
                    except:
                        content = raw_data.decode('utf-8', errors='ignore')
            
            # Парсим через существующий парсер
            parsed_data = parse_xml(content)
            
            # Собираем статистику
            self._analyze_and_log_statistics(parsed_data)
            
            # Удаляем служебные поля перед сохранением в БД
            if '_customer_info' in parsed_data:
                del parsed_data['_customer_info']
            
            # Добавляем имя файла в данные для совместимости
            parsed_data['file_name'] = file_path.name
            parsed_data['file_path'] = str(file_path)
            
            return parsed_data
            
        except Exception as e:
            logging.error(f"Ошибка парсинга файла {file_path}: {e}")
            return None
            
    def _analyze_and_log_statistics(self, parsed_data: Dict[str, Any]):
        """
        Анализирует данные и собирает статистику.
        НЕ ЛОГИРУЕТ промежуточные результаты, только собирает.
        
        Args:
            parsed_data: Распарсенные данные заказа
        """
        order_number = parsed_data.get('order_number', '')
        if not order_number:
            return
        
        # 1. Дата эмиссии - есть ли в продуктах
        products = parsed_data.get('products', [])
        has_emission_date = any(product.get('date_emission', '') for product in products)
        
        if has_emission_date:
            self._emission_orders.add(order_number)
        
        # 2. Solmark заказы - проверяем наличие операции с ID 321
        has_solmark = parsed_data.get('has_solmark', False)
        
        if has_solmark:
            self._solmark_orders.add(order_number)
        
        # 3. Множественные заказчики - добавляем в отдельный список
        customer_info = parsed_data.get('_customer_info', {})
        if customer_info.get('has_multiple', False):
            # Сохраняем не только номер, но и информацию о выборе
            self._multi_customer_orders.append({
                'order_number': order_number,
                'all_customers': customer_info.get('all_customers', []),
                'selected_customer': customer_info.get('customer', ''),
                'selection_method': customer_info.get('selection_method', '')
            })

        # 4. Статистика по diameter_mm и max_labels_per_roll
        # Проверяем количество уникальных оттисков
        operations = parsed_data.get('operations', {})
        unique_sheets = set()

        # Собираем уникальные номера оттисков
        for product in products:
            sheet_num = product.get('sheet_number', '')
            if sheet_num:
                unique_sheets.add(sheet_num)

        # Если оттисков больше одного, проверяем наличие нужных параметров
        if len(unique_sheets) > 1:
            # Проверяем наличие diameter_mm
            if operations.get('diameter_mm'):
                self._diameter_orders.add(order_number)

            # Проверяем наличие max_labels_per_roll
            if operations.get('max_labels_per_roll'):
                self._labels_per_roll_orders.add(order_number)

        # 5. Агрегация
        operations = parsed_data.get('operations', {})
        aggregation_status = operations.get('aggregation_status', '')
        if aggregation_status:
            self._aggregation_orders.add(order_number)
        
        # Увеличиваем счетчик (БЕЗ промежуточного логирования)
        self._processed_files += 1
            
    def _log_collected_statistics(self, context: str = "сканирование"):
        """
        Логирует собранную статистику в компактном формате.
        ТОЛЬКО ИТОГОВЫЙ ЛОГ.
        
        Args:
            context: Контекст операции ("сканирование", "обновление", "проверка")
        """
        # Логируем только если есть что логировать
        has_emission = len(self._emission_orders) > 0
        has_solmark = len(self._solmark_orders) > 0
        has_multi_customer = len(self._multi_customer_orders) > 0
        
        if not (has_emission or has_solmark or has_multi_customer):
            logging.info(f"Статистика {context}: изменений не обнаружено")
            return
        
        try:
            # Разделитель для визуального выделения
            logging.info("=" * 70)
            logging.info(f"ИТОГОВАЯ СТАТИСТИКА ({context.upper()})")
            logging.info("=" * 70)
            
            # 1. Заказы с датой эмиссии
            if has_emission:
                # Получаем информацию о заказчиках для заказов с датой эмиссии
                emission_with_customers = self._get_orders_with_customers(self._emission_orders)
                self._log_compact_list(
                    title="Заказы с Дата эмиссии",
                    items=emission_with_customers,
                    items_per_line=5  # Уменьшаем количество в строке из-за длинных записей
                )
            
            # 2. Solmark заказы
            if has_solmark:
                # Получаем информацию о заказчиках для Solmark заказов
                solmark_with_customers = self._get_orders_with_customers(self._solmark_orders)
                self._log_compact_list(
                    title="Solmark заказы (ID 321)",
                    items=solmark_with_customers,
                    items_per_line=5  # Уменьшаем количество в строке из-за длинных записей
                )
            
            # 3. Заказы с множественными заказчиками
            if has_multi_customer:
                logging.info(f"Заказы с множественными заказчиками ({len(self._multi_customer_orders)}):")
                
                for item in sorted(self._multi_customer_orders, 
                                  key=lambda x: x['order_number']):
                    order_num = item['order_number']
                    selected = item['selected_customer']
                    all_count = len(item['all_customers'])
                    method = item['selection_method']
                    
                    # Компактный формат для одного заказа
                    logging.info(f"  {order_num}: выбрано '{selected}' из {all_count} (метод: {method})")              
                
                logging.info("")  # Пустая строка

            # 4. Заказы с diameter_mm (более одного оттиска)
            if len(self._diameter_orders) > 0:
                diameter_with_customers = self._get_orders_with_customers(self._diameter_orders)
                self._log_compact_list(
                    title="Заказы с diameter_mm (оттисков > 1)",
                    items=diameter_with_customers,
                    items_per_line=5
                )

            # 5. Заказы с max_labels_per_roll (более одного оттиска)
            if len(self._labels_per_roll_orders) > 0:
                labels_with_customers = self._get_orders_with_customers(self._labels_per_roll_orders)
                self._log_compact_list(
                    title="Заказы с max_labels_per_roll (оттисков > 1)",
                    items=labels_with_customers,
                    items_per_line=5
                )
            # 5. Заказы с агрегацией
            if len(self._aggregation_orders) > 0:
                aggregation_with_customers = self._get_orders_with_customers(self._aggregation_orders)
                self._log_compact_list(
                    title="Заказы с агрегацией",
                    items=aggregation_with_customers,
                    items_per_line=5
                )
            
            # Общая статистика
            logging.info(f"Обработано файлов: {self._processed_files}")
            if has_emission:
                logging.info(f"Заказов с датой эмиссии: {len(self._emission_orders)}")
            if has_solmark:
                logging.info(f"Solmark заказов: {len(self._solmark_orders)}")
            if has_multi_customer:
                logging.info(f"Заказов с множественными заказчиками: {len(self._multi_customer_orders)}")
            # Статистика по оттискам
            if len(self._diameter_orders) > 0:
                logging.info(f"Заказов с diameter_mm (>1 оттиска): {len(self._diameter_orders)}")
            if len(self._labels_per_roll_orders) > 0:
                logging.info(f"Заказов с max_labels_per_roll (>1 оттиска): {len(self._labels_per_roll_orders)}")
            logging.info("=" * 70)
            logging.info("")  # Пустая строка для разделения
            
        except (PermissionError, IOError, OSError):
            pass
            
    def _get_orders_with_customers(self, order_numbers: set) -> list:
        """
        Получает список заказов с информацией о заказчике в формате:
        "номер_заказа (заказчик)"
        
        Args:
            order_numbers: Множество номеров заказов
            
        Returns:
            Список строк с номером заказа и заказчиком
        """
        if not order_numbers:
            return []
        
        try:
            with self._lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Создаем список для запроса
                placeholders = ','.join('?' for _ in order_numbers)
                query = f"""
                    SELECT order_number, customer 
                    FROM orders 
                    WHERE order_number IN ({placeholders})
                """
                
                cursor.execute(query, list(order_numbers))
                results = cursor.fetchall()
                conn.close()
                
                # Создаем словарь номер_заказа -> заказчик
                customer_map = {row[0]: row[1] for row in results}
                
                # Формируем список в формате "номер (заказчик)"
                formatted_list = []
                for order_num in sorted(order_numbers):
                    customer = customer_map.get(order_num, 'неизвестно')
                    formatted_list.append(f"{order_num} ({customer})")
                
                return formatted_list
                
        except Exception as e:
            logging.error(f"Ошибка получения информации о заказчиках: {e}")
            # Возвращаем просто номера заказов в случае ошибки
            return sorted(order_numbers)            
        
    @staticmethod
    def _log_compact_list(title: str, items: list, items_per_line: int = 10):
        """
        Логирует список в компактном формате.
        
        Args:
            title: Заголовок списка
            items: Список элементов для логирования
            items_per_line: Количество элементов в одной строке
        """
        if not items:
            return
        
        logging.info(f"{title} ({len(items)}):")
        
        # Разбиваем на группы по items_per_line
        for i in range(0, len(items), items_per_line):
            line_items = items[i:i + items_per_line]
            line = ", ".join(line_items)
            # Добавляем отступ для визуального отделения
            logging.info(f"  {line}")
        
        # Пустая строка после списка
        logging.info("")
    
    @staticmethod
    def _calculate_file_hash(file_path: Path) -> str:
        """Вычисляет MD5 хэш файла для отслеживания изменений."""
        try:
            file_content = file_path.read_bytes()
            return hashlib.md5(file_content).hexdigest()
        except Exception as e:
            logging.error(f"Ошибка вычисления хэша для {file_path}: {e}")
            return ""
    
    @staticmethod
    def _save_order_to_db(conn: sqlite3.Connection, file_path: Path,
                          parsed_data: Dict[str, Any], file_hash: str) -> bool:
        """
        Сохраняет данные заказа в БД.
        
        Returns:
            True если успешно, False в случае ошибки
        """        
        try:
            cursor = conn.cursor()
            file_name = file_path.name
            last_modified = file_path.stat().st_mtime
            current_time = time.time()
            
            # Подготавливаем данные для таблицы orders
            order_data = (
                file_name,
                str(file_path),
                parsed_data.get('order_number', ''),
                parsed_data.get('order_prefix', ''),
                parsed_data.get('order_suffix', ''),
                parsed_data.get('order_name', ''),
                parsed_data.get('order_manager', ''),
                parsed_data.get('customer', ''),
                parsed_data.get('executor', ''),
                parsed_data.get('tu_number', ''),
                json.dumps(parsed_data, ensure_ascii=False),
                file_hash,
                last_modified,
                current_time
            )
            
            # Вставляем или обновляем запись в orders
            cursor.execute("""
                INSERT OR REPLACE INTO orders 
                (file_name, file_path, order_number, order_prefix, order_suffix, 
                 order_name, order_manager, customer, executor, tu_number, parsed_data, file_hash, 
                 last_modified, cached_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, order_data)
            
            # Удаляем старые записи для этого файла в products и sheets
            cursor.execute("DELETE FROM products WHERE order_file = ?", (file_name,))
            cursor.execute("DELETE FROM sheets WHERE order_file = ?", (file_name,))
            
            # Сохраняем продукты
            products = parsed_data.get('products', [])
            for product in products:
                product_data = (
                    file_name,
                    product.get('detail_number', ''),
                    product.get('product_name', ''),
                    product.get('full_name', ''),
                    product.get('gtin', ''),
                    product.get('date_emission', ''),
                    product.get('quantity', ''),
                    product.get('sheet_number', ''),       # ← Цифры оттиска (совместимость)
                    product.get('sheet_full_name', ''),    # Полное название оттиска
                    product.get('stream', '')
                )
                cursor.execute("""
                    INSERT INTO products 
                    (order_file, detail_number, product_name, short_name, gtin, 
                     date_emission, quantity, sheet_number, sheet_full_name, stream)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, product_data)
            
            # Сохраняем оттиски в таблицу sheets
            sheet_data = {}  # sheet_number -> sheet_full_name
            
            for product in products:
                sheet_num = product.get('sheet_number', '')
                sheet_full_name = product.get('sheet_full_name', '')
                
                if sheet_num:  # Если есть номер оттиска (цифры)
                    # Сохраняем самое полное название
                    if sheet_full_name and sheet_full_name not in sheet_data.get(sheet_num, []):
                        if sheet_num not in sheet_data:
                            sheet_data[sheet_num] = []
                        sheet_data[sheet_num].append(sheet_full_name)
            
            # Сохраняем в таблицу sheets
            for sheet_num, full_names in sheet_data.items():
                # Берем первое полное название
                sheet_full_name = full_names[0] if full_names else f"Тиражи I-{sheet_num}"
                
                cursor.execute("""
                    INSERT OR REPLACE INTO sheets (order_file, sheet_number, sheet_name)
                    VALUES (?, ?, ?)
                """, (file_name, sheet_num, sheet_full_name))
            
            return True
            
        except Exception as e:
            logging.error(f"Ошибка сохранения {file_path} в БД: {e}")
            return False

    def initial_scan(self) -> None:
        """
        ПЕРВИЧНОЕ СКАНИРОВАНИЕ.
        Вызывается при запуске программы (можно в фоне)
        Заполняет БД при первом запуске
        """

        def scan_in_background():
            try:
                # Проверяем есть ли данные в бд
                with self._lock:
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM orders")
                    count = cursor.fetchone()[0]
                    conn.close()

                if count > 0:
                    self._notify_status(f"База загружена ({count} записей)")
                    return

                self._notify_status("Проверка доступности источника XML...")

                # Проверяем доступность папки с тайм-аутом
                if not self._check_xml_source_available():
                    self._notify_status("⚠️ Источник XML недоступен")
                    logging.error(f"Папка XML недоступна: {self.xml_folder}")
                    return

                # Считаем файлы для прогресса
                xml_files = list(self.xml_folder.glob("*.xml"))
                total_files = len(xml_files)
                logging.info(f"Найдено XML файлов: {total_files}")

                if total_files == 0:
                    logging.warning("В папке XML не найдено файлов")
                    self._notify_status("⚠️ В источнике нет XML файлов")
                    return

                # Сообщение в уи
                self._notify_status(f"🔄 Ожидайте, идёт обновление базы ({total_files} файлов)...")

                # Очищаем БД перед полным сканированием
                with self._lock:
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM orders")
                    cursor.execute("DELETE FROM products")
                    cursor.execute("DELETE FROM sheets")
                    conn.commit()
                    conn.close()

                processed = 0
                errors = 0
                # batch_size больше не нужен, убираем

                # Инициализируем статистику перед сканированием
                self._emission_orders = set()
                self._solmark_orders = set()
                self._multi_customer_orders = []
                self._processed_files = 0

                for file_path in xml_files:  # ← убрали enumerate и batch_size
                    try:
                        # Парсим файл
                        parsed_data = self._parse_xml_file(file_path)
                        if not parsed_data:
                            errors += 1
                            continue

                        # Вычисляем хэш
                        file_hash = self._calculate_file_hash(file_path)

                        # Сохраняем в БД
                        with self._lock:
                            conn = sqlite3.connect(self.db_path)
                            if self._save_order_to_db(conn, file_path, parsed_data, file_hash):
                                processed += 1
                            conn.commit()
                            conn.close()

                    except Exception as e:
                        errors += 1
                        logging.error(f"Ошибка обработки {file_path.name}: {e}")

                # Финальное логирование статистики
                self._log_collected_statistics("первичное сканирование")

                # Финальное сообщение
                if errors > 0:
                    self._notify_status(f"✅ База создана ({processed} заказов, {errors} ошибок)")
                else:
                    self._notify_status(f"✅ База создана ({processed} заказов)")

                logging.info(f"Первичное сканирование завершено. Успешно: {processed}, Ошибок: {errors}")

            except Exception as e:
                logging.error(f"Ошибка при первичном сканировании: {e}")
                self._notify_status(f"❌ Ошибка сканирования: {e}")

        # Запускаем в фоновом потоке
        thread = threading.Thread(target=scan_in_background, daemon=True)
        thread.start()
        
    @staticmethod
    def _collect_statistics_for_file(parsed_data: Dict[str, Any],
                                     emission_set: set,
                                     solmark_set: set,
                                     multi_customer_list: list,
                                     diameter_set: set,
                                     labels_set: set,
                                     aggregation_set: set):
        """
        Собирает статистику для одного файла в указанные коллекции.
        
        Args:
            parsed_data: Данные заказа
            emission_set: Множество для заказов с датой эмиссии
            solmark_set: Множество для Solmark заказов
            multi_customer_list: Список для заказов с множественными заказчиками
        """
        order_number = parsed_data.get('order_number', '')
        if not order_number:
            return
        
        # 1. Дата эмиссии
        products = parsed_data.get('products', [])
        has_emission_date = any(product.get('date_emission', '') for product in products)
        
        if has_emission_date:
            emission_set.add(order_number)
        
        # 2. Solmark заказы
        has_solmark = parsed_data.get('has_solmark', False)
        
        if has_solmark:
            solmark_set.add(order_number)
        
        # 3. Множественные заказчики
        customer_info = parsed_data.get('_customer_info', {})
        if customer_info.get('has_multiple', False):
            multi_customer_list.append({
                'order_number': order_number,
                'all_customers': customer_info.get('all_customers', []),
                'selected_customer': customer_info.get('customer', ''),
                'selection_method': customer_info.get('selection_method', '')
            })

        # 4. Статистика по diameter_mm и max_labels_per_roll
        products = parsed_data.get('products', [])
        operations = parsed_data.get('operations', {})
        unique_sheets = set()

        for product in products:
            sheet_num = product.get('sheet_number', '')
            if sheet_num:
                unique_sheets.add(sheet_num)

        if len(unique_sheets) > 1:
            if operations.get('diameter_mm'):
                diameter_set.add(order_number)
            if operations.get('max_labels_per_roll'):
                labels_set.add(order_number)

        # 5. Агрегация
        operations = parsed_data.get('operations', {})
        aggregation_status = operations.get('aggregation_status', '')
        if aggregation_status:
            aggregation_set.add(order_number)
    
    def _check_xml_source_available(self) -> bool:
        """
        Проверяет доступность источника XML с тайм-аутом.
        
        Returns:
            True если источник доступен, False если недоступен
        """
        
        def check_folder():
            try:
                # Простая проверка существования папки
                return self.xml_folder.exists()
            except:
                return False
        
        # Создаём поток с тайм-аутом
        result = [None]
        
        def run_check():
            result[0] = check_folder()
        
        thread = threading.Thread(target=run_check, daemon=True)
        thread.start()
        thread.join(timeout=3)  # Таймаут 3 секунды
        
        if thread.is_alive():
            logging.warning(f"Таймаут проверки источника XML: {self.xml_folder}")
            return False
        
        return result[0] if result[0] is not None else False
    
    def search_combined(self, order_query: str, sheet_query: str = None) -> List[Dict[str, Any]]:
        """
        ОСНОВНОЙ МЕТОД ДЛЯ UI.
        Ищет заказы по номеру + фильтр по оттиску.
        Возвращает список словарей в ТОЧНОМ формате parse_xml()
        
        Args:
            order_query: Номер заказа (или его часть)
            sheet_query: Номер оттиска для фильтрации (опционально)
            
        Returns:
            Список словарей с данными заказов
        """
        start_time = time.time()
        
        # Увеличиваем счётчик читателей
        with self._readers_lock:
            self._readers_count += 1
        
        try:
            with self._lock:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Нормализуем запрос: удаляем всё кроме цифр
                order_digits = ''.join(filter(str.isdigit, order_query))
                
                if not order_digits:
                    return []
                
                # Базовый запрос
                if sheet_query:
                    # Поиск с фильтром по оттиску
                    sheet_digits = ''.join(filter(str.isdigit, sheet_query))
                    
                    query = """
                        SELECT DISTINCT o.* 
                        FROM orders o
                        JOIN products p ON o.file_name = p.order_file
                        WHERE o.order_number LIKE ? 
                          AND (p.sheet_number LIKE ? 
                               OR p.sheet_full_name LIKE ? 
                               OR p.detail_number LIKE ?)
                        ORDER BY o.order_number
                    """
                    params = (f'%{order_digits}%', 
                             f'%{sheet_digits}%', 
                             f'%{sheet_query}%', 
                             f'%{sheet_query}%')
                else:
                    # Поиск только по номеру заказа
                    query = """
                        SELECT * FROM orders 
                        WHERE order_number LIKE ? 
                        ORDER BY order_number
                    """
                    params = (f'%{order_digits}%',)
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                # Преобразуем в нужный формат
                results = []
                for row in rows:
                    try:
                        # Получаем данные из JSON поля
                        parsed_data = json.loads(row['parsed_data'])
                        
                        # Если нужна фильтрация по продуктам (при указании sheet_query)
                        if sheet_query and 'products' in parsed_data:
                            sheet_digits = ''.join(filter(str.isdigit, sheet_query))
                            filtered_products = []
                            
                            for product in parsed_data['products']:
                                # Проверяем совпадение по номеру оттиска (цифры)
                                # ИЛИ по полному названию оттиска
                                # ИЛИ по номеру детали
                                sheet_num = product.get('sheet_number', '')
                                sheet_full_name = product.get('sheet_full_name', '')
                                detail_num = product.get('detail_number', '')
                                
                                matches = (
                                    (sheet_digits and sheet_digits in sheet_num) or
                                    (sheet_query and sheet_query in sheet_full_name) or
                                    (sheet_query and sheet_query in detail_num)
                                )
                                
                                if matches:
                                    filtered_products.append(product)
                            
                            # Если после фильтрации есть продукты - добавляем заказ
                            if filtered_products:
                                parsed_data['products'] = filtered_products
                                results.append(parsed_data)
                        else:
                            # Без фильтрации - добавляем как есть
                            results.append(parsed_data)
                            
                    except json.JSONDecodeError as e:
                        logging.error(f"Ошибка декодирования JSON для {row['file_name']}: {e}")              
                
                elapsed = (time.time() - start_time) * 1000
                
                return results
                
        except sqlite3.Error as e:
            logging.error(f"Ошибка поиска в БД: {e}")
            # Пробуем восстановить БД
            self._recreate_database()
            return []
        except Exception as e:
            logging.error(f"Непредвиденная ошибка при поиске: {e}")
            return []
        finally:
            if 'conn' in locals():
                conn.close()
            
            # Уменьшаем счётчик читателей и проверяем отложенное обновление
            with self._readers_lock:
                self._readers_count -= 1
                # После уменьшения счётчика проверяем, не пора ли обновить
                if self._update_scheduled and self._readers_count == 0:
                    # Запускаем в отдельном потоке, чтобы не задерживать ответ
                    thread = threading.Thread(target=self._try_scheduled_update, daemon=True)
                    thread.start()
                
    def _try_scheduled_update(self):
        """Пытается выполнить отложенное обновление"""
        with self._readers_lock:
            if not self._update_scheduled:
                return
            if self._readers_count > 0:
                return  # Всё ещё есть читатели
        
        # Нет читателей и есть отложенное обновление - запускаем
        self._update_scheduled = False
        self._start_background_check(silent=True)
    
    def _start_background_check(self, silent=False):
        """Запускает фоновую проверку, если она не выполняется."""
        if self._background_running is None:
            self._background_running = False
        
        if not self._background_running and self._background_lock.acquire(blocking=False):
            try:
                self._background_running = True
                # Передаём silent в target через lambda
                thread = threading.Thread(
                    target=lambda: self.background_check(silent=silent), 
                    daemon=True
                )
                thread.start()
            except:
                self._background_running = False
                self._background_lock.release()
                
    def start_background_check(self, silent=False):
        """
        ПУБЛИЧНЫЙ МЕТОД для запуска фоновой проверки извне.
        
        Args:
            silent: Если True - не показывать уведомления в UI
        """
        if not silent and self.status_callback:
            self._notify_status("🔄 Проверка обновлений базы заказов...")
        self._start_background_check(silent=silent)
    
    def background_check(self, silent=False):
        """
        ФОНОВАЯ ПРОВЕРКА ПАПКИ XML (ОБНОВЛЕНИЕ БАЗЫ)
        
        Примечания:
        - Использует блокировку для потокобезопасности
        - При ошибках БД не падает, а уведомляет пользователя
        - Статистика логируется только при наличии изменений
        """
        # Проверяем, есть ли активные читатели
        with self._readers_lock:
            if self._readers_count > 0:
                # Есть чтения - откладываем обновление
                self._update_scheduled = True
                logging.info(f"Обновление отложено: {self._readers_count} активных чтений")
                
                # Можно показать сообщение в UI, если это явный запрос
                if not silent:
                    self._notify_status("⏳ Обновление отложено: база используется")
                return
            
            # Нет читателей - можем обновлять
            self._update_scheduled = False
        
        # Захватываем блокировку записи
        with self._write_lock:
            try:
                # Проверка доступности источника
                if not self._check_xml_source_available():
                    self._notify_status("⚠️ Источник XML недоступен")
                    return
                
                with self._lock:  # Блокировка для потокобезопасности
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    
                    # Получение текущего состояния бд
                    cursor.execute("SELECT file_name, file_hash, last_modified FROM orders")
                    db_files = {row[0]: (row[1], row[2]) for row in cursor.fetchall()}
                    
                    # Инициализация статистики (только для новых/изменённых файлов)
                    new_emission_orders = set()          # Заказы с датой эмиссии
                    new_solmark_orders = set()           # Solmark заказы (ID 321)
                    new_multi_customer_orders = []       # Заказы с множественными заказчиками
                    processed_files = 0                  # Счётчик обработанных файлов
                    new_diameter_orders = set()
                    new_labels_per_roll_orders = set()
                    new_aggregation_orders = set()
                    
                    # Сканирование файловой системы
                    xml_files = list(self.xml_folder.glob("*.xml"))
                    
                    for file_path in xml_files:
                        file_name = file_path.name
                        
                        try:
                            # Пропускаем если файл недоступен
                            if not file_path.exists():
                                continue
                            
                            # Получаем метаданные файла
                            file_hash = self._calculate_file_hash(file_path)
                            last_modified = file_path.stat().st_mtime
                            
                            # Определение типа изменения
                            needs_processing = False
                            
                            if file_name not in db_files:
                                # СЛУЧАЙ 1: Новый файл (отсутствует в БД)
                                needs_processing = True
                            else:
                                # СЛУЧАЙ 2: Изменённый файл (разный хэш или дата)
                                db_hash, db_mtime = db_files[file_name]
                                if file_hash != db_hash or abs(last_modified - db_mtime) > 1:
                                    needs_processing = True
                            
                            # Обработка файла (если требуется)
                            if needs_processing:
                                # Парсинг XML
                                parsed_data = self._parse_xml_file(file_path)
                                if not parsed_data:
                                    continue  # Пропускаем невалидные файлы
                                
                                # Сохранение в БД
                                if self._save_order_to_db(conn, file_path, parsed_data, file_hash):
                                    logging.info(f"Добавлен новый заказ: {file_name}")
                                    processed_files += 1
                                    # Сбор статистики для обработанного файла
                                    self._collect_statistics_for_file(
                                        parsed_data=parsed_data,
                                        emission_set=new_emission_orders,
                                        solmark_set=new_solmark_orders,
                                        multi_customer_list=new_multi_customer_orders,
                                        diameter_set=new_diameter_orders,
                                        labels_set=new_labels_per_roll_orders,
                                        aggregation_set=new_aggregation_orders
                                    )

                        except (PermissionError, FileNotFoundError) as e:
                            # Файл недоступен или удалён во время обработки
                            continue  # Пропускаем без паники
                        except Exception as e:
                            # Любая другая ошибка при обработке файла
                            continue  # Пропускаем проблемный файл
                    
                    # Фиксация изменений в бд
                    conn.commit()
                    
                    # Обработка результатов
                    if processed_files > 0:
                        # Сохраняем статистику для логирования
                        self._emission_orders = new_emission_orders
                        self._solmark_orders = new_solmark_orders
                        self._multi_customer_orders = new_multi_customer_orders
                        self._processed_files = processed_files
                        self._diameter_orders = new_diameter_orders
                        self._labels_per_roll_orders = new_labels_per_roll_orders
                        self._aggregation_orders = new_aggregation_orders
                        
                        # Логирование итоговой статистики (всегда в файл)
                        self._log_collected_statistics("обновление")
                        
                        # Уведомляем UI только если НЕ silent
                        if not silent:
                            status_parts = []
                            if new_emission_orders:
                                status_parts.append(f"📅 {len(new_emission_orders)} с датой эмиссии")
                            if new_solmark_orders:
                                status_parts.append(f"🖨 {len(new_solmark_orders)} Solmark")
                            if new_multi_customer_orders:
                                status_parts.append(f"👥 {len(new_multi_customer_orders)} с многими заказчиками")
                            
                            if status_parts:
                                status_msg = f"Обновлено {processed_files} файлов ({', '.join(status_parts)})"
                            else:
                                status_msg = f"Обновлено {processed_files} файлов"
                            
                            self._notify_status(status_msg)
                
            except sqlite3.Error as e:
                # Ошибка базы данных
                logging.error(f"SQLite ошибка в background_check: {e}")
                self._notify_status("⚠️ Ошибка обновления базы данных")
                
            except Exception as e:
                # Непредвиденная ошибка
                logging.error(f"Непредвиденная ошибка в background_check: {e}")
                self._notify_status("⚠️ Ошибка при проверке файлов")
                
            finally:
                # Гарантированная очистка ресурсов
                if 'conn' in locals():
                    try:
                        conn.close()
                    except:
                        pass
                    
                    if not silent and self.status_callback:
                        self._notify_status("✅ Проверка обновлений завершена")
                
                # Сброс флага выполнения
                self._background_running = False
                if hasattr(self, '_background_lock'):
                    try:
                        self._background_lock.release()
                    except:
                        pass
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Статистика: файлов в кэше, размер БД, время последнего обновления
        """
        try:
            with self._lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Количество файлов в кэше
                cursor.execute("SELECT COUNT(*) FROM orders")
                file_count = cursor.fetchone()[0]
                
                # Количество уникальных заказов
                cursor.execute("SELECT COUNT(DISTINCT order_number) FROM orders")
                order_count = cursor.fetchone()[0]
                
                # Время последнего обновления
                cursor.execute("SELECT MAX(cached_at) FROM orders")
                last_update_timestamp = cursor.fetchone()[0]
                
                # Размер БД
                db_size = self.db_path.stat().st_size if self.db_path.exists() else 0
                
                conn.close()
                
                # Форматируем время
                last_update = "никогда"
                if last_update_timestamp:
                    last_update = datetime.fromtimestamp(last_update_timestamp).strftime('%Y-%m-%d %H:%M:%S')
                
                return {
                    'files_in_cache': file_count,
                    'unique_orders': order_count,
                    'last_update': last_update,
                    'db_size_mb': round(db_size / (1024 * 1024), 2),
                    'xml_folder': str(self.xml_folder),
                    'xml_folder_exists': self.xml_folder.exists()
                }
                
        except Exception as e:
            logging.error(f"Ошибка получения статистики: {e}")
            return {
                'files_in_cache': 0,
                'unique_orders': 0,
                'last_update': 'ошибка',
                'db_size_mb': 0,
                'xml_folder': str(self.xml_folder),
                'xml_folder_exists': self.xml_folder.exists()
            }
    
    def clear_cache(self) -> bool:
        """Очищает весь кэш."""
        try:
            with self._lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM orders")
                cursor.execute("DELETE FROM products")
                cursor.execute("DELETE FROM sheets")
                conn.commit()
                conn.close()
                
                logging.info("Кэш полностью очищен")
                return True
                
        except Exception as e:
            logging.error(f"Ошибка очистки кэша: {e}")
            return False


# Фабричная функция для удобства использования
def create_data_manager(config_manager):
    """Создаёт экземпляр XMLDataManager."""
    return XMLDataManager(config_manager)