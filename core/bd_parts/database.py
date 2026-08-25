"""
Модуль database.py - DAO слой для работы с SQLite базой данных заказов.
Содержит класс OrderRepository для всех операций с БД.
"""

import json
import logging
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set


@dataclass
class FileMetadata:
    """Метаданные файла из БД"""
    file_hash: str
    last_modified: float


# noinspection PyTypeChecker,PyArgumentList
class OrderRepository:
    """
    Репозиторий для работы с базой данных заказов.
    Предоставляет методы для CRUD операций и поиска.
    Потокобезопасен.
    """
    
    def __init__(self, db_path: Path):
        """
        Инициализация репозитория.
        
        Args:
            db_path: Путь к файлу базы данных SQLite
        """
        self.db_path = db_path
        self._logger = logging.getLogger(__name__)

    @contextmanager
    def _connection(self):
        """
        Контекстный менеджер для работы с БД.
        Автоматически управляет транзакциями и соединением.

        Особенности:
        - Использует WAL-режим для параллельных чтений/записей
        - Тайм-аут ожидания 3 секунды при блокировках
        - Автоматический commit/rollback

        Yields:
            sqlite3.Connection: Активное соединение с БД
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)

            # Настройки для производительности
            conn.execute("PRAGMA journal_mode=WAL")  # WAL-режим
            conn.execute("PRAGMA synchronous=NORMAL")  # Баланс скорость/безопасность
            conn.execute("PRAGMA busy_timeout=3000")  # Таймаут 3 сек

            yield conn
            conn.commit()

        except Exception as e:
            if conn:
                conn.rollback()
            self._logger.error(f"Ошибка в транзакции БД: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def init_database(self) -> None:
        """
        Инициализация базы данных: создание таблиц и индексов.
        Если БД повреждена - восстанавливает.
        """
        try:
            with self._connection() as conn:
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
                
                # Таблица products (для поиска по деталям)
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
                        sheet_number TEXT,
                        sheet_full_name TEXT,
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
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_sheet_full_name ON products(sheet_full_name)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_order ON products(order_file)")
                
                # Проверяем наличие колонки sheet_full_name
                cursor.execute("PRAGMA table_info(products)")
                columns = [col[1] for col in cursor.fetchall()]
                
                if 'sheet_full_name' not in columns:
                    cursor.execute("ALTER TABLE products ADD COLUMN sheet_full_name TEXT")
                    self._logger.info("Добавлена колонка sheet_full_name в таблицу products")
                
                # Проверяем наличие колонки order_name
                cursor.execute("PRAGMA table_info(orders)")
                columns = [col[1] for col in cursor.fetchall()]
                
                if 'order_name' not in columns:
                    cursor.execute("ALTER TABLE orders ADD COLUMN order_name TEXT")
                    self._logger.info("Добавлена колонка order_name в таблицу orders")
                    
        except sqlite3.Error as e:
            self._logger.error(f"Ошибка инициализации БД: {e}")
            self.recreate_database()
    
    def recreate_database(self) -> None:
        """
        Пересоздание базы данных в случае повреждения.
        Создает бэкап поврежденной БД.
        """
        try:
            if self.db_path.exists():
                backup_path = self.db_path.with_suffix('.db_cut.bak')
                self.db_path.rename(backup_path)
                self._logger.warning(f"БД повреждена. Создан бэкап: {backup_path}")
            
            # Пересоздаём с нуля
            self.init_database()
            self._logger.info("База данных пересоздана")
            
        except Exception as e:
            self._logger.error(f"Критическая ошибка восстановления БД: {e}")
            raise
    
    def save_order(self, file_path: Path, parsed_data: Dict[str, Any], 
                   file_hash: str) -> bool:
        """
        Сохраняет или обновляет заказ в БД.
        
        Args:
            file_path: Путь к XML файлу
            parsed_data: Распарсенные данные заказа
            file_hash: MD5 хэш файла
            
        Returns:
            True если сохранено успешно, False в случае ошибки
        """
        try:
            with self._connection() as conn:
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
                     order_name, order_manager, customer, executor, tu_number, 
                     parsed_data, file_hash, last_modified, cached_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, order_data)
                
                # Удаляем старые записи для этого файла
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
                        product.get('sheet_number', ''),
                        product.get('sheet_full_name', ''),
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
                    
                    if sheet_num:
                        if sheet_num not in sheet_data:
                            sheet_data[sheet_num] = []
                        if sheet_full_name:
                            sheet_data[sheet_num].append(sheet_full_name)
                
                for sheet_num, full_names in sheet_data.items():
                    sheet_full_name = full_names[0] if full_names else f"Тиражи I-{sheet_num}"
                    cursor.execute("""
                        INSERT OR REPLACE INTO sheets (order_file, sheet_number, sheet_name)
                        VALUES (?, ?, ?)
                    """, (file_name, sheet_num, sheet_full_name))
                
                return True
                
        except sqlite3.Error as e:
            self._logger.error(f"Ошибка сохранения {file_path} в БД: {e}")
            return False
    
    def get_orders_with_customers(self, order_numbers: Set[str]) -> Dict[str, str]:
        """
        Получает словарь {номер_заказа: заказчик} для переданных номеров.
        
        Args:
            order_numbers: Множество номеров заказов
            
        Returns:
            Словарь {номер_заказа: заказчик}
        """
        if not order_numbers:
            return {}
        
        try:
            with self._connection() as conn:
                cursor = conn.cursor()
                placeholders = ','.join('?' for _ in order_numbers)
                query = f"""
                    SELECT order_number, customer 
                    FROM orders 
                    WHERE order_number IN ({placeholders})
                """
                cursor.execute(query, list(order_numbers))
                results = cursor.fetchall()
                return {row[0]: row[1] for row in results}
                
        except sqlite3.Error as e:
            self._logger.error(f"Ошибка получения заказчиков: {e}")
            return {}
    
    def search_orders(self, order_query: str, sheet_query: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Поиск заказов по номеру и опционально по оттиску.
        
        Args:
            order_query: Номер заказа (или его часть)
            sheet_query: Номер оттиска для фильтрации (опционально)
            
        Returns:
            Список словарей с данными заказов (формат parse_xml)
        """
        try:
            with self._connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Нормализуем запрос: удаляем всё кроме цифр
                order_digits = ''.join(filter(str.isdigit, order_query))
                
                if not order_digits:
                    return []
                
                # Базовый запрос
                if sheet_query:
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
                        parsed_data = json.loads(row['parsed_data'])
                        
                        # Если нужна фильтрация по продуктам
                        if sheet_query and 'products' in parsed_data:
                            sheet_digits = ''.join(filter(str.isdigit, sheet_query))
                            filtered_products = []
                            
                            for product in parsed_data['products']:
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
                            
                            if filtered_products:
                                parsed_data['products'] = filtered_products
                                results.append(parsed_data)
                        else:
                            results.append(parsed_data)
                            
                    except json.JSONDecodeError as e:
                        self._logger.error(f"Ошибка декодирования JSON для {row['file_name']}: {e}")
                
                return results
                
        except sqlite3.Error as e:
            self._logger.error(f"Ошибка поиска в БД: {e}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Получает статистику о базе данных.
        
        Returns:
            Словарь со статистикой
        """
        try:
            with self._connection() as conn:
                cursor = conn.cursor()
                
                stats = {}
                
                # Общее количество заказов
                cursor.execute("SELECT COUNT(*) FROM orders")
                stats['total_orders'] = cursor.fetchone()[0]
                
                # Количество уникальных заказчиков
                cursor.execute("SELECT COUNT(DISTINCT customer) FROM orders WHERE customer IS NOT NULL AND customer != ''")
                stats['unique_customers'] = cursor.fetchone()[0]
                
                # Количество продуктов
                cursor.execute("SELECT COUNT(*) FROM products")
                stats['total_products'] = cursor.fetchone()[0]
                
                # Размер БД в байтах
                if self.db_path.exists():
                    stats['db_size_bytes'] = self.db_path.stat().st_size
                else:
                    stats['db_size_bytes'] = 0
                
                return stats
                
        except sqlite3.Error as e:
            self._logger.error(f"Ошибка получения статистики: {e}")
            return {}
    
    def clear_cache(self) -> None:
        """Очищает все таблицы базы данных."""
        try:
            with self._connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM orders")
                cursor.execute("DELETE FROM products")
                cursor.execute("DELETE FROM sheets")
                self._logger.info("База данных очищена")
                
        except sqlite3.Error as e:
            self._logger.error(f"Ошибка очистки БД: {e}")
            raise
    
    def get_all_files_metadata(self) -> Dict[str, Tuple[str, float]]:
        """
        Получает метаданные всех файлов в БД.
        
        Returns:
            Словарь {file_name: (file_hash, last_modified)}
        """
        try:
            with self._connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT file_name, file_hash, last_modified FROM orders")
                results = cursor.fetchall()
                return {row[0]: (row[1], row[2]) for row in results}
                
        except sqlite3.Error as e:
            self._logger.error(f"Ошибка получения метаданных: {e}")
            return {}
    
    def order_exists(self, file_name: str) -> bool:
        """
        Проверяет существование заказа в БД.
        
        Args:
            file_name: Имя файла заказа
            
        Returns:
            True если заказ существует
        """
        try:
            with self._connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM orders WHERE file_name = ?", (file_name,))
                return cursor.fetchone() is not None
                
        except sqlite3.Error as e:
            self._logger.error(f"Ошибка проверки существования заказа {file_name}: {e}")
            return False
    
    def delete_order(self, file_name: str) -> bool:
        """
        Удаляет заказ из БД.
        
        Args:
            file_name: Имя файла заказа
            
        Returns:
            True если удаление успешно
        """
        try:
            with self._connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM orders WHERE file_name = ?", (file_name,))
                cursor.execute("DELETE FROM products WHERE order_file = ?", (file_name,))
                cursor.execute("DELETE FROM sheets WHERE order_file = ?", (file_name,))
                return True
                
        except sqlite3.Error as e:
            self._logger.error(f"Ошибка удаления заказа {file_name}: {e}")
            return False
    
    def update_file_metadata(self, file_name: str, file_hash: str, last_modified: float) -> bool:
        """
        Обновляет метаданные файла.
        
        Args:
            file_name: Имя файла
            file_hash: Новый хэш
            last_modified: Новая дата модификации
            
        Returns:
            True если обновление успешно
        """
        try:
            with self._connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE orders 
                    SET file_hash = ?, last_modified = ?, cached_at = ? 
                    WHERE file_name = ?
                """, (file_hash, last_modified, time.time(), file_name))
                return cursor.rowcount > 0
                
        except sqlite3.Error as e:
            self._logger.error(f"Ошибка обновления метаданных {file_name}: {e}")
            return False