# BƯỚC 4. LÀM SẠCH DỮ LIỆU (TRANSFORM – CLEANING)
**Giai đoạn B – Kỹ thuật dữ liệu (ETL)** · [← Bước 3](./B03_KIEM_TRA_CHAT_LUONG_DU_LIEU.md) · [Bước 5 →](./B05_NAP_KHO_POLYGLOT.md)

---

## 1. Nhiệm vụ
Biến dữ liệu thô thành dữ liệu sạch, đúng kiểu, đúng miền giá trị, **không làm mất dòng** và **không dùng thông tin tương lai** (trừ thuộc tính tĩnh).

---

## 2. Cơ sở lý thuyết

### 2.1. Các chiến lược xử lý giá trị thiếu

| Chiến lược | Mô tả | Ưu / Nhược |
|---|---|---|
| Xóa dòng (listwise deletion) | Bỏ dòng có giá trị thiếu | Đơn giản / mất dữ liệu, gây lệch nếu không phải MCAR |
| Điền hằng số thống kê | Mean, median, mode | Nhanh / làm giảm phương sai; median bền với ngoại lai hơn mean |
| Điền theo nhóm | Median theo nhóm liên quan (ví dụ `Household_Size`) | Tận dụng cấu trúc MAR |
| **LOCF / Forward-fill** | *Last Observation Carried Forward*: lấy giá trị kỳ trước của cùng cá thể | Rất hợp với dữ liệu theo chiều dọc, **không dùng tương lai** |
| Backward-fill | Lấy giá trị kỳ sau | Dù thuộc tính tĩnh, *việc biết* giá trị vẫn phụ thuộc thời gian → dễ rò rỉ (xem 2.2); dự án **không dùng** |
| Dựa trên mô hình | KNN Imputer, Iterative Imputer (MICE) | Chính xác hơn / phức tạp, chậm |
| **Missing indicator** | Thêm cột cờ 0/1 "giá trị này từng bị thiếu" | Giữ thông tin khi thiếu không ngẫu nhiên (MNAR) |

### 2.2. Thuộc tính tĩnh và thuộc tính biến động theo thời gian
* **Tĩnh (time-invariant):** không đổi qua các kỳ (`Age`, `Gender`, `Family_Income`, `Scholarship`, `Tuition_Base`…). Giá trị không đổi, nhưng **thời điểm hệ thống biết giá trị đó** thì có: thu nhập chưa khai báo ở kỳ 1 mà kỳ 3 mới khai báo thì tại kỳ 1 hệ thống *chưa biết*. Vì vậy cũng chỉ được ffill.
  * *Bài học của dự án:* bản đầu dùng ffill + bfill cho `Family_Income` và đặt cờ `Income_Missing` = "không khai báo ở kỳ nào". Cờ đó **nhìn trước tương lai**: sinh viên bỏ học sau kỳ 1 chỉ có 1 kỳ để khai báo, nên 84,7% dòng mang cờ là bỏ học (so với 10,7% khi tính đúng thời điểm). SHAP ở B13 phát hiện cờ này có hệ số 3,5 (gấp ~4 lần biến mạnh nhất) → đã sửa thành chỉ ffill.
* **Biến động (time-varying):** thay đổi theo kỳ (`LMS_Logins`, `Sem_GPA`…). Chỉ được lấy từ **quá khứ** (ffill). Dùng bfill sẽ "nhìn trước tương lai", gây **rò rỉ thời gian (temporal leakage)**.

### 2.3. Clipping và Winsorization
* **Clipping:** chặn giá trị về một khoảng **cố định theo nghiệp vụ**, ví dụ `Attendance` > 100 (đếm dư) về 100. Chỉ dùng khi giá trị lỗi vẫn **gần** giá trị thật. Nếu giá trị lỗi là một **mã lỗi** (như `Attendance = −2`), clip sẽ tạo ra số đo giả (0%), nên phải coi là **thiếu** và xử lý như dữ liệu thiếu.
* **Winsorization:** chặn giá trị về **phân vị** của dữ liệu (ví dụ P1 – P99). Dùng để giảm ảnh hưởng của giá trị cực đoan **hợp lệ** lên mô hình nhạy cảm (hồi quy tuyến tính). Vì phân vị được "học" từ dữ liệu, winsorization phải **fit trên Train** (thực hiện ở B10, không làm ở đây).

### 2.4. Chuẩn hóa dữ liệu phân loại
Chuẩn hóa chuỗi theo thứ tự `strip()` (bỏ khoảng trắng) → `lower()` (chữ thường) → **bảng ánh xạ (mapping)** về tập giá trị chuẩn. Giá trị nằm ngoài bảng ánh xạ được đưa về nhóm "Other/Unknown" và ghi log để xem xét.

### 2.5. Biến đổi xác định (deterministic) và biến đổi "học từ dữ liệu"
| Loại | Ví dụ | Làm ở đâu |
|---|---|---|
| **Xác định** (quy tắc cố định, không phụ thuộc phân phối dữ liệu) | Clip [0, 100], map Gender, ffill theo sinh viên | **B4** (trước khi chia tập) |
| **Học từ dữ liệu** (cần tính thống kê) | Median toàn cục, mean/std để scale, phân vị winsorize | **B10** (fit trên Train) |

Đây là cách tránh **rò rỉ từ tập Test**: nếu tính median trên toàn bộ dữ liệu rồi mới chia, thông tin của Test đã "lọt" vào Train.

### 2.6. Định dạng Parquet (liên hệ Lecture 3 – CSDL dạng cột)
* Parquet là định dạng **lưu theo cột (columnar)**, được nêu trong bài giảng như ví dụ của Column Database.
* Ưu điểm so với CSV: **giữ kiểu dữ liệu**, **nén tốt** (các giá trị cùng cột giống nhau), **đọc nhanh** khi chỉ cần một vài cột.

---

## 3. Input
File thô (79.239 × 22) + bảng quyết định ở [B3](./B03_KIEM_TRA_CHAT_LUONG_DU_LIEU.md).

---

## 4. Biến đổi (theo đúng thứ tự)
1. **Khử trùng lặp:** `drop_duplicates(subset=['Student_ID','Semester'], keep='last')`.
2. **Ép kiểu:** `Student_ID` → string; `Age`, `Semester`, `Course_Load`, `LMS_Logins`, `Advising_Visits`, `Failed_Courses` → số nguyên (nullable `Int64` với `LMS_Logins`); cột nhị phân → 0/1; còn lại → float.
3. **Sắp xếp** theo `Student_ID`, `Semester` (bắt buộc trước các thao tác theo nhóm).
4. **Chuẩn hóa `Gender`:** `strip().lower()` rồi map:
   `female, f → Female` · `male, m → Male` · `other, prefer not to say → Other/Unknown`.
5. **Chuẩn hóa `Housing_Status`:** `strip()`, kiểm tra thuộc {On-Campus, Off-Campus, With Parents}.
6. **Sửa `Attendance`:** Giá trị âm luôn đúng bằng **−2** (mã lỗi): kỳ trước / kỳ sau của chính sinh viên đó quanh 86%, và không có ai thực sự chuyên cần 0 – 10% → coi là **thiếu**, điền bằng kỳ trước (ffill), không clip về 0 (clip sẽ tạo cú sụt giả ~−86 điểm). Giá trị > 100 (101, 105) là đếm dư → clip về 100. (164 dòng clip; 85 dòng âm: 60 điền được bằng kỳ trước, 25 dòng ở kỳ 1 còn thiếu → B10.)
7. **Điền `Family_Income`:** `groupby('Student_ID').ffill()` (**không bfill**, xem 2.2). `Income_Missing = 1` nghĩa là "chưa khai báo tính đến kỳ này" (1.030 dòng; 199 sinh viên không khai báo ở kỳ nào).
8. **Điền `LMS_Logins`:** `groupby('Student_ID').ffill()` (**không bfill**). Gán `LMS_Missing = 1` cho các dòng ban đầu bị thiếu.
9. **Giữ nguyên** `Financial_Stress`, `Emergency_Expense`, `Work_Hours`.
10. **Kiểm tra sau làm sạch:**
    * Số dòng vẫn = 79.239.
    * `Attendance` ∈ [0, 100]; `Gender` chỉ còn 3 giá trị.
    * Các cột tĩnh không đổi trong cùng một sinh viên.

---

## 5. Output
* `data/processed/clean_semesters.parquet` (79.239 × 24 = 22 cột gốc + `Income_Missing` + `LMS_Missing`, ~1 MB so với 7,4 MB của CSV) và bản sao `s3://processed/academic/batch_id=<batch_id>/clean_semesters.parquet`.
* [`reports/cleaning_log.md`](../../reports/cleaning_log.md): số dòng bị ảnh hưởng ở từng thao tác + kết quả kiểm tra sau làm sạch + hash nội dung.

**Kết quả thực tế** (lô `20261011T085849Z_7df267`):

| Thao tác | Số dòng |
|---|---:|
| Khử trùng lặp | 0 |
| Chuẩn hóa `Gender` (đổi cách ghi) | 4.648 |
| `Attendance` > 100 → clip về 100 | 164 |
| `Attendance` < 0 (mã lỗi −2) → thiếu, điền bằng kỳ trước | 60 |
| `Attendance` vẫn thiếu (lỗi rơi vào kỳ 1) | 25 |
| Điền `Family_Income` bằng kỳ trước (ffill) | 2.574 |
| `Family_Income` vẫn thiếu (chưa khai báo đến kỳ đó) → `Income_Missing = 1` | 1.030 |
| Điền `LMS_Logins` bằng kỳ trước | 658 |
| `LMS_Logins` vẫn thiếu (không có kỳ trước) | 209 |

## 6. Công cụ / File thực hiện
* `src/etl/clean.py`: chạy `python -m src.etl.clean [--file PATH]`. Dữ liệu phải **qua data contract của B3 trước** (có ERROR thì dừng, không ghi output); kiểm tra sau làm sạch không đạt cũng không ghi output.
* Kiểu dữ liệu được ép theo `src/core/schema.py`: số nguyên → `int64`, số thực → `float64`, `LMS_Logins` → `Int64` (nullable, vì còn thiếu ở kỳ đầu), chuỗi → `string`, cờ → `int8`.
* `tests/test_clean.py`: 10 unit test (map Gender, clip, `Family_Income` chỉ ffill và cờ đúng thời điểm, không mượn dữ liệu của sinh viên khác, LMS chỉ ffill, khử trùng giữ bản cuối, tính xác định…).

## 7. Tiêu chí hoàn thành (đã kiểm tra 2026-10-24)
- [x] Mọi kiểm tra ở mục 4.10 đều đạt: 79.239 dòng; `Attendance` ∈ [0, 100]; `Gender` còn 3 nhóm; 0 vi phạm cột tĩnh; đủ 24 cột.
- [x] Chạy lại hai lần cho kết quả giống hệt nhau: MD5 file Parquet `d9ffd8db51926ede46ad39608bcfa838` cả hai lần; hash nội dung `c0980650c9f4212a` (sau khi sửa cách xử lý `Attendance` ở B7).
- [x] File cố tình làm hỏng → dừng ở data contract, mã thoát 1, không ghi output.

---

## 8. Câu hỏi bảo vệ thường gặp
**Hỏi:** `Family_Income` không đổi qua các kỳ, sao không bfill?  
**Đáp:** Giá trị không đổi, nhưng *việc đã biết* giá trị thì phụ thuộc thời gian. Nhóm từng bfill và đặt cờ "không khai báo ở kỳ nào"; SHAP (B13) cho thấy cờ này có hệ số 3,5 vì nó ngầm chứa thông tin sinh viên còn học bao nhiêu kỳ (84,7% dòng mang cờ là bỏ học, trong khi tính đúng thời điểm chỉ 10,7%). Đây là rò rỉ thời gian, nên nhóm chỉ ffill như `LMS_Logins`.

**Hỏi:** Vì sao không scale dữ liệu ngay ở bước làm sạch?  
**Đáp:** Scale cần mean/std, tức là "học" từ dữ liệu. Nếu làm trước khi chia tập, thông tin của tập Test sẽ rò sang Train. Việc này được làm trong Pipeline ở B10.
