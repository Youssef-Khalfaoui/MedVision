"""MedVision 3.0 — Backend API.
"""
import app.env_isolation
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import auth, patients, medical_history, clinical_context, exams
# from agent_1_5.router import router as agent_15_router  # Moved to AI API

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(patients.router)
app.include_router(medical_history.router)
app.include_router(clinical_context.router)
# app.include_router(agent_15_router  # Moved to AI API)
app.include_router(exams.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "3.0.0"}
