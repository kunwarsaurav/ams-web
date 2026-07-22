from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.orm import declarative_base
from datetime import datetime

MasterBase = declarative_base()

class Client(MasterBase):
    __tablename__ = "clients"

    id = Column(String, primary_key=True, index=True) # e.g., 'saurav'
    name = Column(String)                             # e.g., 'Saurav Corp'
    db_filename = Column(String)                      # e.g., 'saurav.db'
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
