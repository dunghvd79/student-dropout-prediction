"""Bước 14 – Dự đoán theo lô (batch inference) cho sinh viên đang theo học.

Chạy:  python -m src.ml.predict [--run-id ID] [--local]
  Mặc định tải mô hình models:/dropout_model@production từ MLflow; --local dùng data/models/dropout_model.joblib.

Luồng:
  1. Scoring set = kỳ mới nhất của sinh viên đang theo học (Censored = 1), lấy từ feature_table.parquet (B7),
     tức là CÙNG code đặc trưng với lúc huấn luyện.
  2. Kiểm tra schema (chống training–serving skew): cột và thứ tự khớp feature_spec.json VÀ khớp cột mô hình
     đã học; kiểu số; nhóm phân loại không lạ. Sai thì dừng, không ghi gì.
  3. risk_score = predict_proba; risk_level theo config/risk_thresholds.json (chọn ở B12).
  4. 3 lý do cảnh báo: SHAP theo nhóm + top_reasons() (B13), nền = tập Train mà mô hình đã học.
  5. Upsert vào PostgreSQL predictions theo (run_id, student_id) → chạy lại cùng run_id không nhân đôi.
  6. Đối soát sau khi ghi + reports/scoring_report.md.

run_id mặc định = <ngày>-v<phiên bản mô hình>: chạy lại trong ngày với cùng mô hình thì ghi đè, đổi mô hình
hoặc sang ngày khác thì thành lần chạy mới (giữ lịch sử rủi ro của từng sinh viên).
"""

import argparse
import json
import sys
import time
from datetime import datetime

import numpy as np
import pandas as pd
from sqlalchemy import text

from src.core import config, db
from src.ml.evaluate import LEVELS, risk_level
from src.ml.explain import explain, reasons_text, top_reasons
from src.ml.split import load_spec, load_splits

N_REASONS = 3
NO_REASON = reasons_text([])


# ---------------------------------------------------------------- mô hình

def load_model(local: bool = False):
    """→ (pipeline, model_version). Registry là nguồn chính; --local cho lúc MLflow không chạy."""
    if local:
        import joblib
        return joblib.load(config.path("models_dir") / "dropout_model.joblib"), "local"
    import mlflow
    import mlflow.sklearn
    from mlflow import MlflowClient

    cfg = config.settings()["mlflow"]
    mlflow.set_tracking_uri(cfg["tracking_uri"])
    version = MlflowClient().get_model_version_by_alias(cfg["model_name"], "production").version
    return mlflow.sklearn.load_model(f"models:/{cfg['model_name']}/{version}"), str(version)


# ---------------------------------------------------------------- kiểm tra schema

def check_schema(X: pd.DataFrame, spec: dict, model) -> list[str]:
    """Danh sách lỗi (rỗng = đạt). So với feature_spec.json VÀ với cột mô hình đã thấy lúc fit."""
    errors = []
    if list(X.columns) != spec["features"]:
        missing = [c for c in spec["features"] if c not in X.columns]
        extra = [c for c in X.columns if c not in spec["features"]]
        errors.append(f"Cột không khớp feature_spec.json (thiếu {missing}, thừa {extra}"
                      + (", sai thứ tự" if not missing and not extra else "") + ")")
    trained = list(model[0].feature_names_in_)
    if trained != spec["features"]:
        errors.append("feature_spec.json khác danh sách cột lúc huấn luyện mô hình (spec đã đổi sau khi train)")
    for col in spec["numeric"] + spec["binary"]:
        if col in X.columns and not pd.api.types.is_numeric_dtype(X[col]):
            errors.append(f"{col} phải là kiểu số, đang là {X[col].dtype}")
    for col in spec["binary"]:
        if col in X.columns and not X[col].dropna().isin([0, 1]).all():
            errors.append(f"{col} có giá trị ngoài 0/1")
    known = dict(zip(spec["categorical"], model[1].named_transformers_["categorical"].categories_))
    for col, cats in known.items():
        if col in X.columns:
            unseen = sorted(set(X[col].dropna().astype(str)) - set(cats))
            if unseen:
                errors.append(f"{col} có nhóm mô hình chưa thấy: {unseen}")
    return errors


# ---------------------------------------------------------------- dựng bảng kết quả

def build_predictions(keys: pd.DataFrame, X: pd.DataFrame, group_phi: pd.DataFrame, proba: np.ndarray,
                      thresholds: dict, run_id: str, model_version: str, run_date: datetime) -> pd.DataFrame:
    """Một dòng / sinh viên, đúng cột của bảng predictions."""
    reasons = []
    for i in range(len(X)):
        r = [f"{x['ten']}: {x['mo_ta']}" for x in top_reasons(group_phi.iloc[i], X.iloc[i], k=N_REASONS)]
        reasons.append((r or [NO_REASON]) + [None] * (N_REASONS - max(len(r), 1)))
    out = pd.DataFrame({
        "run_id": run_id, "run_date": run_date, "model_version": model_version,
        "student_id": keys["Student_ID"].astype(str).values, "semester": keys["Semester"].astype(int).values,
        "risk_score": np.round(proba, 4), "risk_level": risk_level(proba, thresholds),
    })
    out[[f"top_reason_{k}" for k in range(1, N_REASONS + 1)]] = pd.DataFrame(reasons, index=out.index)
    return out


# ---------------------------------------------------------------- ghi CSDL

def upsert_predictions(df: pd.DataFrame) -> None:
    engine = db.pg_engine()
    db.run_sql_file(engine, "02_core_tables.sql")
    cols = ", ".join(df.columns)
    updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in df.columns if c not in ("run_id", "student_id"))
    with engine.begin() as conn:  # một transaction: lỗi giữa chừng thì không ghi dòng nào
        df.to_sql("_staging_predictions", conn, if_exists="replace", index=False)
        conn.execute(text(f"INSERT INTO predictions ({cols}) SELECT {cols} FROM _staging_predictions "
                          f"ON CONFLICT (run_id, student_id) DO UPDATE SET {updates}"))
        conn.execute(text("DROP TABLE _staging_predictions"))


def reconcile(run_id: str, expected: pd.DataFrame) -> list[tuple[str, bool, str]]:
    with db.pg_engine().connect() as conn:
        stored = pd.read_sql(text("SELECT student_id, risk_score::float8 AS risk_score, risk_level, top_reason_1 "
                                  "FROM predictions WHERE run_id = :r"), conn, params={"r": run_id})
        runs = conn.execute(text("SELECT count(DISTINCT run_id) FROM predictions")).scalar()
    merged = expected[["student_id", "risk_score"]].merge(stored, on="student_id", suffixes=("", "_db"))
    return [
        ("Số dòng trong CSDL = số sinh viên được chấm", len(stored) == len(expected), f"{len(stored):,} / {len(expected):,}"),
        ("Không có risk_score / risk_level / lý do NULL",
         not stored[["risk_score", "risk_level", "top_reason_1"]].isna().any().any(), ""),
        ("risk_score trong CSDL khớp kết quả tính", len(merged) == len(expected)
         and np.allclose(merged["risk_score"], merged["risk_score_db"], atol=5e-5), ""),
        ("Lịch sử các lần chạy", True, f"{runs} run_id trong bảng predictions"),
    ]


# ---------------------------------------------------------------- báo cáo

def write_report(res: dict) -> None:
    lv = pd.DataFrame(res["levels"])
    lines = [
        "# BÁO CÁO CHẤM ĐIỂM RỦI RO (B14)",
        f"*Sinh tự động bởi `python -m src.ml.predict` lúc {res['run_date']}. `run_id = {res['run_id']}`, "
        f"mô hình `dropout_model` v{res['model_version']}, {res['seconds']:.0f} giây.*",
        "",
        f"* **Sinh viên được chấm:** {res['n']:,} (kỳ mới nhất của sinh viên đang theo học, `Censored = 1`).",
        f"* **Mốc rủi ro** (`config/risk_thresholds.json`, B12): Trung bình ≥ {res['thresholds']['medium']:.4f}, "
        f"Cao ≥ {res['thresholds']['high']:.4f}.",
        f"* **Xác suất trung bình:** {res['mean_score']:.1%} (tỷ lệ bỏ học kỳ sau trên tập có nhãn: {res['base_rate']:.1%}).",
        "",
        "## 1. Phân bố mức rủi ro",
        "",
        "| Mức | Số sinh viên | Tỷ lệ | Tỷ lệ trên tập Test (B12) |",
        "|---|---:|---:|---:|",
        *[f"| {r.muc} | {r.so_sv:,} | {r.ty_le:.1%} | {r.ty_le_test:.1%} |" for r in lv.itertuples()],
        "",
        "## 2. Theo học kỳ",
        "",
        pd.DataFrame(res["by_semester"]).rename(columns={"semester": "Học kỳ", "so_sv": "Số SV", "diem_tb": "Xác suất TB",
                                                         "ty_le_cao": "Tỷ lệ mức Cao"})
        .to_markdown(index=False, floatfmt=(".0f", ".0f", ".3f", ".3f")),
        "",
        "## 3. Lý do số 1 của sinh viên mức Cao",
        "",
        "| Nhóm | Số sinh viên | Tỷ lệ |",
        "|---|---:|---:|",
        *[f"| {k} | {v['so_sv']:,} | {v['ty_le']:.1%} |" for k, v in res["top1_high"].items()],
        "",
        "## 4. Kiểm tra",
        "",
        "| Kiểm tra | Kết quả | Chi tiết |",
        "|---|:---:|---|",
        *[f"| {n} | {'✅' if ok else '❌'} | {d} |" for n, ok, d in res["checks"]],
        "",
        "## 5. Ví dụ 5 sinh viên rủi ro cao nhất",
        "",
        pd.DataFrame(res["top5"]).to_markdown(index=False),
        "",
    ]
    (config.path("reports_dir") / "scoring_report.md").write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------- main

def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="B14 – chấm điểm rủi ro cho sinh viên đang theo học.")
    parser.add_argument("--run-id", help="Mặc định <ngày>-v<phiên bản mô hình>")
    parser.add_argument("--local", action="store_true", help="Dùng data/models/dropout_model.joblib thay vì MLflow")
    args = parser.parse_args()
    start = time.perf_counter()

    model, version = load_model(args.local)
    splits, spec = load_splits(), load_spec()
    X, keys = splits.X_score.reset_index(drop=True), splits.keys_score.reset_index(drop=True)
    errors = check_schema(X, spec, model)
    if errors:
        for e in errors:
            print(f"[LỖI SCHEMA] {e}")
        print("Dừng: không ghi kết quả.")
        return 1
    thresholds = json.loads((config.ROOT / "config" / "risk_thresholds.json").read_text(encoding="utf-8"))

    run_date = datetime.now().astimezone()
    run_id = args.run_id or f"{run_date:%Y%m%d}-v{version}"
    ex = explain(model, X, splits.X_train, spec)
    proba = model.predict_proba(X)[:, 1]
    if not np.allclose(proba, ex.proba):
        raise RuntimeError("Xác suất từ SHAP không khớp predict_proba.")
    preds = build_predictions(keys, X, ex.groups, proba, thresholds, run_id, version, run_date)
    upsert_predictions(preds)
    seconds = time.perf_counter() - start

    checks = [("Kiểm tra schema đặc trưng", True, f"{X.shape[1]} cột khớp feature_spec.json và mô hình")]
    checks += reconcile(run_id, preds)
    checks.append(("Thời gian chạy < 2 phút", seconds < 120, f"{seconds:.0f} giây"))

    test_levels = pd.DataFrame(json.loads((config.path("reports_dir") / "test_metrics.json")
                                          .read_text(encoding="utf-8"))["levels"]).set_index("muc")["ty_le_dong"]
    counts = preds["risk_level"].value_counts().reindex(LEVELS, fill_value=0)
    high = preds[preds["risk_level"] == "Cao"]["top_reason_1"].str.split(":").str[0].value_counts()
    by_sem = preds.groupby("semester").agg(so_sv=("student_id", "size"), diem_tb=("risk_score", "mean"),
                                           ty_le_cao=("risk_level", lambda s: (s == "Cao").mean())).reset_index()
    res = {
        "run_id": run_id, "run_date": f"{run_date:%Y-%m-%d %H:%M}", "model_version": version, "seconds": seconds,
        "n": len(preds), "thresholds": thresholds, "mean_score": float(proba.mean()),
        "base_rate": float(pd.concat([splits.y_train, splits.y_test]).mean()),
        "levels": [{"muc": m, "so_sv": int(counts[m]), "ty_le": counts[m] / len(preds),
                    "ty_le_test": float(test_levels.get(m, np.nan))} for m in LEVELS],
        "by_semester": by_sem.to_dict("records"),
        "top1_high": {k: {"so_sv": int(v), "ty_le": v / max(len(preds[preds["risk_level"] == "Cao"]), 1)}
                      for k, v in high.items()},
        "checks": checks,
        "top5": preds.nlargest(5, "risk_score")[["student_id", "semester", "risk_score", "top_reason_1",
                                                  "top_reason_2", "top_reason_3"]].to_dict("records"),
    }
    write_report(res)

    print(f"run_id {run_id} | dropout_model v{version} | {len(preds):,} sinh viên | {seconds:.0f} giây")
    print("Mức rủi ro:", {m: int(counts[m]) for m in LEVELS}, f"| xác suất TB {proba.mean():.1%}")
    for name, ok, detail in checks:
        print(f"[{'OK' if ok else 'LỖI'}] {name}: {detail}")
    print(f"Báo cáo: {config.path('reports_dir') / 'scoring_report.md'}")
    return 0 if all(ok for _, ok, _ in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
