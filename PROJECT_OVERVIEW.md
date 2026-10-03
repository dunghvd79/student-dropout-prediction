# TÀI LIỆU TỔNG QUAN DỰ ÁN BÀI TẬP LỚN
**Môn học:** Tích hợp và Phân tích Dữ liệu Lớn / Khai phá Dữ liệu (Data Mining)

---

## 1. THÔNG TIN CHUNG

* **Tên đề tài tiếng Việt:** Dự đoán nguy cơ bỏ học của sinh viên đại học dựa trên dữ liệu theo chiều dọc
* **Tên đề tài tiếng Anh:** Predicting University Student Dropout Risk Using Longitudinal Academic and Engagement Data
* **Tệp dữ liệu:** `academic_survival_longitudinal.csv`
* **Quy mô dữ liệu:** 79.239 bản ghi, theo dõi gần 20.000 sinh viên qua tối đa 8 học kỳ.
* **Loại bài toán:** 
  * **Khai phá dữ liệu (Data Mining):** Khám phá tri thức, phân cụm sinh viên và tìm luật kết hợp các yếu tố rủi ro.
  * **Học máy (Machine Learning):** Phân loại nhị phân (Binary Classification) cảnh báo sớm nguy cơ bỏ học ở học kỳ kế tiếp.

---

## 2. BỐI CẢNH VÀ Ý TƯỞNG CỐT LÕI

### 2.1. Vấn đề thực tiễn (Problem Statement)
* Tỷ lệ sinh viên bỏ học gây tổn thất lớn về tài chính cho nhà trường, ảnh hưởng tiêu cực đến tương lai người học và chỉ số duy trì học tập (retention rate) của cơ sở giáo dục.
* Các phương pháp truyền thống thường phát hiện quá muộn (khi sinh viên đã nợ môn quá nhiều hoặc bị buộc thôi học).
* **Mục tiêu của dự án:** Xây dựng **Hệ thống Cảnh báo Sớm (Early Warning System - EWS)** giúp nhà trường can thiệp chủ động (proactive intervention) ngay trong học kỳ hiện tại trước khi sinh viên quyết định dừng học ở học kỳ tiếp theo.

### 2.2. Điểm độc đáo: Bản chất dữ liệu theo chiều dọc (Longitudinal Trajectory)
* Không đánh giá sinh viên tại một thời điểm tĩnh (Snapshot).
* Theo dõi **quỹ đạo thay đổi** (Trajectory) qua các học kỳ:
  * Sự sụt giảm GPA theo thời gian ($\Delta \text{GPA} = \text{GPA}_t - \text{GPA}_{t-1}$).
  * Mức độ sụt giảm chuyên cần và tương tác LMS.
  * Sự gia tăng áp lực tài chính và số giờ làm thêm.

---

## 3. TỪ ĐIỂN VÀ CẤU TRÚC DỮ LIỆU (DATA DICTIONARY)

Dataset gồm **22 thuộc tính**, được chia thành 5 nhóm thông tin:

| STT | Tên thuộc tính | Ý nghĩa nghiệp vụ | Phân loại |
| :---: | :--- | :--- | :--- |
| **I** | **Định danh & Nhân khẩu học** | | |
| 1 | `Student_ID` | Mã định danh duy nhất của sinh viên | Categorical / ID |
| 2 | `Age` | Tuổi sinh viên | Numerical |
| 3 | `Gender` | Giới tính (Male / Female) | Categorical |
| 4 | `First_Generation` | Thế hệ đầu tiên trong gia đình học đại học (0/1) | Binary |
| 5 | `Household_Size` | Số nhân khẩu trong gia đình | Numerical |
| 6 | `Housing_Status` | Tình trạng cư trú (On-Campus / Off-Campus) | Categorical |
| **II**| **Kinh tế & Áp lực tài chính** | | |
| 7 | `Family_Income` | Thu nhập gia đình hàng năm (có giá trị khuyết thiếu) | Numerical |
| 8 | `Scholarship` | Có học bổng hay không (0/1) | Binary |
| 9 | `Tuition_Base` | Mức học phí cơ sở | Numerical |
| 10 | `Work_Hours` | Số giờ làm thêm mỗi tuần | Numerical |
| 11 | `Emergency_Expense` | Chi phí phát sinh khẩn cấp | Numerical |
| 12 | `Financial_Stress` | Mức độ áp lực tài chính tự đánh giá (thang điểm 1 - 5) | Numerical |
| **III**| **Hành vi & Tương tác học tập** | | |
| 13 | `Semester` | Học kỳ thứ mấy (từ 1 đến 8) | Ordinal |
| 14 | `Course_Load` | Số tín chỉ đăng ký trong học kỳ | Numerical |
| 15 | `Attendance` | Tỷ lệ chuyên cần (%) | Numerical |
| 16 | `LMS_Logins` | Số lần đăng nhập hệ thống học tập trực tuyến LMS | Numerical |
| 17 | `Advising_Visits` | Số lần gặp cố vấn học tập | Numerical |
| **IV** | **Kết quả học tập** | | |
| 18 | `Sem_GPA` | Điểm trung bình học kỳ | Numerical |
| 19 | `Failed_Courses` | Số môn học bị trượt trong học kỳ | Numerical |
| **V** | **Nhãn mục tiêu & Trạng thái** | | |
| 20 | `Target_Dropout_Next_Sem` | **Biến mục tiêu chính**: Bỏ học ở học kỳ kế tiếp hay không (0 = Ở lại, 1 = Bỏ học) | **Target (Binary)** |
| 21 | `End_of_Semester_Status` | Trạng thái cuối học kỳ (Enrolled / Dropped / Graduated) | Categorical |
| 22 | `Censored` | Bản ghi bị kiểm duyệt (thuật ngữ Survival Analysis) | Binary |

---

## 4. QUY TRÌNH THỰC HIỆN TOÀN DIỆN (PIPELINE)

```
       academic_survival_longitudinal.csv
                       │
                       ▼
┌──────────────────────────────────────────────┐
│  BƯỚC 1: TIỀN XỬ LÝ & LÀM SẠCH DỮ LIỆU       │
│  - Xử lý giá trị khuyết (Family_Income)      │
│  - Xử lý kiểu dữ liệu, định dạng             │
│  - Kiểm tra và xử lý ngoại lai (Outliers)    │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│  BƯỚC 2: KHAI PHÁ DỮ LIỆU DẪN ĐƯỜNG (EDA)    │
│  - Phân tích tương quan (Correlation Matrix) │
│  - Khảo sát biến động theo học kỳ (Trends)   │
│  - Phân tích tỷ lệ mất cân bằng nhãn         │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│  BƯỚC 3: TRÍCH XUẤT ĐẶC TRƯNG NÂNG CAO       │
│  (Longitudinal Feature Engineering)          │
│  - Delta GPA: GPA(t) - GPA(t-1)              │
│  - Delta Attendance: Biến động chuyên cần    │
│  - Cumulative Failed: Tích lũy môn nợ        │
│  - Rolling Average: Điểm trung bình trượt    │
└──────────────────────┬───────────────────────┘
                       │
       ┌───────────────┴───────────────┐
       ▼                               ▼
┌─────────────────────────┐     ┌─────────────────────────┐
│ BƯỚC 4A: DATA MINING    │     │ BƯỚC 4B: MACHINE LEARNING│
│ (Khám phá tri thức)     │     │ (Dự báo nguy cơ)        │
│ - Phân cụm sinh viên    │     │ - Logistic Regression   │
│   (K-Means / DBSCAN)    │     │ - Decision Tree         │
│ - Khai phá luật kết hợp │     │ - Random Forest         │
│   (Apriori / FP-Growth) │     │ - XGBoost / LightGBM    │
└──────────────┬──────────┘     └────────────┬────────────┘
               └───────────────┬─────────────┘
                               ▼
┌──────────────────────────────────────────────┐
│  BƯỚC 5: ĐÁNH GIÁ & GIẢI THÍCH MÔ HÌNH       │
│  - Chia tập: GroupKFold theo Student_ID      │
│  - Đánh giá: Recall, PR-AUC, F1-Score, ROC   │
│  - Giải thích mô hình: SHAP Values / XAI     │
└──────────────────────────────────────────────┘
```

---

## 5. CÁC NỘI DUNG KỸ THUẬT QUAN TRỌNG

### 5.1. Kỹ thuật chống rò rỉ dữ liệu (Data Leakage Prevention)
* **Quy tắc bắt buộc:** Một sinh viên xuất hiện ở nhiều học kỳ. Không được dùng `train_test_split` ngẫu nhiên từng dòng.
* **Giải pháp:** Sử dụng `GroupKFold` hoặc `GroupShuffleSplit` theo cột `Student_ID`. Toàn bộ lịch sử học tập của một sinh viên chỉ được nằm hoàn toàn ở tập Train hoặc hoàn toàn ở tập Test.

### 5.2. Kỹ thuật trích xuất đặc trưng theo chuỗi thời gian (Feature Engineering)
Tận dụng lịch sử các kỳ trước để tạo ra các thuộc tính có tính dự báo mạnh nhất:
1. `Delta_Sem_GPA = Sem_GPA - Sem_GPA_prev` (Mức sụt giảm điểm kỳ này so với kỳ trước).
2. `Delta_Attendance = Attendance - Attendance_prev` (Mức độ suy giảm chuyên cần).
3. `Cumulative_Failed_Courses` (Tổng số môn nợ tích lũy đến kỳ hiện tại).
4. `Financial_Burden_Index` = `Work_Hours * Financial_Stress / (Family_Income + 1)` (Chỉ số gánh nặng kinh tế).

### 5.3. Tiêu chí đánh giá mô hình (Evaluation Metrics)
* Vì tỷ lệ sinh viên bỏ học là lớp thiểu số (Imbalance Class), độ chính xác tổng thể (`Accuracy`) không phản ánh đúng chất lượng mô hình.
* Các tiêu chí trọng tâm:
  * **Recall (Độ nhạy):** Quan trọng nhất – tránh bỏ sót sinh viên có nguy cơ thực sự.
  * **Precision (Độ chuẩn xác):** Tránh báo động giả quá nhiều làm lãng phí nguồn lực hỗ trợ của trường.
  * **F1-Score & PR-AUC:** Cân bằng giữa Precision và Recall trên bài toán mất cân bằng.

---

## 6. KỊCH BẢN BẢO VỆ ĐỀ TÀI TRƯỚC GIẢNG VIÊN

| Câu hỏi của Thầy/Cô | Câu trả lời trọng tâm cần trình bày |
| :--- | :--- |
| **1. Tại sao nhóm lại chọn đề tài này?** | Đề tài giải quyết bài toán thực tế của các trường đại học: Xây dựng hệ thống cảnh báo sớm (Early Warning System) để can thiệp kịp thời, cải thiện tỷ lệ giữ chân sinh viên. |
| **2. Điểm khác biệt lớn nhất của tập dữ liệu này là gì?** | Đây là dữ liệu theo chiều dọc (Longitudinal Data), cho phép theo dõi toàn bộ quỹ đạo biến thiên (Trajectory) của từng sinh viên qua tối đa 8 học kỳ, thay vì chỉ là dữ liệu tĩnh tại một thời điểm. |
| **3. Nhóm phân định phần Data Mining và phần Machine Learning như thế nào?** | Data Mining giúp **mô tả và tìm hiểu tri thức ẩn** (phân cụm sinh viên, tìm luật kết hợp giữa làm thêm - tài chính - điểm số). Machine Learning giúp **dự báo định lượng xác suất** sinh viên bỏ học ở kỳ tiếp theo. |
| **4. Làm sao nhóm đảm bảo mô hình không bị Overfitting do dữ liệu lặp lại?** | Nhóm chia tập kiểm thử bằng chiến lược `GroupKFold` theo `Student_ID`, đảm bảo lịch sử của cùng một sinh viên không bị rò rỉ đồng thời giữa tập huấn luyện và tập kiểm thử. |

---

## 7. CẤU TRÚC THƯ MỤC DỰ KIẾN CỦA DỰ ÁN

```text
Tich_Hop_pTich_DlieuLon/
│
├── academic_survival_longitudinal.csv   # Dữ liệu gốc
├── PROJECT_OVERVIEW.md                  # Tài liệu tổng quan đề tài
│
├── notebooks/
│   ├── 01_data_cleaning_eda.ipynb       # Làm sạch dữ liệu & Phân tích khám phá
│   ├── 02_feature_engineering.ipynb     # Trích xuất đặc trưng chuỗi thời gian (Delta, Cumulative)
│   ├── 03_data_mining_patterns.ipynb    # Phân cụm (Clustering) & Luật kết hợp (Apriori)
│   └── 04_machine_learning_models.ipynb # Huấn luyện, so sánh mô hình & Giải thích SHAP
│
└── reports/
    └── final_report.docx / .pdf         # Báo cáo tổng kết môn học
```
