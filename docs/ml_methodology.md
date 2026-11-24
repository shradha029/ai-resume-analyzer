# Machine learning and scoring methodology

This document explains every number the application shows. Nothing here is a prediction of being selected or hired.

## 1. Components and where ML is used
| Component | Technique | Trained? |
|---|---|---|
| Resume parsing | PyMuPDF text extraction, regex, section-heading rules, skill dictionary | rule-based, no training |
| Job description analysis | section/line cues, skill dictionary, phrase patterns for unfamiliar skills | rule-based |
| Keyword similarity | TF-IDF (1-2 grams, sublinear tf) + cosine similarity | fitted per comparison |
| Semantic similarity | Sentence Transformers (`all-MiniLM-L6-v2`), optional | pre-trained model, threshold needs calibration |
| **Job-role classification** | TF-IDF + Logistic Regression / Multinomial Naive Bayes / Linear SVM | **trained by you on a labelled dataset** |
| Resume quality score | documented rules (below) | rule-based |
| Match score | weighted formula (below) | formula |

## 2. Resume-Job Match Score
`Match = sum(w_i * S_i) / sum(w_i)` over the components that could be scored; each `S_i` is 0-100.
Default weights: skills 0.40, experience 0.20, education 0.15, projects 0.15, certifications 0.10 (configurable per request).
If a component's information is missing (for example the job states no education requirement), it is marked **unknown**,
excluded, and the remaining weights are re-normalised. It is never silently counted as 0 or 100.

### Skill Match Score
`sum(weight x credit) / sum(weight) x 100`. Requirement weights: mandatory 1.0, preferred 0.6, optional 0.3.
Credit per required skill: demonstrated in a project/experience/certification = 1.0; implied by a more specific skill
(e.g. MySQL for SQL) = 0.85 (0.55 if only listed); only listed in the Skills section = 0.7;
related technology (e.g. Flask for Django) = 0.35; semantic-only match <= 0.5 (threshold 0.6, initial value, to be calibrated); otherwise 0.

### Skill Coverage Score
`weight of demonstrated skills / total weight x 100` (strict: listing a skill is not enough).

### Experience, education, projects, certifications
- Experience: required years vs documented years (internship months count 50%); entry-level jobs score 100; internship / project requirements add 0 or 100 sub-scores that are averaged.
- Education: level (diploma < bachelor < master < doctorate) 70% + field match 30%; a degree still in progress counts at 90%.
- Projects: share (by weight) of the job's skills that appear in at least one project; per-project TF-IDF (and semantic) similarity is shown for ranking.
- Certifications: 1 relevant certification = 50, 2 or more = 100; unknown if the resume lists none and the job does not mention certifications.

## 3. Resume Quality Score (0-100)
Section completeness 20 + skills presentation 20 + experience/project descriptions 25 + quantifiable achievements 15 +
formatting/readability 10 + education/certification presentation 10. Every rule, its points and its advice are returned by the API
(`quality.components[*].rules`). Grammar is not checked. It measures presentation, not suitability.

## 4. Profile Readiness (heuristic)
`0.3 Quality + 0.45 Match + 0.25 Coverage` (re-normalised if one is unknown). A convenience summary only.

## 5. Job-role classifier (the trained model)
- **Data:** a labelled CSV of job descriptions and categories that the team downloads (see `datasets/README.md`). Which dataset was used,
  its size and class counts are written into `role_classifier_metrics.json` by the training script. If the dataset is synthetic, say so in the report.
- **Features:** TF-IDF (unigrams+bigrams, `min_df=2`, `max_features=50000`, sublinear tf). The cleaning function is stored inside the saved pipeline.
- **Models compared:** Logistic Regression, Multinomial Naive Bayes, Linear SVM.
- **Protocol:** stratified 80/20 train/test split. Models are compared with stratified k-fold cross-validation (default 3) on the training part only;
  the best mean macro-F1 wins. The winner is refit on the training split and evaluated once on the held-out test split.
- **Reported metrics:** accuracy, macro precision, macro recall, macro F1, per-class precision/recall/F1, confusion matrix (JSON + PNG).
  These are written by the script; the app shows them only if the model file exists.
- **Reproduce:** `python scripts/train_models.py --data datasets/FILE.csv` (fixed seed 42).
- **Limits:** accuracy depends entirely on the dataset; the classifier labels the *job description*, it does not rate the candidate.
  Linear SVM has no probabilities: the UI/API call its output a relative score.

## 6. Semantic vs TF-IDF evaluation (human-labelled)
`python scripts/make_relevance_sheet.py ...` builds a sheet of (job, resume) pairs. Team members fill `relevance` by hand (0/1/2).
`python -m app.ml.evaluation.ranking --labels ../datasets/relevance_labels.csv` then reports Precision@1/3, NDCG@1/3 and MRR for TF-IDF and the
semantic model. Rows without a human label are rejected. `python -m app.ml.evaluation.threshold --labels FILE.csv` calibrates the semantic threshold
from labelled (phrase, evidence, 0/1) pairs.

## 7. Known limitations
Rule-based parsing can misread unusual layouts; scanned PDFs are rejected (no OCR); skills outside the dictionary are found only from phrases such as
"experience with X"; semantic matching needs the optional model download; scores are decision-support indicators.
