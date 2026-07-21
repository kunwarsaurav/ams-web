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
            context_str = "Recent Attendance Data (Last 7 Days):\n"
            try:
                # Only fetch the last 7 days to prevent context window overflow with many employees
                recent_date = datetime.now().date() - timedelta(days=7)
                # Cap at 250 records max (approx 6,500 tokens) to guarantee it fits in an 8K context window
                records = db.query(DailyAttendance).filter(DailyAttendance.date >= recent_date).order_by(DailyAttendance.date.desc()).limit(250).all()
                
                # Group by employee for a cleaner prompt
                emp_map = {}
                for emp in db.query(Employee).all():
                    emp_map[emp.id] = {
                        "name": emp.full_name,
                        "dept": emp.department,
                        "role": emp.designation
                    }
                
                for r in records:
                    emp_info = emp_map.get(r.employee_id, {"name": "Unknown", "dept": "Unknown", "role": "Unknown"})
                    name = emp_info["name"]
                    dept = emp_info["dept"]
                    role = emp_info["role"]
                    
                    date_str = r.date.strftime("%Y-%m-%d") if r.date else "Unknown"
                    status = r.status
                    check_in = r.check_in.strftime("%H:%M") if r.check_in else "None"
                    check_out = r.check_out.strftime("%H:%M") if r.check_out else "None"
                    hours = round(r.working_hours, 1) if r.working_hours else 0.0
                    
                    # Pre-calculate flags so the tiny AI model doesn't have to do the math
                    flags = []
                    if r.status == "Absent":
                        flags.append("ABSENT")
                    if r.check_in and r.check_in.strftime("%H:%M") > "10:15":
                        flags.append("LATE")
                    if r.status == "Present" and r.check_in and not r.check_out:
                        flags.append("MISSED_CHECKOUT")
                    if hours > 8.0:
                        flags.append("OVERTIME")
                        
                    flags_str = f"[{', '.join(flags)}]" if flags else "[ON TIME/NORMAL]"
                    
                    context_str += f"- {name} ({role} in {dept}) on {date_str}: {status} {flags_str}, IN: {check_in}, OUT: {check_out}, Hours: {hours}h\n"
            except Exception as e:
                logger.error(f"Failed to fetch DB context: {e}")
                context_str += "(Failed to load database records)\n"
            finally:
                db.close()
            
            system_prompt = (
                "You are SYNTHBIT AI 1.0, a highly intelligent, proactive AI assistant for an Attendance Management System developed by Synthbit Technologies. "
                "CRITICAL IDENTITY INSTRUCTION: If asked about your identity, what model you are, who created you, or anything related to AI models, you MUST reply that you are SYNTHBIT AI 1.0 developed by Synthbit Technologies. Never mention Gemma, Llama, OpenAI, Anthropic, Google, or any other underlying model architecture. "
                "You help managers understand attendance data. Always be concise, accurate, and highly analytical.\n\n"
                "CRITICAL RULES FOR ANSWERING:\n"
                "1. DO NOT guess or calculate who is late, who missed checkout, or who is absent. I have already calculated this for you in the context provided.\n"
                "2. Simply look at the flags next to the employee's name. The flags will say [LATE], [ABSENT], [MISSED_CHECKOUT], [OVERTIME], or [ON TIME/NORMAL].\n"
                "3. If a user asks 'who is late', ONLY list employees who have the [LATE] flag.\n"
                "4. Be brief. List the names clearly."
            )
            
            enriched_prompt = (
                f"Given the following database context, please answer the user's question directly and intelligently based ONLY on the flags provided next to each record.\n\n"
                f"{context_str}\n\nUser Question: {prompt}"
            )
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
