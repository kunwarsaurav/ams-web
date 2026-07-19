import sqlite3

conn = sqlite3.connect('ams.db')
cursor = conn.cursor()

print("--- Attendance Logs ---")
cursor.execute("SELECT * FROM attendance_logs ORDER BY id DESC LIMIT 5")
for row in cursor.fetchall():
    print(row)
    
print("--- Employees ---")
cursor.execute("SELECT * FROM employees ORDER BY id DESC LIMIT 5")
for row in cursor.fetchall():
    print(row)

conn.close()
