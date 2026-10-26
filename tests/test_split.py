"""Unit test cho Bước 9 – chia tập theo sinh viên (không cần Docker; dữ liệu tổng hợp)."""

import numpy as np
import pandas as pd
import pytest

from src.ml.split import build_splits, check_splits, choose_test_students, separate

SPEC = {
    "id_cols": ["Student_ID", "Semester"], "target": "Target_Dropout_Next_Sem", "censored": "Censored",
    "leakage_cols": ["End_of_Semester_Status", "Censored"], "features": ["Semester", "f1", "f2"],
}


@pytest.fixture(scope="module")
def features():
    rng = np.random.RandomState(1)
    rows = []
    for i in range(1000):
        n = rng.randint(1, 6)
        outcome = rng.choice(["drop", "censored", "grad"], p=[0.35, 0.55, 0.10])
        for sem in range(1, n + 1):
            last = sem == n
            dropped = outcome == "drop" and last
            rows.append({
                "Student_ID": f"S{i:04d}", "Semester": sem, "f1": rng.rand(), "f2": rng.rand(),
                "Target_Dropout_Next_Sem": int(dropped),
                "End_of_Semester_Status": "Dropped_Out" if dropped else ("Graduated" if outcome == "grad" and last else "Enrolled"),
                "Censored": int(outcome == "censored" and last),
            })
    return pd.DataFrame(rows)


@pytest.fixture(scope="module")
def splits(features):
    labeled, _ = separate(features, SPEC)
    return build_splits(features, SPEC, choose_test_students(labeled, SPEC))


def test_no_student_in_both_train_and_test(splits):
    assert not set(splits.groups_train) & set(splits.groups_test)


def test_all_labeled_rows_used_once_and_censored_go_to_scoring(features, splits):
    labeled = features[features["Censored"] == 0]
    assert len(splits.y_train) + len(splits.y_test) == len(labeled)
    assert len(splits.X_score) == int(features["Censored"].sum())


def test_x_has_only_spec_features(splits):
    for X in (splits.X_train, splits.X_test, splits.X_score):
        assert list(X.columns) == SPEC["features"]


def test_test_share_and_stratification(splits):
    share = len(splits.y_test) / (len(splits.y_train) + len(splits.y_test))
    assert 0.15 < share < 0.25
    assert abs(splits.y_train.mean() - splits.y_test.mean()) < 0.03


def test_split_is_reproducible(features):
    labeled, _ = separate(features, SPEC)
    assert choose_test_students(labeled, SPEC).equals(choose_test_students(labeled, SPEC))


def test_rebuilding_from_saved_ids_gives_same_split(features, splits):
    saved = pd.Index(sorted(splits.groups_test.unique()))
    rebuilt = build_splits(features, SPEC, saved)
    pd.testing.assert_frame_equal(rebuilt.X_test, splits.X_test)
    pd.testing.assert_series_equal(rebuilt.y_train, splits.y_train)


def test_checks_pass(splits):
    failed = [name for name, ok, _ in check_splits(splits, SPEC) if not ok and "Tỷ lệ Test" not in name]
    assert not failed
