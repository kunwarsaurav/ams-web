from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import List
from datetime import date, datetime
import pandas as pd
from fastapi.responses import FileResponse
import os

from app.database.database import get_db
from app.models.attendance import DailyAttendance as DailyAttendanceModel
from app.models.employee import Employee as EmployeeModel
from app.schemas.attendance import DailyAttendance
from app.integrations.pctl_mock import PCTLMockAttendanceProvider
from app.services.attendance_processor import AttendanceProcessor

router = APIRouter(prefix="/attendance", tags=["Attendance"])

@router.post("/sync")
def sync_attendance(db: Session = Depends(get_db)):
    provider = PCTLMockAttendanceProvider(db)
    
    # 0. Push any unsynced employees to the machine
    unsynced_employees = db.query(EmployeeModel).filter(EmployeeModel.is_synced == 0).all()
    for emp in unsynced_employees:
        try:
            # Assuming add_employee acts as an upsert (update if exists)
            provider.add_employee(machine_user_id=emp.machine_user_id, full_name=emp.full_name)
            emp.is_synced = 1
        except ConnectionError:
            pass # Fails quietly, we will catch the main ConnectionError below anyway
    db.commit()

    # 1. Fetch raw logs from provider (Mock for now)
    
    try:
        logs = provider.fetch_logs()
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    
    # 2. Save raw logs & process
    processor = AttendanceProcessor(db)
    processor.save_raw_logs(logs)
    
    # Process for today
    today = datetime.now().date()
    processor.process_daily_attendance(today)
    
    return {"message": "Attendance synced successfully", "logs_synced": len(logs)}

@router.get("/today", response_model=List[DailyAttendance])
def get_today_attendance(db: Session = Depends(get_db)):
    today = datetime.now().date()
    return db.query(DailyAttendanceModel).filter(DailyAttendanceModel.date == today).all()

@router.get("/report", response_model=List[DailyAttendance])
def get_attendance_report(start_date: date, end_date: date, db: Session = Depends(get_db)):
    return db.query(DailyAttendanceModel).filter(
        DailyAttendanceModel.date >= start_date,
        DailyAttendanceModel.date <= end_date
    ).all()

@router.get("/monthly")
def get_monthly_summary(year: int, month: int, db: Session = Depends(get_db)):
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)
        
    records = db.query(DailyAttendanceModel).filter(
        DailyAttendanceModel.date >= start_date,
        DailyAttendanceModel.date < end_date
    ).all()
    
    # Simple summary
    summary = {}
    for r in records:
        if r.employee_id not in summary:
            summary[r.employee_id] = {"Present": 0, "Absent": 0, "employee": r.employee.full_name}
        summary[r.employee_id][r.status] += 1
        
    return summary

@router.get("/employee/{emp_id}", response_model=List[DailyAttendance])
def get_employee_attendance(emp_id: int, db: Session = Depends(get_db)):
    return db.query(DailyAttendanceModel).filter(DailyAttendanceModel.employee_id == emp_id).all()

@router.get("/export")
def export_attendance_excel(start_date: date, end_date: date, x_client_id: str = Header(default="saurav"), db: Session = Depends(get_db)):
    records = db.query(DailyAttendanceModel).filter(
        DailyAttendanceModel.date >= start_date,
        DailyAttendanceModel.date <= end_date
    ).all()
    
    data = []
    for r in records:
        emp_name = r.employee.full_name if r.employee else f"Deleted Employee"
        emp_uid = r.employee.machine_user_id if r.employee else f"ID: {r.employee_id}"
        emp_dept = r.employee.department if r.employee else "N/A"
        data.append({
            "Date": r.date,
            "Employee ID": emp_uid,
            "Employee Name": emp_name,
            "Department": emp_dept,
            "Check In": r.check_in.strftime("%H:%M:%S") if r.check_in else "",
            "Check Out": r.check_out.strftime("%H:%M:%S") if r.check_out else "",
            "Working Hours": round(r.working_hours, 2),
            "Status": r.status
        })
        
    df = pd.DataFrame(data)
    file_path = f"{x_client_id}_attendance_export.xlsx"
    df.to_excel(file_path, index=False)
    
    return FileResponse(path=file_path, filename=file_path, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@router.get("/logs/today")
def get_today_raw_logs(db: Session = Depends(get_db)):
    from app.models.attendance import AttendanceLog as AttendanceLogModel
    today = datetime.now().date()
    start_dt = datetime.combine(today, datetime.min.time())
    end_dt = datetime.combine(today, datetime.max.time())
    
    logs = db.query(AttendanceLogModel).filter(
        AttendanceLogModel.timestamp >= start_dt,
        AttendanceLogModel.timestamp <= end_dt
    ).order_by(AttendanceLogModel.timestamp.desc()).all()
    
    employees = db.query(EmployeeModel).all()
    emp_map = {e.machine_user_id: e.full_name for e in employees}
    
    result = []
    for log in logs:
        result.append({
            "id": log.id,
            "machine_user_id": log.machine_user_id,
            "employee_name": emp_map.get(log.machine_user_id, f"Unknown ({log.machine_user_id})"),
            "timestamp": log.timestamp.isoformat(),
            "punch_type": log.punch_type
        })
        
    return result

@router.delete("/today")
def delete_today_attendance(db: Session = Depends(get_db)):
    from app.models.attendance import AttendanceLog as AttendanceLogModel
    
    today = datetime.now().date()
    start_dt = datetime.combine(today, datetime.min.time())
    end_dt = datetime.combine(today, datetime.max.time())
    
    # Delete raw logs for today
    deleted_raw = db.query(AttendanceLogModel).filter(
        AttendanceLogModel.timestamp >= start_dt,
        AttendanceLogModel.timestamp <= end_dt
    ).delete(synchronize_session=False)
    
    # Delete daily attendance logs for today
    deleted_daily = db.query(DailyAttendanceModel).filter(
        DailyAttendanceModel.date == today
    ).delete(synchronize_session=False)
    
    db.commit()
    return {
        "message": "Today's attendance records deleted successfully",
        "raw_logs_deleted": deleted_raw,
        "daily_records_deleted": deleted_daily
    }

@router.delete("/report")
def delete_attendance_report(start_date: date, end_date: date, db: Session = Depends(get_db)):
    from app.models.attendance import AttendanceLog as AttendanceLogModel
    
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())
    
    # Delete raw logs in date range
    deleted_raw = db.query(AttendanceLogModel).filter(
        AttendanceLogModel.timestamp >= start_dt,
        AttendanceLogModel.timestamp <= end_dt
    ).delete(synchronize_session=False)
    
    # Delete daily attendance logs in date range
    deleted_daily = db.query(DailyAttendanceModel).filter(
        DailyAttendanceModel.date >= start_date,
        DailyAttendanceModel.date <= end_date
    ).delete(synchronize_session=False)
    
    db.commit()
    return {
        "message": f"Attendance records from {start_date} to {end_date} deleted successfully",
        "raw_logs_deleted": deleted_raw,
        "daily_records_deleted": deleted_daily
    }
