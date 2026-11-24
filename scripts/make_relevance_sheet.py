"""Build the human-labelling sheet for the semantic-vs-TF-IDF evaluation.

Put plain-text resumes in a folder (resumes/*.txt) and plain-text job descriptions in another (jobs/*.txt),
then run:
    python scripts/make_relevance_sheet.py --resumes path/to/resumes --jobs path/to/jobs --out datasets/relevance_labels.csv
Every resume x job pair becomes a row with an EMPTY `relevance` column. Team members fill it in by hand:
    0 = not relevant, 1 = partly relevant, 2 = highly relevant.
Then run (from backend/):  python -m app.ml.evaluation.ranking --labels ../datasets/relevance_labels.csv
"""
import argparse
import csv
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--resumes", required=True)
ap.add_argument("--jobs", required=True)
ap.add_argument("--out", default="datasets/relevance_labels.csv")
a = ap.parse_args()

resumes = sorted(Path(a.resumes).glob("*.txt"))
jobs = sorted(Path(a.jobs).glob("*.txt"))
if len(resumes) < 3 or not jobs:
    raise SystemExit("Need at least 3 resumes and 1 job description to rank.")
Path(a.out).parent.mkdir(parents=True, exist_ok=True)
with open(a.out, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["job_id", "job_text", "resume_id", "resume_text", "relevance"])
    for j in jobs:
        for r in resumes:
            w.writerow([j.stem, j.read_text(encoding="utf-8"), r.stem, r.read_text(encoding="utf-8"), ""])
print(f"Wrote {len(jobs) * len(resumes)} pairs to {a.out}. Now fill the 'relevance' column by hand (0/1/2).")
