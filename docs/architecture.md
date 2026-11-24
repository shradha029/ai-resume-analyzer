# Architecture

## High-level flow
```
 Browser (React + Vite + Tailwind + Recharts)
        |  Axios, JWT in Authorization header   (dev: Vite proxies /api -> :8000)
        v
 FastAPI (routes -> services -> ML/NLP)  ----  SQLite via SQLAlchemy
        |
        +-- routes/      auth, resumes, jobs, analysis, reports, ml     (HTTP, validation, ownership checks)
        +-- services/    pdf_service -> resume_parser (+ skill_catalog) -> jd_analyzer -> matcher
        |                quality -> recommender -> report_service (ReportLab) -> gemini_service (optional)
        |                embedding_service (optional Sentence Transformers), role_classifier (trained model)
        +-- ml/          preprocessing, training (3 classifiers), evaluation (ranking, threshold), models/ (joblib + metrics)
        v
 uploads/<user_id>/*.pdf  (random filenames)      app.db (SQLite)
```

## Request flow for one analysis
1. **Upload** `POST /api/resumes/upload`: extension + `%PDF-` signature + size check; PyMuPDF opens the file (rejects corrupt, encrypted, empty/scanned); stored under a random name.
2. **Extract** `POST /api/resumes/{id}/extract`: text -> sections -> personal info, education, skills (with evidence per section), experience/internships, projects, certifications. Stored as JSON; the user can correct it (`PUT .../extracted`).
3. **Job** `POST /api/jobs/analyze`: skills classified mandatory/preferred/optional, experience, education, soft skills; predicted category if the classifier is trained.
4. **Analysis** `POST /api/analysis/create`: matcher computes skill match, coverage, experience, education, projects, certifications -> final match; gap detector and recommender run; quality score is computed; everything is saved.
5. **Dashboard** reads `GET /api/analysis/{id}` (+ extracted data + recommendations). **PDF** from `GET /api/reports/{id}/download`.

## Folder structure
```
resume-analyzer/
  backend/
    app/
      main.py config.py database.py dependencies.py
      models/    users, resumes, extracted data, jobs, analyses, skill matches/gaps, recommendations, reports
      schemas/   Pydantic request/response models
      routes/    auth.py resumes.py jobs.py analysis.py reports.py ml.py
      services/  pdf_service.py resume_parser.py skill_catalog.py jd_analyzer.py matcher.py quality.py
                 recommender.py report_service.py gemini_service.py embedding_service.py role_classifier.py
      utils/     security.py (bcrypt, JWT)
      ml/        preprocessing/ training/ evaluation/ models/
    tests/       pytest suites (auth, parser, matcher, quality, recommender, reports, ML)
    requirements.txt requirements-ml.txt .env.example
  frontend/
    src/  pages/ components/ charts/ context/ services/ utils/ test/
    package.json vite.config.js tailwind.config.js
  datasets/      README.md (+ your downloaded CSV, not committed)
  data/samples/  synthetic resumes and job descriptions
  docs/          architecture, database_schema, api_documentation, ml_methodology, RESUME_BULLETS
  scripts/       setup.py train_models.py make_samples.py make_relevance_sheet.py
```

## Security
bcrypt password hashing; JWT access tokens with server-side revocation on logout; every data route filters by the logged-in user
(other users' ids return 404); upload validation (extension, signature, size, page count, no user filename on disk); ORM only
(no raw SQL); secrets from environment variables; CORS restricted to configured origins; deletion removes DB rows and files.
