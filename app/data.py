"""Lớp dữ liệu của ứng dụng Streamlit (B15): đọc PostgreSQL / MongoDB / mô hình, có cache.

Chỉ ĐỌC kết quả của B8 (cụm), B14 (predictions) và kho B5; giải thích SHAP tính lại bằng đúng mô hình
đã chấm điểm (cùng phiên bản trong predictions.model_version) để waterfall khớp risk_score.
"""

import json

import numpy as np
import pandas as pd
import streamlit as st
from sqlalchemy import text

from app.style import GENDER_VI, HOUSING_VI
from src.core import config, db
from src.etl.load import from_documents, mongo_collection
from src.ml.explain import GROUPS, explain
from src.ml.split import load_spec, load_splits

# Gợi ý can thiệp theo nhóm lý do (mục 2.5 của B15: dashboard phải nói "nên làm gì")
ACTIONS = {
    "hoc_tap": "Hẹn gặp cố vấn học tập, rà lại kế hoạch học và các môn đang yếu.",
    "truot_mon": "Đăng ký học lại hoặc phụ đạo các môn đã trượt; cân nhắc giảm tín chỉ kỳ tới.",
    "ap_luc_tai_chinh": "Giới thiệu học bổng, quỹ hỗ trợ hoặc giãn thời hạn đóng học phí.",
    "thu_nhap": "Kiểm tra điều kiện miễn giảm học phí theo hoàn cảnh gia đình.",
    "dot_xuat": "Giới thiệu quỹ hỗ trợ khẩn cấp của trường.",
    "hoc_bong": "Rà các học bổng đang mở mà sinh viên đủ điều kiện nộp.",
    "chuyen_can": "Liên hệ trực tiếp sinh viên để hỏi lý do vắng học.",
    "lms": "Nhắc sinh viên theo dõi bài trên LMS; hỏi xem có khó khăn khi truy cập không.",
    "lam_them": "Trao đổi về giờ làm thêm; giới thiệu việc làm bán thời gian trong trường.",
    "the_he_dau": "Kết nối chương trình đồng hành dành cho sinh viên thế hệ đầu.",
    "tien_trinh": "Rà soát khối lượng tín chỉ đăng ký kỳ tới.",
}


def _read(sql: str, **params) -> pd.DataFrame:
    with db.pg_engine().connect() as conn:
        return pd.read_sql(text(sql), conn, params=params)


@st.cache_data(ttl=300, show_spinner=False)
def latest_run() -> dict | None:
    df = _read("SELECT run_id, max(run_date) AS run_date, max(model_version) AS model_version, count(*) AS n "
               "FROM predictions GROUP BY run_id ORDER BY max(run_date) DESC LIMIT 1")
    return None if df.empty else df.iloc[0].to_dict()


@st.cache_data(ttl=300, show_spinner=False)
def predictions(run_id: str) -> pd.DataFrame:
    """Một dòng / sinh viên đang học: điểm rủi ro + hồ sơ tĩnh + cụm."""
    return _read("""
        SELECT p.student_id, p.semester, p.risk_score::float8 AS risk_score, p.risk_level,
               p.top_reason_1, p.top_reason_2, p.top_reason_3,
               s.age, s.gender, s.first_generation, s.household_size, s.housing_status,
               s.family_income::float8 AS family_income, f.scholarship,
               c.cluster_name
        FROM predictions p
        JOIN students s USING (student_id)
        JOIN financial_profiles f USING (student_id)
        LEFT JOIN student_clusters c USING (student_id)
        WHERE p.run_id = :run_id
    """, run_id=run_id).assign(gender=lambda d: d["gender"].map(GENDER_VI).fillna(d["gender"]),
                              housing_status=lambda d: d["housing_status"].map(HOUSING_VI).fillna(d["housing_status"]))


@st.cache_data(ttl=300, show_spinner=False)
def trajectory(student_id: str) -> pd.DataFrame:
    client, coll = mongo_collection()
    try:
        docs = list(coll.find({"student_id": student_id}, {"_id": 0}).sort("semester", 1))
    finally:
        client.close()
    return from_documents(docs) if docs else pd.DataFrame()


@st.cache_data(show_spinner=False)
def base_rate() -> float:
    """Tỷ lệ bỏ học kỳ sau trên toàn bộ dữ liệu có nhãn (mốc so sánh trong câu kết luận)."""
    s = load_splits()
    return float(pd.concat([s.y_train, s.y_test]).mean())


@st.cache_data(show_spinner=False)
def thresholds() -> dict:
    return json.loads((config.ROOT / "config" / "risk_thresholds.json").read_text(encoding="utf-8"))


@st.cache_resource(show_spinner="Đang nạp mô hình và tính giải thích…")
def explanations(model_version: str):
    """SHAP theo nhóm cho toàn bộ scoring set, bằng đúng phiên bản mô hình đã chấm điểm."""
    import mlflow.sklearn

    cfg = config.settings()["mlflow"]
    if model_version == "local":
        import joblib
        model = joblib.load(config.path("models_dir") / "dropout_model.joblib")
    else:
        mlflow.set_tracking_uri(cfg["tracking_uri"])
        model = mlflow.sklearn.load_model(f"models:/{cfg['model_name']}/{model_version}")
    splits, spec = load_splits(), load_spec()
    X = splits.X_score.reset_index(drop=True)
    ex = explain(model, X, splits.X_train, spec)
    ids = splits.keys_score["Student_ID"].astype(str).values
    groups = ex.groups.set_index(pd.Index(ids, name="student_id"))
    features = X.set_index(pd.Index(ids, name="student_id"))
    return ex.base, groups, features


def group_label(key: str) -> str:
    return GROUPS[key][0]


@st.cache_data(ttl=300, show_spinner=False)
def semester_summary() -> pd.DataFrame:
    """Cùng bảng Power BI đọc (python -m src.etl.publish)."""
    return _read("SELECT * FROM semester_summary ORDER BY semester")


@st.cache_data(ttl=300, show_spinner=False)
def risk_by_group() -> pd.DataFrame:
    df = _read("SELECT chieu, nhom, so_sinh_vien, ty_le_cao::float8 AS ty_le_cao, "
               "ty_le_trung_binh::float8 AS ty_le_trung_binh FROM v_rui_ro_theo_nhom")
    housing = df["chieu"] == "Nơi ở"
    df.loc[housing, "nhom"] = df.loc[housing, "nhom"].map(HOUSING_VI).fillna(df.loc[housing, "nhom"])
    return df


@st.cache_data(show_spinner=False)
def cluster_profiles() -> pd.DataFrame:
    df = pd.read_csv(config.path("reports_dir") / "cluster_profiles.csv", encoding="utf-8-sig")
    return df.assign(bo_hoc_pct=df["ty_le_bo_hoc"] * 100)


# Item của luật kết hợp (src/analysis/mining.make_items) → câu cho cán bộ đọc
ITEM_TEXT = {
    "GPA_Low": "GPA kỳ dưới 2,0", "Failed_2plus": "trượt từ 2 môn", "Attendance_Low": "chuyên cần dưới 75%",
    "Stress_High": "áp lực tài chính từ 5", "Work_High": "làm thêm từ 25 giờ/tuần", "GPA_Drop": "GPA giảm từ 0,3",
    "First_Gen": "thế hệ đầu vào đại học", "No_Scholarship": "không có học bổng",
    "Has_Emergency": "có chi phí đột xuất", "LMS_Low": "ít đăng nhập LMS",
}


@st.cache_data(show_spinner=False)
def association_rules() -> pd.DataFrame:
    rules = pd.read_csv(config.path("reports_dir") / "association_rules.csv", encoding="utf-8-sig")
    text_ = rules["antecedents"].map(lambda s: ", ".join(ITEM_TEXT.get(i.strip(), i.strip()) for i in s.split("+")))
    rules["mo_ta"] = text_.str[0].str.upper() + text_.str[1:]
    rules["ty_le_pct"] = rules["confidence"] * 100
    rules["gap"] = rules["lift"].map(lambda v: f"{v:.1f} lần".replace(".", ","))
    return rules


def sigmoid(x):
    return 1 / (1 + np.exp(-x))
