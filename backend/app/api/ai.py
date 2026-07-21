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
    model: str = "llama3.1:8b"

class QueryRequest(BaseModel):
    prompt: str
    model: str = "llama3.1:8b"

class DraftWarningRequest(BaseModel):
    employee_id: int
    lates: int
    absences: int
    start_date: str
    end_date: str
    model: str = "llama3.1:8b"

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
    request.model = "llama3.1:8b"
    if not ai_service_instance.is_ollama_running():
        with open("ai_debug.log", "a") as f:
            f.write(f"[{datetime.now()}] ERROR in query_ai: Ollama is not running\n")
        raise HTTPException(status_code=503, detail="Ollama is not running.")
        
    return StreamingResponse(
        ai_service_instance.generate_response(request.prompt, request.model),
        media_type="application/x-ndjson"
    )

@router.get("/alerts")
def get_ai_alerts(weeks_ago: int = 0, db: Session = Depends(get_db)):
    """Returns employees who have been late or absent >= 3 times in a specific 7-day window."""
    # Compute the date window
    end_date = datetime.now().date() - timedelta(days=weeks_ago * 7)
    start_date = end_date - timedelta(days=7)
    
    # Get all employees
    employees = db.query(Employee).filter(Employee.status != "Deleted").all()
    alerts = []
    
    for emp in employees:
        records = db.query(DailyAttendance).filter(
            DailyAttendance.employee_id == emp.id,
            DailyAttendance.date >= start_date,
            DailyAttendance.date < end_date
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
            
    return {
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "alerts": alerts
    }

@router.post("/draft-warning")
async def draft_warning(request: DraftWarningRequest, db: Session = Depends(get_db)):
    """Drafts an email warning using a deterministic template for 100% reliability."""
    emp = db.query(Employee).filter(Employee.id == request.employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
        
    config = db.query(DeviceConfig).first()
    company_name = config.company_name if config else "Synthbit Technologies"
    
    clean_name = emp.full_name.split('(')[0].strip().title()
    
    issues = []
    if request.lates > 0:
        issues.append(f"{request.lates} late arrival{'s' if request.lates > 1 else ''}")
    if request.absences > 0:
        issues.append(f"{request.absences} full absence{'s' if request.absences > 1 else ''}")
    issues_str = " and ".join(issues)
    
    # We use a deterministic template because tiny local LLMs (0.5b/1.5b) consistently hallucinate on strict HR formatting.
    template = (
        f"Subject: Official Attendance Warning\n\n"
        f"Dear {clean_name},\n\n"
        f"We are writing to officially address your recent attendance. According to our records from {request.start_date} to {request.end_date}, "
        f"you have had {issues_str}. This level of absenteeism is unacceptable and disrupts the team's workflow.\n\n"
        f"Please consider this a formal warning. We expect immediate improvement in your attendance and punctuality. "
        f"Be advised that any further infractions may lead to severe disciplinary action.\n\n"
        f"Regards,\n"
        f"HR Department, {company_name}"
    )

    async def stream_template():
        # Stream it in small chunks to simulate AI typing for a smooth UX
        import asyncio, json
        chunk_size = 4
        for i in range(0, len(template), chunk_size):
            chunk = template[i:i+chunk_size]
            yield json.dumps({"response": chunk, "done": False}) + "\n"
            await asyncio.sleep(0.01)
        yield json.dumps({"response": "", "done": True}) + "\n"
        
    return StreamingResponse(
        stream_template(),
        media_type="application/x-ndjson"
    )
