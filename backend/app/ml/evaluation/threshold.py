"""Calibrate the semantic-similarity threshold from HUMAN-labelled (phrase, evidence_text, label) pairs.

CSV columns: phrase, evidence_text, label   (label 1 = the evidence really shows the skill, 0 = it does not)
Prints precision/recall/F1 for a range of thresholds and the best F1 threshold. The suggested value is then
set manually as SEMANTIC_THRESHOLD in app/services/matcher.py.
"""
import argparse
import sys

import numpy as np
import pandas as pd


def sweep(sims, labels, thresholds=None):
    sims, labels = np.asarray(sims, dtype=float), np.asarray(labels, dtype=int)
    rows = []
    for t in (thresholds if thresholds is not None else np.arange(0.30, 0.91, 0.05)):
        pred = sims >= t
        tp = int(((pred == 1) & (labels == 1)).sum())
        fp = int(((pred == 1) & (labels == 0)).sum())
        fn = int(((pred == 0) & (labels == 1)).sum())
        p = tp / (tp + fp) if tp + fp else 0.0
        r = tp / (tp + fn) if tp + fn else 0.0
        f = 2 * p * r / (p + r) if p + r else 0.0
        rows.append({"threshold": round(float(t), 2), "precision": round(p, 3), "recall": round(r, 3), "f1": round(f, 3)})
    return rows, max(rows, key=lambda x: x["f1"])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--labels", required=True)
    ap.add_argument("--model", default="all-MiniLM-L6-v2")
    a = ap.parse_args(argv)
    df = pd.read_csv(a.labels)
    if df["label"].isna().any() or not df["label"].isin([0, 1]).all():
        print("ERROR: every row needs a human label of 0 or 1.", file=sys.stderr)
        return 1
    from sentence_transformers import SentenceTransformer
    m = SentenceTransformer(a.model)
    q = m.encode(df["phrase"].tolist(), normalize_embeddings=True)
    e = m.encode(df["evidence_text"].tolist(), normalize_embeddings=True)
    rows, best = sweep((q * e).sum(axis=1), df["label"])
    for r in rows:
        print(r)
    print("Best F1 threshold:", best)
    return 0


if __name__ == "__main__":
    sys.exit(main())
