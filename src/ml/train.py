"""Bước 10 – Tiền xử lý trong Pipeline & xử lý mất cân bằng lớp (B11 – B12 bổ sung huấn luyện, đánh giá).

Nguyên tắc: MỌI thao tác học từ dữ liệu (trung vị, mean/std, phân vị winsorize, SMOTE) nằm BÊN TRONG
Pipeline → khi chạy CV, mỗi fold tự fit lại chỉ trên phần huấn luyện của fold đó, không rò rỉ.
Bước duy nhất ngoài "học" là CastTypes: ép kiểu cố định, không phụ thuộc dữ liệu.

    build_pipeline("xgb", imbalance="weight", y_train=y)   # → Pipeline CHƯA fit
"""

import numpy as np
import pandas as pd
from imblearn.over_sampling import SMOTE, SMOTENC
from imblearn.pipeline import Pipeline as ImbPipeline
from lightgbm import LGBMClassifier
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier
from xgboost import XGBClassifier

from src.core import config

MODELS = ["dummy", "logreg", "dtree", "rf", "xgb", "lgbm"]
IMBALANCE = ["none", "weight", "smote"]
NATIVE_NAN_MODELS = {"xgb", "lgbm"}  # tự xử lý NaN, không cần imputer

# Biến lệch phải: winsorize P1–P99 + log1p, chỉ cho mô hình tuyến tính
SKEWED = ["Family_Income", "Financial_Stress", "Emergency_Expense", "Financial_Burden_Index",
          "Cum_Emergency_Expense", "Tuition_to_Income"]


def _random_state() -> int:
    return config.settings()["project"]["random_state"]


# ---------------------------------------------------------------- bộ biến đổi tự viết

class CastTypes(BaseEstimator, TransformerMixin):
    """Ép kiểu cố định (không học gì): số/nhị phân → float64 (pd.NA → NaN), phân loại → chuỗi."""

    def __init__(self, categorical=()):
        self.categorical = categorical

    def fit(self, X, y=None):
        self.feature_names_in_ = np.asarray(X.columns, dtype=object)
        return self

    def transform(self, X):
        X = X.copy()
        for col in X.columns:
            if col in self.categorical:
                X[col] = X[col].astype(object).where(X[col].notna(), "missing").astype(str)
            else:
                X[col] = pd.to_numeric(X[col], errors="coerce").astype("float64")
        return X

    def get_feature_names_out(self, input_features=None):
        return self.feature_names_in_


class Winsorizer(BaseEstimator, TransformerMixin):
    """Chặn mỗi cột về [phân vị lower, phân vị upper] HỌC TỪ dữ liệu fit (tập Train của fold)."""

    def __init__(self, lower=0.01, upper=0.99):
        self.lower = lower
        self.upper = upper

    def fit(self, X, y=None):
        X = np.asarray(X, dtype=float)
        self.low_ = np.nanquantile(X, self.lower, axis=0)
        self.high_ = np.nanquantile(X, self.upper, axis=0)
        self.n_features_in_ = X.shape[1]
        return self

    def transform(self, X):
        return np.clip(np.asarray(X, dtype=float), self.low_, self.high_)

    def get_feature_names_out(self, input_features=None):
        return np.asarray(input_features, dtype=object)


class DiscreteAwareSMOTE(BaseEstimator):
    """SMOTE không tạo giá trị "không thể có" ở cột rời rạc.

    SMOTE thường nội suy MỌI cột → cột nhị phân / One-Hot / cột đếm nhận giá trị lẻ (Scholarship = 0,43,
    Semester = 2,37). Mô hình cây tách được ngay dòng tổng hợp bằng một ngưỡng như vậy, nên học trên dữ
    liệu "cân bằng" nhưng dự đoán trên dữ liệu thật vẫn như chưa cân bằng. Lớp này phát hiện lúc fit các
    cột mà mọi giá trị đều là số nguyên và giao cho SMOTENC (lấy giá trị phổ biến của láng giềng thay vì
    nội suy); cột liên tục vẫn nội suy như SMOTE.
    """

    def __init__(self, random_state=None):
        self.random_state = random_state

    def fit_resample(self, X, y):
        X = np.asarray(X, dtype=float)
        discrete = [j for j in range(X.shape[1]) if np.all(np.mod(X[:, j], 1) == 0)]
        self.discrete_columns_ = discrete
        if not discrete or len(discrete) == X.shape[1]:
            sampler = SMOTE(random_state=self.random_state)
        else:
            sampler = SMOTENC(categorical_features=discrete, random_state=self.random_state)
        return sampler.fit_resample(X, y)


# ---------------------------------------------------------------- tiền xử lý

def column_groups(spec: dict) -> dict[str, list[str]]:
    numeric = spec["numeric"]
    delta = [c for c in numeric if c.startswith("Delta_") or c == "GPA_Slope"]
    skewed = [c for c in SKEWED if c in numeric]
    other = [c for c in numeric if c not in delta and c not in skewed]
    return {"skewed": skewed, "delta": delta, "numeric": other,
            "binary": spec["binary"], "categorical": spec["categorical"]}


def _onehot():
    return OneHotEncoder(handle_unknown="ignore", sparse_output=False)


def build_preprocessor(spec: dict, kind: str) -> ColumnTransformer:
    """kind = 'linear' (LogReg), 'impute' (DT, RF, SMOTE) hoặc 'native' (XGBoost / LightGBM giữ NaN)."""
    g = column_groups(spec)
    if kind == "linear":
        transformers = [
            ("skewed", Pipeline([("impute", SimpleImputer(strategy="median")), ("winsor", Winsorizer()),
                                 ("log1p", FunctionTransformer(np.log1p, feature_names_out="one-to-one")),
                                 ("scale", StandardScaler())]), g["skewed"]),
            # Kỳ 1 không có kỳ trước → Delta / Slope = 0 nghĩa là "không thay đổi"
            ("delta", Pipeline([("impute", SimpleImputer(strategy="constant", fill_value=0.0)),
                                ("scale", StandardScaler())]), g["delta"]),
            ("numeric", Pipeline([("impute", SimpleImputer(strategy="median")),
                                  ("scale", StandardScaler())]), g["numeric"]),
            ("binary", "passthrough", g["binary"]),
            ("categorical", _onehot(), g["categorical"]),
        ]
    elif kind == "impute":
        numeric = g["skewed"] + g["delta"] + g["numeric"]
        transformers = [
            ("numeric", SimpleImputer(strategy="median"), numeric),
            ("binary", "passthrough", g["binary"]),
            ("categorical", _onehot(), g["categorical"]),
        ]
    elif kind == "native":
        numeric = g["skewed"] + g["delta"] + g["numeric"]
        transformers = [
            ("numeric", "passthrough", numeric),
            ("binary", "passthrough", g["binary"]),
            ("categorical", _onehot(), g["categorical"]),
        ]
    else:
        raise ValueError(f"kind không hợp lệ: {kind}")
    return ColumnTransformer(transformers, remainder="drop", verbose_feature_names_out=False)


# ---------------------------------------------------------------- mô hình

def positive_weight(y) -> float:
    """scale_pos_weight = số mẫu âm / số mẫu dương, tính từ nhãn của tập huấn luyện được truyền vào."""
    y = np.asarray(y)
    pos = int((y == 1).sum())
    if pos == 0:
        raise ValueError("Tập huấn luyện không có mẫu dương.")
    return float((y == 0).sum() / pos)


def build_model(name: str, weighted: bool, pos_weight: float | None, params: dict | None = None):
    rs = _random_state()
    params = params or {}
    cw = "balanced" if weighted else None
    if name == "dummy":
        return DummyClassifier(strategy="prior")
    # Tham số mặc định; `params` (từ Optuna ở B11) ghi đè lên
    if name == "logreg":
        return LogisticRegression(**{"C": 1.0, "max_iter": 3000, **params}, class_weight=cw, random_state=rs)
    if name == "dtree":
        return DecisionTreeClassifier(**{"max_depth": 8, "min_samples_leaf": 50, **params},
                                      class_weight=cw, random_state=rs)
    if name == "rf":
        return RandomForestClassifier(**{"n_estimators": 300, "min_samples_leaf": 20, "max_features": "sqrt", **params},
                                      class_weight="balanced_subsample" if weighted else None,
                                      n_jobs=-1, random_state=rs)
    spw = pos_weight if weighted else 1.0
    if name == "xgb":
        defaults = dict(n_estimators=400, learning_rate=0.05, max_depth=5, subsample=0.8, colsample_bytree=0.8,
                        min_child_weight=5, tree_method="hist", eval_metric="aucpr")
        return XGBClassifier(**{**defaults, **params}, scale_pos_weight=spw, n_jobs=-1, random_state=rs)
    if name == "lgbm":
        defaults = dict(n_estimators=400, learning_rate=0.05, num_leaves=31, min_child_samples=50,
                        subsample=0.8, subsample_freq=1, colsample_bytree=0.8)
        return LGBMClassifier(**{**defaults, **params}, scale_pos_weight=spw, n_jobs=-1, random_state=rs, verbose=-1)
    raise ValueError(f"Mô hình không hợp lệ: {name}. Chọn một trong {MODELS}")


def build_pipeline(name: str, spec: dict, imbalance: str = "weight", y_train=None, params: dict | None = None):
    """Pipeline CHƯA fit: CastTypes → tiền xử lý → (SMOTE) → mô hình.

    imbalance: 'none' | 'weight' (class_weight / scale_pos_weight) | 'smote' (chỉ chạy lúc fit, trên fold huấn luyện)
    y_train: bắt buộc với XGBoost / LightGBM khi imbalance='weight' để tính scale_pos_weight.
    """
    if imbalance not in IMBALANCE:
        raise ValueError(f"imbalance phải thuộc {IMBALANCE}")
    if name == "logreg":
        kind = "linear"
    elif name in NATIVE_NAN_MODELS and imbalance != "smote":
        kind = "native"
    else:
        kind = "impute"  # SMOTE cần dữ liệu không có NaN
    pos_weight = None
    if name in NATIVE_NAN_MODELS and imbalance == "weight":
        if y_train is None:
            raise ValueError("Cần y_train để tính scale_pos_weight.")
        pos_weight = positive_weight(y_train)

    steps = [("cast", CastTypes(categorical=tuple(spec["categorical"]))),
             ("prep", build_preprocessor(spec, kind))]
    model = build_model(name, weighted=(imbalance == "weight"), pos_weight=pos_weight, params=params)
    if imbalance == "smote":
        return ImbPipeline(steps + [("smote", DiscreteAwareSMOTE(random_state=_random_state())), ("model", model)])
    return Pipeline(steps + [("model", model)])
