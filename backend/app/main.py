from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.database.database import engine, Base, db_path, get_db
from app.api import employees, attendance, device, ai, auth
from app.models import config # To ensure it's registered
from app.models.config import DeviceConfig
from app.websocket_manager import manager
from pydantic import BaseModel
from app.services.ai_service import ai_service_instance
from contextlib import asynccontextmanager
import sqlite3

def check_and_migrate_db():
    try:
        conn = sqlite3.connect(db_path)
        # Check if table exists first
        tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        if "device_config" in tables:
            columns = [row[1] for row in conn.execute("PRAGMA table_info(device_config)").fetchall()]
            if "admin_password" not in columns:
                conn.execute("ALTER TABLE device_config ADD COLUMN admin_password VARCHAR DEFAULT 'admin123'")
                conn.commit()
                print("Database Migration: Added 'admin_password' column to device_config.")
        conn.close()
    except Exception as e:
        print(f"Database Migration Error: {e}")

# Create database tables
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run migrations
    check_and_migrate_db()
    
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
def backup_database(request: BackupRequest, db: Session = Depends(get_db)):
    device_config = db.query(DeviceConfig).first()
    if not device_config or request.password != device_config.admin_password:
        raise HTTPException(status_code=401, detail="Invalid password")
    return FileResponse(path=db_path, filename="ams_backup.db", media_type="application/octet-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)