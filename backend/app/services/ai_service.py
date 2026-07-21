import os
import subprocess
import urllib.request
import json
import logging
import asyncio
from typing import Optional, AsyncGenerator
from datetime import datetime, timedelta
from app.database.database import SessionLocal
from app.models.employee import Employee
from app.models.attendance import DailyAttendance

logger = logging.getLogger(__name__)

OLLAMA_URL = "http://127.0.0.1:11434"
OLLAMA_INSTALLER_URL = "https://ollama.com/download/OllamaSetup.exe"

class AIService:
    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        
    def start_ollama(self):
        """Starts the local Ollama process."""
        if self.is_ollama_running():
            logger.info("Ollama is already running.")
            return

        try:
            self.process = subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            logger.info("Ollama started successfully in the background.")
        except FileNotFoundError:
            logger.warning("Ollama executable not found. It may not be installed.")
        except Exception as e:
            logger.error(f"Failed to start Ollama: {e}")

    def stop_ollama(self):
        """Stops the local Ollama process if we started it."""
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            logger.info("Ollama process stopped.")
            self.process = None

    def is_ollama_running(self) -> bool:
        """Checks if the Ollama API is reachable."""
        try:
            req = urllib.request.Request(OLLAMA_URL)
            with urllib.request.urlopen(req, timeout=2) as response:
                return response.status == 200
        except Exception:
            return False

    def is_ollama_installed(self) -> bool:
        """Checks if the ollama command is available in PATH."""
        try:
            result = subprocess.run(
                ["ollama", "--version"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False

    def install_ollama(self, installer_path: str = "OllamaSetup.exe") -> bool:
        """Downloads and installs Ollama silently."""
        try:
            if not os.path.exists(installer_path):
                logger.info(f"Downloading Ollama installer from {OLLAMA_INSTALLER_URL}...")
                urllib.request.urlretrieve(OLLAMA_INSTALLER_URL, installer_path)
            
            logger.info("Running Ollama installer silently...")
            subprocess.run(
                [installer_path, "/S", "/SILENT"],
                check=True
            )
            logger.info("Ollama installation completed.")
            return True
        except Exception as e:
            logger.error(f"Error installing Ollama: {e}")
            return False

    def get_installed_models(self) -> list:
        """Fetches a list of installed models."""
        try:
            req = urllib.request.Request(f"{OLLAMA_URL}/api/tags")
            with urllib.request.urlopen(req, timeout=2) as response:
                data = json.loads(response.read().decode())
                return [model["name"] for model in data.get("models", [])]
        except Exception as e:
            logger.error(f"Error fetching installed models: {e}")
            return []

    async def pull_model(self, model_name: str) -> AsyncGenerator[str, None]:
        """Pulls a model and yields streaming progress."""
        url = f"{OLLAMA_URL}/api/pull"
        data = json.dumps({"name": model_name}).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST", headers={'Content-Type': 'application/json'})
        
        try:
            # We use an executor because urllib blocks
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, urllib.request.urlopen, req)
            
            while True:
                line = await loop.run_in_executor(None, response.readline)
                if not line:
                    break
                await asyncio.sleep(0.01)
                yield line.decode("utf-8")
        except Exception as e:
            logger.error(f"Error pulling model: {e}")
            yield json.dumps({"error": str(e)})

    async def generate_response(self, prompt: str, model_name: str = "qwen2.5:1.5b", is_draft: bool = False) -> AsyncGenerator[str, None]:
        """Generates a response from the model based on the prompt, streaming the result."""
        if not self.is_ollama_running():
            yield json.dumps({"error": "Ollama is not running.", "done": True}) + "\n"
            return
            
        url = f"{OLLAMA_URL}/api/generate"
        
        context_str = ""
        system_prompt = ""
        enriched_prompt = prompt

        if not is_draft:
            # Build context from the database
            db = SessionLocal()
            context_str = "ATTENDANCE DATA SUMMARY:\n"
            try:
                recent_date = datetime.now().date() - timedelta(days=7)
                records = db.query(DailyAttendance).filter(DailyAttendance.date >= recent_date).order_by(DailyAttendance.date.desc()).limit(1000).all()
                
                emp_map = {emp.id: emp.full_name for emp in db.query(Employee).all()}
                
                # Group by date
                grouped_by_date = {}
                for r in records:
                    date_str = r.date.strftime("%Y-%m-%d") if r.date else "Unknown"
                    name = emp_map.get(r.employee_id, "Unknown")
                    
                    if date_str not in grouped_by_date:
                        grouped_by_date[date_str] = {
                            "ABSENT": [],
                            "LATE": [],
                            "MISSED_CHECKOUT": [],
                            "OVERTIME": [],
                            "NORMAL": []
                        }
                    
                    if r.status == "Absent":
                        grouped_by_date[date_str]["ABSENT"].append(name)
                    else:
                        is_normal = True
                        if r.check_in and r.check_in.strftime("%H:%M") > "10:15":
                            grouped_by_date[date_str]["LATE"].append(name)
                            is_normal = False
                        if r.status == "Present" and r.check_in and not r.check_out:
                            grouped_by_date[date_str]["MISSED_CHECKOUT"].append(name)
                            is_normal = False
                        if r.working_hours and r.working_hours > 8.0:
                            grouped_by_date[date_str]["OVERTIME"].append(name)
                            is_normal = False
                            
                        if is_normal:
                            grouped_by_date[date_str]["NORMAL"].append(name)
                
                # Build context string
                for d, categories in grouped_by_date.items():
                    context_str += f"\n--- DATE: {d} ---\n"
                    if categories["ABSENT"]:
                        context_str += f"ABSENT EMPLOYEES: {', '.join(categories['ABSENT'])}\n"
                    if categories["LATE"]:
                        context_str += f"LATE EMPLOYEES: {', '.join(categories['LATE'])}\n"
                    if categories["MISSED_CHECKOUT"]:
                        context_str += f"EMPLOYEES WHO MISSED CHECKOUT: {', '.join(categories['MISSED_CHECKOUT'])}\n"
                    if categories["OVERTIME"]:
                        context_str += f"EMPLOYEES WITH OVERTIME: {', '.join(categories['OVERTIME'])}\n"
                    if not any([categories["ABSENT"], categories["LATE"], categories["MISSED_CHECKOUT"], categories["OVERTIME"]]):
                        context_str += "All employees were normal on this day.\n"
                        
            except Exception as e:
                logger.error(f"Failed to fetch DB context: {e}")
                context_str += "Error loading data.\n"
            finally:
                db.close()
            
            system_prompt = (
                "You are SYNTHBIT AI 1.0, developed by Synthbit Technologies.\n"
                "CRITICAL RULES:\n"
                "1. Answer ONLY based on the ATTENDANCE DATA SUMMARY provided below.\n"
                "2. The data is grouped by DATE, and explicitly lists the names of employees who were ABSENT, LATE, etc.\n"
                "3. If a user asks 'who is absent', simply read the names from the 'ABSENT EMPLOYEES' list for the requested date.\n"
                "4. Be very concise. Use bullet points. Do not invent data."
            )
            
            enriched_prompt = f"{context_str}\n\nUser Question: {prompt}"
        else:
            system_prompt = "You are an AI that writes complete emails exactly as instructed. You never use placeholders."
        
        payload = {
            "model": model_name,
            "prompt": enriched_prompt,
            "system": system_prompt,
            "stream": True
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST", headers={'Content-Type': 'application/json'})
        
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, urllib.request.urlopen, req)
            
            while True:
                line = await loop.run_in_executor(None, response.readline)
                if not line:
                    break
                
                # Parse JSON to extract just the text if desired, or yield raw json string
                # We yield raw json strings to let the frontend parse it.
                await asyncio.sleep(0.01)
                yield line.decode("utf-8")
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            with open("ai_debug.log", "a") as f:
                f.write(f"[{datetime.now()}] ERROR in generate_response: {str(e)}\n")
            yield json.dumps({"error": str(e), "done": True}) + "\n"

ai_service_instance = AIService()
