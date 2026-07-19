from pydantic import BaseModel
from typing import Optional

class EmployeeBase(BaseModel):
    machine_user_id: str
    full_name: str
    department: str
    designation: str
    email: Optional[str] = None
    status: Optional[str] = "Active"
    is_synced: Optional[int] = 0

class EmployeeCreate(EmployeeBase):
    pass

class EmployeeUpdate(EmployeeBase):
    pass

class Employee(EmployeeBase):
    id: int

    class Config:
        from_attributes = True
