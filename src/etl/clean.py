"""Bước 4 – Làm sạch dữ liệu (Transform – Cleaning).

Chạy:  python -m src.etl.clean [--file PATH]
  Mặc định đọc lô SUCCESS mới nhất trong MinIO; --file dùng một CSV trên máy.

Chỉ gồm các biến đổi XÁC ĐỊNH (quy tắc cố định, không học thống kê từ dữ liệu).
Các thao tác cần "học" (trung vị, mean/std, winsorize) để ở B10, fit trên tập Train.

Output:
  data/processed/clean_semesters.parquet                       (79.239 × 24)
  s3://processed/academic/batch_id=<id>/clean_semesters.parquet
  reports/cleaning_log.md                                      (số dòng bị ảnh hưởng mỗi thao tác)
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.core import config, db
from src.core.schema import COLUMNS, GENDER_MAP, HOUSING_VALUES, STATIC_COLUMNS
from src.etl.validate import load_file, load_latest_batch, to_typed, validate

INT_COLUMNS = [c for c, kind in COLUMNS.items() if kind in {"int", "binary"} and c != "LMS_Logins"]
FLOAT_COLUMNS = [c for c, kind in COLUMNS.items() if kind == "float"]
OUTPUT_COLUMNS = list(COLUMNS) + ["Income_Missing", "LMS_Missing"]


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, list[tuple[str, int]]]:
    """Làm sạch DataFrame đã đúng kiểu (từ to_typed). Trả về (dữ liệu sạch, log [(thao tác, số dòng)])."""
    log = []
    n_in = len(df)

    # 1. Khử trùng lặp khóa (Student_ID, Semester), giữ bản cuối
    df = df.drop_duplicates(subset=["Student_ID", "Semester"], keep="last")
    log.append(("Khử trùng lặp (Student_ID, Semester)", n_in - len(df)))

    # 2–3. Sắp xếp theo sinh viên, học kỳ (bắt buộc trước các thao tác theo nhóm)
    df = df.sort_values(["Student_ID", "Semester"]).reset_index(drop=True)

    # 4. Chuẩn hóa Gender về 3 nhóm
    gender = df["Gender"].str.strip().str.lower().map(GENDER_MAP)
    if gender.isna().any():
        raise ValueError(f"Gender không có trong GENDER_MAP: {df.loc[gender.isna(), 'Gender'].unique()[:5]}")
    log.append(("Chuẩn hóa Gender (đổi cách ghi)", int((gender != df["Gender"]).sum())))
    df["Gender"] = gender

    # 5. Housing_Status: bỏ khoảng trắng, kiểm tra tập giá trị
    df["Housing_Status"] = df["Housing_Status"].str.strip()
    unknown = set(df["Housing_Status"].dropna()) - HOUSING_VALUES
    if unknown:
        raise ValueError(f"Housing_Status không hợp lệ: {unknown}")

    # 6. Attendance: hai loại lỗi khác nhau
    #    • < 0: luôn đúng bằng -2 (mã lỗi); kỳ trước/sau của cùng sinh viên quanh 86% → coi là THIẾU,
    #      không clip về 0 (clip sẽ tạo "0% chuyên cần" và cú sụt giả ~-86 điểm ở Delta_Attendance).
    #    • > 100: 101 hoặc 105 (đếm dư) → clip về 100.
    negative = df["Attendance"] < 0
    above = df["Attendance"] > 100
    df.loc[negative, "Attendance"] = float("nan")
    df["Attendance"] = df["Attendance"].clip(upper=100)
    log.append(("Attendance > 100 → clip về 100", int(above.sum())))

    by_student = df.groupby("Student_ID", sort=False)

    #    Giá trị âm đã thành thiếu → lấy chuyên cần kỳ trước của cùng sinh viên (ffill, không bfill)
    df["Attendance"] = by_student["Attendance"].ffill()
    log.append(("Attendance < 0 (mã lỗi -2) → thiếu, điền bằng kỳ trước", int(negative.sum() - df["Attendance"].isna().sum())))
    log.append(("Attendance vẫn thiếu (lỗi ở kỳ 1, điền ở B10)", int(df["Attendance"].isna().sum())))

    # 7. Family_Income: thuộc tính tĩnh → lấy từ kỳ khác của cùng sinh viên (ffill + bfill)
    missing_before = df["Family_Income"].isna()
    df["Family_Income"] = by_student["Family_Income"].transform(lambda s: s.ffill().bfill())
    df["Income_Missing"] = df["Family_Income"].isna().astype("int8")
    log.append(("Điền Family_Income từ kỳ khác của cùng sinh viên", int(missing_before.sum() - df["Income_Missing"].sum())))
    log.append(("Family_Income vẫn thiếu (cờ Income_Missing, điền ở B10)", int(df["Income_Missing"].sum())))

    # 8. LMS_Logins: biến động theo kỳ → chỉ lấy kỳ trước (ffill), KHÔNG bfill
    df["LMS_Missing"] = df["LMS_Logins"].isna().astype("int8")
    df["LMS_Logins"] = by_student["LMS_Logins"].ffill()
    log.append(("Điền LMS_Logins bằng kỳ trước (ffill)", int(df["LMS_Missing"].sum() - df["LMS_Logins"].isna().sum())))
    log.append(("LMS_Logins vẫn thiếu (không có kỳ trước, điền ở B10)", int(df["LMS_Logins"].isna().sum())))

    # 9. Financial_Stress, Emergency_Expense, Work_Hours: giữ nguyên (giá trị cao là tín hiệu thật)

    # Ép kiểu cuối cùng
    df[INT_COLUMNS] = df[INT_COLUMNS].astype("int64")
    df[FLOAT_COLUMNS] = df[FLOAT_COLUMNS].astype("float64")
    df["LMS_Logins"] = df["LMS_Logins"].astype("Int64")  # nullable: còn thiếu ở kỳ đầu
    df["Student_ID"] = df["Student_ID"].astype("string")
    for col in ("Gender", "Housing_Status", "End_of_Semester_Status"):
        df[col] = df[col].astype("string")

    return df[OUTPUT_COLUMNS], log


def post_checks(df: pd.DataFrame, n_expected: int) -> list[tuple[str, bool, str]]:
    """Kiểm tra sau làm sạch (mục 4.10 của B04). Trả về [(kiểm tra, đạt?, chi tiết)]."""
    static_varying = (df.groupby("Student_ID")[STATIC_COLUMNS].nunique() > 1).sum()
    income_missing_students = df.loc[df["Income_Missing"] == 1, "Student_ID"].nunique()
    return [
        ("Số dòng không đổi", len(df) == n_expected, f"{len(df):,} / {n_expected:,}"),
        ("Attendance trong [0, 100] (bỏ qua ô thiếu)", bool(df["Attendance"].dropna().between(0, 100).all()),
         f"min {df['Attendance'].min()}, max {df['Attendance'].max()}, thiếu {int(df['Attendance'].isna().sum())}"),
        ("Gender còn 3 nhóm", set(df["Gender"].unique()) <= set(GENDER_MAP.values()),
         ", ".join(sorted(df["Gender"].unique()))),
        ("Cột tĩnh không đổi trong cùng sinh viên", int(static_varying.sum()) == 0,
         f"{int(static_varying.sum())} vi phạm"),
        ("Income_Missing là thuộc tính của cả sinh viên",
         int(df.groupby("Student_ID")["Income_Missing"].nunique().max()) == 1,
         f"{income_missing_students} sinh viên không khai báo thu nhập ở kỳ nào"),
        ("Không còn trùng khóa", not df.duplicated(["Student_ID", "Semester"]).any(), ""),
        ("Đủ 24 cột", list(df.columns) == OUTPUT_COLUMNS, f"{df.shape[1]} cột"),
    ]


def content_hash(df: pd.DataFrame) -> str:
    """Hash nội dung (không phụ thuộc metadata file) để kiểm tra tính xác định."""
    return f"{pd.util.hash_pandas_object(df, index=True).sum() & 0xFFFFFFFFFFFFFFFF:016x}"


def write_log(path: Path, source: dict, log, checks, out_path: Path, object_uri: str, digest: str) -> None:
    lines = [
        "# NHẬT KÝ LÀM SẠCH DỮ LIỆU",
        f"*Sinh tự động bởi `python -m src.etl.clean` lúc {datetime.now():%Y-%m-%d %H:%M}. "
        "Phương pháp: `QUY_TRINH_DU_AN/GIAI_DOAN_B_KY_THUAT_DU_LIEU_ETL/B04_LAM_SACH_DU_LIEU.md`.*",
        "",
        *[f"* **{k}:** `{v}`" for k, v in source.items()],
        f"* **Output:** `{out_path.relative_to(config.ROOT).as_posix()}` và `{object_uri}`",
        f"* **Hash nội dung:** `{digest}`",
        "",
        "## Các thao tác",
        "",
        "| Thao tác | Số dòng |",
        "|---|---:|",
        *[f"| {name} | {n:,} |" for name, n in log],
        "",
        "## Kiểm tra sau làm sạch",
        "",
        "| Kiểm tra | Kết quả | Chi tiết |",
        "|---|:---:|---|",
        *[f"| {name} | {'✅' if ok else '❌'} | {detail} |" for name, ok, detail in checks],
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Làm sạch dữ liệu nguồn → clean_semesters.parquet.")
    parser.add_argument("--file", type=Path, help="CSV trên máy; mặc định: lô SUCCESS mới nhất trong MinIO")
    args = parser.parse_args()

    raw, source = load_file(args.file) if args.file else load_latest_batch()

    # Data contract của B3: có ERROR thì không làm sạch
    results, _ = validate(raw)
    errors = [r.name for r in results if r.status == "ERROR"]
    if errors:
        print(f"Dừng: dữ liệu không đạt data contract ({errors}). Chạy python -m src.etl.validate để xem chi tiết.")
        return 1

    df_clean, log = clean(to_typed(raw))
    checks = post_checks(df_clean, n_expected=len(raw))
    for name, n in log:
        print(f"  {name}: {n:,}")
    for name, ok, detail in checks:
        print(f"[{'OK' if ok else 'LỖI'}] {name}: {detail}")
    if not all(ok for _, ok, _ in checks):
        print("Dừng: kiểm tra sau làm sạch không đạt, không ghi output.")
        return 1

    out_path = config.path("processed_dir") / "clean_semesters.parquet"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df_clean.to_parquet(out_path, index=False)

    bucket = config.settings()["minio"]["buckets"]["processed"]
    batch_id = source.get("batch_id", "local")
    key = f"{config.settings()['minio']['raw_prefix']}/batch_id={batch_id}/clean_semesters.parquet"
    db.minio_client().fput_object(bucket, key, str(out_path), content_type="application/vnd.apache.parquet")
    object_uri = f"s3://{bucket}/{key}"

    digest = content_hash(df_clean)
    log_path = config.path("reports_dir") / "cleaning_log.md"
    write_log(log_path, source, log, checks, out_path, object_uri, digest)

    print(f"Output: {out_path} ({df_clean.shape[0]:,} × {df_clean.shape[1]})")
    print(f"        {object_uri}")
    print(f"Hash nội dung: {digest}")
    print(f"Nhật ký: {log_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
