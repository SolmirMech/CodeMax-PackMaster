"""
Модуль data_manager.py - кэширующий слой для работы с XML-файлами заказов.
Ускоряет поиск в 100+ раз за счет использования SQLite базы данных.
"""

import sqlite3
import json
import hashlib
import logging
import time
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

# Импорт существующего парсера
from core.parse.xml_order_parser import parse_xml


class XMLDataManager:
    """
    Кэширующий менеджер данных для работы с XML-файлами заказов.
    Прозрачно заменяет прямой парсинг XML на поиск из БД.
    """
    
    def __init__(self, config_manager):
        """
        Инициализация через существующий ConfigManager.
        
        Args:
            config_manager: Экземпляр ConfigManager для получения путей
        """
        self.config = config_manager
        self.status_callback = None
        
        # Получаем путь к XML заказам
        xml_path = config_manager.get_weight_data_base_path()
        self.xml_folder = Path(xml_path)
        
        # Путь к БД в папке data AppData
        self.db_path = config_manager.data_dir / "orders_cache.db"
        
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
        
        logging.info(f"DataManager инициализирован. XML папка: {self.xml_folder}")
        logging.info(f"БД: {self.db_path}")
        
    def set_status_callback(self, callback):
        """Устанавливает callback для отправки статусных сообщений в UI"""
        self.status_callback = callback
    
    def _notify_status(self, message: str):
        """Отправляет статусное сообщение в UI"""
        if self.status_callback:
            try:
                self.status_callback(message)
            except Exception as e:
                logging.error(f"Ошибка вызова callback: {e}")
    
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
                
                conn.commit()
                logging.info("База данных инициализирована")
                
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
                        import chardet
                        encoding = chardet.detect(raw_data)['encoding'] or 'windows-1251'
                        content = raw_data.decode(encoding)
                    except:
                        content = raw_data.decode('utf-8', errors='ignore')
            
            # Парсим через существующий парсер
            parsed_data = parse_xml(content)
            
            # Собираем статистику
            self._analyze_and_log_statistics(parsed_data, file_path.name)
            
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
            
    def _analyze_and_log_statistics(self, parsed_data: Dict[str, Any], file_name: str):
        """
        Анализирует данные и сразу логирует ВСЕ статистические случаи.
        """
        # 1. Множественные заказчики
        customer_info = parsed_data.get('_customer_info', {})
        if customer_info.get('has_multiple', False):
            all_customers = customer_info.get('all_customers', [])
            chosen_customer = customer_info.get('customer', '')
            
            logging.info(
                f"МНОГИЕ ЗАКАЗЧИКИ | Файл: {file_name} | "
                f"Всего заказчиков: {len(all_customers)} | "
                f"Выбран: {chosen_customer} | "
                f"Список: {', '.join(all_customers)}"
            )
        
        # 2. Даты эмиссии - просто факт наличия
        products = parsed_data.get('products', [])
        has_emission_date = False
        
        for product in products:
            if product.get('date_emission', ''):
                has_emission_date = True
                break
        
        if has_emission_date:
            logging.info(f"ДАТА ЭМИССИИ | Файл: {file_name}")
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Вычисляет MD5 хэш файла для отслеживания изменений."""
        try:
            file_content = file_path.read_bytes()
            return hashlib.md5(file_content).hexdigest()
        except Exception as e:
            logging.error(f"Ошибка вычисления хэша для {file_path}: {e}")
            return ""
    
    def _save_order_to_db(self, conn: sqlite3.Connection, file_path: Path, 
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
                 customer, executor, tu_number, parsed_data, file_hash, 
                 last_modified, cached_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    product.get('sheet_full_name', ''),    # ← НОВОЕ: полное название оттиска
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
        ПЕРВИЧНОЕ СКАНИРОВАНИЕ
        Вызывается при запуске программы (можно в фоне)
        Заполняет БД при первом запуске
        """
        def scan_in_background():
            try:
                logging.info("Начато первичное сканирование папки XML")
                
                # Проверяем есть ли данные в бд
                with self._lock:
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM orders")
                    count = cursor.fetchone()[0]
                    conn.close()
                
                if count > 0:
                    logging.info(f"БД уже содержит {count} записей. Пропускаем полное сканирование.")
                    self._notify_status(f"База загружена ({count} записей)")
                    return
                
                self._notify_status("Проверка доступности источника XML...")
                
                # Проверяем доступность папки с таймаутом
                if not self._check_xml_source_available():
                    self._notify_status("⚠️ Источник XML недоступен")
                    logging.error(f"Папка XML недоступна: {self.xml_folder}")
                    return
                
                self._notify_status("Сканирование источника XML...")
                
                # Считаем файлы для прогресса
                xml_files = list(self.xml_folder.glob("*.xml"))
                total_files = len(xml_files)
                logging.info(f"Найдено XML файлов: {total_files}")
                
                if total_files == 0:
                    logging.warning("В папке XML не найдено файлов")
                    self._notify_status("⚠️ В источнике нет XML файлов")
                    return
                
                self._notify_status(f"Обработка {total_files} файлов...")
                
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
                batch_size = 50  # Отправляем статус каждые N файлов
                
                for i, file_path in enumerate(xml_files):
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
                        
                        # Отправляем промежуточный статус
                        if (i + 1) % batch_size == 0 or (i + 1) == total_files:
                            self._notify_status(f"Загружено {i + 1}/{total_files} файлов...")
                    
                    except Exception as e:
                        errors += 1
                        logging.error(f"Ошибка обработки {file_path.name}: {e}")
                
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
    
    def _check_xml_source_available(self) -> bool:
        """
        Проверяет доступность источника XML с таймаутом.
        
        Returns:
            True если источник доступен, False если недоступен
        """
        import threading
        
        def check_folder():
            try:
                # Простая проверка существования папки
                return self.xml_folder.exists()
            except:
                return False
        
        # Создаём поток с таймаутом
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
        ОСНОВНОЙ МЕТОД ДЛЯ UI
        Ищет заказы по номеру + фильтр по оттиску
        Возвращает список словарей в ТОЧНОМ формате parse_xml()
        
        Args:
            order_query: Номер заказа (или его часть)
            sheet_query: Номер оттиска для фильтрации (опционально)
            
        Returns:
            Список словарей с данными заказов
        """
        start_time = time.time()
        
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
                
                # Запускаем фоновую проверку
                self._start_background_check()
                
                elapsed = (time.time() - start_time) * 1000
                logging.debug(f"Поиск '{order_query}' выполнен за {elapsed:.1f} мс. Найдено: {len(results)}")
                
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
    
    def _start_background_check(self):
        """Запускает фоновую проверку, если она не выполняется."""
        if not hasattr(self, '_background_running'):
            self._background_running = False
        
        if not self._background_running and self._background_lock.acquire(blocking=False):
            try:
                self._background_running = True
                thread = threading.Thread(target=self.background_check, daemon=True)
                thread.start()
            except:
                self._background_running = False
                self._background_lock.release()
    
    def background_check(self) -> None:
        """
        ФОНОВАЯ ПРОВЕРКА ПАПКИ
        Вызывается после поиска, не блокирует UI
        Проверяет новые/изменённые XML, НЕ удаляет отсутствующие
        """
        try:
            logging.info("Запущена фоновая проверка папки XML")
            
            # Быстрая проверка доступности
            if not self._check_xml_source_available():
                logging.warning(f"Папка XML недоступна: {self.xml_folder}")
                self._notify_status("⚠️ Источник недоступен")
                return
            
            with self._lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Получаем текущее состояние БД
                cursor.execute("SELECT file_name, file_hash, last_modified FROM orders")
                db_files = {row[0]: (row[1], row[2]) for row in cursor.fetchall()}
                
                # Сканируем файловую систему
                fs_files = {}
                xml_files = list(self.xml_folder.glob("*.xml"))
                
                for file_path in xml_files:
                    file_name = file_path.name
                    try:
                        file_hash = self._calculate_file_hash(file_path)
                        last_modified = file_path.stat().st_mtime
                        fs_files[file_name] = (file_hash, last_modified, file_path)
                    except Exception as e:
                        logging.error(f"Ошибка чтения {file_name}: {e}")
                
                # Определяем действия
                added = 0
                updated = 0
                
                # 1. Проверяем новые и изменённые файлы
                for file_name, (fs_hash, fs_mtime, file_path) in fs_files.items():
                    if file_name not in db_files:
                        # Новый файл
                        parsed_data = self._parse_xml_file(file_path)
                        if parsed_data and self._save_order_to_db(conn, file_path, parsed_data, fs_hash):
                            added += 1
                            logging.info(f"Добавлен новый файл: {file_name}")
                    
                    else:
                        db_hash, db_mtime = db_files[file_name]
                        if fs_hash != db_hash or abs(fs_mtime - db_mtime) > 1:
                            # Изменённый файл
                            parsed_data = self._parse_xml_file(file_path)
                            if parsed_data and self._save_order_to_db(conn, file_path, parsed_data, fs_hash):
                                updated += 1
                                logging.info(f"Обновлён изменённый файл: {file_name}")
                
                conn.commit()
                
                # Уведомляем о результатах
                if added > 0 or updated > 0:
                    status_msg = ""
                    if added > 0:
                        status_msg += f"➕ {added} новых"
                    if updated > 0:
                        if status_msg:
                            status_msg += ", "
                        status_msg += f"✏️ {updated} изменённых"
                    
                    self._notify_status(f"Обновлено: {status_msg}")
                    logging.info(f"Фоновая проверка: {status_msg}")
                else:
                    logging.debug("Фоновая проверка: изменений не обнаружено")
                
        except Exception as e:
            logging.error(f"Ошибка фоновой проверки: {e}")
        finally:
            if 'conn' in locals():
                conn.close()
            self._background_running = False
            if hasattr(self, '_background_lock') and hasattr(self._background_lock, 'locked'):
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