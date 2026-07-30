"""Nettoyage de l'environnement Python — appel unique au lancement.

LE SEUL ENDROIT où ce module est importé est le début de main.py,
start_worker.py, et e2e_test.py, AVANT tout autre import du projet.

En important ce module, sys.path est nettoyé des entrées Hermes et le
venv du projet est placé en tête. Plus rien à faire après.

V2 : Chemins auto-détectés à partir de la position de ce fichier,
plus de valeurs D:/MedVision codées en dur.
"""
import os
import sys

# Auto-detect project root from this file's location:
# backend/app/env_isolation.py -> backend/ -> project root
_PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PROJECT_VENV = os.path.join(_PROJECT_DIR, '.venv', 'Lib', 'site-packages')
_PROJECT_BACKEND = os.path.join(_PROJECT_DIR, 'backend')
_PROJECT_ROOT = _PROJECT_DIR

_HERMES_MARKERS = [
    r"C:\Users\youss\AppData\Local\hermes",
    r"/c/Users/youss/AppData/Local/hermes",
    "hermes-agent",
    "hermes_agent",
]

for p in list(sys.path):
    if any(marker in p for marker in _HERMES_MARKERS):
        while p in sys.path:
            sys.path.remove(p)

for p in (_PROJECT_VENV, _PROJECT_BACKEND, _PROJECT_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)
    else:
        sys.path.remove(p)
        sys.path.insert(0, p)

pp = os.environ.get("PYTHONPATH", "")
if pp:
    cleaned = [
        e for e in pp.split(os.pathsep)
        if not any(marker in e for marker in _HERMES_MARKERS)
    ]
    os.environ["PYTHONPATH"] = os.pathsep.join(cleaned)

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
