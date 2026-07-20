from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.models.config import DeviceConfig, AdminSession
from pydantic import BaseModel
import secrets
from datetime import datetime, timedelta, timezone

router = APIRouter()

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login")
def login(request: LoginRequest, response: Response, db: Session = Depends(get_db)):
    config = db.query(DeviceConfig).first()
    # Initialize config if it doesn't exist
    if not config:
        config = DeviceConfig()
        db.add(config)
        db.commit()
        db.refresh(config)

    if request.username != "admin" or request.password != config.admin_password:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    # Generate session token
    token = secrets.token_hex(32)
    expires = datetime.now(timezone.utc) + timedelta(days=7)

    # Store in DB
    session = AdminSession(session_token=token, expires_at=expires)
    db.add(session)
    db.commit()

    # Set HttpOnly cookie
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        max_age=7 * 24 * 60 * 60,  # 7 days in seconds
        path="/",
        samesite="lax",
        secure=False  # Set to True in production with HTTPS
    )

    return {"message": "Login successful"}

@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get("session_token")
    if token:
        # Remove from DB
        session = db.query(AdminSession).filter(AdminSession.session_token == token).first()
        if session:
            db.delete(session)
            db.commit()
    
    # Clear cookie
    response.delete_cookie("session_token", path="/")
    return {"message": "Logout successful"}

@router.get("/me")
def verify_session(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("session_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    session = db.query(AdminSession).filter(AdminSession.session_token == token).first()
    
    # Check if session exists and is not expired
    if not session or (session.expires_at and session.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc)):
        raise HTTPException(status_code=401, detail="Session expired or invalid")
        
    return {"status": "authenticated"}
