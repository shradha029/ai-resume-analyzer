import pandas as pd
import pytest

from app.ml.evaluation.ranking import evaluate, ndcg_at_k, precision_at_k, reciprocal_rank, tfidf_scores
from app.ml.evaluation.threshold import sweep


def test_precision_ndcg_mrr_hand_calculated():
    rels = [2, 0, 1, 0]                                       # relevance of resumes in ranked order
    assert precision_at_k(rels, 1) == 1.0 and precision_at_k(rels, 2) == 0.5 and precision_at_k(rels, 3) == pytest.approx(2 / 3)
    assert reciprocal_rank([0, 0, 1]) == pytest.approx(1 / 3) and reciprocal_rank([0, 0]) == 0.0
    assert ndcg_at_k([2, 1, 0], 3) == pytest.approx(1.0)       # already ideal
    ideal = 3 / 1 + 1 / 1.5849625007211562
    actual = 0 + 1 / 1.5849625007211562 + 3 / 2
    assert ndcg_at_k([0, 1, 2], 3) == pytest.approx(actual / ideal, abs=1e-6)
    assert ndcg_at_k([0, 0, 0], 3) == 0.0


def labelled_df():
    jobs = {"j1": "python pandas machine learning engineer", "j2": "react javascript frontend developer"}
    resumes = {"r1": "python machine learning pandas projects", "r2": "react html css javascript portfolio", "r3": "cooking recipes and travel blogging"}
    rel = {("j1", "r1"): 2, ("j1", "r2"): 0, ("j1", "r3"): 0, ("j2", "r1"): 0, ("j2", "r2"): 2, ("j2", "r3"): 0}
    return pd.DataFrame([{"job_id": j, "job_text": jobs[j], "resume_id": r, "resume_text": resumes[r], "relevance": v} for (j, r), v in rel.items()])


def test_tfidf_ranks_the_relevant_resume_first():
    res = evaluate(labelled_df(), {"tfidf_cosine": tfidf_scores})
    r = res["tfidf_cosine"]
    assert r["P@1"] == 1.0 and r["MRR"] == 1.0 and r["NDCG@3"] == 1.0 and r["queries"] == 2


def test_evaluate_compares_multiple_scorers_and_detects_a_bad_one():
    bad = lambda job, resumes: [-len(r) for r in resumes]       # noqa: E731  (ignores content)
    res = evaluate(labelled_df(), {"tfidf_cosine": tfidf_scores, "bad": bad})
    assert res["tfidf_cosine"]["MRR"] >= res["bad"]["MRR"]


def test_unlabelled_or_invalid_rows_are_rejected():
    df = labelled_df()
    df.loc[0, "relevance"] = None
    with pytest.raises(ValueError, match="no human relevance label"):
        evaluate(df, {"t": tfidf_scores})
    df = labelled_df()
    df.loc[0, "relevance"] = 5
    with pytest.raises(ValueError, match="0, 1 or 2"):
        evaluate(df, {"t": tfidf_scores})
    with pytest.raises(ValueError, match="Missing columns"):
        evaluate(pd.DataFrame({"a": [1]}), {"t": tfidf_scores})


def test_threshold_sweep_finds_the_separating_threshold():
    sims = [0.9, 0.8, 0.75, 0.4, 0.3, 0.2]
    labels = [1, 1, 1, 0, 0, 0]
    rows, best = sweep(sims, labels)
    assert best["f1"] == 1.0 and 0.45 <= best["threshold"] <= 0.75
    low = next(r for r in rows if r["threshold"] == 0.3)
    assert low["recall"] == 1.0 and low["precision"] < 1.0
