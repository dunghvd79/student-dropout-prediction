"""Bước 16 – Điều phối pipeline chấm điểm định kỳ (DAG tuyến tính).

Chạy:  python -m src.ops.run_pipeline [--trigger scheduled] [--from STEP] [--file CSV]

  ingest → validate → clean → load → features → predict → publish → monitor

* Mỗi bước chạy trong một tiến trình riêng (`python -m ...`), đúng như khi chạy tay → không có
  "phiên bản pipeline" thứ hai để lệch nhau. Một bước trả mã ≠ 0 thì DỪNG, các bước sau không chạy.
* Mọi lần chạy ghi vào PostgreSQL pipeline_runs (trạng thái, thời gian từng bước, chỉ số giám sát, cảnh báo)
  và log đầy đủ vào logs/pipeline/<run_id>.log.
* Không gồm huấn luyện lại (B9 – B12): việc đó chạy theo học kỳ hoặc khi có cảnh báo, và chỉ thay mô hình
  khi bản mới tốt hơn (champion – challenger, xem B16 mục 4).
* --file: nạp một CSV mới (dữ liệu kỳ mới) thay cho file gốc ở bước ingest.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime

from sqlalchemy import text

from src.core import config, db

STEPS = [
    ("ingest", "src.etl.ingest"),
    ("validate", "src.etl.validate"),
    ("clean", "src.etl.clean"),
    ("load", "src.etl.load"),
    ("features", "src.analysis.features"),
    ("predict", "src.ml.predict"),
    ("publish", "src.etl.publish"),
]
STEP_NAMES = [s for s, _ in STEPS] + ["monitor"]


def plan(start: str = "ingest") -> list[tuple[str, str]]:
    names = [s for s, _ in STEPS]
    if start not in names:
        raise ValueError(f"Bước không hợp lệ: {start}. Chọn một trong {names}")
    return STEPS[names.index(start):]


def _record(conn, run_id: str, **fields) -> None:
    sets = ", ".join(f"{k} = :{k}" for k in fields)
    conn.execute(text(f"UPDATE pipeline_runs SET {sets} WHERE run_id = :run_id"), {"run_id": run_id, **fields})


def run(trigger: str = "manual", start: str = "ingest", file: str | None = None) -> int:
    from src.ops.monitor import collect, write_report

    engine = db.pg_engine()
    db.run_sql_file(engine, "04_pipeline_runs.sql")
    with engine.begin() as conn:
        running = conn.execute(text("SELECT run_id FROM pipeline_runs WHERE status = 'RUNNING' "
                                    "AND started_at > now() - interval '1 hour'")).scalar()
    if running:
        print(f"Đang có lần chạy {running} chưa kết thúc (< 1 giờ). Không chạy chồng.")
        return 2

    started = datetime.now().astimezone()
    run_id = f"run_{started:%Y%m%dT%H%M%S}"
    log_dir = config.ROOT / "logs" / "pipeline"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{run_id}.log"
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO pipeline_runs (run_id, trigger, started_at, status) "
                          "VALUES (:r, :t, :s, 'RUNNING')"), {"r": run_id, "t": trigger, "s": started})

    steps, failed, t0 = [], None, time.perf_counter()
    with open(log_path, "w", encoding="utf-8") as log:
        for name, module in plan(start):
            cmd = [sys.executable, "-m", module] + (["--file", file] if name == "ingest" and file else [])
            log.write(f"\n===== {name}: {' '.join(cmd[1:])} =====\n")
            log.flush()
            s0 = time.perf_counter()
            proc = subprocess.run(cmd, cwd=config.ROOT, stdout=log, stderr=subprocess.STDOUT,
                                  env={**os.environ, "PYTHONIOENCODING": "utf-8"})
            seconds = round(time.perf_counter() - s0, 1)
            ok = proc.returncode == 0
            steps.append({"step": name, "status": "SUCCESS" if ok else "FAILED", "seconds": seconds,
                          "exit_code": proc.returncode})
            print(f"[{'OK' if ok else 'LỖI'}] {name:<9} {seconds:6.1f} giây")
            with engine.begin() as conn:
                _record(conn, run_id, steps=json.dumps(steps))
            if not ok:
                failed = name
                break

    seconds = time.perf_counter() - t0
    metrics, alerts = None, []
    if failed:
        alerts = [f"Bước {failed} thất bại (mã {steps[-1]['exit_code']}); xem {log_path.relative_to(config.ROOT)}"]
    else:
        m0 = time.perf_counter()
        metrics, alerts = collect(pipeline_seconds=seconds)
        steps.append({"step": "monitor", "status": "SUCCESS", "seconds": round(time.perf_counter() - m0, 1),
                      "exit_code": 0})
        write_report(metrics, alerts, run_id)
        print(f"[OK] monitor   {steps[-1]['seconds']:6.1f} giây")
    with engine.begin() as conn:
        _record(conn, run_id, finished_at=datetime.now().astimezone(), status="FAILED" if failed else "SUCCESS",
                failed_step=failed, seconds=round(time.perf_counter() - t0, 1), steps=json.dumps(steps),
                metrics=json.dumps(metrics, default=float) if metrics else None, alerts=alerts)

    print(f"{run_id}: {'THẤT BẠI ở bước ' + failed if failed else 'THÀNH CÔNG'} sau {time.perf_counter() - t0:.0f} giây"
          f" | log: {log_path.relative_to(config.ROOT)}")
    for a in alerts:
        print(f"[CẢNH BÁO] {a}")
    return 1 if failed else 0


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="B16 – chạy pipeline chấm điểm định kỳ.")
    parser.add_argument("--trigger", choices=["manual", "scheduled"], default="manual")
    parser.add_argument("--from", dest="start", default="ingest", help="Bắt đầu từ bước này (chạy lại sau lỗi)")
    parser.add_argument("--file", help="CSV dữ liệu mới cho bước ingest")
    args = parser.parse_args()
    return run(args.trigger, args.start, args.file)


if __name__ == "__main__":
    sys.exit(main())
