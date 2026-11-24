# AI-Powered Resume Analyzer and Job-Specific Skill Gap Detection System

Final-year B.Tech CSE project. Upload a PDF resume, paste a job description, and get an explainable analysis: resume quality score,
resume-job match score, skill coverage, matched / partial / missing skills, experience and education gaps, personalised
recommendations, a visual dashboard and a downloadable PDF report. Includes a trained job-role classifier (scikit-learn).

Scores describe presentation and fit. **They are not the probability of being selected or hired.**

## What is implemented
| Area | Status |
|---|---|
| Auth (register, login, logout with token revocation, JWT, bcrypt, per-user data) | done, tested |
| PDF upload (type/size/signature checks; corrupt, encrypted, empty, scanned PDFs rejected clearly) | done, tested |
| Resume parsing (personal info, education, skills with evidence, experience vs internships vs projects, certifications) + user correction | done, tested |
| Job description analysis (mandatory / preferred / optional, experience, education, soft skills, unfamiliar skills) | done, tested |
| Matching (weighted skills/experience/education/projects/certifications, unknown-aware, configurable weights, TF-IDF + optional semantic) | done, tested |
| Skill gap detection + recommendations (gap-driven, official-doc links, optional Gemini explanation) | done, tested (Gemini mocked) |
| Resume quality score (documented rules) and PDF report (15 sections) | done, tested |
| React dashboard (6 charts, tables, history, review/edit, PDF download) | done, 41 tests |
| ML: 3 classifiers compared with cross-validation, held-out evaluation, saved artifacts, ranking and threshold evaluation scripts | scripts done and tested; **you train it with your dataset** |

## Differences from the original master prompt (decided with the team lead to keep it runnable)
| Master prompt | This project | How to upgrade later |
|---|---|---|
| PostgreSQL + Alembic | SQLite (no setup); same SQLAlchemy models | set `DATABASE_URL=postgresql+psycopg2://...`, `pip install psycopg2-binary`; add Alembic |
| OCR fallback (Tesseract) | scanned PDFs rejected with a clear message | add pytesseract |
| spaCy NER, pdfplumber | regex + section rules + skill dictionary, PyMuPDF only | add spaCy for name/organisation NER |
| Docker | not included | add Dockerfile / compose |
| Sentence Transformers required | optional (large download); rules + TF-IDF work without it, and the result states which method ran | `pip install -r backend/requirements-ml.txt` |
| Gemini | optional, off unless `GEMINI_API_KEY` is set | set the key in `backend/.env` |

## Requirements
Python 3.10 - 3.12, Node.js 18+. Windows commands shown; macOS/Linux use `source venv/bin/activate`.

## Run it
**Backend** (terminal 1):
```
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```
API docs: http://127.0.0.1:8000/docs. Edit `backend/.env` and set a long random `SECRET_KEY`. The SQLite file `app.db` is created automatically.

**Frontend** (terminal 2):
```
cd frontend
npm install
npm run dev
```
Open http://localhost:5173.

## Train the ML model (needs your dataset)
Follow `datasets/README.md`, then from the project root with the venv active:
```
python scripts/train_models.py --data datasets/YOUR_FILE.csv
```
Restart the backend. The dashboard shows the real metrics, and every analysed job description gets a predicted category.

## Run the tests
```
cd backend && pytest -q          # 90 tests
cd frontend && npm test          # 41 tests
```
## Machine Learning

The project includes a text classifier that predicts a category from a document's text. The text is converted to numbers using TF-IDF (word and two-word-phrase weights that give more importance to rarer, more informative words). We compared three models on these features: Logistic Regression, Multinomial Naive Bayes and Linear SVM. We used 3-fold cross-validation on the training data and chose the model with the best macro-F1; Linear SVM won (cross-validated macro-F1 0.661, against 0.641 for Logistic Regression and 0.534 for Naive Bayes). The chosen model was then tested once on 485 held-out documents. It reached accuracy 0.680, precision 0.686, recall 0.669 and F1-score 0.663 (macro averages) across 22 categories; random guessing would give about 4.5%. Precision is the share of predicted labels that are correct, recall is the share of real members of a category that were found, and F1 is the balance of the two. The model was trained on the Kaggle Resume Dataset (2,425 resumes), so the category it shows for a job description is indicative only.

## Documentation
`docs/architecture.md`, `docs/database_schema.md`, `docs/api_documentation.md`, `docs/ml_methodology.md`, `docs/RESUME_BULLETS.md`.

## Sample data
`data/samples/` has synthetic resumes (PDF) and job descriptions (TXT). Regenerate: `python scripts/make_samples.py`.

## Privacy and deletion
Resumes contain personal data. Each user can delete a resume (removes the file, extracted data, analyses and reports), an analysis, or a job
description. Passwords are stored only as bcrypt hashes. `.env`, `app.db`, `uploads/`, `venv/` and `node_modules/` are git-ignored; never commit secrets.

## Known limitations
Rule-based parsing can misread unusual layouts; no OCR; skills outside the built-in dictionary are found only from phrases like "experience with X";
no grammar checking; the semantic threshold (0.60) is an initial value until calibrated with labelled data; the classifier is only as good as its dataset.

## Troubleshooting
- `ModuleNotFoundError`: the venv is not active or `pip install -r requirements.txt` was not run.
- Frontend shows "Cannot reach the server": start the backend on port 8000.
- 401 after a restart: log in again (tokens expire after 60 minutes).
