"""
Storage abstraction pour les images radiologiques uploadées.

Dev : stockage local dans <project_root>/data/uploads/{exam_id}.png (ou MEDVISION_UPLOAD_DIR).
Prod : à remplacer par S3/MinIO (Interface abstraite respectée).

V2: Chemin par défaut auto-détecté depuis __file__ au lieu de D:/MedVision/
    codé en dur.
"""
import os
from pathlib import Path

_STORAGE_DIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / "data"

UPLOAD_DIR = Path(os.environ.get(
    "MEDVISION_UPLOAD_DIR",
    str(_STORAGE_DIR / "uploads"),
))

PDF_DIR = Path(os.environ.get(
    "MEDVISION_PDF_DIR",
    str(_STORAGE_DIR / "pdfs"),
))


def _ensure_dir() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    PDF_DIR.mkdir(parents=True, exist_ok=True)


def pdf_path(exam_id: int, kind: str) -> Path:
    """Chemin du PDF persisté pour un examen.

    kind = 'clinical' | 'patient'.
    """
    _ensure_dir()
    return PDF_DIR / f"{exam_id}_report_{kind}.pdf"


def get_pdf_path(exam_id: int, kind: str) -> str:
    return str(pdf_path(exam_id, kind).resolve())


def save_image(exam_id: int, image_bytes: bytes, ext: str = ".png") -> str:
    """Sauvegarde l'image uploadée et retourne le chemin absolu."""
    _ensure_dir()
    filename = f"{exam_id}{ext}"
    path = UPLOAD_DIR / filename
    path.write_bytes(image_bytes)
    return str(path.resolve())


def get_image_path(exam_id: int, ext: str = ".png") -> str:
    """Retourne le chemin absolu de l'image pour un exam_id.

    Commence par l'extension donnee, puis essaie .jpg/.jpeg si absente.
    """
    for c in [f"{exam_id}{ext}", f"{exam_id}.jpg", f"{exam_id}.jpeg"]:
        p = UPLOAD_DIR / c
        if p.is_file():
            return str(p.resolve())
    return str((UPLOAD_DIR / f"{exam_id}{ext}").resolve())
