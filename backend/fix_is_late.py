import sqlite3
import os

APP_NAME = 'SynthbitAMS'
app_data_dir = os.path.join(os.environ.get('APPDATA', ''), APP_NAME)
db_path = os.path.join(app_data_dir, 'ams.db')

conn = sqlite3.connect(db_path)
c = conn.cursor()

# Recalculate is_late for ALL existing records:
# - is_late = 1 if check_in time is after 10:15 AM
# - is_late = 0 if absent (no check_in) or on time
c.execute("""
    UPDATE daily_attendance
    SET is_late = CASE
        WHEN check_in IS NOT NULL AND time(check_in) > '10:15:00' THEN 1
        ELSE 0
    END
""")
conn.commit()
updated = c.rowcount
print(f"Updated is_late for {updated} records.")

# Verify
c.execute("""
    SELECT e.full_name, da.status, da.is_late, da.check_in
    FROM daily_attendance da
    JOIN employees e ON e.id = da.employee_id
    WHERE da.date = '2026-07-19' AND da.check_in IS NOT NULL
    ORDER BY da.check_in
""")
rows = c.fetchall()
print(f"\nAll present employees on 2026-07-19 ({len(rows)} total):")
for r in rows:
    late_flag = "LATE" if r[2] == 1 else "on time"
    print(f"  {r[0]:40s} check_in={r[3]}  [{late_flag}]")

c.execute("""
    SELECT e.full_name, da.check_in
    FROM daily_attendance da
    JOIN employees e ON e.id = da.employee_id
    WHERE da.date = '2026-07-19' AND da.is_late = 1
""")
late_rows = c.fetchall()
print(f"\nLate employees on 2026-07-19: {len(late_rows)}")
for r in late_rows:
    print(f"  {r[0]} (checked in at {r[1]})")

conn.close()
