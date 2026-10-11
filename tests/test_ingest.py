"""Unit test cho phần kiểm tra schema và checksum của Bước 2 (không cần Docker)."""

import hashlib

import pandas as pd
import pytest

from src.ingest import check_schema, md5_of_file
from src.schema import COLUMNS

ROW = [
    "STU_00001", "18", "Female", "0", "15000", "2", "Off-Campus", "0", "15000", "1", "15",
    "18.4", "0", "2.85", "85.8", "67", "0", "0", "1.7", "0", "Enrolled", "0",
]


@pytest.fixture
def valid_df():
    return pd.DataFrame([ROW, ROW], columns=list(COLUMNS))


def test_valid_file_has_no_errors(valid_df):
    assert check_schema(valid_df) == []


def test_blank_numeric_value_is_allowed(valid_df):
    valid_df.loc[0, "Family_Income"] = ""  # giá trị thiếu được xử lý ở B3/B4, không phải lỗi schema
    assert check_schema(valid_df) == []


def test_missing_column(valid_df):
    errors = check_schema(valid_df.drop(columns=["Sem_GPA"]))
    assert any("Thiếu cột" in e and "Sem_GPA" in e for e in errors)


def test_extra_column(valid_df):
    valid_df["Unexpected"] = "x"
    assert any("không có trong schema" in e for e in check_schema(valid_df))


def test_wrong_column_order(valid_df):
    cols = list(COLUMNS)
    cols[1], cols[2] = cols[2], cols[1]
    assert check_schema(valid_df[cols]) == ["Sai thứ tự cột"]


def test_non_numeric_value(valid_df):
    valid_df.loc[1, "Attendance"] = "abc"
    errors = check_schema(valid_df)
    assert len(errors) == 1 and "Attendance" in errors[0]


def test_empty_file():
    assert "File không có dòng dữ liệu" in check_schema(pd.DataFrame(columns=list(COLUMNS)))


def test_md5_of_file(tmp_path):
    p = tmp_path / "a.csv"
    p.write_bytes(b"hello")
    assert md5_of_file(p) == hashlib.md5(b"hello").hexdigest()
