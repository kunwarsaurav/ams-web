import random
from datetime import datetime, timedelta
from app.database.database import SessionLocal, engine, Base
from app.models.employee import Employee
from app.models.attendance import AttendanceLog, DailyAttendance
from app.services.attendance_processor import AttendanceProcessor

# Ensure tables exist
Base.metadata.create_all(bind=engine)

def seed_data():
    db = SessionLocal()
    try:
        # Check if we already have employees
        if db.query(Employee).count() > 0:
            print("Database already seeded!")
            return

        print("Seeding Employees...")
        # 5 Specific Test Users
        test_users = [
            {"id": "2001", "name": "Alice (Normal)", "dept": "Engineering", "desig": "Developer"},
            {"id": "2002", "name": "Bob (Late)", "dept": "Sales", "desig": "Executive"},
            {"id": "2003", "name": "Charlie (Early Leave)", "dept": "HR", "desig": "Manager"},
            {"id": "2004", "name": "Diana (Late & Early Leave)", "dept": "Marketing", "desig": "Analyst"},
            {"id": "2005", "name": "Eve (Missing Checkout)", "dept": "Finance", "desig": "Director"},
        ]

        employees = []
        for u in test_users:
            emp = Employee(
                machine_user_id=u["id"],
                full_name=u["name"],
                department=u["dept"],
                designation=u["desig"],
                status="Active"
            )
            db.add(emp)
            employees.append(emp)
        
        db.commit()

        print("Seeding Attendance Logs for the past 5 days...")
        today = datetime.now().date()
        logs_to_add = []

        for day_offset in range(5):
            process_date = today - timedelta(days=day_offset)
            
            for emp in employees:
                # 85% chance they showed up
                if random.random() < 0.85:
                    if "Normal" in emp.full_name:
                        # 10:00 AM - 10:15 AM
                        check_in_time = datetime.combine(process_date, datetime.min.time()) + timedelta(hours=10, minutes=random.randint(0, 15))
                        # 5:00 PM - 5:30 PM
                        check_out_time = datetime.combine(process_date, datetime.min.time()) + timedelta(hours=17, minutes=random.randint(0, 30))
                    elif "Bob (Late)" in emp.full_name:
                        # 10:30 AM - 11:00 AM (Late)
                        check_in_time = datetime.combine(process_date, datetime.min.time()) + timedelta(hours=10, minutes=random.randint(30, 60))
                        check_out_time = datetime.combine(process_date, datetime.min.time()) + timedelta(hours=17, minutes=random.randint(0, 30))
                    elif "Charlie" in emp.full_name:
                        # 10:00 AM - 10:15 AM
                        check_in_time = datetime.combine(process_date, datetime.min.time()) + timedelta(hours=10, minutes=random.randint(0, 15))
                        # 4:00 PM - 4:45 PM (Early Leave)
                        check_out_time = datetime.combine(process_date, datetime.min.time()) + timedelta(hours=16, minutes=random.randint(0, 45))
                    elif "Diana" in emp.full_name:
                        # Late & Early Leave
                        check_in_time = datetime.combine(process_date, datetime.min.time()) + timedelta(hours=10, minutes=random.randint(30, 60))
                        check_out_time = datetime.combine(process_date, datetime.min.time()) + timedelta(hours=16, minutes=random.randint(0, 45))
                    elif "Eve" in emp.full_name:
                        check_in_time = datetime.combine(process_date, datetime.min.time()) + timedelta(hours=10, minutes=random.randint(0, 15))
                        check_out_time = None
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
        
        for log in logs_to_add:
            db.add(log)
        db.commit()

        print("Processing Daily Attendance...")
        processor = AttendanceProcessor(db)
        for day_offset in range(5):
            process_date = today - timedelta(days=day_offset)
            processor.process_daily_attendance(process_date)

        print("Seeding completed successfully!")
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
