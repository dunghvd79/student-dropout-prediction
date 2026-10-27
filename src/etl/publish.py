"""Bước 15 – Xuất dữ liệu cho dashboard (Power BI đọc PostgreSQL; Streamlit dùng chung).

Chạy:  python -m src.etl.publish

Power BI không đọc được MongoDB, nên phần theo học kỳ được tổng hợp sẵn vào PostgreSQL:
  semester_summary      bảng: mỗi học kỳ một dòng (số SV, GPA / chuyên cần / áp lực TB, tỷ lệ bỏ học…)
  v_canh_bao            view: lần chấm điểm MỚI NHẤT + hồ sơ tĩnh + cụm (một dòng / sinh viên đang học)
  v_rui_ro_theo_nhom    view: tỷ lệ mức Cao / Trung bình theo học kỳ, học bổng, thế hệ đầu, nơi ở, cụm
Bảng semester_summary được tính lại toàn bộ mỗi lần chạy (thay thế trong một transaction).
"""

import sys

import pandas as pd
from sqlalchemy import text

from src.core import db
from src.etl.load import load_analytic_table

SUMMARY_COLUMNS = ["semester", "so_sinh_vien", "so_co_nhan", "ty_le_bo_hoc", "gpa_tb", "chuyen_can_tb",
                   "ap_luc_tc_tb", "lam_them_tb", "truot_mon_tb", "so_dang_hoc"]


def semester_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Bảng sạch (B4/B5) → một dòng / học kỳ. Tỷ lệ bỏ học chỉ tính trên dòng có nhãn (Censored = 0)."""
    labeled = df[df["Censored"] == 0]
    g = df.groupby("Semester")
    out = pd.DataFrame({
        "so_sinh_vien": g["Student_ID"].nunique(),
        "so_co_nhan": labeled.groupby("Semester").size(),
        "ty_le_bo_hoc": labeled.groupby("Semester")["Target_Dropout_Next_Sem"].mean(),
        "gpa_tb": g["Sem_GPA"].mean(),
        "chuyen_can_tb": g["Attendance"].mean(),
        "ap_luc_tc_tb": g["Financial_Stress"].mean(),
        "lam_them_tb": g["Work_Hours"].mean(),
        "truot_mon_tb": g["Failed_Courses"].mean(),
        "so_dang_hoc": df[df["Censored"] == 1].groupby("Semester").size(),
    }).reset_index().rename(columns={"Semester": "semester"})
    out[["so_co_nhan", "so_dang_hoc"]] = out[["so_co_nhan", "so_dang_hoc"]].fillna(0).astype(int)
    return out[SUMMARY_COLUMNS]


VIEWS = """
CREATE OR REPLACE VIEW v_canh_bao AS
SELECT p.run_id, p.run_date, p.model_version, p.student_id, p.semester,
       p.risk_score, p.risk_level,
       CASE p.risk_level WHEN 'Cao' THEN 1 WHEN 'Trung bình' THEN 2 ELSE 3 END AS thu_tu_muc,
       p.top_reason_1, p.top_reason_2, p.top_reason_3,
       split_part(p.top_reason_1, ':', 1) AS nhom_ly_do_1,
       s.age, s.gender, s.first_generation, s.household_size, s.housing_status, s.family_income,
       f.scholarship, f.tuition_base, c.cluster_id, c.cluster_name
FROM predictions p
JOIN students s USING (student_id)
JOIN financial_profiles f USING (student_id)
LEFT JOIN student_clusters c USING (student_id)
WHERE p.run_id = (SELECT run_id FROM predictions ORDER BY run_date DESC LIMIT 1);

CREATE OR REPLACE VIEW v_rui_ro_theo_nhom AS
WITH base AS (
    SELECT risk_level, semester::text AS hoc_ky,
           CASE WHEN scholarship THEN 'Có học bổng' ELSE 'Không học bổng' END AS hoc_bong,
           CASE WHEN first_generation THEN 'Thế hệ đầu' ELSE 'Không phải thế hệ đầu' END AS the_he_dau,
           housing_status AS noi_o, coalesce(cluster_name, 'Chưa phân cụm') AS cum
    FROM v_canh_bao
), long AS (
    SELECT 'Học kỳ' AS chieu, hoc_ky AS nhom, risk_level FROM base
    UNION ALL SELECT 'Học bổng', hoc_bong, risk_level FROM base
    UNION ALL SELECT 'Thế hệ đầu', the_he_dau, risk_level FROM base
    UNION ALL SELECT 'Nơi ở', noi_o, risk_level FROM base
    UNION ALL SELECT 'Cụm sinh viên', cum, risk_level FROM base
)
SELECT chieu, nhom, count(*) AS so_sinh_vien,
       avg((risk_level = 'Cao')::int)::numeric(6, 4) AS ty_le_cao,
       avg((risk_level = 'Trung bình')::int)::numeric(6, 4) AS ty_le_trung_binh
FROM long GROUP BY chieu, nhom;
"""


def publish() -> pd.DataFrame:
    summary = semester_summary(load_analytic_table())
    engine = db.pg_engine()
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS semester_summary (
                semester INT PRIMARY KEY, so_sinh_vien INT, so_co_nhan INT, ty_le_bo_hoc NUMERIC(6, 4),
                gpa_tb NUMERIC(5, 3), chuyen_can_tb NUMERIC(6, 2), ap_luc_tc_tb NUMERIC(6, 3),
                lam_them_tb NUMERIC(6, 2), truot_mon_tb NUMERIC(5, 3), so_dang_hoc INT,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now())"""))
        conn.execute(text("DELETE FROM semester_summary"))
        summary.to_sql("semester_summary", conn, if_exists="append", index=False)
        conn.execute(text(VIEWS))
    return summary


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    summary = publish()
    with db.pg_engine().connect() as conn:
        n_view = conn.execute(text("SELECT count(*) FROM v_canh_bao")).scalar()
        n_pred = conn.execute(text(
            "SELECT count(*) FROM predictions WHERE run_id = "
            "(SELECT run_id FROM predictions ORDER BY run_date DESC LIMIT 1)")).scalar()
        groups = conn.execute(text("SELECT count(DISTINCT chieu) FROM v_rui_ro_theo_nhom")).scalar()
    checks = [
        ("semester_summary đủ 8 học kỳ", len(summary) == 8, f"{len(summary)} dòng"),
        ("v_canh_bao = số dòng lần chấm mới nhất", n_view == n_pred and n_view > 0, f"{n_view:,} / {n_pred:,}"),
        ("v_rui_ro_theo_nhom có 5 chiều", groups == 5, f"{groups} chiều"),
    ]
    print(summary.round(3).to_string(index=False))
    for name, ok, detail in checks:
        print(f"[{'OK' if ok else 'LỖI'}] {name}: {detail}")
    return 0 if all(ok for _, ok, _ in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
