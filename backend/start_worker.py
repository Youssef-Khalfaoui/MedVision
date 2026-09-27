"""Worker de fond du pipeline MedVision (Round 4/6).

Consomme la file Redis `mv:pipeline:q` (LPUSH par l'upload) via BRPOP,
et exécute `run_pipeline(exam_id)` pour chaque tâche. Le pipeline publie
sa progression sur `exam:{id}:progress` (consommée par le WebSocket).

Usage :
    python start_worker.py
"""
import json
import logging
import os
import sys
import time

# Isolation d'environnement (doit être premier import du projet).
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "app")))
import app.env_isolation  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [worker] %(levelname)s %(message)s",
)
logger = logging.getLogger("worker")

QUEUE_KEY = "mv:pipeline:q"
from app.routers.exams import _redis_conn, QUEUE_KEY  # noqa: E402


def main():
    redis_conn = _redis_conn()
    logger.info("Worker démarre — écoute de la file %s", QUEUE_KEY)
    while True:
        try:
            item = redis_conn.brpop(QUEUE_KEY, timeout=0)
            if not item:
                continue
            _key, payload = item
            try:
                exam_id = json.loads(payload)["exam_id"]
            except Exception:
                logger.error("Payload invalide: %r", payload)
                continue
            logger.info("Traitement examen %d", exam_id)
            # Import différé pour ne charger torch qu'au 1er job.
            from app.pipeline import run_pipeline

            verdict = run_pipeline(exam_id)
            logger.info("Examen %d terminé (verdict=%s)", exam_id, verdict)
        except KeyboardInterrupt:
            logger.info("Worker arrêté (Ctrl-C)")
            break
        except Exception as e:
            logger.error("Erreur worker: %s", e, exc_info=True)
            time.sleep(1)


if __name__ == "__main__":
    main()
