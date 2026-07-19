import traceback
from datetime import date
from app.database.database import SessionLocal
from app.api.attendance import export_attendance_excel
db=SessionLocal()
try:
    export_attendance_excel(date(2026, 6, 30), date(2026, 7, 7), db)
except Exception as e:
    traceback.print_exc()
