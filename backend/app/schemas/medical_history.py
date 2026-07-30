"""Schemas pour PatientMedicalHistory."""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.medical_history import SmokingStatus


class MedicalHistoryRead(BaseModel):
    patient_id: str
    smoking_status: Optional[SmokingStatus] = None
    prior_pneumonia: bool = False
    tuberculosis_history: bool = False
    copd: bool = False
    asthma: bool = False
    heart_disease: bool = False
    heart_failure: bool = False
    diabetes: bool = False
    hypertension: bool = False
    previous_operations: bool = False
    allergies: bool = False
    current_symptoms: bool = False
    current_medication: bool = False
    doctor_notes: Optional[str] = None
    phone: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[int] = None

    model_config = {"from_attributes": True}


class MedicalHistoryUpsert(BaseModel):
    smoking_status: Optional[SmokingStatus] = None
    prior_pneumonia: bool = False
    tuberculosis_history: bool = False
    copd: bool = False
    asthma: bool = False
    heart_disease: bool = False
    heart_failure: bool = False
    diabetes: bool = False
    hypertension: bool = False
    previous_operations: bool = False
    allergies: bool = False
    current_symptoms: bool = False
    current_medication: bool = False
    doctor_notes: Optional[str] = None
    phone: Optional[str] = None


class MedicalHistoryUpdate(BaseModel):
    """Partiel — seuls les champs fournis sont mis à jour."""
    smoking_status: Optional[SmokingStatus] = None
    prior_pneumonia: Optional[bool] = None
    tuberculosis_history: Optional[bool] = None
    copd: Optional[bool] = None
    asthma: Optional[bool] = None
    heart_disease: Optional[bool] = None
    diabetes: Optional[bool] = None
    hypertension: Optional[bool] = None
