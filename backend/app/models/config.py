from sqlalchemy import Column, Integer, String
from app.database.database import Base

class DeviceConfig(Base):
    __tablename__ = "device_config"

    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String, default="10.10.10.10")
