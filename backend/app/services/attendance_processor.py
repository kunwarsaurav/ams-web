from sqlalchemy.orm import Session
from app.models.attendance import AttendanceLog, DailyAttendance
from app.models.employee import Employee
from app.schemas.attendance import AttendanceLogCreate
from datetime import datetime, date

class AttendanceProcessor:
    def __init__(self, db: Session):
        self.db = db

    def save_raw_logs(self, logs: list[AttendanceLogCreate]):
        for log in logs:
            db_log = AttendanceLog(**log.model_dump())
            self.db.add(db_log)
        self.db.commit()

    def process_daily_attendance(self, process_date: date):
        # Fetch all logs for the given date
        start_datetime = datetime.combine(process_date, datetime.min.time())
        end_datetime = datetime.combine(process_date, datetime.max.time())
        
        logs = self.db.query(AttendanceLog).filter(
            AttendanceLog.timestamp >= start_datetime,
            AttendanceLog.timestamp <= end_datetime
        ).order_by(AttendanceLog.timestamp.asc()).all()

        # Group logs by employee
        employee_logs = {}
        for log in logs:
            if log.machine_user_id not in employee_logs:
                employee_logs[log.machine_user_id] = []
            employee_logs[log.machine_user_id].append(log)

        employees = self.db.query(Employee).all()
        employee_map = {e.machine_user_id: e for e in employees}
        
        # Auto-create missing employees from logs so they show up on the dashboard!
        for log in logs:
            if log.machine_user_id not in employee_map:
                new_emp = Employee(
                    machine_user_id=log.machine_user_id,
                    full_name=f"Fetching... ({log.machine_user_id})",
                    department="Auto-Generated",
                    designation="Unknown",
                    status="Active",
                    is_synced=1
                )
                self.db.add(new_emp)
                self.db.commit()
                self.db.refresh(new_emp)
                employee_map[log.machine_user_id] = new_emp
                employees.append(new_emp)

        for emp in employees:
            existing = self.db.query(DailyAttendance).filter(
                DailyAttendance.employee_id == emp.id,
                DailyAttendance.date == process_date
            ).first()

            if not existing:
                existing = DailyAttendance(employee_id=emp.id, date=process_date)
                self.db.add(existing)
            
            logs_for_emp = employee_logs.get(emp.machine_user_id, [])
            
            if logs_for_emp:
                check_in = logs_for_emp[0].timestamp
                check_out = logs_for_emp[-1].timestamp if len(logs_for_emp) > 1 else None
                
                existing.check_in = check_in
                existing.check_out = check_out
                
                if check_in and check_out:
                    delta = check_out - check_in
                    existing.working_hours = delta.total_seconds() / 3600.0
                else:
                    existing.working_hours = 0.0
                
                existing.status = "Present"
            else:
                existing.check_in = None
                existing.check_out = None
                existing.working_hours = 0.0
                existing.status = "Absent"

        self.db.commit()

