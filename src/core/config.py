"""Đọc cấu hình dự án (config/settings.yaml) và bí mật (.env), tạo chuỗi kết nối dùng chung."""

import os
from functools import lru_cache
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]

load_dotenv(ROOT / ".env")


@lru_cache
def settings() -> dict:
    with open(ROOT / "config" / "settings.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def path(key: str) -> Path:
    """Đường dẫn tuyệt đối của một mục trong settings.paths."""
    return ROOT / settings()["paths"][key]


def env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None:
        raise RuntimeError(f"Thiếu biến môi trường {name}. Hãy tạo .env từ .env.example.")
    return value


def postgres_url(database: str | None = None) -> str:
    host = settings()["postgres"]["host"]
    db = database or env("POSTGRES_DB")
    return (
        f"postgresql+psycopg2://{env('POSTGRES_USER')}:{env('POSTGRES_PASSWORD')}"
        f"@{host}:{env('POSTGRES_PORT', '5433')}/{db}"
    )


def mongo_url() -> str:
    host = settings()["mongo"]["host"]
    return (
        f"mongodb://{env('MONGO_USER')}:{env('MONGO_PASSWORD')}"
        f"@{host}:{env('MONGO_PORT', '27018')}/?authSource=admin"
    )


def minio_endpoint() -> str:
    return f"{settings()['minio']['host']}:{env('MINIO_PORT', '9000')}"
