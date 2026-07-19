from typing import List
import random
from datetime import datetime, timedelta
from app.integrations.provider import AttendanceProvider
from app.schemas.attendance import AttendanceLogCreate
from sqlalchemy.orm import Session
from app.models.employee import Employee

class PCTLMockAttendanceProvider(AttendanceProvider):
    def __init__(self, db: Session):
        self.db = db

    def fetch_logs(self, start_date=None, end_date=None) -> List[AttendanceLogCreate]:
        # Simulate generating mock logs for testing and demo purposes
        employees = self.db.query(Employee).all()
        if not employees:
            return []

        # We are disabling the mock data generation so it stops adding random punches.
        # Real devices use the webhook in device.py for real-time punches.
        logs = []
        return logs

    def add_employee(self, machine_user_id: str, full_name: str) -> bool:
        # Simulate success when pushing employee to mock machine
        return True

    def update_employee(self, machine_user_id: str, full_name: str) -> bool:
        # Simulate success when updating employee on mock machine
        return True

    def delete_employee(self, machine_user_id: str) -> bool:
        # Simulate success when deleting employee from mock machine
        return True
