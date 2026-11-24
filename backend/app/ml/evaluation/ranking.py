"""Ranking metrics and the TF-IDF vs semantic comparison on HUMAN-labelled resume-job pairs.

Input CSV columns: job_id, job_text, resume_id, resume_text, relevance
relevance is a human label: 0 = not relevant, 1 = partly relevant, 2 = highly relevant.
Rows with an empty relevance are rejected: no labels are ever invented.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

REQUIRED = ["job_id", "job_text", "resume_id", "resume_text", "relevance"]


def precision_at_k(rels_in_rank_order, k: int, threshold: int = 1) -> float:
    top = list(rels_in_rank_order)[:k]
    return sum(1 for r in top if r >= threshold) / k if k > 0 else 0.0


def dcg(rels, k):
    return sum((2 ** r - 1) / math.log2(i + 2) for i, r in enumerate(list(rels)[:k]))


def ndcg_at_k(rels_in_rank_order, k: int) -> float:
    ideal = dcg(sorted(rels_in_rank_order, reverse=True), k)
    return dcg(rels_in_rank_order, k) / ideal if ideal > 0 else 0.0


def reciprocal_rank(rels_in_rank_order, threshold: int = 1) -> float:
    for i, r in enumerate(rels_in_rank_order, 1):
        if r >= threshold:
            return 1.0 / i
    return 0.0


def tfidf_scores(job_text: str, resumes: list[str]) -> list[float]:
    m = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True).fit_transform([job_text] + resumes)
    return cosine_similarity(m[0], m[1:])[0].tolist()


def semantic_scores(job_text: str, resumes: list[str], model) -> list[float]:
    v = model.encode([job_text[:2000]] + [r[:2000] for r in resumes], normalize_embeddings=True)
    return (v[1:] @ v[0]).tolist()


def evaluate(df: pd.DataFrame, scorers: dict, ks=(1, 3)) -> dict:
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    if df["relevance"].isna().any():
        raise ValueError("Some rows have no human relevance label. Fill every label (0/1/2) before evaluating.")
    if not df["relevance"].isin([0, 1, 2]).all():
        raise ValueError("relevance must be 0, 1 or 2.")
    out = {}
    for name, fn in scorers.items():
        per = {f"P@{k}": [] for k in ks} | {f"NDCG@{k}": [] for k in ks} | {"MRR": []}
        for _, g in df.groupby("job_id"):
            if len(g) < 2:
                continue
            scores = fn(g["job_text"].iloc[0], g["resume_text"].tolist())
            rels = g["relevance"].to_numpy()[np.argsort(scores)[::-1]].tolist()
            for k in ks:
                per[f"P@{k}"].append(precision_at_k(rels, min(k, len(rels))))
                per[f"NDCG@{k}"].append(ndcg_at_k(rels, min(k, len(rels))))
            per["MRR"].append(reciprocal_rank(rels))
        out[name] = {m: round(float(np.mean(v)), 4) if v else None for m, v in per.items()} | {"queries": len(per["MRR"])}
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--labels", required=True)
    ap.add_argument("--model", default="all-MiniLM-L6-v2")
    a = ap.parse_args(argv)
    df = pd.read_csv(a.labels)
    scorers = {"tfidf_cosine": tfidf_scores}
    try:
        from sentence_transformers import SentenceTransformer
        st = SentenceTransformer(a.model)
        scorers["semantic_" + a.model] = lambda j, rs: semantic_scores(j, rs, st)
    except Exception as e:
        print(f"NOTE: semantic model unavailable ({type(e).__name__}); evaluating TF-IDF only. "
              "Run: pip install -r requirements-ml.txt (needs internet once).", file=sys.stderr)
    try:
        res = evaluate(df, scorers)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    print(json.dumps(res, indent=2))
    out = Path(__file__).resolve().parents[1] / "models" / "matching_evaluation.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"pairs": len(df), "results": res}, indent=2))
    print(f"Saved to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
