# Datasets

Datasets are **not** committed to GitHub (large, and licences vary). Download them yourself.

## 1. Job-role classifier training data (required for the ML model)
You need one CSV where each row has a **job description text** and a **category / job title**.
Good size: 2,000+ rows, 5-30 categories, 100+ rows per category, English.

1. Create a free account on kaggle.com and search for "job description dataset".
2. Choose a dataset that has a description column and a title/category column. Check its licence and whether it is real or synthetic.
3. Download the zip, extract the CSV, and put it in this folder (`datasets/`).
4. See its columns (from the project root):
   `python scripts/train_models.py --data datasets/FILE.csv --show-columns`
5. Train (from the project root, venv active). Column names are guessed; pass them if the guess fails:
   `python scripts/train_models.py --data datasets/FILE.csv`
   `python scripts/train_models.py --data datasets/FILE.csv --text-col "Job Description" --label-col "Role"`
   Large files are handled by keeping the 25 most frequent classes and up to 2,000 rows per class
   (change with `--top-classes` and `--max-per-class`).
6. Results are printed and saved in `backend/app/ml/models/`: `role_classifier.joblib`, `role_classifier_metrics.json`,
   `role_classifier_confusion_matrix.png`. Restart the backend; the dashboard now shows the real metrics.

**Report honestly:** write down the dataset name, link, size, number of classes and whether it is synthetic. Quote only the numbers in `role_classifier_metrics.json`.

## 2. Human-labelled relevance data (for the semantic vs TF-IDF comparison)
1. Collect 10+ resumes and 3+ job descriptions as `.txt` files (use synthetic or consented data only).
2. `python scripts/make_relevance_sheet.py --resumes <folder> --jobs <folder> --out datasets/relevance_labels.csv`
3. Team members fill the empty `relevance` column by hand: 0 = not relevant, 1 = partly, 2 = highly relevant.
4. Install the optional model package once: `pip install -r backend/requirements-ml.txt`
5. From `backend/`: `python -m app.ml.evaluation.ranking --labels ../datasets/relevance_labels.csv`
   Output: Precision@1/3, NDCG@1/3, MRR for TF-IDF and the semantic model (saved to `matching_evaluation.json`).

## 3. Optional: threshold calibration
Create a CSV with columns `phrase, evidence_text, label` (label 1 = the text really shows that skill, 0 = not), labelled by hand, then
`python -m app.ml.evaluation.threshold --labels FILE.csv` and set `SEMANTIC_THRESHOLD` in `backend/app/services/matcher.py`.

## Sample data
`data/samples/` holds synthetic resumes and job descriptions for testing (regenerate with `python scripts/make_samples.py`).
