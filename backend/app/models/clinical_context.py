"""ExamClinicalContext — contexte clinique ponctuel au moment de l'examen.

⚠️ UNE SEULE LIGNE par examen (unique sur exam_id).
Ne JAMAIS fusionner avec patient_medical_history (chronique).
"""

from datetime import datetime, timezone
from sqlalchemy import Integer, String, Boolean, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class ExamClinicalContext(Base):
    __tablename__ = "exam_clinical_context"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exam_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("exams.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    fever: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    cough: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    chest_pain: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    shortness_of_breath: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    oxygen_saturation: Mapped[float | None] = mapped_column(Numeric(4, 1), nullable=True)
    body_temperature: Mapped[float | None] = mapped_column(Numeric(3, 1), nullable=True)
    recorded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    exam = relationship("Exam", back_populates="clinical_context")
