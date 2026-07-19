import os
import random
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.models.employee import Employee
from app.models.attendance import AttendanceLog, DailyAttendance
from app.services.attendance_processor import AttendanceProcessor
from app.database.database import Base, db_path, engine, SessionLocal

def generate():
    print(f"Using database path: {db_path}")
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"Cleared existing database at {db_path}")

    # Create tables
    Base.metadata.create_all(bind=engine)

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
            
        # Add special test cases for AI Alerts
        emp_late_alert = Employee(
            machine_user_id="9998",
            full_name="AI Alert Test (3 Lates)",
            department="QA",
            designation="Tester",
            status="Active"
        )
        emp_absent_alert = Employee(
            machine_user_id="9999",
            full_name="AI Alert Test (3 Absences)",
            department="QA",
            designation="Tester",
            status="Active"
        )
        db.add(emp_late_alert)
        db.add(emp_absent_alert)
        employees.extend([emp_late_alert, emp_absent_alert])
        
        db.commit()

        print("Seeding Attendance Logs for the past 60 days...")
        today = datetime.now().date()
        logs_to_add = []

        for day_offset in range(60):
            process_date = today - timedelta(days=day_offset)
            
            for emp in employees:
                # Skip the AI test employees from random log generation, we will manually insert them later
                if "AI Alert Test" in emp.full_name:
                    continue
                    
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
            
        print("Injecting AI Alert Test Data...")
        # For emp_late_alert: inject 3 late checkins in last 3 days (after 10:15 AM)
        for i in range(1, 4):
            date = today - timedelta(days=i)
            late_checkin = datetime.combine(date, datetime.min.time()) + timedelta(hours=10, minutes=45)
            db.add(DailyAttendance(employee_id=emp_late_alert.id, date=date, check_in=late_checkin, status="Present"))
            
        # For emp_absent_alert: inject 3 absences in last 3 days
        for i in range(1, 4):
            date = today - timedelta(days=i)
            db.add(DailyAttendance(employee_id=emp_absent_alert.id, date=date, status="Absent"))

        db.commit()
        print(f"Seeding completed! Database saved to {db_path}")
    finally:
        db.close()

if __name__ == "__main__":
    generate()
