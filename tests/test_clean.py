"""Unit test cho Bước 4 – làm sạch dữ liệu (không cần Docker)."""

import numpy as np
import pandas as pd
import pytest

from src.etl.clean import OUTPUT_COLUMNS, clean, content_hash, post_checks
from tests.test_validate import make_df  # S1: 3 kỳ (bị cắt), S2: 2 kỳ (bỏ học), S3: 2 kỳ (tốt nghiệp)


def rows_of(df, sid):
    return df[df["Student_ID"] == sid].sort_values("Semester")


@pytest.fixture
def df():
    return make_df()


def test_output_shape_and_columns(df):
    out, _ = clean(df)
    assert len(out) == len(df)
    assert list(out.columns) == OUTPUT_COLUMNS


def test_gender_mapped_to_groups(df):
    out, log = clean(df)
    assert set(out["Gender"]) <= {"Female", "Male", "Other/Unknown"}
    assert rows_of(out, "S2")["Gender"].eq("Male").all()  # "m" → Male
    assert dict(log)["Chuẩn hóa Gender (đổi cách ghi)"] == 2  # 2 dòng của S2


def test_attendance_clipped(df):
    df.loc[0, "Attendance"] = 105
    df.loc[1, "Attendance"] = -2
    out, log = clean(df)
    assert out["Attendance"].between(0, 100).all()
    assert dict(log)["Clip Attendance về [0, 100]"] == 2


def test_family_income_filled_within_student_both_directions(df):
    s1 = df["Student_ID"] == "S1"
    df.loc[s1 & (df["Semester"] == 1), "Family_Income"] = np.nan  # bfill từ kỳ 2
    df.loc[s1 & (df["Semester"] == 3), "Family_Income"] = np.nan  # ffill từ kỳ 2
    out, _ = clean(df)
    assert rows_of(out, "S1")["Family_Income"].eq(15000).all()
    assert out["Income_Missing"].sum() == 0


def test_family_income_never_borrowed_from_other_student(df):
    df.loc[df["Student_ID"] == "S3", "Family_Income"] = np.nan
    out, _ = clean(df)
    s3 = rows_of(out, "S3")
    assert s3["Family_Income"].isna().all()
    assert s3["Income_Missing"].eq(1).all()


def test_lms_only_forward_filled(df):
    s1 = df["Student_ID"] == "S1"
    df.loc[s1 & (df["Semester"] == 1), "LMS_Logins"] = np.nan  # kỳ đầu: không có kỳ trước → vẫn thiếu
    df.loc[s1 & (df["Semester"] == 2), "LMS_Logins"] = 70
    df.loc[s1 & (df["Semester"] == 3), "LMS_Logins"] = np.nan  # lấy từ kỳ 2
    out, _ = clean(df)
    s1_out = rows_of(out, "S1")
    assert pd.isna(s1_out["LMS_Logins"].iloc[0])           # không bfill từ kỳ 2
    assert s1_out["LMS_Logins"].iloc[2] == 70
    assert s1_out["LMS_Missing"].tolist() == [1, 0, 1]


def test_duplicates_keep_last(df):
    dup = df.iloc[[0]].copy()
    dup["Sem_GPA"] = 1.5
    out, log = clean(pd.concat([df, dup], ignore_index=True))
    assert len(out) == len(df)
    assert rows_of(out, "S1")["Sem_GPA"].iloc[0] == 1.5
    assert dict(log)["Khử trùng lặp (Student_ID, Semester)"] == 1


def test_unknown_gender_raises(df):
    df.loc[0, "Gender"] = "xyz"
    with pytest.raises(ValueError):
        clean(df)


def test_post_checks_pass(df):
    out, _ = clean(df)
    assert all(ok for _, ok, _ in post_checks(out, len(df)))


def test_deterministic(df):
    shuffled = df.sample(frac=1, random_state=0)
    assert content_hash(clean(df)[0]) == content_hash(clean(shuffled)[0])
