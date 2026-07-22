import os
import platform
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from fastapi import Header, HTTPException

APP_NAME = "SynthbitAMS"

# Determine the correct AppData folder depending on the OS
if platform.system() == "Windows":
    app_data_dir = os.path.join(os.environ.get("APPDATA", ""), APP_NAME)
elif platform.system() == "Darwin": # macOS
    app_data_dir = os.path.expanduser(f"~/Library/Application Support/{APP_NAME}")
else: # Linux
    app_data_dir = os.path.expanduser(f"~/.local/share/{APP_NAME}")

# Create the folder if it doesn't exist
os.makedirs(app_data_dir, exist_ok=True)

# ----------------- Master Database Setup -----------------
master_db_path = os.path.join(app_data_dir, "master.db")
master_engine = create_engine(
    f"sqlite:///{master_db_path}", connect_args={"check_same_thread": False}
)
MasterSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=master_engine)

# ----------------- Client Database Setup -----------------
Base = declarative_base()
_client_engines = {}

def get_client_engine(db_filename: str):
    """Returns a cached SQLAlchemy engine for a specific client DB."""
    if db_filename not in _client_engines:
        db_path = os.path.join(app_data_dir, db_filename)
        engine = create_engine(
            f"sqlite:///{db_path}", connect_args={"check_same_thread": False}
        )
        _client_engines[db_filename] = engine
    return _client_engines[db_filename]

def get_db(x_client_id: str = Header(default="saurav")):
    """FastAPI Dependency to get a tenant-aware database session."""
    from app.models.client import Client
    
    master_db = MasterSessionLocal()
    try:
        client = master_db.query(Client).filter(Client.id == x_client_id).first()
        if not client or not client.is_active:
            raise HTTPException(status_code=400, detail=f"Invalid or inactive client ID: {x_client_id}")
        
        engine = get_client_engine(client.db_filename)
        ClientSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = ClientSession()
        try:
            yield db
        finally:
            db.close()
    finally:
        master_db.close()

def get_client_db_path(x_client_id: str) -> str:
    """Helper to get the raw path for a client (useful for backups/exports)."""
    from app.models.client import Client
    master_db = MasterSessionLocal()
    try:
        client = master_db.query(Client).filter(Client.id == x_client_id).first()
        if not client:
            raise Exception("Client not found")
        return os.path.join(app_data_dir, client.db_filename)
    finally:
        master_db.close()
