"""Train and compare job-role classifiers on a labelled CSV of job descriptions.

Models compared (all on TF-IDF features): Logistic Regression, Multinomial Naive Bayes, Linear SVM.
Selection: best mean macro-F1 over stratified k-fold cross-validation on the TRAINING split.
Final numbers are reported on a held-out TEST split that is never used for selection.

Usage (from the backend folder):
    python -m app.ml.training.train_role_classifier --data ../datasets/FILE.csv
    python -m app.ml.training.train_role_classifier --data ../datasets/FILE.csv --text-col "Job Description" --label-col "Role"
    python -m app.ml.training.train_role_classifier --data ../datasets/FILE.csv --show-columns
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support
from sklearn.model_selection import StratifiedKFold, cross_validate, train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

from app.ml.preprocessing.text import TOKEN_PATTERN, clean_text

MODEL_DIR = Path(__file__).resolve().parents[1] / "models"
MODEL_PATH = MODEL_DIR / "role_classifier.joblib"
METRICS_PATH = MODEL_DIR / "role_classifier_metrics.json"
TEXT_GUESSES = ["job description", "job_description", "jobdescription", "description", "text", "resume_str", "details"]
LABEL_GUESSES = ["category", "role", "job title", "job_title", "jobtitle", "title", "label", "position"]


class DatasetError(ValueError):
    pass


def guess_column(columns, guesses, what):
    low = {c.lower().strip(): c for c in columns}
    for g in guesses:
        if g in low:
            return low[g]
    raise DatasetError(f"Could not guess the {what} column. Columns are: {list(columns)}. "
                       f"Pass it explicitly with --{'text' if what == 'text' else 'label'}-col.")


def load_dataset(path, text_col=None, label_col=None, max_per_class=2000, top_classes=25, min_count=50, seed=42):
    """Memory-safe loader: counts labels first, keeps the top classes, then samples up to max_per_class rows each."""
    path = Path(path)
    if not path.exists():
        raise DatasetError(f"File not found: {path}")
    header = pd.read_csv(path, nrows=0, encoding="utf-8", encoding_errors="ignore").columns
    text_col = text_col or guess_column(header, TEXT_GUESSES, "text")
    label_col = label_col or guess_column(header, LABEL_GUESSES, "label")
    for c in (text_col, label_col):
        if c not in header:
            raise DatasetError(f"Column '{c}' not found. Columns are: {list(header)}")

    def chunks(cols):
        return pd.read_csv(path, usecols=cols, chunksize=50000, encoding="utf-8", encoding_errors="ignore")

    counts = pd.Series(dtype="int64")
    for ch in chunks([label_col]):
        counts = counts.add(ch[label_col].dropna().astype(str).str.strip().value_counts(), fill_value=0)
    counts = counts[counts >= min_count].sort_values(ascending=False).head(top_classes)
    if len(counts) < 2:
        raise DatasetError(f"Need at least 2 classes with {min_count}+ rows; found {len(counts)}.")

    keep, have = [], {c: 0 for c in counts.index}
    for ch in chunks([text_col, label_col]):
        ch = ch.dropna()
        ch[label_col] = ch[label_col].astype(str).str.strip()
        ch = ch[ch[label_col].isin(have) & (ch[text_col].astype(str).str.len() > 30)].sample(frac=1, random_state=seed)
        for label, g in ch.groupby(label_col):
            take = max_per_class - have[label]
            if take > 0:
                keep.append(g.head(take))
                have[label] += min(take, len(g))
    df = pd.concat(keep, ignore_index=True).rename(columns={text_col: "text", label_col: "label"})
    return df[["text", "label"]], {"text_col": text_col, "label_col": label_col, "classes_available": int((counts > 0).sum())}


def build_pipeline(model_name: str) -> Pipeline:
    vec = TfidfVectorizer(preprocessor=clean_text, token_pattern=TOKEN_PATTERN, stop_words="english",
                          ngram_range=(1, 2), min_df=2, max_df=0.9, max_features=50000, sublinear_tf=True)
    clf = {"logistic_regression": LogisticRegression(max_iter=300, C=5.0),
           "multinomial_nb": MultinomialNB(alpha=0.1),
           "linear_svm": LinearSVC(C=1.0)}[model_name]
    return Pipeline([("tfidf", vec), ("clf", clf)])


MODELS = ["logistic_regression", "multinomial_nb", "linear_svm"]


def train(df: pd.DataFrame, test_size=0.2, cv=3, seed=42, model_dir=MODEL_DIR, save=True, source="unknown") -> dict:
    if not {"text", "label"} <= set(df.columns):
        raise DatasetError("DataFrame needs 'text' and 'label' columns.")
    df = df.dropna(subset=["text", "label"]).copy()
    counts = df["label"].value_counts()
    if len(counts) < 2:
        raise DatasetError("Need at least two classes to train a classifier.")
    if counts.min() < max(cv, 2) + 1:
        raise DatasetError(f"Every class needs more than {max(cv, 2)} rows; smallest class has {counts.min()}.")

    X_tr, X_te, y_tr, y_te = train_test_split(df["text"], df["label"], test_size=test_size, stratify=df["label"], random_state=seed)
    skf = StratifiedKFold(n_splits=cv, shuffle=True, random_state=seed)
    comparison = []
    for name in MODELS:
        res = cross_validate(build_pipeline(name), X_tr, y_tr, cv=skf, scoring=["f1_macro", "accuracy"], n_jobs=1)
        comparison.append({"model": name, "cv_macro_f1_mean": round(float(res["test_f1_macro"].mean()), 4),
                           "cv_macro_f1_std": round(float(res["test_f1_macro"].std()), 4),
                           "cv_accuracy_mean": round(float(res["test_accuracy"].mean()), 4)})
    best = max(comparison, key=lambda r: r["cv_macro_f1_mean"])["model"]

    model = build_pipeline(best).fit(X_tr, y_tr)
    pred = model.predict(X_te)
    labels = sorted(df["label"].unique())
    p, r, f, _ = precision_recall_fscore_support(y_te, pred, labels=labels, zero_division=0)
    pm, rm, fm, _ = precision_recall_fscore_support(y_te, pred, average="macro", zero_division=0)
    _, _, fw, _ = precision_recall_fscore_support(y_te, pred, average="weighted", zero_division=0)
    metrics = {
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dataset": {"source_file": source, "rows_used": int(len(df)), "n_classes": len(labels),
                    "class_counts": {k: int(v) for k, v in counts.items()}},
        "split": {"train_rows": int(len(X_tr)), "test_rows": int(len(X_te)), "test_size": test_size, "cv_folds": cv, "seed": seed},
        "comparison": comparison,
        "selected_model": best,
        "selection_rule": "highest mean macro-F1 in stratified cross-validation on the training split",
        "test": {"accuracy": round(float(accuracy_score(y_te, pred)), 4), "precision_macro": round(float(pm), 4),
                 "recall_macro": round(float(rm), 4), "f1_macro": round(float(fm), 4), "f1_weighted": round(float(fw), 4),
                 "per_class": {l: {"precision": round(float(p[i]), 4), "recall": round(float(r[i]), 4), "f1": round(float(f[i]), 4),
                                   "support": int((y_te == l).sum())} for i, l in enumerate(labels)},
                 "labels": labels, "confusion_matrix": confusion_matrix(y_te, pred, labels=labels).tolist()},
    }
    if save:
        model_dir = Path(model_dir)
        model_dir.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, model_dir / "role_classifier.joblib")
        (model_dir / "role_classifier_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        save_confusion_png(metrics, model_dir / "role_classifier_confusion_matrix.png")
    return metrics


def save_confusion_png(metrics: dict, path: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return
    labels, cm = metrics["test"]["labels"], np.array(metrics["test"]["confusion_matrix"])
    fig, ax = plt.subplots(figsize=(max(6, len(labels) * 0.6), max(5, len(labels) * 0.5)))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(len(labels)), labels, rotation=90, fontsize=7)
    ax.set_yticks(range(len(labels)), labels, fontsize=7)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")
    ax.set_title(f"Confusion matrix - {metrics['selected_model']} (test split)")
    fig.colorbar(im)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def print_report(m: dict) -> None:
    print(f"\nDataset: {m['dataset']['rows_used']} rows, {m['dataset']['n_classes']} classes  "
          f"(train {m['split']['train_rows']} / test {m['split']['test_rows']})")
    print("\nModel comparison (cross-validation on the training split):")
    for r in m["comparison"]:
        print(f"  {r['model']:<22} macro-F1 {r['cv_macro_f1_mean']:.4f} +/- {r['cv_macro_f1_std']:.4f}   accuracy {r['cv_accuracy_mean']:.4f}")
    t = m["test"]
    print(f"\nSelected: {m['selected_model']}\nHeld-out TEST results:")
    print(f"  accuracy {t['accuracy']:.4f} | precision(macro) {t['precision_macro']:.4f} | recall(macro) {t['recall_macro']:.4f} | F1(macro) {t['f1_macro']:.4f}")
    print(f"\nSaved to: {MODEL_DIR}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", required=True)
    ap.add_argument("--text-col")
    ap.add_argument("--label-col")
    ap.add_argument("--show-columns", action="store_true")
    ap.add_argument("--max-per-class", type=int, default=2000)
    ap.add_argument("--top-classes", type=int, default=25)
    ap.add_argument("--min-count", type=int, default=50)
    ap.add_argument("--test-size", type=float, default=0.2)
    ap.add_argument("--cv", type=int, default=3)
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args(argv)
    try:
        if a.show_columns:
            print(list(pd.read_csv(a.data, nrows=3, encoding="utf-8", encoding_errors="ignore").columns))
            return 0
        df, info = load_dataset(a.data, a.text_col, a.label_col, a.max_per_class, a.top_classes, a.min_count, a.seed)
        print(f"Using text column '{info['text_col']}' and label column '{info['label_col']}'; "
              f"{len(df)} rows, {df['label'].nunique()} classes. Training (this can take a few minutes)...")
        print_report(train(df, a.test_size, a.cv, a.seed, source=Path(a.data).name))
        return 0
    except DatasetError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
