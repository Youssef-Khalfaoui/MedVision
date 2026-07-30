"""
Pipeline d'exécution Agent 1 → 1.5 → 2 → 3.
Forwards the image to the standalone MedVision v2 AI API via HTTP.
Saves results directly to PostgreSQL and publishes progress via Redis.
"""
import json
import logging
import os
import sys
import base64
import requests
import psycopg2
import redis

from app.config import get_settings
from app.storage import UPLOAD_DIR

ROOT = os.path.abspath(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

settings = get_settings()
logger = logging.getLogger("pipeline")

ST_PENDING = "PENDING"
ST_PROCESSING = "PROCESSING"
ST_DONE = "DONE"
ST_FAILED = "FAILED"

AI_API_URL = settings.ai_api_url

DB_PARAMS = {
    "dbname": settings.db_name,
    "user": settings.db_user,
    "password": settings.db_password,
    "host": settings.db_host,
    "port": settings.db_port,
}


def _redis_conn():
    return redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=0,
        protocol=2,
        socket_timeout=None,
        health_check_interval=30,
    )


def _publish_progress(exam_id: int, status: str, error: str = None):
    try:
        r = _redis_conn()
        payload = {"exam_id": exam_id, "status": status}
        if error:
            payload["error"] = error
        r.publish(f"exam:{exam_id}:progress", json.dumps(payload))
    except Exception as e:
        logger.debug("Redis publish failed (non-critical): %s", e)


def _delete_exam(exam_id: int) -> None:
    """Supprime l'examen rejete par le Guard (Agent 0) : image invalide,
    donc on ne garde ni ligne en base ni fichier, pour ne pas polluer
    l'historique avec des uploads qui ne sont pas des radios valides."""
    image_path = None
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cursor = conn.cursor()
        cursor.execute("SELECT image_path FROM exams WHERE id=%s", (exam_id,))
        row = cursor.fetchone()
        if row:
            image_path = row[0]
        cursor.execute("DELETE FROM exams WHERE id=%s", (exam_id,))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        logger.error("DB delete failed for exam %d: %s", exam_id, e)
    if image_path and os.path.isfile(image_path):
        try:
            os.remove(image_path)
        except Exception as e:
            logger.warning("Could not remove rejected image %s: %s", image_path, e)


def _update_status(exam_id: int, status: str, error: str = None) -> None:
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cursor = conn.cursor()
        if error:
            cursor.execute("UPDATE exams SET status=%s, error_message=%s WHERE id=%s", (status, error, exam_id))
        else:
            cursor.execute("UPDATE exams SET status=%s, error_message=NULL WHERE id=%s", (status, exam_id))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        logger.error("DB update failed for exam %d: %s", exam_id, e)


def _save_results(exam_id: int, **fields) -> None:
    sets = []
    vals = []
    for k, v in fields.items():
        sets.append(f"{k}=%s")
        vals.append(json.dumps(v, default=str) if isinstance(v, dict) else v)
    vals.append(exam_id)
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cursor = conn.cursor()
        cursor.execute(f"UPDATE exams SET {', '.join(sets)} WHERE id=%s", vals)
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        logger.error("DB save failed for exam %d: %s", exam_id, e)


def run_pipeline(exam_id: int) -> str:
    logger.info("[pipeline] Starting pipeline for exam %d", exam_id)
    try:
        _update_status(exam_id, ST_PROCESSING)
        _publish_progress(exam_id, ST_PROCESSING)

        from app.storage import get_image_path
        img_path = get_image_path(exam_id)
        if not os.path.isfile(img_path):
            raise FileNotFoundError(f"Image not found: {img_path}")

        logger.info("[pipeline] Forwarding image + patient context to v2 AI API...")

        # Fetch patient data for trend analysis (Agents 1.5 & 2)
        patient_id = None
        prior_exam_data = None
        chronic_history_data = None
        clinical_context_data = None
        try:
            conn = psycopg2.connect(**DB_PARAMS)
            cursor = conn.cursor()

            # 1. Get patient_id for this exam
            cursor.execute("SELECT patient_id FROM exams WHERE id=%s", (exam_id,))
            row = cursor.fetchone()
            if row:
                patient_id = row[0]

            # 2. Fetch chronic medical history for this patient
            if patient_id:
                cursor.execute(
                    "SELECT smoking_status, prior_pneumonia, tuberculosis_history, "
                    "copd, asthma, heart_disease, heart_failure, diabetes, "
                    "hypertension, previous_operations, allergies, "
                    "current_symptoms, current_medication, doctor_notes "
                    "FROM patient_medical_history WHERE patient_id=%s",
                    (patient_id,),
                )
                hrow = cursor.fetchone()
                if hrow:
                    chronic_history_data = {
                        "smoking_status": hrow[0],
                        "prior_pneumonia": hrow[1],
                        "tuberculosis_history": hrow[2],
                        "copd": hrow[3],
                        "asthma": hrow[4],
                        "heart_disease": hrow[5],
                        "heart_failure": hrow[6],
                        "diabetes": hrow[7],
                        "hypertension": hrow[8],
                        "previous_operations": hrow[9],
                        "allergies": hrow[10],
                        "current_symptoms": hrow[11],
                        "current_medication": hrow[12],
                        "doctor_notes": hrow[13],
                    }

            # 3. Fetch clinical context for THIS exam
            cursor.execute(
                "SELECT fever, cough, chest_pain, shortness_of_breath, "
                "oxygen_saturation, body_temperature "
                "FROM exam_clinical_context WHERE exam_id=%s",
                (exam_id,),
            )
            crow = cursor.fetchone()
            if crow:
                clinical_context_data = {
                    "fever": crow[0],
                    "cough": crow[1],
                    "chest_pain": crow[2],
                    "shortness_of_breath": crow[3],
                    "oxygen_saturation": float(crow[4]) if crow[4] is not None else None,
                    "body_temperature": float(crow[5]) if crow[5] is not None else None,
                }

            # 4. Fetch the most recent prior exam (same patient, earlier exam_date)
            if patient_id:
                cursor.execute(
                    "SELECT id, exam_date, structured_findings "
                    "FROM exams WHERE patient_id=%s AND id < %s "
                    "AND structured_findings IS NOT NULL "
                    "ORDER BY exam_date DESC LIMIT 1",
                    (patient_id, exam_id),
                )
            prow = cursor.fetchone()
            if prow:
                prior_exam_data = {
                    "exam_id": prow[0],
                    "exam_date": prow[1].isoformat() if hasattr(prow[1], "isoformat") else str(prow[1]),
                    "findings": json.loads(prow[2]) if isinstance(prow[2], str) else (prow[2] or {}),
                }

            cursor.close()
            conn.close()
        except Exception as e:
            logger.warning("Failed to fetch patient context (non-fatal): %s", e)

        # Build multipart form data: file + optional JSON fields
        files = {"file": f}
        data = {}
        if prior_exam_data:
            data["prior_exam"] = json.dumps(prior_exam_data)
        if chronic_history_data:
            data["chronic_history"] = json.dumps(chronic_history_data)
        if clinical_context_data:
            data["clinical_context"] = json.dumps(clinical_context_data)

        # Auth header for the pipeline API
        headers = {}
        pipeline_token = os.environ.get("PIPELINE_AUTH_TOKEN")
        if pipeline_token:
            headers["Authorization"] = f"Bearer {pipeline_token}"

        response = requests.post(AI_API_URL, files=files, data=data, headers=headers, timeout=120)
        response.raise_for_status()
        ai_result = response.json()

        logger.info("[pipeline] AI API returned results. Saving to PostgreSQL...")

        # Decode and save Grad-CAM image if present
        gradcam_path = None
        gradcam_b64 = ai_result.get("gradcam_base64")
        if gradcam_b64:
            try:
                UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
                gradcam_path = str(UPLOAD_DIR / f"{exam_id}_gradcam.png")

                img_data = base64.b64decode(gradcam_b64)
                with open(gradcam_path, "wb") as f:
                    f.write(img_data)

                logger.info(f"[pipeline] Grad-CAM successfully saved to {gradcam_path}")
            except Exception as e:
                logger.error(f"[pipeline] Failed to save Grad-CAM: {e}")
                import traceback
                logger.error(traceback.format_exc())

        _save_results(
            exam_id,
            structured_findings=ai_result.get("predictions", {}),
            comparison_result={"trend_summary": ai_result.get("trend_summary", "")},
            report_text_clinical=ai_result.get("clinical_report", "No report generated."),
            report_text_patient=ai_result.get("patient_report"),
            validation_result_clinical={"verdict": ai_result.get("validation_verdict", "N/A")},
            gradcam_path=gradcam_path
        )
        _update_status(exam_id, ST_DONE)
        _publish_progress(exam_id, ST_DONE)
        return "DONE"

    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response is not None else None
        try:
            detail = e.response.json().get("detail", str(e)) if e.response is not None else str(e)
        except Exception:
            detail = str(e)

        if status_code == 406:
            logger.info("[pipeline] Exam %d REJECTED by Guard (Agent 0): %s", exam_id, detail)
            _delete_exam(exam_id)
            _publish_progress(exam_id, "REJECTED", error=detail)
            return "REJECTED"

        import traceback
        tb = traceback.format_exc()
        logger.error("[pipeline] Exam %d FAILED (HTTP %s): %s\n%s", exam_id, status_code, e, tb)
        _update_status(exam_id, ST_FAILED, error=detail)
        _publish_progress(exam_id, ST_FAILED, error=detail)
        return ST_FAILED

    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error("[pipeline] Exam %d FAILED: %s\n%s", exam_id, e, tb)
        _update_status(exam_id, ST_FAILED, error=str(e))
        _publish_progress(exam_id, ST_FAILED, error=str(e))
        return ST_FAILED


if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_pipeline(int(sys.argv[1]))
    else:
        print("Usage: python -m app.pipeline <exam_id>")
