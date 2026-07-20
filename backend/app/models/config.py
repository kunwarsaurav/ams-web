from sqlalchemy import Column, Integer, String, DateTime
from app.database.database import Base

class DeviceConfig(Base):
    __tablename__ = "device_config"

    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String, default="10.10.10.10")
    company_name = Column(String, default="Synthbit Technologies")
    hr_email = Column(String, default="hr@synthbit.com")
    admin_password = Column(String, default="admin123")

class AdminSession(Base):
    __tablename__ = "admin_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_token = Column(String, unique=True, index=True)
    expires_at = Column(DateTime)
