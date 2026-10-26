"""Unit test cho Bước 8 – phân cụm và luật kết hợp (không cần Docker; dữ liệu tổng hợp nhỏ)."""

import numpy as np
import pandas as pd
import pytest

from src.analysis.mining import (
    CLUSTER_FEATURES, ITEM_DEFINITIONS, describe_clusters, fit_clusters, make_items, mine_rules,
    name_clusters, student_profile,
)


@pytest.fixture(scope="module")
def features():
    rng = np.random.RandomState(0)
    rows = []
    for i in range(200):
        n = rng.randint(1, 5)
        risky = i % 4 == 0
        for sem in range(1, n + 1):
            last = sem == n
            dropped = risky and last
            rows.append({
                "Student_ID": f"S{i:03d}", "Semester": sem,
                "Sem_GPA": rng.normal(2.0 if risky else 3.0, 0.2), "Failed_Courses": rng.poisson(2 if risky else 0.3),
                "Attendance": rng.normal(85, 3), "LMS_Logins": pd.NA if sem == 1 and i % 7 == 0 else rng.randint(40, 90),
                "Work_Hours": rng.normal(28 if risky else 10, 3), "Financial_Stress": rng.normal(5 if risky else 2, 0.5),
                "Family_Income": np.nan if i == 5 else rng.uniform(1e4, 1e5), "Household_Size": rng.randint(1, 7),
                "First_Generation": int(risky), "Scholarship": int(not risky), "Has_Emergency": int(rng.rand() < 0.1),
                "Delta_GPA": np.nan if sem == 1 else rng.normal(-0.4 if risky else 0, 0.1),
                "End_of_Semester_Status": "Dropped_Out" if dropped else "Enrolled",
                "Target_Dropout_Next_Sem": int(dropped), "Censored": int(last and not dropped),
            })
    df = pd.DataFrame(rows)
    df["LMS_Logins"] = df["LMS_Logins"].astype("Int64")
    return df


def test_student_profile_one_row_per_student_no_missing(features):
    prof = student_profile(features)
    assert len(prof) == features["Student_ID"].nunique()
    assert not prof[CLUSTER_FEATURES].isna().any().any()
    assert prof["Dropped"].sum() == features.loc[features["End_of_Semester_Status"] == "Dropped_Out", "Student_ID"].nunique()


def test_clustering_deterministic_and_named(features):
    prof = student_profile(features)
    labels1, _, _ = fit_clusters(prof)
    labels2, _, _ = fit_clusters(prof)
    assert (labels1 == labels2).all()
    table = describe_clusters(prof, labels1)
    assert len(table) == 4 and table["cluster_name"].is_unique
    assert table["ty_le_bo_hoc"].iloc[0] == table["ty_le_bo_hoc"].max()  # sắp xếp rủi ro giảm dần


def test_name_clusters_uses_dropout_rate_and_work_hours():
    t = pd.DataFrame({"ty_le_bo_hoc": [0.3, 0.7, 0.1, 0.32], "Work_mean": [10, 26, 10, 25]}, index=[0, 1, 2, 3])
    names = name_clusters(t)
    assert names[1].startswith("Nguy cơ cao") and names[2] == "Học tốt – ổn định"
    assert names[3].startswith("Đi làm nhiều") and names[0].startswith("Học lực yếu")


def test_items_are_boolean_without_missing(features):
    items = make_items(features[features["Censored"] == 0])
    assert list(items.columns) == list(ITEM_DEFINITIONS)
    assert (items.dtypes == bool).all()


def test_rules_only_predict_dropout_and_respect_thresholds(features):
    items = make_items(features[features["Censored"] == 0])
    rules = mine_rules(items, min_support=0.05, min_confidence=0.3, min_lift=1.5)
    assert len(rules) > 0
    assert not rules["antecedents"].str.contains("DROPOUT").any()
    assert (rules["confidence"] >= 0.3).all() and (rules["lift"] >= 1.5).all() and (rules["support"] >= 0.05).all()
