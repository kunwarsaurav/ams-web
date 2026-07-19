# Attendance Management System (MVP)

This project is a minimum viable product (MVP) for an Attendance Management System designed to integrate seamlessly with PCTL biometric attendance machines.

## Architecture

- **Backend**: FastAPI, SQLAlchemy, SQLite
- **Frontend**: React, Vite, Axios, React Router
- **Integration**: Pluggable provider system (mocked for now)

## Prerequisites

- Node.js (for frontend)
- Python 3.9+ (for backend)

## Setup and Running

### 1. Backend Setup

Open a terminal and navigate to the backend directory:
```bash
cd backend
python -m venv venv
# Windows
.\venv\Scripts\Activate.ps1
# Mac/Linux
source venv/bin/activate

# Install dependencies
pip install fastapi[all] sqlalchemy uvicorn python-dateutil pandas openpyxl

# Seed the database
python seed.py

# Run the backend server
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```
The backend will run on `http://localhost:8080`

### 2. Frontend Setup

Open a new terminal and navigate to the frontend directory:
```bash
cd frontend
npm install
npm run dev
```
The frontend will run on the URL displayed in your terminal (usually `http://localhost:5173`).

## Hardware Integration Guide

The current MVP uses a `PCTLMockAttendanceProvider` to simulate a PCTL device. To integrate real hardware:

1. Navigate to `backend/app/integrations/`.
2. Create a new provider (e.g., `real_pctl_provider.py`) that inherits from `AttendanceProvider`.
3. Implement the `fetch_logs()` method to communicate with the real PCTL machine via its SDK, TCP/IP, or REST API.
4. Update `backend/app/api/attendance.py` to use your new provider instead of the mock one.
