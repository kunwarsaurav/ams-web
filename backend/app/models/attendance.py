from sqlalchemy import Column, Integer, String, DateTime, Date, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.database.database import Base
import datetime

class AttendanceLog(Base):
    __tablename__ = "attendance_logs"

    id = Column(Integer, primary_key=True, index=True)
    machine_user_id = Column(String, index=True)
    timestamp = Column(DateTime, index=True)
    punch_type = Column(String)
    machine_id = Column(String)

class DailyAttendance(Base):
    __tablename__ = "daily_attendance"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"))
    date = Column(Date, index=True)
    check_in = Column(DateTime, nullable=True)
    check_out = Column(DateTime, nullable=True)
    working_hours = Column(Float, default=0.0)
    status = Column(String) # Present, Absent, Half Day, etc.

    employee = relationship("Employee")
