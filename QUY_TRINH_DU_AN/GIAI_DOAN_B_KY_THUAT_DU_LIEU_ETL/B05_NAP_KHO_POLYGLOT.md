# BƯỚC 5. NẠP DỮ LIỆU VÀO KHO POLYGLOT (LOAD)
**Giai đoạn B – Kỹ thuật dữ liệu (ETL)** · [← Bước 4](./B04_LAM_SACH_DU_LIEU.md) · [Giai đoạn C →](../GIAI_DOAN_C_PHAN_TICH_KHAI_PHA/README.md)

---

## 1. Nhiệm vụ
Tách dữ liệu sạch thành **phần tĩnh** (PostgreSQL) và **phần biến động theo kỳ** (MongoDB) như thiết kế ở [`BAO_CAO_CSDL_GIUA_KY.md`](../../BAO_CAO_CSDL_GIUA_KY.md); nạp nhiều lần không bị nhân đôi dữ liệu.

---

## 2. Cơ sở lý thuyết

### 2.1. Polyglot Persistence (Lecture 3, slide 41 – ví dụ Spotify)
* **Ý tưởng:** không có CSDL nào tốt cho mọi việc. Mỗi loại dữ liệu nên được lưu trong loại CSDL phù hợp nhất với nó.
* **Spotify:** PostgreSQL cho tài khoản/thanh toán; Cassandra cho lịch sử nghe; Redis cho cache; Voyager (vector) cho gợi ý.
* **Dự án:** PostgreSQL cho hồ sơ tĩnh và kết quả dự đoán; MongoDB cho nhật ký học kỳ; MinIO cho dữ liệu thô.
* **4 yếu tố chọn CSDL (slide 40)** áp dụng vào dự án:
  * **Workload:** vừa giao dịch (hồ sơ) vừa phân tích (ML).
  * **Data shape:** bảng cố định + bản ghi theo kỳ có thể thêm trường.
  * **Performance:** truy vấn theo `student_id` nhanh.
  * **Operational burden:** cả hai chạy trong `docker-compose`.

### 2.2. Mô hình quan hệ & chuẩn hóa (PostgreSQL)
* Dữ liệu tổ chức thành **bảng (quan hệ)**; mỗi bảng có **khóa chính (PK)**; quan hệ giữa các bảng thể hiện qua **khóa ngoại (FK)**; truy vấn kết hợp bằng **JOIN**.
* **Chuẩn hóa** (normalization) nhằm loại bỏ dư thừa và bất thường khi cập nhật:
  * **1NF:** mỗi ô chứa giá trị nguyên tử (không phải danh sách).
  * **2NF:** đạt 1NF và mọi thuộc tính không khóa phụ thuộc **toàn bộ** khóa chính.
  * **3NF:** đạt 2NF và không có **phụ thuộc bắc cầu** (thuộc tính không khóa phụ thuộc vào thuộc tính không khóa khác).
* **Áp dụng:** file CSV gốc lặp lại `Age`, `Gender`, `Family_Income`… ở **mọi dòng** của cùng sinh viên, tức là dư thừa (vi phạm 2NF vì các cột này chỉ phụ thuộc `Student_ID`, không phụ thuộc cả khóa `(Student_ID, Semester)`). Tách thành bảng `students` (khóa `student_id`) sẽ loại bỏ dư thừa này.

### 2.3. Tính chất ACID
| Tính chất | Ý nghĩa | Lợi ích cho dự án |
|---|---|---|
| **Atomicity** | Giao dịch thực hiện trọn vẹn hoặc không gì cả | Nạp một lô thất bại giữa chừng thì rollback, không để dữ liệu dở dang |
| **Consistency** | Luôn thỏa mọi ràng buộc (PK, FK, CHECK) | Không có `financial_profiles` trỏ tới sinh viên không tồn tại |
| **Isolation** | Các giao dịch đồng thời không ảnh hưởng nhau | Dashboard đọc trong lúc pipeline ghi vẫn thấy dữ liệu nhất quán |
| **Durability** | Đã commit thì không mất khi sự cố | Kết quả dự đoán được lưu bền vững |

### 2.4. Mô hình tài liệu (MongoDB)
* Dữ liệu lưu dưới dạng **document** JSON/BSON trong **collection**; **không cần schema cố định** (schema-less / schema-flexible).
* **Embedding và Referencing:**
  * **Embed** (nhúng): đặt dữ liệu liên quan trong cùng document, đọc một lần là đủ. Dự án nhúng các object `academic_performance`, `engagement`, `socio_economic`, `outcome` trong document của từng kỳ.
  * **Reference** (tham chiếu): lưu khóa trỏ sang nơi khác. Document học kỳ tham chiếu sinh viên qua `student_id` (hồ sơ nằm ở PostgreSQL).
* **Thiết kế 1 document = 1 kỳ** (thay vì 1 document = 1 sinh viên chứa mảng 8 kỳ): ghi thêm một kỳ mới chỉ là chèn một document; không làm document phình to; dễ truy vấn theo kỳ.

### 2.5. Index
* **Index** là cấu trúc dữ liệu phụ (thường là B-Tree) giúp tìm kiếm trong O(log n) thay vì quét toàn bộ O(n).
* **Unique compound index** `(student_id, semester)` vừa tăng tốc truy vấn quỹ đạo của một sinh viên, vừa **cấm trùng** một kỳ của một sinh viên.

### 2.6. Upsert và tính lũy đẳng
* **Upsert** = *update* nếu đã có, *insert* nếu chưa có.
* PostgreSQL: `INSERT … ON CONFLICT (student_id) DO UPDATE`. MongoDB: `ReplaceOne(filter, doc, upsert=True)`.
* Nhờ upsert, pipeline chạy lại bao nhiêu lần thì số dòng vẫn đúng (**idempotent**).

### 2.7. OLTP và OLAP
* **OLTP** (giao dịch trực tuyến): nhiều thao tác nhỏ đọc/ghi từng bản ghi, như cập nhật hồ sơ sinh viên.
* **OLAP** (phân tích trực tuyến): truy vấn tổng hợp trên nhiều bản ghi, như tỷ lệ bỏ học theo kỳ.
* Dự án ở quy mô nhỏ nên dùng chung PostgreSQL cho cả hai; khi lớn hơn có thể tách thêm một kho dạng cột (Lecture 3: BigQuery, Redshift).

---

## 3. Input
`clean_semesters.parquet` (79.239 × 24).

---

## 4. Biến đổi
1. **Tạo schema** bằng `sql/schema.sql`:
   ```sql
   CREATE TABLE IF NOT EXISTS students (
     student_id       VARCHAR(15) PRIMARY KEY,
     age              INT,
     gender           VARCHAR(20),
     first_generation BOOLEAN,
     household_size   INT,
     housing_status   VARCHAR(20),
     family_income    NUMERIC(12,2),      -- NULL cho 199 sinh viên
     income_missing   BOOLEAN
   );
   CREATE TABLE IF NOT EXISTS financial_profiles (
     profile_id   SERIAL PRIMARY KEY,
     student_id   VARCHAR(15) UNIQUE REFERENCES students(student_id),
     scholarship  BOOLEAN,
     tuition_base NUMERIC(10,2)
   );
   CREATE TABLE IF NOT EXISTS predictions (
     run_id VARCHAR(40), run_date TIMESTAMP, model_version VARCHAR(20),
     student_id VARCHAR(15) REFERENCES students(student_id), semester INT,
     risk_score NUMERIC(5,4), risk_level VARCHAR(12),
     top_reason_1 TEXT, top_reason_2 TEXT, top_reason_3 TEXT,
     PRIMARY KEY (run_id, student_id)
   );
   ```
2. **`students`:** lấy dòng đầu tiên của mỗi sinh viên, gồm 7 cột tĩnh + `income_missing` → **20.000 dòng**.
3. **`financial_profiles`:** `scholarship`, `tuition_base` theo sinh viên → **20.000 dòng**.
4. **`academic_semesters`:** mỗi dòng → 1 document → **79.239 document**:
   ```json
   {
     "student_id": "STU_00001", "semester": 1,
     "academic_performance": { "sem_gpa": 2.85, "failed_courses": 0, "course_load": 15 },
     "engagement": { "attendance": 85.8, "lms_logins": 67, "advising_visits": 0, "lms_missing": 0 },
     "socio_economic": { "work_hours": 18.4, "financial_stress": 1.7, "emergency_expense": 0 },
     "outcome": { "target_dropout_next_sem": 0, "end_of_semester_status": "Enrolled", "censored": 0 }
   }
   ```
5. **Tạo unique index** MongoDB trên `(student_id, semester)`.
6. **Nạp kiểu upsert:** PostgreSQL `ON CONFLICT DO UPDATE` trong một transaction; MongoDB `bulk_write` với `ReplaceOne(..., upsert=True)`.
7. **Đối soát:** đếm số dòng/document; mọi `student_id` trong MongoDB đều tồn tại trong `students`.
8. Viết hàm **`load_analytic_table()`**: đọc 2 CSDL, "làm phẳng" document và join theo `student_id` → bảng 79.239 dòng cho các bước sau.

---

## 5. Output
* PostgreSQL: `students` (20.000), `financial_profiles` (20.000), `predictions` (rỗng), `ingestion_log`.
* MongoDB: `academic_semesters` (79.239 document).
* Hàm `load_analytic_table()` trong `src/etl/load.py`.

## 6. Công cụ / File thực hiện
`src/etl/load.py`, `sql/schema.sql` (`sqlalchemy`, `psycopg2`, `pymongo`).

## 7. Tiêu chí hoàn thành
- [ ] Số lượng khớp 20.000 / 20.000 / 79.239.
- [ ] Chạy lại lần 2 số lượng không đổi.
- [ ] `load_analytic_table()` trả về dữ liệu giống hệt `clean_semesters.parquet`.

---

## 8. Câu hỏi bảo vệ thường gặp
**Hỏi:** Dữ liệu nhỏ như vậy, chỉ cần PostgreSQL là đủ, sao phải thêm MongoDB?  
**Đáp:** Đúng là PostgreSQL đủ về hiệu năng. Nhóm tách MongoDB vì dữ liệu học kỳ đến từ LMS và khảo sát, là những nguồn **thường xuyên thêm trường mới**. Document DB cho phép nạp trường mới mà không cần migrate schema. Chi phí vận hành thêm thấp vì chạy chung `docker-compose`.

**Hỏi:** Vì sao `emergency_expense` nằm ở MongoDB chứ không ở `financial_profiles`?  
**Đáp:** Vì nó **thay đổi theo kỳ** (5.083 sinh viên có giá trị khác nhau giữa các kỳ). Bảng `financial_profiles` chỉ chứa thuộc tính cố định; đặt dữ liệu theo kỳ ở đó sẽ phá vỡ khóa và chuẩn hóa.
