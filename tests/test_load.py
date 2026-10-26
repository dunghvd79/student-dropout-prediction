"""Unit test cho Bước 5 – chuyển dữ liệu sạch sang bảng tĩnh và document (không cần Docker)."""

import numpy as np
import pandas as pd
import pytest

from src.etl.clean import clean
from src.etl.load import (
    BOOL_FIELDS, DOC_LAYOUT, from_documents, restore_types, split_static, to_document,
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
    assert set(doc["socio_economic"]) == {"work_hours", "financial_stress", "emergency_expense"}
    assert doc["engagement"]["lms_logins"] is None
    assert type(doc["academic_performance"]["course_load"]) is int  # kiểu Python, không phải numpy


def test_documents_roundtrip(clean_df):
    docs = [to_document(r) for r in clean_df.to_dict("records")]
    students, profiles = split_static(clean_df)
    static = students.merge(profiles, on="student_id")
    static.columns = [
        {"student_id": "Student_ID", "age": "Age", "gender": "Gender", "first_generation": "First_Generation",
         "household_size": "Household_Size", "housing_status": "Housing_Status",
         "family_income": "Family_Income", "income_missing": "Income_Missing",
         "scholarship": "Scholarship", "tuition_base": "Tuition_Base"}[c]
        for c in static.columns
    ]
    for col in ("First_Generation", "Income_Missing", "Scholarship"):
        static[col] = static[col].astype(int)
    rebuilt = restore_types(from_documents(docs).merge(static, on="Student_ID"))
    expected = clean_df.sort_values(["Student_ID", "Semester"]).reset_index(drop=True)
    pd.testing.assert_frame_equal(rebuilt, expected)
