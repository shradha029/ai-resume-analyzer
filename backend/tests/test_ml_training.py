import json

import joblib
import numpy as np
import pandas as pd
import pytest

from app.ml.preprocessing.text import clean_text
from app.ml.training import train_role_classifier as trc
from app.services import role_classifier
from tests.ml_data import make_df


@pytest.fixture(scope="module")
def trained(tmp_path_factory):
    d = tmp_path_factory.mktemp("models")
    metrics = trc.train(make_df(), cv=3, model_dir=d, source="synthetic-test")
    return d, metrics


def test_preprocessing():
    assert clean_text("<p>Hello   WORLD</p> https://x.com/a") == "hello world"
    assert clean_text(None) == "" and clean_text(float("nan")) == ""
    assert clean_text("C++ and Node.js") == "c++ and node.js"


def test_three_models_compared_and_best_selected(trained):
    _, m = trained
    assert [r["model"] for r in m["comparison"]] == trc.MODELS
    best = max(m["comparison"], key=lambda r: r["cv_macro_f1_mean"])["model"]
    assert m["selected_model"] == best
    assert m["split"]["train_rows"] + m["split"]["test_rows"] == m["dataset"]["rows_used"] == 240


def test_reported_metrics_are_real_and_consistent(trained):
    _, m = trained
    t = m["test"]
    for k in ("accuracy", "precision_macro", "recall_macro", "f1_macro"):
        assert 0 <= t[k] <= 1
    assert t["accuracy"] > 0.8                                   # synthetic data is easy; only a sanity check
    cm = np.array(t["confusion_matrix"])
    assert cm.shape == (4, 4) and cm.sum() == m["split"]["test_rows"]
    assert cm.trace() / cm.sum() == pytest.approx(t["accuracy"], abs=1e-3)
    assert sum(v["support"] for v in t["per_class"].values()) == m["split"]["test_rows"]


def test_artifacts_saved_and_reloadable(trained):
    d, m = trained
    assert (d / "role_classifier.joblib").exists() and (d / "role_classifier_metrics.json").exists()
    assert json.loads((d / "role_classifier_metrics.json").read_text())["selected_model"] == m["selected_model"]
    assert (d / "role_classifier_confusion_matrix.png").exists()
    model = joblib.load(d / "role_classifier.joblib")
    assert model.predict(["docker kubernetes jenkins terraform deployment pipeline"])[0] == "DevOps"


def test_preprocessing_is_part_of_the_saved_pipeline(trained):
    d, _ = trained
    model = joblib.load(d / "role_classifier.joblib")
    assert model.named_steps["tfidf"].preprocessor is clean_text
    a = model.predict(["<b>REACT</b> javascript css html frontend"])[0]
    b = model.predict(["react javascript css html frontend"])[0]
    assert a == b == "Web Development"


def test_service_predicts_and_reports_model_info(trained, monkeypatch):
    d, m = trained
    monkeypatch.setattr(role_classifier, "MODEL_PATH", d / "role_classifier.joblib")
    monkeypatch.setattr(role_classifier, "METRICS_PATH", d / "role_classifier_metrics.json")
    role_classifier.reset_cache()
    p = role_classifier.predict("java spring hibernate maven microservices junit backend")
    assert p["label"] == "Java Developer" and len(p["top"]) == 3
    assert p["score_type"] in ("probability", "relative_score") and p["test_f1_macro"] == m["test"]["f1_macro"]
    assert role_classifier.info()["trained"] is True
    assert role_classifier.predict("") is None and role_classifier.predict("   ") is None
    role_classifier.reset_cache()


def test_untrained_state_is_reported_honestly(tmp_path, monkeypatch):
    monkeypatch.setattr(role_classifier, "MODEL_PATH", tmp_path / "missing.joblib")
    monkeypatch.setattr(role_classifier, "METRICS_PATH", tmp_path / "missing.json")
    role_classifier.reset_cache()
    assert role_classifier.predict("python pandas") is None
    i = role_classifier.info()
    assert i["trained"] is False and i["metrics"] is None
    role_classifier.reset_cache()


def test_training_edge_cases():
    df = make_df(20)
    with pytest.raises(trc.DatasetError):
        trc.train(df[df["label"] == "DevOps"], save=False)                     # one class
    with pytest.raises(trc.DatasetError):
        trc.train(pd.concat([df[df["label"] != "DevOps"], df[df["label"] == "DevOps"].head(2)]), save=False)   # tiny class
    with pytest.raises(trc.DatasetError):
        trc.train(pd.DataFrame({"a": [1]}), save=False)


def test_load_dataset(tmp_path):
    rows = [{"Job Description": f"{c} role text with enough characters to pass the filter {i}", "Role": c}
            for c in ("A", "B") for i in range(60)]
    rows += [{"Job Description": "rare class text that is long enough to be kept here", "Role": "Rare"}] * 3
    rows += [{"Job Description": None, "Role": "A"}, {"Job Description": "short", "Role": "B"}]
    f = tmp_path / "jobs.csv"
    pd.DataFrame(rows).to_csv(f, index=False)
    df, info = trc.load_dataset(f, min_count=50, max_per_class=40)
    assert info == {"text_col": "Job Description", "label_col": "Role", "classes_available": 2}
    assert set(df["label"]) == {"A", "B"} and df["label"].value_counts().max() == 40
    with pytest.raises(trc.DatasetError, match="not found"):
        trc.load_dataset(f, text_col="nope")
    with pytest.raises(trc.DatasetError, match="File not found"):
        trc.load_dataset(tmp_path / "missing.csv")
    pd.DataFrame({"x": ["a long enough text here to count as something"] * 5, "y": ["z"] * 5}).to_csv(tmp_path / "w.csv", index=False)
    with pytest.raises(trc.DatasetError, match="guess"):
        trc.load_dataset(tmp_path / "w.csv")


def test_cli_show_columns_and_missing_file(tmp_path, capsys):
    f = tmp_path / "x.csv"
    pd.DataFrame({"Job Description": ["a"], "Category": ["b"]}).to_csv(f, index=False)
    assert trc.main(["--data", str(f), "--show-columns"]) == 0
    assert "Job Description" in capsys.readouterr().out
    assert trc.main(["--data", str(tmp_path / "none.csv")]) == 1
