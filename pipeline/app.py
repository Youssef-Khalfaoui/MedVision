import os
import uuid
import shutil
import json
import torch
from fastapi import FastAPI, UploadFile, File, Form, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from run_pipeline import MedVisionPipeline

app = FastAPI(title="MedVision API")

# In production, change "*" to "http://193.95.31.163:8080"
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared auth secret to authenticate requests from the backend worker
# Set via PIPELINE_AUTH_TOKEN env var; if unset, no auth is enforced (dev mode)
PIPELINE_AUTH_TOKEN = os.environ.get("PIPELINE_AUTH_TOKEN")

# Initialize the heavy pipeline ONCE when the server starts
print("Loading MedVision Pipeline...")
pipeline = MedVisionPipeline()


def _verify_auth(authorization=None):
    """Verify the shared auth token when configured."""
    if PIPELINE_AUTH_TOKEN is None:
        return  # No auth configured - dev mode
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or parts[1] != PIPELINE_AUTH_TOKEN:
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
    # Verify auth token if configured
    _verify_auth(authorization)

    temp_path = f"/tmp/{uuid.uuid4()}.jpg"

    # Save the uploaded file temporarily
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
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
    return {"status": "MedVision API is running!"}
