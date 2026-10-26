"""Bước 7 – Trích xuất đặc trưng theo chiều dọc (Longitudinal Feature Engineering).

Chạy:  python -m src.analysis.features [--file PATH]
  Mặc định đọc data/processed/clean_semesters.parquet (output của B4).

Quy tắc bắt buộc: đặc trưng tại kỳ t chỉ dùng dữ liệu các kỳ <= t của CHÍNH sinh viên đó
(groupby Student_ID + shift / cumsum / expanding / rolling lùi). Vì không dùng thống kê của sinh
viên khác, bước này làm trước khi chia Train/Test mà không gây rò rỉ.

Output:
  data/features/feature_table.parquet   khóa + đặc trưng + nhãn + Censored + End_of_Semester_Status
  config/feature_spec.json              danh sách đặc trưng dùng chung cho B9–B14
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from src.core import config

KEYS = ["Student_ID", "Semester"]
TARGET = "Target_Dropout_Next_Sem"
NON_FEATURES = [TARGET, "Censored", "End_of_Semester_Status"]  # giữ trong bảng để tách tập, KHÔNG làm đặc trưng

# Đặc trưng gốc (một kỳ, "ảnh chụp tĩnh") – dùng làm mốc so sánh ở B11 (ablation)
BASE_NUMERIC = [
    "Age", "Family_Income", "Household_Size", "Tuition_Base", "Semester", "Course_Load", "Work_Hours",
    "Emergency_Expense", "Sem_GPA", "Attendance", "LMS_Logins", "Advising_Visits", "Failed_Courses",
    "Financial_Stress",
]
BASE_BINARY = ["First_Generation", "Scholarship", "Income_Missing", "LMS_Missing"]
CATEGORICAL = ["Gender", "Housing_Status"]

LAGGED = {"Sem_GPA": "GPA", "Attendance": "Attendance", "LMS_Logins": "LMS",
          "Financial_Stress": "Stress", "Work_Hours": "Work"}
DELTA_NAMES = {"Sem_GPA": "Delta_GPA", "Attendance": "Delta_Attendance", "LMS_Logins": "Delta_LMS",
               "Financial_Stress": "Delta_Stress", "Work_Hours": "Delta_Work_Hours"}


def _expanding_slope(df: pd.DataFrame, value: str, by: pd.core.groupby.DataFrameGroupBy) -> pd.Series:
    """Độ dốc OLS của `value` theo học kỳ, tính trên các kỳ 1..t (expanding). NaN khi mới có 1 kỳ.

    β = (n·Σkx − Σk·Σx) / (n·Σk² − (Σk)²), với các tổng tích lũy theo sinh viên.
    """
    k = df["Semester"].astype(float)
    x = df[value].astype(float)
    n = by.cumcount() + 1
    sk = k.groupby(df["Student_ID"]).cumsum()
    sx = x.groupby(df["Student_ID"]).cumsum()
    skx = (k * x).groupby(df["Student_ID"]).cumsum()
    skk = (k * k).groupby(df["Student_ID"]).cumsum()
    denom = n * skk - sk ** 2
    return ((n * skx - sk * sx) / denom.where(denom != 0)).astype(float)


def build_features(clean: pd.DataFrame) -> pd.DataFrame:
    """Từ clean_semesters (đã sắp xếp hay chưa đều được) → bảng đặc trưng, sắp xếp theo khóa."""
    df = clean.sort_values(KEYS).reset_index(drop=True).copy()
    by = df.groupby("Student_ID", sort=False)

    # Lag & Delta (kỳ trước của cùng sinh viên)
    for col, short in LAGGED.items():
        df[f"{short}_prev"] = by[col].shift(1).astype(float)
        df[DELTA_NAMES[col]] = df[col].astype(float) - df[f"{short}_prev"]

    # Tích lũy đến hết kỳ t
    df["Cum_Failed_Courses"] = by["Failed_Courses"].cumsum()
    df["Cum_Advising_Visits"] = by["Advising_Visits"].cumsum()
    df["Cum_Emergency_Expense"] = by["Emergency_Expense"].cumsum()
    df["Has_Emergency"] = (df["Emergency_Expense"] > 0).astype("int8")
    df["Num_Emergency_Sems"] = df.groupby("Student_ID", sort=False)["Has_Emergency"].cumsum()
    weighted = (df["Sem_GPA"] * df["Course_Load"]).groupby(df["Student_ID"]).cumsum()
    df["CGPA"] = weighted / by["Course_Load"].cumsum()

    # Cửa sổ trượt 3 kỳ gần nhất (chỉ lùi về quá khứ) và độ dốc GPA
    for col, name in (("Sem_GPA", "GPA_Roll3"), ("Attendance", "Attendance_Roll3")):
        df[name] = by[col].transform(lambda s: s.rolling(3, min_periods=1).mean())
    df["GPA_Slope"] = _expanding_slope(df, "Sem_GPA", by)

    # Tài chính
    df["Financial_Burden_Index"] = df["Work_Hours"] * df["Financial_Stress"] / (df["Family_Income"] + 1)
    df["Tuition_to_Income"] = df["Tuition_Base"] / df["Family_Income"]

    # Ngữ cảnh
    df["Is_First_Semester"] = (df["Semester"] == 1).astype("int8")
    df["Failed_Ratio"] = df["Failed_Courses"] / (df["Course_Load"] / 3)

    spec = feature_spec()
    return df[KEYS + NON_FEATURES + [c for c in spec["features"] if c != "Semester"]]


def feature_spec() -> dict:
    lag = [f"{s}_prev" for s in LAGGED.values()]
    longitudinal_numeric = (
        lag + list(DELTA_NAMES.values())
        + ["Cum_Failed_Courses", "Cum_Advising_Visits", "Cum_Emergency_Expense", "Num_Emergency_Sems", "CGPA",
           "GPA_Roll3", "Attendance_Roll3", "GPA_Slope", "Financial_Burden_Index", "Tuition_to_Income",
           "Failed_Ratio"]
    )
    longitudinal_binary = ["Has_Emergency", "Is_First_Semester"]
    numeric = BASE_NUMERIC + longitudinal_numeric
    binary = BASE_BINARY + longitudinal_binary
    return {
        "id_cols": KEYS,
        "target": TARGET,
        "censored": "Censored",
        "leakage_cols": ["End_of_Semester_Status", "Censored"],
        "numeric": numeric,
        "binary": binary,
        "categorical": CATEGORICAL,
        "features": numeric + binary + CATEGORICAL,
        # Dùng cho ablation ở B11: chỉ đặc trưng gốc so với gốc + chiều dọc
        "baseline_features": BASE_NUMERIC + BASE_BINARY + CATEGORICAL,
        "longitudinal_features": longitudinal_numeric + longitudinal_binary,
    }


def signal_table(features: pd.DataFrame) -> pd.DataFrame:
    """Tương quan Spearman của từng đặc trưng số với nhãn, trên tập có nhãn (Censored = 0)."""
    spec = feature_spec()
    labeled = features[features["Censored"] == 0]
    cols = spec["numeric"] + spec["binary"]
    rho = labeled[cols + [TARGET]].corr(method="spearman")[TARGET].drop(TARGET)
    out = pd.DataFrame({
        "spearman": rho.round(3),
        "abs": rho.abs().round(3),
        "thieu_%": (features[cols].isna().mean() * 100).round(2),
        "nhom": ["chiều dọc" if c in spec["longitudinal_features"] else "gốc" for c in cols],
    })
    return out.sort_values("abs", ascending=False)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Tạo bảng đặc trưng theo chiều dọc.")
    parser.add_argument("--file", type=Path, default=config.path("processed_dir") / "clean_semesters.parquet")
    args = parser.parse_args()
    if not args.file.exists():
        print(f"Không thấy {args.file}. Hãy chạy python -m src.etl.clean trước.")
        return 1

    clean = pd.read_parquet(args.file)
    features = build_features(clean)
    if len(features) != len(clean) or features.duplicated(KEYS).any():
        print("Lỗi: số dòng thay đổi hoặc trùng khóa sau khi tạo đặc trưng.")
        return 1

    out_path = config.path("features_dir") / "feature_table.parquet"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    features.to_parquet(out_path, index=False)
    spec_path = config.ROOT / "config" / "feature_spec.json"
    spec = feature_spec()
    spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Output: {out_path} ({features.shape[0]:,} × {features.shape[1]})")
    print(f"        {spec_path} ({len(spec['features'])} đặc trưng: {len(spec['baseline_features'])} gốc + "
          f"{len(spec['longitudinal_features'])} chiều dọc)")
    print("\nTop 15 đặc trưng theo |Spearman| với nhãn (tập có nhãn):")
    print(signal_table(features).head(15).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
