import os
import subprocess
import urllib.request
import json
import logging
import asyncio
from typing import Optional, AsyncGenerator
from datetime import datetime, timedelta
from app.models.employee import Employee
from app.models.attendance import DailyAttendance
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Configurable via environment variable — set OLLAMA_URL on VPS if Ollama runs on a different host/port
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")

# Absolute log path so it survives git pulls and working directory changes
AI_DEBUG_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ai_debug.log")


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

    async def generate_response(self, prompt: str, db: Session, model_name: str = "llama3.1:8b", is_draft: bool = False) -> AsyncGenerator[str, None]:
        """Generates a response from the model based on the prompt, streaming the result."""
        if not self.is_ollama_running():
            yield json.dumps({"error": "Ollama is not running.", "done": True}) + "\n"
            return
            
        url = f"{OLLAMA_URL}/api/generate"
        
        context_str = ""
        system_prompt = ""
        enriched_prompt = prompt

        if not is_draft:
            import re, calendar
            from datetime import date as _date
            p_lower = prompt.lower()
            now = datetime.now()
            current_date = now.strftime("%Y-%m-%d")
            yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")

            # --- STEP 1: RESOLVE DATE / DATE RANGE ---
            target_date = current_date
            range_start = None
            range_end   = None
            range_label = ""

            # Priority 1: explicit YYYY-MM-DD
            date_match = re.search(r'\d{4}-\d{2}-\d{2}', prompt)
            if date_match:
                target_date = date_match.group(0)
            else:
                # Priority 2: natural language dates — "19th july", "july 19", "19 july 2026"
                months = {"jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,
                          "jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12,
                          "january":1,"february":2,"march":3,"april":4,"june":6,
                          "july":7,"august":8,"september":9,"october":10,"november":11,"december":12}
                nat_match = re.search(
                    r'(\d{1,2})(?:st|nd|rd|th)?\s+(' + '|'.join(months.keys()) + r')(?:\s+(\d{4}))?'
                    r'|(' + '|'.join(months.keys()) + r')\s+(\d{1,2})(?:st|nd|rd|th)?(?:\s+(\d{4}))?',
                    p_lower
                )
                if nat_match:
                    g = nat_match.groups()
                    if g[0]:  # "19th july 2026"
                        day, mon_str, yr = int(g[0]), g[1][:3], int(g[2]) if g[2] else now.year
                    else:     # "july 19 2026"
                        mon_str, day, yr = g[3][:3], int(g[4]), int(g[5]) if g[5] else now.year
                    mon = months.get(mon_str, now.month)
                    target_date = f"{yr:04d}-{mon:02d}-{day:02d}"
                elif "yesterday" in p_lower:
                    target_date = yesterday

            # Multi-day ranges
            if "this month" in p_lower:
                range_start = now.replace(day=1).strftime("%Y-%m-%d")
                range_end   = current_date
                range_label = now.strftime("%B %Y")
            elif "last month" in p_lower:
                first_this       = now.replace(day=1)
                last_month_end   = first_this - timedelta(days=1)
                last_month_start = last_month_end.replace(day=1)
                range_start = last_month_start.strftime("%Y-%m-%d")
                range_end   = last_month_end.strftime("%Y-%m-%d")
                range_label = last_month_end.strftime("%B %Y")
            elif "this week" in p_lower:
                week_start  = now - timedelta(days=now.weekday())
                range_start = week_start.strftime("%Y-%m-%d")
                range_end   = current_date
                range_label = f"this week ({range_start} to {range_end})"
            elif "last week" in p_lower:
                this_week_start = now - timedelta(days=now.weekday())
                last_week_end   = this_week_start - timedelta(days=1)
                last_week_start = last_week_end - timedelta(days=6)
                range_start = last_week_start.strftime("%Y-%m-%d")
                range_end   = last_week_end.strftime("%Y-%m-%d")
                range_label = f"last week ({range_start} to {range_end})"

            is_range = range_start is not None

            # Employee name extraction (broader patterns)
            name_match = re.search(
                r"(?:for|about|of|did|employee(?:\s+name)?)\s+([a-z][\w\s\(\)]+?)(?:\s+check|\s+attend|\s+come|\s+on\s|\s+today|\s+yesterday|$|\?)",
                p_lower
            )
            target_name = name_match.group(1).strip() if name_match else None

            # --- STEP 2: DETECT INTENT ---
            attendance_keywords = [
                "absent", "late", "present", "attendance", "check in", "check-in",
                "check out", "check-out", "overtime", "working hours", "summary",
                "report", "employee", "who", "how many", "month", "week",
                "today", "yesterday", "frequent", "department", "punctual",
                "info", "detail", "profile", "role", "title", "designation"
            ]
            requires_db = any(k in p_lower for k in attendance_keywords)

            # --- STEP 3: BUILD SQL (Python, 100% deterministic) ---
            # ORDER MATTERS: more specific checks first to avoid wrong branch
            generated_sql    = None
            sql_context_label = ""
            query_mode = "llm"

            if requires_db:

                # ── EMPLOYEE PROFILE (info / details / who is) ───────────────
                if any(k in p_lower for k in ["info about", "details of", "detail of", "who is", "everything about",
                                               "tell me about", "profile of", "role", "designation", "title"]) and target_name:
                    generated_sql = (
                        f"SELECT e.full_name, e.department, e.designation, e.status, e.machine_user_id, "
                        f"COUNT(CASE WHEN da.status='Present' THEN 1 END) as days_present, "
                        f"COUNT(CASE WHEN da.status='Absent' THEN 1 END) as days_absent, "
                        f"COUNT(CASE WHEN da.is_late=1 THEN 1 END) as days_late, "
                        f"round(AVG(CASE WHEN da.working_hours>0 THEN da.working_hours END), 2) as avg_hours "
                        f"FROM employees e LEFT JOIN daily_attendance da ON e.id = da.employee_id "
                        f"WHERE e.full_name LIKE '%{target_name}%' GROUP BY e.id"
                    )
                    sql_context_label = f"Employee profile: {target_name}"
                    query_mode = "summary"

                # ── FREQUENT ABSENTEES (must be before absent+who) ───────────
                elif "frequent" in p_lower or ("most" in p_lower and ("absent" in p_lower or "late" in p_lower)):
                    r_start = range_start or (now - timedelta(days=30)).strftime("%Y-%m-%d")
                    r_end   = range_end   or current_date
                    if "late" in p_lower and "absent" not in p_lower:
                        generated_sql = (
                            f"SELECT e.full_name, COUNT(*) as late_days "
                            f"FROM employees e JOIN daily_attendance da ON e.id = da.employee_id "
                            f"WHERE da.date BETWEEN '{r_start}' AND '{r_end}' AND da.is_late = 1 "
                            f"GROUP BY e.id HAVING late_days >= 2 ORDER BY late_days DESC LIMIT 20"
                        )
                        sql_context_label = f"Most frequent late-comers ({r_start} to {r_end})"
                    else:
                        generated_sql = (
                            f"SELECT e.full_name, COUNT(*) as absent_days "
                            f"FROM employees e JOIN daily_attendance da ON e.id = da.employee_id "
                            f"WHERE da.date BETWEEN '{r_start}' AND '{r_end}' AND da.status = 'Absent' "
                            f"GROUP BY e.id HAVING absent_days >= 2 ORDER BY absent_days DESC LIMIT 20"
                        )
                        sql_context_label = f"Frequent absentees ({r_start} to {r_end})"
                    query_mode = "list"

                # ── DEPARTMENT PUNCTUALITY ────────────────────────────────────
                elif "department" in p_lower and any(k in p_lower for k in ["punctual", "best", "worst", "on time", "late"]):
                    r_start = range_start or (now - timedelta(days=30)).strftime("%Y-%m-%d")
                    r_end   = range_end   or current_date
                    generated_sql = (
                        f"SELECT e.department, "
                        f"COUNT(CASE WHEN da.status='Present' THEN 1 END) as present_days, "
                        f"COUNT(CASE WHEN da.is_late=1 THEN 1 END) as late_days, "
                        f"round(100.0 * COUNT(CASE WHEN da.is_late=1 THEN 1 END) / MAX(1, COUNT(CASE WHEN da.status='Present' THEN 1 END)), 1) as late_pct "
                        f"FROM employees e JOIN daily_attendance da ON e.id = da.employee_id "
                        f"WHERE da.date BETWEEN '{r_start}' AND '{r_end}' "
                        f"GROUP BY e.department ORDER BY late_pct ASC"
                    )
                    sql_context_label = f"Department punctuality ({r_start} to {r_end})"
                    query_mode = "summary"

                # ── WHO WAS ABSENT ────────────────────────────────────────────
                elif "absent" in p_lower and "who" in p_lower:
                    if is_range:
                        generated_sql = (
                            f"SELECT e.full_name, COUNT(*) as absent_days "
                            f"FROM employees e JOIN daily_attendance da ON e.id = da.employee_id "
                            f"WHERE da.date BETWEEN '{range_start}' AND '{range_end}' AND da.status = 'Absent' "
                            f"GROUP BY e.id ORDER BY absent_days DESC, e.full_name"
                        )
                        sql_context_label = f"Absent employees in {range_label}"
                    else:
                        generated_sql = (
                            f"SELECT e.full_name FROM employees e "
                            f"JOIN daily_attendance da ON e.id = da.employee_id "
                            f"WHERE da.date = '{target_date}' AND da.status = 'Absent' ORDER BY e.full_name"
                        )
                        sql_context_label = f"Absent employees on {target_date}"
                    query_mode = "list"

                # ── WHO WAS LATE ──────────────────────────────────────────────
                elif "late" in p_lower and "who" in p_lower:
                    if is_range:
                        generated_sql = (
                            f"SELECT e.full_name, COUNT(*) as late_days "
                            f"FROM employees e JOIN daily_attendance da ON e.id = da.employee_id "
                            f"WHERE da.date BETWEEN '{range_start}' AND '{range_end}' AND da.is_late = 1 "
                            f"GROUP BY e.id ORDER BY late_days DESC, e.full_name"
                        )
                        sql_context_label = f"Late employees in {range_label}"
                    else:
                        generated_sql = (
                            f"SELECT e.full_name, time(da.check_in) as check_in_time "
                            f"FROM employees e JOIN daily_attendance da ON e.id = da.employee_id "
                            f"WHERE da.date = '{target_date}' AND da.is_late = 1 ORDER BY e.full_name"
                        )
                        sql_context_label = f"Late employees on {target_date}"
                    query_mode = "list"

                # ── WHO DID OVERTIME ──────────────────────────────────────────
                elif ("overtime" in p_lower or "over time" in p_lower) and "who" in p_lower:
                    if is_range:
                        generated_sql = (
                            f"SELECT e.full_name, round(SUM(da.working_hours) - COUNT(*)*8, 2) as overtime_hours "
                            f"FROM employees e JOIN daily_attendance da ON e.id = da.employee_id "
                            f"WHERE da.date BETWEEN '{range_start}' AND '{range_end}' AND da.working_hours > 8 "
                            f"GROUP BY e.id ORDER BY overtime_hours DESC"
                        )
                        sql_context_label = f"Overtime employees in {range_label}"
                    else:
                        generated_sql = (
                            f"SELECT e.full_name, round(da.working_hours, 2) as working_hours "
                            f"FROM employees e JOIN daily_attendance da ON e.id = da.employee_id "
                            f"WHERE da.date = '{target_date}' AND da.working_hours > 8 ORDER BY da.working_hours DESC"
                        )
                        sql_context_label = f"Overtime employees on {target_date}"
                    query_mode = "list"

                # ── WHO WAS PRESENT ───────────────────────────────────────────
                elif "present" in p_lower and "who" in p_lower:
                    generated_sql = (
                        f"SELECT e.full_name, time(da.check_in) as check_in_time "
                        f"FROM employees e JOIN daily_attendance da ON e.id = da.employee_id "
                        f"WHERE da.date = '{target_date}' AND da.status = 'Present' ORDER BY da.check_in"
                    )
                    sql_context_label = f"Present employees on {target_date}"
                    query_mode = "list"

                # ── CHECK-IN / CHECK-OUT for a person ────────────────────────
                elif "check" in p_lower and (target_name or "saurav" in p_lower or "employee" in p_lower):
                    # Try to extract name more broadly if regex didn't catch it
                    if not target_name:
                        name_broad = re.search(
                            r"(?:employee(?:\s+name)?|named?|for|the)\s+([\w\s\(\)]+?)(?:\s+check|\s+on\s|$|\?)",
                            p_lower
                        )
                        target_name = name_broad.group(1).strip() if name_broad else None

                    if target_name:
                        # Word-boundary LIKE: "employee 3" should NOT match "employee 30"
                        # Use: LIKE 'name %' OR LIKE 'name(%' OR = 'name'
                        t = target_name.lower()
                        name_filter = (
                            f"(lower(e.full_name) = '{t}' "
                            f"OR lower(e.full_name) LIKE '{t} %' "
                            f"OR lower(e.full_name) LIKE '{t}(%')"
                        )
                        generated_sql = (
                            f"SELECT e.full_name, e.department, e.designation, "
                            f"time(da.check_in) as check_in_time, time(da.check_out) as check_out_time, "
                            f"da.status, da.is_late, round(da.working_hours, 2) as working_hours "
                            f"FROM employees e JOIN daily_attendance da ON e.id = da.employee_id "
                            f"WHERE {name_filter} AND da.date = '{target_date}'"
                        )
                        sql_context_label = f"Attendance for '{target_name}' on {target_date}"
                        query_mode = "summary"   # LLM phrases it naturally, not as a raw list

                # ── SUMMARY / REPORT ──────────────────────────────────────────
                elif "summary" in p_lower or "report" in p_lower:
                    if is_range:
                        generated_sql = (
                            f"SELECT COUNT(DISTINCT da.date) as working_days, "
                            f"COUNT(DISTINCT e.id) as total_employees, "
                            f"SUM(CASE WHEN da.status='Present' THEN 1 ELSE 0 END) as total_present, "
                            f"SUM(CASE WHEN da.status='Absent' THEN 1 ELSE 0 END) as total_absent, "
                            f"SUM(CASE WHEN da.is_late=1 THEN 1 ELSE 0 END) as total_late, "
                            f"SUM(CASE WHEN da.working_hours > 8 THEN 1 ELSE 0 END) as total_overtime, "
                            f"round(SUM(da.working_hours), 2) as total_hours_worked "
                            f"FROM employees e JOIN daily_attendance da ON e.id = da.employee_id "
                            f"WHERE da.date BETWEEN '{range_start}' AND '{range_end}'"
                        )
                        sql_context_label = f"Attendance summary for {range_label}"
                    else:
                        generated_sql = (
                            f"SELECT "
                            f"SUM(CASE WHEN da.status='Present' THEN 1 ELSE 0 END) as present_count, "
                            f"SUM(CASE WHEN da.status='Absent' THEN 1 ELSE 0 END) as absent_count, "
                            f"SUM(CASE WHEN da.is_late=1 THEN 1 ELSE 0 END) as late_count, "
                            f"SUM(CASE WHEN da.working_hours > 8 THEN 1 ELSE 0 END) as overtime_count, "
                            f"round(SUM(da.working_hours), 2) as total_hours "
                            f"FROM daily_attendance da WHERE da.date = '{target_date}'"
                        )
                        sql_context_label = f"Attendance summary for {target_date}"
                    query_mode = "summary"

                elif "how many" in p_lower and "employee" in p_lower:
                    generated_sql = "SELECT COUNT(*) as total_employees FROM employees WHERE status != 'Deleted'"
                    sql_context_label = "Total active employees"
                    query_mode = "summary"

                else:
                    generated_sql = (
                        f"SELECT e.full_name, da.status, da.is_late, time(da.check_in) as check_in_time "
                        f"FROM employees e JOIN daily_attendance da ON e.id = da.employee_id "
                        f"WHERE da.date = '{target_date}' ORDER BY da.status, e.full_name"
                    )
                    sql_context_label = f"Full attendance for {target_date}"
                    query_mode = "list"

            # --- STEP 4: EXECUTE SQL ---
            sql_results = ""
            if requires_db and generated_sql:
                yield json.dumps({"response": "*(Analyzing database for your query...)*\n\n"}) + "\n"
                try:
                    with open("ai_debug.log", "a") as f:
                        f.write(f"[{datetime.now()}] PROMPT: {prompt}\n")
                        f.write(f"[{datetime.now()}] INTENT: {sql_context_label} | MODE: {query_mode}\n")
                        f.write(f"[{datetime.now()}] SQL: {generated_sql}\n")

                    result = db.execute(text(generated_sql))
                    rows   = result.fetchall()
                    headers = list(result.keys())

                    if rows:
                        text_results = f"[{sql_context_label}: {len(rows)} records]\n"
                        for i, r in enumerate(rows):
                            if "full_name" in headers:
                                name   = r[headers.index("full_name")]
                                extras = ", ".join(
                                    f"{headers[j]}: {r[j]}" for j in range(len(headers))
                                    if headers[j] != "full_name" and r[j] is not None
                                )
                                text_results += f"{i+1}. {name}" + (f" ({extras})" if extras else "") + "\n"
                            else:
                                text_results += f"{i+1}. " + ", ".join(
                                    f"{headers[j]}: {r[j]}" for j in range(len(headers)) if r[j] is not None
                                ) + "\n"
                        sql_results = text_results
                    else:
                        sql_results = f"[{sql_context_label}: 0 records found]"
                        query_mode  = "summary"   # let LLM phrase "no data" naturally

                    with open("ai_debug.log", "a") as f:
                        f.write(f"[{datetime.now()}] RESULTS LENGTH: {len(sql_results)}\n")

                except Exception as e:
                    logger.error(f"DB Error: {e}")
                    sql_results = f"[Database error: {str(e)}]"
                    query_mode  = "summary"
                    with open("ai_debug.log", "a") as f:
                        f.write(f"[{datetime.now()}] DB EXCEPTION: {str(e)}\n")

            # --- STEP 5: RESPOND ---
            # MODE A: list  → Python streams directly, LLM never called (no truncation possible)
            # MODE B: summary → Python fetches data, LLM phrases it naturally
            # MODE C: llm   → General chat, no DB involved

            if query_mode == "list" and sql_results:
                async def stream_list():
                    import asyncio as _asyncio
                    if "0 records found" in sql_results:
                        intro = f"No records found for: **{sql_context_label}**."
                    else:
                        header_line = sql_results.split("\n")[0]  # e.g. "[Absent employees on ...: 41 records]"
                        list_lines  = [l for l in sql_results.split("\n")[1:] if l.strip()]
                        intro = f"Here is the complete list — **{sql_context_label}**:\n\n" + "\n".join(list_lines)
                    chunk_size = 8
                    for i in range(0, len(intro), chunk_size):
                        yield json.dumps({"response": intro[i:i+chunk_size], "done": False}) + "\n"
                        await _asyncio.sleep(0.005)
                    yield json.dumps({"response": "", "done": True}) + "\n"

                async for chunk in stream_list():
                    yield chunk
                return

            elif query_mode == "summary" and sql_results:
                # DB data is real; LLM only handles natural-language phrasing
                system_prompt = (
                    "You are SYNTHBIT AI 1.0, an HR attendance assistant.\n"
                    "Rules:\n"
                    "1. The DATA block below is REAL, accurate database output. Never contradict it.\n"
                    "2. Phrase the data naturally and helpfully as an HR summary.\n"
                    "3. Never mention databases, SQL, or queries.\n"
                    "4. If data shows 0 records, say so politely."
                )
                enriched_prompt = f"DATA:\n{sql_results}\n\nSummarise this for the manager who asked: {prompt}"

            else:
                # Pure conversational — no DB data
                system_prompt = "You are SYNTHBIT AI 1.0, a helpful HR assistant. Answer the user's message conversationally."
                enriched_prompt = prompt
        else:
            system_prompt = "You are an AI that writes complete emails exactly as instructed. You never use placeholders."
            enriched_prompt = prompt

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
                await asyncio.sleep(0.01)
                yield line.decode("utf-8")

        except Exception as e:
            logger.error(f"Error generating response: {e}")
            with open("ai_debug.log", "a") as f:
                f.write(f"[{datetime.now()}] ERROR in generate_response: {str(e)}\n")
            yield json.dumps({"error": str(e), "done": True}) + "\n"


ai_service_instance = AIService()
