"""Unit test cho Bước 7 – đặc trưng theo chiều dọc (không cần Docker; đọc 50 sinh viên đầu từ CSV gốc)."""

import numpy as np
import pandas as pd
import pytest

from src.analysis.features import KEYS, NON_FEATURES, build_features, feature_spec
from src.core import config
from src.etl.clean import clean
from src.etl.validate import to_typed


@pytest.fixture(scope="module")
def clean_df():
    raw = pd.read_csv(config.path("source_csv"), dtype=str, keep_default_na=False, nrows=400)
    raw = raw[raw["Student_ID"].isin(raw["Student_ID"].unique()[:50])]
    return clean(to_typed(raw))[0]


@pytest.fixture(scope="module")
def feats(clean_df):
    return build_features(clean_df)


def row(feats, sid, sem):
    return feats[(feats["Student_ID"] == sid) & (feats["Semester"] == sem)].iloc[0]


def test_known_values_stu_00001(feats):
    # STU_00001: GPA 2.85, 2.73, 2.60, 2.34, 1.90; môn trượt 0, 0, 2, 3, 2; tín chỉ 15, 15, 15, 15, 18
    assert row(feats, "STU_00001", 2)["Delta_GPA"] == pytest.approx(-0.12)
    assert row(feats, "STU_00001", 4)["Cum_Failed_Courses"] == 5
    assert row(feats, "STU_00001", 2)["CGPA"] == pytest.approx((2.85 + 2.73) / 2)
    assert row(feats, "STU_00001", 2)["GPA_Slope"] == pytest.approx(-0.12)
    assert row(feats, "STU_00001", 3)["GPA_Roll3"] == pytest.approx((2.85 + 2.73 + 2.60) / 3)
    assert row(feats, "STU_00001", 5)["GPA_Roll3"] == pytest.approx((2.60 + 2.34 + 1.90) / 3)


def test_first_semester_has_no_history(feats):
    first = feats[feats["Semester"] == 1]
    assert first["Is_First_Semester"].eq(1).all()
    for col in ("GPA_prev", "Delta_GPA", "Stress_prev", "GPA_Slope"):
        assert first[col].isna().all(), col  # không mượn dữ liệu của sinh viên đứng trước


def test_slope_matches_numpy_polyfit(feats):
    s = feats[feats["Student_ID"] == "STU_00001"].sort_values("Semester")
    for t in range(2, len(s) + 1):
        expected = np.polyfit(s["Semester"][:t], s["Sem_GPA"][:t], 1)[0]
        assert s["GPA_Slope"].iloc[t - 1] == pytest.approx(expected)


def test_no_future_information(clean_df, feats):
    """Xóa kỳ cuối của mọi sinh viên rồi tính lại: đặc trưng các kỳ còn lại phải không đổi."""
    last = clean_df.groupby("Student_ID")["Semester"].transform("max")
    truncated = build_features(clean_df[clean_df["Semester"] < last])
    expected = feats.merge(truncated[KEYS], on=KEYS)
    pd.testing.assert_frame_equal(truncated.reset_index(drop=True), expected.reset_index(drop=True))


def test_row_order_does_not_matter(clean_df, feats):
    shuffled = build_features(clean_df.sample(frac=1, random_state=0))
    pd.testing.assert_frame_equal(shuffled, feats)


def test_spec_is_consistent(feats):
    spec = feature_spec()
    assert set(spec["features"]) <= set(feats.columns)
    assert not set(spec["features"]) & set(NON_FEATURES + ["Student_ID"])  # không có nhãn / cột rò rỉ
    assert sorted(spec["baseline_features"] + spec["longitudinal_features"]) == sorted(spec["features"])
    assert len(feats) == feats[KEYS].drop_duplicates().shape[0]
