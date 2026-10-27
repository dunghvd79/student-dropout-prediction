"""Giao diện chung: bảng màu, font, mẫu biểu đồ Plotly.

Nguyên tắc (B15 mục 2.2): màu cảnh báo CHỈ dành cho mức rủi ro; mọi thứ khác dùng mực / chì trung tính.
"""

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

PAPER = "#F3F5F4"   # nền "giấy kẻ" lạnh
INK = "#1E2B2F"     # chữ chính
LEAD = "#66767B"    # chữ phụ, mức Thấp, dữ liệu trung tính
RULE = "#D3DCDA"    # đường kẻ
WASH = "#E6ECEA"    # nền phụ (thanh, vùng chọn)
RISK = {"Cao": "#B83227", "Trung bình": "#C7821A", "Thấp": LEAD}
LEVELS = ["Cao", "Trung bình", "Thấp"]

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700&display=swap');
html, body, [class*="st-"], .stMarkdown, button, input, textarea {{
  font-family: 'Be Vietnam Pro', system-ui, sans-serif;
  font-variant-numeric: tabular-nums;
}}
.block-container {{ max-width: 1180px; padding-top: 2.2rem; }}
div[data-testid="stMarkdownContainer"] h1, h1 {{ font-weight: 700; font-size: 1.9rem; letter-spacing: -0.01em;
  color: {INK}; }}
div[data-testid="stMarkdownContainer"] h2 {{ font-weight: 600; font-size: 1.2rem; color: {INK};
  border-top: 1px solid {RULE}; padding: 1.1rem 0 0.2rem 0; margin-top: 1.4rem; }}
div[data-testid="stMarkdownContainer"] h3 {{ font-weight: 600; font-size: 1.02rem; color: {INK}; padding-top: 0.6rem; }}
.lead {{ color: {LEAD}; font-size: 0.95rem; max-width: 72ch; line-height: 1.55; }}
.verdict {{ font-size: 2.05rem; line-height: 1.25; font-weight: 600; color: {INK}; max-width: 30ch;
            margin: 0.4rem 0 0.6rem 0; }}
.verdict .lvl {{ padding: 0 0.15em; border-bottom: 4px solid currentColor; }}
.meta {{ color: {LEAD}; font-size: 0.9rem; }}
.reason {{ display: grid; grid-template-columns: 1.1fr 1fr; gap: 1.4rem; padding: 0.85rem 0;
           border-top: 1px solid {RULE}; }}
.reason .why b {{ display: block; font-weight: 600; color: {INK}; }}
.reason .why span, .reason .do {{ color: {INK}; font-size: 0.95rem; line-height: 1.5; }}
.reason .do {{ border-left: 3px solid {INK}; padding-left: 0.9rem; }}
.tag {{ display: inline-block; font-size: 0.82rem; font-weight: 600; padding: 0.05rem 0.5rem;
        border-radius: 3px; color: white; }}
.stat {{ font-size: 0.95rem; color: {INK}; line-height: 1.6; }}
.stat b {{ font-size: 1.35rem; font-weight: 700; }}
@media (max-width: 760px) {{
  .reason {{ grid-template-columns: 1fr; gap: 0.4rem; }}
  .verdict {{ font-size: 1.55rem; }}
}}
@media (prefers-reduced-motion: reduce) {{ * {{ transition: none !important; animation: none !important; }} }}
</style>
"""


def apply() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    pio.templates["ews"] = go.layout.Template(layout=go.Layout(
        font=dict(family="Be Vietnam Pro, system-ui, sans-serif", color=INK, size=13),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        colorway=[INK, LEAD, "#9AA7AC"],
        separators=",.",  # dấu thập phân kiểu Việt Nam
        xaxis=dict(gridcolor=RULE, linecolor=RULE, zeroline=False, ticks="", tickfont=dict(size=12)),
        yaxis=dict(gridcolor=RULE, linecolor=RULE, zeroline=False, ticks="", tickfont=dict(size=13)),
        margin=dict(l=10, r=10, t=36, b=10),
        hoverlabel=dict(bgcolor="white", font=dict(color=INK)),
        legend=dict(orientation="h", y=1.08, x=0, title=None),
    ))
    pio.templates.default = "ews"


# Giá trị gốc trong dữ liệu → tiếng Việt khi hiển thị
GENDER_VI = {"Female": "Nữ", "Male": "Nam", "Other/Unknown": "Khác / không rõ"}
HOUSING_VI = {"On-Campus": "Ký túc xá", "Off-Campus": "Thuê ngoài", "With Parents": "Ở cùng gia đình"}


def vn_num(x: float, digits: int = 2, sign: bool = False) -> str:
    s = f"{x:+.{digits}f}" if sign else f"{x:.{digits}f}"
    return s.replace(".", ",")


def tag(level: str) -> str:
    return f'<span class="tag" style="background:{RISK[level]}">{level}</span>'


def pct(x: float, digits: int = 1) -> str:
    return f"{x * 100:.{digits}f}".replace(".", ",") + "%"


def num(x: float) -> str:
    return f"{x:,.0f}".replace(",", ".")
