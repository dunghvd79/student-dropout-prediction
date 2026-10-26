"""Bước 9 – Tạo tập có nhãn & chia Train/Test theo Student_ID.

Chạy:  python -m src.ml.split
  Đọc data/features/feature_table.parquet + config/feature_spec.json (output của B7).

  1. Dòng Censored = 1 (nhãn chưa xác nhận) → Scoring set, dành cho B14.
  2. Dòng Censored = 0 → tập có nhãn; bỏ cột rò rỉ (End_of_Semester_Status, Censored).
  3. Chia 80/20 THEO SINH VIÊN bằng StratifiedGroupKFold (1 fold làm Test), random_state cố định.
  4. Lưu danh sách Student_ID của Test → data/splits/test_student_ids.csv.

Các bước sau gọi load_splits() để dựng lại ĐÚNG cách chia này, không chia lại.
"""

import json
import sys
from dataclasses import dataclass

import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold

from src.core import config

TEST_IDS_FILE = "test_student_ids.csv"
SUMMARY_FILE = "split_summary.json"


@dataclass
class Splits:
    X_train: pd.DataFrame
    y_train: pd.Series
    groups_train: pd.Series
    X_test: pd.DataFrame
    y_test: pd.Series
    groups_test: pd.Series
    X_score: pd.DataFrame
    keys_train: pd.DataFrame
    keys_test: pd.DataFrame
    keys_score: pd.DataFrame


def load_spec() -> dict:
    return json.loads((config.ROOT / "config" / "feature_spec.json").read_text(encoding="utf-8"))


def load_features() -> pd.DataFrame:
    path = config.path("features_dir") / "feature_table.parquet"
    if not path.exists():
        raise FileNotFoundError(f"Không thấy {path}. Hãy chạy python -m src.analysis.features trước.")
    return pd.read_parquet(path)


def separate(features: pd.DataFrame, spec: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(tập có nhãn, scoring set). Không bỏ cột ở đây để còn kiểm tra; X chỉ lấy cột trong spec."""
    censored = features[spec["censored"]] == 1
    return features[~censored].reset_index(drop=True), features[censored].reset_index(drop=True)


def choose_test_students(labeled: pd.DataFrame, spec: dict) -> pd.Index:
    """Chọn sinh viên cho tập Test: 1 fold của StratifiedGroupKFold (giữ tỷ lệ lớp, không chia sinh viên)."""
    cfg = config.settings()
    n_splits = round(1 / cfg["split"]["test_size"])
    sgkf = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=cfg["project"]["random_state"])
    _, test_idx = next(sgkf.split(labeled, labeled[spec["target"]], groups=labeled["Student_ID"]))
    return pd.Index(sorted(labeled.loc[test_idx, "Student_ID"].unique()), name="Student_ID")


def build_splits(features: pd.DataFrame, spec: dict, test_students: pd.Index) -> Splits:
    labeled, scoring = separate(features, spec)
    is_test = labeled["Student_ID"].isin(test_students)
    X_cols = spec["features"]
    key_cols = spec["id_cols"]
    train, test = labeled[~is_test].reset_index(drop=True), labeled[is_test].reset_index(drop=True)
    return Splits(
        X_train=train[X_cols], y_train=train[spec["target"]], groups_train=train["Student_ID"],
        X_test=test[X_cols], y_test=test[spec["target"]], groups_test=test["Student_ID"],
        X_score=scoring[X_cols],
        keys_train=train[key_cols], keys_test=test[key_cols], keys_score=scoring[key_cols],
    )


def cv_splitter() -> StratifiedGroupKFold:
    """Bộ chia CV dùng cho B11: k fold theo sinh viên, giữ tỷ lệ lớp."""
    cfg = config.settings()
    return StratifiedGroupKFold(n_splits=cfg["split"]["cv_folds"], shuffle=True,
                                random_state=cfg["project"]["random_state"])


def check_splits(s: Splits, spec: dict) -> list[tuple[str, bool, str]]:
    train_ids, test_ids = set(s.groups_train), set(s.groups_test)
    n_labeled = len(s.y_train) + len(s.y_test)
    test_share = len(s.y_test) / n_labeled
    p_train, p_test = s.y_train.mean(), s.y_test.mean()
    labeled_keys = pd.concat([s.keys_train, s.keys_test])
    score_overlap = not s.keys_score.merge(labeled_keys, on=list(labeled_keys.columns)).empty
    leak = set(spec["leakage_cols"] + [spec["target"], "Student_ID"]) & set(s.X_train.columns)
    folds = [s.y_train.iloc[val].mean()
             for _, val in cv_splitter().split(s.X_train, s.y_train, groups=s.groups_train)]
    fold_overlap = any(
        set(s.groups_train.iloc[tr]) & set(s.groups_train.iloc[val])
        for tr, val in cv_splitter().split(s.X_train, s.y_train, groups=s.groups_train)
    )
    return [
        ("Không sinh viên nào ở cả Train và Test", not (train_ids & test_ids),
         f"{len(train_ids):,} SV Train, {len(test_ids):,} SV Test, giao {len(train_ids & test_ids)}"),
        ("Tỷ lệ Test ≈ 20%", 0.17 <= test_share <= 0.23, f"{test_share:.1%} số dòng"),
        ("Tỷ lệ lớp dương xấp xỉ nhau", abs(p_train - p_test) < 0.01, f"Train {p_train:.2%}, Test {p_test:.2%}"),
        ("Không có cột rò rỉ trong X", not leak, "sạch" if not leak else str(leak)),
        ("Scoring set: mỗi SV đúng 1 dòng, không trùng dòng nào của Train/Test",
         s.keys_score["Student_ID"].is_unique and not score_overlap,
         f"{len(s.X_score):,} dòng, {s.keys_score['Student_ID'].nunique():,} SV"),
        (f"CV {len(folds)} fold theo sinh viên trên Train", not fold_overlap,
         "tỷ lệ dương mỗi fold: " + ", ".join(f"{p:.2%}" for p in folds)),
    ]


def make_splits() -> tuple[Splits, list]:
    features, spec = load_features(), load_spec()
    labeled, _ = separate(features, spec)
    test_students = choose_test_students(labeled, spec)
    out_dir = config.path("splits_dir")
    out_dir.mkdir(parents=True, exist_ok=True)
    test_students.to_series().to_csv(out_dir / TEST_IDS_FILE, index=False)
    splits = build_splits(features, spec, test_students)
    checks = check_splits(splits, spec)
    summary = {
        "random_state": config.settings()["project"]["random_state"],
        "rows": {"train": len(splits.y_train), "test": len(splits.y_test), "score": len(splits.X_score)},
        "students": {"train": splits.groups_train.nunique(), "test": splits.groups_test.nunique(),
                     "score": int(splits.keys_score["Student_ID"].nunique())},
        "positives": {"train": int(splits.y_train.sum()), "test": int(splits.y_test.sum())},
        "positive_rate": {"train": round(splits.y_train.mean(), 4), "test": round(splits.y_test.mean(), 4)},
        "n_features": splits.X_train.shape[1],
        "checks_passed": all(ok for _, ok, _ in checks),
    }
    (out_dir / SUMMARY_FILE).write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return splits, checks


def load_splits() -> Splits:
    """Dựng lại đúng cách chia đã lưu (B10 – B14 dùng hàm này)."""
    path = config.path("splits_dir") / TEST_IDS_FILE
    if not path.exists():
        raise FileNotFoundError(f"Không thấy {path}. Hãy chạy python -m src.ml.split trước.")
    test_students = pd.Index(pd.read_csv(path)["Student_ID"].astype(str))
    return build_splits(load_features(), load_spec(), test_students)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    splits, checks = make_splits()
    summary = json.loads((config.path("splits_dir") / SUMMARY_FILE).read_text(encoding="utf-8"))
    print(f"Train : {summary['rows']['train']:,} dòng, {summary['students']['train']:,} SV, "
          f"{summary['positives']['train']:,} dương ({summary['positive_rate']['train']:.2%})")
    print(f"Test  : {summary['rows']['test']:,} dòng, {summary['students']['test']:,} SV, "
          f"{summary['positives']['test']:,} dương ({summary['positive_rate']['test']:.2%})")
    print(f"Score : {summary['rows']['score']:,} dòng ({summary['students']['score']:,} SV đang theo học)")
    print(f"X     : {summary['n_features']} đặc trưng")
    for name, ok, detail in checks:
        print(f"[{'OK' if ok else 'LỖI'}] {name}: {detail}")
    print(f"Đã lưu: {config.path('splits_dir') / TEST_IDS_FILE}")
    return 0 if summary["checks_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
