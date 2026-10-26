"""Unit test cho Bước 13 – SHAP cho LogReg, gom nhóm, top_reasons (không cần Docker)."""

import warnings

import numpy as np
import pandas as pd
import pytest

from src.ml.explain import (DESCRIBE, GROUPS, NOT_A_REASON, _vn, explain, group_of, opposite_signs, original_feature,
                            reasons_text, top_reasons)
from src.ml.split import load_spec
from src.ml.train import build_pipeline


@pytest.fixture(scope="module")
def spec():
    return load_spec()


def make_X(spec, n, seed):
    """Dữ liệu giả có đủ 43 đặc trưng thật, giá trị trong khoảng hợp lý."""
    rng = np.random.RandomState(seed)
    X = pd.DataFrame({c: rng.normal(1, 0.5, n) for c in spec["numeric"]})
    for c in ("Semester", "Course_Load", "Failed_Courses", "Cum_Failed_Courses", "Advising_Visits", "Age",
              "Household_Size", "Num_Emergency_Sems", "LMS_Logins"):
        X[c] = rng.randint(1, 8, n)
    for c in spec["binary"]:
        X[c] = (rng.rand(n) < 0.3).astype(int)
    X["Gender"] = rng.choice(["Female", "Male", "Other/Unknown"], n)
    X["Housing_Status"] = rng.choice(["On-Campus", "Off-Campus", "With Parents"], n)
    X.loc[rng.rand(n) < 0.05, "Family_Income"] = np.nan
    return X[spec["features"]]


@pytest.fixture(scope="module")
def fitted(spec):
    X = make_X(spec, 1500, 0)
    logit = -2 + 1.2 * X["Failed_Courses"] / 4 - 1.0 * X["Sem_GPA"] + 0.8 * X["First_Generation"]
    y = (np.random.RandomState(1).rand(len(X)) < 1 / (1 + np.exp(-logit))).astype(int)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = build_pipeline("logreg", spec, imbalance="none", y_train=y).fit(X, y)
    X_new = make_X(spec, 300, 2)
    return model, X, X_new, explain(model, X_new, X, spec)


def test_every_feature_in_exactly_one_group(spec):
    members = [f for _, feats in GROUPS.values() for f in feats]
    assert sorted(members) == sorted(spec["features"])
    assert len(members) == len(set(members))
    assert set(DESCRIBE) == set(GROUPS) and NOT_A_REASON <= set(GROUPS)


def test_original_feature_maps_onehot(spec):
    assert original_feature("Gender_Male", spec) == "Gender"
    assert original_feature("Housing_Status_With Parents", spec) == "Housing_Status"
    assert original_feature("Sem_GPA", spec) == "Sem_GPA"
    with pytest.raises(KeyError):
        original_feature("Không_có", spec)


def test_shap_additive_and_matches_model(fitted, spec):
    model, _, X_new, ex = fitted
    # φ0 + Σφ = log-odds mô hình; cộng theo đặc trưng hay theo nhóm đều như nhau
    assert np.allclose(ex.base + ex.features.sum(axis=1), ex.logit, atol=1e-8)
    assert np.allclose(ex.features.sum(axis=1), ex.groups.sum(axis=1), atol=1e-10)
    assert np.allclose(ex.proba, model.predict_proba(X_new)[:, 1])
    assert list(ex.features.columns) == spec["features"] and list(ex.groups.columns) == list(GROUPS)


def test_linear_shap_closed_form(fitted, spec):
    """Với LogReg: φ_j = β_j (x_j − E[x_j]) trên dữ liệu đã tiền xử lý, E lấy trên nền (Train)."""
    model, X_bg, X_new, ex = fitted
    prep, lr = model[:-1], model[-1]
    bg, Xt = prep.transform(X_bg), prep.transform(X_new)
    phi = (Xt - bg.mean(axis=0)) * lr.coef_[0]
    names = list(prep.get_feature_names_out())
    assert np.allclose(ex.features["Sem_GPA"], phi[:, names.index("Sem_GPA")])
    gender = [i for i, n in enumerate(names) if n.startswith("Gender_")]
    assert np.allclose(ex.features["Gender"], phi[:, gender].sum(axis=1))
    assert ex.base == pytest.approx(lr.intercept_[0] + bg.mean(axis=0) @ lr.coef_[0])


def test_top_reasons_only_positive_and_actionable(fitted):
    _, _, X_new, ex = fitted
    for i in range(50):
        reasons = top_reasons(ex.groups.iloc[i], X_new.iloc[i], k=3)
        assert len(reasons) <= 3
        assert all(r["shap"] > 0 and r["nhom"] not in NOT_A_REASON for r in reasons)
        assert [r["shap"] for r in reasons] == sorted((r["shap"] for r in reasons), reverse=True)
        assert all(isinstance(r["mo_ta"], str) and r["mo_ta"] for r in reasons)


def test_top_reasons_skips_demographics_even_if_largest():
    phi = pd.Series(0.0, index=list(GROUPS))
    phi[["nhan_khau", "co_van", "truot_mon", "hoc_bong"]] = [3.0, 2.0, 0.5, -0.4]
    row = pd.Series({"Failed_Courses": 2, "Cum_Failed_Courses": 5, "Scholarship": 0})
    reasons = top_reasons(phi, row)
    assert [r["nhom"] for r in reasons] == ["truot_mon"]
    assert reasons[0]["mo_ta"] == "Trượt 2 môn kỳ này, tích lũy 5 môn"
    assert reasons_text([]) == "Không có yếu tố nào cao hơn mức trung bình"


def test_vietnamese_number_format():
    assert _vn(1234.567) == "1.234,57"
    assert _vn(2.1, 1) == "2,1"


def test_describe_handles_missing_values():
    row = pd.Series({"LMS_Logins": np.nan, "LMS_Missing": 1, "Delta_LMS": np.nan, "Attendance": np.nan,
                     "Delta_Attendance": np.nan, "Income_Missing": 1, "Sem_GPA": 2.5, "Delta_GPA": np.nan, "CGPA": 2.5})
    assert DESCRIBE["lms"](row) == "Không có dữ liệu LMS kỳ này"
    assert DESCRIBE["chuyen_can"](row) == "Không có dữ liệu chuyên cần"
    assert DESCRIBE["thu_nhap"](row) == "Chưa khai báo thu nhập gia đình"
    assert DESCRIBE["hoc_tap"](row) == "GPA kỳ này 2,50, GPA tích lũy 2,50"  # kỳ 1: không có "so với kỳ trước"


def test_opposite_signs_found_within_group(spec):
    rng = np.random.RandomState(0)
    X = pd.DataFrame({"Work_Hours": rng.normal(16, 10, 200)})
    X["Work_prev"] = X["Work_Hours"] + rng.normal(0, 2, 200)
    coef = pd.Series({"Work_Hours": 0.07, "Work_prev": -0.05, "Delta_Work_Hours": 0.01})
    out = opposite_signs(coef, X, spec)
    assert [(o["dac_trung"], o["bien_chinh"]) for o in out] == [("Work_prev", "Work_Hours")]
    assert out[0]["tuong_quan"] > 0.9
