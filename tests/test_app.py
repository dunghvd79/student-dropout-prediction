"""Kiểm thử khói cho ứng dụng Streamlit (B15). Cần PostgreSQL có kết quả B14; không có thì bỏ qua."""

import pytest
from sqlalchemy import text


def _has_predictions() -> bool:
    try:
        from src.core import db
        with db.pg_engine().connect() as conn:
            return conn.execute(text("SELECT count(*) FROM predictions")).scalar() > 0
    except Exception:
        return False


@pytest.mark.skipif(not _has_predictions(), reason="Cần Docker (PostgreSQL) và đã chạy python -m src.ml.predict")
def test_default_page_renders_without_error():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("app/streamlit_app.py", default_timeout=120).run()
    assert not at.exception
    assert at.title[0].value == "Sinh viên cần liên hệ"
    assert any("sinh viên phù hợp bộ lọc" in m.value for m in at.markdown)
