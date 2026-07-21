import sqlite3
import os

APP_NAME = 'SynthbitAMS'
app_data_dir = os.path.join(os.environ.get('APPDATA', ''), APP_NAME)
db_path = os.path.join(app_data_dir, 'ams.db')

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
c = conn.cursor()

print("=== Daily Attendance columns ===")
c.execute("PRAGMA table_info(daily_attendance)")
for row in c.fetchall():
    print(dict(row))

print("\n=== Sample records on 2026-07-19 (first 15) ===")
c.execute("""
    SELECT e.full_name, da.status, da.is_late, da.check_in
    FROM daily_attendance da
    JOIN employees e ON e.id = da.employee_id
    WHERE da.date = '2026-07-19'
    LIMIT 15
""")
for row in c.fetchall():
    print(dict(row))

print("\n=== Late employees on 2026-07-19 ===")
c.execute("""
    SELECT e.full_name, da.check_in
    FROM daily_attendance da
    JOIN employees e ON e.id = da.employee_id
    WHERE da.date = '2026-07-19' AND da.is_late = 1
""")
rows = c.fetchall()
print(f"Total late: {len(rows)}")
for row in rows:
    print(dict(row))

conn.close()
