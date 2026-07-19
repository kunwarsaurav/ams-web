import os
import platform
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

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

# Define the absolute path to ams.db
db_path = os.path.join(app_data_dir, "ams.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{db_path}"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
