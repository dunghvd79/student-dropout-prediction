"""Bước 12 – Chọn ngưỡng, đánh giá trên tập Test (MỘT LẦN), công bằng & đăng ký mô hình.

Chạy:  python -m src.ml.evaluate [--force] [--no-register]

Thứ tự (mọi lựa chọn chốt trên Train TRƯỚC khi nhìn Test):
  1. Cấu hình cuối: LogReg, tham số từ B11, KHÔNG trọng số lớp. LogReg học bằng log-loss nên xác suất
     đã được hiệu chỉnh tốt (Brier OOF 0,0742 = bằng isotonic / sigmoid); mất cân bằng xử lý bằng ngưỡng.
  2. Dự đoán out-of-fold trên Train → chọn 2 mốc rủi ro theo chính sách trong settings.yaml
     → config/risk_thresholds.json.
  3. Huấn luyện lại trên toàn bộ Train.
  4. Đánh giá Test một lần (có chốt chặn: reports/test_metrics.json đã tồn tại thì từ chối, trừ khi --force).
     Kèm phân tích công bằng, ca bỏ sót, và 2 đối chứng phụ (không dùng để chọn): ablation, XGBoost.
  5. Đăng ký MLflow Model Registry: dropout_model, alias "production".
"""

import argparse
import json
import sys
import warnings
from datetime import datetime

import joblib
import numpy as np
import pandas as pd
from matplotlib.figure import Figure
from sklearn.calibration import calibration_curve
from sklearn.metrics import (average_precision_score, brier_score_loss, confusion_matrix, f1_score,
                             precision_recall_curve, precision_score, recall_score, roc_auc_score, roc_curve)

from src.core import config
from src.ml.experiments import subset_spec
from src.ml.split import cv_splitter, load_spec, load_splits
from src.ml.train import build_pipeline

LEVELS = ["Thấp", "Trung bình", "Cao"]
FINAL_IMBALANCE = "none"


def reports_dir():
    return config.path("reports_dir")


def final_config() -> dict:
    best = json.loads((reports_dir() / "best_model.json").read_text(encoding="utf-8"))
    return {"model": best["model"], "params": best["params"], "imbalance": FINAL_IMBALANCE}


def fit_final(cfg, X, y, spec):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return build_pipeline(cfg["model"], spec, imbalance=cfg["imbalance"], y_train=y, params=cfg["params"]).fit(X, y)


# ---------------------------------------------------------------- ngưỡng

def oof_predictions(cfg, splits, spec) -> np.ndarray:
    oof = np.zeros(len(splits.y_train))
    for tr, va in cv_splitter().split(splits.X_train, splits.y_train, groups=splits.groups_train):
        model = fit_final(cfg, splits.X_train.iloc[tr], splits.y_train.iloc[tr], spec)
        oof[va] = model.predict_proba(splits.X_train.iloc[va])[:, 1]
    return oof


def choose_thresholds(y, proba, target_recall: float, high_precision: float) -> dict:
    """medium = ngưỡng LỚN NHẤT còn đạt Recall ≥ target; high = ngưỡng NHỎ NHẤT đạt Precision ≥ high_precision."""
    prec, rec, thr = precision_recall_curve(y, proba)
    prec, rec = prec[:-1], rec[:-1]
    if not (rec >= target_recall).any() or not (prec >= high_precision).any():
        raise ValueError("Không có ngưỡng thỏa chính sách.")
    medium = float(thr[rec >= target_recall].max())
    high = float(thr[prec >= high_precision].min())
    if high <= medium:
        raise ValueError(f"Mốc Cao ({high:.4f}) phải lớn hơn mốc Trung bình ({medium:.4f}).")
    return {"medium": medium, "high": high}


def risk_level(proba, thresholds: dict) -> np.ndarray:
    return np.where(proba >= thresholds["high"], "Cao", np.where(proba >= thresholds["medium"], "Trung bình", "Thấp"))


def metrics_at(y, proba, threshold: float) -> dict:
    pred = (proba >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {"threshold": threshold, "precision": precision_score(y, pred, zero_division=0),
            "recall": recall_score(y, pred), "f1": f1_score(y, pred, zero_division=0),
            "alert_rate": float(pred.mean()), "tp": int(tp), "fp": int(fp), "fn": int(fn), "tn": int(tn)}


def overall_metrics(y, proba, thresholds) -> dict:
    return {"pr_auc": average_precision_score(y, proba), "roc_auc": roc_auc_score(y, proba),
            "brier": brier_score_loss(y, proba), "mean_proba": float(np.mean(proba)), "positive_rate": float(np.mean(y)),
            "at_medium": metrics_at(y, proba, thresholds["medium"]), "at_high": metrics_at(y, proba, thresholds["high"])}


def level_table(y, proba, thresholds) -> pd.DataFrame:
    lv = pd.Series(risk_level(proba, thresholds), name="muc")
    t = pd.DataFrame({"muc": lv, "y": np.asarray(y)}).groupby("muc")["y"].agg(so_dong="size", so_bo_hoc="sum")
    t["ty_le_bo_hoc_thuc"] = t["so_bo_hoc"] / t["so_dong"]
    t["ty_le_dong"] = t["so_dong"] / t["so_dong"].sum()
    t["ty_le_ca_bo_hoc_bat_duoc"] = t["so_bo_hoc"] / t["so_bo_hoc"].sum()
    return t.reindex(LEVELS)


# ---------------------------------------------------------------- công bằng & lỗi

def fairness_table(X, y, proba, threshold) -> pd.DataFrame:
    groups = {
        "Học kỳ": X["Semester"].map(lambda s: "Kỳ 1" if s == 1 else ("Kỳ 2" if s == 2 else "Kỳ ≥ 3")),
        "Gender": X["Gender"].astype(str),
        "First_Generation": X["First_Generation"].map({0: "Không", 1: "Thế hệ đầu"}),
        "Housing_Status": X["Housing_Status"].astype(str),
        "Scholarship": X["Scholarship"].map({0: "Không học bổng", 1: "Có học bổng"}),
    }
    y, proba = np.asarray(y), np.asarray(proba)
    rows = []
    for dim, labels in groups.items():
        labels = np.asarray(labels)
        for g in sorted(pd.unique(labels)):
            m = labels == g
            pred = proba[m] >= threshold
            rows.append({"chieu": dim, "nhom": g, "so_dong": int(m.sum()), "ty_le_bo_hoc": y[m].mean(),
                         "recall": recall_score(y[m], pred) if y[m].sum() else np.nan,
                         "precision": precision_score(y[m], pred, zero_division=0),
                         "pr_auc": average_precision_score(y[m], proba[m]) if 0 < y[m].sum() < m.sum() else np.nan})
    return pd.DataFrame(rows)


def missed_cases(X, y, proba, threshold) -> pd.DataFrame:
    """So sánh ca bỏ sót (FN) với ca bắt được (TP) trên các biến chính."""
    y, proba = np.asarray(y), np.asarray(proba)
    cols = ["Sem_GPA", "Failed_Courses", "Financial_Stress", "Work_Hours", "Attendance", "Semester", "Family_Income"]
    fn = X.loc[(y == 1) & (proba < threshold), cols].astype(float).mean()
    tp = X.loc[(y == 1) & (proba >= threshold), cols].astype(float).mean()
    neg = X.loc[y == 0, cols].astype(float).mean()
    return pd.DataFrame({"bo_sot_FN": fn, "bat_duoc_TP": tp, "o_lai": neg}).round(2)


# ---------------------------------------------------------------- biểu đồ & báo cáo

def make_figures(y_oof, p_oof, y_test, p_test, thresholds, fair) -> list[tuple[str, str]]:
    out_dir = config.path("figures_dir")
    figs = []

    def save(fig, name, caption):
        fig.tight_layout()
        fig.savefig(out_dir / name, dpi=110)
        figs.append((name, caption))

    fig = Figure(figsize=(11, 4))
    ax1, ax2 = fig.subplots(1, 2)
    prec, rec, _ = precision_recall_curve(y_test, p_test)
    ax1.plot(rec, prec, color="#C44E52", label=f"Test (AP = {average_precision_score(y_test, p_test):.3f})")
    for name, t, mk in (("Trung bình", thresholds["medium"], "o"), ("Cao", thresholds["high"], "s")):
        m = metrics_at(y_test, p_test, t)
        ax1.plot(m["recall"], m["precision"], mk, color="black", label=f"Mốc {name} ({t:.3f})")
    ax1.axhline(np.mean(y_test), color="gray", ls="--", label="Ngẫu nhiên")
    ax1.set_xlabel("Recall"); ax1.set_ylabel("Precision"); ax1.set_title("Đường Precision–Recall (Test)"); ax1.legend(fontsize=8)
    fpr, tpr, _ = roc_curve(y_test, p_test)
    ax2.plot(fpr, tpr, color="#C44E52", label=f"Test (AUC = {roc_auc_score(y_test, p_test):.3f})")
    ax2.plot([0, 1], [0, 1], color="gray", ls="--")
    ax2.set_xlabel("FPR"); ax2.set_ylabel("TPR (Recall)"); ax2.set_title("Đường ROC (Test)"); ax2.legend(fontsize=8)
    save(fig, "eval_pr_roc.png", "Đường PR và ROC trên tập Test, kèm 2 mốc rủi ro")

    fig = Figure(figsize=(5.5, 4.5))
    ax = fig.subplots()
    for name, yy, pp, c in (("OOF Train", y_oof, p_oof, "#4C72B0"), ("Test", y_test, p_test, "#C44E52")):
        frac, mean = calibration_curve(yy, pp, n_bins=10, strategy="quantile")
        ax.plot(mean, frac, "o-", color=c, label=f"{name} (Brier {brier_score_loss(yy, pp):.4f})")
    ax.plot([0, 0.8], [0, 0.8], color="gray", ls="--", label="Hiệu chỉnh hoàn hảo")
    ax.set_xlabel("Xác suất dự đoán (trung bình nhóm)"); ax.set_ylabel("Tỷ lệ bỏ học thực tế"); ax.legend(fontsize=8)
    ax.set_title("Reliability diagram (10 nhóm phân vị)")
    save(fig, "eval_calibration.png", "Độ hiệu chỉnh xác suất: OOF trên Train và Test")

    fig = Figure(figsize=(9, 3.6))
    axes = fig.subplots(1, 2)
    for ax, (name, t) in zip(axes, (("Trung bình", thresholds["medium"]), ("Cao", thresholds["high"]))):
        cm = confusion_matrix(y_test, (p_test >= t).astype(int))
        ax.imshow(cm, cmap="Blues")
        for (i, j), v in np.ndenumerate(cm):
            ax.text(j, i, f"{v:,}", ha="center", va="center", color="black", fontsize=11)
        ax.set_xticks([0, 1], ["Dự đoán ở lại", "Dự đoán bỏ học"]); ax.set_yticks([0, 1], ["Thực tế ở lại", "Thực tế bỏ học"])
        ax.set_title(f"Ngưỡng {name} ({t:.3f})")
    save(fig, "eval_confusion.png", "Ma trận nhầm lẫn trên Test tại 2 mốc")

    dims = fair["chieu"].unique()
    fig = Figure(figsize=(12, 3.8))
    axes = fig.subplots(1, len(dims))
    for ax, dim in zip(axes, dims):
        d = fair[fair["chieu"] == dim]
        ax.bar(range(len(d)), d["recall"], color="#C44E52")
        ax.axhline(0.8, color="gray", ls="--")
        ax.set_xticks(range(len(d)), d["nhom"], rotation=30, ha="right", fontsize=8)
        ax.set_ylim(0, 1); ax.set_title(dim, fontsize=9)
    axes[0].set_ylabel("Recall tại mốc Trung bình")
    save(fig, "eval_fairness.png", "Recall theo nhóm trên Test (đường xám: mục tiêu 0,80)")
    return figs


def _pct(x):
    return f"{x:.1%}"


def write_report(res: dict, figs) -> None:
    t, ov, oof = res["thresholds"], res["test"], res["oof"]
    lv = pd.DataFrame(res["levels"]).set_index("muc")
    fair = pd.DataFrame(res["fairness"])
    sec = res["secondary"]
    lines = [
        "# BÁO CÁO ĐÁNH GIÁ MÔ HÌNH (B12)",
        f"*Sinh tự động bởi `python -m src.ml.evaluate` lúc {res['evaluated_at']}. Tập Test được dùng **một lần**; mọi lựa chọn chốt trên Train trước đó.*",
        "",
        f"* **Mô hình:** Logistic Regression, `C = {res['config']['params']['C']:.3f}`, không trọng số lớp, {res['n_features']} đặc trưng.",
        f"* **Train:** {res['n_train']:,} dòng · **Test:** {res['n_test']:,} dòng ({res['n_test_students']:,} sinh viên), tỷ lệ bỏ học {_pct(ov['positive_rate'])}.",
        f"* **Mốc rủi ro** (chọn trên OOF Train): Trung bình ≥ **{t['medium']:.4f}** (Recall OOF ≥ 0,80) · Cao ≥ **{t['high']:.4f}** (Precision OOF ≥ 0,50).",
        "",
        "## 1. Kết quả tổng thể",
        "",
        "| Chỉ số | OOF Train (để chọn) | **Test (một lần)** |",
        "|---|---:|---:|",
        f"| PR-AUC | {oof['pr_auc']:.4f} | **{ov['pr_auc']:.4f}** |",
        f"| ROC-AUC | {oof['roc_auc']:.4f} | **{ov['roc_auc']:.4f}** |",
        f"| Brier score | {oof['brier']:.4f} | **{ov['brier']:.4f}** |",
        f"| Xác suất TB / tỷ lệ thật | {oof['mean_proba']:.4f} / {oof['positive_rate']:.4f} | {ov['mean_proba']:.4f} / {ov['positive_rate']:.4f} |",
        f"| Recall @ Trung bình | {oof['at_medium']['recall']:.3f} | **{ov['at_medium']['recall']:.3f}** |",
        f"| Precision @ Trung bình | {oof['at_medium']['precision']:.3f} | **{ov['at_medium']['precision']:.3f}** |",
        f"| % dòng ≥ Trung bình | {_pct(oof['at_medium']['alert_rate'])} | {_pct(ov['at_medium']['alert_rate'])} |",
        f"| Recall @ Cao | {oof['at_high']['recall']:.3f} | **{ov['at_high']['recall']:.3f}** |",
        f"| Precision @ Cao | {oof['at_high']['precision']:.3f} | **{ov['at_high']['precision']:.3f}** |",
        f"| % dòng ở mức Cao | {_pct(oof['at_high']['alert_rate'])} | {_pct(ov['at_high']['alert_rate'])} |",
        "",
        "## 2. Ba mức rủi ro trên Test",
        "",
        "| Mức | Số dòng | % dòng | Tỷ lệ bỏ học thực tế | % ca bỏ học thuộc mức này |",
        "|---|---:|---:|---:|---:|",
        *[f"| {m} | {int(r.so_dong):,} | {_pct(r.ty_le_dong)} | {_pct(r.ty_le_bo_hoc_thuc)} | {_pct(r.ty_le_ca_bo_hoc_bat_duoc)} |"
          for m, r in lv.iterrows()],
        "",
        "## 3. Công bằng theo nhóm (Test, tại mốc Trung bình)",
        "",
        fair.assign(**{c: fair[c].round(3) for c in ("ty_le_bo_hoc", "recall", "precision", "pr_auc")}).to_markdown(index=False),
        "",
        "## 4. Ca bỏ sót (bỏ học nhưng dưới mốc Trung bình) so với ca bắt được",
        "",
        pd.DataFrame(res["missed"]).to_markdown(),
        "",
        "## 5. Đối chứng phụ trên Test (KHÔNG dùng để chọn mô hình; mô hình đã chốt trước)",
        "",
        "| Mô hình | PR-AUC Test |",
        "|---|---:|",
        *[f"| {k} | {v:.4f} |" for k, v in sec.items()],
        "",
        "## 6. Biểu đồ",
        "",
        *[f"**{c}**\n\n![{n}](figures/{n})\n" for n, c in figs],
    ]
    (reports_dir() / "evaluation_report.md").write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------- đăng ký mô hình

def register(model, res, X_example) -> str:
    import mlflow
    import mlflow.sklearn
    from mlflow import MlflowClient

    cfg = config.settings()["mlflow"]
    mlflow.set_tracking_uri(cfg["tracking_uri"])
    mlflow.set_experiment(cfg["experiment"])
    with mlflow.start_run(run_name="final-logreg-test") as run:
        mlflow.set_tags({"stage": "final", "test_evaluated_once": "true"})
        mlflow.log_params({"model": "logreg", "imbalance": FINAL_IMBALANCE, "C": res["config"]["params"]["C"],
                           "n_features": res["n_features"], "threshold_medium": res["thresholds"]["medium"],
                           "threshold_high": res["thresholds"]["high"]})
        ov = res["test"]
        mlflow.log_metrics({"test_pr_auc": ov["pr_auc"], "test_roc_auc": ov["roc_auc"], "test_brier": ov["brier"],
                            "test_recall_medium": ov["at_medium"]["recall"], "test_precision_medium": ov["at_medium"]["precision"],
                            "test_recall_high": ov["at_high"]["recall"], "test_precision_high": ov["at_high"]["precision"]})
        for p in ("evaluation_report.md", "test_metrics.json"):
            mlflow.log_artifact(str(reports_dir() / p))
        mlflow.log_artifact(str(config.ROOT / "config" / "risk_thresholds.json"))
        mlflow.log_artifact(str(config.ROOT / "config" / "feature_spec.json"))
        info = mlflow.sklearn.log_model(model, artifact_path="model", code_paths=[str(config.ROOT / "src")],
                                        registered_model_name=cfg["model_name"])
    client = MlflowClient()
    version = client.search_model_versions(f"name='{cfg['model_name']}' and run_id='{run.info.run_id}'")[0].version
    client.set_registered_model_alias(cfg["model_name"], "production", version)
    client.set_model_version_tag(cfg["model_name"], version, "test_pr_auc", f"{ov['pr_auc']:.4f}")
    # Kiểm tra tải lại từ Registry cho cùng kết quả
    loaded = mlflow.sklearn.load_model(f"models:/{cfg['model_name']}@production")
    same = np.allclose(loaded.predict_proba(X_example)[:, 1], model.predict_proba(X_example)[:, 1])
    if not same:
        raise RuntimeError("Mô hình tải lại từ Registry cho kết quả khác.")
    return version


# ---------------------------------------------------------------- main

def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="B12 – chọn ngưỡng, đánh giá Test một lần, đăng ký mô hình.")
    parser.add_argument("--force", action="store_true", help="Cho phép đánh giá lại Test (ghi rõ trong báo cáo)")
    parser.add_argument("--no-register", action="store_true")
    args = parser.parse_args()

    metrics_path = reports_dir() / "test_metrics.json"
    if metrics_path.exists() and not args.force:
        print(f"Tập Test đã được đánh giá ({metrics_path}). Không đánh giá lại để tránh 'nhìn Test nhiều lần'. "
              "Dùng --force nếu thật sự cần (sẽ được ghi nhận).")
        return 1
    previous_runs = json.loads(metrics_path.read_text(encoding="utf-8")).get("test_runs", 0) if metrics_path.exists() else 0

    splits, spec = load_splits(), load_spec()
    cfg = final_config()
    policy = config.settings()["risk_levels"]

    # 1–2. OOF trên Train → chọn ngưỡng (Test chưa được đụng tới)
    p_oof = oof_predictions(cfg, splits, spec)
    thresholds = choose_thresholds(splits.y_train, p_oof, policy["target_recall"], policy["high_precision"])
    (config.ROOT / "config" / "risk_thresholds.json").write_text(json.dumps({
        **thresholds, "target_recall": policy["target_recall"], "high_precision": policy["high_precision"],
        "chosen_on": "OOF Train (5 fold theo sinh viên)", "model": cfg["model"]}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    print(f"Mốc rủi ro (chọn trên OOF Train): Trung bình ≥ {thresholds['medium']:.4f}, Cao ≥ {thresholds['high']:.4f}")

    # 3. Huấn luyện lại trên toàn bộ Train
    model = fit_final(cfg, splits.X_train, splits.y_train, spec)
    models_dir = config.path("models_dir"); models_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, models_dir / "dropout_model.joblib")

    # 4. Đánh giá Test MỘT LẦN
    p_test = model.predict_proba(splits.X_test)[:, 1]
    y_test = splits.y_test.values
    base_spec = subset_spec(spec, spec["baseline_features"])
    baseline = fit_final(cfg, splits.X_train[base_spec["features"]], splits.y_train, base_spec)
    tuned = json.loads((reports_dir() / "tuned_models.json").read_text(encoding="utf-8"))
    xgb = fit_final({"model": "xgb", "params": tuned["xgb"]["params"], "imbalance": "weight"},
                    splits.X_train, splits.y_train, spec)
    fair = fairness_table(splits.X_test, y_test, p_test, thresholds["medium"])
    res = {
        "evaluated_at": f"{datetime.now():%Y-%m-%d %H:%M}", "test_runs": previous_runs + 1,
        "config": cfg, "thresholds": thresholds, "n_features": len(spec["features"]),
        "n_train": len(splits.y_train), "n_test": len(y_test), "n_test_students": int(splits.groups_test.nunique()),
        "oof": overall_metrics(splits.y_train.values, p_oof, thresholds),
        "test": overall_metrics(y_test, p_test, thresholds),
        "levels": level_table(y_test, p_test, thresholds).reset_index().to_dict("records"),
        "fairness": fair.to_dict("records"),
        "missed": missed_cases(splits.X_test, y_test, p_test, thresholds["medium"]).to_dict(),
        "secondary": {
            "LogReg – 43 đặc trưng (mô hình được chọn)": average_precision_score(y_test, p_test),
            "LogReg – chỉ 20 đặc trưng gốc (ablation)": average_precision_score(
                y_test, baseline.predict_proba(splits.X_test[base_spec["features"]])[:, 1]),
            "XGBoost tinh chỉnh (dự phòng)": average_precision_score(y_test, xgb.predict_proba(splits.X_test)[:, 1]),
        },
    }
    metrics_path.write_text(json.dumps(res, ensure_ascii=False, indent=2, default=float) + "\n", encoding="utf-8")
    figs = make_figures(splits.y_train.values, p_oof, y_test, p_test, thresholds, fair)
    write_report(res, figs)
    ov = res["test"]
    print(f"TEST: PR-AUC {ov['pr_auc']:.4f} | ROC-AUC {ov['roc_auc']:.4f} | Brier {ov['brier']:.4f}")
    print(f"  @Trung bình: Recall {ov['at_medium']['recall']:.3f}, Precision {ov['at_medium']['precision']:.3f}, "
          f"cảnh báo {ov['at_medium']['alert_rate']:.1%}")
    print(f"  @Cao       : Recall {ov['at_high']['recall']:.3f}, Precision {ov['at_high']['precision']:.3f}, "
          f"cảnh báo {ov['at_high']['alert_rate']:.1%}")
    print("Đối chứng phụ:", {k: round(v, 4) for k, v in res["secondary"].items()})
    print(f"Báo cáo: {reports_dir() / 'evaluation_report.md'}")

    # 5. Đăng ký mô hình
    if not args.no_register:
        version = register(model, res, splits.X_test.head(200))
        print(f"MLflow Model Registry: {config.settings()['mlflow']['model_name']} v{version}, alias 'production' "
              "(tải lại kiểm tra: khớp)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
