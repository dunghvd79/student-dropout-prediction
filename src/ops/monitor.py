"""Bước 16 – Giám sát hệ thống và mô hình sau mỗi lần chạy pipeline.

Chạy riêng:  python -m src.ops.monitor            (ghi báo cáo, không ghi pipeline_runs)
Trong pipeline: run_pipeline.py gọi collect() rồi lưu metrics + alerts vào pipeline_runs.

Năm nhóm chỉ số (ngưỡng trong settings.yaml → monitoring):
  1. Thời gian chạy pipeline                       (do run_pipeline truyền vào)
  2. Tỷ lệ lỗi schema của lô thô mới nhất          sai kiểu dữ liệu hoặc thiếu ở cột bắt buộc
  3. Tỷ lệ thiếu Family_Income, LMS_Logins         trên lô thô
  4. Data drift: PSI của các biến chính            Train (mô hình đã học) so với scoring set (dữ liệu mới)
  5. Mô hình: phân bố mức rủi ro so với Test; Recall / PR-AUC trên NHÃN MỚI khi đã có kết cục của
     các sinh viên được chấm ở lần trước (concept drift chỉ thấy được khi có nhãn thật).
"""

import json
import sys

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, recall_score
from sqlalchemy import text

from src.core import config, db
from src.core.schema import COLUMNS, NULLABLE_COLUMNS
from src.ml.split import load_features, load_spec, load_splits

EPS = 1e-4


# ---------------------------------------------------------------- chỉ số (hàm thuần, có unit test)

def psi(expected, actual, bins: int = 10) -> float:
    """Population Stability Index; bin theo phân vị của `expected` (mẫu huấn luyện), bỏ giá trị thiếu.

    Biến rời rạc có thể cho ít bin hơn (cạnh trùng nhau được gộp). Tỷ lệ 0 được thay bằng EPS.
    """
    e = pd.Series(expected, dtype=float).dropna().to_numpy()
    a = pd.Series(actual, dtype=float).dropna().to_numpy()
    edges = np.unique(np.quantile(e, np.linspace(0, 1, bins + 1)))
    if len(edges) < 2:
        return 0.0
    edges[0], edges[-1] = -np.inf, np.inf
    pe = np.histogram(e, edges)[0] / len(e)
    pa = np.histogram(a, edges)[0] / len(a)
    pe, pa = np.clip(pe, EPS, None), np.clip(pa, EPS, None)
    return float(np.sum((pa - pe) * np.log(pa / pe)))


def psi_level(value: float, warn: float, alert: float) -> str:
    return "Thay đổi đáng kể" if value > alert else "Cần theo dõi" if value > warn else "Ổn định"


def schema_error_rate(raw: pd.DataFrame) -> float:
    """Tỷ lệ dòng có ô sai kiểu (có giá trị nhưng không ép được) hoặc thiếu ở cột không được phép thiếu."""
    bad = pd.Series(False, index=raw.index)
    for col, kind in COLUMNS.items():
        if col not in raw.columns:
            return 1.0
        values = raw[col]
        present = values.notna() & (values.astype(str).str.strip() != "")
        if kind in {"int", "float", "binary"}:
            bad |= present & pd.to_numeric(values, errors="coerce").isna()
        if col not in NULLABLE_COLUMNS:
            bad |= ~present
    return float(bad.mean())


def performance_on_new_labels(previous: pd.DataFrame, features: pd.DataFrame, target: str) -> dict:
    """Lần chấm cũ (student_id, semester, risk_score, risk_level) ghép với nhãn hiện có của đúng dòng đó.

    Dòng được chấm là kỳ mới nhất của sinh viên đang học (Censored = 1). Khi dữ liệu kỳ sau về, dòng đó
    có nhãn (Censored = 0) → so dự đoán với kết cục thật.
    """
    labeled = features[features["Censored"] == 0][["Student_ID", "Semester", target]]
    m = previous.merge(labeled, left_on=["student_id", "semester"], right_on=["Student_ID", "Semester"])
    out = {"n": int(len(m))}
    if len(m) and 0 < m[target].sum() < len(m):
        y = m[target].astype(int)
        out.update(pr_auc=float(average_precision_score(y, m["risk_score"])),
                   recall_medium=float(recall_score(y, m["risk_level"] != "Thấp")),
                   positive_rate=float(y.mean()))
    return out


# ---------------------------------------------------------------- thu thập

def _latest_raw():
    from src.etl.validate import load_latest_batch
    return load_latest_batch()


def _query(sql: str, **params) -> pd.DataFrame:
    with db.pg_engine().connect() as conn:
        return pd.read_sql(text(sql), conn, params=params)


def collect(pipeline_seconds: float | None = None) -> tuple[dict, list[str]]:
    cfg = config.settings()["monitoring"]
    alerts: list[str] = []
    metrics: dict = {}

    if pipeline_seconds is not None:
        metrics["pipeline_seconds"] = round(pipeline_seconds, 1)
        if pipeline_seconds > cfg["max_pipeline_seconds"]:
            alerts.append(f"Pipeline chạy {pipeline_seconds:.0f} giây > {cfg['max_pipeline_seconds']} giây")

    # 2–3. Lô thô mới nhất
    raw, source = _latest_raw()
    metrics["batch"] = source.get("batch_id") or source.get("Lô") or str(source)
    metrics["schema_error_rate"] = schema_error_rate(raw)
    if metrics["schema_error_rate"] > cfg["max_schema_error_rate"]:
        alerts.append(f"Tỷ lệ lỗi schema {metrics['schema_error_rate']:.2%} > {cfg['max_schema_error_rate']:.1%}")
    metrics["missing_rate"] = {}
    for col in ("Family_Income", "LMS_Logins"):
        rate = float(pd.to_numeric(raw[col], errors="coerce").isna().mean())
        metrics["missing_rate"][col] = rate
        if rate > cfg["max_missing_rate"]:
            alerts.append(f"{col} thiếu {rate:.1%} > {cfg['max_missing_rate']:.0%}")

    # 4. Data drift
    splits = load_splits()
    metrics["psi"] = {}
    for col in cfg["psi_features"]:
        value = psi(splits.X_train[col], splits.X_score[col])
        metrics["psi"][col] = {"value": value, "level": psi_level(value, cfg["psi_warn"], cfg["psi_alert"])}
        if value > cfg["psi_alert"]:
            alerts.append(f"Data drift: PSI {col} = {value:.3f} > {cfg['psi_alert']}")
    metrics["psi_all_numeric"] = {c: psi(splits.X_train[c], splits.X_score[c]) for c in load_spec()["numeric"]}

    # 5. Mô hình
    runs = _query("SELECT run_id, max(run_date) AS run_date, max(model_version) AS model_version FROM predictions "
                  "GROUP BY run_id ORDER BY max(run_date) DESC")
    if runs.empty:
        alerts.append("Chưa có lần chấm điểm nào trong predictions")
    else:
        latest = runs.iloc[0]
        pred = _query("SELECT student_id, semester, risk_score::float8 AS risk_score, risk_level FROM predictions "
                      "WHERE run_id = :r", r=latest["run_id"])
        test = json.loads((config.path("reports_dir") / "test_metrics.json").read_text(encoding="utf-8"))
        test_high = next(r["ty_le_dong"] for r in test["levels"] if r["muc"] == "Cao")
        share_high = float((pred["risk_level"] == "Cao").mean())
        metrics["predictions"] = {"run_id": latest["run_id"], "model_version": str(latest["model_version"]),
                                  "n": int(len(pred)), "share_high": share_high, "test_share_high": test_high,
                                  "mean_score": float(pred["risk_score"].mean())}
        if abs(share_high - test_high) / test_high > cfg["high_share_tolerance"]:
            alerts.append(f"Tỷ lệ mức Cao {share_high:.1%} lệch xa Test ({test_high:.1%})")
        # Nhãn mới: đánh giá các lần chấm TRƯỚC lần mới nhất
        features, target = load_features(), load_spec()["target"]
        perf = []
        for _, r in runs.iloc[1:].iterrows():
            prev = _query("SELECT student_id, semester, risk_score::float8 AS risk_score, risk_level "
                          "FROM predictions WHERE run_id = :r", r=r["run_id"])
            res = {"run_id": r["run_id"], **performance_on_new_labels(prev, features, target)}
            perf.append(res)
            if "pr_auc" in res:
                drop_pr = test["test"]["pr_auc"] - res["pr_auc"]
                drop_rec = test["test"]["at_medium"]["recall"] - res["recall_medium"]
                if max(drop_pr, drop_rec) > cfg["max_metric_drop"]:
                    alerts.append(f"Hiệu năng trên nhãn mới giảm (run {r['run_id']}): PR-AUC {res['pr_auc']:.3f}, "
                                  f"Recall {res['recall_medium']:.3f}")
        metrics["new_label_performance"] = perf
    return metrics, alerts


# ---------------------------------------------------------------- báo cáo

def write_report(metrics: dict, alerts: list[str], run_id: str | None = None) -> None:
    psi_rows = sorted(metrics["psi_all_numeric"].items(), key=lambda kv: -kv[1])[:8]
    pred = metrics.get("predictions", {})
    perf = metrics.get("new_label_performance", [])
    lines = [
        "# BÁO CÁO GIÁM SÁT (B16)",
        f"*Sinh tự động bởi `src/ops/monitor.py` lúc {pd.Timestamp.now():%Y-%m-%d %H:%M}"
        + (f", lần chạy pipeline `{run_id}`" if run_id else "") + ".*",
        "",
        "## Cảnh báo",
        "",
        *([f"* ⚠️ {a}" for a in alerts] or ["Không có chỉ số nào vượt ngưỡng."]),
        "",
        "## 1. Hệ thống và dữ liệu",
        "",
        "| Chỉ số | Giá trị |",
        "|---|---:|",
        *([f"| Thời gian chạy pipeline | {metrics['pipeline_seconds']:.0f} giây |"] if "pipeline_seconds" in metrics else []),
        f"| Lô dữ liệu thô | `{metrics['batch']}` |",
        f"| Tỷ lệ lỗi schema | {metrics['schema_error_rate']:.2%} |",
        *[f"| Thiếu {c} | {v:.1%} |" for c, v in metrics["missing_rate"].items()],
        "",
        "## 2. Data drift (PSI: Train so với sinh viên đang học)",
        "",
        "| Biến giám sát | PSI | Đánh giá |",
        "|---|---:|---|",
        *[f"| {c} | {v['value']:.3f} | {v['level']} |" for c, v in metrics["psi"].items()],
        "",
        "8 biến số có PSI lớn nhất (để tham khảo): "
        + ", ".join(f"`{c}` {v:.3f}" for c, v in psi_rows) + ".",
        "",
        "## 3. Mô hình",
        "",
        f"* Lần chấm mới nhất `{pred.get('run_id')}` (mô hình v{pred.get('model_version')}): {pred.get('n', 0):,} sinh viên, "
        f"mức Cao {pred.get('share_high', 0):.1%} (Test {pred.get('test_share_high', 0):.1%}), "
        f"nguy cơ trung bình {pred.get('mean_score', 0):.1%}.",
        "* Hiệu năng trên nhãn mới: "
        + ("; ".join(f"run `{p['run_id']}`: {p['n']} dòng đã có kết cục"
                     + (f", PR-AUC {p['pr_auc']:.3f}, Recall {p['recall_medium']:.3f}" if "pr_auc" in p else "")
                     for p in perf)
           if perf else "chưa có lần chấm cũ nào có kết cục (cần dữ liệu học kỳ sau)."),
        "",
    ]
    (config.path("reports_dir") / "monitoring_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    metrics, alerts = collect()
    write_report(metrics, alerts)
    for col, v in metrics["psi"].items():
        print(f"PSI {col}: {v['value']:.3f} ({v['level']})")
    print(f"Lỗi schema {metrics['schema_error_rate']:.2%}; thiếu "
          + ", ".join(f"{c} {v:.1%}" for c, v in metrics["missing_rate"].items()))
    for a in alerts or ["Không có cảnh báo."]:
        print(f"[CẢNH BÁO] {a}" if alerts else a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
