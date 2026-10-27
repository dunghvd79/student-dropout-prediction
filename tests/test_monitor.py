"""Unit test cho Bước 16 – PSI, lỗi schema, hiệu năng trên nhãn mới, thứ tự pipeline (không cần Docker)."""

import numpy as np
import pandas as pd
import pytest

from src.core.schema import COLUMNS
from src.ops.monitor import performance_on_new_labels, psi, psi_level, schema_error_rate
from src.ops.run_pipeline import STEP_NAMES, plan


def test_psi_zero_for_same_distribution_and_grows_with_shift():
    rng = np.random.RandomState(0)
    train = rng.normal(2.8, 0.6, 20000)
    assert psi(train, rng.normal(2.8, 0.6, 5000)) < 0.01
    small, large = psi(train, rng.normal(2.95, 0.6, 5000)), psi(train, rng.normal(3.4, 0.6, 5000))
    assert 0 < small < large and large > 0.2


def test_psi_handles_discrete_values_missing_and_empty_bins():
    train = pd.Series([0, 0, 0, 1, 1, 2] * 500 + [np.nan] * 10)
    assert psi(train, train) == pytest.approx(0, abs=1e-12)
    assert psi(train, pd.Series([5] * 100)) > 1          # toàn bộ dữ liệu mới rơi vào bin cuối
    assert psi(pd.Series([1.0] * 50), pd.Series([1.0] * 20)) == 0.0   # biến hằng


def test_psi_level_thresholds():
    assert [psi_level(v, 0.1, 0.2) for v in (0.05, 0.15, 0.25)] == ["Ổn định", "Cần theo dõi", "Thay đổi đáng kể"]


def _raw(n=10):
    return pd.DataFrame({c: ["1"] * n for c in COLUMNS})


def test_schema_error_rate_counts_bad_types_and_required_missing():
    raw = _raw()
    assert schema_error_rate(raw) == 0
    raw.loc[0, "Sem_GPA"] = "ba phẩy hai"     # sai kiểu
    raw.loc[1, "Age"] = ""                    # thiếu ở cột bắt buộc
    raw.loc[2, "Family_Income"] = ""          # được phép thiếu → không tính
    assert schema_error_rate(raw) == pytest.approx(0.2)
    assert schema_error_rate(raw.drop(columns="Sem_GPA")) == 1.0


def test_performance_on_new_labels_matches_only_rows_with_outcome():
    previous = pd.DataFrame({"student_id": ["A", "B", "C", "D"], "semester": [2, 3, 1, 4],
                             "risk_score": [0.9, 0.05, 0.4, 0.2], "risk_level": ["Cao", "Thấp", "Trung bình", "Thấp"]})
    features = pd.DataFrame({"Student_ID": ["A", "B", "C", "D"], "Semester": [2, 3, 1, 5],
                             "Censored": [0, 0, 0, 1], "Target_Dropout_Next_Sem": [1, 0, 1, 0]})
    res = performance_on_new_labels(previous, features, "Target_Dropout_Next_Sem")
    assert res["n"] == 3                       # D chưa có kết cục ở kỳ 4
    assert res["recall_medium"] == pytest.approx(1.0)
    assert res["pr_auc"] == pytest.approx(1.0)
    assert performance_on_new_labels(previous, features.assign(Censored=1), "Target_Dropout_Next_Sem") == {"n": 0}


def test_pipeline_order_and_restart():
    assert STEP_NAMES == ["ingest", "validate", "clean", "load", "features", "predict", "publish", "monitor"]
    assert [s for s, _ in plan("features")] == ["features", "predict", "publish"]
    with pytest.raises(ValueError):
        plan("train")
