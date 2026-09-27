"""Make the agent source packages importable regardless of pytest rootdir.

The agent modules live in <repo>/<agent>/src (not installed packages), so the
tests import them by absolute path. This conftest runs before test collection.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]  # .../backend/tests -> repo root

AGENT_SRC_DIRS = [
    PROJECT_ROOT / "agent_1_5_comparator" / "src",
    PROJECT_ROOT / "agent_3_validator" / "src",
]

for src_dir in AGENT_SRC_DIRS:
    if src_dir.is_dir() and str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
