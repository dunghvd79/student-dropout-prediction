"""Unit test cho Bước 14 – kiểm tra schema và dựng bảng predictions (không cần Docker / MLflow)."""

import warnings
from datetime import datetime

import numpy as np
import pandas as pd
import pytest

from src.ml.explain import explain
from src.ml.predict import NO_REASON, build_predictions, check_schema
from src.ml.split import load_spec
from src.ml.train import build_pipeline
from tests.test_explain import make_X


@pytest.fixture(scope="module")
def spec():
    return load_spec()


@pytest.fixture(scope="module")
def model(spec):
    X = make_X(spec, 800, 0)
    y = (np.random.RandomState(1).rand(len(X)) < 1 / (1 + np.exp(2 + X["Sem_GPA"] - X["First_Generation"]))).astype(int)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return build_pipeline("logreg", spec, imbalance="none", y_train=y).fit(X, y), X


def test_schema_ok(spec, model):
    m, _ = model
    assert check_schema(make_X(spec, 50, 3), spec, m) == []


def test_schema_detects_missing_extra_and_order(spec, model):
    m, _ = model
    X = make_X(spec, 50, 3)
    assert any("thiếu ['Sem_GPA']" in e for e in check_schema(X.drop(columns="Sem_GPA"), spec, m))
    assert any("thừa ['Thua']" in e for e in check_schema(X.assign(Thua=1), spec, m))
    cols = list(X.columns)
    cols[0], cols[1] = cols[1], cols[0]
    assert any("sai thứ tự" in e for e in check_schema(X[cols], spec, m))


def test_schema_detects_types_and_unseen_categories(spec, model):
    m, _ = model
    X = make_X(spec, 50, 3)
    bad = X.assign(Sem_GPA=X["Sem_GPA"].astype(str), Scholarship=2, Housing_Status="Ký túc xá mới")
    errors = check_schema(bad, spec, m)
    assert any("Sem_GPA phải là kiểu số" in e for e in errors)
    assert any("Scholarship có giá trị ngoài 0/1" in e for e in errors)
    assert any("Housing_Status có nhóm mô hình chưa thấy" in e for e in errors)


def test_schema_detects_spec_changed_after_training(spec, model):
    m, _ = model
    changed = {**spec, "features": spec["features"][:-1]}
    X = make_X(spec, 20, 3)[changed["features"]]
    assert any("khác danh sách cột lúc huấn luyện" in e for e in check_schema(X, changed, m))


def test_build_predictions_matches_table(spec, model):
    m, X_bg = model
    X = make_X(spec, 120, 4)
    keys = pd.DataFrame({"Student_ID": [f"S{i}" for i in range(len(X))], "Semester": X["Semester"]})
    ex = explain(m, X, X_bg, spec)
    proba = m.predict_proba(X)[:, 1]
    t = {"medium": float(np.quantile(proba, 0.5)), "high": float(np.quantile(proba, 0.9))}
    out = build_predictions(keys, X, ex.groups, proba, t, "r1", "2", datetime(2026, 1, 1))
    assert list(out.columns) == ["run_id", "run_date", "model_version", "student_id", "semester", "risk_score",
                                 "risk_level", "top_reason_1", "top_reason_2", "top_reason_3"]
    assert len(out) == len(X) and out["student_id"].is_unique
    assert out["risk_level"].value_counts()["Cao"] == (proba >= t["high"]).sum()
    assert out["top_reason_1"].notna().all()                      # mọi sinh viên có ít nhất một dòng lý do
    assert out["risk_score"].between(0, 1).all()


def test_student_without_positive_reason_gets_placeholder(spec, model):
    m, X_bg = model
    X = make_X(spec, 1, 5)
    keys = pd.DataFrame({"Student_ID": ["S0"], "Semester": [1]})
    groups = explain(m, X, X_bg, spec).groups * 0 - 1           # mọi nhóm đều kéo rủi ro xuống
    out = build_predictions(keys, X, groups, np.array([0.01]), {"medium": 0.1, "high": 0.3}, "r", "2", datetime.now())
    assert out.loc[0, "top_reason_1"] == NO_REASON
    assert out.loc[0, ["top_reason_2", "top_reason_3"]].isna().all()
    assert out.loc[0, "risk_level"] == "Thấp"
