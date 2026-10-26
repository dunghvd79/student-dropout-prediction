"""Bước 11 – Huấn luyện, tinh chỉnh & theo dõi bằng MLflow.

Chạy:  python -m src.ml.experiments [--stage all|compare|tune|ablation] [--trials 40] [--no-mlflow]

  compare   CV 5 fold theo sinh viên cho 6 mô hình (trọng số lớp) + so sánh none / weight / smote
            cho logreg, xgb, lgbm → reports/model_comparison.csv
  tune      Optuna (TPE, tối ưu PR-AUC trung bình CV) cho LogReg và mô hình cây tốt nhất
            → reports/tuning_<model>.csv
  ablation  Mô hình đã tinh chỉnh: chỉ đặc trưng gốc so với gốc + chiều dọc; chọn mô hình tốt nhất
            → reports/best_model.json, data/models/oof_best.parquet (dự đoán out-of-fold cho B12)

Chỉ dùng tập Train (load_splits). Tập Test để dành cho B12, dùng đúng một lần.
"""

import argparse
import json
import subprocess
import sys
import time
import warnings
from dataclasses import dataclass, field

import numpy as np
import optuna
import pandas as pd
from sklearn.metrics import average_precision_score, f1_score, precision_score, recall_score, roc_auc_score

from src.core import config
from src.ml.split import cv_splitter, load_spec, load_splits
from src.ml.train import build_pipeline

TREE_MODELS = ["dtree", "rf", "xgb", "lgbm"]
COMPARE_CONFIGS = (
    [(m, "weight") for m in ["dummy", "logreg", "dtree", "rf", "xgb", "lgbm"]]
    + [(m, imb) for m in ["logreg", "xgb", "lgbm"] for imb in ("none", "smote")]
)
METRICS = ["pr_auc", "roc_auc", "precision", "recall", "f1"]


# ---------------------------------------------------------------- cross-validation

def subset_spec(spec: dict, features: list[str]) -> dict:
    keep = set(features)
    return {**spec, "features": [c for c in spec["features"] if c in keep],
            **{k: [c for c in spec[k] if c in keep] for k in ("numeric", "binary", "categorical")}}


def fold_metrics(y, proba, threshold: float = 0.5) -> dict:
    pred = (proba >= threshold).astype(int)
    return {
        "pr_auc": average_precision_score(y, proba),
        "roc_auc": roc_auc_score(y, proba),
        "precision": precision_score(y, pred, zero_division=0),
        "recall": recall_score(y, pred),
        "f1": f1_score(y, pred, zero_division=0),
    }


@dataclass
class CVResult:
    model: str
    imbalance: str
    feature_set: str
    params: dict
    folds: list[dict]
    oof: np.ndarray
    seconds: float
    n_features: int = 0
    extra: dict = field(default_factory=dict)

    def summary(self) -> dict:
        df = pd.DataFrame(self.folds)
        out = {"model": self.model, "imbalance": self.imbalance, "feature_set": self.feature_set,
               "n_features": self.n_features, "seconds": round(self.seconds, 1)}
        for m in METRICS:
            out[f"{m}_mean"] = df[m].mean()
            out[f"{m}_std"] = df[m].std(ddof=1)
        return out


def cross_validate(name, X, y, groups, spec, imbalance="weight", params=None, feature_set="full",
                   on_fold=None) -> CVResult:
    """CV theo sinh viên. Mỗi fold dựng Pipeline mới (tiền xử lý + scale_pos_weight học lại trên fold)."""
    oof = np.full(len(y), np.nan)
    folds, start = [], time.perf_counter()
    for k, (tr, va) in enumerate(cv_splitter().split(X, y, groups=groups)):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            pipe = build_pipeline(name, spec, imbalance=imbalance, y_train=y.iloc[tr], params=params)
            pipe.fit(X.iloc[tr], y.iloc[tr])
            oof[va] = pipe.predict_proba(X.iloc[va])[:, 1]
        folds.append(fold_metrics(y.iloc[va], oof[va]))
        if on_fold is not None:
            on_fold(k, folds[-1]["pr_auc"])  # dùng cho Optuna pruning
    return CVResult(name, imbalance, feature_set, params or {}, folds, oof,
                    time.perf_counter() - start, n_features=len(spec["features"]))


# ---------------------------------------------------------------- MLflow

class Tracker:
    """Ghi MLflow nếu bật; nếu MLflow lỗi thì báo và chạy tiếp (không làm hỏng thí nghiệm)."""

    def __init__(self, enabled: bool):
        self.enabled = enabled
        if not enabled:
            return
        import mlflow

        self.mlflow = mlflow
        cfg = config.settings()["mlflow"]
        mlflow.set_tracking_uri(cfg["tracking_uri"])
        mlflow.set_experiment(cfg["experiment"])
        # leaky = false: phân biệt với 19 run của lần chạy có rò rỉ Income_Missing (gắn leaky = true ở B13)
        self.tags = {"data_md5": _data_md5(), "git_commit": _git_commit(), "cv": "StratifiedGroupKFold(5)", "leaky": "false"}

    def log(self, stage: str, result: CVResult, artifacts: list | None = None) -> str | None:
        if not self.enabled:
            return None
        try:
            run_name = f"{stage}-{result.model}-{result.imbalance}-{result.feature_set}"
            with self.mlflow.start_run(run_name=run_name) as run:
                self.mlflow.set_tags({**self.tags, "stage": stage})
                self.mlflow.log_params({"model": result.model, "imbalance": result.imbalance,
                                        "feature_set": result.feature_set, "n_features": result.n_features,
                                        **{f"p_{k}": v for k, v in result.params.items()}})
                s = result.summary()
                self.mlflow.log_metrics({k: float(v) for k, v in s.items() if k.endswith(("_mean", "_std"))})
                self.mlflow.log_metric("cv_seconds", result.seconds)
                for k, fold in enumerate(result.folds):
                    self.mlflow.log_metrics({f"fold_{m}": float(v) for m, v in fold.items()}, step=k)
                for path in artifacts or []:
                    self.mlflow.log_artifact(str(path))
                return run.info.run_id
        except Exception as e:  # MLflow chỉ để theo dõi; lỗi ghi log không được dừng thí nghiệm
            print(f"  [MLflow] không ghi được: {type(e).__name__}: {e}")
            return None


def _git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=config.ROOT,
                              capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return "unknown"


def _data_md5() -> str:
    try:
        from sqlalchemy import text

        from src.core import db

        with db.pg_engine().connect() as conn:
            return conn.execute(text("SELECT md5 FROM ingestion_log WHERE status = 'SUCCESS' "
                                     "ORDER BY ingested_at DESC LIMIT 1")).scalar() or "unknown"
    except Exception:
        return "unknown"


# ---------------------------------------------------------------- các giai đoạn

def _print(result: CVResult) -> None:
    s = result.summary()
    print(f"  {s['model']:<7} {s['imbalance']:<7} {s['feature_set']:<9} PR-AUC {s['pr_auc_mean']:.4f} ± "
          f"{s['pr_auc_std']:.4f} | ROC-AUC {s['roc_auc_mean']:.4f} | Recall@0.5 {s['recall_mean']:.3f} "
          f"| Precision@0.5 {s['precision_mean']:.3f} | {s['seconds']:.0f}s")


def stage_compare(splits, spec, tracker) -> pd.DataFrame:
    print(f"[compare] {len(COMPARE_CONFIGS)} cấu hình, CV 5 fold theo sinh viên")
    rows = []
    for name, imbalance in COMPARE_CONFIGS:
        r = cross_validate(name, splits.X_train, splits.y_train, splits.groups_train, spec, imbalance)
        _print(r)
        tracker.log("compare", r)
        rows.append({"stage": "compare", **r.summary()})
    table = pd.DataFrame(rows)
    table.to_csv(config.path("reports_dir") / "model_comparison.csv", index=False, encoding="utf-8-sig")
    return table


def search_space(trial: optuna.Trial, name: str) -> dict:
    if name == "logreg":
        return {"C": trial.suggest_float("C", 1e-3, 10.0, log=True)}
    if name == "lgbm":
        return {
            "n_estimators": trial.suggest_int("n_estimators", 150, 900, step=50),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.15, log=True),
            "num_leaves": trial.suggest_int("num_leaves", 7, 63),
            "min_child_samples": trial.suggest_int("min_child_samples", 20, 300, log=True),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
            "reg_lambda": trial.suggest_float("reg_lambda", 1e-3, 10.0, log=True),
        }
    if name == "xgb":
        return {
            "n_estimators": trial.suggest_int("n_estimators", 150, 900, step=50),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.15, log=True),
            "max_depth": trial.suggest_int("max_depth", 2, 8),
            "min_child_weight": trial.suggest_float("min_child_weight", 1.0, 30.0, log=True),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
            "reg_lambda": trial.suggest_float("reg_lambda", 1e-3, 10.0, log=True),
        }
    if name == "rf":
        return {
            "n_estimators": trial.suggest_int("n_estimators", 200, 600, step=100),
            "min_samples_leaf": trial.suggest_int("min_samples_leaf", 5, 100, log=True),
            "max_features": trial.suggest_float("max_features", 0.2, 0.8),
        }
    raise ValueError(f"Chưa có không gian tìm kiếm cho {name}")


def tune(name: str, splits, spec, n_trials: int, tracker) -> dict:
    """Optuna TPE + MedianPruner (cắt sớm thử nghiệm kém sau từng fold). Trả về tham số tốt nhất."""
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    rs = config.settings()["project"]["random_state"]

    def objective(trial):
        params = search_space(trial, name)

        def report(k, value):
            trial.report(value, k)
            if trial.should_prune():
                raise optuna.TrialPruned()

        r = cross_validate(name, splits.X_train, splits.y_train, splits.groups_train, spec, "weight",
                           params=params, on_fold=report)
        return r.summary()["pr_auc_mean"]

    study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=rs),
                                pruner=optuna.pruners.MedianPruner(n_startup_trials=5, n_warmup_steps=1))
    start = time.perf_counter()
    study.optimize(objective, n_trials=n_trials)
    trials = study.trials_dataframe()
    path = config.path("reports_dir") / f"tuning_{name}.csv"
    trials.to_csv(path, index=False, encoding="utf-8-sig")
    n_pruned = int((trials["state"] == "PRUNED").sum())
    print(f"  {name}: {n_trials} thử nghiệm ({n_pruned} bị cắt sớm), {time.perf_counter() - start:.0f}s; "
          f"tốt nhất PR-AUC {study.best_value:.4f} với {study.best_params}")
    return study.best_params


def stage_tune(splits, spec, n_trials, tracker) -> dict:
    comparison = pd.read_csv(config.path("reports_dir") / "model_comparison.csv")
    weighted = comparison[(comparison["imbalance"] == "weight") & comparison["model"].isin(TREE_MODELS)]
    best_tree = weighted.sort_values("pr_auc_mean", ascending=False)["model"].iloc[0]
    candidates = ["logreg", best_tree]
    print(f"[tune] Optuna cho {candidates} (LogReg + mô hình cây tốt nhất), {n_trials} thử nghiệm mỗi mô hình")
    tuned = {}
    for name in candidates:
        params = tune(name, splits, spec, n_trials, tracker)
        r = cross_validate(name, splits.X_train, splits.y_train, splits.groups_train, spec, "weight", params)
        _print(r)
        tracker.log("tuned", r, artifacts=[config.path("reports_dir") / f"tuning_{name}.csv"])
        tuned[name] = {"params": params, **r.summary()}
    (config.path("reports_dir") / "tuned_models.json").write_text(
        json.dumps(tuned, ensure_ascii=False, indent=2, default=float) + "\n", encoding="utf-8")
    return tuned


def stage_ablation(splits, spec, tracker) -> dict:
    tuned = json.loads((config.path("reports_dir") / "tuned_models.json").read_text(encoding="utf-8"))
    base_spec = subset_spec(spec, spec["baseline_features"])
    print("[ablation] Chỉ đặc trưng gốc (20) so với gốc + chiều dọc (43), cùng tham số đã tinh chỉnh")
    rows, results = [], {}
    for name, info in tuned.items():
        for feature_set, sp in (("baseline", base_spec), ("full", spec)):
            X = splits.X_train[sp["features"]]
            r = cross_validate(name, X, splits.y_train, splits.groups_train, sp, "weight", info["params"],
                               feature_set=feature_set)
            _print(r)
            tracker.log("ablation", r)
            rows.append({"stage": "ablation", **r.summary()})
            results[(name, feature_set)] = r
    ablation = pd.DataFrame(rows)
    ablation.to_csv(config.path("reports_dir") / "ablation.csv", index=False, encoding="utf-8-sig")

    full = ablation[ablation["feature_set"] == "full"].sort_values("pr_auc_mean", ascending=False)
    best_by_cv = full["model"].iloc[0]
    # Mô hình cuối do nhóm chốt trong settings.yaml (model.final); không có thì lấy PR-AUC CV cao nhất
    best_name = config.settings()["model"].get("final") or best_by_cv
    best = results[(best_name, "full")]
    models_dir = config.path("models_dir")
    models_dir.mkdir(parents=True, exist_ok=True)
    oof = splits.keys_train.assign(y=splits.y_train.values, oof_proba=best.oof)
    oof.to_parquet(models_dir / "oof_best.parquet", index=False)
    info = {"model": best_name, "imbalance": "weight", "feature_set": "full", "params": tuned[best_name]["params"],
            "cv": {k: float(v) for k, v in best.summary().items() if k.endswith(("_mean", "_std"))},
            "best_by_cv": best_by_cv,
            "cv_by_model": dict(zip(full["model"], full["pr_auc_mean"].astype(float))),
            "oof_path": "data/models/oof_best.parquet"}
    (config.path("reports_dir") / "best_model.json").write_text(
        json.dumps(info, ensure_ascii=False, indent=2, default=float) + "\n", encoding="utf-8")
    print(f"Mô hình được chọn: {best_name} (PR-AUC CV {info['cv']['pr_auc_mean']:.4f}; cao nhất theo CV: {best_by_cv}); "
          f"OOF lưu tại {info['oof_path']}")
    return info


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="B11 – so sánh, tinh chỉnh, ablation (chỉ dùng tập Train).")
    parser.add_argument("--stage", choices=["all", "compare", "tune", "ablation"], default="all")
    parser.add_argument("--trials", type=int, default=40)
    parser.add_argument("--no-mlflow", action="store_true")
    args = parser.parse_args()

    splits, spec = load_splits(), load_spec()
    tracker = Tracker(enabled=not args.no_mlflow)
    print(f"Train: {len(splits.y_train):,} dòng, {splits.groups_train.nunique():,} sinh viên, "
          f"tỷ lệ dương {splits.y_train.mean():.2%} (Test chưa được dùng)")
    if args.stage in ("all", "compare"):
        stage_compare(splits, spec, tracker)
    if args.stage in ("all", "tune"):
        stage_tune(splits, spec, args.trials, tracker)
    if args.stage in ("all", "ablation"):
        stage_ablation(splits, spec, tracker)
    return 0


if __name__ == "__main__":
    sys.exit(main())
