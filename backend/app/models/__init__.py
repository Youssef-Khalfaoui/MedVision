"""Models — import centralisé pour Alembic autogenerate."""
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.medical_history import PatientMedicalHistory, SmokingStatus
from app.models.exam import Exam
from app.models.clinical_context import ExamClinicalContext

__all__ = [
    "Doctor",
    "Patient",
    "PatientMedicalHistory",
    "SmokingStatus",
    "Exam",
    "ExamClinicalContext",
]
