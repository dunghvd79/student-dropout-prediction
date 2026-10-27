# NHẬT KÝ LÀM SẠCH DỮ LIỆU
*Sinh tự động bởi `python -m src.etl.clean` lúc 2026-10-27 09:15. Phương pháp: `QUY_TRINH_DU_AN/GIAI_DOAN_B_KY_THUAT_DU_LIEU_ETL/B04_LAM_SACH_DU_LIEU.md`.*

* **Nguồn:** `s3://raw/academic/ingest_date=2026-10-11/batch_id=20261011T085849Z_7df267/academic_survival_longitudinal.csv`
* **batch_id:** `20261011T085849Z_7df267`
* **MD5:** `94f87baf205fb7f1446639749a2dd852`
* **Output:** `data/processed/clean_semesters.parquet` và `s3://processed/academic/batch_id=20261011T085849Z_7df267/clean_semesters.parquet`
* **Hash nội dung:** `50cf52555b47593d`

## Các thao tác

| Thao tác | Số dòng |
|---|---:|
| Khử trùng lặp (Student_ID, Semester) | 0 |
| Chuẩn hóa Gender (đổi cách ghi) | 4,648 |
| Attendance > 100 → clip về 100 | 164 |
| Attendance < 0 (mã lỗi -2) → thiếu, điền bằng kỳ trước | 60 |
| Attendance vẫn thiếu (lỗi ở kỳ 1, điền ở B10) | 25 |
| Điền Family_Income bằng kỳ trước (ffill, không bfill) | 2,574 |
| Family_Income vẫn thiếu (chưa khai báo đến kỳ đó, cờ Income_Missing, điền ở B10) | 1,030 |
| Điền LMS_Logins bằng kỳ trước (ffill) | 658 |
| LMS_Logins vẫn thiếu (không có kỳ trước, điền ở B10) | 209 |

## Kiểm tra sau làm sạch

| Kiểm tra | Kết quả | Chi tiết |
|---|:---:|---|
| Số dòng không đổi | ✅ | 79,239 / 79,239 |
| Attendance trong [0, 100] (bỏ qua ô thiếu) | ✅ | min 58.7, max 100.0, thiếu 25 |
| Gender còn 3 nhóm | ✅ | Female, Male, Other/Unknown |
| Cột tĩnh không đổi trong cùng sinh viên | ✅ | 0 vi phạm |
| Income_Missing chỉ dựa vào các kỳ đã qua (không tăng lại theo kỳ) | ✅ | 1030 dòng chưa khai báo; 199 sinh viên không khai báo ở kỳ nào |
| Không còn trùng khóa | ✅ |  |
| Đủ 24 cột | ✅ | 24 cột |
