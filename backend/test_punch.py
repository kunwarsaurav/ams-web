import os
import json
from datetime import datetime
from app.database.database import SessionLocal
from app.models.attendance import AttendanceLog
from app.services.attendance_processor import AttendanceProcessor
from app.models.employee import Employee

db = SessionLocal()
text_body = '{"fk_bin_data_lib":"FKDataHS105","io_mode":285212681,"io_time":"20260710001432","log_image":null,"user_id":"1","verify_mode":268435456}'
data = json.loads(text_body)

user_id = data.get("user_id")
io_time_str = data.get("io_time")
timestamp = datetime.strptime(io_time_str, "%Y%m%d%H%M%S")

new_log = AttendanceLog(
    machine_user_id=str(user_id),
    timestamp=timestamp,
    punch_type=data.get("verify_mode", "0"),
    machine_id="C26188C41B251635"
)
try:
    db.add(new_log)
    db.commit()
    print("Log saved successfully.")
except Exception as e:
    print("Error saving log:", e)
    db.rollback()

processor = AttendanceProcessor(db)
try:
    processor.process_daily_attendance(timestamp.date())
    print("Process daily attendance successful.")
except Exception as e:
    print("Error processing attendance:", e)

employees = db.query(Employee).all()
for emp in employees:
    print(emp.id, emp.machine_user_id, emp.full_name)
