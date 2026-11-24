# Database schema

SQLite (default, zero setup) via SQLAlchemy. Tables are created automatically on first start (`Base.metadata.create_all`). Switching to PostgreSQL only needs `DATABASE_URL` (see the README); Alembic migrations are not included.

This file is generated from the SQLAlchemy models, so it matches the code.


## `analysis_reports`

| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | PK |
| analysis_id | INTEGER | indexed, not null, FK -> resume_analyses.id (cascade delete) |
| file_path | VARCHAR(300) | not null |
| file_size | INTEGER | not null |
| generated_at | DATETIME | not null |

## `extracted_resume_data`

| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | PK |
| resume_id | INTEGER | unique, indexed, not null, FK -> resumes.id (cascade delete) |
| data | JSON | not null |
| raw_text | TEXT | not null |
| is_user_edited | BOOLEAN | not null |
| updated_at | DATETIME | not null |

## `job_descriptions`

| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| user_id | INTEGER | indexed, not null, FK -> users.id (cascade delete) |
| target_role | VARCHAR(100) | not null |
| text | TEXT | not null |
| parsed | JSON | not null |
| created_at | DATETIME | not null |

## `recommendations`

| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | PK |
| analysis_id | INTEGER | indexed, not null, FK -> resume_analyses.id (cascade delete) |
| category | VARCHAR(20) | not null |
| priority | VARCHAR(10) | not null |
| title | VARCHAR(200) | not null |
| action | TEXT | not null |
| reason | TEXT | not null |
| resources | JSON | not null |

## `resume_analyses`

| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| user_id | INTEGER | indexed, not null, FK -> users.id (cascade delete) |
| resume_id | INTEGER | indexed, not null, FK -> resumes.id (cascade delete) |
| job_id | INTEGER | indexed, not null, FK -> job_descriptions.id (cascade delete) |
| target_role | VARCHAR(100) | not null |
| match_score | FLOAT |  |
| skill_match_score | FLOAT |  |
| skill_coverage_score | FLOAT |  |
| tfidf_similarity | FLOAT |  |
| semantic_similarity | FLOAT |  |
| method | VARCHAR(40) | not null |
| component_scores | JSON | not null |
| additional_skills | JSON | not null |
| details | JSON | not null |
| created_at | DATETIME | not null |

## `resumes`

| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| user_id | INTEGER | indexed, not null, FK -> users.id (cascade delete) |
| original_filename | VARCHAR(255) | not null |
| stored_filename | VARCHAR(64) | not null |
| file_size | INTEGER | not null |
| page_count | INTEGER | not null |
| status | VARCHAR(20) | not null |
| uploaded_at | DATETIME | not null |

## `revoked_tokens`

| Column | Type | Constraints |
|---|---|---|
| jti | VARCHAR(64) | PK |
| expires_at | DATETIME | not null |

## `skill_gaps`

| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | PK |
| analysis_id | INTEGER | indexed, not null, FK -> resume_analyses.id (cascade delete) |
| gap_type | VARCHAR(30) | not null |
| severity | VARCHAR(10) | not null |
| title | VARCHAR(200) | not null |
| description | TEXT | not null |

## `skill_matches`

| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | PK |
| analysis_id | INTEGER | indexed, not null, FK -> resume_analyses.id (cascade delete) |
| skill | VARCHAR(100) | not null |
| category | VARCHAR(30) | not null |
| level | VARCHAR(15) | not null |
| weight | FLOAT | not null |
| status | VARCHAR(15) | not null |
| credit | FLOAT | not null |
| custom | BOOLEAN | not null |
| demonstrated | BOOLEAN | not null |
| evidence | JSON | not null |
| explanation | TEXT | not null |

## `users`

| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | PK, indexed |
| full_name | VARCHAR(100) | not null |
| email | VARCHAR(255) | unique, indexed, not null |
| hashed_password | VARCHAR(255) | not null |
| created_at | DATETIME | not null |

## Relationships
- `users` 1-N `resumes`, `job_descriptions`, `resume_analyses` (each row stores `user_id`; every query filters by it, so users only see their own data).
- `resumes` 1-1 `extracted_resume_data`; `resumes` 1-N `resume_analyses`.
- `resume_analyses` 1-N `skill_matches`, `skill_gaps`, `recommendations`, `analysis_reports`.
- Deleting a resume, job description or analysis removes its dependent rows and the stored PDF files (ORM cascade + file cleanup).

## Not stored
Passwords are stored only as bcrypt hashes. Uploaded PDFs are stored under random filenames in `backend/uploads/<user_id>/`.
The master prompt's `skill_catalog` and `extracted_skills` tables are not separate tables: the skill dictionary lives in
`app/services/skill_catalog.py` and extracted skills are part of the JSON in `extracted_resume_data.data`.
