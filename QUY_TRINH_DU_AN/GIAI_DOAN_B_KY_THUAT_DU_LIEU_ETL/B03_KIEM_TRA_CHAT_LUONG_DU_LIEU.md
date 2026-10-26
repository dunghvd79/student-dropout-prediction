# BƯỚC 3. KIỂM TRA CHẤT LƯỢNG DỮ LIỆU (DATA PROFILING & VALIDATION)
**Giai đoạn B – Kỹ thuật dữ liệu (ETL)** · [← Bước 2](./B02_THU_THAP_NAP_DU_LIEU_THO.md) · [Bước 4 →](./B04_LAM_SACH_DU_LIEU.md)

---

## 1. Nhiệm vụ
**Đo lường mọi vấn đề chất lượng trước khi sửa**, rồi ra quyết định xử lý có căn cứ cho từng vấn đề. Nguyên tắc: *"Đo trước, sửa sau"*. Không sửa mù quáng.

---

## 2. Cơ sở lý thuyết

### 2.1. Sáu chiều chất lượng dữ liệu (Data Quality Dimensions)

| Chiều | Câu hỏi kiểm tra | Ví dụ trong dataset |
|---|---|---|
| **Completeness** (Đầy đủ) | Có bị thiếu giá trị không? | `Family_Income` thiếu 4,5% |
| **Validity** (Hợp lệ) | Giá trị có nằm trong miền cho phép? | `Attendance` = −2 hoặc 105 |
| **Consistency** (Nhất quán) | Cùng một ý nghĩa có ghi giống nhau không? | `Gender`: "F", "female", "Female" |
| **Uniqueness** (Duy nhất) | Có bản ghi trùng không? | Khóa `(Student_ID, Semester)` |
| **Accuracy** (Chính xác) | Giá trị có phản ánh đúng thực tế? | Kiểm tra logic giữa nhãn và trạng thái |
| **Timeliness** (Kịp thời) | Dữ liệu có cập nhật đúng hạn? | Theo dõi `ingested_at` mỗi lô |

### 2.2. Cơ chế dữ liệu thiếu (Rubin, 1976)
Cách điền khuyết đúng phụ thuộc vào **vì sao** dữ liệu bị thiếu:

| Cơ chế | Định nghĩa | Hệ quả |
|---|---|---|
| **MCAR** – Missing Completely At Random | Thiếu hoàn toàn ngẫu nhiên, không liên quan tới bất kỳ biến nào | Xóa hoặc điền đơn giản không gây lệch |
| **MAR** – Missing At Random | Thiếu phụ thuộc vào **biến quan sát được khác** (ví dụ theo `Household_Size`) | Điền theo nhóm / theo mô hình dùng biến liên quan |
| **MNAR** – Missing Not At Random | Thiếu phụ thuộc vào **chính giá trị bị thiếu** (ví dụ thu nhập thấp nên ngại khai) | Bản thân việc thiếu là thông tin, nên thêm **cờ thiếu (missing indicator)** |

`Family_Income` có thể là MNAR (sinh viên ngại khai báo), vì vậy nhóm thêm cờ `Income_Missing` để mô hình tự học xem việc "không khai báo" có liên quan đến bỏ học hay không.

### 2.3. Phát hiện ngoại lai (Outliers)
* **Quy tắc IQR (Tukey):** ngoại lai nếu $x < Q_1 - 1{,}5 \cdot IQR$ hoặc $x > Q_3 + 1{,}5 \cdot IQR$, với $IQR = Q_3 - Q_1$.
* **Z-score:** ngoại lai nếu $|z| = \left|\frac{x-\mu}{\sigma}\right| > 3$. Chỉ phù hợp với phân phối gần chuẩn.
* **Kiểm tra miền nghiệp vụ:** giá trị vi phạm quy tắc logic (tỷ lệ % ngoài [0, 100]).

**Phân biệt hai loại ngoại lai:**

| Loại | Ví dụ | Cách xử lý |
|---|---|---|
| **Lỗi dữ liệu** (không thể xảy ra) | `Attendance` = 105% | Sửa / chặn (clip) |
| **Giá trị cực đoan hợp lệ** (hiếm nhưng có thật) | `Family_Income` = 488.000; `Financial_Stress` = 18,6 | **Giữ lại**; biến đổi log / winsorize nếu mô hình nhạy cảm |

Xóa nhầm giá trị cực đoan hợp lệ sẽ **làm mất tín hiệu**. Ví dụ: tỷ lệ bỏ học ở nhóm `Financial_Stress` ≥ 10 là 50,2%, so với 5,3% ở mức 1.

### 2.4. Rò rỉ nhãn (Target Leakage)
Rò rỉ xảy ra khi một đặc trưng **chứa thông tin về nhãn mà tại thời điểm dự đoán chưa thể biết**. Mô hình sẽ đạt điểm "hoàn hảo" khi kiểm thử nhưng vô dụng khi triển khai.
* Trong dataset: `Target = 1` **khi và chỉ khi** `End_of_Semester_Status = Dropped_Out`. Đây là rò rỉ tuyệt đối.

### 2.5. Dữ liệu bị cắt phải (Right-censoring)
* Thuật ngữ của **Phân tích sống sót (Survival Analysis)**: ta biết sinh viên **còn theo học đến kỳ *t***, nhưng **không quan sát được** điều xảy ra sau đó (dữ liệu kết thúc).
* Dòng cuối của sinh viên bị cắt có nhãn 0, nhưng nhãn này **chưa được xác nhận**. Dùng chúng để huấn luyện như "chắc chắn ở lại" sẽ làm mô hình **đánh giá thấp rủi ro**.

### 2.6. Data Contract
Tập quy tắc kiểm tra được **viết thành code** (số cột, kiểu, miền giá trị, tỷ lệ thiếu tối đa) và chạy tự động mỗi lần nạp dữ liệu mới. Lô vi phạm sẽ bị chặn trước khi làm hỏng các bước sau.

---

## 3. Input
File thô từ MinIO (79.239 × 22).

---

## 4. Biến đổi (các phép kiểm tra)
1. Đếm giá trị thiếu theo cột.
2. Kiểm tra miền giá trị hợp lệ (min/max, tập giá trị cho phép).
3. Đếm số cách ghi khác nhau của cột phân loại.
4. Kiểm tra trùng khóa `(Student_ID, Semester)`.
5. Kiểm tra tính liên tục của học kỳ cho mỗi sinh viên (1, 2, …, n).
6. Kiểm tra cột nào cố định theo sinh viên, cột nào thay đổi theo kỳ.
7. Kiểm tra quan hệ logic giữa nhãn và các cột trạng thái.

### Kết quả kiểm tra thực tế & quyết định xử lý

| # | Vấn đề | Số liệu thực tế | Quyết định xử lý (bước) |
|:---:|---|---|---|
| 1 | `Family_Income` thiếu | 3.604 dòng (4,5%); cột **không đổi theo kỳ**; 3.387 dòng lấy lại được từ kỳ khác của cùng sinh viên; 199 sinh viên thiếu ở mọi kỳ | Điền theo sinh viên (B4); phần còn lại + cờ `Income_Missing`, điền trung vị trong Pipeline (B10) |
| 2 | `LMS_Logins` thiếu | 867 dòng (1,1%), 206 dòng ở kỳ 1 | Forward-fill theo sinh viên (B4); phần còn lại điền trung vị (B10) |
| 3 | `Attendance` ngoài [0, 100] | 85 dòng < 0 (**đều bằng −2**, kỳ trước / sau quanh 86%), 164 dòng > 100 (101 hoặc 105) | Giá trị âm → thiếu, điền bằng kỳ trước; > 100 → clip về 100 (B4). *Ban đầu định clip cả hai về [0, 100]; sửa ở B7 khi phát hiện −2 là mã lỗi.* |
| 4 | `Financial_Stress` vượt thang 1 – 5 | Trung vị 2,1; P99 = 9,0; max 18,6; 7.348 dòng > 5. Tỷ lệ bỏ học tăng đều theo chỉ số | **Giữ nguyên**; winsorize P99 / `log1p` cho mô hình tuyến tính (B10) |
| 5 | `Family_Income` lệch phải | 3.000 → 488.000 | `log1p` cho mô hình tuyến tính (B10) |
| 6 | `Gender` không nhất quán | 8 cách ghi | Map về 3 nhóm (B4) |
| 7 | `Housing_Status` | 3 giá trị hợp lệ: On-Campus, Off-Campus, With Parents | Giữ nguyên, One-Hot (B10) |
| 8 | Trùng lặp | 0 dòng trùng | Vẫn chạy `drop_duplicates` để phòng ngừa (B4) |
| 9 | Tính liên tục học kỳ | 100% liên tục từ kỳ 1 | Không cần xử lý |
| 10 | Rò rỉ nhãn | `Target = 1` ⇔ `Dropped_Out` | Loại `End_of_Semester_Status`, `Censored` khỏi đặc trưng (B9) |
| 11 | Nhãn bị cắt | 11.115 dòng `Censored = 1` | Loại khỏi Train/Test, dùng làm tập chấm điểm (B9, B14) |

---

## 5. Output
* [`reports/data_quality_report.md`](../../reports/data_quality_report.md): tóm tắt 9 kiểm tra, bảng quyết định xử lý, bảng chi tiết và 4 biểu đồ (`reports/figures/dq_*.png`).
* Data contract tự động trong `src/etl/validate.py`, mỗi kiểm tra trả về một trong ba mức:
  * **OK:** sạch.
  * **WARN:** vấn đề đã biết, đã có cách xử lý ở B4 / B9 / B10; không chặn pipeline.
  * **ERROR:** vi phạm contract, chặn pipeline (mã thoát 1). Gồm: thiếu > 10% ở một cột, **thiếu ở cột không được phép thiếu** (chỉ `Family_Income` và `LMS_Logins` được phép, theo `NULLABLE_COLUMNS`), > 1% giá trị ngoài miền, giá trị phân loại lạ, học kỳ đứt quãng, cột tĩnh bị đổi trong cùng sinh viên, logic nhãn sai.
  * Dòng trùng khóa `(Student_ID, Semester)` chỉ là **WARN** (B4 khử trùng, giữ bản cuối); các kiểm tra cấu trúc còn lại chạy trên dữ liệu đã khử trùng để lô nạp lại không bị báo nhầm ERROR.

## 6. Công cụ / File thực hiện
* `src/etl/validate.py`: chạy `python -m src.etl.validate` (mặc định đọc lô `SUCCESS` mới nhất trong MinIO), hoặc `--file PATH` để kiểm tra một file trên máy, `--no-report` để chỉ in kết quả.
* `src/core/schema.py`: miền giá trị (`RANGES`), cột tĩnh (`STATIC_COLUMNS`), bảng ánh xạ `GENDER_MAP` (B4 dùng lại), tập giá trị hợp lệ của `Housing_Status` và `End_of_Semester_Status`.
* `tests/test_validate.py`: 13 unit test.

## 7. Tiêu chí hoàn thành (đã kiểm tra 2026-10-24)
- [x] Mọi cột đều có kết luận "sạch" hoặc "có vấn đề + cách xử lý" (xem báo cáo). Lô `20261011T085849Z_7df267`: **ĐẠT** (4 OK, 5 WARN, 0 ERROR).
- [x] File cố tình làm hỏng (Gender lạ, `Tuition_Base` đổi giữa các kỳ, học kỳ đứt quãng, `Work_Hours` thiếu 11%) → 5 ERROR, mã thoát 1.
- [x] Số liệu khớp phép đo trước: thiếu 3.604 / 867; `Attendance` 249 dòng; `Gender` 8 cách ghi; `Financial_Stress` > 5: 7.348 dòng; 0 trùng khóa; 11.115 dòng `Censored = 1`; tập có nhãn 68.124 dòng (10,2%).

> **Ghi chú:** tỷ lệ bỏ học theo `Financial_Stress` được tính trên **tập có nhãn** (`Censored = 0`): 5,3% ở mức 1 → 50,2% ở mức ≥ 10. Số cũ (4,6% → 47%) tính trên toàn bộ dữ liệu, gồm cả các dòng có nhãn chưa xác nhận, nên đã được thay.

---

## 8. Câu hỏi bảo vệ thường gặp
**Hỏi:** Vì sao không xóa luôn các dòng thiếu `Family_Income`?  
**Đáp:** Sẽ mất 4,5% dữ liệu và có thể gây lệch nếu việc thiếu không ngẫu nhiên (MNAR). Hơn nữa, 94% số dòng thiếu lấy lại được từ kỳ khác của chính sinh viên đó.

**Hỏi:** `Financial_Stress` lên tới 18,6 trong khi mô tả là thang 1 – 5, vì sao không chặn về 5?  
**Đáp:** Tỷ lệ bỏ học tăng đều theo chỉ số này (5,3% → 50,2% trên tập có nhãn), nên giá trị cao là tín hiệu thật. Chặn về 5 sẽ xóa mất sự khác biệt giữa nhóm rủi ro vừa và rủi ro rất cao.
