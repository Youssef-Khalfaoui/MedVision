"""Patient model — identité patient.

⚠️ Stocke uniquement l'identité. Les antécédents médicaux (chronique)
et le contexte clinique (ponctuel) sont dans des tables séparées.
"""

from datetime import datetime, date
from sqlalchemy import String, DateTime, Date, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=True)
    sex: Mapped[str] = mapped_column(String(10), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    created_by: Mapped[int] = mapped_column(
        ForeignKey("doctors.id"), nullable=False
    )

    creator = relationship("Doctor", foreign_keys=[created_by])
    medical_history = relationship(
        "PatientMedicalHistory", back_populates="patient", uselist=False, cascade="all, delete-orphan"
    )
    exams = relationship("Exam", back_populates="patient", cascade="all, delete-orphan")
