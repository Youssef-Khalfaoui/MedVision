"""Router — contexte clinique ponctuel (examen).

POST /api/exams/{exam_id}/clinical-context
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.dependencies import get_db, get_current_doctor
from app.models.doctor import Doctor
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
    _doctor: Doctor = Depends(get_current_doctor),
):
    """Crée (ou met à jour) le contexte clinique d'un examen.

    ⚠️ Authentification obligatoire : ces données (SpO2, température, symptômes)
    sont des données de santé ; elles étaient auparavant lisibles et modifiables
    par quiconque connaissait un exam_id.
    """
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


@router.put("/api/exams/{exam_id}/clinical-context", status_code=200)
async def upsert_clinical_context(
    exam_id: int,
    body: ClinicalContextUpsert,
    db: AsyncSession = Depends(get_db),
    _doctor: Doctor = Depends(get_current_doctor),
):
    """Met à jour (ou crée) le contexte clinique d'un examen (upsert).

    Endpoint ajouté : le POST renvoyait 409 en invitant à utiliser un PUT qui
    n'existait pas, laissant la mise à jour impossible.
    """
    await _ensure_exam(exam_id, db)

    result = await db.execute(
        select(ExamClinicalContext).where(ExamClinicalContext.exam_id == exam_id)
    )
    ctx = result.scalar_one_or_none()

    if ctx:
        for field, value in body.model_dump(exclude_none=True).items():
            setattr(ctx, field, value)
    else:
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
    _doctor: Doctor = Depends(get_current_doctor),
):
    """Retourne le contexte clinique d'un examen (données de santé protégées)."""
    await _ensure_exam(exam_id, db)
    result = await db.execute(
        select(ExamClinicalContext).where(ExamClinicalContext.exam_id == exam_id)
    )
    ctx = result.scalar_one_or_none()
    if not ctx:
        raise HTTPException(status_code=404, detail="Clinical context not found")
    return ClinicalContextRead.model_validate(ctx)



