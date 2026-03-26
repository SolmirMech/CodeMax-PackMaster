# core/packaging/packaging_data_manager.py
import sqlite3
import threading
import os


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
            cursor_local = conn_local.cursor()
            cursor_local.execute("SELECT * FROM packaging_log WHERE synced = 0 ORDER BY id ASC")
            rows = cursor_local.fetchall()

            if not rows:
                return 0

            # Получаем названия колонок (без id)
            cursor_local.execute("PRAGMA table_info(packaging_log)")
            columns = [col[1] for col in cursor_local.fetchall() if col[1] != 'id']

            cursor_network = conn_network.cursor()

            for row in rows:
                row_dict = {col: row[columns.index(col)] for col in columns}
                placeholders = ','.join(['?'] * len(row_dict))
                columns_str = ','.join(row_dict.keys())
                cursor_network.execute(
                    f"INSERT INTO packaging_log ({columns_str}) VALUES ({placeholders})",
                    list(row_dict.values())
                )

            conn_network.commit()
            synced_count = len(rows)

            # Удаляем синхронизированные из локальной
            cursor_local.execute("DELETE FROM packaging_log WHERE synced = 0")
            conn_local.commit()

            return synced_count  # ← добавляем return

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

    def _init_local_backup(self):
        """Инициализирует локальную БД-бэкап"""
        conn = sqlite3.connect(self.local_backup_path)
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS packaging_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT, order_number TEXT, customer TEXT, product_name TEXT,
                    quantity_labels INTEGER DEFAULT 0, packer_name TEXT, weight_kg REAL DEFAULT 0,
                    col_1 INTEGER DEFAULT 0, col_2 INTEGER DEFAULT 0, col_3 INTEGER DEFAULT 0,
                    col_4 INTEGER DEFAULT 0, col_5 INTEGER DEFAULT 0, col_6 INTEGER DEFAULT 0,
                    col_7 INTEGER DEFAULT 0, col_8 INTEGER DEFAULT 0, col_9 INTEGER DEFAULT 0,
                    col_10 INTEGER DEFAULT 0, note TEXT, exported INTEGER DEFAULT 0,
                    source_type TEXT DEFAULT 'manual', source_file TEXT, source_sheet TEXT,
                    source_row INTEGER, sheet_index INTEGER DEFAULT 0, restore_flag INTEGER DEFAULT 0,
                    row_color TEXT, synced INTEGER DEFAULT 1
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
            # Обновляем в сетевой БД
            with self._write_lock:
                try:
                    with self._lock:
                        conn = sqlite3.connect(self.network_db_path)
                        cursor = conn.cursor()

                        cursor.execute(f"""
                            UPDATE packaging_log 
                            SET {field} = ?, exported = 0 
                            WHERE id = ?
                        """, (value, entry_id))

                        conn.commit()
                        result = cursor.rowcount > 0

                        # Делаем бэкап
                        if result:
                            self._backup_to_local()

                        return result
                finally:
                    conn.close()
        else:
            # Офлайн-режим: обновляем в локальной БД только если запись не синхронизирована
            conn = sqlite3.connect(self.local_backup_path)
            try:
                cursor = conn.cursor()

                # Проверяем, можно ли обновлять
                cursor.execute("SELECT synced FROM packaging_log WHERE id = ?", (entry_id,))
                row = cursor.fetchone()

                if not row:
                    return False

                if row[0] == 1:
                    # Запись уже синхронизирована, в офлайне нельзя изменять
                    return False

                cursor.execute(f"""
                    UPDATE packaging_log 
                    SET {field} = ?, exported = 0 
                    WHERE id = ?
                """, (value, entry_id))

                conn.commit()
                return cursor.rowcount > 0
            finally:
                conn.close()

    def clear_database(self):
        """Полностью очищает БД и пересоздаёт таблицу с новой структурой"""
        if not self._is_network_available():
            # В офлайне нельзя очистить БД, т.к. данные могут быть не синхронизированы
            if self.status_callback:
                self.status_callback("Очистка БД недоступна в офлайн-режиме")
            return False

        with self._write_lock:
            try:
                with self._lock:
                    conn = sqlite3.connect(self.network_db_path)
                    cursor = conn.cursor()

                    # Удаляем старую таблицу
                    cursor.execute("DROP TABLE IF EXISTS packaging_log")

                    # Создаём заново с новой структурой
                    cursor.execute("""
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
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pack_date ON packaging_log(date)")
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pack_order ON packaging_log(order_number)")
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pack_customer ON packaging_log(customer)")
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pack_product ON packaging_log(product_name)")
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pack_exported ON packaging_log(exported)")
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pack_source ON packaging_log(source_type)")
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pack_sheet_index ON packaging_log(sheet_index)")

                    conn.commit()

                    # Делаем бэкап очищенной БД
                    self._backup_to_local()

                    return True

            except Exception as e:
                print(f"Ошибка очистки БД: {e}")
                return False
            finally:
                conn.close()

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
        """Инициализация БД для журнала упаковки"""
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
            # Обновляем в сетевой БД
            with self._write_lock:
                try:
                    with self._lock:
                        conn = sqlite3.connect(self.network_db_path)
                        cursor = conn.cursor()
                        cursor.execute(
                            "UPDATE packaging_log SET row_color = ?, exported = 0 WHERE id = ?",
                            (hex_color, entry_id)
                        )
                        conn.commit()
                        result = cursor.rowcount > 0

                        # Делаем бэкап
                        if result:
                            self._backup_to_local()

                        return result
                finally:
                    conn.close()
        else:
            # Офлайн-режим: обновляем в локальной только если запись не синхронизирована
            conn = sqlite3.connect(self.local_backup_path)
            try:
                cursor = conn.cursor()

                # Проверяем, можно ли обновлять
                cursor.execute("SELECT synced FROM packaging_log WHERE id = ?", (entry_id,))
                row = cursor.fetchone()

                if not row:
                    return False

                if row[0] == 1:
                    return False

                cursor.execute(
                    "UPDATE packaging_log SET row_color = ?, exported = 0 WHERE id = ?",
                    (hex_color, entry_id)
                )
                conn.commit()
                return cursor.rowcount > 0
            finally:
                conn.close()

    def get_row_color(self, entry_id):
        """Возвращает цвет строки"""
        conn = None
        try:
            if self._is_network_available():
                conn = sqlite3.connect(self.network_db_path)
            else:
                conn = sqlite3.connect(self.local_backup_path)

            cursor = conn.cursor()
            cursor.execute(
                "SELECT row_color FROM packaging_log WHERE id = ?",
                (entry_id,)
            )
            row = cursor.fetchone()
            return row[0] if row else None
        finally:
            if conn:
                conn.close()

    def get_unexported_entries(self):
        """Возвращает все неэкспортированные записи"""
        conn = None
        try:
            if self._is_network_available():
                conn = sqlite3.connect(self.network_db_path)
            else:
                conn = sqlite3.connect(self.local_backup_path)

            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM packaging_log 
                WHERE exported = 0 
                ORDER BY id ASC
            """)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Ошибка в get_unexported_entries: {e}")
            return []
        finally:
            if conn:
                conn.close()

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
            # Обновляем в сетевой БД
            with self._write_lock:
                try:
                    with self._lock:
                        conn = sqlite3.connect(self.network_db_path)
                        cursor = conn.cursor()
                        placeholders = ','.join(['?'] * len(entry_ids))

                        if sheet_name:
                            cursor.execute(f"""
                                UPDATE packaging_log 
                                SET exported = 1, source_sheet = ?, sheet_index = 0
                                WHERE id IN ({placeholders})
                            """, [sheet_name] + entry_ids)
                        else:
                            cursor.execute(f"""
                                UPDATE packaging_log 
                                SET exported = 1
                                WHERE id IN ({placeholders})
                            """, entry_ids)

                        conn.commit()
                        result = cursor.rowcount

                        # Делаем бэкап
                        if result > 0:
                            self._backup_to_local()

                        return result
                except Exception as e:
                    print(f"Ошибка в mark_as_exported: {e}")
                    return 0
                finally:
                    conn.close()
        else:
            # Офлайн-режим: обновляем в локальной только если записи не синхронизированы
            conn = sqlite3.connect(self.local_backup_path)
            try:
                cursor = conn.cursor()
                placeholders = ','.join(['?'] * len(entry_ids))

                # Проверяем, все ли записи можно обновлять
                cursor.execute(f"SELECT id FROM packaging_log WHERE id IN ({placeholders}) AND synced = 1", entry_ids)
                synced_ids = [row[0] for row in cursor.fetchall()]

                if synced_ids:
                    # Есть синхронизированные записи, их нельзя менять в офлайне
                    return 0

                if sheet_name:
                    cursor.execute(f"""
                        UPDATE packaging_log 
                        SET exported = 1, source_sheet = ?, sheet_index = 0
                        WHERE id IN ({placeholders})
                    """, [sheet_name] + entry_ids)
                else:
                    cursor.execute(f"""
                        UPDATE packaging_log 
                        SET exported = 1
                        WHERE id IN ({placeholders})
                    """, entry_ids)

                conn.commit()
                return cursor.rowcount
            except Exception as e:
                print(f"Ошибка в mark_as_exported (офлайн): {e}")
                return 0
            finally:
                conn.close()

    def get_recent(self, limit=20):
        """Последние записи - с fallback на локальную БД"""
        conn = None
        try:
            if self._is_network_available():
                conn = sqlite3.connect(self.network_db_path)
            else:
                conn = sqlite3.connect(self.local_backup_path)

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
            if conn:
                conn.close()

    def search(self, filters):
        conn = None
        try:
            if self._is_network_available():
                conn = sqlite3.connect(self.network_db_path)
            else:
                conn = sqlite3.connect(self.local_backup_path)

            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = "SELECT * FROM packaging_log WHERE 1=1"
            params = []

            for key, value in filters.items():
                if key == 'date':
                    query += " AND date = ?"
                    params.append(value)
                elif key == 'id':
                    query += " AND id = ?"
                    params.append(value)
                elif key in ['order_number', 'customer', 'product_name']:
                    query += f" AND {key} LIKE ?"
                    params.append(f'%{value}%')

            query += " ORDER BY id DESC"

            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            if conn:
                conn.close()

    def update_entry(self, entry_id, field, value):
        """Обновление конкретной ячейки - с учётом офлайн-режима"""
        if self._is_network_available():
            # Обновляем в сетевой БД
            with self._write_lock:
                try:
                    with self._lock:
                        conn = sqlite3.connect(self.network_db_path)
                        cursor = conn.cursor()
                        cursor.execute(f"UPDATE packaging_log SET {field} = ? WHERE id = ?", (value, entry_id))
                        conn.commit()
                        result = cursor.rowcount > 0

                        # Делаем бэкап
                        if result:
                            self._backup_to_local()

                        return result
                finally:
                    conn.close()
        else:
            # Офлайн-режим: обновляем в локальной только если запись не синхронизирована
            conn = sqlite3.connect(self.local_backup_path)
            try:
                cursor = conn.cursor()

                # Проверяем, можно ли обновлять
                cursor.execute("SELECT synced FROM packaging_log WHERE id = ?", (entry_id,))
                row = cursor.fetchone()

                if not row:
                    return False

                if row[0] == 1:
                    return False

                cursor.execute(f"UPDATE packaging_log SET {field} = ? WHERE id = ?", (value, entry_id))
                conn.commit()
                return cursor.rowcount > 0
            finally:
                conn.close()

    def add_entry(self, data):
        """Добавление новой записи с учётом офлайн-режима"""
        if self._is_network_available():
            # Пишем в сетевую БД
            with self._write_lock:
                try:
                    with self._lock:
                        conn = sqlite3.connect(self.network_db_path)
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
        else:
            # Офлайн-режим: пишем в локальную БД
            return self._add_to_local_offline(data)

    def delete_entry(self, entry_id):
        """Удаление записи с учётом офлайн-режима"""
        if self._is_network_available():
            # Удаляем из сетевой БД
            with self._write_lock:
                try:
                    with self._lock:
                        conn = sqlite3.connect(self.network_db_path)
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM packaging_log WHERE id = ?", (entry_id,))
                        conn.commit()
                        result = cursor.rowcount > 0

                        # Делаем бэкап
                        if result:
                            self._backup_to_local()

                        return result
                finally:
                    conn.close()
        else:
            # Офлайн-режим: удаляем из локальной только если запись не синхронизирована
            conn = sqlite3.connect(self.local_backup_path)
            try:
                cursor = conn.cursor()

                # Проверяем, можно ли удалять
                cursor.execute("SELECT synced FROM packaging_log WHERE id = ?", (entry_id,))
                row = cursor.fetchone()

                if not row:
                    return False

                if row[0] == 1:
                    # Запись уже синхронизирована, в офлайне нельзя удалять
                    return False

                cursor.execute("DELETE FROM packaging_log WHERE id = ?", (entry_id,))
                conn.commit()
                return cursor.rowcount > 0
            finally:
                conn.close()

    def get_restorable_entries(self):
        """Возвращает записи для восстановления в Excel"""
        conn = None
        try:
            if self._is_network_available():
                conn = sqlite3.connect(self.network_db_path)
            else:
                conn = sqlite3.connect(self.local_backup_path)

            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Получаем уникальные листы с их индексами
            cursor.execute("""
                SELECT DISTINCT source_sheet, sheet_index 
                FROM packaging_log 
                WHERE source_type = 'excel' OR (source_type = 'manual' AND exported = 1)
                ORDER BY sheet_index ASC
            """)
            sheets = cursor.fetchall()

            result = []

            for sheet in sheets:
                sheet_name = sheet['source_sheet'].strip() or "Лист1"
                sheet_index = sheet['sheet_index']

                # Получаем записи для этого листа
                cursor.execute("""
                    SELECT * FROM packaging_log 
                    WHERE (source_type = 'excel' OR (source_type = 'manual' AND exported = 1))
                    AND source_sheet = ? AND sheet_index = ?
                    ORDER BY id ASC
                """, (sheet_name, sheet_index))

                rows = cursor.fetchall()
                if rows:
                    entries = [dict(row) for row in rows]
                    result.append((sheet_name, entries))

            return result
        except Exception as e:
            print(f"Ошибка в get_restorable_entries: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def mark_manual_as_restorable(self, entry_ids):
        """Помечает экспортированные ручные записи как восстанавливаемые"""
        if not entry_ids:
            return 0

        if isinstance(entry_ids, (int, str)):
            entry_ids = [entry_ids]

        if self._is_network_available():
            # Обновляем в сетевой БД
            with self._write_lock:
                try:
                    with self._lock:
                        conn = sqlite3.connect(self.network_db_path)
                        cursor = conn.cursor()
                        placeholders = ','.join(['?'] * len(entry_ids))
                        cursor.execute(f"""
                            UPDATE packaging_log 
                            SET restore_flag = 1 
                            WHERE id IN ({placeholders}) AND source_type = 'manual'
                        """, entry_ids)
                        conn.commit()
                        result = cursor.rowcount

                        # Делаем бэкап
                        if result > 0:
                            self._backup_to_local()

                        return result
                except Exception as e:
                    print(f"Ошибка в mark_manual_as_restorable: {e}")
                    return 0
                finally:
                    conn.close()
        else:
            # Офлайн-режим: обновляем в локальной только если записи не синхронизированы
            conn = sqlite3.connect(self.local_backup_path)
            try:
                cursor = conn.cursor()
                placeholders = ','.join(['?'] * len(entry_ids))

                # Проверяем, все ли записи можно обновлять
                cursor.execute(f"SELECT id FROM packaging_log WHERE id IN ({placeholders}) AND synced = 1", entry_ids)
                synced_ids = [row[0] for row in cursor.fetchall()]

                if synced_ids:
                    return 0

                cursor.execute(f"""
                    UPDATE packaging_log 
                    SET restore_flag = 1 
                    WHERE id IN ({placeholders}) AND source_type = 'manual'
                """, entry_ids)
                conn.commit()
                return cursor.rowcount
            except Exception as e:
                print(f"Ошибка в mark_manual_as_restorable (офлайн): {e}")
                return 0
            finally:
                conn.close()
