"""Unit test cho các kiểm tra chất lượng dữ liệu của Bước 3 (không cần Docker)."""

import pandas as pd
import pytest

from src.schema import COLUMNS
from src.validate import (
    check_categories, check_label_logic, check_missing, check_ranges,
    check_semester_continuity, check_static_columns, validate,
)

STATIC = {
    "S1": dict(Age=18, Gender="Female", First_Generation=0, Family_Income=15000, Household_Size=2,
               Housing_Status="Off-Campus", Scholarship=0, Tuition_Base=15000),
    "S2": dict(Age=20, Gender="m", First_Generation=1, Family_Income=80000, Household_Size=5,
               Housing_Status="On-Campus", Scholarship=1, Tuition_Base=25000),
    "S3": dict(Age=19, Gender="Male", First_Generation=1, Family_Income=24000, Household_Size=2,
               Housing_Status="With Parents", Scholarship=0, Tuition_Base=15000),
}
# (sinh viên, số kỳ, kết cục): S1 bị cắt sau 3 kỳ, S2 bỏ học ở kỳ 2, S3 tốt nghiệp sau 2 kỳ
STUDENTS = [("S1", 3, "Censored"), ("S2", 2, "Dropped_Out"), ("S3", 2, "Graduated")]


def make_df() -> pd.DataFrame:
    rows = []
    for sid, n, outcome in STUDENTS:
        for sem in range(1, n + 1):
            last = sem == n
            status = outcome if last and outcome != "Censored" else "Enrolled"
            rows.append({
                "Student_ID": sid, **STATIC[sid], "Semester": sem, "Course_Load": 15, "Work_Hours": 10.0,
                "Emergency_Expense": 0.0, "Sem_GPA": 3.0, "Attendance": 90.0, "LMS_Logins": 60,
                "Advising_Visits": 0, "Failed_Courses": 0, "Financial_Stress": 2.0,
                "Target_Dropout_Next_Sem": int(status == "Dropped_Out"),
                "End_of_Semester_Status": status,
                "Censored": int(last and outcome == "Censored"),
            })
    return pd.DataFrame(rows)[list(COLUMNS)]


@pytest.fixture
def df():
    return make_df()


def test_clean_data_has_no_errors(df):
    for check in (check_missing, check_ranges, check_categories, check_semester_continuity,
                  check_static_columns, check_label_logic):
        assert check(df).status != "ERROR", check.__name__


def test_missing_above_threshold_is_error(df):
    df.loc[0, "LMS_Logins"] = None  # 1/7 ≈ 14% > 10%
    assert check_missing(df).status == "ERROR"


def test_out_of_range_detected(df):
    df.loc[0, "Attendance"] = 105
    result = check_ranges(df)
    assert result.table.loc["Attendance", "tren_max"] == 1
    assert result.status == "ERROR"  # 1/7 dòng vượt ngưỡng 1%


def test_binary_column_must_be_0_or_1(df):
    df.loc[0, "Scholarship"] = 2
    assert check_ranges(df).table.loc["Scholarship", "vi_pham"] == 1


def test_gender_variants_warn_and_unknown_error(df):
    assert check_categories(df).status == "WARN"  # "m" và "Male" là 2 cách ghi của cùng nhóm
    df.loc[0, "Gender"] = "xyz"
    assert check_categories(df).status == "ERROR"


def test_unknown_housing_is_error(df):
    df.loc[0, "Housing_Status"] = "Dorm"
    assert check_categories(df).status == "ERROR"


def test_semester_gap_is_error(df):
    df.loc[(df["Student_ID"] == "S1") & (df["Semester"] == 2), "Semester"] = 4
    assert check_semester_continuity(df).status == "ERROR"


def test_static_column_changing_is_error(df):
    df.loc[(df["Student_ID"] == "S1") & (df["Semester"] == 2), "Tuition_Base"] = 45000
    result = check_static_columns(df)
    assert result.status == "ERROR"
    assert result.table.loc["Tuition_Base", "so_sinh_vien_vi_pham"] == 1


def test_static_check_ignores_missing(df):
    df.loc[(df["Student_ID"] == "S1") & (df["Semester"] == 2), "Family_Income"] = None
    assert check_static_columns(df).status == "OK"


def test_label_logic_valid_is_warn_for_leakage(df):
    assert check_label_logic(df).status == "WARN"


def test_censored_not_on_last_row_is_error(df):
    df.loc[(df["Student_ID"] == "S1") & (df["Semester"] == 1), "Censored"] = 1
    assert check_label_logic(df).status == "ERROR"


def test_target_status_mismatch_is_error(df):
    df.loc[(df["Student_ID"] == "S2") & (df["Semester"] == 2), "End_of_Semester_Status"] = "Enrolled"
    assert check_label_logic(df).status == "ERROR"


def test_validate_stops_on_schema_error(df):
    raw = df.astype(str).drop(columns=["Sem_GPA"])
    results, typed = validate(raw)
    assert typed is None and results[0].status == "ERROR"
