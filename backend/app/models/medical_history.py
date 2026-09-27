"""PatientMedicalHistory — antécédents médicaux chroniques.

⚠️ UNE SEULE LIGNE COURANTE par patient (unique sur patient_id).
Toute mise à jour écrase la ligne existante — jamais d'historique de versions ici.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Integer, String, Boolean, DateTime, ForeignKey, Enum as SAEnum, Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
import enum


class SmokingStatus(str, enum.Enum):
    never = "never"
    former = "former"
    current = "current"


class PatientMedicalHistory(Base):
    __tablename__ = "patient_medical_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("patients.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    smoking_status: Mapped[SmokingStatus | None] = mapped_column(
        SAEnum(SmokingStatus, name="smoking_status_enum", create_constraint=True),
        nullable=True,
    )
    prior_pneumonia: Mapped[bool] = mapped_column(Boolean, default=False)
    tuberculosis_history: Mapped[bool] = mapped_column(Boolean, default=False)
    copd: Mapped[bool] = mapped_column(Boolean, default=False)
    asthma: Mapped[bool] = mapped_column(Boolean, default=False)
    heart_disease: Mapped[bool] = mapped_column(Boolean, default=False)
    heart_failure: Mapped[bool] = mapped_column(Boolean, default=False)
    diabetes: Mapped[bool] = mapped_column(Boolean, default=False)
    hypertension: Mapped[bool] = mapped_column(Boolean, default=False)
    previous_operations: Mapped[bool] = mapped_column(Boolean, default=False)
    allergies: Mapped[bool] = mapped_column(Boolean, default=False)
    current_symptoms: Mapped[bool] = mapped_column(Boolean, default=False)
    current_medication: Mapped[bool] = mapped_column(Boolean, default=False)
    doctor_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    updated_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("doctors.id", ondelete="SET NULL"), nullable=True
    )

    patient = relationship("Patient", back_populates="medical_history")
    updater = relationship("Doctor", foreign_keys=[updated_by])
