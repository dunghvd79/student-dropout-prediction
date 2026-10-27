"""Bước 16 – Sao lưu và diễn tập khôi phục.

Chạy:  python -m src.ops.backup                 sao lưu → backups/<thời điểm>/
       python -m src.ops.backup verify [DIR]    khôi phục thử bản mới nhất (hoặc DIR) vào container TẠM

Sao lưu đúng phần KHÔNG tái tạo được (B16 mục 2.6):
  PostgreSQL  dropout_ews (students, predictions, pipeline_runs…) + mlflow (runs, Model Registry)  pg_dump -Fc
  MongoDB     dropout_ews (academic_semesters)                                                     mongodump --archive --gzip
  MinIO       raw, processed, mlflow (dữ liệu thô + artifact mô hình)                              tải từng object
File đặc trưng, Parquet, báo cáo không sao lưu vì chạy lại script là có.

manifest.json ghi kích thước + SHA-256 từng file và số dòng / document / object lúc sao lưu.
verify dựng postgres:16.6 và mongo:7.0.16 TẠM (không mở cổng, xóa khi xong), khôi phục vào đó rồi đối chiếu
với manifest; MinIO đối chiếu SHA-256. Kho đang chạy không bị đụng tới. Thời gian khôi phục = RTO đo được.
Quy tắc 3-2-1: bản này là bản thứ 2 (ổ máy); bản 3 chép thư mục backups/<thời điểm> ra ổ rời / Drive (thủ công).
"""

import hashlib
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from sqlalchemy import text

from src.core import config, db

PG_DATABASES = ["dropout_ews", "mlflow"]
PG_TABLES = ["students", "financial_profiles", "predictions", "student_clusters", "ingestion_log", "pipeline_runs",
             "semester_summary"]
BUCKETS = ["raw", "processed", "mlflow"]


def backup_root() -> Path:
    return config.ROOT / config.settings()["backup"]["dir"]


def _container(service: str) -> str:
    cid = subprocess.run(["docker", "compose", "ps", "-q", service], cwd=config.ROOT, capture_output=True,
                         text=True, check=True).stdout.strip()
    if not cid:
        raise RuntimeError(f"Container {service} không chạy. Hãy chạy docker compose up -d.")
    return cid


def _to_file(cmd: list[str], path: Path) -> None:
    with open(path, "wb") as f:
        proc = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise RuntimeError(f"{cmd[:4]} lỗi: {proc.stderr.decode(errors='replace')[-400:]}")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _mongo_uri(host: str = "localhost:27017") -> str:
    from urllib.parse import quote_plus
    return f"mongodb://{quote_plus(config.env('MONGO_USER'))}:{quote_plus(config.env('MONGO_PASSWORD'))}@{host}/?authSource=admin"


# ---------------------------------------------------------------- đếm (để đối chiếu)

def live_counts() -> dict:
    counts = {"postgres": {}, "mongo": {}, "minio": {}}
    with db.pg_engine().connect() as conn:
        for t in PG_TABLES:
            exists = conn.execute(text("SELECT to_regclass(:t)"), {"t": t}).scalar()
            if exists:
                counts["postgres"][t] = conn.execute(text(f"SELECT count(*) FROM {t}")).scalar()
    from src.etl.load import mongo_collection
    client, coll = mongo_collection()
    try:
        counts["mongo"]["academic_semesters"] = coll.count_documents({})
    finally:
        client.close()
    mc = db.minio_client()
    for b in BUCKETS:
        counts["minio"][b] = sum(1 for _ in mc.list_objects(b, recursive=True))
    return counts


# ---------------------------------------------------------------- sao lưu

def backup() -> Path:
    t0 = time.perf_counter()
    out = backup_root() / datetime.now().strftime("%Y%m%dT%H%M%S")
    out.mkdir(parents=True)
    pg, mongo = _container("postgres"), _container("mongo")
    user = config.env("POSTGRES_USER")
    for name in PG_DATABASES:
        _to_file(["docker", "exec", pg, "pg_dump", "-U", user, "-Fc", name], out / f"postgres_{name}.dump")
    _to_file(["docker", "exec", mongo, "mongodump", "--quiet", "--uri", _mongo_uri(), "--db", config.env("MONGO_DB"),
              "--archive", "--gzip"], out / "mongo_dropout_ews.archive.gz")
    mc = db.minio_client()
    for b in BUCKETS:
        for obj in mc.list_objects(b, recursive=True):
            target = out / "minio" / b / obj.object_name
            target.parent.mkdir(parents=True, exist_ok=True)
            mc.fget_object(b, obj.object_name, str(target))

    files = {str(p.relative_to(out)).replace("\\", "/"): {"bytes": p.stat().st_size, "sha256": sha256(p)}
             for p in sorted(out.rglob("*")) if p.is_file()}
    manifest = {"created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                "seconds": round(time.perf_counter() - t0, 1), "counts": live_counts(), "files": files}
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    rotate()
    return out


def rotate() -> list[Path]:
    """Giữ `keep` bản mới nhất, xóa bản cũ hơn."""
    keep = config.settings()["backup"]["keep"]
    dirs = sorted(p for p in backup_root().iterdir() if p.is_dir() and (p / "manifest.json").exists())
    removed = dirs[:-keep] if len(dirs) > keep else []
    for p in removed:
        shutil.rmtree(p)
    return removed


# ---------------------------------------------------------------- diễn tập khôi phục

def _wait(cmd: list[str], seconds: int = 90) -> None:
    for _ in range(seconds):
        if subprocess.run(cmd, capture_output=True).returncode == 0:
            return
        time.sleep(1)
    raise RuntimeError(f"Container tạm không sẵn sàng: {cmd}")


def _exec_stdin(cmd: list[str], path: Path) -> None:
    with open(path, "rb") as f:
        proc = subprocess.run(cmd, stdin=f, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(f"{cmd[:5]} lỗi: {proc.stderr.decode(errors='replace')[-400:]}")


def verify(directory: Path | None = None) -> list[tuple[str, bool, str]]:
    if directory is None:
        dirs = sorted(p for p in backup_root().iterdir() if (p / "manifest.json").exists())
        if not dirs:
            raise RuntimeError("Chưa có bản sao lưu nào. Chạy python -m src.ops.backup trước.")
        directory = dirs[-1]
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    checks = []
    t0 = time.perf_counter()

    # 1. Toàn vẹn file
    bad = [f for f, info in manifest["files"].items() if sha256(directory / f) != info["sha256"]]
    checks.append(("SHA-256 mọi file khớp manifest", not bad, f"{len(manifest['files'])} file" + (f", sai: {bad[:3]}" if bad else "")))

    # 2. PostgreSQL vào container tạm
    pg_name, mongo_name = "ews-restore-pg", "ews-restore-mongo"
    subprocess.run(["docker", "rm", "-f", pg_name, mongo_name], capture_output=True)
    try:
        subprocess.run(["docker", "run", "-d", "--rm", "--name", pg_name, "-e", "POSTGRES_PASSWORD=restore_drill",
                        "postgres:16.6"], check=True, capture_output=True)
        _wait(["docker", "exec", pg_name, "pg_isready", "-U", "postgres"])
        time.sleep(2)
        for name in PG_DATABASES:
            subprocess.run(["docker", "exec", pg_name, "createdb", "-U", "postgres", name], check=True, capture_output=True)
            _exec_stdin(["docker", "exec", "-i", pg_name, "pg_restore", "-U", "postgres", "-d", name, "--no-owner",
                         "--no-privileges"], directory / f"postgres_{name}.dump")
        for table, expected in manifest["counts"]["postgres"].items():
            got = subprocess.run(["docker", "exec", pg_name, "psql", "-U", "postgres", "-d", "dropout_ews", "-tAc",
                                  f"SELECT count(*) FROM {table}"], capture_output=True, text=True).stdout.strip()
            checks.append((f"PostgreSQL {table}", got == str(expected), f"{got} / {expected}"))
        versions = subprocess.run(["docker", "exec", pg_name, "psql", "-U", "postgres", "-d", "mlflow", "-tAc",
                                   "SELECT count(*) FROM model_versions WHERE name = 'dropout_model'"],
                                  capture_output=True, text=True).stdout.strip()
        checks.append(("MLflow Model Registry khôi phục được", versions.isdigit() and int(versions) > 0,
                       f"{versions} phiên bản dropout_model"))

        # 3. MongoDB vào container tạm
        subprocess.run(["docker", "run", "-d", "--rm", "--name", mongo_name, "mongo:7.0.16"], check=True,
                       capture_output=True)
        _wait(["docker", "exec", mongo_name, "mongosh", "--quiet", "--eval", "db.runCommand({ping: 1})"])
        _exec_stdin(["docker", "exec", "-i", mongo_name, "mongorestore", "--quiet", "--archive", "--gzip"],
                    directory / "mongo_dropout_ews.archive.gz")
        got = subprocess.run(["docker", "exec", mongo_name, "mongosh", "--quiet", config.env("MONGO_DB"), "--eval",
                              "db.academic_semesters.countDocuments()"], capture_output=True, text=True).stdout.strip()
        expected = manifest["counts"]["mongo"]["academic_semesters"]
        checks.append(("MongoDB academic_semesters", got == str(expected), f"{got} / {expected}"))
    finally:
        subprocess.run(["docker", "rm", "-f", pg_name, mongo_name], capture_output=True)

    # 4. MinIO: đủ số object từng bucket
    for b, expected in manifest["counts"]["minio"].items():
        got = sum(1 for f in manifest["files"] if f.startswith(f"minio/{b}/"))
        checks.append((f"MinIO {b}", got == expected, f"{got} / {expected} object"))
    rto = time.perf_counter() - t0
    checks.append(("Thời gian khôi phục (RTO) < 1 giờ", rto < 3600, f"{rto:.0f} giây"))
    return checks


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) > 1 and sys.argv[1] == "verify":
        directory = Path(sys.argv[2]) if len(sys.argv) > 2 else None
        checks = verify(directory)
        for name, ok, detail in checks:
            print(f"[{'OK' if ok else 'LỖI'}] {name}: {detail}")
        return 0 if all(ok for _, ok, _ in checks) else 1
    out = backup()
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    size = sum(f["bytes"] for f in manifest["files"].values())
    print(f"Sao lưu: {out.relative_to(config.ROOT)} | {len(manifest['files'])} file, {size / 1e6:.1f} MB, "
          f"{manifest['seconds']:.0f} giây")
    print("Số lượng:", json.dumps(manifest["counts"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
