# BÁO CÁO BÀI TẬP GIỮA KỲ: THIẾT KẾ CƠ SỞ DỮ LIỆU & QUY MÔ DỮ LIỆU CHO HỌC MÁY
**Học phần:** Tích hợp và Phân tích Dữ liệu Lớn  
**Giảng viên hướng dẫn:** Thầy Phạm Kim Thành – Phenikaa University  
**Tài liệu tham khảo chính:** Bài giảng *Lecture 3: Các loại Cơ sở dữ liệu*  
**Đề tài:** Dự đoán nguy cơ bỏ học của sinh viên đại học dựa trên dữ liệu theo chiều dọc (Longitudinal Academic Data)

---

## CÂU 1: XÁC ĐỊNH CƠ SỞ DỮ LIỆU PHÙ HỢP CHO BÀI GIỮA KỲ VÀ LÝ DO

### 1.1. Phân tích bối cảnh bài toán theo bài giảng Lecture 3
Theo bài giảng *Lecture 3*, khi lựa chọn cơ sở dữ liệu (CSDL) cho một hệ thống lớn, cần xem xét **4 yếu tố cốt lõi** (Slide 40):
1. **Khối lượng công việc (Workload):** Hệ thống vừa cần đảm bảo tính toàn vẹn giao dịch quản lý hồ sơ sinh viên (Transactional - OLTP), vừa cần xử lý dữ liệu động học kỳ để trích xuất đặc trưng phục vụ phân tích và học máy (Analytical - OLAP).
2. **Hình dạng dữ liệu (Data shape):** Dữ liệu của đề tài bao gồm cả **dữ liệu có cấu trúc cố định** (thông tin cá nhân, hồ sơ nhân khẩu học) và **dữ liệu bán cấu trúc / chuỗi thời gian biến động theo từng kỳ** (nhật ký chuyên cần, tương tác LMS, áp lực tài chính thay đổi theo thời gian).
3. **Hiệu suất (Performance):** Cần truy vấn nhanh hồ sơ sinh viên và tối ưu hóa việc trích xuất hàng loạt bản ghi theo chuỗi học kỳ.
4. **Gánh nặng vận hành (Operational burden):** Đảm bảo tính mở rộng linh hoạt khi bổ sung thêm các trường dữ liệu hành vi mới mà không phải thiết kế lại toàn bộ bảng.

### 1.2. Đề xuất kiến trúc: Đa lưu trữ (Polyglot Persistence)
Học tập từ mô hình thực tế của các hệ sinh thái lớn như **Spotify** (Slide 41 trong bài giảng), nhóm lựa chọn giải pháp kết hợp **02 loại cơ sở dữ liệu** chính:

```
                  NGUỒN DỮ LIỆU SINH VIÊN
                             │
            ┌────────────────┴────────────────┐
            ▼                                 ▼
┌─────────────────────────┐       ┌─────────────────────────┐
│ CƠ SỞ DỮ LIỆU QUAN HỆ   │       │ CƠ SỞ DỮ LIỆU TÀI LIỆU  │
│ (Relational Database)   │       │ (Document Database)     │
│ Đại diện: PostgreSQL    │       │ Đại diện: MongoDB       │
├─────────────────────────┤       ├─────────────────────────┤
│ • Lưu thông tin tĩnh    │       │ • Lưu nhật ký động theo │
│ • Quản lý hồ sơ định    │       │   từng học kỳ           │
│   danh sinh viên        │       │ • Dữ liệu LMS, chuyên   │
│ • Ràng buộc toàn vẹn    │       │   cần, stress tài chính │
│   ACID, khóa ngoại FK   │       │ • Schema linh hoạt      │
└─────────────────────────┘       └─────────────────────────┘
```

### 1.3. Chi tiết các cơ sở dữ liệu được lựa chọn và Lý do

#### 1. Cơ sở dữ liệu Quan hệ (Relational Database) – Công nghệ đề xuất: PostgreSQL / MySQL
* **Vị trí trong bài toán:** Quản lý dữ liệu hồ sơ gốc, thông tin cá nhân và định danh sinh viên.
* **Lý do lựa chọn (Căn cứ Slide 13 - 16):**
  * **Cấu trúc ổn định và định nghĩa chặt chẽ:** Thông tin như `Student_ID`, `Gender`, `First_Generation`, `Household_Size`, `Tuition_Base` là dữ liệu có cấu trúc (Structured data) cố định trong suốt quá trình sinh viên học tập.
  * **Tuân thủ thuộc tính ACID:** Đảm bảo tính nhất quán mạnh mẽ (Strong consistency), tránh việc sai lệch dữ liệu định danh sinh viên hoặc hồ sơ tài chính.
  * **Khóa chính và Ràng buộc (Primary Key / Constraints):** Đảm bảo mỗi `Student_ID` là duy nhất, không bị trùng lặp.

#### 2. Cơ sở dữ liệu Dạng Tài liệu (Document Database) – Công nghệ đề xuất: MongoDB
* **Vị trí trong bài toán:** Lưu trữ lịch sử học tập, mức độ tương tác và biến động tài chính theo từng học kỳ của sinh viên (Longitudinal Logs).
* **Lý do lựa chọn (Căn cứ Slide 22 - 27):**
  * **Không cần lược đồ cố định (Schema-less):** Sinh viên qua từng học kỳ có thể có các phát sinh khác nhau (có kỳ có chi phí khẩn cấp, có kỳ phát sinh nhiều lần gặp cố vấn, v.v.). Document DB cho phép thêm/bớt trường thuộc tính dễ dàng.
  * **Hỗ trợ dữ liệu lồng nhau (Embedded Documents / Arrays):** Cho phép nhúng toàn bộ danh sách 8 học kỳ của một sinh viên vào trong một tài liệu duy nhất (hoặc lưu từng log học kỳ dạng JSON tự diễn giải).
  * **Tối ưu hóa việc nạp và xử lý dữ liệu cho Machine Learning:** Dữ liệu JSON/BSON tương thích trực tiếp với các thư viện Data Science (Pandas, PySpark, Python Scikit-Learn).

---

## CÂU 2: THIẾT KẾ CƠ SỞ DỮ LIỆU & VÍ DỤ DỮ LIỆU MẪU (5 ĐIỂM DỮ LIỆU CHO MỖI BẢNG)

### 2.1. Thiết kế Cơ sở dữ liệu Quan hệ (Relational Database - PostgreSQL)

Nhóm phân rã dữ liệu thành **2 bảng quan hệ** chuẩn hóa để tránh dư thừa dữ liệu:
* **Bảng 1: `students`** (Lưu thông tin nhân khẩu học và định danh sinh viên).
* **Bảng 2: `financial_profiles`** (Lưu hồ sơ tài chính và thông tin học phí cố định).

#### Bảng 1: `students`
* **Các trường thông tin:**
  * `student_id` (VARCHAR(15), Primary Key): Mã định danh sinh viên.
  * `age` (INT): Tuổi lúc nhập học.
  * `gender` (VARCHAR(10)): Giới tính (Male/Female).
  * `first_generation` (BOOLEAN): Thế hệ đầu tiên học đại học (0 = Không, 1 = Có).
  * `household_size` (INT): Số người trong gia đình.
  * `housing_status` (VARCHAR(20)): Nơi cư trú (On-Campus / Off-Campus).
  * `family_income` (NUMERIC(12,2)): Thu nhập gia đình hàng năm (USD).

* **Ví dụ 5 điểm dữ liệu thực tế (Lấy từ dataset):**

| student_id | age | gender | first_generation | household_size | housing_status | family_income |
| :--- | :---: | :--- | :---: | :---: | :--- | :---: |
| **STU_00001** | 18 | Female | 0 | 2 | Off-Campus | 15000.00 |
| **STU_00002** | 20 | Male | 1 | 5 | On-Campus | 80000.00 |
| **STU_00003** | 24 | Male | 1 | 3 | On-Campus | 136000.00 |
| **STU_00004** | 19 | Male | 1 | 2 | On-Campus | 24000.00 |
| **STU_00005** | 18 | Female | 0 | 3 | Off-Campus | 30000.00 |

---

#### Bảng 2: `financial_profiles`
* **Các trường thông tin:**
  * `profile_id` (INT, Primary Key): Mã hồ sơ tài chính.
  * `student_id` (VARCHAR(15), Foreign Key tham chiếu `students.student_id`).
  * `scholarship` (BOOLEAN): Nhận học bổng (0 = Không, 1 = Có).
  * `tuition_base` (NUMERIC(10,2)): Học phí cơ sở hàng năm.
  * `emergency_expense` (NUMERIC(10,2)): Chi phí phát sinh khẩn cấp.

* **Ví dụ 5 điểm dữ liệu thực tế:**

| profile_id | student_id | scholarship | tuition_base | emergency_expense |
| :---: | :--- | :---: | :---: | :---: |
| **1** | STU_00001 | 0 | 15000.00 | 0.00 |
| **2** | STU_00002 | 1 | 25000.00 | 0.00 |
| **3** | STU_00003 | 0 | 15000.00 | 0.00 |
| **4** | STU_00004 | 0 | 15000.00 | 0.00 |
| **5** | STU_00005 | 0 | 45000.00 | 0.00 |

---

### 2.2. Thiết kế Cơ sở dữ liệu Dạng Tài liệu (Document Database - MongoDB)

Nhóm thiết kế một Collection có tên là **`academic_semesters`** nhằm lưu trữ các bản ghi học kỳ theo chiều dọc. Cấu trúc linh hoạt của JSON/BSON giúp phản ánh trọn vẹn toàn bộ hành vi học tập và biến động tài chính của sinh viên ở từng kỳ.

* **Các trường thông tin trong mỗi tài liệu (Document):**
  * `_id`: ObjectId duy nhất do MongoDB sinh ra.
  * `student_id`: Mã sinh viên.
  * `semester`: Học kỳ thứ mấy (1 - 8).
  * `academic_performance`: Đối tượng lồng nhau gồm `sem_gpa`, `failed_courses`, `course_load`.
  * `engagement`: Đối tượng lồng nhau gồm `attendance` (%), `lms_logins`, `advising_visits`.
  * `socio_economic`: Đối tượng lồng nhau gồm `work_hours`, `financial_stress`.
  * `outcome`: Đối tượng mục tiêu gồm `target_dropout_next_sem` (0/1), `end_of_semester_status`, `censored`.

* **Ví dụ 5 điểm dữ liệu (5 Document JSON) mô tả chuỗi theo dõi 5 học kỳ của sinh viên `STU_00001`:**

```json
// Điểm dữ liệu 1: Học kỳ 1 của STU_00001
{
  "_id": "67041a01b12f8e1234567801",
  "student_id": "STU_00001",
  "semester": 1,
  "academic_performance": { "sem_gpa": 2.85, "failed_courses": 0, "course_load": 15 },
  "engagement": { "attendance": 85.8, "lms_logins": 67, "advising_visits": 0 },
  "socio_economic": { "work_hours": 18.4, "financial_stress": 1.7 },
  "outcome": { "target_dropout_next_sem": 0, "end_of_semester_status": "Enrolled", "censored": 0 }
}

// Điểm dữ liệu 2: Học kỳ 2 của STU_00001
{
  "_id": "67041a01b12f8e1234567802",
  "student_id": "STU_00001",
  "semester": 2,
  "academic_performance": { "sem_gpa": 2.73, "failed_courses": 0, "course_load": 15 },
  "engagement": { "attendance": 81.0, "lms_logins": 89, "advising_visits": 1 },
  "socio_economic": { "work_hours": 23.1, "financial_stress": 3.1 },
  "outcome": { "target_dropout_next_sem": 0, "end_of_semester_status": "Enrolled", "censored": 0 }
}

// Điểm dữ liệu 3: Học kỳ 3 của STU_00001
{
  "_id": "67041a01b12f8e1234567803",
  "student_id": "STU_00001",
  "semester": 3,
  "academic_performance": { "sem_gpa": 2.60, "failed_courses": 2, "course_load": 15 },
  "engagement": { "attendance": 78.3, "lms_logins": 60, "advising_visits": 0 },
  "socio_economic": { "work_hours": 19.1, "financial_stress": 3.0 },
  "outcome": { "target_dropout_next_sem": 0, "end_of_semester_status": "Enrolled", "censored": 0 }
}

// Điểm dữ liệu 4: Học kỳ 4 của STU_00001 (Nguy cơ tăng vọt)
{
  "_id": "67041a01b12f8e1234567804",
  "student_id": "STU_00001",
  "semester": 4,
  "academic_performance": { "sem_gpa": 2.34, "failed_courses": 3, "course_load": 15 },
  "engagement": { "attendance": 77.2, "lms_logins": 59, "advising_visits": 2 },
  "socio_economic": { "work_hours": 26.5, "financial_stress": 5.1 },
  "outcome": { "target_dropout_next_sem": 0, "end_of_semester_status": "Enrolled", "censored": 0 }
}

// Điểm dữ liệu 5: Học kỳ 5 của STU_00001 (Bị cảnh báo nguy cơ cao)
{
  "_id": "67041a01b12f8e1234567805",
  "student_id": "STU_00001",
  "semester": 5,
  "academic_performance": { "sem_gpa": 1.90, "failed_courses": 2, "course_load": 18 },
  "engagement": { "attendance": 79.3, "lms_logins": 53, "advising_visits": 1 },
  "socio_economic": { "work_hours": 25.4, "financial_stress": 3.6 },
  "outcome": { "target_dropout_next_sem": 0, "end_of_semester_status": "Enrolled", "censored": 1 }
}
```

---

## CÂU 3: XÁC ĐỊNH SỐ LƯỢNG ĐIỂM DỮ LIỆU TỐI THIỂU CẦN THIẾT CHO BÀI TOÁN MACHINE LEARNING / AI

Để xác định số lượng điểm dữ liệu tối thiểu một cách khoa học, nhóm căn cứ vào **3 nguyên lý trong Khoa học Dữ liệu & Thống kê**:

### 3.1. Căn cứ theo số lượng thuộc tính (The Rule of Thumb / Vapnik-Chervonenkis Dimension)
* **Nguyên tắc kinh nghiệm (Harrell's Guidelines):** Để mô hình không bị quá khớp (overfitting), số lượng mẫu quan sát tối thiểu phải gấp từ **10 đến 20 lần** số lượng biến đặc trưng ($N \ge 10 \times p$) đối với mô hình tuyến tính, và gấp **50 lần** ($N \ge 50 \times p$) đối với các mô hình phi tuyến tính phức tạp (Random Forest, Gradient Boosting/XGBoost).
* **Áp dụng vào bài toán:**
  * Tập dữ liệu có khoảng $p = 18 - 20$ đặc trưng (bao gồm cả các đặc trưng tạo thêm như `Delta_GPA`, `Cumulative_Failed`).
  * $\Rightarrow$ Số mẫu tối thiểu theo lý thuyết: $N_{\text{min}} = 50 \times 20 = \mathbf{1.000\text{ bản ghi}}$.

### 3.2. Căn cứ theo đặc thù mất cân bằng nhãn (Class Imbalance)
* **Thực tế bài toán giáo dục:** Tỷ lệ sinh viên bỏ học (`Target_Dropout_Next_Sem = 1`) thường là lớp thiểu số, chiếm khoảng **10% - 15%** tổng số sinh viên.
* **Yêu cầu tập kiểm thử (Test set):** Khi chia tập dữ liệu (80% Train, 10% Validation, 10% Test), để tập Test có tối thiểu **100 - 150 trường hợp sinh viên bỏ học thật sự** (nhằm đảm bảo độ tin cậy thống kê cho các chỉ số Recall, F1-Score, PR-AUC), số lượng mẫu bỏ học cần có trong toàn bộ dữ liệu phải đạt ít nhất $1.000$ trường hợp.
* Với tỷ lệ bỏ học 10%, tổng số mẫu tối thiểu cần có là:
  $$N_{\text{min}} = \frac{1.000}{0.10} = \mathbf{10.000\text{ điểm dữ liệu}}.$$

### 3.3. Căn cứ theo bản chất dữ liệu theo chiều dọc (Longitudinal Trajectory)
* Không giống như dữ liệu tĩnh (mỗi sinh viên là 1 dòng), dữ liệu theo chiều dọc có mỗi sinh viên lặp lại qua **4 đến 8 học kỳ** (trung bình ~4 học kỳ/sinh viên).
* Nếu chỉ có 1.000 bản ghi, thực chất chỉ có khoảng **250 sinh viên độc lập**. Với số lượng cá thể quá ít, khi chia nhóm `GroupKFold` theo `Student_ID`, mô hình sẽ không đủ đa dạng để khái quát hóa hành vi của các nhóm sinh viên khác nhau.
* Để mô hình học máy và khai phá phân cụm (Clustering/Apriori) hoạt động hiệu quả, cần tối thiểu **1.000 đến 1.500 sinh viên độc lập**, tương đương:
  $$N_{\text{min}} \approx 1.250 \times 4 = \mathbf{5.000\text{ đến }6.000\text{ điểm dữ liệu}}.$$

---

### 3.4. KẾT LUẬN & ĐỐI CHIẾU VỚI TẬP DỮ LIỆU THỰC TẾ CỦA NHÓM

| Tiêu chí | Ngưỡng tối thiểu cần thiết | Thực tế tập dữ liệu `academic_survival_longitudinal.csv` | Đánh giá |
| :--- | :---: | :---: | :---: |
| **Tổng số điểm dữ liệu (Records)** | $\ge 5.000 - 10.000$ dòng | **79.239 dòng** | **Vượt bậc (~8 lần ngưỡng tối thiểu)** |
| **Số lượng sinh viên độc lập** | $\ge 1.000 - 1.500$ sinh viên | **gần 20.000 sinh viên** | **Đảm bảo tính đại diện rất cao** |
| **Độ sâu lịch sử theo dõi** | Tối thiểu 3 - 4 kỳ liên tiếp | **Tối đa 8 học kỳ liên tiếp** | **Lý tưởng cho Feature Engineering chuỗi thời gian** |

**Kết luận:** Tập dữ liệu của nhóm hoàn toàn đáp ứng xuất sắc tiêu chuẩn của một bài toán **Dữ liệu lớn (Big Data - đảm bảo yếu tố Volume và Variety)**, cung cấp đầy đủ kích thước mẫu để triển khai cả 2 nhánh: **Khai phá tri thức (Data Mining)** và **Học máy phân loại nhị phân (Machine Learning Classification)** với độ tin cậy khoa học cao nhất.
