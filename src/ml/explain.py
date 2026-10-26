"""Bước 13 – Giải thích mô hình bằng SHAP (toàn cục + từng sinh viên) và kiểm tra rò rỉ.

Chạy:  python -m src.ml.explain

Mô hình cuối là Logistic Regression → dùng shap.LinearExplainer (chính xác, không xấp xỉ):
    φ_j = β_j · (x_j − E[x_j])      trên thang log-odds, E[·] lấy trên tập Train (đã qua tiền xử lý)
    log-odds(x) = φ_0 + Σ φ_j        (φ_0 = log-odds của "sinh viên trung bình")

Vì sao GOM NHÓM: các biến cùng khái niệm tương quan rất mạnh (Sem_GPA, CGPA, GPA_Roll3 ρ ≈ 0,97) nên
LogReg chia hệ số giữa chúng, có biến mang dấu "ngược" (với C = 1,22: GPA_Roll3 > 0; với C hiện tại:
Work_prev < 0 trong khi Work_Hours > 0). Đọc từng biến sẽ ra lý do vô lý ("làm thêm nhiều ở kỳ trước làm
giảm rủi ro"). SHAP có tính cộng nên tổng φ của cả nhóm vẫn chính xác và mang đúng ý nghĩa: "phần rủi ro
đến từ việc làm thêm". Các cột One-Hot cũng được cộng về biến gốc. Báo cáo tự liệt kê các biến ngược dấu.

Output:
  reports/explanation_report.md, reports/shap_group_importance.csv, reports/figures/shap_*.png
  top_reasons() dùng lại ở B14 (chấm điểm hằng kỳ) và B16 (dashboard).
"""

import json
import sys
from dataclasses import dataclass

import joblib
import numpy as np
import pandas as pd

from src.core import config
from src.ml.split import load_spec, load_splits

# (nhãn tiếng Việt, đặc trưng gốc). Mỗi đặc trưng thuộc đúng một nhóm (có test kiểm tra).
GROUPS = {
    "hoc_tap": ("Kết quả học tập", ["Sem_GPA", "GPA_prev", "Delta_GPA", "CGPA", "GPA_Roll3", "GPA_Slope"]),
    "truot_mon": ("Trượt môn", ["Failed_Courses", "Cum_Failed_Courses", "Failed_Ratio"]),
    "chuyen_can": ("Chuyên cần", ["Attendance", "Attendance_prev", "Delta_Attendance", "Attendance_Roll3"]),
    "lms": ("Học trực tuyến (LMS)", ["LMS_Logins", "LMS_prev", "Delta_LMS", "LMS_Missing"]),
    "ap_luc_tai_chinh": ("Áp lực tài chính", ["Financial_Stress", "Stress_prev", "Delta_Stress", "Financial_Burden_Index"]),
    "thu_nhap": ("Thu nhập & học phí", ["Family_Income", "Income_Missing", "Household_Size", "Tuition_Base",
                                        "Tuition_to_Income"]),
    "dot_xuat": ("Chi phí đột xuất", ["Emergency_Expense", "Cum_Emergency_Expense", "Num_Emergency_Sems", "Has_Emergency"]),
    "hoc_bong": ("Học bổng", ["Scholarship"]),
    "lam_them": ("Làm thêm", ["Work_Hours", "Work_prev", "Delta_Work_Hours"]),
    "co_van": ("Gặp cố vấn", ["Advising_Visits", "Cum_Advising_Visits"]),
    "the_he_dau": ("Thế hệ đầu vào đại học", ["First_Generation"]),
    "tien_trinh": ("Tiến trình & tải học", ["Semester", "Is_First_Semester", "Course_Load"]),
    "nhan_khau": ("Nhân khẩu & nơi ở", ["Age", "Gender", "Housing_Status"]),
}
# Vẫn tính vào điểm rủi ro (để tổng SHAP khớp dự đoán) nhưng KHÔNG đưa ra làm "lý do cảnh báo":
#  - nhân khẩu: không phải thứ cán bộ can thiệp được, nêu ra dễ thành phân biệt đối xử
#  - gặp cố vấn: nhân quả ngược (sinh viên gặp khó mới đi gặp cố vấn, insight #8 của B6)
NOT_A_REASON = {"nhan_khau", "co_van"}


def _vn(x: float, digits: int = 2) -> str:
    """Số kiểu Việt Nam: 1.234,56."""
    s = f"{x:,.{digits}f}"
    return s.replace(",", "_").replace(".", ",").replace("_", ".")


def _change(delta, unit: str = "", digits: int = 2) -> str:
    if pd.isna(delta) or abs(delta) < 10 ** -digits:
        return ""
    return f" ({'tăng' if delta > 0 else 'giảm'} {_vn(abs(delta), digits)}{unit} so với kỳ trước)"


DESCRIBE = {
    "hoc_tap": lambda r: f"GPA kỳ này {_vn(r.Sem_GPA)}{_change(r.Delta_GPA)}, GPA tích lũy {_vn(r.CGPA)}",
    "truot_mon": lambda r: f"Trượt {int(r.Failed_Courses)} môn kỳ này, tích lũy {int(r.Cum_Failed_Courses)} môn",
    "chuyen_can": lambda r: (f"Chuyên cần {_vn(r.Attendance, 0)}%{_change(r.Delta_Attendance, ' điểm', 0)}"
                             if pd.notna(r.Attendance) else "Không có dữ liệu chuyên cần"),
    "lms": lambda r: (f"Đăng nhập LMS {int(r.LMS_Logins)} lần{_change(r.Delta_LMS, ' lần', 0)}"
                      if pd.notna(r.LMS_Logins) and not r.LMS_Missing else "Không có dữ liệu LMS kỳ này"),
    "ap_luc_tai_chinh": lambda r: f"Chỉ số áp lực tài chính {_vn(r.Financial_Stress, 1)}{_change(r.Delta_Stress, '', 1)}",
    "thu_nhap": lambda r: ("Chưa khai báo thu nhập gia đình" if r.Income_Missing else
                           f"Học phí bằng {_vn(100 * r.Tuition_to_Income, 0)}% thu nhập gia đình, hộ {int(r.Household_Size)} người"),
    "dot_xuat": lambda r: (f"Chi phí đột xuất {_vn(r.Emergency_Expense, 0)} kỳ này, {int(r.Num_Emergency_Sems)} kỳ có chi phí đột xuất"
                           if r.Num_Emergency_Sems else "Chưa gặp chi phí đột xuất"),
    "hoc_bong": lambda r: "Có học bổng" if r.Scholarship else "Không có học bổng",
    "lam_them": lambda r: f"Làm thêm {_vn(r.Work_Hours, 0)} giờ/tuần{_change(r.Delta_Work_Hours, ' giờ', 0)}",
    "co_van": lambda r: f"Gặp cố vấn {int(r.Advising_Visits)} lần kỳ này",
    "the_he_dau": lambda r: "Thế hệ đầu tiên trong gia đình vào đại học" if r.First_Generation else "Gia đình đã có người học đại học",
    "tien_trinh": lambda r: f"Học kỳ {int(r.Semester)}, {int(r.Course_Load)} tín chỉ",
    "nhan_khau": lambda r: f"{int(r.Age)} tuổi, {r.Gender}, {r.Housing_Status}",
}


# ---------------------------------------------------------------- tính SHAP

@dataclass
class Explanation:
    base: float                  # φ_0, log-odds của sinh viên trung bình (Train)
    features: pd.DataFrame       # φ theo đặc trưng gốc (One-Hot đã cộng lại), cùng index với X
    groups: pd.DataFrame         # φ theo nhóm khái niệm
    logit: np.ndarray            # log-odds mô hình dự đoán (để kiểm tra tính cộng)

    @property
    def proba(self) -> np.ndarray:
        return 1 / (1 + np.exp(-self.logit))


def original_feature(name: str, spec: dict) -> str:
    """Tên cột sau tiền xử lý → đặc trưng gốc (Gender_Male → Gender)."""
    if name in spec["features"]:
        return name
    for col in spec["categorical"]:
        if name.startswith(f"{col}_"):
            return col
    raise KeyError(name)


def group_of() -> dict[str, str]:
    return {f: g for g, (_, feats) in GROUPS.items() for f in feats}


def explain(model, X: pd.DataFrame, background: pd.DataFrame, spec: dict) -> Explanation:
    """SHAP chính xác cho Pipeline (tiền xử lý → LogisticRegression); background = Train (thô)."""
    import shap

    prep, lr = model[:-1], model[-1]
    names = prep.get_feature_names_out()
    bg, Xt = prep.transform(background), prep.transform(X)
    explainer = shap.LinearExplainer(lr, shap.maskers.Independent(bg, max_samples=len(bg)))
    phi = pd.DataFrame(explainer.shap_values(Xt), columns=names, index=X.index)
    features = phi.T.groupby(lambda c: original_feature(c, spec), sort=False).sum().T[spec["features"]]
    groups = features.T.groupby(group_of(), sort=False).sum().T[list(GROUPS)]
    return Explanation(float(np.ravel(explainer.expected_value)[0]), features, groups, lr.decision_function(Xt))


def top_reasons(group_phi: pd.Series, row: pd.Series, k: int = 3) -> list[dict]:
    """k nhóm đẩy rủi ro LÊN mạnh nhất (φ > 0) của một sinh viên, kèm mô tả bằng giá trị thật."""
    pushing = group_phi.drop(list(NOT_A_REASON)).sort_values(ascending=False)
    pushing = pushing[pushing > 0].head(k)
    return [{"nhom": g, "ten": GROUPS[g][0], "shap": round(float(v), 4), "mo_ta": DESCRIBE[g](row)}
            for g, v in pushing.items()]


def reasons_text(reasons: list[dict]) -> str:
    return "; ".join(f"{r['ten']}: {r['mo_ta']}" for r in reasons) or "Không có yếu tố nào cao hơn mức trung bình"


# ---------------------------------------------------------------- kiểm tra

def opposite_signs(coef: pd.Series, X: pd.DataFrame, spec: dict, min_coef: float = 0.02) -> list[dict]:
    """Trong mỗi nhóm: biến số có hệ số (|β| ≥ min_coef) ngược dấu với biến có |β| lớn nhất của nhóm."""
    out = []
    for _, (_, feats) in GROUPS.items():
        num = [f for f in feats if f in coef.index and f in spec["numeric"]]
        if len(num) < 2:
            continue
        main = coef[num].abs().idxmax()
        for f in num:
            if f != main and abs(coef[f]) >= min_coef and np.sign(coef[f]) != np.sign(coef[main]):
                out.append({"dac_trung": f, "he_so": float(coef[f]), "bien_chinh": main, "he_so_chinh": float(coef[main]),
                            "tuong_quan": float(X[[f, main]].astype(float).corr().iloc[0, 1])})
    return out


def leakage_checks(ex: Explanation, X: pd.DataFrame, spec: dict) -> list[tuple[str, bool, str]]:
    """Dấu hiệu rò rỉ: một biến áp đảo, hoặc một biến nhị phân hiếm có tác động cực lớn."""
    imp = ex.features.abs().mean()
    share = imp / imp.sum()
    top = share.idxmax()
    rows = [("Không biến nào chiếm > 30% tổng |SHAP|", share.max() <= 0.30, f"lớn nhất: {top} {share.max():.1%}")]
    for col in spec["binary"]:
        rare = X[col].astype(float) == 1
        if rare.mean() < 0.05 and rare.any():
            effect = ex.features.loc[rare, col].mean()
            rows.append((f"{col} (hiếm, {rare.mean():.2%} dòng) không đẩy log-odds > 2", abs(effect) <= 2,
                         f"SHAP trung bình khi = 1: {effect:+.2f}"))
    for col in spec["leakage_cols"]:
        rows.append((f"Cột rò rỉ {col} không nằm trong mô hình", col not in spec["features"], ""))
    return rows


# ---------------------------------------------------------------- biểu đồ & báo cáo

def pick_examples(y, proba, thresholds) -> dict[str, int]:
    """Ba sinh viên điển hình (vị trí trong X): trung vị xác suất của mỗi nhóm."""
    y, proba = np.asarray(y), np.asarray(proba)
    cases = {"Rủi ro Cao, thật sự bỏ học": (proba >= thresholds["high"]) & (y == 1),
             "Bị bỏ sót (bỏ học nhưng rủi ro Thấp)": (proba < thresholds["medium"]) & (y == 1),
             "Rủi ro Thấp, ở lại": (proba < thresholds["medium"]) & (y == 0)}
    out = {}
    for name, mask in cases.items():
        idx = np.flatnonzero(mask)
        out[name] = int(idx[np.argsort(proba[idx])[len(idx) // 2]])
    return out


def make_figures(ex: Explanation, X: pd.DataFrame, examples: dict[str, int]) -> list[tuple[str, str]]:
    import matplotlib.pyplot as plt
    import shap

    out_dir = config.path("figures_dir")
    figs = []

    def save(name, caption):
        plt.gcf().tight_layout()
        plt.gcf().savefig(out_dir / name, dpi=110)
        plt.close("all")
        figs.append((name, caption))

    labels = {g: GROUPS[g][0] for g in GROUPS}
    # 1. Toàn cục theo nhóm
    imp = ex.groups.abs().mean().rename(labels).sort_values()
    plt.figure(figsize=(7, 4.5))
    plt.barh(imp.index, imp.values, color="#C44E52")
    plt.xlabel("Trung bình |SHAP| (log-odds)")
    plt.title("Mức ảnh hưởng của từng nhóm yếu tố (Test)")
    save("shap_groups_bar.png", "Tầm quan trọng toàn cục theo nhóm khái niệm (trung bình |SHAP| trên Test)")

    # 2. Beeswarm theo nhóm: màu = log-odds của nhóm (đỏ: đẩy rủi ro lên)
    grp = shap.Explanation(values=ex.groups.values, base_values=np.full(len(ex.groups), ex.base),
                           data=ex.groups.values, feature_names=[labels[g] for g in ex.groups.columns])
    shap.plots.beeswarm(grp, max_display=13, show=False, color_bar=False)
    plt.gcf().set_size_inches(8, 5.5)
    plt.title("Phân bố SHAP theo nhóm (mỗi chấm = một sinh viên-kỳ)")
    save("shap_groups_beeswarm.png", "Beeswarm theo nhóm: vị trí ngang là tác động lên log-odds của từng dòng Test")

    # 3. Beeswarm theo từng đặc trưng gốc (minh họa vấn đề chia hệ số giữa các biến tương quan)
    numeric = [c for c in ex.features.columns if c not in ("Gender", "Housing_Status")]
    top = ex.features[numeric].abs().mean().sort_values(ascending=False).index[:15]
    feat = shap.Explanation(values=ex.features[top].values, base_values=np.full(len(X), ex.base),
                            data=X[top].astype(float).values, feature_names=list(top))
    shap.plots.beeswarm(feat, max_display=15, show=False)
    plt.gcf().set_size_inches(9, 6)
    plt.title("15 đặc trưng đơn lẻ (màu = giá trị đặc trưng)")
    save("shap_features_beeswarm.png", "Beeswarm 15 đặc trưng đơn lẻ (màu = giá trị đặc trưng; đỏ cao, xanh thấp)")

    # 4. Dependence: SHAP của 3 nhóm lớn nhất theo biến đại diện
    show = [("hoc_tap", "Sem_GPA"), ("truot_mon", "Failed_Courses"), ("ap_luc_tai_chinh", "Financial_Stress")]
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.8))
    for ax, (g, col) in zip(axes, show):
        ax.scatter(X[col].astype(float), ex.groups[g], s=4, alpha=0.25, color="#4C72B0")
        ax.axhline(0, color="gray", lw=0.8)
        ax.set_xlabel(col); ax.set_ylabel(f"SHAP nhóm {labels[g]}"); ax.set_title(labels[g], fontsize=10)
    save("shap_dependence.png", "SHAP của nhóm theo biến đại diện (độ tản dọc = phần đóng góp của các biến khác cùng nhóm)")

    # 5. Waterfall cho 3 sinh viên điển hình
    for i, (case, pos) in enumerate(examples.items(), 1):
        e = shap.Explanation(values=ex.groups.iloc[pos].values, base_values=ex.base,
                             feature_names=[labels[g] for g in ex.groups.columns])
        shap.plots.waterfall(e, max_display=8, show=False)
        plt.gcf().set_size_inches(8, 4.8)
        plt.title(f"{case}: xác suất {ex.proba[pos]:.1%}", fontsize=10)
        save(f"shap_waterfall_{i}.png", f"Waterfall (log-odds) – {case}")
    return figs


def write_report(res: dict, figs) -> None:
    g = pd.DataFrame(res["groups"])
    f = pd.DataFrame(res["features"]).head(15)
    lines = [
        "# GIẢI THÍCH MÔ HÌNH BẰNG SHAP (B13)",
        f"*Sinh tự động bởi `python -m src.ml.explain` lúc {res['created_at']}. SHAP chính xác cho Logistic Regression "
        f"(`LinearExplainer`), thang log-odds, nền = trung bình Train. Giải thích trên {res['n_rows']:,} dòng Test.*",
        "",
        f"* Giá trị cơ sở φ₀ = {res['base']:.3f} (log-odds) ↔ xác suất {res['base_proba']:.1%} cho \"sinh viên trung bình\".",
        f"* Kiểm tra tính cộng φ₀ + Σφ = log-odds của mô hình: sai số lớn nhất {res['additivity_error']:.1e}.",
        "",
        "## 1. Nhóm yếu tố quan trọng nhất (toàn cục)",
        "",
        "| Nhóm | Trung bình \\|SHAP\\| | % tổng | Là lý do số 1 ở mức Cao | Có đưa ra làm lý do |",
        "|---|---:|---:|---:|:---:|",
        *[f"| {r.ten} | {r.mean_abs_shap:.3f} | {r.ty_le:.1%} | {r.top1_muc_cao:.1%} | {'' if r.nhom in NOT_A_REASON else '✓'} |"
          for r in g.itertuples()],
        "",
        "Nhân khẩu & nơi ở và Gặp cố vấn vẫn được tính vào điểm rủi ro nhưng không được nêu làm lý do cảnh báo "
        "(không can thiệp được / nhân quả ngược).",
        "",
        "## 2. Đặc trưng đơn lẻ (15 lớn nhất) và dấu hệ số",
        "",
        "| Đặc trưng | Nhóm | Trung bình \\|SHAP\\| | Hệ số (sau chuẩn hóa) |",
        "|---|---|---:|---:|",
        *[f"| {r.dac_trung} | {GROUPS[r.nhom][0]} | {r.mean_abs_shap:.3f} | {r.he_so} |" for r in f.itertuples()],
        "",
        "Biến cùng nhóm tương quan mạnh (ví dụ `Sem_GPA`, `CGPA`, `GPA_Roll3`, ρ ≈ 0,97) nên LogReg chia hệ số giữa "
        "chúng, có biến mang dấu ngược với biến chính của nhóm:",
        "",
        *([f"* `{o['dac_trung']}` ({o['he_so']:+.3f}) ngược dấu với `{o['bien_chinh']}` ({o['he_so_chinh']:+.3f}), "
           f"tương quan {o['tuong_quan']:+.2f}" for o in res["opposite"]] or ["* (không có cặp nào)"]),
        "",
        "Đọc riêng các biến này sẽ ra lý do vô lý, vì vậy lý do cảnh báo được tổng hợp theo **nhóm**, không theo từng biến.",
        "",
        "## 3. Kiểm tra rò rỉ",
        "",
        "| Kiểm tra | Kết quả | Chi tiết |",
        "|---|:---:|---|",
        *[f"| {n} | {'✅' if ok else '❌'} | {d} |" for n, ok, d in res["leakage_checks"]],
        "",
        "## 4. Ví dụ giải thích cho từng sinh viên (`top_reasons`)",
        "",
        *[line for ex in res["examples"] for line in (
            f"**{ex['case']}** – xác suất {ex['proba']:.1%}, mức {ex['muc']}",
            "",
            *([f"{i}. **{r['ten']}** (+{r['shap']:.2f}): {r['mo_ta']}" for i, r in enumerate(ex["reasons"], 1)]
              or ["Không có nhóm nào đẩy rủi ro lên so với sinh viên trung bình."]),
            "")],
        "## 5. Biểu đồ",
        "",
        *[f"**{c}**\n\n![{n}](figures/{n})\n" for n, c in figs],
    ]
    (config.path("reports_dir") / "explanation_report.md").write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------- main

def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    import matplotlib
    matplotlib.use("Agg")
    from src.ml.evaluate import risk_level

    model_path = config.path("models_dir") / "dropout_model.joblib"
    if not model_path.exists():
        print(f"Không thấy {model_path}. Hãy chạy python -m src.ml.evaluate trước.")
        return 1
    model = joblib.load(model_path)
    splits, spec = load_splits(), load_spec()
    thresholds = json.loads((config.ROOT / "config" / "risk_thresholds.json").read_text(encoding="utf-8"))

    X = splits.X_test.reset_index(drop=True)
    ex = explain(model, X, splits.X_train, spec)
    err = float(np.max(np.abs(ex.base + ex.groups.sum(axis=1).values - ex.logit)))
    if err > 1e-6:
        raise RuntimeError(f"SHAP không cộng đúng ra dự đoán (sai số {err:.2e}).")

    # Nhóm nào là lý do số 1 ở các dòng mức Cao
    high = ex.proba >= thresholds["high"]
    first = [top_reasons(ex.groups.iloc[i], X.iloc[i], k=1) for i in np.flatnonzero(high)]
    top1 = pd.Series([r[0]["nhom"] for r in first if r]).value_counts(normalize=True)
    imp = ex.groups.abs().mean()
    groups = pd.DataFrame({"nhom": imp.index, "ten": [GROUPS[g][0] for g in imp.index], "mean_abs_shap": imp.values,
                           "ty_le": (imp / imp.sum()).values, "top1_muc_cao": top1.reindex(imp.index).fillna(0).values})
    groups = groups.sort_values("mean_abs_shap", ascending=False)
    groups.to_csv(config.path("reports_dir") / "shap_group_importance.csv", index=False)

    coef = pd.Series(model[-1].coef_[0], index=model[:-1].get_feature_names_out())
    fimp = ex.features.abs().mean().sort_values(ascending=False)
    features = pd.DataFrame({"dac_trung": fimp.index, "nhom": [group_of()[c] for c in fimp.index],
                             "mean_abs_shap": fimp.values,
                             "he_so": [", ".join(f"{v:+.2f}" for v in coef[[n for n in coef.index
                                                                             if original_feature(n, spec) == c]])
                                       for c in fimp.index]})

    examples = pick_examples(splits.y_test.values, ex.proba, thresholds)
    levels = risk_level(ex.proba, thresholds)
    res = {
        "created_at": f"{pd.Timestamp.now():%Y-%m-%d %H:%M}", "n_rows": len(X), "base": ex.base,
        "base_proba": float(1 / (1 + np.exp(-ex.base))), "additivity_error": err,
        "groups": groups.to_dict("records"), "features": features.to_dict("records"),
        "leakage_checks": leakage_checks(ex, X, spec),
        "opposite": opposite_signs(coef, splits.X_train, spec),
        "examples": [{"case": case, "proba": float(ex.proba[pos]), "muc": str(levels[pos]),
                      "reasons": top_reasons(ex.groups.iloc[pos], X.iloc[pos])} for case, pos in examples.items()],
    }
    figs = make_figures(ex, X, examples)
    write_report(res, figs)

    print(f"φ0 = {ex.base:.3f} (xác suất {res['base_proba']:.1%}); tính cộng: sai số {err:.1e}")
    print(groups.round(3).to_string(index=False))
    for name, ok, detail in res["leakage_checks"]:
        print(f"[{'OK' if ok else 'CẢNH BÁO'}] {name}: {detail}")
    for e in res["examples"]:
        print(f"- {e['case']} ({e['proba']:.1%}): {reasons_text(e['reasons'])}")
    print(f"Báo cáo: {config.path('reports_dir') / 'explanation_report.md'}")
    return 0 if all(ok for _, ok, _ in res["leakage_checks"]) else 1


if __name__ == "__main__":
    sys.exit(main())
