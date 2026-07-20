from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from app.database.database import engine, Base, db_path
from app.api import employees, attendance, device, ai, auth
from app.models import config # To ensure it's registered
from app.websocket_manager import manager
from app.services.ai_service import ai_service_instance
from contextlib import asynccontextmanager

# Create database tables
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
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
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://40.81.245.157"], # Explicit origins required for credentials
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

@app.get("/database/backup")
def backup_database():
    return FileResponse(path=db_path, filename="ams_backup.db", media_type="application/octet-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)