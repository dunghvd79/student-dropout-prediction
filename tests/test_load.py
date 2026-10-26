"""Unit test cho Bước 5 – chuyển dữ liệu sạch sang bảng tĩnh và document (không cần Docker)."""

import numpy as np
import pandas as pd
import pytest

from src.etl.clean import clean
from src.etl.load import (
    BOOL_FIELDS, DOC_LAYOUT, from_documents, merge_static, split_static, static_from_tables, to_document,
)
from tests.test_validate import make_df


@pytest.fixture
def clean_df():
    df = make_df()
    df.loc[0, "LMS_Logins"] = np.nan  # kỳ 1 của S1 thiếu LMS → None trong document
    return clean(df)[0]


def test_split_static_one_row_per_student(clean_df):
    students, profiles = split_static(clean_df)
    assert len(students) == len(profiles) == clean_df["Student_ID"].nunique()
    assert list(profiles.columns) == ["student_id", "scholarship", "tuition_base"]
    assert "semester" not in students.columns
    for frame in (students, profiles):
        for col in BOOL_FIELDS & set(frame.columns):
            assert frame[col].dtype == bool


def test_document_structure(clean_df):
    doc = to_document(clean_df.iloc[0].to_dict())
    assert doc["student_id"] == "S1" and doc["semester"] == 1
    assert set(doc) == {"student_id", "semester", *DOC_LAYOUT}
    assert set(doc["socio_economic"]) == {"work_hours", "financial_stress", "emergency_expense", "income_missing"}
    assert doc["engagement"]["lms_logins"] is None
    assert type(doc["academic_performance"]["course_load"]) is int  # kiểu Python, không phải numpy


def test_documents_roundtrip(clean_df):
    docs = [to_document(r) for r in clean_df.to_dict("records")]
    rebuilt = merge_static(from_documents(docs), static_from_tables(*split_static(clean_df)))
    expected = clean_df.sort_values(["Student_ID", "Semester"]).reset_index(drop=True)
    pd.testing.assert_frame_equal(rebuilt, expected)


def test_income_declared_later_roundtrip():
    """Kỳ 1 chưa khai báo, kỳ 2 mới khai báo: students giữ thu nhập, bảng phẳng vẫn trống ở kỳ 1."""
    df = make_df()
    df.loc[(df["Student_ID"] == "S1") & (df["Semester"] == 1), "Family_Income"] = np.nan
    clean_df = clean(df)[0]
    students, profiles = split_static(clean_df)
    s1 = students.set_index("student_id").loc["S1"]
    assert s1["family_income"] == 15000 and not s1["income_missing"]
    docs = [to_document(r) for r in clean_df.to_dict("records")]
    rebuilt = merge_static(from_documents(docs), static_from_tables(students, profiles))
    pd.testing.assert_frame_equal(rebuilt, clean_df.sort_values(["Student_ID", "Semester"]).reset_index(drop=True))
    first = rebuilt[(rebuilt["Student_ID"] == "S1") & (rebuilt["Semester"] == 1)]
    assert first["Family_Income"].isna().all()
