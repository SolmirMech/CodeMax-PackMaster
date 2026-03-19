# core/packaging/packaging_data_manager.py
import sqlite3
import threading


class PackagingDataManager:
    """Кэширующий слой БД для журнала упаковки (аналог XMLDataManager)"""

    def __init__(self, config_manager, coordinator=None):
        """
        Инициализация через ConfigManager.

        Args:
            config_manager: Экземпляр ConfigManager для получения путей
            coordinator: Координатор для подписки на уведомления
        """
        self.status_callback = None
        self.config = config_manager
        self.coordinator = coordinator

        # Путь к БД в папке data AppData
        self.db_path = config_manager.data_dir / "packaging.db"

        # Атрибуты для управления потоками (КОПИРУЕМ из XMLDataManager)
        self._readers_count = 0  # Счётчик активных читателей
        self._readers_lock = threading.RLock()  # Блокировка для счётчика
        self._write_lock = threading.RLock()  # Блокировка для записи
        self._lock = threading.RLock()  # Основная блокировка

        # Инициализация БД
        self._init_database()

        # Подписываемся на уведомления координатора
        if self.coordinator and hasattr(self.coordinator, 'subscribe'):
            self.coordinator.subscribe(self.on_settings_changed)

    def clear_database(self):
        """Полностью очищает таблицу packaging_log"""
        with self._write_lock:
            try:
                with self._lock:
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM packaging_log")
                    cursor.execute("VACUUM")  # сжимает файл БД
                    conn.commit()
                    return True
            except Exception as e:
                print(f"Ошибка очистки БД: {e}")
                return False
            finally:
                conn.close()
        
    def on_settings_changed(self, context=None):
        pass
        
    def set_status_callback(self, callback):
        """Устанавливает callback для отправки статусных сообщений в UI"""
        self.status_callback = callback

    def _init_database(self):
        """Инициализация БД для журнала упаковки"""
        with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                # Создаём таблицу packaging_log
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS packaging_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date TEXT,
                        order_number TEXT,
                        customer TEXT,
                        product_name TEXT,
                        quantity_labels INTEGER DEFAULT 0,
                        packer_name TEXT,
                        large_boxes INTEGER DEFAULT 0,
                        small_boxes INTEGER DEFAULT 0,
                        aquaLife_boxes INTEGER DEFAULT 0,
                        note TEXT,
                        exported INTEGER DEFAULT 0  -- 0 = не экспортирован, 1 = экспортирован
                    )
                """)

                # Индексы
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_pack_date ON packaging_log(date)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_pack_order ON packaging_log(order_number)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_pack_customer ON packaging_log(customer)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_pack_product ON packaging_log(product_name)")
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_pack_exported ON packaging_log(exported)")  # новый индекс

                conn.commit()

            except sqlite3.Error as e:
                print(f"Ошибка инициализации БД: {e}")
            finally:
                if 'conn' in locals():
                    conn.close()

    def get_unexported_entries(self):
        """Возвращает все неэкспортированные записи"""
        with self._readers_lock:
            self._readers_count += 1
        try:
            with self._lock:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM packaging_log 
                    WHERE exported = 0 
                    ORDER BY id ASC
                """)
                rows = cursor.fetchall()
                return [dict(row) for row in rows]  # Всегда возвращаем список
        except Exception as e:
            print(f"Ошибка в get_unexported_entries: {e}")
            return []  # При ошибке возвращаем пустой список
        finally:
            with self._readers_lock:
                self._readers_count -= 1
            conn.close()

    def mark_as_exported(self, entry_ids):
        """
        Помечает записи как экспортированные

        Args:
            entry_ids: список ID или одно число

        Returns:
            int: количество обновленных записей (0 если ничего не обновлено)
        """
        if not entry_ids:
            return 0  # Явно возвращаем 0, если нет ID

        if isinstance(entry_ids, (int, str)):
            entry_ids = [entry_ids]

        with self._write_lock:
            try:
                with self._lock:
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    placeholders = ','.join(['?'] * len(entry_ids))
                    cursor.execute(f"""
                        UPDATE packaging_log 
                        SET exported = 1 
                        WHERE id IN ({placeholders})
                    """, entry_ids)
                    conn.commit()
                    updated = cursor.rowcount
                    return updated  # Всегда возвращаем число
            except Exception as e:
                print(f"Ошибка в mark_as_exported: {e}")
                return 0  # Возвращаем 0 при ошибке
            finally:
                conn.close()

    def get_recent(self, limit=10):
        """Последние записи - копируем блокировки и подход из XMLDataManager"""
        with self._readers_lock:
            self._readers_count += 1
        try:
            with self._lock:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM packaging_log 
                    ORDER BY id DESC 
                    LIMIT ?
                """, (limit,))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        finally:
            with self._readers_lock:
                self._readers_count -= 1
            conn.close()

    def search(self, filters):
        """Поиск по одному или нескольким полям - копируем подход с блокировками"""
        with self._readers_lock:
            self._readers_count += 1
        try:
            with self._lock:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                query = "SELECT * FROM packaging_log WHERE 1=1"
                params = []

                for key, value in filters.items():
                    if key == 'date':
                        query += " AND date = ?"
                        params.append(value)
                    elif key in ['order_number', 'customer', 'product_name']:
                        query += f" AND {key} LIKE ?"
                        params.append(f'%{value}%')

                query += " ORDER BY id DESC"

                cursor.execute(query, params)
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        finally:
            with self._readers_lock:
                self._readers_count -= 1
            conn.close()

    def update_entry(self, entry_id, field, value):
        """Обновление конкретной ячейки - с блокировкой записи"""
        with self._write_lock:
            try:
                with self._lock:
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    cursor.execute(f"UPDATE packaging_log SET {field} = ? WHERE id = ?", (value, entry_id))
                    conn.commit()
                    return cursor.rowcount > 0
            finally:
                conn.close()

    def add_entry(self, data):
        """Добавление новой записи - exported всегда 0"""
        with self._write_lock:
            try:
                with self._lock:
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO packaging_log 
                        (date, order_number, customer, product_name, quantity_labels, 
                         packer_name, large_boxes, small_boxes, aquaLife_boxes, note, exported)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)  -- exported = 0
                    """, (
                        data.get('date', ''),
                        data.get('order_number', ''),
                        data.get('customer', ''),
                        data.get('product_name', ''),
                        data.get('quantity_labels') if data.get('quantity_labels') not in (None, '') else None,
                        data.get('packer_name', ''),
                        data.get('large_boxes') if data.get('large_boxes') not in (None, '') else None,
                        data.get('small_boxes') if data.get('small_boxes') not in (None, '') else None,
                        data.get('aquaLife_boxes') if data.get('aquaLife_boxes') not in (None, '') else None,
                        data.get('note', '')
                    ))
                    conn.commit()
                    return cursor.lastrowid
            finally:
                conn.close()

    def delete_entry(self, entry_id):
        """Удаление записи - с блокировкой записи"""
        with self._write_lock:
            try:
                with self._lock:
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM packaging_log WHERE id = ?", (entry_id,))
                    conn.commit()
                    return cursor.rowcount > 0
            finally:
                conn.close()
