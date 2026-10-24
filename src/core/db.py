"""Kết nối dùng chung tới PostgreSQL và MinIO."""

from functools import lru_cache

from minio import Minio
from sqlalchemy import Engine, create_engine

from src.core import config


@lru_cache
def pg_engine(database: str | None = None) -> Engine:
    return create_engine(config.postgres_url(database), pool_pre_ping=True)


def minio_client() -> Minio:
    return Minio(
        config.minio_endpoint(),
        access_key=config.env("MINIO_ROOT_USER"),
        secret_key=config.env("MINIO_ROOT_PASSWORD"),
        secure=False,
    )


def run_sql_file(engine: Engine, filename: str) -> None:
    """Chạy một file trong thư mục sql/ (các câu lệnh đều idempotent: IF NOT EXISTS)."""
    sql = (config.ROOT / "sql" / filename).read_text(encoding="utf-8")
    with engine.begin() as conn:
        conn.exec_driver_sql(sql)
