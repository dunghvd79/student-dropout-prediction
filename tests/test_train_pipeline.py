"""Unit test cho Bước 10 – Pipeline tiền xử lý & mất cân bằng lớp (không cần Docker; dữ liệu tổng hợp)."""

import numpy as np
import pandas as pd
import pytest
from sklearn.exceptions import NotFittedError
from sklearn.utils.validation import check_is_fitted

from src.ml.train import MODELS, Winsorizer, build_pipeline, column_groups, positive_weight

SPEC = {
    "numeric": ["Sem_GPA", "Family_Income", "Financial_Stress", "Delta_GPA", "GPA_Slope", "LMS_Logins"],
    "binary": ["Scholarship", "Is_First_Semester"],
    "categorical": ["Gender", "Housing_Status"],
}
SPEC["features"] = SPEC["numeric"] + SPEC["binary"] + SPEC["categorical"]


def make_xy(n, seed):
    rng = np.random.RandomState(seed)
    X = pd.DataFrame({
        "Sem_GPA": rng.uniform(1, 4, n),
        "Family_Income": np.where(rng.rand(n) < 0.05, np.nan, rng.lognormal(10.8, 0.6, n)),
        "Financial_Stress": rng.gamma(2, 1.3, n) + 1,
        "Delta_GPA": np.where(rng.rand(n) < 0.25, np.nan, rng.normal(0, 0.2, n)),
        "GPA_Slope": np.where(rng.rand(n) < 0.25, np.nan, rng.normal(0, 0.1, n)),
        "LMS_Logins": pd.array(np.where(rng.rand(n) < 0.02, None, rng.randint(20, 100, n)), dtype="Int64"),
        "Scholarship": rng.randint(0, 2, n),
        "Is_First_Semester": rng.randint(0, 2, n),
        "Gender": pd.array(rng.choice(["Female", "Male", "Other/Unknown"], n), dtype="string"),
        "Housing_Status": pd.array(rng.choice(["On-Campus", "Off-Campus", "With Parents"], n), dtype="string"),
    })
    logit = -2.5 - 1.5 * (X["Sem_GPA"] - 2.7) + 0.4 * (X["Financial_Stress"] - 2.5)
    y = pd.Series((rng.rand(n) < 1 / (1 + np.exp(-logit))).astype(int))
    return X, y


@pytest.fixture(scope="module")
def data():
    return make_xy(600, 0), make_xy(200, 1)


@pytest.mark.parametrize("name", MODELS)
@pytest.mark.parametrize("imbalance", ["none", "weight", "smote"])
def test_every_pipeline_fits_on_data_with_missing_values(data, name, imbalance):
    (X, y), (X_te, _) = data
    pipe = build_pipeline(name, SPEC, imbalance=imbalance, y_train=y)
    pipe.fit(X, y)
    proba = pipe.predict_proba(X_te)
    assert proba.shape == (len(X_te), 2)
    assert np.isfinite(proba).all()


def test_pipeline_is_returned_unfitted(data):
    (X, y), _ = data
    pipe = build_pipeline("logreg", SPEC, y_train=y)
    with pytest.raises(NotFittedError):
        check_is_fitted(pipe.named_steps["model"])


def test_learned_statistics_come_from_training_data_only(data):
    (X, y), (X_te, _) = data
    pipe = build_pipeline("logreg", SPEC, y_train=y).fit(X, y)
    prep = pipe.named_steps["prep"]
    scaler = prep.named_transformers_["numeric"].named_steps["scale"]
    imputer = prep.named_transformers_["numeric"].named_steps["impute"]
    cols = column_groups(SPEC)["numeric"]
    train = X[cols].astype(float)
    np.testing.assert_allclose(imputer.statistics_, train.median().values)
    np.testing.assert_allclose(scaler.mean_, train.fillna(train.median()).mean().values)
    # tham số không đổi khi dự đoán trên dữ liệu khác
    before = scaler.mean_.copy()
    pipe.predict_proba(X_te)
    np.testing.assert_allclose(scaler.mean_, before)


def test_delta_missing_filled_with_zero_for_linear(data):
    (X, y), _ = data
    pipe = build_pipeline("logreg", SPEC, y_train=y).fit(X, y)
    imputer = pipe.named_steps["prep"].named_transformers_["delta"].named_steps["impute"]
    assert (imputer.statistics_ == 0).all()


def test_winsorizer_uses_fit_quantiles():
    w = Winsorizer(0.1, 0.9).fit(np.arange(100, dtype=float).reshape(-1, 1))
    out = w.transform(np.array([[-1000.0], [50.0], [1000.0]]))
    assert out[0, 0] == pytest.approx(9.9) and out[1, 0] == 50 and out[2, 0] == pytest.approx(89.1)


def test_tree_native_models_keep_nan(data):
    (X, y), _ = data
    pipe = build_pipeline("xgb", SPEC, y_train=y).fit(X, y)
    transformed = pipe[:-1].transform(X)
    assert np.isnan(transformed).any()  # XGBoost tự xử lý NaN


def test_scale_pos_weight_from_training_labels(data):
    (X, y), _ = data
    pipe = build_pipeline("xgb", SPEC, imbalance="weight", y_train=y)
    assert pipe.named_steps["model"].get_params()["scale_pos_weight"] == pytest.approx((y == 0).sum() / (y == 1).sum())
    assert positive_weight([0, 0, 0, 1]) == 3.0


def test_smote_only_resamples_during_fit(data):
    (X, y), (X_te, _) = data
    pipe = build_pipeline("rf", SPEC, imbalance="smote", y_train=y).fit(X, y)
    smote = pipe.named_steps["smote"]
    prepped = pipe[:2].transform(X)
    _, y_res = smote.fit_resample(prepped, y)
    assert y_res.mean() == pytest.approx(0.5)            # fold huấn luyện được cân bằng
    assert len(pipe.predict_proba(X_te)) == len(X_te)    # dự đoán không tạo / bỏ dòng


def test_onehot_ignores_unseen_category(data):
    (X, y), (X_te, _) = data
    pipe = build_pipeline("logreg", SPEC, y_train=y).fit(X, y)
    X_new = X_te.copy()
    X_new["Housing_Status"] = pd.array(["Dorm"] * len(X_new), dtype="string")
    assert np.isfinite(pipe.predict_proba(X_new)).all()


def test_invalid_arguments():
    with pytest.raises(ValueError):
        build_pipeline("svm", SPEC)
    with pytest.raises(ValueError):
        build_pipeline("xgb", SPEC, imbalance="weight", y_train=None)


def test_smote_keeps_discrete_columns_discrete(data):
    """Mẫu tổng hợp không được có giá trị lẻ ở cột nhị phân / One-Hot (nếu có, mô hình cây tách được ngay)."""
    (X, y), _ = data
    pipe = build_pipeline("rf", SPEC, imbalance="smote", y_train=y).fit(X, y)
    prepped = pipe[:2].transform(X)
    X_res, y_res = pipe.named_steps["smote"].fit_resample(prepped, y)
    synthetic = X_res[len(X):]
    discrete = pipe.named_steps["smote"].discrete_columns_
    assert len(discrete) >= 2 + 6  # 2 cột nhị phân + 6 cột One-Hot
    assert np.all(np.mod(synthetic[:, discrete], 1) == 0)
    assert y_res.mean() == pytest.approx(0.5)


@pytest.mark.parametrize("name, params", [
    ("logreg", {"C": 0.05}),
    ("dtree", {"max_depth": 3}),
    ("rf", {"n_estimators": 50, "min_samples_leaf": 7, "max_features": 0.5}),
    ("xgb", {"n_estimators": 50, "max_depth": 3}),
    ("lgbm", {"n_estimators": 50, "num_leaves": 9}),
])
def test_params_override_defaults(data, name, params):
    """Tham số tinh chỉnh (Optuna) phải ghi đè mặc định, không báo lỗi trùng tham số."""
    (X, y), _ = data
    pipe = build_pipeline(name, SPEC, imbalance="weight", y_train=y, params=params).fit(X, y)
    got = pipe.named_steps["model"].get_params()
    assert all(got[k] == v for k, v in params.items())
