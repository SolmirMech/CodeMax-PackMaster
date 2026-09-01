"""
Модуль data_manager.py - кэширующий слой для работы с XML-файлами заказов.
Ускоряет поиск за счет использования SQLite базы данных.
"""

import hashlib
import logging
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

import chardet

from core.bd_parts.database import OrderRepository
from core.bd_parts.statistics import OrderStatistics, StatisticsLogger
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
        
        self._stats = OrderStatistics()
        self._stats_logger = StatisticsLogger()
        
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
        
        # Создаем репозиторий
        db_path = config_manager.data_dir / "orders_cache.db"
        self.repository = OrderRepository(db_path)

        # Инициализация БД через репозиторий
        self.repository.init_database()

        # Подписываемся на уведомления координатора
        if self.coordinator and hasattr(self.coordinator, 'subscribe'):
            self.coordinator.subscribe(self.on_settings_changed)

        logging.debug(f"DataManager инициализирован. XML папка: {self.xml_folder}")
        logging.debug(f"БД: {db_path}")
        
        self._pending_status = None  # ID отложенного сообщения
        self._last_message = ""      # Для дублей
        # Флаг для периодической проверки
        self._periodic_check_running = False
        self._start_periodic_check()

    def _setup_logging(self):
        """Настройка логгирования."""
        logging.basicConfig(
            filename=self.log_file,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            encoding='utf-8'
        )

    def on_settings_changed(self, context=None):
        """Обработчик уведомлений от координатора"""
        if context and isinstance(context, dict):
            # Существующая логика для обновления даты
            if context.get("type") == "list_changed" and context.get("list_name") == "update_date_request":
                self.start_fast_check(silent=False)

            # Новая логика для обновления БД с различными периодами
            if context.get("type") == "list_changed" and context.get("list_name") == "db_update":
                update_type = context.get("update_type")

                if update_type == "update_full":
                    self.start_background_check(silent=False)
                elif update_type == "update_3days":
                    self.start_check_with_days(3, silent=False)
                elif update_type == "update_week":
                    self.start_check_with_days(7, silent=False)
                elif update_type == "update_2weeks":
                    self.start_check_with_days(14, silent=False)
                elif update_type == "update_month":
                    self.start_check_with_days(30, silent=False)

            # Существующая логика для смены папки
            if context.get("type") == "xml_folder_changed":
                new_path = self.config.get_weight_data_base_path()
                new_path = Path(new_path)

                if new_path != self.xml_folder:
                    self.xml_folder = new_path
                    self.start_background_check(silent=False)
                else:
                    logging.debug("Папка не изменилась, пропускаем")

    def _start_periodic_check(self):
        """Запускает периодическую проверку каждые 15 минут"""
        if self._periodic_check_running:
            return
        
        self._periodic_check_running = True
        
        def periodic_check():
            while self._periodic_check_running:
                time.sleep(900)  # 15 минут
                if self._periodic_check_running:  # Проверяем ещё раз после сна
                    self.start_fast_check(silent=True)
        
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
            self._stats.add_order(parsed_data)
            
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

    def _log_collected_statistics(self, context: str = "сканирование") -> None:
        """
        Логирует собранную статистику с заказчиками.

        Args:
            context: Контекст операции ("сканирование", "обновление", "проверка")
        """
        # Собираем все номера заказов из статистики
        all_order_numbers = set()
        all_order_numbers.update(self._stats.emission_orders)
        all_order_numbers.update(self._stats.solmark_orders)
        all_order_numbers.update(self._stats.diameter_orders)
        all_order_numbers.update(self._stats.labels_per_roll_orders)
        all_order_numbers.update(self._stats.aggregation_orders)

        # Получаем заказчиков из БД
        customer_map = self.repository.get_orders_with_customers(all_order_numbers)

        # Логируем с заказчиками
        self._stats_logger.log(self._stats, context, customer_map)

    @staticmethod
    def _calculate_file_hash(file_path: Path) -> str:
        """Вычисляет MD5 хэш файла для отслеживания изменений."""
        try:
            file_content = file_path.read_bytes()
            return hashlib.md5(file_content).hexdigest()
        except Exception as e:
            logging.error(f"Ошибка вычисления хэша для {file_path}: {e}")
            return ""

    def initial_scan(self) -> None:
        """
        ПЕРВИЧНОЕ СКАНИРОВАНИЕ.
        Заполняет БД при первом запуске
        """
        def scan_in_background():
            try:
                # проверяем есть ли данные в бд
                stats = self.repository.get_stats()
                count = stats.get('total_orders', 0)

                if count > 0:
                    self._notify_status(f"База загружена ({count} записей)")
                    return

                self._notify_status("Проверка доступности источника XML...")

                if not self._check_xml_source_available():
                    self._notify_status("⚠️ Источник XML недоступен")
                    logging.error(f"Папка XML недоступна: {self.xml_folder}")
                    return

                xml_files = list(self.xml_folder.glob("*.xml"))
                total_files = len(xml_files)
                logging.info(f"Найдено XML файлов: {total_files}")

                if total_files == 0:
                    logging.warning("В папке XML не найдено файлов")
                    self._notify_status("⚠️ В источнике нет XML файлов")
                    return

                self._notify_status(f"🔄 Ожидайте, идёт обновление базы ({total_files} файлов)...")

                # ← ИСПОЛЬЗУЕМ РЕПОЗИТОРИЙ
                self.repository.clear_cache()

                self._stats.clear()

                processed = 0
                errors = 0

                for file_path in xml_files:
                    try:
                        parsed_data = self._parse_xml_file(file_path)
                        if not parsed_data:
                            errors += 1
                            continue

                        file_hash = self._calculate_file_hash(file_path)

                        # ← ИСПОЛЬЗУЕМ РЕПОЗИТОРИЙ
                        if self.repository.save_order(file_path, parsed_data, file_hash):
                            processed += 1
                        else:
                            errors += 1

                    except Exception as e:
                        errors += 1
                        logging.error(f"Ошибка обработки {file_path.name}: {e}")

                self._log_collected_statistics("первичное сканирование")

                if errors > 0:
                    self._notify_status(f"✅ База создана ({processed} заказов, {errors} ошибок)")
                else:
                    self._notify_status(f"✅ База создана ({processed} заказов)")

                logging.info(f"Первичное сканирование завершено. Успешно: {processed}, Ошибок: {errors}")

            except Exception as e:
                logging.error(f"Ошибка при первичном сканировании: {e}")
                self._notify_status(f"❌ Ошибка сканирования: {e}")

        thread = threading.Thread(target=scan_in_background, daemon=True)
        thread.start()

    def _check_xml_source_available(self) -> bool:
        """
        Проверяет доступность источника XML.
        ВЫЗЫВАТЬ ТОЛЬКО ИЗ ФОНОВОГО ПОТОКА!

        Returns:
            True если источник доступен, False если недоступен
        """
        try:
            # Простая проверка существования папки
            # Теперь вызывается только из фоновых потоков, поэтому безопасно
            return self.xml_folder.exists()
        except Exception as e:
            logging.warning(f"Ошибка проверки источника XML: {e}")
            return False

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

        # Проверка на пустой запрос
        if not order_query or not ''.join(filter(str.isdigit, order_query)):
            return []

        # Увеличиваем счётчик читателей
        with self._readers_lock:
            self._readers_count += 1

        try:
            # Поиск через репозиторий
            results = self.repository.search_orders(order_query, sheet_query)

            elapsed = (time.time() - start_time) * 1000
            logging.debug(f"Поиск выполнен за {elapsed:.2f}мс, найдено {len(results)} записей")

            return results

        except sqlite3.OperationalError as e:
            if "database is locked" in str(e):
                logging.warning("БД заблокирована, повтор через 100мс")
                time.sleep(0.1)
                # Повторяем попытку
                return self.repository.search_orders(order_query, sheet_query)

            logging.error(f"Ошибка поиска в БД: {e}")
            # Пробуем восстановить БД
            self.repository.recreate_database()
            return []

        except Exception as e:
            logging.error(f"Непредвиденная ошибка при поиске: {e}")
            return []

        finally:
            # Уменьшаем счётчик читателей и проверяем отложенное обновление
            with self._readers_lock:
                self._readers_count -= 1
                if self._update_scheduled and self._readers_count == 0:
                    thread = threading.Thread(target=self._try_scheduled_update, daemon=True)
                    thread.start()

    def _try_scheduled_update(self):
        """Пытается выполнить отложенное обновление"""
        with self._readers_lock:
            if not self._update_scheduled:
                return
            if self._readers_count > 0:
                return

        self._update_scheduled = False
        self._start_background_check(silent=True)

    def _start_background_check(self, silent=False):
        """Запускает фоновую проверку, если она не выполняется."""
        if self._background_running is None:
            self._background_running = False

        if not self._background_running and self._background_lock.acquire(blocking=False):
            try:
                self._background_running = True
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
        """
        with self._readers_lock:
            if self._readers_count > 0:
                self._update_scheduled = True
                logging.info(f"Обновление отложено: {self._readers_count} активных чтений")
                if not silent:
                    self._notify_status("⏳ Обновление отложено: база используется")
                return
            self._update_scheduled = False

        with self._write_lock:
            try:
                if not self._check_xml_source_available():
                    self._notify_status("⚠️ Источник XML недоступен")
                    return

                # ← ИСПОЛЬЗУЕМ РЕПОЗИТОРИЙ
                db_files = self.repository.get_all_files_metadata()

                new_stats = OrderStatistics()
                processed_files = 0

                xml_files = list(self.xml_folder.glob("*.xml"))

                for file_path in xml_files:
                    file_name = file_path.name

                    try:
                        if not file_path.exists():
                            continue

                        file_hash = self._calculate_file_hash(file_path)
                        last_modified = file_path.stat().st_mtime

                        needs_processing = False

                        if file_name not in db_files:
                            needs_processing = True
                        else:
                            db_hash, db_mtime = db_files[file_name]
                            if file_hash != db_hash or abs(last_modified - db_mtime) > 1:
                                needs_processing = True

                        if needs_processing:
                            parsed_data = self._parse_xml_file(file_path)
                            if not parsed_data:
                                continue

                            # ← ИСПОЛЬЗУЕМ РЕПОЗИТОРИЙ
                            if self.repository.save_order(file_path, parsed_data, file_hash):
                                logging.info(f"Добавлен новый заказ: {file_name}")
                                processed_files += 1
                                new_stats.add_order(parsed_data)

                    except (PermissionError, FileNotFoundError):
                        continue
                    except Exception as e:
                        logging.error(f"Ошибка обработки {file_name}: {e}")
                        continue

                if processed_files > 0:
                    self._stats.merge(new_stats)
                    self._log_collected_statistics("обновление")

                    if not silent:
                        status_parts = []
                        if new_stats.emission_orders:
                            status_parts.append(f"📅 {len(new_stats.emission_orders)} с датой эмиссии")
                        if new_stats.solmark_orders:
                            status_parts.append(f"🖨 {len(new_stats.solmark_orders)} Solmark")
                        if new_stats.multi_customer_orders:
                            status_parts.append(f"👥 {len(new_stats.multi_customer_orders)} с многими заказчиками")
                        if new_stats.diameter_orders:
                            status_parts.append(f"📏 {len(new_stats.diameter_orders)} с diameter_mm")
                        if new_stats.labels_per_roll_orders:
                            status_parts.append(f"🏷 {len(new_stats.labels_per_roll_orders)} с labels_per_roll")
                        if new_stats.aggregation_orders:
                            status_parts.append(f"📦 {len(new_stats.aggregation_orders)} с агрегацией")

                        if status_parts:
                            status_msg = f"Обновлено {processed_files} файлов ({', '.join(status_parts)})"
                        else:
                            status_msg = f"Обновлено {processed_files} файлов"

                        self._notify_status(status_msg)

            except sqlite3.Error as e:
                logging.error(f"SQLite ошибка в background_check: {e}")
                self._notify_status("⚠️ Ошибка обновления базы данных")
            except Exception as e:
                logging.error(f"Непредвиденная ошибка в background_check: {e}")
                self._notify_status("⚠️ Ошибка при проверке файлов")
            finally:
                if not silent and self.status_callback:
                    self._notify_status("✅ Проверка обновлений завершена")

                self._background_running = False
                if hasattr(self, '_background_lock'):
                    try:
                        self._background_lock.release()
                    except:
                        pass

    def fast_check_today(self, silent=False):
        """
        БЫСТРАЯ ПРОВЕРКА: сканирует только файлы, измененные сегодня.
        Используется при нажатии кнопки обновления даты.

        Args:
            silent: Если True - не показывать уведомления в UI

        Returns:
            int: Количество обработанных файлов
        """
        with self._readers_lock:
            if self._readers_count > 0:
                self._update_scheduled = True
                if not silent:
                    self._notify_status("⏳ Обновление отложено: база используется")
                return 0
            self._update_scheduled = False

        with self._write_lock:
            try:
                if not self._check_xml_source_available():
                    self._notify_status("⚠️ Источник XML недоступен")
                    return 0

                    # Проверяем за последние 2 дня (на случай задержки)
                today = datetime.now().date()
                date_from = today - timedelta(days=2)  # ← используем timedelta

                changed_files = []
                for file_path in self.xml_folder.glob("*.xml"):
                    try:
                        mtime = file_path.stat().st_mtime
                        file_date = datetime.fromtimestamp(mtime).date()

                        # Если файл изменен в период от date_from до today
                        if date_from <= file_date <= today:
                            changed_files.append(file_path)

                    except Exception as e:
                        logging.error(f"Ошибка проверки файла {file_path.name}: {e}")
                        continue

                if not changed_files:
                    if not silent:
                        self._notify_status("📭 Сегодня измененных файлов нет")
                    return 0

                # Получаем метаданные из БД для сравнения
                db_files = self.repository.get_all_files_metadata()

                # Обрабатываем только изменившиеся файлы
                new_stats = OrderStatistics()
                processed_files = 0
                unchanged_files = 0

                for file_path in changed_files:
                    file_name = file_path.name

                    try:
                        file_hash = self._calculate_file_hash(file_path)
                        last_modified = file_path.stat().st_mtime

                        needs_processing = False

                        if file_name not in db_files:
                            # Новый файл
                            needs_processing = True
                        else:
                            db_hash, db_mtime = db_files[file_name]
                            # Сравниваем хэш или дату изменения
                            if file_hash != db_hash or abs(last_modified - db_mtime) > 1:
                                needs_processing = True
                            else:
                                unchanged_files += 1

                        if needs_processing:
                            parsed_data = self._parse_xml_file(file_path)
                            if parsed_data:
                                if self.repository.save_order(file_path, parsed_data, file_hash):
                                    processed_files += 1
                                    new_stats.add_order(parsed_data)
                                    logging.info(f"Быстрое обновление: {file_name}")

                    except Exception as e:
                        logging.error(f"Ошибка быстрой обработки {file_name}: {e}")
                        continue

                # Обновляем статистику
                if processed_files > 0:
                    self._stats.merge(new_stats)
                    self._log_collected_statistics("быстрое обновление")

                    if not silent:
                        status_parts = []
                        if new_stats.emission_orders:
                            status_parts.append(f"📅 {len(new_stats.emission_orders)} с датой эмиссии")
                        if new_stats.solmark_orders:
                            status_parts.append(f"🖨 {len(new_stats.solmark_orders)} Solmark")
                        if new_stats.multi_customer_orders:
                            status_parts.append(f"👥 {len(new_stats.multi_customer_orders)} с многими заказчиками")
                        if new_stats.diameter_orders:
                            status_parts.append(f"📏 {len(new_stats.diameter_orders)} с diameter_mm")
                        if new_stats.labels_per_roll_orders:
                            status_parts.append(f"🏷 {len(new_stats.labels_per_roll_orders)} с labels_per_roll")
                        if new_stats.aggregation_orders:
                            status_parts.append(f"📦 {len(new_stats.aggregation_orders)} с агрегацией")

                        if status_parts:
                            status_msg = f"✅ Обновлено {processed_files} файлов ({', '.join(status_parts)})"
                        else:
                            status_msg = f"✅ Обновлено {processed_files} файлов"

                        if unchanged_files > 0:
                            status_msg += f" (еще {unchanged_files} без изменений)"

                        self._notify_status(status_msg)
                else:
                    if not silent:
                        if unchanged_files > 0:
                            self._notify_status(f"📭 Все {unchanged_files} файлов за сегодня уже актуальны")
                        else:
                            self._notify_status("📭 Новых изменений в файлах за сегодня нет")

                return processed_files

            except Exception as e:
                logging.error(f"Ошибка быстрой проверки: {e}")
                self._notify_status(f"❌ Ошибка быстрой проверки: {e}")
                return 0
            finally:
                self._background_running = False
                if hasattr(self, '_background_lock'):
                    try:
                        self._background_lock.release()
                    except:
                        pass

    def start_fast_check(self, silent=False):
        """
        Публичный метод для запуска быстрой проверки извне.
        Запускается в фоновом потоке, чтобы не блокировать UI.
        """
        # Проверяем, не запущена ли уже проверка
        with self._background_lock:
            if self._background_running:
                if not silent:
                    self._notify_status("⏳ Проверка уже выполняется...")
                return

            self._background_running = True

        if not silent and self.status_callback:
            self._notify_status("🔍 Быстрая проверка новых файлов...")

        # Запускаем в фоновом потоке
        thread = threading.Thread(
            target=self._fast_check_async,
            args=(silent,),
            daemon=True
        )
        thread.start()

    def _fast_check_async(self, silent=False):
        """
        Асинхронная обёртка для fast_check_today.
        Выполняется в фоновом потоке.
        """
        try:
            self.fast_check_today(silent=silent)
        except Exception as e:
            logging.error(f"Ошибка в фоновой проверке: {e}")
            if not silent:
                self._notify_status(f"❌ Ошибка проверки: {e}")
        finally:
            # Освобождаем блокировку
            with self._background_lock:
                self._background_running = False

    def start_check(self, silent=False):
        """
        Умный запуск проверки:
        - если БД пуста - полная проверка (initial_scan)
        - если БД не пуста - быстрая проверка (fast_check)

        ВСЕГДА в фоновом потоке.

        Args:
            silent: Если True - не показывать уведомления в UI
        """
        stats = self.repository.get_stats()
        total_orders = stats.get('total_orders', 0)

        if total_orders == 0:
            # База пуста - полная проверка
            if not silent:
                self._notify_status("🔄 Первичное создание базы данных...")
            # initial_scan уже работает в фоновом потоке
            self.initial_scan()
        else:
            # База не пуста - быстрая проверка
            self.start_fast_check(silent=silent)

    def start_check_with_days(self, days: int = None, silent: bool = False):
        """
        Универсальный метод проверки обновлений базы данных.

        Args:
            days: Количество дней для проверки.
                  None или 0 - полная проверка (все файлы)
                  2 - быстрая проверка (файлы за 2 дня)
                  другое число - проверка за указанное количество дней
            silent: Если True - не показывать уведомления в UI

        Returns:
            int: Количество обработанных файлов (0 если полная проверка)
        """
        if days is None or days == 0:
            if not silent:
                self._notify_status("🔄 Полная проверка всех файлов...")
            self.start_background_check(silent=silent)
            return 0
        elif days == 2:
            return self.start_fast_check(silent=silent)
        else:
            return self._check_files_by_days(days, silent)

    def _check_files_by_days(self, days: int, silent=False):
        """
        Проверка обновлений за указанное количество дней.

        Args:
            days: Количество дней для проверки
            silent: Если True - не показывать уведомления в UI
        """
        if not silent:
            self._notify_status(f"🔍 Проверка файлов за {days} дней...")

        with self._readers_lock:
            if self._readers_count > 0:
                self._update_scheduled = True
                if not silent:
                    self._notify_status("⏳ Обновление отложено: база используется")
                return 0

        with self._write_lock:
            try:
                if not self._check_xml_source_available():
                    self._notify_status("⚠️ Источник XML недоступен")
                    return 0

                # Вычисляем дату начала проверки
                date_from = datetime.now().date() - timedelta(days=days)

                changed_files = []
                for file_path in self.xml_folder.glob("*.xml"):
                    try:
                        mtime = file_path.stat().st_mtime
                        file_date = datetime.fromtimestamp(mtime).date()

                        if file_date >= date_from:
                            changed_files.append(file_path)
                    except Exception as e:
                        logging.error(f"Ошибка проверки файла {file_path.name}: {e}")
                        continue

                if not changed_files:
                    if not silent:
                        self._notify_status(f"📭 Файлов, измененных за последние {days} дней, нет")
                    return 0

                # Получаем метаданные из БД для сравнения
                db_files = self.repository.get_all_files_metadata()

                new_stats = OrderStatistics()
                processed_files = 0
                unchanged_files = 0

                for file_path in changed_files:
                    file_name = file_path.name

                    try:
                        file_hash = self._calculate_file_hash(file_path)
                        last_modified = file_path.stat().st_mtime

                        needs_processing = False

                        if file_name not in db_files:
                            needs_processing = True
                        else:
                            db_hash, db_mtime = db_files[file_name]
                            if file_hash != db_hash or abs(last_modified - db_mtime) > 1:
                                needs_processing = True
                            else:
                                unchanged_files += 1

                        if needs_processing:
                            parsed_data = self._parse_xml_file(file_path)
                            if parsed_data:
                                if self.repository.save_order(file_path, parsed_data, file_hash):
                                    processed_files += 1
                                    new_stats.add_order(parsed_data)
                                    logging.info(f"Обновление за {days} дней: {file_name}")
                    except Exception as e:
                        logging.error(f"Ошибка обработки {file_name}: {e}")
                        continue

                # Обновляем статистику
                if processed_files > 0:
                    self._stats.merge(new_stats)
                    self._log_collected_statistics(f"обновление за {days} дней")

                    if not silent:
                        status_parts = []
                        if new_stats.emission_orders:
                            status_parts.append(f"📅 {len(new_stats.emission_orders)} с датой эмиссии")
                        if new_stats.solmark_orders:
                            status_parts.append(f"🖨 {len(new_stats.solmark_orders)} Solmark")
                        if new_stats.multi_customer_orders:
                            status_parts.append(f"👥 {len(new_stats.multi_customer_orders)} с многими заказчиками")
                        if new_stats.diameter_orders:
                            status_parts.append(f"📏 {len(new_stats.diameter_orders)} с diameter_mm")
                        if new_stats.labels_per_roll_orders:
                            status_parts.append(f"🏷 {len(new_stats.labels_per_roll_orders)} с labels_per_roll")
                        if new_stats.aggregation_orders:
                            status_parts.append(f"📦 {len(new_stats.aggregation_orders)} с агрегацией")

                        if status_parts:
                            status_msg = f"✅ Обновлено {processed_files} файлов за {days} дней ({', '.join(status_parts)})"
                        else:
                            status_msg = f"✅ Обновлено {processed_files} файлов за {days} дней"

                        if unchanged_files > 0:
                            status_msg += f" (еще {unchanged_files} без изменений)"

                        self._notify_status(status_msg)
                else:
                    if not silent:
                        if unchanged_files > 0:
                            self._notify_status(
                                f"📭 Все {unchanged_files} файлов за последние {days} дней уже актуальны")
                        else:
                            self._notify_status(f"📭 Новых изменений в файлах за последние {days} дней нет")

                return processed_files

            except Exception as e:
                logging.error(f"Ошибка проверки за {days} дней: {e}")
                self._notify_status(f"❌ Ошибка проверки: {e}")
                return 0
            finally:
                self._background_running = False
                if hasattr(self, '_background_lock'):
                    try:
                        self._background_lock.release()
                    except:
                        pass