import os
from datetime import datetime
from app.database.database import SessionLocal
from app.models.attendance import AttendanceLog
from app.models.employee import Employee

db = SessionLocal()
today = datetime.now().date()
start_dt = datetime.combine(today, datetime.min.time())
end_dt = datetime.combine(today, datetime.max.time())

logs = db.query(AttendanceLog).filter(
    AttendanceLog.timestamp >= start_dt,
    AttendanceLog.timestamp <= end_dt
).order_by(AttendanceLog.timestamp.desc()).all()

print(f"Start: {start_dt}, End: {end_dt}")
print(f"Found {len(logs)} logs.")
for log in logs:
    print(log.id, log.timestamp, log.machine_user_id)
