from fastapi import APIRouter, Request, Depends, Response
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy.orm import Session
from datetime import datetime
import json
import subprocess
import platform

from app.database.database import get_db
from app.models.employee import Employee
from app.models.attendance import AttendanceLog
from app.models.config import DeviceConfig
from app.services.attendance_processor import AttendanceProcessor
from app.websocket_manager import manager

router = APIRouter(tags=["Device"])

@router.get("/device/settings")
def get_device_settings(db: Session = Depends(get_db)):
    config = db.query(DeviceConfig).first()
    if not config:
        config = DeviceConfig(ip_address="10.10.10.10")
        db.add(config)
        db.commit()
    return {"ip_address": config.ip_address}

@router.post("/device/settings")
async def update_device_settings(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    new_ip = data.get("ip_address")
    if not new_ip:
        return JSONResponse(status_code=400, content={"message": "ip_address is required"})
    
    config = db.query(DeviceConfig).first()
    if not config:
        config = DeviceConfig(ip_address=new_ip)
        db.add(config)
    else:
        config.ip_address = new_ip
    db.commit()
    return {"message": "Device settings updated", "ip_address": new_ip}

@router.get("/device/ping")
def ping_device(db: Session = Depends(get_db)):
    config = db.query(DeviceConfig).first()
    ip_to_ping = config.ip_address if config else "10.10.10.10"
    
    # Check if this is the mock IP or local address to bypass actual ping subprocess
    if ip_to_ping in ["10.10.10.10", "127.0.0.1", "localhost"] or "mock" in ip_to_ping.lower():
        return {"status": "active", "message": f"Device at {ip_to_ping} (Mock Mode) is synced and active."}
        
    # Ping the device to see if it is active on the network
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    command = ['ping', param, '1', ip_to_ping]
    
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=2)
        if result.returncode == 0:
            return {"status": "active", "message": f"Device at {ip_to_ping} is synced and active."}
        else:
            return {"status": "inactive", "message": f"Device at {ip_to_ping} is unreachable."}
    except Exception:
        return {"status": "inactive", "message": "Ping command failed."}

@router.post("/ISAPI/AccessControl/AcsEvent")
async def ignore_hikvision_webhook():
    # Silently ignore Hikvision protocol requests to stop 404 spam in terminal
    return JSONResponse(status_code=200, content={"status": "ignored"})

@router.post("/")
async def handle_device_webhook(request: Request, db: Session = Depends(get_db)):
    body = await request.body()
    try:
        data = json.loads(body.decode("utf-8"))
    except:
        data = {}
        
    # Extract headers or body manually
    request_code = request.headers.get("request_code") or data.get("request_code")
    dev_id = request.headers.get("dev_id") or data.get("dev_id")
    trans_id = request.headers.get("trans_id") or data.get("trans_id")
    
    print("=" * 50)
    print(f"WEBHOOK RECEIVED FROM DEVICE: {dev_id}")
    print(f"Event Type: {request_code}")
    print(f"Query Params: {request.query_params}")
    print(f"Request Headers: {dict(request.headers)}")
    print(f"Raw Bytes Body: {repr(body)}")
    
    try:
        text_body = body.decode('utf-8', errors='ignore')
        
        # Log to file for debugging
        with open("webhook_debug.log", "a", encoding="utf-8") as f:
            f.write(f"\n--- NEW WEBHOOK ---\nEvent: {request_code}\nBody: {text_body}\n")
            
        
        # Robust JSON extraction (these devices often pad with binary data before/after the JSON)
        start_idx = text_body.find('{"')
        if start_idx == -1:
            start_idx = text_body.find('{')
            
        if start_idx != -1:
            # The device sends JSON on a single line, often followed by binary fingerprint data
            # which can contain random '}' characters. We extract just the line with the JSON.
            lines = text_body[start_idx:].split('\n')
            json_str = lines[0].strip()
            
            # Fallback if it somehow didn't grab the whole JSON
            if not json_str.endswith('}'):
                end_idx = text_body.rfind('}')
                json_str = text_body[start_idx:end_idx+1]
                
            # If there's STILL extra binary data appended to the string, json.loads will fail.
            # We can strip any trailing characters after the last '}' in the selected json_str
            last_brace = json_str.rfind('}')
            if last_brace != -1:
                json_str = json_str[:last_brace+1]
                
            print(f"Extracted JSON String: {repr(json_str)}")
            try:
                data = json.loads(json_str)
            except Exception as e:
                print(f"JSON Parse Error: {e}. String was: {repr(json_str)}")
                data = {}
            
            # If it's a punch/log event
            if request_code == "realtime_glog":
                user_id = data.get("user_id")
                io_time_str = data.get("io_time") # Format: 20260707131855
                
                if user_id and io_time_str:
                    # Parse timestamp
                    timestamp = datetime.strptime(io_time_str, "%Y%m%d%H%M%S")
                    
                    formatted_device_time = timestamp.strftime("%Y-%m-%d %I:%M:%S %p")
                    current_server_time = datetime.now().strftime("%I:%M:%S %p")

                    # Removed duplicate check for testing purposes
                    print(f"[{current_server_time}] [SUCCESS] Real-Time Punch: User {user_id} (Device Time: {formatted_device_time})")
                    # Save raw log
                    new_log = AttendanceLog(
                        machine_user_id=str(user_id),
                        timestamp=timestamp,
                        punch_type=data.get("verify_mode", "0"),
                        machine_id=dev_id or "PCTL-Unknown"
                    )
                    db.add(new_log)
                    db.commit()
                    
                    # Trigger processor for today
                    processor = AttendanceProcessor(db)
                    processor.process_daily_attendance(timestamp.date())
                    
                    # Find employee name to include in broadcast
                    emp = db.query(Employee).filter(Employee.machine_user_id == str(user_id)).first()
                    emp_name = emp.full_name if emp else f"Unknown ({user_id})"
                    
                    await manager.broadcast({
                        "type": "NEW_PUNCH",
                        "data": {
                            "user_id": user_id,
                            "employee_name": emp_name,
                            "timestamp": formatted_device_time
                        }
                    })
                    await manager.broadcast({
                        "type": "NEW_EMPLOYEE",
                        "data": {}
                    })
            elif request_code == "realtime_enroll_data":
                user_id = data.get("user_id")
                user_name = data.get("user_name", f"Unknown User ({user_id})")
                
                if user_id:
                    # Auto-create or update employee from the device
                    existing_emp = db.query(Employee).filter(Employee.machine_user_id == str(user_id)).first()
                    if not existing_emp:
                        new_emp = Employee(
                            machine_user_id=str(user_id),
                            full_name=user_name,
                            department="Auto-Generated",
                            designation="Unknown",
                            status="Active",
                            is_synced=1
                        )
                        db.add(new_emp)
                        db.commit()
                        db.refresh(new_emp)
                        current_server_time = datetime.now().strftime("%I:%M:%S %p")
                        print(f"[{current_server_time}] [SUCCESS] New employee downloaded from device: {user_name} (ID: {user_id})")
                        
                        await manager.broadcast({
                            "type": "NEW_EMPLOYEE",
                            "data": {
                                "id": new_emp.id,
                                "machine_user_id": new_emp.machine_user_id,
                                "full_name": new_emp.full_name,
                                "department": new_emp.department
                            }
                        })
                    else:
                        # Update the name if it was previously Unknown/Fetching, OR if it was deleted
                        updated = False
                        if existing_emp.status == "Deleted":
                            existing_emp.status = "Active"
                            existing_emp.full_name = user_name
                            updated = True
                        else:
                            is_placeholder = any(x in existing_emp.full_name for x in ["Unknown", "Fetching", "Waiting"])
                            if is_placeholder and "Unknown" not in user_name:
                                existing_emp.full_name = user_name
                                updated = True
                                
                        if updated:
                            db.commit()
                            db.refresh(existing_emp)
                            current_server_time = datetime.now().strftime("%I:%M:%S %p")
                            print(f"[{current_server_time}] [UPDATED] Employee restored/updated to: {existing_emp.full_name} (ID: {user_id})")
                            
                            # If it was deleted, broadcast as NEW_EMPLOYEE so the UI adds it to the list
                            # Otherwise broadcast as EMPLOYEE_UPDATED
                            if existing_emp.status == "Active" and updated:
                                await manager.broadcast({
                                    "type": "NEW_EMPLOYEE",
                                    "data": {
                                        "id": existing_emp.id,
                                        "machine_user_id": existing_emp.machine_user_id,
                                        "full_name": existing_emp.full_name,
                                        "department": existing_emp.department
                                    }
                                })
                        else:
                            current_server_time = datetime.now().strftime("%I:%M:%S %p")
                            print(f"[{current_server_time}] Employee already exists: {existing_emp.full_name} (ID: {user_id})")
            else:
                # Other events like receive_cmd
                current_server_time = datetime.now().strftime("%I:%M:%S %p")
                print(f"[{current_server_time}] Data parsed successfully for event: {request_code}")
                
                if request_code == "receive_cmd":
                    # 1. Check for pending deletions first
                    deleted_emp = db.query(Employee).filter(Employee.is_synced == 0, Employee.status == "Deleted").first()
                    if deleted_emp:
                        print(f"Sending delete command for Employee {deleted_emp.full_name} to device...")
                        cmd_data = {
                            "ReturnCode": "0",
                            "cloud_command": [
                                {
                                    "cmd": "deleteuser",
                                    "enroll_number": str(deleted_emp.machine_user_id)
                                }
                            ]
                        }
                        if trans_id:
                            cmd_data["trans_id"] = trans_id
                        
                        # Do NOT physically delete from DB! 
                        # If the device ignores the delete and the user punches again, 
                        # we don't want to auto-create a new "Fetching..." profile.
                        # Instead, just mark the deletion as synced.
                        deleted_emp.is_synced = 1
                        db.commit()
                        return PlainTextResponse(content=json.dumps(cmd_data))

                    # 2. Check for unsynced new/updated employees
                    unsynced_emp = db.query(Employee).filter(Employee.is_synced == 0, Employee.status != "Deleted").first()
                    if unsynced_emp:
                        print(f"Pushing Employee {unsynced_emp.full_name} to device...")
                        cmd_data = {
                            "ReturnCode": "0",
                            "cloud_command": [
                                {
                                    "cmd": "setuserinfo",
                                    "enroll_number": str(unsynced_emp.machine_user_id),
                                    "name": unsynced_emp.full_name,
                                    "backup_number": 0,
                                    "user_privilege": 0
                                }
                            ]
                        }
                        if trans_id:
                            cmd_data["trans_id"] = trans_id
                        unsynced_emp.is_synced = 1
                        db.commit()
                        return PlainTextResponse(content=json.dumps(cmd_data))
                    
                    # Next, check if we need to fetch any unknown user's name
                    unknown_emp = db.query(Employee).filter(Employee.full_name.like('Fetching...%')).first()
                    if unknown_emp:
                        print(f"Requesting real name for User ID {unknown_emp.machine_user_id} from device...")
                        cmd_data = {
                            "ReturnCode": "0",
                            "cloud_command": [
                                {
                                    "cmd": "getuserinfo",
                                    "enroll_number": str(unknown_emp.machine_user_id)
                                }
                            ]
                        }
                        # Change to waiting so we don't spam the device in an infinite loop
                        unknown_emp.full_name = f"Waiting... ({unknown_emp.machine_user_id})"
                        db.commit()
                        return PlainTextResponse(content=json.dumps(cmd_data))
                
    except Exception as e:
        print(f"Error processing webhook: {e}")
        
    print("=" * 50)
    
    # Send acknowledgment
    # Realtime Biometrics Push API expects plain text result=OK and Connection: close header for logs/enrolls
    # Content-Type must be strictly "text/plain" without "charset=utf-8" for legacy firmware compatibility.
    if request_code in ["realtime_glog", "realtime_enroll_data"]:
        headers = {
            "Content-Type": "text/plain",
            "Connection": "close",
            "response_code": "OK"
        }
        if trans_id:
            headers["trans_id"] = trans_id
        return Response(content="result=OK", headers=headers)
        
    resp = {"ReturnCode": "0"}
    if trans_id:
        resp["trans_id"] = trans_id
        
    return Response(content=json.dumps(resp), headers={"Content-Type": "application/json", "Connection": "close"})
