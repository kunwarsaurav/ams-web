import sqlite3
import os

APP_NAME = 'SynthbitAMS'
app_data_dir = os.path.join(os.environ.get('APPDATA', ''), APP_NAME)
db_path = os.path.join(app_data_dir, 'ams.db')

conn = sqlite3.connect(db_path)
c = conn.cursor()

try:
    c.execute("ALTER TABLE daily_attendance ADD COLUMN is_late BOOLEAN DEFAULT 0;")
    print('Added is_late column.')
except Exception as e:
    print('Column might already exist:', e)

c.execute("UPDATE daily_attendance SET is_late = 1 WHERE check_in IS NOT NULL AND time(check_in) > '10:15:00';")
conn.commit()
print('Updated is_late values.')
conn.close()
