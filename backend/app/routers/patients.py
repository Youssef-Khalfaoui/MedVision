"""Patients CRUD router."""

import os
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.dependencies import get_db, get_current_doctor
from app.models.patient import Patient
from app.models.doctor import Doctor
from app.schemas.patient import (
    PatientCreate, PatientUpdate, PatientResponse, PatientListResponse
)

router = APIRouter(prefix="/api/patients", tags=["patients"])


@router.get("", response_model=List[PatientListResponse])
async def list_patients(
    name: str = "",
    patient_id: str = "",
    age: int | None = None,
    db: AsyncSession = Depends(get_db),
    doctor: Doctor = Depends(get_current_doctor),
):
    """List patients, filtered independently by name, ID, and/or age (AND logic)."""
    query = select(Patient)

    if name:
        query = query.where(Patient.full_name.ilike(f"%{name}%"))

    if patient_id:
        query = query.where(Patient.id.ilike(f"%{patient_id}%"))

    if age is not None:
        today = date.today()
        start = date(today.year - age - 1, today.month, today.day) + timedelta(days=1)
        end = date(today.year - age, today.month, today.day)
        query = query.where(Patient.date_of_birth.between(start, end))

    query = query.order_by(Patient.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    doctor: Doctor = Depends(get_current_doctor),
):
    """Get a single patient by ID."""
    result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@router.post("", response_model=PatientResponse, status_code=201)
async def create_patient(
    body: PatientCreate,
    db: AsyncSession = Depends(get_db),
    doctor: Doctor = Depends(get_current_doctor),
):
    """Create a new patient."""
    result = await db.execute(select(Patient).where(Patient.id == body.id))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Patient ID already exists",
        )

    ALLOWED_SEX = {"M", "F", "other"}
    sex = None
    if body.sex:
        if body.sex not in ALLOWED_SEX:
            raise HTTPException(
                status_code=422, detail=f"Invalid sex '{body.sex}'. Use M, F, or other"
            )
        sex = body.sex

    patient = Patient(
        id=body.id,
        full_name=body.full_name,
        date_of_birth=body.date_of_birth,
        sex=sex,
        created_by=doctor.id,
    )
    db.add(patient)
    await db.flush()
    return patient


@router.put("/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: str,
    body: PatientUpdate,
    db: AsyncSession = Depends(get_db),
    doctor: Doctor = Depends(get_current_doctor),
):
    """Update patient details."""
    result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    if body.full_name is not None:
        patient.full_name = body.full_name
    if body.date_of_birth is not None:
        patient.date_of_birth = body.date_of_birth
    if body.sex is not None:
        ALLOWED_SEX = {"M", "F", "other"}
        if body.sex not in ALLOWED_SEX:
            raise HTTPException(
                status_code=422, detail=f"Invalid sex '{body.sex}'"
            )
        patient.sex = body.sex

    await db.flush()
    return patient


@router.delete("/{patient_id}")
async def delete_patient(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    doctor: Doctor = Depends(get_current_doctor),
):
    """Supprime un patient et tout son dossier (examens + antécédents en cascade).

    Supprime aussi les fichiers persistés (images radio, Grad-CAM, PDFs)
    associés à chaque examen. Action irréversible.
    """
    from app.models.exam import Exam
    from app.models.medical_history import PatientMedicalHistory
    from app.storage import UPLOAD_DIR, PDF_DIR

    result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    ex_res = await db.execute(select(Exam).where(Exam.patient_id == patient_id))
    exams = ex_res.scalars().all()
    deleted_files = 0
    for e in exams:
        for p in (
            e.image_path,
            e.gradcam_path,
            e.pdf_clinical_path,
            e.pdf_patient_path,
        ):
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                    deleted_files += 1
                except OSError:
                    pass
        import glob
        for pattern in (
            str(UPLOAD_DIR / f"{e.id}.*"),
            str(PDF_DIR / f"{e.id}_report_*.pdf"),
        ):
            for f in glob.glob(pattern):
                try:
                    os.remove(f)
                    deleted_files += 1
                except OSError:
                    pass

    exam_count = len(exams)

    await db.delete(patient)
    await db.commit()

    return {
        "deleted": True,
        "patient_id": patient_id,
        "exams_deleted": exam_count,
        "files_deleted": deleted_files,
    }


@router.get("/{patient_id}/exists")
async def check_patient_exists(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    doctor: Doctor = Depends(get_current_doctor),
):
    """Check if a patient ID exists (for the double-confirm flow)."""
    result = await db.execute(select(Patient).where(Patient.id == patient_id))
    return {"exists": result.scalar_one_or_none() is not None}


@router.get("/{patient_id}/exams")
async def list_patient_exams(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    doctor: Doctor = Depends(get_current_doctor),
):
    """List all exams for a patient (history tab). Read-only."""
    from app.models.exam import Exam
    result = await db.execute(
        select(Exam)
        .where(Exam.patient_id == patient_id)
        .order_by(Exam.exam_date.asc())
    )
    exams = result.scalars().all()
    return [
        {
            "id": e.id,
            "patient_id": e.patient_id,
            "exam_date": e.exam_date.isoformat() if e.exam_date else None,
            "status": e.status,
            "examen_number": e.examen_number,
            "structured_findings": e.structured_findings,
            "report_text_clinical": e.report_text_clinical,
            "validation_result_clinical": e.validation_result_clinical,
        }
        for e in exams
    ]
