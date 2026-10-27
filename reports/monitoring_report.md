# BÁO CÁO GIÁM SÁT (B16)
*Sinh tự động bởi `src/ops/monitor.py` lúc 2026-10-27 09:15, lần chạy pipeline `run_20261027T091452`.*

## Cảnh báo

Không có chỉ số nào vượt ngưỡng.

## 1. Hệ thống và dữ liệu

| Chỉ số | Giá trị |
|---|---:|
| Thời gian chạy pipeline | 59 giây |
| Lô dữ liệu thô | `20261011T085849Z_7df267` |
| Tỷ lệ lỗi schema | 0.00% |
| Thiếu Family_Income | 4.5% |
| Thiếu LMS_Logins | 1.1% |

## 2. Data drift (PSI: Train so với sinh viên đang học)

| Biến giám sát | PSI | Đánh giá |
|---|---:|---|
| Sem_GPA | 0.014 | Ổn định |
| Financial_Stress | 0.010 | Ổn định |
| Attendance | 0.011 | Ổn định |

8 biến số có PSI lớn nhất (để tham khảo): `Semester` 0.098, `Cum_Failed_Courses` 0.022, `Cum_Advising_Visits` 0.018, `GPA_Slope` 0.017, `Attendance_prev` 0.016, `Attendance_Roll3` 0.016, `Sem_GPA` 0.014, `Delta_Attendance` 0.013.

## 3. Mô hình

* Lần chấm mới nhất `20261027-v2` (mô hình v2): 11,115 sinh viên, mức Cao 3.9% (Test 5.7%), nguy cơ trung bình 8.9%.
* Hiệu năng trên nhãn mới: run `20261026-v2`: 0 dòng đã có kết cục
