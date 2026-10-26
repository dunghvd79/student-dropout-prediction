# THIẾT KẾ DATA PIPELINE: DỰ ĐOÁN NGUY CƠ BỎ HỌC CỦA SINH VIÊN
**Môn học:** Tích hợp và Phân tích Dữ liệu Lớn  
**Kiến trúc tổng thể:** `Raw Data → Ingestion → ETL → Storage → Machine Learning → Visualization`

---

### 1. Nguồn dữ liệu (Data Sources)
* **Dữ liệu đến từ đâu:** Bộ dữ liệu `academic_survival_longitudinal.csv` (**79.239 bản ghi, 22 cột, 20.000 sinh viên**, mỗi dòng là một cặp `Student_ID – Semester`). Trong thực tế, các cột này được tổng hợp từ 3 hệ thống nội bộ của trường:
  1. *Hệ thống thông tin đào tạo (SIS - Student Information System):* Điểm số (`Sem_GPA`), số tín chỉ (`Course_Load`), môn trượt (`Failed_Courses`), học phí (`Tuition_Base`), học bổng (`Scholarship`).
  2. *Hệ thống học tập trực tuyến (LMS - Moodle/Canvas):* Số lần đăng nhập (`LMS_Logins`), điểm danh chuyên cần (`Attendance`).
  3. *Khảo sát sinh viên & Phòng Công tác sinh viên:* Thu nhập gia đình (`Family_Income`), áp lực tài chính (`Financial_Stress`), giờ làm thêm (`Work_Hours`), chi phí đột xuất (`Emergency_Expense`), gặp cố vấn (`Advising_Visits`).
* **Loại dữ liệu:** Dữ liệu có cấu trúc dạng bảng (CSV, CSDL SQL), đã được tổng hợp theo học kỳ (longitudinal). Ở hệ thống thực, log LMS là dữ liệu bán cấu trúc và được cộng dồn thành `LMS_Logins` theo kỳ.
* **Dung lượng mỗi ngày:** Toàn bộ tập dữ liệu chỉ ~**7,4 MB**. Dữ liệu điểm số cập nhật theo đợt (giữa kỳ/cuối kỳ). Dữ liệu hành vi LMS phát sinh khoảng **1.000 – 5.000 sự kiện/ngày** (dưới 10 MB/ngày).

---

### 2. Batch hay Streaming
* **Lựa chọn:** **Batch Processing (Xử lý theo lô)**.
* **Vì sao:** 
  * Bài toán là dự đoán nguy cơ bỏ học ở **học kỳ tiếp theo** (`Target_Dropout_Next_Sem`).
  * Quyết định can thiệp học vụ diễn ra theo chu kỳ tuần/tháng hoặc trước học kỳ mới, không cần phản hồi tức thời (mili-giây) như phát hiện gian lận thẻ tín dụng hay sensor IoT.
  * Xử lý Batch định kỳ giúp tiết kiệm tài nguyên tính toán và chi phí vận hành.
* **Lập lịch:** Dùng cron / Windows Task Scheduler (hoặc Apache Airflow khi mở rộng) để chạy pipeline **hàng tuần** và **sau mỗi đợt thi**.

---

### 3. Dữ liệu bẩn và Cách xử lý (Data Quality Issues)
*(Số liệu kiểm tra trực tiếp trên `academic_survival_longitudinal.csv`)*

1. **Giá trị khuyết thiếu (Missing Values):** 
   * *Thực tế:* `Family_Income` thiếu **3.604 dòng (~4,5%)** do sinh viên không khai báo; `LMS_Logins` thiếu **867 dòng (~1,1%)**.
   * *Cách xử lý:* `Family_Income` của một sinh viên **không đổi qua các kỳ**, nhưng *việc biết* giá trị thì phụ thuộc thời gian, nên chỉ điền bằng giá trị đã khai báo ở **kỳ trước** của chính sinh viên đó (ffill theo `Student_ID`, **không bfill**). Cách này khôi phục được **2.574 / 3.604 dòng**. Bản đầu dùng thêm bfill và đặt cờ "không khai báo ở kỳ nào"; SHAP ở B13 cho thấy cờ đó nhìn trước tương lai (84,7% dòng mang cờ là bỏ học, đúng thời điểm chỉ 10,7%) nên đã bỏ. Phần còn lại (1.030 dòng chưa khai báo tính đến kỳ đó) điền bằng trung vị theo nhóm `Household_Size`, với trung vị tính trên tập Train, và thêm cột cờ `Income_Missing`. `LMS_Logins` điền bằng giá trị của chính sinh viên đó ở kỳ trước (forward-fill theo `Student_ID`), nếu không có thì dùng trung vị.
2. **Giá trị bất thường / Ngoại lai (Outliers):**
   * *Thực tế:* `Attendance` nằm ngoài khoảng hợp lệ [0, 100] (min = **-2**, max = **105**; 249 dòng). `Family_Income` lệch phải mạnh (từ 3.000 đến **488.000**). `Financial_Stress` được mô tả là thang 1 - 5 nhưng thực tế là **chỉ số liên tục lệch phải** (trung vị 2,1; P99 = 9,0; max = **18,6**; 7.348 dòng > 5).
   * *Cách xử lý:* `Attendance`: Giá trị âm luôn đúng bằng **−2** (mã lỗi): kỳ trước / kỳ sau của chính sinh viên đó quanh 86%, và không có ai thực sự chuyên cần 0 – 10% → coi là **thiếu**, điền bằng kỳ trước (ffill), không clip về 0 (clip sẽ tạo cú sụt giả ~−86 điểm). Giá trị > 100 (101, 105) là đếm dư → clip về 100. `Family_Income` dùng biến đổi log (`log1p`) hoặc chặn theo IQR (Winsorization). `Financial_Stress` **không được chặn về 5**: tỷ lệ bỏ học tăng đều theo chỉ số này (5,3% ở mức 1 → 20,7% ở mức 5 → 50,2% ở mức ≥ 10, tính trên tập có nhãn), nên giá trị cao là tín hiệu thật chứ không phải lỗi. Chỉ chặn ở P99 (Winsorization) hoặc dùng `log1p` cho các mô hình tuyến tính; các mô hình cây dùng giá trị gốc.
3. **Sai lệch định dạng phân loại (Categorical Inconsistency):**
   * *Thực tế:* `Gender` có 8 cách ghi cho cùng ý nghĩa: `Female / female / F`, `Male / male / M`, `Other`, `Prefer not to say`. `Housing_Status` có 3 giá trị hợp lệ: `On-Campus`, `Off-Campus`, `With Parents`.
   * *Cách xử lý:* Chuẩn hóa `lower().strip()` rồi map về 3 nhóm: `Female`, `Male`, `Other/Unknown`. `Housing_Status` giữ nguyên 3 nhóm và mã hóa One-Hot.
4. **Trùng lặp bản ghi (kiểm tra phòng ngừa):**
   * *Thực tế:* Hiện **không có** bản ghi trùng (`Student_ID`, `Semester`), nhưng có thể phát sinh khi nạp lại file.
   * *Cách xử lý:* Luôn chạy `drop_duplicates(subset=['Student_ID', 'Semester'], keep='last')` ở đầu pipeline.
5. **Rò rỉ dữ liệu (Data Leakage):**
   * *Thực tế:* Cột `End_of_Semester_Status` (`Dropped_Out`, `Graduated`, `Enrolled`) và `Censored` chứa thông tin kết quả.
   * *Cách xử lý:* Loại 2 cột này khỏi tập đặc trưng khi huấn luyện mô hình. Lưu ý `Target_Dropout_Next_Sem = 1` **khi và chỉ khi** `End_of_Semester_Status = Dropped_Out`, nên giữ lại cột này sẽ cho kết quả "hoàn hảo" giả.
6. **Nhãn chưa xác định do dữ liệu bị cắt (Right-censoring):**
   * *Thực tế:* **11.115 dòng** có `Censored = 1`. Đây là kỳ cuối cùng quan sát được của những sinh viên chưa bỏ học cũng chưa tốt nghiệp. Nhãn của các dòng này đang là 0, nhưng thực chất **chưa biết** kỳ sau sinh viên có bỏ học hay không.
   * *Cách xử lý:* Không dùng các dòng này để huấn luyện và kiểm thử. Tập có nhãn còn **68.124 dòng**, trong đó lớp bỏ học chiếm 10,2%. 11.115 dòng `Censored = 1` chính là **tập sinh viên đang theo học cần chấm điểm rủi ro** ở bước Batch Inference.

---

### 4. ETL hay ELT
* **Lựa chọn:** **ETL (Extract - Transform - Load)**.
* **Giải thích ngắn gọn:** 
  * Dữ liệu có dung lượng vừa phải (~79.239 bản ghi, ~7,4 MB), biến đổi bằng Pandas trong bộ nhớ chỉ mất vài giây.
  * Cần làm sạch và tạo đặc trưng theo thời gian (Delta GPA, tích lũy nợ môn) *trước khi* nạp vào kho, để nhà phân tích và mô hình ML dùng được ngay.
  * ELT chỉ có lợi khi có Data Warehouse trên cloud với sức tính toán lớn (BigQuery, Snowflake), điều không cần thiết với quy mô này.

---

### 5. Quy trình Biến đổi dữ liệu (Transformation Steps)
Chuỗi biến đổi từ dữ liệu thô sang dữ liệu sạch sẵn sàng cho mô hình:
```text
Raw Ingestion → Join data (SIS + LMS + Survey theo Student_ID, Semester) → Remove Duplicates
→ Handle Missing Values → Fix Outliers → Standardize & Encode Categoricals
→ Feature Engineering (Delta GPA, Delta Attendance, Cumulative Failed Courses)
→ Drop Leakage Columns → Tách dòng Censored = 1 ra làm tập chấm điểm
→ Train/Test Split (GroupKFold by Student_ID)
→ Feature Scaling (fit trên tập Train, áp dụng cho Test)
```
> Scaling được thực hiện **sau** khi chia Train/Test để tránh rò rỉ thông tin từ tập Test. Chia theo `Student_ID` để cùng một sinh viên không xuất hiện ở cả hai tập. Chi tiết input, biến đổi và output của từng bước xem tại thư mục [`QUY_TRINH_DU_AN/`](./QUY_TRINH_DU_AN/README.md).

---

### 6. Đánh giá nhu cầu Apache Spark / Flink
* **Đánh giá:** **Python / Pandas / SQL là HOÀN TOÀN ĐỦ**, **KHÔNG CẦN** Apache Spark hay Apache Flink.
* **Vì sao:** 
  * Tập dữ liệu gồm 79.239 dòng, kích thước file khoảng **7,4 MB**. Khi nạp toàn bộ vào RAM qua Pandas chỉ tốn chưa tới **150 MB RAM**.
  * Máy tính cá nhân hiện nay (8GB – 16GB RAM) xử lý, tạo đặc trưng và huấn luyện mô hình trong vài chục giây.
  * Dựng cụm phân tán Spark/Flink cho tập dữ liệu này gây lãng phí tài nguyên, tốn công thiết lập và phát sinh độ trễ mạng không cần thiết (Over-engineering).
* **Khi nào mới cần:** Khi dữ liệu vượt quá RAM một máy (hàng chục GB, ví dụ log LMS thô của nhiều năm) thì dùng **Spark**; khi cần cảnh báo theo thời gian thực từ luồng sự kiện LMS thì dùng **Flink**.

---

### 7. Lưu trữ dữ liệu (Storage Architecture)
Kế thừa kiến trúc **Polyglot Persistence (PostgreSQL + MongoDB)** đã thiết kế ở bài giữa kỳ (`BAO_CAO_CSDL_GIUA_KY.md`), bổ sung thêm tầng Object Storage cho dữ liệu thô:

| Tầng | Công nghệ | Lưu gì | Vì sao |
|---|---|---|---|
| **Raw Data Lake** | **Object Storage** (MinIO local, tương thích AWS S3) | Tệp gốc CSV/Parquet của mỗi đợt nạp | Lưu vết lịch sử (audit trail), cho phép chạy lại pipeline từ đầu |
| **Dữ liệu tĩnh & kết quả** | **PostgreSQL** (Relational DB) | `students`, `financial_profiles` (như bài giữa kỳ) + bảng mới `predictions` (Risk Score mỗi lần chạy batch) | Dữ liệu cấu trúc cố định, cần ACID, khóa chính/khóa ngoại; Power BI kết nối trực tiếp |
| **Dữ liệu theo học kỳ** | **MongoDB** (Document DB) | Collection `academic_semesters`: mỗi document là một kỳ của một sinh viên, gồm các object lồng nhau `academic_performance`, `engagement`, `socio_economic` (gồm cả `emergency_expense` vì biến động theo kỳ), `outcome` | Schema linh hoạt khi thêm chỉ số hành vi mới (ví dụ log LMS chi tiết, kết quả khảo sát JSON) mà không phải sửa bảng |

* **Vì sao không dùng một CSDL duy nhất:** Ở quy mô hiện tại (~7,4 MB) PostgreSQL một mình vẫn chạy được. Nhóm vẫn tách MongoDB vì dữ liệu học kỳ đến từ LMS và khảo sát, là những nguồn **thường xuyên thêm trường mới**. Document DB giúp nạp các trường này mà không cần migrate schema. Chi phí vận hành thêm thấp vì cả hai chạy chung trong `docker-compose`.
* **Cách ghép dữ liệu cho ML:** ETL đọc `students` + `financial_profiles` từ PostgreSQL và `academic_semesters` từ MongoDB, rồi join theo `student_id` bằng Pandas để tạo bảng đặc trưng.

---

### 8. Hạ tầng triển khai: Cloud, Local hay Hybrid
* **Lựa chọn:** **Local (đóng gói bằng Docker Containers)**, sẵn sàng mở rộng sang **Hybrid**.
* **Giải thích:**
  * *Chi phí:* 0 đồng cho bài tập lớn; tận dụng phần cứng có sẵn.
  * *Bảo mật dữ liệu:* Dữ liệu sinh viên, học phí và điểm số là dữ liệu nhạy cảm, chạy On-premise/Local giúp kiểm soát hoàn toàn quyền truy cập.
  * *Khả năng mở rộng:* Toàn bộ dịch vụ (MinIO, PostgreSQL, MongoDB, MLflow, Streamlit) được triển khai qua `docker-compose.yml`, dễ dàng chuyển lên Cloud (AWS/GCP) khi nhà trường muốn áp dụng thực tế.

---

### 9. Chiến lược Sao lưu (Backup Strategy)
* **Dữ liệu cần backup:** 
  1. **Dữ liệu thô** trong MinIO (nguồn gốc duy nhất để chạy lại toàn bộ pipeline).
  2. Cơ sở dữ liệu **PostgreSQL** (hồ sơ sinh viên, hồ sơ tài chính, lịch sử dự đoán).
  3. Cơ sở dữ liệu **MongoDB** (collection `academic_semesters`).
  4. **MLflow** artifacts, trọng số mô hình và metadata của Model Registry.
  * *Không cần backup* dữ liệu trung gian/đặc trưng vì có thể tạo lại từ dữ liệu thô.
* **Tần suất backup:** **Hàng tuần (Weekly)** và ngay sau mỗi đợt nạp dữ liệu cuối học kỳ. Giữ 4 bản tuần gần nhất + 1 bản cuối mỗi học kỳ.
* **Nơi lưu bản sao lưu:** Theo **quy tắc 3-2-1**: bản dump nén (`pg_dump`, `mongodump`, đồng bộ bucket MinIO) lưu trên máy chính + một ổ cứng độc lập + một bản ngoài site (Google Drive/AWS S3 Glacier).

---

### 10. Machine Learning & Quản lý phiên bản (Model Management)
* **Mục đích của Model:** Dự đoán xác suất sinh viên bỏ học ở kỳ tiếp theo (`Target_Dropout_Next_Sem = 1`, chiếm ~**8,7%** toàn bộ dữ liệu và **10,2%** tập có nhãn sau khi loại các dòng `Censored = 1`, mất cân bằng lớp) và gán Risk Score 3 mức theo chính sách chốt ở B12: **Cao** (≥ 0,315, Precision ≥ 0,5: liên hệ trực tiếp, ~6% sinh viên), **Trung bình** (0,070 – 0,315, cùng mức Cao đạt Recall ≥ 0,80: theo dõi / email), **Thấp** (còn lại). Mốc được chọn trên dự đoán out-of-fold, lưu trong `config/risk_thresholds.json`.
* **Mô hình:** **Logistic Regression** (trọng số lớp), chọn sau khi so sánh 6 mô hình bằng CV 5 fold theo sinh viên. Sau tinh chỉnh, XGBoost chỉ nhỉnh hơn ~0,003 PR-AUC (0,7%, nhỏ hơn dao động giữa các fold) nên chọn mô hình đơn giản, dễ giải thích hơn (xem B11).
* **Nơi chạy:** Batch Inference Script bằng Python (Scikit-Learn) chạy định kỳ trên máy local/container. Đối tượng được chấm điểm là kỳ mới nhất của các sinh viên đang theo học (11.115 dòng `Censored = 1`). Kết quả ghi vào bảng `predictions` trong PostgreSQL.
* **Công cụ quản lý phiên bản:** **MLflow** (chạy trong container Docker, backend store là PostgreSQL, artifact store là MinIO) để:
  * Theo dõi tham số (Hyperparameters), độ đo (Recall, F1-Score, PR-AUC).
  * Đăng ký và quản lý phiên bản mô hình (Model Registry: Staging, Production).

---

### 11. Trực quan hóa dữ liệu (Visualization & Dashboard)
* **Các thông tin hiển thị trên Dashboard:**
  * Tỷ lệ sinh viên có nguy cơ bỏ học tổng thể và phân bổ theo học kỳ, nơi ở (`Housing_Status`), học bổng (`Scholarship`), sinh viên thế hệ đầu (`First_Generation`).
  * Danh sách cảnh báo đỏ: Top sinh viên có nguy cơ cao nhất kèm Risk Score.
  * Biểu đồ xu hướng: Tương quan giữa sụt giảm GPA, số giờ làm thêm, áp lực tài chính với nguy cơ bỏ học.
  * Biểu đồ SHAP Waterfall: Giải thích lý do cụ thể vì sao một sinh viên bị cảnh báo (ví dụ: nợ 3 môn hay áp lực tài chính tăng vọt).
* **Công cụ lựa chọn:**
  * **Power BI** (kết nối PostgreSQL): báo cáo tổng quan cho cán bộ phòng đào tạo/quản lý.
  * **Streamlit**: giao diện web tra cứu từng sinh viên và hiển thị biểu đồ SHAP (Power BI không hỗ trợ SHAP trực tiếp).

---

### 12. Giám sát hệ thống (System & Model Monitoring)
Lựa chọn **5 metrics cốt lõi** để kiểm tra tính ổn định:
1. `Pipeline Execution Latency:` Thời gian hoàn thành toàn bộ chu trình ETL + Inference (mục tiêu: < 2 phút).
2. `Data Ingestion Error Rate:` Tỷ lệ bản ghi lỗi schema hoặc không thể nạp (mục tiêu: < 0,1%).
3. `Missing Data Rate:` Tỷ lệ trường bị khuyết trong mỗi đợt nạp mới (mốc hiện tại: `Family_Income` ~4,5%; cảnh báo nếu > 10%).
4. `Model Performance (Recall & PR-AUC):` Giám sát độ nhạy của mô hình trên dữ liệu kỳ mới để tránh bỏ sót sinh viên nguy cơ (theo dõi qua MLflow).
5. `Data Drift:` Độ lệch phân phối của các biến chính (`Sem_GPA`, `Financial_Stress`) giữa tập huấn luyện và dữ liệu kỳ mới, đo bằng chỉ số PSI (cảnh báo nếu PSI > 0,2).

---

### 13. Tóm tắt Pipeline trong 1 dòng & Lý giải độ phù hợp

**Pipeline của nhóm:**
```text
CSV (SIS/LMS/Survey) → MinIO (Raw) → Python ETL (Pandas) → PostgreSQL + MongoDB → MLflow → Logistic Regression → Power BI / Streamlit
```

* **Lý giải ngắn gọn tại sao kiến trúc này phù hợp:**
  Kiến trúc này **tinh gọn, thực dụng và không over-engineering ở tầng xử lý**. Với khoảng 79.239 bản ghi (~7,4 MB), dữ liệu được xử lý hoàn toàn trong bộ nhớ bằng Python/Pandas chỉ trong vài giây, nên không cần Spark/Flink. Tầng lưu trữ kế thừa thiết kế Polyglot của bài giữa kỳ: PostgreSQL cho dữ liệu tĩnh cần toàn vẹn, MongoDB cho dữ liệu học kỳ có schema linh hoạt, còn MinIO giữ dữ liệu thô để chạy lại khi cần. MLflow ghi lại mọi thí nghiệm (6 mô hình, tinh chỉnh, ablation) và quản lý phiên bản mô hình Logistic Regression được chọn. Toàn bộ chạy local bằng Docker với chi phí 0 đồng nhưng vẫn theo chuẩn công nghiệp và dễ chuyển lên cloud khi quy mô tăng.
