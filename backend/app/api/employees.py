from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database.database import get_db
from app.models.employee import Employee as EmployeeModel
from app.schemas.employee import Employee, EmployeeCreate, EmployeeUpdate

from app.integrations.pctl_mock import PCTLMockAttendanceProvider

router = APIRouter(prefix="/employees", tags=["Employees"])

@router.get("", response_model=List[Employee])
def get_employees(db: Session = Depends(get_db)):
    """
    Retrieve a list of all active employees.
    """
    return db.query(EmployeeModel).filter(EmployeeModel.status != "Deleted").all()

@router.post("", response_model=Employee)
def create_employee(employee: EmployeeCreate, db: Session = Depends(get_db)):
    db_emp = db.query(EmployeeModel).filter(EmployeeModel.machine_user_id == employee.machine_user_id).first()
    if db_emp:
        raise HTTPException(status_code=400, detail="Machine user ID already registered")
    
    new_emp = EmployeeModel(**employee.model_dump())
    new_emp.is_synced = 0
    db.add(new_emp)
    
    # Try to push to machine right away if possible
    provider = PCTLMockAttendanceProvider(db)
    try:
        provider.add_employee(machine_user_id=new_emp.machine_user_id, full_name=new_emp.full_name)
        new_emp.is_synced = 1
    except ConnectionError:
        print("Device offline. Employee saved locally and queued for sync.")
        
    db.commit()
    db.refresh(new_emp)
    return new_emp

@router.put("/{emp_id}", response_model=Employee)
def update_employee(emp_id: int, employee: EmployeeUpdate, db: Session = Depends(get_db)):
    db_emp = db.query(EmployeeModel).filter(EmployeeModel.id == emp_id).first()
    if not db_emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    for key, value in employee.model_dump().items():
        setattr(db_emp, key, value)
    
    db_emp.is_synced = 0
    
    # Try to push update to machine
    provider = PCTLMockAttendanceProvider(db)
    try:
        provider.update_employee(machine_user_id=db_emp.machine_user_id, full_name=db_emp.full_name)
        db_emp.is_synced = 1
    except ConnectionError:
        print("Device offline. Employee update queued for sync.")
    
    db.commit()
    db.refresh(db_emp)
    return db_emp

@router.delete("/{emp_id}")
def delete_employee(emp_id: int, db: Session = Depends(get_db)):
    db_emp = db.query(EmployeeModel).filter(EmployeeModel.id == emp_id).first()
    if not db_emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Mark as deleted and unsynced so device.py will pick it up and push deleteuser
    db_emp.status = "Deleted"
    db_emp.is_synced = 0
    db.commit()
    return {"message": "Employee queued for deletion from device"}
