"""Unit test cho Bước 15 – bảng semester_summary cho dashboard (không cần Docker)."""

import pandas as pd
import pytest

from src.etl.clean import clean
from src.etl.publish import SUMMARY_COLUMNS, semester_summary
from tests.test_validate import make_df


@pytest.fixture
def df():
    return clean(make_df())[0]


def test_one_row_per_semester(df):
    s = semester_summary(df)
    assert list(s.columns) == SUMMARY_COLUMNS
    assert s["semester"].tolist() == sorted(df["Semester"].unique())
    assert s["so_sinh_vien"].tolist() == df.groupby("Semester")["Student_ID"].nunique().tolist()


def test_dropout_rate_uses_labeled_rows_only(df):
    df.loc[(df["Student_ID"] == "S1") & (df["Semester"] == 1), ["Censored", "Target_Dropout_Next_Sem"]] = [1, 0]
    s = semester_summary(df).set_index("semester")
    labeled = df[(df["Semester"] == 1) & (df["Censored"] == 0)]
    assert s.loc[1, "so_co_nhan"] == len(labeled)
    assert s.loc[1, "ty_le_bo_hoc"] == pytest.approx(labeled["Target_Dropout_Next_Sem"].mean())
    assert s.loc[1, "so_dang_hoc"] == 1


def test_means_match_clean_table(df):
    s = semester_summary(df).set_index("semester")
    g = df.groupby("Semester")
    pd.testing.assert_series_equal(s["gpa_tb"], g["Sem_GPA"].mean(), check_names=False)
    pd.testing.assert_series_equal(s["ap_luc_tc_tb"], g["Financial_Stress"].mean(), check_names=False)
