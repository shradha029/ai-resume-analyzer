# API documentation

Base URL: `http://127.0.0.1:8000`. Interactive Swagger UI: `/docs`. All routes except health, register and login need the header `Authorization: Bearer <access_token>` (returned by login). Errors use `{"detail": "..."}` (422 validation errors return a list).

This table is generated from the FastAPI app.

| Group | Method | Route | Summary |
|---|---|---|---|
| Authentication | POST | `/api/auth/login` | Login |
| Authentication | POST | `/api/auth/logout` | Logout |
| Authentication | GET | `/api/auth/me` | Me |
| Authentication | POST | `/api/auth/register` | Register |
| Resumes | GET | `/api/resumes` | List Resumes |
| Resumes | POST | `/api/resumes/upload` | Upload Resume |
| Resumes | DELETE | `/api/resumes/{resume_id}` | Delete Resume |
| Resumes | GET | `/api/resumes/{resume_id}` | Get Resume |
| Resumes | POST | `/api/resumes/{resume_id}/extract` | Extract Resume |
| Resumes | GET | `/api/resumes/{resume_id}/extracted` | Get Extracted |
| Resumes | PUT | `/api/resumes/{resume_id}/extracted` | Update Extracted |
| Jobs | GET | `/api/jobs` | List Jobs |
| Jobs | POST | `/api/jobs/analyze` | Analyze |
| Jobs | GET | `/api/jobs/roles` | Roles |
| Jobs | DELETE | `/api/jobs/{job_id}` | Delete Job |
| Jobs | GET | `/api/jobs/{job_id}` | Get Job |
| Analysis | POST | `/api/analysis/create` | Create Analysis |
| Analysis | GET | `/api/analysis/history` | History |
| Analysis | DELETE | `/api/analysis/{analysis_id}` | Delete Analysis |
| Analysis | GET | `/api/analysis/{analysis_id}` | Get Analysis |
| Analysis | GET | `/api/analysis/{analysis_id}/gaps` | Get Gaps |
| Analysis | GET | `/api/analysis/{analysis_id}/recommendations` | Get Recommendations |
| Reports | GET | `/api/reports/{analysis_id}/download` | Download Report |
| ML | GET | `/api/ml/info` | Ml Info |
| Health | GET | `/api/health` | Health |

## Typical flow
1. `POST /api/auth/register` then `POST /api/auth/login` -> `access_token`.
2. `POST /api/resumes/upload` (multipart form field `file`, PDF only, max 5 MB) -> resume `id`.
3. `POST /api/resumes/{id}/extract` -> parsed data; optionally correct it with `PUT /api/resumes/{id}/extracted`.
4. `POST /api/jobs/analyze` with `{"target_role": "...", "job_description": "..."}` -> job `id` (+ requirements, + predicted category if the ML model is trained).
5. `POST /api/analysis/create` with `{"resume_id": 1, "job_id": 1, "weights": {...optional...}}` -> scores, skill matches, gaps, quality breakdown.
6. `GET /api/analysis/{id}/recommendations` (`?ai=true` adds an optional Gemini explanation) and `GET /api/reports/{id}/download` (PDF).

## Status codes used
201 created - 204 deleted - 400 empty file - 401 not authenticated / bad token - 404 not found (also for other users' data) -
409 resume not extracted yet / duplicate email - 410 stored file missing - 413 file too large - 415 not a PDF - 422 invalid input,
unreadable PDF (scanned, encrypted, corrupt).
