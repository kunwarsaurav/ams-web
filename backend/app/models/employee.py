from sqlalchemy import Column, Integer, String
from app.database.database import Base

class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    machine_user_id = Column(String, unique=True, index=True)
    full_name = Column(String, index=True)
    department = Column(String, index=True)
    designation = Column(String)
    status = Column(String, default="Active")
    is_synced = Column(Integer, default=0) # 0 for False, 1 for True
