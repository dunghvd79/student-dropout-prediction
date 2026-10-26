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
* **Kết quả kiểm chứng** (chi tiết ở [B11](QUY_TRINH_DU_AN/GIAI_DOAN_D_HOC_MAY/B11_HUAN_LUYEN_TINH_CHINH.md)):
  * EDA cho thấy nhóm sắp bỏ học **sa sút rõ** trong 4 kỳ trước khi bỏ (GPA 2,74 → 2,35; áp lực tài chính 2,94 → 3,87).
  * Tuy nhiên, thí nghiệm ablation (3 seed × 5 fold) cho thấy thêm 23 đặc trưng chiều dọc **không cải thiện** dự báo: PR-AUC LogReg 0,4090 → 0,4098, khoảng tin cậy chứa 0.
  * Riêng các đặc trưng chiều dọc vẫn đạt PR-AUC 0,354 (so với mốc 0,10), tức là **có thông tin nhưng trùng với trạng thái hiện tại**: sự sa sút đã thể hiện sẵn trong GPA, số môn nợ, áp lực tài chính của kỳ đang xét.
  * ⇒ Giá trị của dữ liệu theo chiều dọc trong đề tài nằm ở **mô tả, khai phá và giải thích** (EDA, luật `GPA thấp + GPA tụt → 48% bỏ học`, lý do cảnh báo cho cố vấn). Đây là một **kết quả âm có đối chứng**, không phải giả định.

---

## 3. TỪ ĐIỂN VÀ CẤU TRÚC DỮ LIỆU (DATA DICTIONARY)

Dataset gồm **22 thuộc tính**, được chia thành 5 nhóm thông tin:

| STT | Tên thuộc tính | Ý nghĩa nghiệp vụ | Phân loại |
| :---: | :--- | :--- | :--- |
| **I** | **Định danh & Nhân khẩu học** | | |
| 1 | `Student_ID` | Mã định danh duy nhất của sinh viên | Categorical / ID |
| 2 | `Age` | Tuổi sinh viên | Numerical |
| 3 | `Gender` | Giới tính (Male / Female / Other / Prefer not to say; dữ liệu thô có 8 cách ghi, cần chuẩn hóa) | Categorical |
| 4 | `First_Generation` | Thế hệ đầu tiên trong gia đình học đại học (0/1) | Binary |
| 5 | `Household_Size` | Số nhân khẩu trong gia đình (1 - 6) | Numerical |
| 6 | `Housing_Status` | Tình trạng cư trú (On-Campus / Off-Campus / With Parents) | Categorical |
| **II**| **Kinh tế & Áp lực tài chính** | | |
| 7 | `Family_Income` | Thu nhập gia đình hàng năm, không đổi theo kỳ (thiếu ~4,5% số dòng) | Numerical |
| 8 | `Scholarship` | Có học bổng hay không (0/1) | Binary |
| 9 | `Tuition_Base` | Mức học phí cơ sở | Numerical |
| 10 | `Work_Hours` | Số giờ làm thêm mỗi tuần | Numerical |
| 11 | `Emergency_Expense` | Chi phí phát sinh khẩn cấp trong học kỳ (thay đổi theo kỳ) | Numerical |
| 12 | `Financial_Stress` | Chỉ số áp lực tài chính (liên tục, từ 1,0; trung vị 2,1, lệch phải, tối đa 18,6) | Numerical |
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
| 20 | `Target_Dropout_Next_Sem` | **Biến mục tiêu chính**: Bỏ học ở học kỳ kế tiếp hay không (0 = Ở lại, 1 = Bỏ học); lớp 1 chiếm ~8,7% | **Target (Binary)** |
| 21 | `End_of_Semester_Status` | Trạng thái cuối học kỳ (Enrolled / Dropped_Out / Graduated); trùng hoàn toàn với nhãn nên **không được dùng làm đặc trưng** | Categorical |
| 22 | `Censored` | = 1 ở kỳ cuối cùng quan sát được của sinh viên chưa bỏ học cũng chưa tốt nghiệp (dữ liệu bị cắt, thuật ngữ Survival Analysis) | Binary |

---

## 4. QUY TRÌNH THỰC HIỆN TOÀN DIỆN (PIPELINE)

```
       academic_survival_longitudinal.csv
                       │
                       ▼
┌──────────────────────────────────────────────┐
│  BƯỚC 1: TIỀN XỬ LÝ & LÀM SẠCH DỮ LIỆU       │
│  - Khuyết thiếu: Family_Income, LMS_Logins   │
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
Tận dụng lịch sử các kỳ trước để tạo ra các thuộc tính mô tả xu hướng (7/10 đặc trưng có tín hiệu đơn biến mạnh nhất là đặc trưng chiều dọc, nhưng không tăng độ chính xác khi đã có giá trị hiện tại; xem mục 2.2):
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
| **2. Điểm khác biệt lớn nhất của tập dữ liệu này là gì?** | Đây là dữ liệu theo chiều dọc (Longitudinal Data), cho phép theo dõi toàn bộ quỹ đạo biến thiên (Trajectory) của từng sinh viên qua tối đa 8 học kỳ. Nhóm **không mặc định** quỹ đạo giúp dự báo tốt hơn mà **kiểm chứng bằng ablation**: quỹ đạo không tăng PR-AUC (0,4090 so với 0,4098) vì thông tin đã có trong trạng thái hiện tại, nhưng rất có giá trị để mô tả xu hướng sa sút và giải thích lý do cảnh báo. |
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

> Cấu trúc đầy đủ (gồm `src/`, `config/`, `sql/`, `app/`, `docker-compose.yml`) và vai trò của từng file theo từng bước xem tại [`QUY_TRINH_DU_AN/README.md`](./QUY_TRINH_DU_AN/README.md), mục 6.
