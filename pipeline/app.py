import os
import hmac
import json
import shutil
import tempfile
import torch
from fastapi import FastAPI, UploadFile, File, Form, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from run_pipeline import MedVisionPipeline

# Shared auth secret to authenticate requests from the backend worker.
# ⚠️ MANDATORY since the security review: this service processes patient data
# and runs a ~7B VLM, and used to start with NO auth when the variable was
# unset ("dev mode"). Fail closed instead. Generate a token with:
#   python -c "import secrets; print(secrets.token_urlsafe(48))"
PIPELINE_AUTH_TOKEN = os.environ.get("PIPELINE_AUTH_TOKEN")
if not PIPELINE_AUTH_TOKEN:
    raise RuntimeError(
        "PIPELINE_AUTH_TOKEN is not set. The AI pipeline processes patient data "
        "and must never run unauthenticated. Set the same value for this "
        "service and for the backend/worker (see .env.example)."
    )

# Allowed browser origins (comma-separated). Never combine "*" with
# allow_credentials=True — that lets any site make credentialed calls.
ALLOWED_ORIGINS = [
    o.strip() for o in os.environ.get("PIPELINE_ALLOWED_ORIGINS", "").split(",") if o.strip()
]

MAX_UPLOAD_BYTES = int(os.environ.get("PIPELINE_MAX_UPLOAD_MB", "50")) * 1024 * 1024

app = FastAPI(title="MedVision AI Pipeline")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=bool(ALLOWED_ORIGINS),
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

# Initialize the heavy pipeline ONCE when the server starts
print("Loading MedVision Pipeline...")
pipeline = MedVisionPipeline()


def _verify_auth(authorization=None):
    """Verify the shared auth token (constant-time comparison)."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    parts = authorization.split(" ", 1)
    if (
        len(parts) != 2
        or parts[0].lower() != "bearer"
        or not hmac.compare_digest(parts[1], PIPELINE_AUTH_TOKEN)
    ):
        raise HTTPException(status_code=401, detail="Invalid auth token")


@app.post("/analyze")
async def analyze_image(
    file: UploadFile = File(...),
    prior_exam: str = Form(None),
    chronic_history: str = Form(None),
    clinical_context: str = Form(None),
    authorization: str = Header(None),
):
    """Receives an X-ray image + optional patient data, runs the pipeline.

    - prior_exam: JSON string with {exam_date, findings} from most recent prior exam
    - chronic_history: JSON string with chronic condition booleans (PatientMedicalHistory)
    - clinical_context: JSON string with acute symptom booleans (ExamClinicalContext)
    """
    # Verify auth token (mandatory — see PIPELINE_AUTH_TOKEN above)
    _verify_auth(authorization)

    # Stream to a temp file with a real suffix (portable across OSes), refusing
    # oversized uploads DURING the copy so a huge body can't fill the disk.
    fd, temp_path = tempfile.mkstemp(suffix=".jpg")
    try:
        written = 0
        with os.fdopen(fd, "wb") as buffer:
            while True:
                chunk = file.file.read(1024 * 1024)
                if not chunk:
                    break
                written += len(chunk)
                if written > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large (max {MAX_UPLOAD_BYTES // (1024 * 1024)}MB)",
                    )
                buffer.write(chunk)

        if written == 0:
            raise HTTPException(status_code=400, detail="Empty file")

        # Parse optional patient data
        prior = json.loads(prior_exam) if prior_exam else None
        chronic = json.loads(chronic_history) if chronic_history else None
        context = json.loads(clinical_context) if clinical_context else None

        # Run the AI pipeline with real patient context
        results = pipeline.run(temp_path, prior_exam=prior, chronic_history=chronic, clinical_context=context)

        if results.get("error") == "invalid_image":
            return JSONResponse(status_code=406, content=results)

        return results
    except torch.cuda.OutOfMemoryError:
        torch.cuda.empty_cache()
        raise HTTPException(
            status_code=503,
            detail="GPU is temporarily out of memory. Please retry in a few seconds."
        )
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON in patient data: {e}")
    finally:
        torch.cuda.empty_cache()
        if os.path.exists(temp_path):
            os.remove(temp_path)


@app.get("/")
def read_root():
    return {"status": "MedVision AI pipeline is running"}
