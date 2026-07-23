from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os

from app.database.database import Base, get_db, MasterSessionLocal, master_engine, app_data_dir, get_client_engine, get_client_db_path
from app.models.client import MasterBase, Client
from app.api import employees, attendance, device, ai, auth
from app.models import config # To ensure it's registered
from app.models.config import DeviceConfig
from app.websocket_manager import manager
from pydantic import BaseModel
from app.services.ai_service import ai_service_instance
from contextlib import asynccontextmanager
import sqlite3

def check_and_migrate_db(client_db_path: str, engine):
    try:
        # Create tables using SQLAlchemy
        Base.metadata.create_all(bind=engine)

        # Raw sqlite3 migration
        conn = sqlite3.connect(client_db_path)
        tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        if "device_config" in tables:
            columns = [row[1] for row in conn.execute("PRAGMA table_info(device_config)").fetchall()]
            if "admin_password" not in columns:
                conn.execute("ALTER TABLE device_config ADD COLUMN admin_password VARCHAR DEFAULT 'admin123'")
                conn.commit()
                print(f"Database Migration ({client_db_path}): Added 'admin_password' column to device_config.")
        conn.close()
    except Exception as e:
        print(f"Database Migration Error for {client_db_path}: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize Master DB
    MasterBase.metadata.create_all(bind=master_engine)
    
    master_db = MasterSessionLocal()
    try:
        saurav_client = master_db.query(Client).filter(Client.id == "saurav").first()
        if not saurav_client:
            saurav_client = Client(id="saurav", name="Saurav Default", db_filename="saurav.db")
            master_db.add(saurav_client)
            master_db.commit()
            
        # Migrate old ams.db to saurav.db if it exists
        old_db_path = os.path.join(app_data_dir, "ams.db")
        new_db_path = os.path.join(app_data_dir, "saurav.db")
        if os.path.exists(old_db_path) and not os.path.exists(new_db_path):
            os.rename(old_db_path, new_db_path)
            
        # Run migrations for all active clients
        active_clients = master_db.query(Client).filter(Client.is_active == True).all()
        for client in active_clients:
            db_path = os.path.join(app_data_dir, client.db_filename)
            engine = get_client_engine(client.db_filename)
            check_and_migrate_db(db_path, engine)
            
    finally:
        master_db.close()
    
    # Startup: Start Ollama if it's installed
    if ai_service_instance.is_ollama_installed():
        ai_service_instance.start_ollama()
    yield
    # Shutdown: Stop Ollama
    ai_service_instance.stop_ollama()

app = FastAPI(title="Attendance Management System API", lifespan=lifespan)


# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", 
        "http://127.0.0.1:5173",
        "http://40.81.245.157",       # VPS Nginx/Port 80
        "http://40.81.245.157:5173",  # VPS Vite Dev
        "http://40.81.245.157:4173",  # VPS Vite Preview
        "http://40.81.245.157:8000",  # VPS Frontend on port 8000!
        "http://40.81.245.157:8080"   # Direct backend
    ],
    allow_origin_regex=r"^https?://(.*\.)?(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(employees.router)
app.include_router(attendance.router)
app.include_router(device.router)
app.include_router(ai.router, prefix="/ai", tags=["AI"])
app.include_router(auth.router, prefix="/auth", tags=["Auth"])

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # We don't really expect client to send messages right now, but we keep it open
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Attendance Management System API"}

class BackupRequest(BaseModel):
    password: str

@app.post("/database/backup")
def backup_database(request: BackupRequest, x_client_id: str = Header(default="saurav"), db: Session = Depends(get_db)):
    device_config = db.query(DeviceConfig).first()
    if not device_config or request.password != device_config.admin_password:
        raise HTTPException(status_code=401, detail="Invalid password")
    
    try:
        client_db_path = get_client_db_path(x_client_id)
        return FileResponse(path=client_db_path, filename=f"{x_client_id}_backup.db", media_type="application/octet-stream")
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)