"""Bước 15 – Ứng dụng Streamlit cho cố vấn học tập.

Chạy:  streamlit run app/streamlit_app.py     (http://localhost:8501)
Cần: Docker (PostgreSQL, MongoDB, MLflow) đang chạy; đã chạy B14 (predict) và src.etl.publish.

Bốn trang, đi từ tổng quan tới chi tiết (Shneiderman):
  Cần liên hệ    danh sách theo nguy cơ, có bộ lọc → chọn một dòng để mở hồ sơ
  Hồ sơ          câu kết luận, "Vì sao → Nên làm", đóng góp theo nhóm (SHAP), quỹ đạo các kỳ
  Toàn trường    phân bổ mức rủi ro theo học kỳ / nhóm; xu hướng theo học kỳ
  Nhóm & quy luật  hồ sơ cụm (B8A) và luật kết hợp (B8B)
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from app import data, style  # noqa: E402
from app.style import INK, LEAD, LEVELS, RISK, RULE, WASH, num, pct, vn_num  # noqa: E402
from src.ml.explain import NOT_A_REASON, top_reasons  # noqa: E402

st.set_page_config(page_title="Cảnh báo sớm bỏ học", layout="wide")


def run_or_stop() -> dict:
    try:
        run = data.latest_run()
    except Exception as exc:  # CSDL chưa chạy
        st.error(f"Không kết nối được PostgreSQL. Bật Docker (`docker compose up -d`) rồi tải lại trang.\n\n{exc}")
        st.stop()
    if run is None:
        st.warning("Chưa có kết quả chấm điểm. Chạy `python -m src.ml.predict` rồi tải lại trang.")
        st.stop()
    return run


def open_profile(student_id: str) -> None:
    st.session_state["student_id"] = student_id
    st.switch_page(PAGES["ho_so"])


# ---------------------------------------------------------------- trang 1: cần liên hệ

def page_contact() -> None:
    run = run_or_stop()
    df = data.predictions(run["run_id"])
    st.title("Sinh viên cần liên hệ")
    st.markdown(
        f'<p class="lead">Lần chấm điểm ngày {pd.Timestamp(run["run_date"]):%d/%m/%Y}, mô hình phiên bản '
        f'{run["model_version"]}. {num(len(df))} sinh viên đang học, xếp theo nguy cơ bỏ học ở kỳ tới. '
        'Chọn một dòng để xem lý do và việc nên làm.</p>', unsafe_allow_html=True)

    counts = df["risk_level"].value_counts().reindex(LEVELS, fill_value=0)
    fig = go.Figure()
    for lvl in LEVELS:
        fig.add_bar(y=[""], x=[counts[lvl]], orientation="h", name=f"{lvl}: {num(counts[lvl])}",
                    marker_color=RISK[lvl] if lvl != "Thấp" else WASH,
                    hovertemplate=f"{lvl}: %{{x:,}} sinh viên<extra></extra>")
    fig.update_layout(barmode="stack", height=92, showlegend=True, xaxis=dict(visible=False),
                      yaxis=dict(visible=False), margin=dict(l=0, r=0, t=26, b=0))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    reason_groups = sorted({r.split(":")[0] for r in df["top_reason_1"].dropna() if ":" in r})
    c1, c2, c3, c4 = st.columns([1.3, 1.2, 1.3, 1.2])
    levels = c1.multiselect("Mức rủi ro", LEVELS, default=["Cao"])
    semesters = c2.multiselect("Học kỳ hiện tại", sorted(df["semester"].unique()), placeholder="Tất cả")
    reason = c3.selectbox("Lý do chính", ["Tất cả"] + reason_groups)
    cluster = c4.selectbox("Cụm sinh viên", ["Tất cả"] + sorted(df["cluster_name"].dropna().unique()))
    c5, c6, c7, _ = st.columns([1.3, 1.2, 1.3, 1.2])
    scholarship = c5.selectbox("Học bổng", ["Tất cả", "Có học bổng", "Không học bổng"])
    first_gen = c6.selectbox("Thế hệ đầu vào đại học", ["Tất cả", "Có", "Không"])
    housing = c7.selectbox("Nơi ở", ["Tất cả"] + sorted(df["housing_status"].unique()))

    view = df[df["risk_level"].isin(levels or LEVELS)]
    if semesters:
        view = view[view["semester"].isin(semesters)]
    if reason != "Tất cả":
        view = view[view["top_reason_1"].str.startswith(reason + ":")]
    if cluster != "Tất cả":
        view = view[view["cluster_name"] == cluster]
    if scholarship != "Tất cả":
        view = view[view["scholarship"] == (scholarship == "Có học bổng")]
    if first_gen != "Tất cả":
        view = view[view["first_generation"] == (first_gen == "Có")]
    if housing != "Tất cả":
        view = view[view["housing_status"] == housing]
    view = view.sort_values("risk_score", ascending=False).reset_index(drop=True)

    st.markdown(f"### {num(len(view))} sinh viên phù hợp bộ lọc")
    if view.empty:
        st.info("Không có sinh viên nào khớp bộ lọc. Bỏ bớt điều kiện, ví dụ thêm mức Trung bình.")
        return
    table = view[["student_id", "semester", "risk_score", "risk_level", "top_reason_1", "top_reason_2",
                  "top_reason_3"]]
    event = st.dataframe(
        table, hide_index=True, use_container_width=True, height=460, on_select="rerun",
        selection_mode="single-row",
        column_config={
            "student_id": st.column_config.TextColumn("Mã sinh viên", width="small"),
            "semester": st.column_config.NumberColumn("Kỳ", width="small"),
            "risk_score": st.column_config.ProgressColumn("Nguy cơ", format="%.2f", min_value=0, max_value=1,
                                                          width="small"),
            "risk_level": st.column_config.TextColumn("Mức", width="small"),
            "top_reason_1": st.column_config.TextColumn("Lý do 1", width="large"),
            "top_reason_2": st.column_config.TextColumn("Lý do 2", width="medium"),
            "top_reason_3": st.column_config.TextColumn("Lý do 3", width="medium"),
        })
    rows = event.selection.rows if event else []
    b1, b2 = st.columns([1, 3])
    if rows:
        sid = table.iloc[rows[0]]["student_id"]
        if b1.button(f"Mở hồ sơ {sid}", type="primary"):
            open_profile(sid)
    b2.download_button("Tải danh sách đang lọc (CSV)", table.to_csv(index=False).encode("utf-8-sig"),
                       file_name=f"canh_bao_{run['run_id']}.csv", mime="text/csv")


# ---------------------------------------------------------------- trang 2: hồ sơ

def waterfall(base: float, phi: pd.Series) -> go.Figure:
    """SHAP theo nhóm trên log-odds; tick trục là xác suất tương ứng để cán bộ đọc được."""
    phi = phi[phi.abs() > 0.01].sort_values(key=np.abs, ascending=False)
    shown, rest = phi.head(7), phi.iloc[7:].sum()
    labels = [data.group_label(g) for g in shown.index] + (["Các yếu tố khác"] if abs(rest) > 0.01 else [])
    values = list(shown.values) + ([rest] if abs(rest) > 0.01 else [])
    fig = go.Figure(go.Waterfall(
        orientation="h", y=["Sinh viên trung bình"] + labels + ["Sinh viên này"],
        x=[base] + values + [0], measure=["absolute"] + ["relative"] * len(values) + ["total"],
        base=0, increasing=dict(marker_color=INK), decreasing=dict(marker_color="#A9B6BA"),
        totals=dict(marker_color=LEAD), connector=dict(line=dict(color=RULE, width=1)),
        text=[pct(data.sigmoid(base))] + [vn_num(v, 2, sign=True) for v in values] + [pct(data.sigmoid(base + sum(values)))],
        textposition="outside", hoverinfo="skip"))
    path = base + np.concatenate([[0.0], np.cumsum(values)])
    lo, hi = min(0.0, path.min()) - 0.6, max(0.0, path.max()) + 0.9
    ticks = [p for p in (0.01, 0.02, 0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9) if lo <= np.log(p / (1 - p)) <= hi]
    fig.update_layout(height=60 + 34 * (len(labels) + 2), showlegend=False,
                      yaxis=dict(autorange="reversed", gridcolor="rgba(0,0,0,0)"),
                      xaxis=dict(range=[lo, hi], tickvals=[np.log(p / (1 - p)) for p in ticks],
                                 ticktext=[pct(p, 0) for p in ticks], title="Nguy cơ (thang log-odds)"))
    return fig


def small_multiples(traj: pd.DataFrame, summary: pd.DataFrame) -> go.Figure:
    from plotly.subplots import make_subplots

    panels = [("Sem_GPA", "gpa_tb", "GPA"), ("Failed_Courses", "truot_mon_tb", "Số môn trượt"),
              ("Attendance", "chuyen_can_tb", "Chuyên cần (%)"), ("Financial_Stress", "ap_luc_tc_tb", "Áp lực tài chính")]
    fig = make_subplots(rows=2, cols=2, subplot_titles=[p[2] for p in panels], horizontal_spacing=0.08,
                        vertical_spacing=0.2)
    ref = summary.set_index("semester")
    for i, (col, ref_col, _) in enumerate(panels, 1):
        sem, r, c = traj["Semester"], (i - 1) // 2 + 1, (i - 1) % 2 + 1
        fig.add_scatter(x=ref.index, y=ref[ref_col], mode="lines", line=dict(color="#A9B6BA", width=1.5, dash="dot"),
                        name="Trung bình cùng kỳ", showlegend=i == 1, row=r, col=c,
                        hovertemplate="Kỳ %{x}: TB %{y:.2f}<extra></extra>")
        fig.add_scatter(x=sem, y=traj[col], mode="lines+markers", line=dict(color=INK, width=2.2),
                        marker=dict(size=7), name="Sinh viên này", showlegend=i == 1, row=r, col=c,
                        hovertemplate="Kỳ %{x}: %{y:.2f}<extra></extra>")
        fig.update_xaxes(dtick=1, range=[0.6, max(8, sem.max()) + 0.4], row=r, col=c)
    fig.update_annotations(font=dict(size=13, color=INK))
    fig.update_layout(height=520, legend=dict(y=-0.1, x=0))
    return fig


def page_profile() -> None:
    run = run_or_stop()
    df = data.predictions(run["run_id"]).sort_values("risk_score", ascending=False)
    ids = df["student_id"].tolist()
    current = st.session_state.get("student_id", ids[0])
    st.title("Hồ sơ sinh viên")
    sid = st.selectbox("Mã sinh viên", ids, index=ids.index(current) if current in ids else 0,
                       help="Danh sách xếp từ nguy cơ cao xuống thấp; gõ để tìm.")
    st.session_state["student_id"] = sid
    row = df.set_index("student_id").loc[sid]
    base, groups, features = data.explanations(str(run["model_version"]))
    phi, x = groups.loc[sid], features.loc[sid]
    p, base_rate = row["risk_score"], data.base_rate()
    ratio = p / base_rate
    compare = (f"gấp {ratio:.1f} lần".replace(".", ",") if ratio >= 1.15
               else "ngang" if ratio > 0.85 else f"bằng {ratio:.1f} lần".replace(".", ","))
    st.markdown(
        f'<div class="verdict">Nguy cơ bỏ học kỳ tới {pct(p, 0)}, '
        f'<span class="lvl" style="color:{RISK[row["risk_level"]]}">mức {row["risk_level"].lower()}</span></div>'
        f'<p class="meta">Đang học kỳ {int(row["semester"])}. Nguy cơ {compare} mức chung của toàn trường '
        f'({pct(base_rate)}). Chấm điểm ngày {pd.Timestamp(run["run_date"]):%d/%m/%Y}.</p>',
        unsafe_allow_html=True)

    st.markdown("## Vì sao, và nên làm gì")
    reasons = top_reasons(phi, x, k=3)
    if not reasons:
        st.markdown('<p class="lead">Không có yếu tố nào cao hơn sinh viên trung bình. Chưa cần can thiệp.</p>',
                    unsafe_allow_html=True)
    for r in reasons:
        st.markdown(f'<div class="reason"><div class="why"><b>{r["ten"]}</b><span>{r["mo_ta"]}</span></div>'
                    f'<div class="do">{data.ACTIONS[r["nhom"]]}</div></div>', unsafe_allow_html=True)
    if row["risk_level"] == "Thấp" and reasons:
        st.caption("Mức thấp: các yếu tố trên cao hơn trung bình nhưng chưa đủ để cảnh báo. Theo dõi ở lần chấm sau.")

    left, right = st.columns([1.15, 1])
    with left:
        st.markdown("## Các yếu tố đẩy nguy cơ lên hoặc xuống")
        st.plotly_chart(waterfall(base, phi), use_container_width=True, config={"displayModeBar": False})
        hidden = [data.group_label(g) for g in NOT_A_REASON]
        st.caption(f"Thanh đậm làm tăng nguy cơ, thanh nhạt làm giảm. {' và '.join(hidden)} có tính vào điểm "
                   "nhưng không được nêu làm lý do cảnh báo.")
    with right:
        st.markdown("## Hồ sơ")
        facts = [
            ("Tuổi", int(row["age"])), ("Giới tính", row["gender"]), ("Nơi ở", row["housing_status"]),
            ("Số người trong hộ", int(row["household_size"])),
            ("Thế hệ đầu vào đại học", "Có" if row["first_generation"] else "Không"),
            ("Học bổng", "Có" if row["scholarship"] else "Không"),
            ("Thu nhập gia đình", num(row["family_income"]) if pd.notna(row["family_income"]) else "Chưa khai báo"),
            ("Cụm sinh viên", row["cluster_name"] or "Chưa phân cụm"),
        ]
        st.markdown("".join(f'<div class="stat" style="display:flex;justify-content:space-between;'
                            f'border-top:1px solid {RULE};padding:0.35rem 0"><span style="color:{LEAD}">{k}</span>'
                            f'<span>{v}</span></div>' for k, v in facts), unsafe_allow_html=True)

    st.markdown("## Quỹ đạo qua các kỳ")
    traj = data.trajectory(sid)
    if traj.empty:
        st.info("Không tìm thấy dữ liệu theo kỳ của sinh viên này trong MongoDB.")
    else:
        st.plotly_chart(small_multiples(traj, data.semester_summary()), use_container_width=True,
                        config={"displayModeBar": False})


# ---------------------------------------------------------------- trang 3: toàn trường

def page_overview() -> None:
    run = run_or_stop()
    df = data.predictions(run["run_id"])
    st.title("Toàn trường")
    high, mid = (df["risk_level"] == "Cao").mean(), (df["risk_level"] == "Trung bình").mean()
    st.markdown(
        f'<p class="stat">Trong <b>{num(len(df))}</b> sinh viên đang học, <b style="color:{RISK["Cao"]}">'
        f'{num((df["risk_level"] == "Cao").sum())}</b> người ở mức cao ({pct(high)}) và '
        f'<b style="color:{RISK["Trung bình"]}">{num((df["risk_level"] == "Trung bình").sum())}</b> người ở mức trung '
        f'bình ({pct(mid)}).</p>', unsafe_allow_html=True)

    st.markdown("## Nguy cơ theo nhóm sinh viên")
    groups = data.risk_by_group()
    dim = st.radio("Chia theo", ["Học kỳ", "Học bổng", "Thế hệ đầu", "Nơi ở", "Cụm sinh viên"], horizontal=True)
    g = groups[groups["chieu"] == dim].copy()
    g = g.sort_values("nhom", key=lambda s: s.astype(int)) if dim == "Học kỳ" else g.sort_values("ty_le_cao")
    labels = [f"Kỳ {n}" for n in g["nhom"]] if dim == "Học kỳ" else list(g["nhom"])
    fig = go.Figure()
    fig.add_bar(y=labels, x=g["ty_le_cao"], name="Cao", orientation="h", marker_color=RISK["Cao"],
                customdata=g["so_sinh_vien"], hovertemplate="%{y}: %{x:.1%} mức cao (%{customdata:,} SV)<extra></extra>")
    fig.add_bar(y=labels, x=g["ty_le_trung_binh"], name="Trung bình", orientation="h",
                marker_color=RISK["Trung bình"], hovertemplate="%{y}: %{x:.1%} mức trung bình<extra></extra>")
    fig.update_layout(barmode="stack", height=90 + 38 * len(g), xaxis=dict(tickformat=".0%", title="Tỷ lệ sinh viên"),
                      yaxis=dict(autorange="reversed" if dim == "Học kỳ" else True))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.markdown("## Xu hướng theo học kỳ (toàn bộ dữ liệu lịch sử)")
    s = data.semester_summary()
    cols = st.columns(4)
    for c, (col, title, fmt) in zip(cols, [("ty_le_bo_hoc", "Tỷ lệ bỏ học kỳ sau", ".0%"), ("gpa_tb", "GPA trung bình", ".2f"),
                                           ("chuyen_can_tb", "Chuyên cần (%)", ".0f"),
                                           ("ap_luc_tc_tb", "Áp lực tài chính", ".1f")]):
        f = go.Figure(go.Scatter(x=s["semester"], y=s[col], mode="lines+markers", line=dict(color=INK, width=2),
                                 hovertemplate="Kỳ %{x}: %{y:" + fmt + "}<extra></extra>"))
        f.update_layout(title=dict(text=title, font=dict(size=13)), height=220,
                        xaxis=dict(dtick=1, title=None), yaxis=dict(tickformat=fmt))
        c.plotly_chart(f, use_container_width=True, config={"displayModeBar": False})
    st.caption("Tỷ lệ bỏ học tính trên các kỳ đã biết kết cục; kỳ 8 thấp vì phần lớn sinh viên tốt nghiệp.")


# ---------------------------------------------------------------- trang 4: nhóm & quy luật

def page_patterns() -> None:
    st.title("Nhóm sinh viên và quy luật")
    st.markdown('<p class="lead">Kết quả khai phá dữ liệu (B8) trên toàn bộ 20.000 sinh viên: phân khúc bằng '
                'K-Means và các tổ hợp đặc điểm hay đi cùng việc bỏ học.</p>', unsafe_allow_html=True)
    st.markdown("## Bốn cụm sinh viên")
    cp = data.cluster_profiles().sort_values("ty_le_bo_hoc", ascending=False)
    st.dataframe(
        cp[["cluster_name", "so_sinh_vien", "bo_hoc_pct", "GPA_mean", "Failed_per_sem", "Stress_mean",
            "Work_mean", "Family_Income_trung_vi"]],
        hide_index=True, use_container_width=True,
        column_config={
            "cluster_name": st.column_config.TextColumn("Cụm", width="large"),
            "so_sinh_vien": st.column_config.NumberColumn("Số SV", format="%d"),
            "bo_hoc_pct": st.column_config.ProgressColumn("Đã bỏ học", format="%.0f%%", min_value=0, max_value=100),
            "GPA_mean": st.column_config.NumberColumn("GPA TB", format="%.2f"),
            "Failed_per_sem": st.column_config.NumberColumn("Môn trượt / kỳ", format="%.2f"),
            "Stress_mean": st.column_config.NumberColumn("Áp lực TC", format="%.1f"),
            "Work_mean": st.column_config.NumberColumn("Giờ làm thêm", format="%.0f"),
            "Family_Income_trung_vi": st.column_config.NumberColumn("Thu nhập (trung vị)", format="%d"),
        })
    st.caption("Cụm là phân khúc mô tả (silhouette ≈ 0,13), không phải nhóm tách biệt rõ ràng.")

    st.markdown("## Tổ hợp đặc điểm đi cùng việc bỏ học")
    rules = data.association_rules().sort_values("lift", ascending=False)
    st.dataframe(
        rules[["mo_ta", "so_dong", "ty_le_pct", "gap"]], hide_index=True, use_container_width=True,
        column_config={
            "mo_ta": st.column_config.TextColumn("Khi sinh viên có", width="large"),
            "so_dong": st.column_config.NumberColumn("Số lần gặp", format="%d"),
            "ty_le_pct": st.column_config.ProgressColumn("Tỷ lệ bỏ học kỳ sau", format="%.0f%%", min_value=0,
                                                         max_value=100),
            "gap": st.column_config.TextColumn("Gấp mức chung"),
        })


PAGES = {
    "lien_he": st.Page(page_contact, title="Cần liên hệ", default=True),  # trang mặc định luôn ở địa chỉ gốc /
    "ho_so": st.Page(page_profile, title="Hồ sơ sinh viên", url_path="ho-so"),
    "toan_truong": st.Page(page_overview, title="Toàn trường", url_path="toan-truong"),
    "quy_luat": st.Page(page_patterns, title="Nhóm và quy luật", url_path="quy-luat"),
}
page = st.navigation(list(PAGES.values()))  # chọn trang trước mọi lệnh hiển thị khác
style.apply()
page.run()
