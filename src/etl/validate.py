"""Bước 3 – Kiểm tra chất lượng dữ liệu (Data Profiling & Validation).

Chạy:  python -m src.etl.validate [--file PATH] [--report PATH]
  Mặc định đọc lô SUCCESS mới nhất trong ingestion_log từ MinIO (bucket raw).
  --file dùng một file CSV trên máy (để thử data contract với file hỏng).

Mỗi kiểm tra trả về một trạng thái:
  OK    – sạch
  WARN  – có vấn đề đã biết, sẽ xử lý ở B4/B9/B10 (không chặn pipeline)
  ERROR – vi phạm data contract, chặn pipeline (mã thoát 1)
"""

import argparse
import io
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd
from matplotlib.figure import Figure  # vẽ không qua pyplot → không đổi backend của nơi import module này
from sqlalchemy import text

from src.core import config, db
from src.etl.ingest import check_schema
from src.core.schema import (
    COLUMNS, GENDER_MAP, HOUSING_VALUES, NULLABLE_COLUMNS, NUMERIC_KINDS, RANGES, STATIC_COLUMNS,
    STATUS_VALUES,
)

MISSING_MAX = 0.10       # tỷ lệ thiếu tối đa mỗi cột (khớp ngưỡng giám sát ở B16)
OUT_OF_RANGE_MAX = 0.01  # tỷ lệ giá trị ngoài miền tối đa mỗi cột


@dataclass
class CheckResult:
    name: str
    status: str  # OK / WARN / ERROR
    summary: str
    table: pd.DataFrame | None = None


def _status(errors: bool, warnings: bool) -> str:
    return "ERROR" if errors else "WARN" if warnings else "OK"


# ---------------------------------------------------------------- đọc dữ liệu

def to_typed(raw: pd.DataFrame) -> pd.DataFrame:
    """Chuyển DataFrame đọc dạng chuỗi sang đúng kiểu; ô trống thành NaN/NA."""
    df = pd.DataFrame(index=raw.index)
    for col, kind in COLUMNS.items():
        values = raw[col].str.strip().replace("", pd.NA)
        df[col] = pd.to_numeric(values) if kind in NUMERIC_KINDS else values
    return df


def load_latest_batch() -> tuple[pd.DataFrame, dict]:
    with db.pg_engine().connect() as conn:
        row = conn.execute(
            text(
                "SELECT batch_id, bucket, object_key, md5 FROM ingestion_log "
                "WHERE status = 'SUCCESS' ORDER BY ingested_at DESC LIMIT 1"
            )
        ).mappings().first()
    if row is None:
        raise RuntimeError("Chưa có lô SUCCESS nào trong ingestion_log. Hãy chạy python -m src.etl.ingest trước.")
    response = db.minio_client().get_object(row["bucket"], row["object_key"])
    try:
        content = response.read()
    finally:
        response.close()
        response.release_conn()
    raw = pd.read_csv(io.BytesIO(content), dtype=str, keep_default_na=False, encoding="utf-8-sig")
    source = {"Nguồn": f"s3://{row['bucket']}/{row['object_key']}", "batch_id": row["batch_id"], "MD5": row["md5"]}
    return raw, source


def load_file(path: Path) -> tuple[pd.DataFrame, dict]:
    raw = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    return raw, {"Nguồn": str(path)}


# ---------------------------------------------------------------- các kiểm tra

def check_missing(df: pd.DataFrame) -> CheckResult:
    n = df.isna().sum()
    table = pd.DataFrame({"so_dong_thieu": n, "ty_le_%": (n / len(df) * 100).round(2)})
    table = table[table["so_dong_thieu"] > 0].sort_values("so_dong_thieu", ascending=False)
    table["duoc_phep_thieu"] = table.index.isin(NULLABLE_COLUMNS)
    too_high = table[table["ty_le_%"] > MISSING_MAX * 100]
    not_allowed = table[~table["duoc_phep_thieu"]]
    summary = (
        "Không có giá trị thiếu" if table.empty
        else ", ".join(f"{c}: {int(r.so_dong_thieu):,} ({r['ty_le_%']}%)" for c, r in table.iterrows())
    )
    if not too_high.empty:
        summary += f". Vượt ngưỡng {MISSING_MAX:.0%}: {list(too_high.index)}"
    if not not_allowed.empty:
        summary += f". Cột không được phép thiếu: {list(not_allowed.index)}"
    errors = not too_high.empty or not not_allowed.empty
    return CheckResult("Giá trị thiếu (Completeness)", _status(errors, not table.empty), summary, table)


def check_ranges(df: pd.DataFrame) -> CheckResult:
    rows = []
    for col, (lo, hi) in RANGES.items():
        s = df[col]
        below = int((s < lo).sum()) if lo is not None else 0
        above = int((s > hi).sum()) if hi is not None else 0
        rows.append({"cot": col, "mien": f"[{lo}, {'∞' if hi is None else hi}]",
                     "min": s.min(), "max": s.max(), "duoi_min": below, "tren_max": above})
    for col, kind in COLUMNS.items():
        if kind == "binary":
            bad = int((~df[col].isin([0, 1]) & df[col].notna()).sum())
            rows.append({"cot": col, "mien": "{0, 1}", "min": df[col].min(), "max": df[col].max(),
                         "duoi_min": 0, "tren_max": bad})
    table = pd.DataFrame(rows).set_index("cot")
    table["vi_pham"] = table["duoi_min"] + table["tren_max"]
    table["ty_le_%"] = (table["vi_pham"] / len(df) * 100).round(2)
    violations = table[table["vi_pham"] > 0]
    too_many = violations[violations["ty_le_%"] > OUT_OF_RANGE_MAX * 100]
    summary = (
        "Mọi cột nằm trong miền hợp lệ" if violations.empty
        else ", ".join(f"{c}: {int(r.vi_pham):,} dòng ({r['ty_le_%']}%)" for c, r in violations.iterrows())
    )
    return CheckResult("Miền giá trị (Validity)", _status(not too_many.empty, not violations.empty), summary, table)


def check_financial_stress_scale(df: pd.DataFrame) -> CheckResult:
    """Financial_Stress được mô tả là thang 1–5; đo phần vượt thang và quan hệ với tỷ lệ bỏ học."""
    fs = df["Financial_Stress"]
    above = int((fs > 5).sum())
    labeled = df[df["Censored"] == 0]
    bucket = labeled["Financial_Stress"].clip(upper=10).astype(int).rename("muc")
    table = labeled.groupby(bucket)["Target_Dropout_Next_Sem"].agg(so_dong="size", ty_le_bo_hoc="mean")
    table["ty_le_bo_hoc"] = (table["ty_le_bo_hoc"] * 100).round(1)
    table.index = [f"{i}" if i < 10 else "≥10" for i in table.index]
    summary = (
        f"{above:,} dòng > 5 (trung vị {fs.median():.1f}, P99 {fs.quantile(0.99):.1f}, max {fs.max():.1f}). "
        f"Tỷ lệ bỏ học tăng từ {table['ty_le_bo_hoc'].iloc[0]}% (mức 1) lên {table['ty_le_bo_hoc'].iloc[-1]}% "
        "(mức ≥10), nên giá trị cao là tín hiệu thật: GIỮ NGUYÊN, không chặn về 5."
    )
    return CheckResult("Thang đo Financial_Stress", "WARN" if above else "OK", summary, table)


def check_categories(df: pd.DataFrame) -> CheckResult:
    rows = []
    for value, count in df["Gender"].value_counts(dropna=False).items():
        group = GENDER_MAP.get(str(value).strip().lower(), "KHÔNG XÁC ĐỊNH")
        rows.append({"cot": "Gender", "gia_tri": value, "so_dong": count, "nhom_chuan": group})
    for col, allowed in (("Housing_Status", HOUSING_VALUES), ("End_of_Semester_Status", STATUS_VALUES)):
        for value, count in df[col].value_counts(dropna=False).items():
            rows.append({"cot": col, "gia_tri": value, "so_dong": count,
                         "nhom_chuan": value if value in allowed else "KHÔNG XÁC ĐỊNH"})
    table = pd.DataFrame(rows)
    unknown = table[table["nhom_chuan"] == "KHÔNG XÁC ĐỊNH"]
    gender_variants = int((table["cot"] == "Gender").sum())
    gender_groups = table.loc[table["cot"] == "Gender", "nhom_chuan"].nunique()
    summary = f"Gender có {gender_variants} cách ghi cho {gender_groups} nhóm chuẩn"
    if not unknown.empty:
        summary += f"; giá trị không xác định: {unknown[['cot', 'gia_tri']].values.tolist()}"
    return CheckResult("Giá trị phân loại (Consistency)",
                       _status(not unknown.empty, gender_variants > gender_groups), summary, table)


def check_duplicates(df: pd.DataFrame) -> CheckResult:
    n = int(df.duplicated(subset=["Student_ID", "Semester"]).sum())
    summary = "Không có dòng trùng (Student_ID, Semester)" if n == 0 else f"{n:,} dòng trùng khóa, B4 giữ bản cuối"
    return CheckResult("Trùng khóa (Uniqueness)", "WARN" if n else "OK", summary)


def check_semester_continuity(df: pd.DataFrame) -> CheckResult:
    g = df.groupby("Student_ID")["Semester"]
    n_rows = g.size()
    ok = (g.min() == 1) & (g.max() == n_rows) & (g.nunique() == n_rows)
    bad = ok[~ok].index.tolist()
    per_student = n_rows.value_counts().sort_index().rename("so_sinh_vien").to_frame()
    per_student.index.name = "so_ky"
    summary = (
        f"{len(n_rows):,} sinh viên, 100% có học kỳ liên tục từ kỳ 1 (trung bình {n_rows.mean():.2f} kỳ)"
        if not bad else f"{len(bad):,} sinh viên có học kỳ không liên tục, ví dụ {bad[:5]}"
    )
    return CheckResult("Tính liên tục học kỳ", "ERROR" if bad else "OK", summary, per_student)


def check_static_columns(df: pd.DataFrame) -> CheckResult:
    nunique = df.groupby("Student_ID")[STATIC_COLUMNS].nunique()  # bỏ qua NaN
    violations = (nunique > 1).sum().rename("so_sinh_vien_vi_pham").to_frame()
    bad = violations[violations["so_sinh_vien_vi_pham"] > 0]
    summary = (
        f"{len(STATIC_COLUMNS)} cột tĩnh không đổi trong cùng sinh viên" if bad.empty
        else ", ".join(f"{c}: {int(r.iloc[0]):,} sinh viên" for c, r in bad.iterrows())
    )
    return CheckResult("Cột tĩnh theo sinh viên", "ERROR" if not bad.empty else "OK", summary, violations)


def check_label_logic(df: pd.DataFrame) -> CheckResult:
    d = df.sort_values(["Student_ID", "Semester"])
    is_last = ~d["Student_ID"].duplicated(keep="last")
    terminal = d["End_of_Semester_Status"].isin(["Dropped_Out", "Graduated"]) | (d["Censored"] == 1)

    issues = {
        "Target=1 nhưng trạng thái khác Dropped_Out (hoặc ngược lại)":
            int(((d["Target_Dropout_Next_Sem"] == 1) != (d["End_of_Semester_Status"] == "Dropped_Out")).sum()),
        "Kết cục (bỏ học / tốt nghiệp / bị cắt) không ở kỳ cuối": int((terminal & ~is_last).sum()),
        "Kỳ cuối không có kết cục": int((is_last & ~terminal).sum()),
        "Censored=1 nhưng trạng thái khác Enrolled":
            int(((d["Censored"] == 1) & (d["End_of_Semester_Status"] != "Enrolled")).sum()),
    }
    last = d[is_last]
    outcome = last["End_of_Semester_Status"].where(last["Censored"] == 0, "Censored (bị cắt)")
    labeled = d[d["Censored"] == 0]
    table = pd.concat([
        pd.Series(issues, name="so_dong").to_frame().assign(nhom="Vi phạm logic"),
        outcome.value_counts().rename("so_dong").to_frame().assign(nhom="Kết cục của sinh viên"),
        pd.DataFrame({"so_dong": [len(labeled), int(labeled["Target_Dropout_Next_Sem"].sum())],
                      "nhom": "Tập có nhãn (Censored=0)"},
                     index=["Số dòng", "Số dòng bỏ học"]),
    ])
    n_issues = sum(issues.values())
    summary = (
        f"Target=1 ⇔ Dropped_Out trên 100% dòng (rò rỉ nhãn: loại End_of_Semester_Status, Censored khỏi đặc trưng). "
        f"{int((d['Censored'] == 1).sum()):,} dòng Censored=1 có nhãn chưa xác nhận → tập chấm điểm. "
        f"Tập có nhãn: {len(labeled):,} dòng, lớp bỏ học {labeled['Target_Dropout_Next_Sem'].mean():.1%}."
        if n_issues == 0 else f"{n_issues:,} vi phạm logic nhãn: {[k for k, v in issues.items() if v]}"
    )
    return CheckResult("Logic nhãn & dữ liệu bị cắt", "ERROR" if n_issues else "WARN", summary, table)


DATA_CHECKS = [
    check_missing, check_ranges, check_financial_stress_scale, check_categories,
    check_semester_continuity, check_static_columns, check_label_logic,
]


def validate(raw: pd.DataFrame) -> tuple[list[CheckResult], pd.DataFrame | None]:
    errors = check_schema(raw)
    if errors:
        return [CheckResult("Schema", "ERROR", " | ".join(errors))], None
    df = to_typed(raw)
    results = [CheckResult("Schema", "OK", f"{len(df):,} dòng × {df.shape[1]} cột, đúng 22 cột theo src/core/schema.py")]
    # Trùng khóa là WARN (B4 khử trùng, giữ bản cuối) nên các kiểm tra còn lại chạy trên dữ liệu đã khử
    # trùng; nếu không, một lô nạp lại có dòng trùng sẽ bị báo nhầm ERROR ở tính liên tục / logic nhãn.
    deduped = df.drop_duplicates(subset=["Student_ID", "Semester"], keep="last")
    results += [check_duplicates(df)] + [check(deduped) for check in DATA_CHECKS]
    return results, df


# ---------------------------------------------------------------- báo cáo

def make_figures(df: pd.DataFrame, fig_dir: Path) -> list[tuple[str, str]]:
    fig_dir.mkdir(parents=True, exist_ok=True)
    figures = []

    def new_figure(figsize):
        fig = Figure(figsize=figsize)
        return fig, fig.subplots()

    def save(fig, name, caption):
        fig.tight_layout()
        fig.savefig(fig_dir / name, dpi=110)
        figures.append((name, caption))

    missing = df.isna().mean().mul(100)
    missing = missing[missing > 0].sort_values()
    fig, ax = new_figure((6, 2.5))
    ax.barh(missing.index, missing.values, color="#4C72B0")
    ax.axvline(MISSING_MAX * 100, color="#C44E52", ls="--", label=f"Ngưỡng {MISSING_MAX:.0%}")
    ax.set_xlabel("% dòng thiếu")
    ax.legend()
    save(fig, "dq_missing.png", "Tỷ lệ thiếu theo cột (đường đỏ: ngưỡng data contract)")

    fig, ax = new_figure((6, 3))
    ax.hist(df["Attendance"], bins=110, color="#4C72B0")
    for x in (0, 100):
        ax.axvline(x, color="#C44E52", ls="--")
    ax.set_xlabel("Attendance (%)")
    ax.set_ylabel("Số dòng")
    n_out = int(((df["Attendance"] < 0) | (df["Attendance"] > 100)).sum())
    save(fig, "dq_attendance.png", f"Attendance: {n_out:,} dòng nằm ngoài [0, 100] (đường đỏ): giá trị âm là mã lỗi −2 → thiếu; > 100 → clip")

    labeled = df[df["Censored"] == 0]
    rate = labeled.groupby(labeled["Financial_Stress"].clip(upper=10).astype(int))["Target_Dropout_Next_Sem"].mean()
    fig, ax1 = new_figure((6, 3))
    ax1.hist(df["Financial_Stress"], bins=60, color="#4C72B0")
    ax1.axvline(5, color="#C44E52", ls="--")
    ax1.set_xlabel("Financial_Stress")
    ax1.set_ylabel("Số dòng")
    ax2 = ax1.twinx()
    ax2.plot(rate.index + 0.5, rate.values * 100, color="#DD8452", marker="o")
    ax2.set_ylabel("Tỷ lệ bỏ học (%)", color="#DD8452")
    save(fig, "dq_financial_stress.png",
         "Financial_Stress: phân phối (cột) và tỷ lệ bỏ học theo mức (đường cam); vạch đỏ là mốc 5 của thang mô tả")

    fig, ax = new_figure((6, 3))
    ax.hist(df["Family_Income"].dropna(), bins=80, color="#4C72B0")
    ax.set_xscale("log")
    ax.set_xlabel("Family_Income (thang log)")
    ax.set_ylabel("Số dòng")
    lo, hi = df["Family_Income"].min(), df["Family_Income"].max()
    save(fig, "dq_family_income.png",
         f"Family_Income lệch phải mạnh ({lo:,.0f} → {hi:,.0f}) → log1p cho mô hình tuyến tính")
    return figures


DECISIONS = """\
| # | Vấn đề | Quyết định xử lý | Bước |
|:---:|---|---|:---:|
| 1 | `Family_Income` thiếu | Điền theo sinh viên (ffill + bfill, vì là thuộc tính tĩnh); còn trống thì cờ `Income_Missing`, trung vị trong Pipeline | B4, B10 |
| 2 | `LMS_Logins` thiếu | Forward-fill theo sinh viên (không bfill) + cờ `LMS_Missing`; còn trống thì trung vị trong Pipeline | B4, B10 |
| 3 | `Attendance` ngoài [0, 100] | Giá trị âm luôn là −2 (mã lỗi; kỳ trước/sau quanh 86%) → coi là thiếu, điền bằng kỳ trước; > 100 (101, 105) → clip về 100 | B4 |
| 4 | `Financial_Stress` vượt thang 1 – 5 | Giữ nguyên; winsorize P99 / `log1p` chỉ cho mô hình tuyến tính | B10 |
| 5 | `Family_Income` lệch phải | `log1p` cho mô hình tuyến tính | B10 |
| 6 | `Gender` nhiều cách ghi | Map về Female / Male / Other/Unknown theo `GENDER_MAP` | B4 |
| 7 | `Housing_Status` 3 giá trị | Giữ nguyên, One-Hot | B10 |
| 8 | Trùng khóa | `drop_duplicates(keep='last')` phòng ngừa | B4 |
| 9 | Rò rỉ nhãn | Loại `End_of_Semester_Status`, `Censored` khỏi đặc trưng | B9 |
| 10 | Nhãn bị cắt (`Censored = 1`) | Loại khỏi Train/Test, dùng làm tập chấm điểm | B9, B14 |
"""


def _md_table(table: pd.DataFrame) -> str:
    return table.to_markdown() if table is not None else ""


def write_report(results: list[CheckResult], df: pd.DataFrame | None, source: dict, path: Path) -> None:
    icon = {"OK": "✅ OK", "WARN": "⚠️ WARN", "ERROR": "❌ ERROR"}
    overall = _status(any(r.status == "ERROR" for r in results), any(r.status == "WARN" for r in results))
    lines = [
        "# BÁO CÁO CHẤT LƯỢNG DỮ LIỆU",
        f"*Sinh tự động bởi `python -m src.etl.validate` lúc {datetime.now():%Y-%m-%d %H:%M}. "
        "Xem phương pháp tại `QUY_TRINH_DU_AN/GIAI_DOAN_B_KY_THUAT_DU_LIEU_ETL/B03_KIEM_TRA_CHAT_LUONG_DU_LIEU.md`.*",
        "",
        *[f"* **{k}:** `{v}`" for k, v in source.items()],
        f"* **Kết luận data contract:** {icon[overall]}"
        + (" (không có vi phạm chặn pipeline; các mục WARN đã có cách xử lý bên dưới)" if overall != "ERROR" else ""),
        "",
        "## 1. Tóm tắt",
        "",
        "| Kiểm tra | Trạng thái | Kết quả |",
        "|---|:---:|---|",
        *[f"| {r.name} | {icon[r.status]} | {r.summary} |" for r in results],
        "",
        "> **OK**: sạch · **WARN**: vấn đề đã biết, xử lý ở bước sau · **ERROR**: vi phạm data contract, chặn pipeline.",
        "",
        "## 2. Quyết định xử lý",
        "",
        DECISIONS,
        "## 3. Chi tiết từng kiểm tra",
        "",
    ]
    for r in results:
        if r.table is not None:
            lines += [f"### {r.name}", "", r.summary, "", _md_table(r.table), ""]
    if df is not None:
        figures = make_figures(df, path.parent / "figures")
        lines += ["## 4. Biểu đồ", ""]
        lines += [f"**{caption}**\n\n![{name}](figures/{name})\n" for name, caption in figures]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Kiểm tra chất lượng dữ liệu nguồn.")
    parser.add_argument("--file", type=Path, help="CSV trên máy; mặc định: lô SUCCESS mới nhất trong MinIO")
    parser.add_argument("--report", type=Path, default=config.path("reports_dir") / "data_quality_report.md")
    parser.add_argument("--no-report", action="store_true", help="Chỉ in kết quả, không ghi báo cáo")
    args = parser.parse_args()

    raw, source = load_file(args.file) if args.file else load_latest_batch()
    results, df = validate(raw)

    for k, v in source.items():
        print(f"{k}: {v}")
    for r in results:
        print(f"[{r.status:<5}] {r.name}: {r.summary}")
    if not args.no_report:
        write_report(results, df, source, args.report)
        print(f"Báo cáo: {args.report}")

    failed = [r.name for r in results if r.status == "ERROR"]
    print("Data contract: ĐẠT" if not failed else f"Data contract: KHÔNG ĐẠT ({failed})")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
