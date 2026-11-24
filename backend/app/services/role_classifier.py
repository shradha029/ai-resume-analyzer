"""Loads the trained job-role classifier (if the team has trained one) and predicts a category for a job description.
If no model file exists, everything returns None / "not trained": nothing is faked."""
import json
import logging
from pathlib import Path

import joblib
import numpy as np

from app.ml.training.train_role_classifier import METRICS_PATH, MODEL_PATH

logger = logging.getLogger(__name__)
_cache: dict = {}


def reset_cache() -> None:
    _cache.clear()


def _paths(model_path=None, metrics_path=None):
    return Path(model_path or MODEL_PATH), Path(metrics_path or METRICS_PATH)


def load(model_path=None, metrics_path=None):
    key = (str(model_path), str(metrics_path))
    if key in _cache:
        return _cache[key]
    mp, jp = _paths(model_path, metrics_path)
    result = None
    if mp.exists():
        try:
            model = joblib.load(mp)
            metrics = json.loads(jp.read_text(encoding="utf-8")) if jp.exists() else None
            result = (model, metrics)
        except Exception as exc:
            logger.warning("Could not load role classifier: %s", type(exc).__name__)
    _cache[key] = result
    return result


def info(model_path=None, metrics_path=None) -> dict:
    loaded = load(model_path, metrics_path)
    if not loaded:
        return {"trained": False, "message": "Role classifier is not trained yet. See datasets/README.md.", "metrics": None}
    return {"trained": True, "message": "ok", "metrics": loaded[1]}


def predict(text: str, top_k: int = 3, model_path=None, metrics_path=None) -> dict | None:
    loaded = load(model_path, metrics_path)
    if not loaded or not text or not text.strip():
        return None
    model, metrics = loaded
    clf = model.named_steps["clf"]
    X = model.named_steps["tfidf"].transform([text])
    if hasattr(clf, "predict_proba"):
        scores, kind = clf.predict_proba(X)[0], "probability"
    else:                                               # LinearSVC: softmax of margins (relative score, not a probability)
        d = clf.decision_function(X)[0]
        e = np.exp(d - d.max())
        scores, kind = e / e.sum(), "relative_score"
    order = np.argsort(scores)[::-1][:top_k]
    return {
        "label": str(clf.classes_[order[0]]),
        "top": [{"label": str(clf.classes_[i]), "score": round(float(scores[i]), 3)} for i in order],
        "score_type": kind,
        "model": (metrics or {}).get("selected_model"),
        "test_f1_macro": ((metrics or {}).get("test") or {}).get("f1_macro"),
    }
