"""
Router pour les examens — Round 4.

Endpoints :
  - POST /api/exams        upload + enqueue pipeline (Issue A)
  - GET  /api/exams/{id}   résultat complet (Issue E)
  - WS   /api/exams/{id}/progress  suivi temps réel (Issue D)
"""

import asyncio
import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select

from app.config import get_settings

settings = get_settings()
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import get_current_doctor, get_doctor_from_ws_token, get_doctor_from_query_or_header
from app.models.doctor import Doctor
from app.models.exam import (
    Exam,
    EXAM_STATUS_DONE,
    EXAM_STATUS_FAILED,
    EXAM_STATUS_PENDING,
)
from app.storage import save_image

logger = logging.getLogger("router.exams")
router = APIRouter(prefix="/api/exams", tags=["exams"])



@router.post("", status_code=201)
async def upload_exam(
    patient_id: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_session),
    _doctor: Doctor = Depends(get_current_doctor),
):
    """Upload une image radio, crée l'examen en PENDING, enqueue le pipeline.

    Corps multipart :
      - patient_id: str (obligatoire)
      - file: image (PNG/JPEG)

    Retour : {exam_id, status: "PENDING"} immédiatement.
    Le pipeline s'exécute en arrière-plan via RQ.
    """
    if file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(400, detail="Le fichier doit être une image")

    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(400, detail="Fichier vide")
    if len(contents) > 50 * 1024 * 1024:
        raise HTTPException(413, detail="Fichier trop volumineux (max 50MB)")

    ext = ".png"
    if file.filename:
        _, ext = os.path.splitext(file.filename)
        ext = ext.lower()
        if ext not in (".png", ".jpg", ".jpeg"):
            ext = ".png"

    image_hash = hashlib.sha256(contents).hexdigest()
    from sqlalchemy import func, select as _select
    cur_max = await db.execute(
        _select(func.coalesce(func.max(Exam.examen_number), 0)).where(Exam.patient_id == patient_id)
    )
    next_num = (cur_max.scalar() or 0) + 1
    exam = Exam(
        patient_id=patient_id,
        exam_date=datetime.now(timezone.utc),
        status=EXAM_STATUS_PENDING,
        performed_by=_doctor.id,
        image_hash=image_hash,
        examen_number=next_num,
    )
    db.add(exam)
    await db.flush()
    exam_id = exam.id

    image_path = save_image(exam_id, contents, ext)
    exam.image_path = image_path
    await db.commit()

    enqueue_pipeline(exam_id)

    return {"exam_id": exam_id, "examen_number": next_num, "status": EXAM_STATUS_PENDING}


@router.get("/check-duplicate")
async def check_duplicate(
    image_hash: str,
    patient_id: Optional[str] = None,
    db: AsyncSession = Depends(get_session),
    _doctor: Doctor = Depends(get_current_doctor),
):
    """Vérifie si une image identique a déjà été analysée.

    Recherche un examen dont le hash SHA-256 de l'image correspond.
    Renvoie {duplicate: true, exam_id, patient_id (ref dossier)} si trouvé,
    sinon {duplicate: false}.

    Sécurité : limite aux examens du même docteur (FK performed_by) pour ne
    pas fuiter les dossiers d'autres praticiens.
    """
    query = select(Exam).where(Exam.image_hash == image_hash)
    if patient_id:
        query = query.where(Exam.patient_id == patient_id)
    query = query.order_by(Exam.created_at.asc())
    result = await db.execute(query)
    existing = result.scalars().first()
    if existing is None:
        return {"duplicate": False}
    return {
        "duplicate": True,
        "exam_id": existing.id,
        "examen_number": existing.examen_number,
        "patient_id": existing.patient_id,
        "status": existing.status,
    }


def _redis_conn():
    """Connexion Redis (compat Redis 3.x ancien : force RESP2 car le serveur
    ne supporte pas la commande HELLO de RESP3 introduite par redis-py 8.x).
    socket_timeout=None pour permettre le BRPOP bloquant (timeout=0) sans
    que redis-py ne lève 'Timeout reading from socket'."""
    from redis import Redis
    return Redis(host=settings.redis_host, port=settings.redis_port, db=0, protocol=2,
                 socket_timeout=None, health_check_interval=30)


QUEUE_KEY = "mv:pipeline:q"


def enqueue_pipeline(exam_id: int) -> None:
    """Pousse un exam_id dans la file Redis (LPUSH). Compatible Redis 3.0."""
    print(f"[DEBUG enqueue_pipeline] appelé pour exam_id={exam_id}", flush=True)
    try:
        redis_conn = _redis_conn()
        payload = json.dumps({"exam_id": exam_id})
        result = redis_conn.lpush(QUEUE_KEY, payload)
        print(f"[DEBUG enqueue_pipeline] LPUSH result={result}", flush=True)
        logger.info("Enqueued pipeline task for exam %d", exam_id)
    except Exception as e:
        print(f"[DEBUG enqueue_pipeline] EXCEPTION: {type(e).__name__}: {e}", flush=True)
        logger.error("Failed to enqueue pipeline for exam %d: %s", exam_id, e)



@router.get("/{exam_id}")
async def get_exam(
    exam_id: int,
    db: AsyncSession = Depends(get_session),
    _doctor: Doctor = Depends(get_current_doctor),
):
    """Retourne l'état complet de l'examen une fois DONE.

    Champs retournés :
      - id, patient_id, exam_date
      - status, error_message
      - structured_findings, gradcam_path
      - comparison_result
      - report_text_clinical, report_text_patient
      - validation_result_clinical
    """
    result = await db.execute(select(Exam).where(Exam.id == exam_id))
    exam = result.scalar_one_or_none()
    if exam is None:
        raise HTTPException(404, detail="Examen introuvable")

    data = {
        "id": exam.id,
        "patient_id": exam.patient_id,
        "exam_date": exam.exam_date.isoformat() if exam.exam_date else None,
        "status": exam.status,
        "error_message": exam.error_message,
        "examen_number": exam.examen_number,
        "structured_findings": exam.structured_findings,
        "gradcam_path": exam.gradcam_path,
        "comparison_result": exam.comparison_result,
        "report_text_clinical": exam.report_text_clinical,
        "report_text_patient": exam.report_text_patient,
        "validation_result_clinical": exam.validation_result_clinical,
        "engine": (exam.validation_result_clinical or {}).get("engine"),
    }
    return data


@router.get("/{exam_id}/gradcam")
async def get_gradcam(
    exam_id: int,
    db: AsyncSession = Depends(get_session),
    _doctor: Doctor = Depends(get_doctor_from_query_or_header),
):
    """Sert l'image Grad-CAM générée pour l'examen (superposition heatmap).

    Retourne le fichier PNG, ou 404 si absent / examen introuvable.
    """
    result = await db.execute(select(Exam).where(Exam.id == exam_id))
    exam = result.scalar_one_or_none()
    if exam is None:
        raise HTTPException(404, detail="Examen introuvable")
    if not exam.gradcam_path or not os.path.isfile(exam.gradcam_path):
        raise HTTPException(404, detail="Grad-CAM non disponible pour cet examen")
    return FileResponse(
        exam.gradcam_path,
        media_type="image/png",
        filename=f"exam_{exam_id}_gradcam.png",
    )


@router.get("/{exam_id}/image")
async def get_exam_image(
    exam_id: int,
    db: AsyncSession = Depends(get_session),
    _doctor: Doctor = Depends(get_doctor_from_query_or_header),
):
    """Sert l'image radio originale (uploadée) de l'examen.

    Utilisé par la page de détail d'un examen passé (Historique).
    Retourne le fichier PNG/JPEG, ou 404 si absent / examen introuvable.
    """
    result = await db.execute(select(Exam).where(Exam.id == exam_id))
    exam = result.scalar_one_or_none()
    if exam is None:
        raise HTTPException(404, detail="Examen introuvable")
    if not exam.image_path or not os.path.isfile(exam.image_path):
        raise HTTPException(404, detail="Image non disponible pour cet examen")
    ext = os.path.splitext(exam.image_path)[1].lower().lstrip(".")
    media = {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
    }.get(ext, "application/octet-stream")
    return FileResponse(
        exam.image_path,
        media_type=media,
        filename=f"exam_{exam_id}_image.{ext}",
    )


def _build_report_pdf(exam, report_text: str, title: str):
    """Construit un PDF (radio originale + Grad-CAM + texte du rapport) en mémoire.

    Les images sont incluses si les fichiers existent sur disque ; sinon elles
    sont simplement omises (le rapport texte reste toujours généré).
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage
    from reportlab.lib.utils import ImageReader
    import io

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        title=title,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title", parent=styles["Heading1"], fontSize=16, spaceAfter=12)
    subtitle_style = ParagraphStyle("Subtitle", parent=styles["Heading2"], fontSize=12, spaceAfter=8)
    body_style = ParagraphStyle("Body", parent=styles["BodyText"], fontSize=11, leading=16)

    flow = [Paragraph(title, title_style)]

    max_img_width = 170 * mm
    max_img_height = 90 * mm

    def _add_image(path, caption):
        if not path or not os.path.isfile(path):
            return
        try:
            reader = ImageReader(path)
            iw, ih = reader.getSize()
            scale = min(max_img_width / iw, max_img_height / ih, 1.0)
            w, h = iw * scale, ih * scale
            flow.append(Paragraph(caption, subtitle_style))
            flow.append(RLImage(path, width=w, height=h))
            flow.append(Spacer(1, 10))
        except Exception:
            logger.warning("Could not embed image %s in PDF", path)

    _add_image(exam.image_path, "Radiographie thoracique")
    _add_image(exam.gradcam_path, "Grad-CAM (zone d'attention du modèle)")

    flow.append(Paragraph("Rapport", subtitle_style))
    for line in (report_text or "").split("\n"):
        safe = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") or "&nbsp;"
        flow.append(Paragraph(safe, body_style))
        flow.append(Spacer(1, 4))

    doc.build(flow)
    buffer.seek(0)
    return buffer


@router.get("/{exam_id}/report/clinical/pdf")
async def get_clinical_report_pdf(
    exam_id: int,
    inline: bool = False,
    db: AsyncSession = Depends(get_session),
    _doctor: Doctor = Depends(get_doctor_from_query_or_header),
):
    """Génère à la volée le PDF clinique : radio originale + Grad-CAM + rapport clinique.

    ?inline=true -> affiche dans le navigateur (embed), sinon téléchargement.
    """
    result = await db.execute(select(Exam).where(Exam.id == exam_id))
    exam = result.scalar_one_or_none()
    if exam is None:
        raise HTTPException(404, detail="Examen introuvable")
    if not exam.report_text_clinical:
        raise HTTPException(404, detail="Rapport clinique non disponible pour cet examen")

    buffer = _build_report_pdf(
        exam,
        exam.report_text_clinical,
        f"Rapport clinique — Examen {exam_id}",
    )
    disp = "inline" if inline else f"attachment; filename=examen_{exam_id}_rapport_clinique.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": disp},
    )


@router.get("/{exam_id}/report/patient/pdf")
async def get_patient_report_pdf(
    exam_id: int,
    inline: bool = False,
    db: AsyncSession = Depends(get_session),
    _doctor: Doctor = Depends(get_doctor_from_query_or_header),
):
    """Génère à la volée le PDF patient : radio originale + Grad-CAM + rapport patient.

    Retourne 404 si report_text_patient n'existe pas (rapport pas encore validé).
    ?inline=true -> affiche dans le navigateur (embed), sinon téléchargement.
    """
    result = await db.execute(select(Exam).where(Exam.id == exam_id))
    exam = result.scalar_one_or_none()
    if exam is None:
        raise HTTPException(404, detail="Examen introuvable")
    if not exam.report_text_patient:
        raise HTTPException(
            404,
            detail="Version patient non disponible — rapport clinique non validé",
        )

    buffer = _build_report_pdf(
        exam,
        exam.report_text_patient,
        f"Résumé de votre examen radiologique — Examen {exam_id}",
    )
    disp = "inline" if inline else f"attachment; filename=examen_{exam_id}_rapport_patient.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": disp},
    )



@router.websocket("/{exam_id}/progress")
async def exam_progress(websocket: WebSocket, exam_id: int):
    """WebSocket qui transmet les mises à jour de progression du pipeline.

    Authentification par query param ?token=<JWT> (Bearer token depuis login).
    Les statuts possibles :
      PENDING → CLASSIFYING → COMPARING → GENERATING → VALIDATING → DONE
      → FAILED (sur erreur)
    """
    await websocket.accept()
    logger.info("WS connected for exam %d", exam_id)

    doctor_id = await get_doctor_from_ws_token(websocket)
    if doctor_id is None:
        await websocket.send_json({"error": "Unauthorized", "status": "FAILED"})
        await websocket.close(code=4001)
        return

    pubsub = None
    try:
        def _connect_and_subscribe():
            conn = _redis_conn()
            ps = conn.pubsub()
            ps.subscribe(f"exam:{exam_id}:progress")
            return ps
        pubsub = await asyncio.to_thread(_connect_and_subscribe)

        while True:
            message = await asyncio.to_thread(pubsub.get_message, timeout=1.0)
            if message and message["type"] == "message":
                data = json.loads(message["data"])
                await websocket.send_json(data)
                if data.get("status") in (EXAM_STATUS_DONE, EXAM_STATUS_FAILED, "REJECTED"):
                    break

    except WebSocketDisconnect:
        logger.info("WS disconnected for exam %d", exam_id)
    except Exception as e:
        logger.error("WS error for exam %d: %s", exam_id, e)
    finally:
        if pubsub:
            pubsub.unsubscribe()
            pubsub.close()
        try:
            await websocket.close()
        except Exception:
            pass


@router.delete("/{exam_id}", status_code=200)
async def delete_exam(exam_id: int):
    """Supprime un examen et ses fichiers associés (image, gradcam, PDFs)."""
    import os
    from app.database import async_session_factory
    from app.models.exam import Exam
    
    async with async_session_factory() as session:
        exam = await session.get(Exam, exam_id)
        if not exam:
            raise HTTPException(status_code=404, detail="Examen non trouvé")
        
        for file_path in [exam.image_path, exam.gradcam_path, exam.pdf_clinical_path, exam.pdf_patient_path]:
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception:
                    pass
        
        await session.delete(exam)
        await session.commit()
        
    return {"status": "deleted", "exam_id": exam_id}
