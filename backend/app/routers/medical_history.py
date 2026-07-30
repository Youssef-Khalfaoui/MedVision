"""Router — antécédents médicaux (chronique).

GET/PUT /api/patients/{patient_id}/medical-history
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.dependencies import get_db, get_current_doctor
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.medical_history import PatientMedicalHistory
from app.schemas.medical_history import MedicalHistoryRead, MedicalHistoryUpsert

router = APIRouter(tags=["medical-history"])


async def _ensure_patient(patient_id: str, db: AsyncSession) -> Patient:
    """Vérifie que le patient existe, 404 sinon."""
    result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@router.get("/api/patients/{patient_id}/medical-history")
async def get_medical_history(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    _doctor: Doctor = Depends(get_current_doctor),
):
    """Retourne les antécédents d'un patient.
    Si aucune ligne n'existe encore, retourne un objet par défaut (tout à False)
    plutôt que 404 — indispensable pour pré-remplir le formulaire nouveau patient.
    """
    await _ensure_patient(patient_id, db)
    result = await db.execute(
        select(PatientMedicalHistory).where(PatientMedicalHistory.patient_id == patient_id)
    )
    history = result.scalar_one_or_none()
    if not history:
        return MedicalHistoryRead(patient_id=patient_id)
    return MedicalHistoryRead.model_validate(history)


@router.put("/api/patients/{patient_id}/medical-history")
async def upsert_medical_history(
    patient_id: str,
    body: MedicalHistoryUpsert,
    db: AsyncSession = Depends(get_db),
    doctor: Doctor = Depends(get_current_doctor),
):
    """Crée ou remplace les antécédents d'un patient (upsert)."""
    await _ensure_patient(patient_id, db)

    result = await db.execute(
        select(PatientMedicalHistory).where(PatientMedicalHistory.patient_id == patient_id)
    )
    history = result.scalar_one_or_none()

    if history:
        for field in ("smoking_status", "prior_pneumonia", "tuberculosis_history",
                      "copd", "asthma", "heart_disease", "heart_failure", "diabetes",
                      "hypertension", "previous_operations", "allergies",
                      "current_symptoms", "current_medication", "doctor_notes", "phone"):
            setattr(history, field, getattr(body, field))
        history.updated_by = doctor.id
    else:
        history = PatientMedicalHistory(
            patient_id=patient_id,
            updated_by=doctor.id,
            **body.model_dump(),
        )
        db.add(history)

    await db.flush()
    await db.refresh(history)
    return MedicalHistoryRead.model_validate(history)
