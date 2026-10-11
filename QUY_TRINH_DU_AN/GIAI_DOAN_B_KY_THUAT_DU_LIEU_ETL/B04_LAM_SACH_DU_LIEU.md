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
| Backward-fill | Lấy giá trị kỳ sau | **Chỉ được dùng cho thuộc tính tĩnh**; với thuộc tính biến động là rò rỉ tương lai |
| Dựa trên mô hình | KNN Imputer, Iterative Imputer (MICE) | Chính xác hơn / phức tạp, chậm |
| **Missing indicator** | Thêm cột cờ 0/1 "giá trị này từng bị thiếu" | Giữ thông tin khi thiếu không ngẫu nhiên (MNAR) |

### 2.2. Thuộc tính tĩnh và thuộc tính biến động theo thời gian
* **Tĩnh (time-invariant):** không đổi qua các kỳ (`Age`, `Gender`, `Family_Income`, `Scholarship`, `Tuition_Base`…). Điền từ **bất kỳ kỳ nào** của cùng sinh viên (ffill + bfill) đều hợp lệ, vì giá trị vốn dĩ đã biết từ đầu.
* **Biến động (time-varying):** thay đổi theo kỳ (`LMS_Logins`, `Sem_GPA`…). Chỉ được lấy từ **quá khứ** (ffill). Dùng bfill sẽ "nhìn trước tương lai", gây **rò rỉ thời gian (temporal leakage)**.

### 2.3. Clipping và Winsorization
* **Clipping:** chặn giá trị về một khoảng **cố định theo nghiệp vụ**, ví dụ `Attendance` về [0, 100]. Dùng cho **lỗi dữ liệu**.
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
6. **Sửa `Attendance`:** `clip(0, 100)` (249 dòng bị ảnh hưởng).
7. **Điền `Family_Income`:** `groupby('Student_ID')` → `ffill().bfill()` (hợp lệ vì là thuộc tính tĩnh). Gán `Income_Missing = 1` cho 199 sinh viên vẫn còn trống.
8. **Điền `LMS_Logins`:** `groupby('Student_ID').ffill()` (**không bfill**). Gán `LMS_Missing = 1` cho các dòng ban đầu bị thiếu.
9. **Giữ nguyên** `Financial_Stress`, `Emergency_Expense`, `Work_Hours`.
10. **Kiểm tra sau làm sạch:**
    * Số dòng vẫn = 79.239.
    * `Attendance` ∈ [0, 100]; `Gender` chỉ còn 3 giá trị.
    * Các cột tĩnh không đổi trong cùng một sinh viên.

---

## 5. Output
* `clean_semesters.parquet` (79.239 × 24 = 22 cột gốc + `Income_Missing` + `LMS_Missing`), lưu ở `data/processed/` và MinIO bucket `processed`.
* Log làm sạch: số dòng bị ảnh hưởng ở từng thao tác.

## 6. Công cụ / File thực hiện
`src/clean.py` (`pandas`, `pyarrow`).

## 7. Tiêu chí hoàn thành
- [ ] Mọi kiểm tra ở mục 4.10 đều đạt.
- [ ] Chạy lại hai lần cho kết quả giống hệt nhau (so sánh hash của file Parquet).

---

## 8. Câu hỏi bảo vệ thường gặp
**Hỏi:** Sao `Family_Income` được bfill mà `LMS_Logins` thì không?  
**Đáp:** `Family_Income` không đổi qua các kỳ (đã kiểm tra: 0 sinh viên có hai giá trị khác nhau), nên lấy từ kỳ sau cũng là thông tin đã biết từ trước. `LMS_Logins` thay đổi theo kỳ; bfill sẽ dùng hành vi tương lai để mô tả hiện tại, tức là rò rỉ.

**Hỏi:** Vì sao không scale dữ liệu ngay ở bước làm sạch?  
**Đáp:** Scale cần mean/std, tức là "học" từ dữ liệu. Nếu làm trước khi chia tập, thông tin của tập Test sẽ rò sang Train. Việc này được làm trong Pipeline ở B10.
