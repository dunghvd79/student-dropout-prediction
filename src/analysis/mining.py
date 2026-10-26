"""Bước 8 – Khai phá dữ liệu: 8A phân cụm sinh viên (K-Means), 8B luật kết hợp (Apriori).

Chạy:  python -m src.analysis.mining
  Đọc data/features/feature_table.parquet (output của B7).

Output:
  PostgreSQL student_clusters (student_id, cluster_id, cluster_name)   → dashboard B15
  reports/cluster_profiles.csv     hồ sơ từng cụm
  reports/association_rules.csv    luật {…} → {DROPOUT}

Đây là phần MÔ TẢ (khám phá tri thức). Nhãn bỏ học chỉ dùng để mô tả cụm, không dùng để phân cụm.
Cụm KHÔNG được dùng làm đặc trưng cho mô hình (K-Means ở đây fit trên toàn bộ sinh viên).
"""

import sys
import warnings

import numpy as np
import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler
from sqlalchemy import text

from src.core import config, db

TARGET = "Target_Dropout_Next_Sem"
RANDOM_STATE = 42
N_CLUSTERS = 4

# ---------------------------------------------------------------- 8A. Phân cụm

# Hồ sơ mức sinh viên: trung bình theo kỳ (không dùng số kỳ theo dõi vì nó phản ánh độ dài quan sát,
# tức kết cục / dữ liệu bị cắt, chứ không phải đặc điểm của sinh viên)
CLUSTER_FEATURES = [
    "GPA_mean", "Failed_per_sem", "Attendance_mean", "LMS_mean",
    "Work_mean", "Stress_mean", "Income_log", "Household_Size",
]


def student_profile(features: pd.DataFrame) -> pd.DataFrame:
    """1 dòng / sinh viên: 8 biến dùng để phân cụm + các cột mô tả kết cục (không dùng để phân cụm)."""
    g = features.groupby("Student_ID")
    prof = pd.DataFrame({
        "GPA_mean": g["Sem_GPA"].mean(),
        "Failed_per_sem": g["Failed_Courses"].mean(),
        "Attendance_mean": g["Attendance"].mean(),
        "LMS_mean": g["LMS_Logins"].mean().astype(float),
        "Work_mean": g["Work_Hours"].mean(),
        "Stress_mean": g["Financial_Stress"].mean(),
        "Income_log": np.log1p(g["Family_Income"].first()),
        "Household_Size": g["Household_Size"].first().astype(float),
    })
    # 199 sinh viên không khai báo thu nhập: điền trung vị (chỉ để phân cụm, mô tả)
    prof[CLUSTER_FEATURES] = prof[CLUSTER_FEATURES].fillna(prof[CLUSTER_FEATURES].median())
    last_status = g["End_of_Semester_Status"].last()
    prof["Dropped"] = last_status.eq("Dropped_Out").astype(int)
    prof["Graduated"] = last_status.eq("Graduated").astype(int)
    prof["First_Generation"] = g["First_Generation"].first()
    prof["Scholarship"] = g["Scholarship"].first()
    prof["N_Semesters"] = g.size()
    prof["Family_Income"] = g["Family_Income"].first()  # thu nhập gốc (có thể thiếu), chỉ để mô tả cụm
    return prof


def scan_k(profile: pd.DataFrame, ks=range(2, 11), sample: int = 5000) -> pd.DataFrame:
    """Elbow (inertia) và Silhouette (trên mẫu `sample` sinh viên) cho từng k."""
    X = StandardScaler().fit_transform(profile[CLUSTER_FEATURES])
    idx = np.random.RandomState(RANDOM_STATE).choice(len(X), min(sample, len(X)), replace=False)
    rows = []
    for k in ks:
        km = KMeans(n_clusters=k, n_init=10, random_state=RANDOM_STATE).fit(X)
        rows.append({"k": k, "inertia": km.inertia_, "silhouette": silhouette_score(X[idx], km.labels_[idx])})
    return pd.DataFrame(rows).set_index("k")


def fit_clusters(profile: pd.DataFrame, k: int = N_CLUSTERS) -> tuple[np.ndarray, KMeans, StandardScaler]:
    scaler = StandardScaler()
    X = scaler.fit_transform(profile[CLUSTER_FEATURES])
    km = KMeans(n_clusters=k, n_init=10, random_state=RANDOM_STATE).fit(X)
    return km.labels_, km, scaler


def describe_clusters(profile: pd.DataFrame, labels: np.ndarray) -> pd.DataFrame:
    p = profile.assign(cluster_id=labels)
    table = p.groupby("cluster_id").agg(
        so_sinh_vien=("Dropped", "size"),
        ty_le_bo_hoc=("Dropped", "mean"),
        ty_le_tot_nghiep=("Graduated", "mean"),
        the_he_dau=("First_Generation", "mean"),
        hoc_bong=("Scholarship", "mean"),
        **{c: (c, "mean") for c in CLUSTER_FEATURES if c != "Income_log"},
        Family_Income_trung_vi=("Family_Income", "median"),  # trung vị thật, bỏ qua sinh viên không khai báo
    )
    table["cluster_name"] = name_clusters(table)
    return table.sort_values("ty_le_bo_hoc", ascending=False)


def name_clusters(table: pd.DataFrame) -> pd.Series:
    """Đặt tên 4 cụm theo đặc điểm (không phụ thuộc số thứ tự K-Means gán ngẫu nhiên):
    rủi ro cao nhất / thấp nhất theo tỷ lệ bỏ học; 2 cụm còn lại phân biệt bằng giờ làm thêm."""
    if len(table) != 4:
        return pd.Series([f"Cụm {i}" for i in table.index], index=table.index)
    order = table["ty_le_bo_hoc"].sort_values()
    low, high = order.index[0], order.index[-1]
    middle = table.loc[order.index[1:3]]
    work_heavy = middle["Work_mean"].idxmax()
    weak_study = middle["Work_mean"].idxmin()
    return pd.Series({
        high: "Nguy cơ cao: sa sút học tập + áp lực tài chính",
        work_heavy: "Đi làm nhiều, áp lực tài chính vừa",
        weak_study: "Học lực yếu, tài chính ổn định",
        low: "Học tốt – ổn định",
    })


# ---------------------------------------------------------------- 8B. Luật kết hợp

# Ngưỡng rời rạc hóa: chọn theo ý nghĩa nghiệp vụ để luật dễ diễn giải
ITEM_DEFINITIONS = {
    "GPA_Low": "Sem_GPA < 2,0 (diện cảnh báo học vụ)",
    "Failed_2plus": "Failed_Courses ≥ 2 trong kỳ",
    "Attendance_Low": "Attendance < 75%",
    "Stress_High": "Financial_Stress ≥ 5",
    "Work_High": "Work_Hours ≥ 25 giờ/tuần",
    "GPA_Drop": "Delta_GPA ≤ −0,3 so với kỳ trước",
    "First_Gen": "Sinh viên thế hệ đầu",
    "No_Scholarship": "Không có học bổng",
    "Has_Emergency": "Có chi phí khẩn cấp trong kỳ",
    "LMS_Low": "LMS_Logins dưới phân vị 25",
    "DROPOUT": "Bỏ học ở kỳ sau (nhãn)",
}


def make_items(labeled: pd.DataFrame) -> pd.DataFrame:
    """Ma trận giao dịch One-Hot (mỗi dòng có nhãn = 1 giao dịch). Ô thiếu → không thuộc item."""
    lms_p25 = labeled["LMS_Logins"].astype(float).quantile(0.25)
    items = pd.DataFrame({
        "GPA_Low": labeled["Sem_GPA"] < 2.0,
        "Failed_2plus": labeled["Failed_Courses"] >= 2,
        "Attendance_Low": labeled["Attendance"] < 75,
        "Stress_High": labeled["Financial_Stress"] >= 5,
        "Work_High": labeled["Work_Hours"] >= 25,
        "GPA_Drop": labeled["Delta_GPA"] <= -0.3,
        "First_Gen": labeled["First_Generation"] == 1,
        "No_Scholarship": labeled["Scholarship"] == 0,
        "Has_Emergency": labeled["Has_Emergency"] == 1,
        "LMS_Low": labeled["LMS_Logins"].astype(float) < lms_p25,
        "DROPOUT": labeled[TARGET] == 1,
    })
    return items.fillna(False).astype(bool)


def mine_rules(items: pd.DataFrame, min_support: float = 0.01, min_confidence: float = 0.3,
               min_lift: float = 2.0) -> pd.DataFrame:
    """Apriori → luật có vế phải đúng bằng {DROPOUT}, lọc theo confidence và lift."""
    frequent = apriori(items, min_support=min_support, use_colnames=True)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        rules = association_rules(frequent, num_itemsets=len(items), metric="confidence",
                                  min_threshold=min_confidence)
    rules = rules[(rules["consequents"] == frozenset({"DROPOUT"})) & (rules["lift"] >= min_lift)].copy()
    rules["antecedents"] = rules["antecedents"].apply(lambda s: " + ".join(sorted(s)))
    rules["so_item"] = rules["antecedents"].str.count(r"\+") + 1
    rules["so_dong"] = (rules["support"] * len(items)).round().astype(int)
    cols = ["antecedents", "so_item", "so_dong", "support", "confidence", "lift"]
    return rules[cols].sort_values(["lift", "support"], ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------- lưu kết quả

def save_clusters(profile: pd.DataFrame, labels: np.ndarray, names: pd.Series) -> int:
    engine = db.pg_engine()
    db.run_sql_file(engine, "03_student_clusters.sql")
    rows = pd.DataFrame({
        "student_id": profile.index.astype(str),
        "cluster_id": labels.astype(int),
        "cluster_name": pd.Series(labels).map(names).values,
    })
    with engine.begin() as conn:  # cụm được tính lại toàn bộ mỗi lần → thay thế cả bảng trong 1 transaction
        conn.execute(text("DELETE FROM student_clusters"))
        rows.to_sql("student_clusters", conn, if_exists="append", index=False)
    return len(rows)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    path = config.path("features_dir") / "feature_table.parquet"
    if not path.exists():
        print(f"Không thấy {path}. Hãy chạy python -m src.analysis.features trước.")
        return 1
    features = pd.read_parquet(path)

    profile = student_profile(features)
    print("8A. Chọn số cụm (Silhouette tính trên mẫu 5.000 sinh viên):")
    print(scan_k(profile, ks=range(2, 9)).round(3).to_string())
    labels, _, _ = fit_clusters(profile)
    clusters = describe_clusters(profile, labels)
    print(f"\nHồ sơ {N_CLUSTERS} cụm:")
    print(clusters.round(2).to_string())

    reports = config.path("reports_dir")
    clusters.to_csv(reports / "cluster_profiles.csv", encoding="utf-8-sig")
    n_saved = save_clusters(profile, labels, clusters["cluster_name"])
    print(f"PostgreSQL student_clusters: {n_saved:,} dòng")

    labeled = features[features["Censored"] == 0]
    rules = mine_rules(make_items(labeled))
    rules.to_csv(reports / "association_rules.csv", index=False, encoding="utf-8-sig")
    print(f"\n8B. {len(rules)} luật → DROPOUT (support ≥ 0,01; confidence ≥ 0,3; lift ≥ 2), "
          f"tỷ lệ bỏ học nền {labeled[TARGET].mean():.1%}:")
    print(rules.round(3).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
