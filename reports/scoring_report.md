# BÁO CÁO CHẤM ĐIỂM RỦI RO (B14)
*Sinh tự động bởi `python -m src.ml.predict` lúc 2026-10-27 09:15. `run_id = 20261027-v2`, mô hình `dropout_model` v2, 11 giây.*

* **Sinh viên được chấm:** 11,115 (kỳ mới nhất của sinh viên đang theo học, `Censored = 1`).
* **Mốc rủi ro** (`config/risk_thresholds.json`, B12): Trung bình ≥ 0.0717, Cao ≥ 0.3175.
* **Xác suất trung bình:** 8.9% (tỷ lệ bỏ học kỳ sau trên tập có nhãn: 10.2%).

## 1. Phân bố mức rủi ro

| Mức | Số sinh viên | Tỷ lệ | Tỷ lệ trên tập Test (B12) |
|---|---:|---:|---:|
| Thấp | 6,698 | 60.3% | 58.3% |
| Trung bình | 3,978 | 35.8% | 36.0% |
| Cao | 439 | 3.9% | 5.7% |

## 2. Theo học kỳ

|   Học kỳ |   Số SV |   Xác suất TB |   Tỷ lệ mức Cao |
|---------:|--------:|--------------:|----------------:|
|        1 |    2072 |         0.061 |           0.015 |
|        2 |    1892 |         0.081 |           0.043 |
|        3 |    1703 |         0.089 |           0.042 |
|        4 |    1584 |         0.097 |           0.046 |
|        5 |    1380 |         0.101 |           0.054 |
|        6 |    1289 |         0.101 |           0.045 |
|        7 |    1195 |         0.107 |           0.041 |

## 3. Lý do số 1 của sinh viên mức Cao

| Nhóm | Số sinh viên | Tỷ lệ |
|---|---:|---:|
| Kết quả học tập | 213 | 48.5% |
| Trượt môn | 148 | 33.7% |
| Áp lực tài chính | 74 | 16.9% |
| Thế hệ đầu vào đại học | 4 | 0.9% |

## 4. Kiểm tra

| Kiểm tra | Kết quả | Chi tiết |
|---|:---:|---|
| Kiểm tra schema đặc trưng | ✅ | 43 cột khớp feature_spec.json và mô hình |
| Số dòng trong CSDL = số sinh viên được chấm | ✅ | 11,115 / 11,115 |
| Không có risk_score / risk_level / lý do NULL | ✅ |  |
| risk_score trong CSDL khớp kết quả tính | ✅ |  |
| Lịch sử các lần chạy | ✅ | 2 run_id trong bảng predictions |
| Thời gian chạy < 2 phút | ✅ | 11 giây |

## 5. Ví dụ 5 sinh viên rủi ro cao nhất

| student_id   |   semester |   risk_score | top_reason_1                                                                    | top_reason_2                                                                    | top_reason_3                                                             |
|:-------------|-----------:|-------------:|:--------------------------------------------------------------------------------|:--------------------------------------------------------------------------------|:-------------------------------------------------------------------------|
| STU_06912    |          6 |       0.9182 | Kết quả học tập: GPA kỳ này 0,79 (giảm 0,03 so với kỳ trước), GPA tích lũy 1,54 | Trượt môn: Trượt 3 môn kỳ này, tích lũy 8 môn                                   | Áp lực tài chính: Chỉ số áp lực tài chính 7,2 (tăng 0,7 so với kỳ trước) |
| STU_12303    |          7 |       0.8643 | Kết quả học tập: GPA kỳ này 0,92 (giảm 0,18 so với kỳ trước), GPA tích lũy 1,67 | Trượt môn: Trượt 3 môn kỳ này, tích lũy 7 môn                                   | Áp lực tài chính: Chỉ số áp lực tài chính 8,0 (tăng 1,0 so với kỳ trước) |
| STU_07817    |          6 |       0.8049 | Trượt môn: Trượt 3 môn kỳ này, tích lũy 9 môn                                   | Kết quả học tập: GPA kỳ này 1,63 (giảm 0,10 so với kỳ trước), GPA tích lũy 2,10 | Áp lực tài chính: Chỉ số áp lực tài chính 6,5 (tăng 0,4 so với kỳ trước) |
| STU_19807    |          1 |       0.7863 | Trượt môn: Trượt 3 môn kỳ này, tích lũy 3 môn                                   | Kết quả học tập: GPA kỳ này 1,84, GPA tích lũy 1,84                             | Áp lực tài chính: Chỉ số áp lực tài chính 5,4                            |
| STU_14860    |          2 |       0.759  | Kết quả học tập: GPA kỳ này 1,36 (giảm 0,63 so với kỳ trước), GPA tích lũy 1,67 | Áp lực tài chính: Chỉ số áp lực tài chính 7,6 (tăng 2,8 so với kỳ trước)        | Trượt môn: Trượt 2 môn kỳ này, tích lũy 3 môn                            |
