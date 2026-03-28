import sqlite3
import os

path = r"C:\Users\User\AppData\Local\CodeMax-CutMaster\data"
db_path = os.path.join(path, "packaging_1_cex_local.db")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=== packaging_log (офлайн-записи) ===")
cursor.execute("SELECT id, synced, exported, source_row, source_sheet FROM packaging_log")
for row in cursor.fetchall():
    print(f"id={row[0]}, synced={row[1]}, exported={row[2]}, row={row[3]}, sheet={row[4]}")

print("\n=== packaging_log_backup (бэкап сети) ===")
cursor.execute("SELECT id, synced, exported, source_row, source_sheet FROM packaging_log_backup")
for row in cursor.fetchall():
    print(f"id={row[0]}, synced={row[1]}, exported={row[2]}, row={row[3]}, sheet={row[4]}")

conn.close()