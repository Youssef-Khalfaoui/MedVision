"""Router — contexte clinique ponctuel (examen).

POST /api/exams/{exam_id}/clinical-context
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.dependencies import get_db
from app.models.exam import Exam
from app.models.clinical_context import ExamClinicalContext
from app.schemas.exam import ClinicalContextUpsert, ClinicalContextRead

router = APIRouter(tags=["clinical-context"])


async def _ensure_exam(exam_id: int, db: AsyncSession) -> Exam:
    result = await db.execute(select(Exam).where(Exam.id == exam_id))
    exam = result.scalar_one_or_none()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    return exam


@router.post("/api/exams/{exam_id}/clinical-context", status_code=201)
async def create_clinical_context(
    exam_id: int,
    body: ClinicalContextUpsert,
    db: AsyncSession = Depends(get_db),
):
    """Crée (ou met à jour) le contexte clinique d'un examen."""
    await _ensure_exam(exam_id, db)

    result = await db.execute(
        select(ExamClinicalContext).where(ExamClinicalContext.exam_id == exam_id)
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Clinical context already exists for this exam. Use PUT to update.",
        )

    ctx = ExamClinicalContext(
        exam_id=exam_id,
        **body.model_dump(exclude_none=True),
    )
    db.add(ctx)
    await db.flush()
    await db.refresh(ctx)
    return ClinicalContextRead.model_validate(ctx)


@router.get("/api/exams/{exam_id}/clinical-context")
async def get_clinical_context(
    exam_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Retourne le contexte clinique d'un examen."""
    await _ensure_exam(exam_id, db)
    result = await db.execute(
        select(ExamClinicalContext).where(ExamClinicalContext.exam_id == exam_id)
    )
    ctx = result.scalar_one_or_none()
    if not ctx:
        raise HTTPException(status_code=404, detail="Clinical context not found")
    return ClinicalContextRead.model_validate(ctx)


