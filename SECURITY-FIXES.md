# Security & Bug-Fix Changelog (post-audit)

Records the fixes applied after the full code/security review. Dates: 2026-09-19.

## CRITICAL fixes

### 1. `DELETE /api/exams/{id}` was completely unauthenticated
- **Where:** `backend/app/routers/exams.py` (`delete_exam`)
- **Was:** anyone able to reach the backend could permanently delete any exam
  and its files (image, Grad-CAM, PDFs) by iterating integer IDs.
- **Now:** requires a valid JWT (`Depends(get_current_doctor)`).

### 2. The clinical-context router was fully unauthenticated (PHI read + write)
- **Where:** `backend/app/routers/clinical_context.py`
- **Was:** `GET`/`POST /api/exams/{exam_id}/clinical-context` exposed fever,
  cough, chest pain, SpO2 and body temperature to anonymous callers, and let
  them inject context that the AI pipeline folds into generated reports.
- **Now:** both endpoints require a JWT. A `PUT` upsert endpoint was also
  added â€” the POST's own 409 message told clients to "Use PUT", which did not
  exist.

### 3. The AI pipeline ran unauthenticated by default
- **Where:** `pipeline/app.py`
- **Was:** `PIPELINE_AUTH_TOKEN` was optional; unset (the shipped default)
  meant zero auth on an endpoint that runs a ~7B VLM on arbitrary uploads.
- **Now:** fail-closed (`RuntimeError` at startup if unset), constant-time
  token comparison (`hmac.compare_digest`), 50 MB streamed upload cap, and
  portable temp files (`tempfile.mkstemp` instead of hardcoded `/tmp`).
- **Deployment:** the token is wired through `docker-compose.yml`
  (pipeline, backend, worker) and documented in `.env.example`.

## HIGH fixes

### 4. Agent 1.5 crashed on every exam that had a prior study (reproduced)
- **Where:** `agent_1_5_comparator/src/comparator.py`
- **Was:** `prior_exam["exam_date"].strftime(...)` â€” but the backend ships the
  date as an ISO string, so `AttributeError` failed the entire pipeline and
  broke the "compare against prior exams" feature.
- **Now:** dates and `findings` are normalised (`_format_exam_date`,
  `_coerce_findings`) and accept datetime, date, ISO string, dict or JSON
  string. Regression test in `backend/tests/test_comparator.py`.

### 5. Validator negation scope produced false "Contradictions" (reproduced)
- **Where:** `agent_3_validator/src/validator.py`
- **Was:** negation scanning covered the whole preceding clause and included a
  bare `"normal"`, so 3 of 7 realistic phrasings were extracted backwards â€”
  e.g. *"the heart size is normal and there is a small pleural effusion"*
  marked the **effusion** as negated, forcing a bogus Layer-2 rewrite of a
  correct report.
- **Now:** negation window limited to ~60 chars, `"and"` ends a scope, bare
  `"normal"` removed. 13 regression tests in `backend/tests/test_validator.py`.

### 6. CORS wildcard + credentials on both services
- **Where:** `backend/app/main.py`, `pipeline/app.py`
- **Now:** origins come from `ALLOWED_ORIGINS` / `PIPELINE_ALLOWED_ORIGINS`;
  `"*"` is refused outside debug mode by `config.py`.

### 7. Redis and PostgreSQL were exposed without auth
- **Where:** `docker-compose.yml`
- **Now:** `db`/`redis`/`pipeline` ports bind to `127.0.0.1` only; Redis runs
  with `--requirepass` and the backend/worker authenticate
  (`redis_password` setting threaded through both `_redis_conn()` helpers).

### 8. `check-duplicate` leaked other doctors' exam details
- **Where:** `backend/app/routers/exams.py`
- **Was:** the docstring promised doctor-scoping; the query didn't do it.
- **Now:** same-doctor matches keep full details; other-doctor matches return
  `{"duplicate": true, "same_doctor": false}` with no identifiers. The
  frontend (`AnalysisTab.jsx`) shows a generic message for that case.

## MEDIUM fixes

| # | Fix | File(s) |
|---|-----|---------|
| 1 | `get_current_doctor` catches `TypeError` (token without `sub` â†’ 401, not 500); dead code removed | `dependencies.py` |
| 2 | Grad-CAM divide-by-zero guard (NaN overlay) | `run_pipeline.py` |
| 3 | `torch.load(..., weights_only=True)` (pickle RCE surface) | `run_pipeline.py` |
| 4 | `set_cooccurrence_edges` moved after `load_state_dict` (buffer broke strict load) | `run_pipeline.py` |
| 5 | `.to("cuda")` â†’ `.to(self.device)` (CPU hosts crash) | `run_pipeline.py` |
| 6 | Adapter paths were `/workspace/agent_2/...` (never mounted) â†’ `agent_2_report/...` via `AGENT2_ADAPTER_PATH` | `llm_judge.py`, `predict_agent2.py` |
| 7 | "No Finding" pattern now matches "no acute cardiopulmonary findings" | `validator.py` |
| 8 | Realtime WebSocket was broken through the Vite proxy (missing `ws: true`) â€” UI silently fell back to polling | `vite.config.js` |
| 9 | Containers hardened: non-root backend/webapp, `no-new-privileges` everywhere, `.dockerignore` for backend/pipeline | Dockerfiles, compose |
| 10 | `npm ci`, `node:18` (EOL) â†’ `node:22` | `webapp/Dockerfile` |
| 11 | JWT guard refuses weak/short/example secrets (fail closed) | `backend/app/config.py` |

## Test suite (was broken â€” 0 working tests)

- **Removed** `backend/tests/test_agent_1_5.py`: it imported `agent_1_5.delta`,
  `agent_1_5.models`, `agent_1_5.config` â€” modules that do not exist anywhere
  in the repo, so pytest could not even collect.
- **Added** `conftest.py`, `test_comparator.py`, `test_validator.py`
  â†’ **26 tests, all passing** (`python -m pytest backend/tests -q`).

## Known remaining gaps (documented, not yet fixed)

1. **No per-doctor data isolation** — every authenticated doctor can read all patients/exams (by design per models/doctor.py). Requires a schema change (organization / assigned_doctor scoping) — the largest remaining security item.
2. **Open self-registration** — no approval flow, email verification, or password policy (auth.py).
3. **No rate limiting / account lockout** on POST /api/auth/login.
4. **JWTs still travel in query strings** for images/PDFs/WebSockets (leak into access logs); tokens are not revocable and survive password changes.
5. **Job queue has no ack/retry** (LPUSH/BRPOP): a worker crash mid-job strands the exam in PROCESSING; DB helpers swallow errors, so a failed write leaves exams in PENDING.
6. **120 s HTTP timeout** to the AI pipeline may be too short for the full 5-agent chain — measure on your GPU.
7. **Full validation payload is not persisted** — needs_review, corrected_deterministically, the error list and trend breakdown are dropped; doctors cannot see that a report was flagged for review.
8. **Pipeline container still runs as root** (deliberate: the HF cache volume is at /root/.cache; moving it forces a ~15 GB model re-download).
9. **No pagination** on list endpoints; **no TLS/HTTPS**; /docs exposed in production; vite preview still serves production (nginx recommended).
10. **Verification limits**: sqlalchemy, jose, passlib, psycopg2 and redis are not installed in the review environment, so backend endpoints were verified by AST/static analysis and py_compile, not live HTTP calls. The two reproduced bugs (comparator crash, validator negation) WERE executed and verified, and both have regression tests. Docker images were not rebuilt (no GPU / Compose plugin here) — run docker compose up -d --build and smoke-test an upload.
