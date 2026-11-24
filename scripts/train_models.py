"""Train the job-role classifier. Run from the project root:

    python scripts/train_models.py --data datasets/YOUR_FILE.csv
    python scripts/train_models.py --data datasets/YOUR_FILE.csv --text-col "Job Description" --label-col "Role"
    python scripts/train_models.py --data datasets/YOUR_FILE.csv --show-columns

Outputs (in backend/app/ml/models): role_classifier.joblib, role_classifier_metrics.json, confusion matrix PNG.
"""
import sys
from pathlib import Path

backend = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(backend))

from app.ml.training.train_role_classifier import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
