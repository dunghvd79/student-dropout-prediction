"""Unit test cho Bước 11 – CV, chỉ số, ablation (không cần Docker / MLflow; dữ liệu tổng hợp)."""

import numpy as np
import pandas as pd
import pytest

from src.ml.experiments import Tracker, cross_validate, fold_metrics, subset_spec
from tests.test_train_pipeline import SPEC, make_xy


@pytest.fixture(scope="module")
def data():
    X, y = make_xy(800, 3)
    groups = pd.Series([f"S{i // 4}" for i in range(len(X))])  # mỗi "sinh viên" 4 dòng liên tiếp
    return X, y, groups


def test_fold_metrics_known_values():
    y = np.array([0, 0, 1, 1])
    p = np.array([0.1, 0.6, 0.4, 0.9])
    m = fold_metrics(y, p)
    assert m["roc_auc"] == pytest.approx(0.75)
    assert m["precision"] == pytest.approx(0.5) and m["recall"] == pytest.approx(0.5)


def test_cross_validate_fills_every_oof_once(data):
    X, y, groups = data
    r = cross_validate("logreg", X, y, groups, SPEC)
    assert not np.isnan(r.oof).any() and len(r.oof) == len(y)
    assert len(r.folds) == 5
    s = r.summary()
    assert 0 <= s["pr_auc_mean"] <= 1 and s["pr_auc_std"] >= 0


def test_cross_validate_beats_dummy(data):
    X, y, groups = data
    dummy = cross_validate("dummy", X, y, groups, SPEC).summary()["pr_auc_mean"]
    logreg = cross_validate("logreg", X, y, groups, SPEC).summary()["pr_auc_mean"]
    assert logreg > dummy


def test_on_fold_callback_called_per_fold(data):
    X, y, groups = data
    seen = []
    cross_validate("logreg", X, y, groups, SPEC, on_fold=lambda k, v: seen.append(k))
    assert seen == [0, 1, 2, 3, 4]


def test_subset_spec_keeps_only_selected_features():
    sub = subset_spec(SPEC, ["Sem_GPA", "Scholarship", "Gender"])
    assert sub["features"] == ["Sem_GPA", "Scholarship", "Gender"]
    assert sub["numeric"] == ["Sem_GPA"] and sub["binary"] == ["Scholarship"] and sub["categorical"] == ["Gender"]


def test_tracker_disabled_is_noop(data):
    X, y, groups = data
    r = cross_validate("dummy", X, y, groups, SPEC)
    assert Tracker(enabled=False).log("compare", r) is None
