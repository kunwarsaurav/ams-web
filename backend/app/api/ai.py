from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.services.ai_service import ai_service_instance

router = APIRouter()

class PullRequest(BaseModel):
    model: str = "gemma2:9b"

class QueryRequest(BaseModel):
    prompt: str
    model: str = "gemma2:9b"

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
    if not ai_service_instance.is_ollama_running():
        raise HTTPException(status_code=503, detail="Ollama is not running.")
        
    return StreamingResponse(
        ai_service_instance.generate_response(request.prompt, request.model),
        media_type="application/x-ndjson"
    )
