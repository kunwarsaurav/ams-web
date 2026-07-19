from abc import ABC, abstractmethod
from typing import List
from app.schemas.attendance import AttendanceLogCreate

class AttendanceProvider(ABC):
    @abstractmethod
    def fetch_logs(self, start_date=None, end_date=None) -> List[AttendanceLogCreate]:
        """
        Fetch raw attendance logs from the hardware/device.
        """
        pass

    @abstractmethod
    def add_employee(self, machine_user_id: str, full_name: str) -> bool:
        """
        Push a new employee to the hardware/device.
        """
        pass

    @abstractmethod
    def update_employee(self, machine_user_id: str, full_name: str) -> bool:
        """
        Update an existing employee on the hardware/device.
        """
        pass

    @abstractmethod
    def delete_employee(self, machine_user_id: str) -> bool:
        """
        Delete an employee from the hardware/device.
        """
        pass
