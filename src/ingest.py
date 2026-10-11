"""Bước 2 – Nạp dữ liệu thô vào Raw Data Lake (MinIO) và ghi ingestion_log.

Chạy:  python -m src.ingest [--file PATH] [--date YYYY-MM-DD]

Quy trình:
  1. Tính MD5; nếu nội dung đã được nạp thành công trước đó thì bỏ qua (idempotent).
  2. Kiểm tra schema: đủ 22 cột đúng tên, đúng thứ tự; cột số đọc được thành số.
  3. Upload nguyên trạng lên bucket raw:
       academic/ingest_date=YYYY-MM-DD/batch_id=<id>/<tên file>
     Mỗi lô một batch_id nên không bao giờ ghi đè lô cũ.
  4. Tải ngược object và so MD5 để chắc file không hỏng khi truyền.
  5. Ghi một dòng vào ingestion_log (SUCCESS / FAILED / SKIPPED).
"""

import argparse
import hashlib
import sys
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from src import config, db
from src.schema import COLUMNS, NUMERIC_KINDS


def md5_of_file(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check_schema(df: pd.DataFrame) -> list[str]:
    """Trả về danh sách lỗi schema (rỗng nếu hợp lệ). df phải được đọc với dtype=str."""
    errors = []
    expected = list(COLUMNS)
    actual = list(df.columns)

    missing = [c for c in expected if c not in actual]
    extra = [c for c in actual if c not in expected]
    if missing:
        errors.append(f"Thiếu cột: {missing}")
    if extra:
        errors.append(f"Cột không có trong schema: {extra}")
    if not missing and not extra and actual != expected:
        errors.append("Sai thứ tự cột")
    if df.empty:
        errors.append("File không có dòng dữ liệu")

    for col, kind in COLUMNS.items():
        if col not in df.columns or kind not in NUMERIC_KINDS:
            continue
        values = df[col].str.strip()
        not_numeric = values[(values != "") & pd.to_numeric(values, errors="coerce").isna()]
        if len(not_numeric):
            errors.append(
                f"Cột {col}: {len(not_numeric)} giá trị không phải số, ví dụ {not_numeric.iloc[:3].tolist()}"
            )
    return errors


def _write_log(engine, **row) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO ingestion_log
                    (batch_id, source_file, bucket, object_key, row_count, column_count,
                     file_size_bytes, md5, status, message)
                VALUES
                    (:batch_id, :source_file, :bucket, :object_key, :row_count, :column_count,
                     :file_size_bytes, :md5, :status, :message)
                """
            ),
            row,
        )


def ingest(file_path: Path, ingest_date: date | None = None) -> dict:
    cfg = config.settings()
    bucket = cfg["minio"]["buckets"]["raw"]
    ingest_date = ingest_date or date.today()
    batch_id = f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}_{uuid.uuid4().hex[:6]}"

    engine = db.pg_engine()
    db.run_sql_file(engine, "01_ingestion_log.sql")

    log = {
        "batch_id": batch_id,
        "source_file": file_path.name,
        "bucket": bucket,
        "object_key": None,
        "row_count": None,
        "column_count": None,
        "file_size_bytes": file_path.stat().st_size,
        "md5": md5_of_file(file_path),
        "status": None,
        "message": None,
    }

    # 1. Idempotency: cùng nội dung đã nạp thành công thì không nạp lại
    with engine.connect() as conn:
        previous = conn.execute(
            text("SELECT batch_id FROM ingestion_log WHERE md5 = :md5 AND status = 'SUCCESS' LIMIT 1"),
            {"md5": log["md5"]},
        ).scalar()
    if previous:
        log.update(status="SKIPPED", message=f"Nội dung trùng với lô {previous}")
        _write_log(engine, **log)
        return log

    # 2. Kiểm tra schema
    df = pd.read_csv(file_path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    log.update(row_count=len(df), column_count=df.shape[1])
    errors = check_schema(df)
    if errors:
        log.update(status="FAILED", message=" | ".join(errors))
        _write_log(engine, **log)
        return log

    # 3–4. Upload và kiểm tra lại MD5
    key = f"{cfg['minio']['raw_prefix']}/ingest_date={ingest_date:%Y-%m-%d}/batch_id={batch_id}/{file_path.name}"
    log["object_key"] = key
    try:
        client = db.minio_client()
        client.fput_object(
            bucket,
            key,
            str(file_path),
            content_type="text/csv",
            metadata={"md5": log["md5"], "row-count": str(len(df)), "batch-id": batch_id},
        )
        response = client.get_object(bucket, key)
        try:
            uploaded_md5 = hashlib.md5(response.read()).hexdigest()
        finally:
            response.close()
            response.release_conn()
        if uploaded_md5 != log["md5"]:
            raise RuntimeError(f"MD5 sau khi upload ({uploaded_md5}) khác file gốc ({log['md5']})")
    except Exception as e:
        log.update(status="FAILED", message=f"{type(e).__name__}: {e}")
        _write_log(engine, **log)
        return log

    log.update(status="SUCCESS", message="Đã upload và kiểm tra MD5")
    _write_log(engine, **log)
    return log


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Nạp file CSV nguồn vào MinIO (bucket raw).")
    parser.add_argument("--file", type=Path, default=config.path("source_csv"))
    parser.add_argument("--date", type=date.fromisoformat, default=None, help="Ngày nạp, mặc định hôm nay")
    args = parser.parse_args()

    result = ingest(args.file, args.date)
    print(f"[{result['status']}] batch_id={result['batch_id']}")
    print(f"  file      : {result['source_file']} ({result['file_size_bytes']:,} bytes, md5={result['md5']})")
    if result["row_count"] is not None:
        print(f"  kích thước: {result['row_count']:,} dòng × {result['column_count']} cột")
    if result["object_key"]:
        print(f"  object    : s3://{result['bucket']}/{result['object_key']}")
    print(f"  ghi chú   : {result['message']}")
    return 1 if result["status"] == "FAILED" else 0


if __name__ == "__main__":
    sys.exit(main())
