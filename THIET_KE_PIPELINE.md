# THIẾT KẾ DATA PIPELINE: DỰ ĐOÁN NGUY CƠ BỎ HỌC CỦA SINH VIÊN
**Môn học:** Tích hợp và Phân tích Dữ liệu Lớn  
**Kiến trúc tổng thể:** `Raw Data → Ingestion → ETL/ELT → Storage → Machine Learning → Visualization`

---

### 1. Nguồn dữ liệu (Data Sources)
* **Dữ liệu đến từ đâu:** Đến từ 3 hệ thống nội bộ của trường đại học:
  1. *Hệ thống thông tin đào tạo (SIS - Student Information System):* Điểm số (`Sem_GPA`), số tín chỉ (`Course_Load`), môn trượt (`Failed_Courses`), học phí (`Tuition_Base`).
  2. *Hệ thống học tập trực tuyến (LMS - Moodle/Canvas):* Lịch sử đăng nhập (`LMS_Logins`), điểm danh chuyên cần (`Attendance`).
  3. *Khảo sát sinh viên & Phòng Công tác sinh viên:* Áp lực tài chính (`Financial_Stress`), giờ làm thêm (`Work_Hours`), chi phí đột xuất (`Emergency_Expense`), gặp cố vấn (`Advising_Visits`).
* **Loại dữ liệu:** Dữ liệu hỗn hợp: Dữ liệu có cấu trúc (bảng điểm, học phí từ CSDL SQL) và bán cấu trúc (logs truy cập LMS, file kết quả khảo sát CSV/JSON).
* **Dung lượng mỗi ngày:** Dữ liệu định danh và điểm số chỉ cập nhật theo đợt (cuối kỳ/giữa kỳ). Dữ liệu hành vi LMS phát sinh khoảng **1.000 – 5.000 sự kiện/ngày** (rất nhẹ, dưới 10 MB/ngày).

---

### 2. Batch hay Streaming
* **Lựa chọn:** **Batch Processing (Xử lý theo lô)**.
* **Vì sao:** 
  * Bài toán đặt ra là dự đoán nguy cơ bỏ học ở **học kỳ tiếp theo** (`Target_Dropout_Next_Sem`).
  * Quyết định bỏ học hay can thiệp học vụ diễn ra theo chu kỳ tuần/tháng hoặc trước thềm học kỳ mới, không đòi hỏi phản hồi tức thời theo thời gian thực (mili-giây) như phát hiện gian lận thẻ tín dụng hay sensor IoT.
  * Xử lý Batch định kỳ (ví dụ: chạy hàng tuần hoặc sau mỗi đợt thi) giúp tiết kiệm tài nguyên tính toán và chi phí vận hành.

---

### 3. Dữ liệu bẩn và Cách xử lý (Data Quality Issues)
1. **Giá trị khuyết thiếu (Missing Values):** 
   * *Thực tế:* Cột `Family_Income` bị bỏ trống ở một số sinh viên do không khai báo.
   * *Cách xử lý:* Điền khuyết (Imputation) bằng giá trị trung vị (Median) theo nhóm quy mô hộ gia đình (`Household_Size`) hoặc sử dụng thuật toán KNN Imputer.
2. **Giá trị bất thường / Ngoại lai (Outliers):**
   * *Thực tế:* Số giờ làm thêm (`Work_Hours`) ghi nhận > 80 giờ/tuần hoặc điểm chuyên cần (`Attendance`) ngoài khoảng [0, 100].
   * *Cách xử lý:* Dùng phương pháp IQR để chặn ngưỡng (Winsorization/Clipping) đưa về dải giá trị thực tế hợp lý.
3. **Trùng lặp bản ghi & Sai lệch định dạng (Duplicates & Categorical Inconsistency):**
   * *Thực tế:* Trùng lặp cặp khóa (`Student_ID`, `Semester`) do nạp lại file; chuỗi phân loại như `Housing_Status` viết hoa/thường lộn xộn ("On-Campus", "on-campus").
   * *Cách xử lý:* Chuẩn hóa text (`lower().strip()`) và áp dụng `drop_duplicates(subset=['Student_ID', 'Semester'])`.

---

### 4. ETL hay ELT
* **Lựa chọn:** **ETL (Extract - Transform - Load)**.
* **Giải thích ngắn gọn:** 
  * Dung lượng dữ liệu ở quy mô vừa phải (~79.239 bản ghi, ~7.5 MB).
  * Cần làm sạch, khử nhiễu và trích xuất đặc trưng chuỗi thời gian phức tạp (Delta GPA, tích lũy nợ môn) *trước khi* đưa vào kho dữ liệu để các nhà phân tích và mô hình Machine Learning có thể sử dụng ngay mà không cần xử lý lại trên kho lưu trữ.

---

### 5. Quy trình Biến đổi dữ liệu (Transformation Steps)
Chuỗi biến đổi từ dữ liệu thô sang dữ liệu sạch sẵn sàng cho mô hình:
```text
Raw Ingestion → Remove Duplicates → Handle Missing Values → Standardize & Encode Categoricals 
→ Feature Engineering (Delta GPA, Delta Attendance, Cumulative Failed Courses) 
→ Feature Scaling (StandardScaler/RobustScaler) → Train/Test Split (GroupKFold by Student_ID)
```

---

### 6. Đánh giá nhu cầu Apache Spark / Flink
* **Đánh giá:** **Python / Pandas / SQL là HOÀN TOÀN ĐỦ**, **KHÔNG CẦN** Apache Spark hay Apache Flink.
* **Vì sao:** 
  * Tập dữ liệu gồm 79.239 dòng, kích thước file khoảng **7.4 MB**. Khi nạp toàn bộ vào bộ nhớ RAM qua thư viện Pandas chỉ tốn chưa tới **150 MB RAM**.
  * Máy tính cá nhân hiện nay (8GB – 16GB RAM) có thể xử lý, tính toán đặc trưng và huấn luyện mô hình trong vòng vài chục giây.
  * Việc dựng cụm phân tán Apache Spark/Flink cho tập dữ liệu này sẽ gây lãng phí tài nguyên, tốn chi phí thiết lập cụm và phát sinh độ trễ mạng (network overhead) không cần thiết (Over-engineering).

---

### 7. Lưu trữ dữ liệu (Storage Architecture)
* **Dữ liệu thô (Raw Data Lake):** Lưu dưới dạng tệp gốc CSV/Parquet tại **Object Storage** (MinIO trên Local hoặc AWS S3) để lưu vết lịch sử (Audit trail).
* **Dữ liệu có cấu trúc & Hồ sơ sinh viên:** Lưu tại **Cơ sở dữ liệu quan hệ (PostgreSQL)** để quản lý giao dịch và khóa ngoại.
* **Dữ liệu nhật ký học kỳ (Analytical/Longitudinal Data):** Lưu tại **Document Database (MongoDB)** hoặc các bảng chuẩn hóa trong PostgreSQL để phục vụ trích xuất đặc trưng cho ML.

---

### 8. Hạ tầng triển khai: Cloud, Local hay Hybrid
* **Lựa chọn:** **Local (đóng gói bằng Docker Containers)**, sẵn sàng mở rộng sang **Hybrid**.
* **Giải thích:**
  * *Chi phí:* Chi phí 0 đồng cho bài tập lớn đại học; tận dụng phần cứng máy trạm có sẵn.
  * *Bảo mật dữ liệu:* Dữ liệu sinh viên, học phí và điểm số là dữ liệu nhạy cảm, chạy On-premise/Local giúp kiểm soát hoàn toàn quyền truy cập.
  * *Khả năng mở rộng:* Toàn bộ các dịch vụ (PostgreSQL, MongoDB, MLflow, Dashboard) được triển khai qua `docker-compose.yml`, giúp dễ dàng dịch chuyển lên Cloud (AWS/GCP) khi nhà trường muốn áp dụng thực tế.

---

### 9. Chiến lược Sao lưu (Backup Strategy)
* **Dữ liệu cần backup:** 
  1. Cơ sở dữ liệu PostgreSQL (hồ sơ sinh viên, thông tin tài chính).
  2. Dữ liệu MongoDB (nhật ký biến động học kỳ).
  3. Artifacts và trọng số mô hình tốt nhất từ MLflow.
* **Tần suất backup:** Backup định kỳ **hàng tuần (Weekly)** hoặc ngay sau mỗi đợt nạp dữ liệu cuối học kỳ.
* **Nơi lưu bản sao lưu:** Lưu bản dump nén (`pg_dump`, `mongodump`) trên một ổ cứng lưu trữ độc lập hoặc đẩy tự động lên Google Drive/AWS S3 Glacier.

---

### 10. Machine Learning & Quản lý phiên bản (Model Management)
* **Mục đích của Model:** Dự đoán xác suất nhị phân sinh viên có nguy cơ bỏ học ở kỳ tiếp theo (`Target_Dropout_Next_Sem = 1`) và tính điểm rủi ro (Risk Score: Thấp, Trung bình, Cao).
* **Nơi chạy:** Chạy dạng Batch Inference Script viết bằng Python (Scikit-Learn, XGBoost) kích hoạt định kỳ.
* **Công cụ quản lý phiên bản:** Sử dụng **MLflow** để:
  * Theo dõi tham số (Hyperparameters), độ đo (Recall, F1-Score, PR-AUC).
  * Đăng ký và quản lý phiên bản mô hình (Model Registry: Staging, Production).

---

### 11. Trực quan hóa dữ liệu (Visualization & Dashboard)
* **Các thông tin hiển thị trên Dashboard:**
  * Tỷ lệ sinh viên có nguy cơ bỏ học tổng thể và phân bổ theo khoa/ngành.
  * Danh sách cảnh báo đỏ: Top các sinh viên có nguy cơ cao nhất kèm điểm rủi ro.
  * Biểu đồ xu hướng: Tương quan giữa sụt giảm GPA, số giờ làm thêm với nguy cơ bỏ học.
  * Biểu đồ SHAP Waterfall: Giải thích lý do cụ thể vì sao một sinh viên bị cảnh báo (ví dụ: do nợ 3 môn hay do áp lực tài chính tăng vọt).
* **Công cụ lựa chọn:** **Power BI** (phù hợp cho cán bộ phòng đào tạo/quản lý) kết hợp **Streamlit** (giao diện web demo nhanh cho môn học).

---

### 12. Giám sát hệ thống (System & Model Monitoring)
Lựa chọn **5 metrics cốt lõi** để kiểm tra tính ổn định:
1. `Pipeline Execution Latency:` Thời gian hoàn thành toàn bộ chu trình ETL (mục tiêu: < 2 phút).
2. `Data Ingestion Error Rate:` Tỷ lệ bản ghi bị lỗi schema hoặc không thể nạp (mục tiêu: < 0.1%).
3. `Missing Data Rate:` Tỷ lệ trường thông tin bị khuyết thiếu trong mỗi đợt nạp mới.
4. `Model Performance Metrics (Recall & PR-AUC):` Giám sát độ nhạy của mô hình trên dữ liệu kỳ mới để tránh bỏ sót sinh viên nguy cơ.
5. `Data Drift / Concept Drift:` Độ lệch phân phối của các biến chính (`Sem_GPA`, `Financial_Stress`) giữa tập huấn luyện và dữ liệu kỳ mới.

---

### 13. Tóm tắt Pipeline trong 1 dòng & Lý giải độ phù hợp

**Pipeline của nhóm:**
```text
SIS / LMS / Survey (CSV/API) → Python ETL (Pandas) → PostgreSQL + MongoDB → MLflow (XGBoost) → Power BI Dashboard
```

* **Lý giải ngắn gọn tại sao kiến trúc này phù hợp:**
  Kiến trúc này **tinh gọn, thực dụng và loại bỏ triệt để tình trạng lãng phí tài nguyên (No Over-engineering)**. Với quy mô dữ liệu khoảng 79.239 bản ghi (~7.5 MB), việc sử dụng bộ ba `Python/Pandas + PostgreSQL/MongoDB + XGBoost` xử lý mượt mà 100% trong bộ nhớ với chi phí 0 đồng, thời gian triển khai nhanh, đồng thời vẫn đáp ứng đầy đủ các chuẩn công nghiệp hiện đại từ lưu trữ đa mô hình, quản lý phiên bản MLflow đến trực quan hóa dữ liệu.
