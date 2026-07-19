import os
import random
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.models.employee import Employee
from app.models.attendance import AttendanceLog, DailyAttendance
from app.services.attendance_processor import AttendanceProcessor
from app.database.database import Base

dummy_db_path = "c:/Users/kunwa/Desktop/ams/dummy.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///{dummy_db_path}"

if os.path.exists(dummy_db_path):
    os.remove(dummy_db_path)

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def generate():
    db = SessionLocal()
    try:
        print("Seeding Employees...")
        
        departments = ["Engineering", "Sales", "HR", "Marketing", "Finance", "Operations", "Support"]
        designations = ["Developer", "Manager", "Analyst", "Director", "QA", "Executive", "Agent"]
        behaviors = ["Normal", "Late", "Early Leave", "Late & Early Leave", "Missing Checkout", "Overtime", "Perfect", "Frequent Absentee", "Night Shift"]

        employees = []
        for i in range(1, 51):
            behavior = random.choice(behaviors)
            emp = Employee(
                machine_user_id=str(2000 + i),
                full_name=f"Employee {i} ({behavior})",
                department=random.choice(departments),
                designation=random.choice(designations),
                status="Active"
            )
            db.add(emp)
            employees.append(emp)
        
        db.commit()

        print("Seeding Attendance Logs for the past 60 days...")
        today = datetime.now().date()
        logs_to_add = []

        for day_offset in range(60):
            process_date = today - timedelta(days=day_offset)
            
            for emp in employees:
                chance = 0.95
                if "Frequent Absentee" in emp.full_name:
                    chance = 0.60
                
                if process_date.weekday() >= 5 and "Night Shift" not in emp.full_name:
                    chance = 0.05
                    
                if random.random() < chance:
                    if "Normal" in emp.full_name or "Perfect" in emp.full_name:
                        check_in_time = datetime.combine(process_date, datetime.min.time()) + timedelta(hours=9, minutes=random.randint(50, 59))
                        check_out_time = datetime.combine(process_date, datetime.min.time()) + timedelta(hours=17, minutes=random.randint(0, 15))
                    elif "Late" in emp.full_name and "Early" not in emp.full_name:
                        check_in_time = datetime.combine(process_date, datetime.min.time()) + timedelta(hours=10, minutes=random.randint(30, 90))
                        check_out_time = datetime.combine(process_date, datetime.min.time()) + timedelta(hours=17, minutes=random.randint(0, 30))
                    elif "Early" in emp.full_name and "Late" not in emp.full_name:
                        check_in_time = datetime.combine(process_date, datetime.min.time()) + timedelta(hours=9, minutes=random.randint(50, 59))
                        check_out_time = datetime.combine(process_date, datetime.min.time()) + timedelta(hours=15, minutes=random.randint(0, 45))
                    elif "Late & Early" in emp.full_name:
                        check_in_time = datetime.combine(process_date, datetime.min.time()) + timedelta(hours=10, minutes=random.randint(30, 60))
                        check_out_time = datetime.combine(process_date, datetime.min.time()) + timedelta(hours=15, minutes=random.randint(0, 45))
                    elif "Missing Checkout" in emp.full_name:
                        check_in_time = datetime.combine(process_date, datetime.min.time()) + timedelta(hours=10, minutes=random.randint(0, 15))
                        check_out_time = None if random.random() > 0.3 else datetime.combine(process_date, datetime.min.time()) + timedelta(hours=17)
                    elif "Overtime" in emp.full_name:
                        check_in_time = datetime.combine(process_date, datetime.min.time()) + timedelta(hours=9, minutes=random.randint(50, 59))
                        check_out_time = datetime.combine(process_date, datetime.min.time()) + timedelta(hours=20, minutes=random.randint(0, 60))
                    elif "Night Shift" in emp.full_name:
                        check_in_time = datetime.combine(process_date, datetime.min.time()) + timedelta(hours=22, minutes=random.randint(0, 30))
                        check_out_time = datetime.combine(process_date, datetime.min.time()) + timedelta(hours=24 + 6, minutes=random.randint(0, 30))
                    else:
                        check_in_time = datetime.combine(process_date, datetime.min.time()) + timedelta(hours=10)
                        check_out_time = datetime.combine(process_date, datetime.min.time()) + timedelta(hours=17)

                    logs_to_add.append(AttendanceLog(
                        machine_user_id=emp.machine_user_id,
                        timestamp=check_in_time,
                        punch_type="CheckIn",
                        machine_id="PCTL-TEST"
                    ))
                    
                    if check_out_time:
                        logs_to_add.append(AttendanceLog(
                            machine_user_id=emp.machine_user_id,
                            timestamp=check_out_time,
                            punch_type="CheckOut",
                            machine_id="PCTL-TEST"
                        ))
        
        db.bulk_save_objects(logs_to_add)
        db.commit()

        print("Processing Daily Attendance (this may take a moment for 60 days)...")
        processor = AttendanceProcessor(db)
        for day_offset in range(60):
            process_date = today - timedelta(days=day_offset)
            processor.process_daily_attendance(process_date)

        print(f"Seeding completed! Database saved to {dummy_db_path}")
    finally:
        db.close()

if __name__ == "__main__":
    generate()
