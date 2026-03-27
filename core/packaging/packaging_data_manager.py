# core/packaging/packaging_data_manager.py
import sqlite3
import threading
import os
import time


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

        # Определяем текущий цех
        if coordinator:
            workshop_id = coordinator.get_workshop()
        else:
            workshop_id = "1"

        # Путь к сетевой БД (рядом с Excel-журналом)
        excel_path = self.config.get_packaging_log_path()
        if excel_path:
            network_dir = os.path.dirname(excel_path)
            self.network_db_path = os.path.join(network_dir, f"packaging_{workshop_id}_cex.db")
        else:
            self.network_db_path = None

        # Путь к локальной БД-бэкапу
        self.local_backup_path = self.config.data_dir / f"packaging_{workshop_id}_cex_local.db"

        # Атрибуты для управления потоками
        self._readers_count = 0  # Счётчик активных читателей
        self._readers_lock = threading.RLock()  # Блокировка для счётчика
        self._write_lock = threading.RLock()  # Блокировка для записи
        self._lock = threading.RLock()  # Основная блокировка

        # Проверка цеха
        self.workshop_id = None
        self._update_workshop()
        # Инициализация БД
        self._init_network_database()
        # Инициализация локальной БД (бэкап)
        self._init_local_backup()

        # Синхронизация при старте
        if self._is_network_available():
            synced = self._sync_local_to_network()
            if synced > 0 and self.status_callback:
                self.status_callback(f"Синхронизировано {synced} записей")

        # Подписываемся на уведомления координатора
        if self.coordinator and hasattr(self.coordinator, 'subscribe'):
            self.coordinator.subscribe(self.on_settings_changed)

    def refresh_paths(self):
        """Обновляет пути к БД после изменения Excel файла"""
        self._update_workshop()
        self._init_network_database()
        self._init_local_backup()

        # Синхронизация при обновлении
        if self._is_network_available():
            synced = self._sync_local_to_network()
            if synced > 0 and self.status_callback:
                self.status_callback(f"Синхронизировано {synced} записей")

    @staticmethod
    def _execute_with_retry(operation, max_retries=3):
        """Выполняет операцию с повторными попытками при блокировке"""
        for attempt in range(max_retries):
            try:
                return operation()
            except sqlite3.OperationalError as e:
                if "locked" in str(e) and attempt < max_retries - 1:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                raise
        # Эта строка никогда не выполнится, но для статического анализа
        return None

    def _execute_on_network(self, operation, with_backup=False):
        """Выполняет операцию на сетевой БД с повторными попытками"""
        if not self._is_network_available():
            return None

        with self._write_lock, self._lock:
            def wrapped():
                conn = sqlite3.connect(self.network_db_path)
                try:
                    result = operation(conn)
                    if with_backup:
                        self._backup_to_local()
                    return result
                finally:
                    conn.close()

            return self._execute_with_retry(wrapped)

    def _add_to_local_offline(self, data):
        """Добавляет запись в локальную БД с synced=0"""
        conn = sqlite3.connect(self.local_backup_path)
        try:
            cursor = conn.cursor()

            # Форматируем вес
            weight = data.get('weight_kg')
            if weight is not None and weight != '':
                try:
                    weight = round(float(weight), 1)
                except (ValueError, TypeError):
                    weight = None

            cursor.execute("""
                INSERT INTO packaging_log 
                (date, order_number, customer, product_name, quantity_labels, 
                 packer_name, weight_kg, col_1, col_2, col_3, col_4, col_5, col_6, col_7, col_8, col_9, col_10, note, 
                 exported, source_type, source_file, source_sheet, source_row, 
                 sheet_index, row_color, synced)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """, (
                data.get('date', ''),
                data.get('order_number', ''),
                data.get('customer', ''),
                data.get('product_name', ''),
                data.get('quantity_labels') if data.get('quantity_labels') not in (None, '') else None,
                data.get('packer_name', ''),
                weight,
                data.get('col_1') if data.get('col_1') not in (None, '') else None,
                data.get('col_2') if data.get('col_2') not in (None, '') else None,
                data.get('col_3') if data.get('col_3') not in (None, '') else None,
                data.get('col_4') if data.get('col_4') not in (None, '') else None,
                data.get('col_5') if data.get('col_5') not in (None, '') else None,
                data.get('col_6') if data.get('col_6') not in (None, '') else None,
                data.get('col_7') if data.get('col_7') not in (None, '') else None,
                data.get('col_8') if data.get('col_8') not in (None, '') else None,
                data.get('col_9') if data.get('col_9') not in (None, '') else None,
                data.get('col_10') if data.get('col_10') not in (None, '') else None,
                data.get('note', ''),
                0,  # exported = 0
                data.get('source_type', 'manual'),
                data.get('source_file', ''),
                data.get('source_sheet', ''),
                data.get('source_row'),
                data.get('sheet_index', 0),
                data.get('row_color')
            ))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def _backup_to_local(self):
        """Копирует сетевую БД в локальную (бэкап)"""
        if not self._is_network_available():
            return
        try:
            import shutil
            shutil.copy2(self.network_db_path, self.local_backup_path)
        except Exception as e:
            print(f"Ошибка бэкапа: {e}")

    def _sync_local_to_network(self):
        """Синхронизирует локальные записи (synced=0) в сетевую БД"""
        if not self._is_network_available():
            return 0

        conn_local = sqlite3.connect(self.local_backup_path)
        conn_network = sqlite3.connect(self.network_db_path)

        try:
            # Используем row_factory для получения dict
            conn_local.row_factory = sqlite3.Row
            cursor_local = conn_local.cursor()
            cursor_local.execute("SELECT * FROM packaging_log WHERE synced = 0 ORDER BY id ASC")
            rows = cursor_local.fetchall()

            if not rows:
                return 0

            cursor_network = conn_network.cursor()

            # Получаем список колонок сетевой БД (без id)
            cursor_network.execute("PRAGMA table_info(packaging_log)")
            network_columns = [col[1] for col in cursor_network.fetchall() if col[1] != 'id']

            for row in rows:
                # Преобразуем row в dict
                row_dict = dict(row)
                # Удаляем id из dict (он не нужен при вставке)
                row_dict.pop('id', None)

                # Оставляем только те поля, которые есть в сетевой БД
                filtered_dict = {k: v for k, v in row_dict.items() if k in network_columns}

                placeholders = ','.join(['?'] * len(filtered_dict))
                columns_str = ','.join(filtered_dict.keys())
                cursor_network.execute(
                    f"INSERT INTO packaging_log ({columns_str}) VALUES ({placeholders})",
                    list(filtered_dict.values())
                )

            conn_network.commit()
            synced_count = len(rows)

            # Удаляем синхронизированные из локальной
            cursor_local.execute("DELETE FROM packaging_log WHERE synced = 0")
            conn_local.commit()

            return synced_count

        except Exception as e:
            print(f"Ошибка синхронизации: {e}")
            return 0
        finally:
            conn_local.close()
            conn_network.close()

    def _is_network_available(self):
        """Проверяет доступность сетевой папки (не файла)"""
        if not self.network_db_path:
            return False
        try:
            network_dir = os.path.dirname(self.network_db_path)
            return os.path.exists(network_dir) and os.access(network_dir, os.R_OK | os.W_OK)
        except:
            return False

    def is_network_available(self):
        """Публичный метод проверки доступности сетевой БД"""
        return self._is_network_available()

    def _init_local_backup(self):
        """Инициализирует локальную БД-бэкап"""
        if not self.local_backup_path:
            return

        conn = sqlite3.connect(self.local_backup_path)
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS packaging_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT,
                    order_number TEXT,
                    customer TEXT,
                    product_name TEXT,
                    quantity_labels INTEGER DEFAULT 0,
                    packer_name TEXT,
                    weight_kg REAL DEFAULT 0,
                    col_1 INTEGER DEFAULT 0,
                    col_2 INTEGER DEFAULT 0,
                    col_3 INTEGER DEFAULT 0,
                    col_4 INTEGER DEFAULT 0,
                    col_5 INTEGER DEFAULT 0,
                    col_6 INTEGER DEFAULT 0,
                    col_7 INTEGER DEFAULT 0,
                    col_8 INTEGER DEFAULT 0,
                    col_9 INTEGER DEFAULT 0,
                    col_10 INTEGER DEFAULT 0,
                    note TEXT,
                    exported INTEGER DEFAULT 0 CHECK(exported IN (0,1,2)),
                    source_type TEXT DEFAULT 'manual',
                    source_file TEXT,
                    source_sheet TEXT,
                    source_row INTEGER,
                    sheet_index INTEGER DEFAULT 0,
                    restore_flag INTEGER DEFAULT 0,
                    row_color TEXT,
                    synced INTEGER DEFAULT 1
                )
            """)

            # Индексы
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pack_date ON packaging_log(date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pack_order ON packaging_log(order_number)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pack_customer ON packaging_log(customer)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pack_product ON packaging_log(product_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pack_exported ON packaging_log(exported)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pack_source ON packaging_log(source_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pack_sheet_index ON packaging_log(sheet_index)")

            conn.commit()
        finally:
            conn.close()

    def _update_workshop(self):
        """Определяем текущий цех и обновляем пути к БД"""
        if self.coordinator:
            self.workshop_id = self.coordinator.get_workshop()
        else:
            self.workshop_id = "1"

        # Обновляем путь к сетевой БД
        excel_path = self.config.get_packaging_log_path()
        if excel_path:
            network_dir = os.path.dirname(excel_path)
            self.network_db_path = os.path.join(network_dir, f"packaging_{self.workshop_id}_cex.db")
        else:
            self.network_db_path = None

        # Обновляем путь к локальной БД-бэкапу
        self.local_backup_path = self.config.data_dir / f"packaging_{self.workshop_id}_cex_local.db"

    def update_entry_with_coords(self, entry_id, field, value):
        """
        Обновление ячейки с сохранением координат и сбросом флага экспорта
        """
        if self._is_network_available():
            def operation(conn):
                cur = conn.cursor()
                cur.execute(
                    f"UPDATE packaging_log SET {field} = ?, exported = 0 WHERE id = ?",
                    (value, entry_id)
                )
                conn.commit()
                return cur.rowcount > 0
            return self._execute_on_network(operation, with_backup=True)
        else:
            # Офлайн-режим: обновляем в локальной БД только если запись не синхронизирована
            local_conn = sqlite3.connect(self.local_backup_path)
            try:
                local_cursor = local_conn.cursor()

                # Проверяем, можно ли обновлять
                local_cursor.execute("SELECT synced FROM packaging_log WHERE id = ?", (entry_id,))
                row = local_cursor.fetchone()

                if not row:
                    return False

                if row[0] == 1:
                    return False

                local_cursor.execute(f"""
                    UPDATE packaging_log 
                    SET {field} = ?, exported = 0 
                    WHERE id = ?
                """, (value, entry_id))

                local_conn.commit()
                return local_cursor.rowcount > 0
            finally:
                local_conn.close()

    def clear_database(self):
        """Полностью очищает БД и пересоздаёт таблицу с новой структурой"""
        if not self._is_network_available():
            # В офлайне нельзя очистить БД, т.к. данные могут быть не синхронизированы
            if self.status_callback:
                self.status_callback("Очистка БД недоступна в офлайн-режиме")
            return False

        def operation(conn):
            cur = conn.cursor()

            # Удаляем старую таблицу
            cur.execute("DROP TABLE IF EXISTS packaging_log")

            # Создаём заново с новой структурой
            cur.execute("""
                CREATE TABLE packaging_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT,
                    order_number TEXT,
                    customer TEXT,
                    product_name TEXT,
                    quantity_labels INTEGER DEFAULT 0,
                    packer_name TEXT,
                    weight_kg REAL DEFAULT 0,
                    col_1 INTEGER DEFAULT 0,
                    col_2 INTEGER DEFAULT 0,
                    col_3 INTEGER DEFAULT 0,
                    col_4 INTEGER DEFAULT 0,
                    col_5 INTEGER DEFAULT 0,
                    col_6 INTEGER DEFAULT 0,
                    col_7 INTEGER DEFAULT 0,
                    col_8 INTEGER DEFAULT 0,
                    col_9 INTEGER DEFAULT 0,
                    col_10 INTEGER DEFAULT 0,
                    note TEXT,
                    exported INTEGER DEFAULT 0,
                    source_type TEXT DEFAULT 'manual',
                    source_file TEXT,
                    source_sheet TEXT,
                    source_row INTEGER,
                    sheet_index INTEGER DEFAULT 0,
                    restore_flag INTEGER DEFAULT 0,
                    row_color TEXT,
                    synced INTEGER DEFAULT 1
                )
            """)

            # Индексы
            cur.execute("CREATE INDEX IF NOT EXISTS idx_pack_date ON packaging_log(date)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_pack_order ON packaging_log(order_number)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_pack_customer ON packaging_log(customer)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_pack_product ON packaging_log(product_name)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_pack_exported ON packaging_log(exported)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_pack_source ON packaging_log(source_type)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_pack_sheet_index ON packaging_log(sheet_index)")

            conn.commit()
            return True

        result = self._execute_on_network(operation, with_backup=True)
        return result if result is not None else False

    # noinspection PyUnusedLocal
    def on_settings_changed(self, context=None):
        """При смене цеха переключаем БД"""
        new_workshop = self.coordinator.get_workshop() if self.coordinator else "1"
        if new_workshop != self.workshop_id:
            self._update_workshop()  # ← обновляем путь
            # БД уже существует или создастся при первом обращении
        
    def set_status_callback(self, callback):
        """Устанавливает callback для отправки статусных сообщений в UI"""
        self.status_callback = callback

    def _init_network_database(self):
        """Инициализация сетевой БД для журнала упаковки"""
        if not self.network_db_path:
            return  # нечего инициализировать

        with self._lock:
            try:
                conn = sqlite3.connect(self.network_db_path)
                cursor = conn.cursor()

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS packaging_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date TEXT,
                        order_number TEXT,
                        customer TEXT,
                        product_name TEXT,
                        quantity_labels INTEGER DEFAULT 0,
                        packer_name TEXT,
                        weight_kg REAL DEFAULT 0,
                        col_1 INTEGER DEFAULT 0,
                        col_2 INTEGER DEFAULT 0,
                        col_3 INTEGER DEFAULT 0,
                        col_4 INTEGER DEFAULT 0,
                        col_5 INTEGER DEFAULT 0,
                        col_6 INTEGER DEFAULT 0,
                        col_7 INTEGER DEFAULT 0,
                        col_8 INTEGER DEFAULT 0,
                        col_9 INTEGER DEFAULT 0,
                        col_10 INTEGER DEFAULT 0,
                        note TEXT,
                        exported INTEGER DEFAULT 0 CHECK(exported IN (0,1,2)),
                        source_type TEXT DEFAULT 'manual',
                        source_file TEXT,
                        source_sheet TEXT,
                        source_row INTEGER,
                        sheet_index INTEGER DEFAULT 0,
                        restore_flag INTEGER DEFAULT 0,
                        row_color TEXT,
                        synced INTEGER DEFAULT 1
                    )
                """)

                # Индексы
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_pack_date ON packaging_log(date)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_pack_order ON packaging_log(order_number)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_pack_customer ON packaging_log(customer)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_pack_product ON packaging_log(product_name)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_pack_exported ON packaging_log(exported)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_pack_source ON packaging_log(source_type)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_pack_sheet_index ON packaging_log(sheet_index)")


                conn.commit()

            except sqlite3.Error as e:
                print(f"Ошибка инициализации БД: {e}")
            finally:
                if 'conn' in locals():
                    conn.close()

    def update_row_color(self, entry_id, hex_color):
        """Обновляет цвет строки и сбрасывает флаг экспорта"""
        if self._is_network_available():
            def operation(conn):
                cur = conn.cursor()
                cur.execute(
                    "UPDATE packaging_log SET row_color = ?, exported = 0 WHERE id = ?",
                    (hex_color, entry_id)
                )
                conn.commit()
                return cur.rowcount > 0
            return self._execute_on_network(operation, with_backup=True)
        else:
            # Офлайн-режим: обновляем в локальной только если запись не синхронизирована
            local_conn = sqlite3.connect(self.local_backup_path)
            try:
                local_cursor = local_conn.cursor()

                # Проверяем, можно ли обновлять
                local_cursor.execute("SELECT synced FROM packaging_log WHERE id = ?", (entry_id,))
                row = local_cursor.fetchone()

                if not row:
                    return False

                if row[0] == 1:
                    return False

                local_cursor.execute(
                    "UPDATE packaging_log SET row_color = ?, exported = 0 WHERE id = ?",
                    (hex_color, entry_id)
                )
                local_conn.commit()
                return local_cursor.rowcount > 0
            finally:
                local_conn.close()

    def get_row_color(self, entry_id):
        """Возвращает цвет строки"""
        if self._is_network_available():
            def operation(conn):
                cur = conn.cursor()
                cur.execute(
                    "SELECT row_color FROM packaging_log WHERE id = ?",
                    (entry_id,)
                )
                result_row = cur.fetchone()
                return result_row[0] if result_row else None
            result = self._execute_on_network(operation, with_backup=False)
            return result if result is not None else None
        else:
            local_conn = sqlite3.connect(self.local_backup_path)
            try:
                local_cursor = local_conn.cursor()
                local_cursor.execute(
                    "SELECT row_color FROM packaging_log WHERE id = ?",
                    (entry_id,)
                )
                local_row = local_cursor.fetchone()
                return local_row[0] if local_row else None
            finally:
                local_conn.close()

    def get_unexported_entries(self):
        """Возвращает все неэкспортированные записи"""
        if self._is_network_available():
            def operation(conn):
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                # Используем SELECT FOR UPDATE через BEGIN IMMEDIATE
                cur.execute("BEGIN IMMEDIATE")
                try:
                    cur.execute("""
                        SELECT * FROM packaging_log 
                        WHERE exported = 0 
                        ORDER BY id ASC
                    """)
                    result_rows = cur.fetchall()
                    # Мгновенно помечаем как экспортируемые
                    if result_rows:
                        ids = [row['id'] for row in result_rows]
                        placeholders = ','.join(['?'] * len(ids))
                        cur.execute(f"""
                            UPDATE packaging_log 
                            SET exported = 2 
                            WHERE id IN ({placeholders})
                        """, ids)
                        conn.commit()
                    return [dict(row) for row in result_rows]
                except:
                    conn.rollback()
                    raise

            result = self._execute_on_network(operation, with_backup=False)
            return result if result is not None else []
        else:
            # офлайн-режим без изменений
            local_conn = sqlite3.connect(self.local_backup_path)
            try:
                local_conn.row_factory = sqlite3.Row
                local_cursor = local_conn.cursor()
                local_cursor.execute("""
                    SELECT * FROM packaging_log 
                    WHERE exported = 0 
                    ORDER BY id ASC
                """)
                local_rows = local_cursor.fetchall()
                return [dict(row) for row in local_rows]
            except Exception as e:
                print(f"Ошибка в get_unexported_entries: {e}")
                return []
            finally:
                local_conn.close()

    def mark_as_exported(self, entry_ids, sheet_name=None):
        """
        Помечает записи как экспортированные и сохраняет имя листа

        Args:
            entry_ids: список ID или одно число
            sheet_name: имя листа, в который экспортировали

        Returns:
            int: количество обновленных записей
        """
        if not entry_ids:
            return 0

        if isinstance(entry_ids, (int, str)):
            entry_ids = [entry_ids]

        if self._is_network_available():
            def operation(conn):
                cur = conn.cursor()
                placeholders = ','.join(['?'] * len(entry_ids))
                if sheet_name:
                    cur.execute(f"""
                            UPDATE packaging_log 
                            SET exported = 1, source_sheet = ?, sheet_index = 0
                            WHERE id IN ({placeholders}) AND exported IN (0, 2)
                        """, [sheet_name] + entry_ids)
                else:
                    cur.execute(f"""
                            UPDATE packaging_log 
                            SET exported = 1
                            WHERE id IN ({placeholders}) AND exported IN (0, 2)
                        """, entry_ids)
                conn.commit()
                return cur.rowcount

            return self._execute_on_network(operation, with_backup=True)
        else:
            # Офлайн-режим: обновляем в локальной только если записи не синхронизированы
            local_conn = sqlite3.connect(self.local_backup_path)
            try:
                local_cursor = local_conn.cursor()
                local_placeholders = ','.join(['?'] * len(entry_ids))

                # Проверяем, все ли записи можно обновлять
                local_cursor.execute(f"SELECT id FROM packaging_log WHERE id IN ({local_placeholders}) AND synced = 1", entry_ids)
                synced_ids = [row[0] for row in local_cursor.fetchall()]

                if synced_ids:
                    # Есть синхронизированные записи, их нельзя менять в офлайне
                    return 0

                if sheet_name:
                    local_cursor.execute(f"""
                        UPDATE packaging_log 
                        SET exported = 1, source_sheet = ?, sheet_index = 0
                        WHERE id IN ({local_placeholders})
                    """, [sheet_name] + entry_ids)
                else:
                    local_cursor.execute(f"""
                        UPDATE packaging_log 
                        SET exported = 1
                        WHERE id IN ({local_placeholders})
                    """, entry_ids)

                local_conn.commit()
                return local_cursor.rowcount
            except Exception as e:
                print(f"Ошибка в mark_as_exported (офлайн): {e}")
                return 0
            finally:
                local_conn.close()

    def get_recent(self, limit=20):
        """Последние записи - с fallback на локальную БД"""
        if self._is_network_available():
            def operation(conn):
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute("""
                    SELECT * FROM packaging_log 
                    ORDER BY id DESC 
                    LIMIT ?
                """, (limit,))
                result_rows = cur.fetchall()
                return [dict(row) for row in result_rows]
            result = self._execute_on_network(operation, with_backup=False)
            return result if result is not None else []
        else:
            # Офлайн-режим
            local_conn = sqlite3.connect(self.local_backup_path)
            try:
                local_conn.row_factory = sqlite3.Row
                local_cursor = local_conn.cursor()
                local_cursor.execute("""
                    SELECT * FROM packaging_log 
                    ORDER BY id DESC 
                    LIMIT ?
                """, (limit,))
                local_rows = local_cursor.fetchall()
                return [dict(row) for row in local_rows]
            finally:
                local_conn.close()

    def search(self, filters):
        """Поиск записей по фильтрам"""
        if self._is_network_available():
            def operation(conn):
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()

                sql_query = "SELECT * FROM packaging_log WHERE 1=1"
                sql_params = []

                for f_key, f_value in filters.items():
                    if f_key == 'date':
                        sql_query += " AND date = ?"
                        sql_params.append(f_value)
                    elif f_key == 'id':
                        sql_query += " AND id = ?"
                        sql_params.append(f_value)
                    elif f_key in ['order_number', 'customer', 'product_name']:
                        sql_query += f" AND {f_key} LIKE ?"
                        sql_params.append(f'%{f_value}%')

                sql_query += " ORDER BY id DESC"

                cur.execute(sql_query, sql_params)
                result_rows = cur.fetchall()
                return [dict(row) for row in result_rows]

            result = self._execute_on_network(operation, with_backup=False)
            return result if result is not None else []
        else:
            # Офлайн-режим
            local_conn = sqlite3.connect(self.local_backup_path)
            try:
                local_conn.row_factory = sqlite3.Row
                local_cursor = local_conn.cursor()

                local_query = "SELECT * FROM packaging_log WHERE 1=1"
                local_params = []

                for l_key, l_value in filters.items():
                    if l_key == 'date':
                        local_query += " AND date = ?"
                        local_params.append(l_value)
                    elif l_key == 'id':
                        local_query += " AND id = ?"
                        local_params.append(l_value)
                    elif l_key in ['order_number', 'customer', 'product_name']:
                        local_query += f" AND {l_key} LIKE ?"
                        local_params.append(f'%{l_value}%')

                local_query += " ORDER BY id DESC"

                local_cursor.execute(local_query, local_params)
                local_rows = local_cursor.fetchall()
                return [dict(row) for row in local_rows]
            finally:
                local_conn.close()

    def update_entry(self, entry_id, field, value):
        """Обновление конкретной ячейки - с учётом офлайн-режима"""
        if self._is_network_available():
            def operation(conn):
                cur = conn.cursor()
                cur.execute(f"UPDATE packaging_log SET {field} = ? WHERE id = ?", (value, entry_id))
                conn.commit()
                return cur.rowcount > 0
            return self._execute_on_network(operation, with_backup=True)
        else:
            # Офлайн-режим: обновляем в локальной только если запись не синхронизирована
            local_conn = sqlite3.connect(self.local_backup_path)
            try:
                local_cursor = local_conn.cursor()

                # Проверяем, можно ли обновлять
                local_cursor.execute("SELECT synced FROM packaging_log WHERE id = ?", (entry_id,))
                row = local_cursor.fetchone()

                if not row:
                    return False

                if row[0] == 1:
                    return False

                local_cursor.execute(f"UPDATE packaging_log SET {field} = ? WHERE id = ?", (value, entry_id))
                local_conn.commit()
                return local_cursor.rowcount > 0
            finally:
                local_conn.close()

    def add_entry(self, data):
        """Добавление новой записи с учётом офлайн-режима"""
        if self._is_network_available():
            # Пишем в сетевую БД
            with self._write_lock, self._lock:
                def operation():
                    conn = sqlite3.connect(self.network_db_path)
                    try:
                        cursor = conn.cursor()

                        # Форматируем вес
                        weight = data.get('weight_kg')
                        if weight is not None and weight != '':
                            try:
                                weight = round(float(weight), 1)
                            except (ValueError, TypeError):
                                weight = None

                        cursor.execute("""
                            INSERT INTO packaging_log 
                            (date, order_number, customer, product_name, quantity_labels, 
                             packer_name, weight_kg, col_1, col_2, col_3, col_4, col_5, col_6, col_7, col_8, col_9, col_10, note, 
                             exported, source_type, source_file, source_sheet, source_row, 
                             sheet_index, row_color)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            data.get('date', ''),
                            data.get('order_number', ''),
                            data.get('customer', ''),
                            data.get('product_name', ''),
                            data.get('quantity_labels') if data.get('quantity_labels') not in (None, '') else None,
                            data.get('packer_name', ''),
                            weight,
                            data.get('col_1') if data.get('col_1') not in (None, '') else None,
                            data.get('col_2') if data.get('col_2') not in (None, '') else None,
                            data.get('col_3') if data.get('col_3') not in (None, '') else None,
                            data.get('col_4') if data.get('col_4') not in (None, '') else None,
                            data.get('col_5') if data.get('col_5') not in (None, '') else None,
                            data.get('col_6') if data.get('col_6') not in (None, '') else None,
                            data.get('col_7') if data.get('col_7') not in (None, '') else None,
                            data.get('col_8') if data.get('col_8') not in (None, '') else None,
                            data.get('col_9') if data.get('col_9') not in (None, '') else None,
                            data.get('col_10') if data.get('col_10') not in (None, '') else None,
                            data.get('note', ''),
                            0,  # exported
                            data.get('source_type', 'manual'),
                            data.get('source_file', ''),
                            data.get('source_sheet', ''),
                            data.get('source_row'),
                            data.get('sheet_index', 0),
                            data.get('row_color')
                        ))
                        conn.commit()
                        entry_id = cursor.lastrowid

                        # Делаем бэкап
                        self._backup_to_local()

                        return entry_id
                    finally:
                        conn.close()

                return self._execute_with_retry(operation)
        else:
            # Офлайн-режим: пишем в локальную БД
            return self._add_to_local_offline(data)

    def delete_entry(self, entry_id):
        """Удаление записи с учётом офлайн-режима"""
        if self._is_network_available():
            def operation(conn):
                cur = conn.cursor()
                cur.execute("DELETE FROM packaging_log WHERE id = ?", (entry_id,))
                conn.commit()
                return cur.rowcount > 0
            return self._execute_on_network(operation, with_backup=True)
        else:
            # Офлайн-режим: удаляем из локальной только если запись не синхронизирована
            local_conn = sqlite3.connect(self.local_backup_path)
            try:
                local_cursor = local_conn.cursor()

                # Проверяем, можно ли удалять
                local_cursor.execute("SELECT synced FROM packaging_log WHERE id = ?", (entry_id,))
                row = local_cursor.fetchone()

                if not row:
                    return False

                if row[0] == 1:
                    # Запись уже синхронизирована, в офлайне нельзя удалять
                    return False

                local_cursor.execute("DELETE FROM packaging_log WHERE id = ?", (entry_id,))
                local_conn.commit()
                return local_cursor.rowcount > 0
            finally:
                local_conn.close()

    def get_restorable_entries(self):
        """Возвращает записи для восстановления в Excel"""
        if self._is_network_available():
            def operation(conn):
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()

                # Получаем уникальные листы с их индексами
                cur.execute("""
                    SELECT DISTINCT source_sheet, sheet_index 
                    FROM packaging_log 
                    WHERE source_type = 'excel' OR (source_type = 'manual' AND exported = 1)
                    ORDER BY sheet_index ASC
                """)
                network_sheets = cur.fetchall()

                network_result = []

                for net_sheet in network_sheets:
                    net_sheet_name = net_sheet['source_sheet'].strip() or "Лист1"
                    net_sheet_index = net_sheet['sheet_index']

                    # Получаем записи для этого листа
                    cur.execute("""
                        SELECT * FROM packaging_log 
                        WHERE (source_type = 'excel' OR (source_type = 'manual' AND exported = 1))
                        AND source_sheet = ? AND sheet_index = ?
                        ORDER BY id ASC
                    """, (net_sheet_name, net_sheet_index))

                    net_rows = cur.fetchall()
                    if net_rows:
                        net_entries = [dict(row) for row in net_rows]
                        network_result.append((net_sheet_name, net_entries))

                return network_result
            result = self._execute_on_network(operation, with_backup=False)
            return result if result is not None else []
        else:
            # Офлайн-режим
            local_conn = sqlite3.connect(self.local_backup_path)
            try:
                local_conn.row_factory = sqlite3.Row
                local_cursor = local_conn.cursor()

                # Получаем уникальные листы с их индексами
                local_cursor.execute("""
                    SELECT DISTINCT source_sheet, sheet_index 
                    FROM packaging_log 
                    WHERE source_type = 'excel' OR (source_type = 'manual' AND exported = 1)
                    ORDER BY sheet_index ASC
                """)
                local_sheets = local_cursor.fetchall()

                local_result = []

                for local_sheet in local_sheets:
                    local_sheet_name = local_sheet['source_sheet'].strip() or "Лист1"
                    local_sheet_index = local_sheet['sheet_index']

                    # Получаем записи для этого листа
                    local_cursor.execute("""
                        SELECT * FROM packaging_log 
                        WHERE (source_type = 'excel' OR (source_type = 'manual' AND exported = 1))
                        AND source_sheet = ? AND sheet_index = ?
                        ORDER BY id ASC
                    """, (local_sheet_name, local_sheet_index))

                    local_rows = local_cursor.fetchall()
                    if local_rows:
                        local_entries = [dict(row) for row in local_rows]
                        local_result.append((local_sheet_name, local_entries))

                return local_result
            except Exception as e:
                print(f"Ошибка в get_restorable_entries: {e}")
                return []
            finally:
                local_conn.close()

    def mark_manual_as_restorable(self, entry_ids):
        """Помечает экспортированные ручные записи как восстанавливаемые"""
        if not entry_ids:
            return 0

        if isinstance(entry_ids, (int, str)):
            entry_ids = [entry_ids]

        if self._is_network_available():
            def operation(conn):
                cur = conn.cursor()
                placeholders = ','.join(['?'] * len(entry_ids))
                cur.execute(f"""
                    UPDATE packaging_log 
                    SET restore_flag = 1 
                    WHERE id IN ({placeholders}) AND source_type = 'manual'
                """, entry_ids)
                conn.commit()
                return cur.rowcount
            return self._execute_on_network(operation, with_backup=True)
        else:
            # Офлайн-режим: обновляем в локальной только если записи не синхронизированы
            local_conn = sqlite3.connect(self.local_backup_path)
            try:
                local_cursor = local_conn.cursor()
                local_placeholders = ','.join(['?'] * len(entry_ids))

                # Проверяем, все ли записи можно обновлять
                local_cursor.execute(f"SELECT id FROM packaging_log WHERE id IN ({local_placeholders}) AND synced = 1", entry_ids)
                synced_ids = [row[0] for row in local_cursor.fetchall()]

                if synced_ids:
                    return 0

                local_cursor.execute(f"""
                    UPDATE packaging_log 
                    SET restore_flag = 1 
                    WHERE id IN ({local_placeholders}) AND source_type = 'manual'
                """, entry_ids)
                local_conn.commit()
                return local_cursor.rowcount
            except Exception as e:
                print(f"Ошибка в mark_manual_as_restorable (офлайн): {e}")
                return 0
            finally:
                local_conn.close()
