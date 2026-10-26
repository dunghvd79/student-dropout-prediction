"""Unit test cho Bước 12 – chọn ngưỡng, mức rủi ro, chỉ số (không cần Docker)."""

import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import precision_recall_curve

from src.ml.evaluate import choose_thresholds, fairness_table, level_table, metrics_at, risk_level


@pytest.fixture(scope="module")
def scores():
    rng = np.random.RandomState(0)
    y = (rng.rand(5000) < 0.1).astype(int)
    p = np.clip(0.08 + 0.15 * y + rng.normal(0, 0.08, len(y)), 0.001, 0.999)  # tín hiệu yếu như dữ liệu thật
    return y, p


def test_thresholds_follow_policy(scores):
    y, p = scores
    t = choose_thresholds(y, p, target_recall=0.8, high_precision=0.5)
    assert metrics_at(y, p, t["medium"])["recall"] >= 0.8
    assert metrics_at(y, p, t["high"])["precision"] >= 0.5
    assert t["high"] > t["medium"]
    # medium là ngưỡng LỚN NHẤT còn đạt Recall: nâng lên một bậc thì Recall rớt dưới mục tiêu
    _, rec, thr = precision_recall_curve(y, p)
    above = thr[thr > t["medium"]]
    assert metrics_at(y, p, above.min())["recall"] < 0.8


def test_impossible_policy_raises(scores):
    y, p = scores
    with pytest.raises(ValueError):
        choose_thresholds(y, p, target_recall=0.8, high_precision=1.01)


def test_risk_levels_and_table(scores):
    y, p = scores
    t = {"medium": 0.2, "high": 0.4}
    levels = risk_level(np.array([0.1, 0.2, 0.39, 0.4, 0.9]), t)
    assert levels.tolist() == ["Thấp", "Trung bình", "Trung bình", "Cao", "Cao"]
    table = level_table(y, p, t)
    assert list(table.index) == ["Thấp", "Trung bình", "Cao"]
    assert table["so_dong"].sum() == len(y) and table["ty_le_ca_bo_hoc_bat_duoc"].sum() == pytest.approx(1)
    assert table.loc["Cao", "ty_le_bo_hoc_thuc"] > table.loc["Thấp", "ty_le_bo_hoc_thuc"]


def test_metrics_at_counts(scores):
    y, p = scores
    m = metrics_at(y, p, 0.3)
    assert m["tp"] + m["fp"] + m["fn"] + m["tn"] == len(y)
    assert m["recall"] == pytest.approx(m["tp"] / (m["tp"] + m["fn"]))


def test_fairness_table_covers_groups(scores):
    y, p = scores
    n = len(y)
    rng = np.random.RandomState(1)
    X = pd.DataFrame({
        "Semester": rng.randint(1, 6, n), "Gender": rng.choice(["Female", "Male"], n),
        "First_Generation": rng.randint(0, 2, n), "Housing_Status": rng.choice(["On-Campus", "With Parents"], n),
        "Scholarship": rng.randint(0, 2, n),
    })
    fair = fairness_table(X, y, p, 0.2)
    assert set(fair["chieu"]) == {"Học kỳ", "Gender", "First_Generation", "Housing_Status", "Scholarship"}
    assert fair.groupby("chieu")["so_dong"].sum().eq(n).all()


def test_policy_where_high_not_above_medium_raises():
    """Tín hiệu quá mạnh: ngưỡng đạt Precision 0,5 không còn cao hơn ngưỡng đạt Recall 0,8 → báo lỗi chứ không đảo mức."""
    rng = np.random.RandomState(0)
    y = (rng.rand(3000) < 0.1).astype(int)
    p = np.clip(0.05 + 0.6 * y + rng.normal(0, 0.05, len(y)), 0.001, 0.999)
    with pytest.raises(ValueError):
        choose_thresholds(y, p, target_recall=0.8, high_precision=0.5)
