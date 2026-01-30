from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List

from main import get_current_user, User

router = APIRouter(prefix="/patients", tags=["patients"])

class Patient(BaseModel):
    id: int | None = None  # id اختیاری می‌شه - سرور تولید می‌کنه
    name: str
    national_id: str
    history: dict = {}  # پرونده الکترونیک ساده

fake_patients_db = []  # لیست موقت (بعداً DB واقعی)

@router.post("/", response_model=Patient)
async def create_patient(patient: Patient, current_user: User = Depends(get_current_user)):
    if current_user.role not in ["dentist", "assistant"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    patient.id = len(fake_patients_db) + 1  # سرور id تولید می‌کنه
    fake_patients_db.append(patient)
    return patient

@router.get("/", response_model=List[Patient])
async def get_patients(current_user: User = Depends(get_current_user)):
    if current_user.role != "dentist":
        raise HTTPException(status_code=403, detail="Permission denied")
    return fake_patients_db

@router.get("/{patient_id}", response_model=Patient)
async def get_patient(patient_id: int, current_user: User = Depends(get_current_user)):
    if current_user.role not in ["dentist", "assistant"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    for patient in fake_patients_db:
        if patient.id == patient_id:
            return patient
    raise HTTPException(status_code=404, detail="Patient not found")