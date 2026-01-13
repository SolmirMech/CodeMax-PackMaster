# diagnostic.py
import os
import sqlite3
import json
from pathlib import Path

appdata = Path(os.getenv('LOCALAPPDATA')) / "CodeMax-CutMaster" / "data"
db_path = appdata / "orders_cache.db"

print(f"БД существует: {db_path.exists()}")
if db_path.exists():
    print(f"Размер БД: {db_path.stat().st_size} байт")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Таблицы
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"\nТаблицы: {[t[0] for t in tables]}")
    
    # Количество записей
    for table in ['orders', 'products', 'sheets']:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"{table}: {count} записей")
        except:
            print(f"{table}: таблица не существует")
    
    # Примеры заказов
    cursor.execute("SELECT order_number, file_name FROM orders LIMIT 5")
    orders = cursor.fetchall()
    print(f"\nПервые 5 заказов:")
    for order_num, file_name in orders:
        print(f"  {order_num} -> {file_name}")
    
    conn.close()
else:
    print("БД не найдена!")
    # Проверяем папку
    print(f"Папка существует: {appdata.exists()}")
    print(f"Содержимое папки: {list(appdata.glob('*'))}")