import sqlite3
import os

APP_NAME = "SynthbitAMS"
app_data_dir = os.path.join(os.environ.get("APPDATA", ""), APP_NAME)
db_path = os.path.join(app_data_dir, "ams.db")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("--- Attendance Logs ---")
cursor.execute("SELECT * FROM attendance_logs ORDER BY id DESC LIMIT 5")
for row in cursor.fetchall():
    print(row)
    
print("--- Employees ---")
cursor.execute("SELECT * FROM employees ORDER BY id DESC LIMIT 10")
for row in cursor.fetchall():
    print(row)

conn.close()
