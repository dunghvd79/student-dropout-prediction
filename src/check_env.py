"""Kiểm tra môi trường (tiêu chí hoàn thành Bước 1).

Chạy:  python -m src.check_env
Kiểm tra: thư viện Python, file dữ liệu gốc, MinIO (bucket), PostgreSQL (2 database), MongoDB, MLflow.
"""

import importlib
import sys

from src import config

LIBS = [
    "numpy", "pandas", "pyarrow", "sqlalchemy", "psycopg2", "pymongo", "minio",
    "sklearn", "imblearn", "xgboost", "lightgbm", "optuna", "shap",
    "mlxtend", "lifelines", "mlflow", "matplotlib", "seaborn", "plotly", "streamlit",
]


def check_libs():
    versions = []
    for name in LIBS:
        mod = importlib.import_module(name)
        versions.append(f"{name} {getattr(mod, '__version__', '?')}")
    return ", ".join(versions)


def check_source_csv():
    p = config.path("source_csv")
    if not p.exists():
        raise FileNotFoundError(p)
    return f"{p.name} ({p.stat().st_size / 1e6:.1f} MB)"


def check_minio():
    from minio import Minio

    client = Minio(
        config.minio_endpoint(),
        access_key=config.env("MINIO_ROOT_USER"),
        secret_key=config.env("MINIO_ROOT_PASSWORD"),
        secure=False,
    )
    wanted = set(config.settings()["minio"]["buckets"].values())
    existing = {b.name for b in client.list_buckets()}
    missing = wanted - existing
    if missing:
        raise RuntimeError(f"thiếu bucket {sorted(missing)}")
    return f"bucket {sorted(wanted)}"


def check_postgres():
    from sqlalchemy import create_engine, text

    out = []
    for db in (config.env("POSTGRES_DB"), "mlflow"):
        engine = create_engine(config.postgres_url(db))
        with engine.connect() as conn:
            version = conn.execute(text("SHOW server_version")).scalar()
        engine.dispose()
        out.append(db)
    return f"PostgreSQL {version}, database {out}"


def check_mongo():
    from pymongo import MongoClient

    client = MongoClient(config.mongo_url(), serverSelectionTimeoutMS=3000)
    version = client.server_info()["version"]
    client.close()
    return f"MongoDB {version} (cổng {config.env('MONGO_PORT', '27018')})"


def check_mlflow():
    import mlflow

    mlflow.set_tracking_uri(config.settings()["mlflow"]["tracking_uri"])
    experiments = mlflow.search_experiments()
    return f"{config.settings()['mlflow']['tracking_uri']} ({len(experiments)} experiment)"


CHECKS = [
    ("Thư viện Python", check_libs),
    ("Dữ liệu gốc", check_source_csv),
    ("MinIO", check_minio),
    ("PostgreSQL", check_postgres),
    ("MongoDB", check_mongo),
    ("MLflow", check_mlflow),
]


def main() -> int:
    print(f"Python {sys.version.split()[0]}")
    failed = 0
    for name, fn in CHECKS:
        try:
            print(f"[OK]   {name}: {fn()}")
        except Exception as e:  # báo lỗi từng mục, không dừng cả chương trình
            failed += 1
            print(f"[LỖI] {name}: {type(e).__name__}: {e}")
    print("Tất cả đều sẵn sàng." if failed == 0 else f"{failed} mục lỗi.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
