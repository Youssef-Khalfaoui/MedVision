"""Exam — examen radiographique.

Stocke le résultat complet d'une analyse radiologique :
  - structured_findings (sortie Agent 1)
  - comparison_result (sortie Agent 1.5)
  - report_texts (sortie Agent 2)
  - validation_result (sortie Agent 3)

Colonnes JSON en sqlalchemy.JSON générique (pas JSONB) pour compatibilité
SQLite dev / PostgreSQL prod.
Minimal pour Round 2 (FK target pour exam_clinical_context) ; étendu en Round 4.
"""

from datetime import datetime, timezone
from sqlalchemy import Integer, String, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

EXAM_STATUS_PENDING = "PENDING"
EXAM_STATUS_CLASSIFYING = "CLASSIFYING"
EXAM_STATUS_COMPARING = "COMPARING"
EXAM_STATUS_GENERATING = "GENERATING"
EXAM_STATUS_VALIDATING = "VALIDATING"
EXAM_STATUS_DONE = "DONE"
EXAM_STATUS_FAILED = "FAILED"

EXAM_STATUS_TRANSITIONS = {
    EXAM_STATUS_PENDING: EXAM_STATUS_CLASSIFYING,
    EXAM_STATUS_CLASSIFYING: EXAM_STATUS_COMPARING,
    EXAM_STATUS_COMPARING: EXAM_STATUS_GENERATING,
    EXAM_STATUS_GENERATING: EXAM_STATUS_VALIDATING,
    EXAM_STATUS_VALIDATING: EXAM_STATUS_DONE,
}


class Exam(Base):
    __tablename__ = "exams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False
    )
    exam_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    image_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    structured_findings: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    gradcam_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    comparison_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    report_text_clinical: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_text_patient: Mapped[str | None] = mapped_column(Text, nullable=True)
    pdf_clinical_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    pdf_patient_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    validation_result_clinical: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=EXAM_STATUS_PENDING
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    performed_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("doctors.id", ondelete="SET NULL"), nullable=True
    )
    examen_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    patient = relationship("Patient", back_populates="exams")
    performer = relationship("Doctor", foreign_keys=[performed_by])
    clinical_context = relationship(
        "ExamClinicalContext", back_populates="exam", uselist=False, cascade="all, delete-orphan"
    )
