# MedVision

<p align="center">
  <img src="webapp/public/fulllogo.svg" alt="MedVision logo" width="380" />
</p>

**MedVision** is an AI-powered, multi-agent medical imaging platform designed for automated chest X-ray analysis and radiology report generation. It couples deep learning vision models with Large Language Models (LLMs) to screen pathologies, ground findings in patient history, produce natural-language radiology reports, and autonomously validate results against hallucinations.

---

## 💡 What is MedVision?

In high-volume clinical workflows, interpreting chest radiographs requires precision and time. Traditional AI tools typically operate as single-task models—handling only classification *or* text generation in isolation—frequently causing unverified predictions or clinical hallucinations.

MedVision operates as an interconnected **5-stage multi-agent pipeline**:
1. **Gates incoming scans** to reject non-chest-X-ray images before inference.
2. **Predicts 14 thoracic pathologies** with visual interpretability heatmaps (Grad-CAM).
3. **Compares findings against patient history** to detect longitudinal trends (worsening, stable, resolving).
4. **Generates structured clinical reports** (findings & impressions) as well as patient-friendly explanations.
5. **Autonomously validates the generated text** using clinical rules and an LLM-as-a-judge loop to prevent errors.

---

## 🧠 System Architecture & Multi-Agent Pipeline

```
           [ Upload Chest X-Ray ]
                     │
                     ▼
┌────────────────────────────────────────────────────────┐
│ Agent 0: Guard Agent (OOD Detection)                   │
│ ➔ Rejects invalid modalities / non-medical images      │
└────────────────────┬───────────────────────────────────┘
                     │ (Accepted CXR)
                     ▼
┌────────────────────────────────────────────────────────┐
│ Agent 1: Pathology Classifier (ConvNeXtV2 + GAT)       │
│ ➔ 14 CheXpert labels + Platt Calibration + Grad-CAM    │
└────────────────────┬───────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────┐
│ Agent 1.5: Clinical Trend Comparator                   │
│ ➔ Evaluates deltas against prior exams & conditions    │
└────────────────────┬───────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────┐
│ Agent 2: Report Generator (Qwen2-VL-7B + QLoRA)        │
│ ➔ Generates formal clinical and patient reports        │
└────────────────────┬───────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────┐
│ Agent 3: Clinical Validator & Self-Correction          │
│ ➔ Layer 1 (Regex/Negation) + Layer 2 (LLM Judge)       │
└────────────────────────────────────────────────────────┘
```

### The Agents

- **Agent 0 — Guard Agent (`agent_guard/`)**: Built on a CheXpert-pretrained DenseNet121, this agent performs binary classification (CXR vs. Not-CXR). It rejects erroneous uploads (brain MRIs, CT scans, photos) before they enter the expensive deep learning pipeline.
- **Agent 1 — Multimodal Classifier (`agent_1_v2/`)**: Uses a **ConvNeXtV2-Base** backbone combined with a **Hierarchical Graph Attention Network (GAT)** to model label co-occurrences and anatomical hierarchies across 14 CheXpert conditions. Produces calibrated probabilities and visual Grad-CAM overlays.
- **Agent 1.5 — History Comparator (`agent_1_5_comparator/`)**: A deterministic engine that compares current pathology probabilities against historical exams and patient chronic records (COPD, heart failure, etc.) to compute factual progression trends without LLM hallucination.
- **Agent 2 — Report Generator (`agent_2_report/`)**: A **Qwen2-VL-7B-Instruct** model fine-tuned via 4-bit QLoRA. It transforms visual features, Agent 1 predictions, and historical summaries into structured clinical reports and accessible patient narratives.
- **Agent 3 — Validator Agent (`agent_3_validator/`)**: A dual-layer safety mechanism. Layer 1 runs deterministic regex and negation checks against Agent 1 predictions. If omissions or hallucinations are detected, Layer 2 engages an LLM-as-a-judge to rewrite and correct the report.

---

## 🛠️ Application Stack

The system is organized into decoupled tiers:

```
[ React 18 SPA (Vite) ]  (:8080 / :5173)
         │  REST / WebSockets
         ▼
[ FastAPI Backend ]      (:8003)
   ├── PostgreSQL 16     (Doctors, Patients, Histories, Exams)
   └── Redis 7           (Task Queue & Live Progress Pub/Sub)
         │
   [ Worker Process ]    (start_worker.py)
         │  HTTP / Bearer Auth
         ▼
[ PyTorch AI Pipeline ]  (:8002, GPU-accelerated)
   └── Agents 0 ➔ 1 ➔ 1.5 ➔ 2 ➔ 3
```

- **Frontend (`webapp/`)**: React 18 SPA built with Vite, Material UI, and Recharts. Allows clinicians to manage patient profiles, view longitudinal histories, upload scans, monitor live analysis states via WebSockets, and download validated reports as PDFs.
- **Backend API (`backend/`)**: FastAPI service with asynchronous SQLAlchemy 2.0 and Alembic migrations. Handles authentication (JWT), patient medical histories, clinical contexts, and examination records.
- **Background Worker (`backend/start_worker.py`)**: Asynchronously consumes jobs from Redis to run AI analyses without blocking API threads.
- **AI Inference Service (`pipeline/`)**: Standalone PyTorch microservice hosting the deep learning models and LLMs, exposing an authenticated `POST /analyze` endpoint.

---

## 📂 Repository Structure

```
MedVision/
├── agent_guard/           # Agent 0: Out-of-distribution guard model
├── agent_1_v2/            # Agent 1: ConvNeXtV2 + GAT pathology predictor
├── agent_1_5_comparator/  # Agent 1.5: Temporal trend & history comparator
├── agent_2_report/        # Agent 2: Qwen2-VL vision-language report generator
├── agent_3_validator/     # Agent 3: Dual-layer validator and LLM judge
├── pipeline/              # Multi-agent orchestrator & GPU inference service
├── backend/               # FastAPI backend, worker, database models & tests
│   ├── app/               # Routers, schemas, database config, and services
│   ├── alembic/           # Relational schema migrations
│   └── tests/             # Pytest unit tests for validator & comparator
├── webapp/                # React SPA frontend
├── docker-compose.yml     # Multi-service container definitions
└── .env.example           # Environment template
```

---

## 🚀 Getting Started

### 1. Environment Setup

Create an environment configuration file:
```bash
cp .env.example .env
```
Generate and configure strong keys for `JWT_SECRET` and `PIPELINE_AUTH_TOKEN`:
```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

### 2. Start with Docker Compose

Run the entire system (Database, Redis, Backend, Worker, AI Pipeline, and Web Frontend):

```bash
# 1. Run database migrations
docker compose run --rm backend alembic upgrade head

# 2. Start services
docker compose up -d --build
```

Access the interfaces:
- **Web App**: [http://localhost:8080](http://localhost:8080)
- **FastAPI Documentation**: [http://localhost:8003/docs](http://localhost:8003/docs)

### 3. Running Tests

Run the backend unit test suite:
```bash
python -m pytest backend/tests -q
```

