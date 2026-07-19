from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date
from app.schemas.employee import Employee

class AttendanceLogBase(BaseModel):
    machine_user_id: str
    timestamp: datetime
    punch_type: str
    machine_id: str

class AttendanceLogCreate(AttendanceLogBase):
    pass

class AttendanceLog(AttendanceLogBase):
    id: int

    class Config:
        from_attributes = True

class DailyAttendanceBase(BaseModel):
    employee_id: int
    date: date
    check_in: Optional[datetime]
    check_out: Optional[datetime]
    working_hours: float
    status: str

class DailyAttendanceCreate(DailyAttendanceBase):
    pass

class DailyAttendance(DailyAttendanceBase):
    id: int
    employee: Optional[Employee] = None

    class Config:
        from_attributes = True
