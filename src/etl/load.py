"""Bước 5 – Nạp dữ liệu sạch vào kho Polyglot (Load).

Chạy:  python -m src.etl.load [--file PATH]
  Mặc định đọc data/processed/clean_semesters.parquet (output của B4).

Tách dữ liệu:
  PostgreSQL  students            – 7 thuộc tính tĩnh + income_missing   (1 dòng / sinh viên)
              financial_profiles  – scholarship, tuition_base            (1 dòng / sinh viên)
  MongoDB     academic_semesters  – 1 document / (sinh viên, học kỳ), các object lồng nhau

Thu nhập: students.family_income là giá trị sinh viên đã khai báo (ở bất kỳ kỳ nào), income_missing = không
khai báo ở kỳ nào. Việc "đã biết thu nhập tại kỳ t" lưu theo kỳ trong MongoDB (socio_economic.income_missing);
bảng phẳng đọc lại để trống Family_Income ở các kỳ chưa khai báo, đúng như bảng sạch của B4.

Nạp kiểu upsert nên chạy lại bao nhiêu lần số lượng vẫn đúng (idempotent).
Hàm load_analytic_table() đọc lại 2 CSDL và trả về bảng phẳng giống clean_semesters.parquet.
"""

import argparse
import sys
from pathlib import Path

import pandas as pd
from pymongo import ASCENDING, MongoClient, ReplaceOne
from sqlalchemy import text

from src.core import config, db
from src.etl.clean import FLOAT_COLUMNS, INT_COLUMNS, OUTPUT_COLUMNS

# Cột (tên gốc) → cột PostgreSQL
STUDENT_FIELDS = {
    "Student_ID": "student_id", "Age": "age", "Gender": "gender", "First_Generation": "first_generation",
    "Household_Size": "household_size", "Housing_Status": "housing_status", "Family_Income": "family_income",
}
PROFILE_FIELDS = {"Student_ID": "student_id", "Scholarship": "scholarship", "Tuition_Base": "tuition_base"}
BOOL_FIELDS = {"first_generation", "income_missing", "scholarship"}

# Cấu trúc document MongoDB: object lồng nhau → {tên gốc: tên trường}
DOC_LAYOUT = {
    "academic_performance": {"Sem_GPA": "sem_gpa", "Failed_Courses": "failed_courses", "Course_Load": "course_load"},
    "engagement": {"Attendance": "attendance", "LMS_Logins": "lms_logins",
                   "Advising_Visits": "advising_visits", "LMS_Missing": "lms_missing"},
    "socio_economic": {"Work_Hours": "work_hours", "Financial_Stress": "financial_stress",
                       "Emergency_Expense": "emergency_expense", "Income_Missing": "income_missing"},
    "outcome": {"Target_Dropout_Next_Sem": "target_dropout_next_sem",
                "End_of_Semester_Status": "end_of_semester_status", "Censored": "censored"},
}


# ---------------------------------------------------------------- chuyển đổi (thuần, có unit test)

def split_static(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Lấy 1 dòng / sinh viên cho 2 bảng tĩnh (cột tĩnh đã được B3/B4 kiểm tra không đổi)."""
    df = df.sort_values(["Student_ID", "Semester"])
    first = df.drop_duplicates("Student_ID").set_index("Student_ID")
    # Thu nhập có thể chỉ được khai báo từ kỳ sau (kỳ đầu để trống) → lấy giá trị khai báo đầu tiên
    first["Family_Income"] = df.groupby("Student_ID")["Family_Income"].first()
    first = first.reset_index()
    students = first[list(STUDENT_FIELDS)].rename(columns=STUDENT_FIELDS)
    students["income_missing"] = students["family_income"].isna()
    profiles = first[list(PROFILE_FIELDS)].rename(columns=PROFILE_FIELDS)
    for frame in (students, profiles):
        for col in BOOL_FIELDS & set(frame.columns):
            frame[col] = frame[col].astype(bool)
    return students.reset_index(drop=True), profiles.reset_index(drop=True)


def _py(value):
    """Giá trị numpy/pandas → kiểu Python mà BSON hiểu; NA → None."""
    if pd.isna(value):
        return None
    return value.item() if hasattr(value, "item") else value


def to_document(row: dict) -> dict:
    doc = {"student_id": str(row["Student_ID"]), "semester": int(row["Semester"])}
    for group, fields in DOC_LAYOUT.items():
        doc[group] = {name: _py(row[col]) for col, name in fields.items()}
    return doc


def from_documents(docs: list[dict]) -> pd.DataFrame:
    rows = []
    for doc in docs:
        row = {"Student_ID": doc["student_id"], "Semester": doc["semester"]}
        for group, fields in DOC_LAYOUT.items():
            for col, name in fields.items():
                row[col] = doc[group][name]
        rows.append(row)
    return pd.DataFrame(rows)


def restore_types(df: pd.DataFrame) -> pd.DataFrame:
    """Ép kiểu bảng ghép về đúng kiểu của clean_semesters.parquet."""
    df = df[OUTPUT_COLUMNS].copy()
    df[INT_COLUMNS] = df[INT_COLUMNS].astype("int64")
    df[FLOAT_COLUMNS] = df[FLOAT_COLUMNS].astype("float64")
    df["LMS_Logins"] = df["LMS_Logins"].astype("Int64")
    df[["Income_Missing", "LMS_Missing"]] = df[["Income_Missing", "LMS_Missing"]].astype("int8")
    for col in ("Student_ID", "Gender", "Housing_Status", "End_of_Semester_Status"):
        df[col] = df[col].astype("string")
    return df.sort_values(["Student_ID", "Semester"]).reset_index(drop=True)


def merge_static(semesters: pd.DataFrame, static: pd.DataFrame) -> pd.DataFrame:
    """Ghép phần theo kỳ (MongoDB) với phần tĩnh (PostgreSQL, đã đổi về tên gốc) → bảng phẳng như B4."""
    df = semesters.merge(static, on="Student_ID", how="left", validate="many_to_one")
    df.loc[df["Income_Missing"] == 1, "Family_Income"] = float("nan")  # kỳ chưa khai báo: chưa biết thu nhập
    return restore_types(df)


def static_from_tables(students: pd.DataFrame, profiles: pd.DataFrame) -> pd.DataFrame:
    """students + financial_profiles (tên cột PostgreSQL) → khung tĩnh với tên cột gốc."""
    static = students.drop(columns="income_missing").merge(profiles, on="student_id")
    static = static.rename(columns={v: k for k, v in {**STUDENT_FIELDS, **PROFILE_FIELDS}.items()})
    for col in ("First_Generation", "Scholarship"):
        static[col] = static[col].astype(int)
    return static


# ---------------------------------------------------------------- PostgreSQL

def _upsert(conn, df: pd.DataFrame, table: str, key: str) -> None:
    """Ghi vào bảng tạm rồi INSERT … ON CONFLICT DO UPDATE trong cùng transaction."""
    staging = f"_staging_{table}"
    df.to_sql(staging, conn, if_exists="replace", index=False)
    cols = ", ".join(df.columns)
    updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in df.columns if c != key)
    conn.execute(text(
        f"INSERT INTO {table} ({cols}) SELECT {cols} FROM {staging} "
        f"ON CONFLICT ({key}) DO UPDATE SET {updates}, updated_at = now()"
    ))
    conn.execute(text(f"DROP TABLE {staging}"))


def load_postgres(students: pd.DataFrame, profiles: pd.DataFrame) -> None:
    engine = db.pg_engine()
    db.run_sql_file(engine, "02_core_tables.sql")
    with engine.begin() as conn:  # một transaction: lỗi giữa chừng thì rollback cả hai bảng
        _upsert(conn, students, "students", "student_id")
        _upsert(conn, profiles, "financial_profiles", "student_id")


# ---------------------------------------------------------------- MongoDB

def mongo_collection():
    client = MongoClient(config.mongo_url())
    return client, client[config.env("MONGO_DB")][config.settings()["mongo"]["collection"]]


def load_mongo(df: pd.DataFrame, batch_size: int = 5000) -> dict:
    client, coll = mongo_collection()
    try:
        coll.create_index([("student_id", ASCENDING), ("semester", ASCENDING)], unique=True,
                          name="uniq_student_semester")
        stats = {"upserted": 0, "modified": 0, "matched": 0}
        records = df.to_dict("records")
        for start in range(0, len(records), batch_size):
            ops = [
                ReplaceOne({"student_id": str(r["Student_ID"]), "semester": int(r["Semester"])},
                           to_document(r), upsert=True)
                for r in records[start:start + batch_size]
            ]
            result = coll.bulk_write(ops, ordered=False)
            stats["upserted"] += result.upserted_count
            stats["modified"] += result.modified_count
            stats["matched"] += result.matched_count
        return stats
    finally:
        client.close()


# ---------------------------------------------------------------- đọc lại & đối soát

def load_analytic_table() -> pd.DataFrame:
    """Đọc PostgreSQL + MongoDB, ghép theo student_id → bảng phẳng giống clean_semesters.parquet."""
    with db.pg_engine().connect() as conn:
        students = pd.read_sql(text(
            "SELECT student_id, age, gender, first_generation, household_size, housing_status, "
            "family_income::float8 AS family_income, income_missing FROM students"), conn)
        profiles = pd.read_sql(text(
            "SELECT student_id, scholarship, tuition_base::float8 AS tuition_base FROM financial_profiles"), conn)

    client, coll = mongo_collection()
    try:
        semesters = from_documents(list(coll.find({}, {"_id": 0})))
    finally:
        client.close()
    return merge_static(semesters, static_from_tables(students, profiles))


def reconcile(expected_students: int, expected_rows: int) -> list[tuple[str, bool, str]]:
    with db.pg_engine().connect() as conn:
        n_students = conn.execute(text("SELECT count(*) FROM students")).scalar()
        n_profiles = conn.execute(text("SELECT count(*) FROM financial_profiles")).scalar()
        pg_ids = set(conn.execute(text("SELECT student_id FROM students")).scalars())
    client, coll = mongo_collection()
    try:
        n_docs = coll.count_documents({})
        mongo_ids = set(coll.distinct("student_id"))
    finally:
        client.close()
    orphans = mongo_ids - pg_ids
    return [
        ("PostgreSQL students", n_students == expected_students, f"{n_students:,} / {expected_students:,}"),
        ("PostgreSQL financial_profiles", n_profiles == expected_students, f"{n_profiles:,} / {expected_students:,}"),
        ("MongoDB academic_semesters", n_docs == expected_rows, f"{n_docs:,} / {expected_rows:,}"),
        ("Mọi student_id trong MongoDB có trong students", not orphans,
         f"{len(orphans)} không khớp" if orphans else "khớp 100%"),
    ]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Nạp clean_semesters.parquet vào PostgreSQL + MongoDB.")
    parser.add_argument("--file", type=Path, default=config.path("processed_dir") / "clean_semesters.parquet")
    args = parser.parse_args()
    if not args.file.exists():
        print(f"Không thấy {args.file}. Hãy chạy python -m src.etl.clean trước.")
        return 1

    df = pd.read_parquet(args.file)
    students, profiles = split_static(df)
    load_postgres(students, profiles)
    print(f"PostgreSQL: upsert {len(students):,} students, {len(profiles):,} financial_profiles")
    stats = load_mongo(df)
    # replaceOne luôn ghi đè (modified_count tính cả khi nội dung không đổi) nên không in số "thay đổi"
    print(f"MongoDB   : {stats['upserted']:,} document thêm mới, {stats['matched']:,} document đã có được ghi đè")

    checks = reconcile(len(students), len(df))
    roundtrip = load_analytic_table()
    same = roundtrip.equals(df.sort_values(["Student_ID", "Semester"]).reset_index(drop=True))
    checks.append(("load_analytic_table() giống clean_semesters.parquet", same,
                   f"{roundtrip.shape[0]:,} × {roundtrip.shape[1]}"))
    for name, ok, detail in checks:
        print(f"[{'OK' if ok else 'LỖI'}] {name}: {detail}")
    return 0 if all(ok for _, ok, _ in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
