from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.services.ai_service import ai_service_instance
from app.database.database import get_db
from app.models.employee import Employee
from app.models.attendance import DailyAttendance
from app.models.config import DeviceConfig

router = APIRouter()

class PullRequest(BaseModel):
    model: str = "qwen2.5:0.5b"

class QueryRequest(BaseModel):
    prompt: str
    model: str = "qwen2.5:0.5b"

class DraftWarningRequest(BaseModel):
    employee_id: int
    lates: int
    absences: int
    model: str = "qwen2.5:0.5b"

@router.get("/status")
def get_ai_status():
    """Returns the current status of the AI service."""
    is_installed = ai_service_instance.is_ollama_installed()
    is_running = ai_service_instance.is_ollama_running()
    
    models = []
    if is_running:
        models = ai_service_instance.get_installed_models()
        
    return {
        "installed": is_installed,
        "running": is_running,
        "models": models
    }

@router.post("/setup/install")
def install_ai(background_tasks: BackgroundTasks):
    """Triggers background installation of Ollama."""
    def run_install():
        success = ai_service_instance.install_ollama()
        if success:
            ai_service_instance.start_ollama()
            
    background_tasks.add_task(run_install)
    return {"message": "Installation started in the background."}

@router.post("/setup/pull")
async def pull_model(request: PullRequest):
    """Pulls an AI model and streams the download progress."""
    if not ai_service_instance.is_ollama_running():
        raise HTTPException(status_code=503, detail="Ollama is not running.")
        
    return StreamingResponse(
        ai_service_instance.pull_model(request.model),
        media_type="application/x-ndjson"
    )

@router.post("/query")
async def query_ai(request: QueryRequest):
    """Queries the AI and streams the generated response."""
    request.model = "qwen2.5:0.5b"
    if not ai_service_instance.is_ollama_running():
        with open("ai_debug.log", "a") as f:
            f.write(f"[{datetime.now()}] ERROR in query_ai: Ollama is not running\n")
        raise HTTPException(status_code=503, detail="Ollama is not running.")
        
    return StreamingResponse(
        ai_service_instance.generate_response(request.prompt, request.model),
        media_type="application/x-ndjson"
    )

@router.get("/alerts")
def get_ai_alerts(db: Session = Depends(get_db)):
    """Returns employees who have been late or absent >= 3 times in the last 7 days."""
    recent_date = datetime.now().date() - timedelta(days=7)
    
    # Get all employees
    employees = db.query(Employee).filter(Employee.status != "Deleted").all()
    alerts = []
    
    for emp in employees:
        records = db.query(DailyAttendance).filter(
            DailyAttendance.employee_id == emp.id,
            DailyAttendance.date >= recent_date
        ).all()
        
        lates = 0
        absences = 0
        
        for r in records:
            if r.status == "Absent":
                absences += 1
            elif r.check_in and r.check_in.strftime("%H:%M") > "10:15":
                lates += 1
                
        if lates >= 3 or absences >= 3:
            alerts.append({
                "employee_id": emp.id,
                "full_name": emp.full_name,
                "email": emp.email,
                "department": emp.department,
                "lates": lates,
                "absences": absences
            })
            
    return {"alerts": alerts}

@router.post("/draft-warning")
async def draft_warning(request: DraftWarningRequest, db: Session = Depends(get_db)):
    """Drafts an email warning using the AI."""
    request.model = "qwen2.5:0.5b"
    if not ai_service_instance.is_ollama_running():
        with open("ai_debug.log", "a") as f:
            f.write(f"[{datetime.now()}] ERROR in draft_warning: Ollama is not running\n")
        raise HTTPException(status_code=503, detail="Ollama is not running.")
        
    emp = db.query(Employee).filter(Employee.id == request.employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
        
    config = db.query(DeviceConfig).first()
    company_name = config.company_name if config else "Synthbit Technologies"
    
    prompt = (
        f"Please draft a professional but firm warning email to {emp.full_name} who works in the {emp.department} department. "
        f"In the last 7 days, they have had {request.lates} late arrivals and {request.absences} full absences. "
        f"The email should be sent on behalf of the HR Department at {company_name}. "
        f"Keep it concise, corporate, and clear that further infractions may lead to disciplinary action. "
        f"Do not include placeholders for date/time, just write the body of the email directly."
    )
    
    return StreamingResponse(
        ai_service_instance.generate_response(prompt, request.model),
        media_type="application/x-ndjson"
    )
