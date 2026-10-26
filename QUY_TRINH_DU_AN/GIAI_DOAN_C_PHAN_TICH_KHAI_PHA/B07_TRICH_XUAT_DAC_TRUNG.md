# BƯỚC 7. TRÍCH XUẤT ĐẶC TRƯNG THEO CHIỀU DỌC (LONGITUDINAL FEATURE ENGINEERING)
**Giai đoạn C – Phân tích & Khai phá** · [← Bước 6](./B06_PHAN_TICH_KHAM_PHA_EDA.md) · [Bước 8 →](./B08_KHAI_PHA_DU_LIEU.md)

---

## 1. Nhiệm vụ
Biến lịch sử nhiều kỳ của mỗi sinh viên thành các đặc trưng thể hiện **xu hướng** và **tích lũy**, để kiểm tra **giả thuyết** của đề tài: nhìn theo quỹ đạo giúp dự báo tốt hơn cách nhìn "ảnh chụp tĩnh" (snapshot). Kết quả kiểm chứng ở [B11](../GIAI_DOAN_D_HOC_MAY/B11_HUAN_LUYEN_TINH_CHINH.md): giả thuyết **không đúng với bộ dữ liệu này** về độ chính xác, nhưng các đặc trưng vẫn có giá trị mô tả và giải thích.

---

## 2. Cơ sở lý thuyết

### 2.1. Feature Engineering là gì?
Là quá trình dùng **hiểu biết nghiệp vụ** để tạo biến mới từ dữ liệu thô, giúp mô hình học dễ hơn. Câu nói quen thuộc: *"Dữ liệu và đặc trưng quyết định giới hạn trên của mô hình; thuật toán chỉ tiến gần tới giới hạn đó."*

### 2.2. Snapshot và Trajectory
* **Snapshot:** chỉ nhìn GPA kỳ này = 2,3. Hai sinh viên cùng GPA 2,3 trông như nhau.
* **Trajectory:** sinh viên A đi từ 3,2 → 2,3 (**sa sút mạnh**), sinh viên B đi từ 1,9 → 2,3 (**đang tiến bộ**). Rủi ro khác hẳn nhau.
* Đặc trưng theo chiều dọc mã hóa được **hướng đi** này.

### 2.3. Các họ đặc trưng cho dữ liệu bảng (panel data)

| Họ | Định nghĩa | Công thức (cho sinh viên *i*, kỳ *t*) |
|---|---|---|
| **Lag (trễ)** | Giá trị kỳ trước | $x_{i,t-1}$ |
| **Difference (sai phân / Delta)** | Mức thay đổi so với kỳ trước | $\Delta x_{i,t} = x_{i,t} - x_{i,t-1}$ |
| **Cumulative (tích lũy)** | Tổng từ đầu đến kỳ *t* | $\sum_{k=1}^{t} x_{i,k}$ |
| **Expanding mean** | Trung bình từ đầu đến *t* | $\frac{1}{t}\sum_{k=1}^{t} x_{i,k}$ |
| **Rolling window (trượt)** | Trung bình *w* kỳ gần nhất | $\frac{1}{w}\sum_{k=t-w+1}^{t} x_{i,k}$ |
| **Slope (độ dốc)** | Tốc độ thay đổi theo thời gian (hồi quy OLS) | $\beta = \frac{\sum (k-\bar{k})(x_k-\bar{x})}{\sum (k-\bar{k})^2}$ |
| **Trọng số** | Trung bình có trọng số | CGPA $= \frac{\sum GPA_k \cdot Load_k}{\sum Load_k}$ |

### 2.4. Tính đúng tại thời điểm (Point-in-time correctness)
* Đặc trưng tại kỳ *t* chỉ được dùng **thông tin có thật tại cuối kỳ *t***. Nếu dùng dữ liệu kỳ *t+1* (ví dụ cửa sổ trượt trung tâm, hoặc trung bình của **toàn bộ** lịch sử sinh viên), mô hình sẽ "nhìn trước tương lai". Kết quả kiểm thử khi đó đẹp giả tạo nhưng không dùng được khi triển khai.
* Trong Pandas: chỉ dùng `groupby('Student_ID')` kết hợp `shift(1)`, `cumsum()`, `expanding()`, `rolling()` (cửa sổ lùi). **Không** dùng `transform('mean')` trên toàn nhóm, **không** dùng `shift(-1)`.

### 2.5. Vì sao làm Feature Engineering trước khi chia tập vẫn an toàn?
Mỗi đặc trưng chỉ dùng dữ liệu **của chính sinh viên đó** và **ở quá khứ**, không dùng thống kê của các sinh viên khác. Vì vậy dù làm trước khi chia Train/Test cũng **không có thông tin nào lọt từ Test sang Train**. Ngược lại, các thao tác như "chuẩn hóa theo mean toàn bộ" thì phải để sau khi chia (B10).

### 2.6. Đặc trưng tỷ lệ theo nghiệp vụ
Kết hợp các biến thô thành các chỉ số có ý nghĩa, ví dụ gánh nặng tài chính = giờ làm thêm × áp lực / thu nhập. Mô hình cây có thể tự học tương tác, nhưng đặc trưng nghiệp vụ giúp học nhanh hơn, ổn định hơn và **dễ giải thích hơn** (SHAP ở B13).

### 2.7. Xử lý kỳ đầu tiên
Kỳ 1 không có kỳ trước, nên Lag/Delta không xác định. Có ba lựa chọn: để `NaN` (XGBoost/LightGBM tự học hướng rẽ cho giá trị thiếu), điền 0 (không thay đổi), hoặc thêm cờ `Is_First_Semester`. Nhóm **giữ `NaN` + cờ**, và điền 0 cho mô hình tuyến tính trong Pipeline.

---

## 3. Input
`clean_semesters.parquet` (79.239 × 24), đã sắp xếp theo `Student_ID`, `Semester`.

---

## 4. Biến đổi (danh sách đặc trưng)

| Nhóm | Đặc trưng | Công thức | Ý nghĩa |
|---|---|---|---|
| Lag | `GPA_prev`, `Attendance_prev`, `LMS_prev`, `Stress_prev`, `Work_prev` | `groupby.shift(1)` | Giá trị kỳ trước |
| Delta | `Delta_GPA` | `Sem_GPA − GPA_prev` | Sụt giảm điểm |
| | `Delta_Attendance` | `Attendance − Attendance_prev` | Sụt giảm chuyên cần |
| | `Delta_LMS` | `LMS_Logins − LMS_prev` | Giảm tương tác trực tuyến |
| | `Delta_Stress`, `Delta_Work_Hours` | tương tự | Áp lực / giờ làm thêm tăng |
| Tích lũy | `Cum_Failed_Courses` | `cumsum(Failed_Courses)` | Tổng số môn nợ |
| | `Cum_Advising_Visits` | `cumsum(Advising_Visits)` | Mức độ được hỗ trợ |
| | `Cum_Emergency_Expense`, `Num_Emergency_Sems` | `cumsum` | Số lần gặp biến cố tài chính |
| | `CGPA` | `cumsum(GPA × Course_Load) / cumsum(Course_Load)` | Điểm trung bình tích lũy |
| Rolling | `GPA_Roll3`, `Attendance_Roll3` | `rolling(3, min_periods=1).mean()` | Xu hướng ngắn hạn |
| | `GPA_Slope` | Độ dốc OLS của GPA theo kỳ (≥ 2 kỳ, `expanding`) | Tốc độ sa sút |
| Tài chính | `Financial_Burden_Index` | `Work_Hours × Financial_Stress / (Family_Income + 1)` | Gánh nặng kinh tế |
| | `Tuition_to_Income` | `Tuition_Base / Family_Income` | Học phí so với thu nhập |
| | `Has_Emergency` | `Emergency_Expense > 0` | Có biến cố trong kỳ |
| Ngữ cảnh | `Is_First_Semester` | `Semester == 1` | Kỳ 1 không có lịch sử |
| | `Failed_Ratio` | `Failed_Courses / (Course_Load / 3)` | Tỷ lệ môn trượt (≈ 3 tín chỉ/môn) |

* Mã hóa phân loại (`Gender`, `Housing_Status`) để ở B10 (One-Hot trong Pipeline).
* Lưu danh sách đặc trưng cuối cùng vào `config/feature_spec.json`.

---

## 5. Output
* `data/features/feature_table.parquet` (79.239 × 47): khóa (`Student_ID`, `Semester`) + 43 đặc trưng + `Target_Dropout_Next_Sem` + `Censored` + `End_of_Semester_Status` (giữ lại để tách tập ở B9, **không** dùng làm đặc trưng).
* `config/feature_spec.json`: **43 đặc trưng = 20 gốc + 23 chiều dọc**, chia theo `numeric` / `binary` / `categorical`, kèm `baseline_features` và `longitudinal_features` để làm ablation ở B11. B11 (huấn luyện) và B14 (dự đoán) dùng **cùng một** danh sách.
* Notebook [`notebooks/02_feature_engineering.ipynb`](../../notebooks/02_feature_engineering.ipynb) + `reports/figures/feat_*.png`: kiểm tra tín hiệu của đặc trưng.

**Kết quả kiểm tra tín hiệu** (tập có nhãn):
* **7 / 10** đặc trưng mạnh nhất theo mutual information là đặc trưng chiều dọc (`GPA_Roll3`, `CGPA`, `Failed_Ratio`, `GPA_prev`, `Financial_Burden_Index`, `Stress_prev`, `GPA_Slope`).
* Quan hệ phi tuyến:
  * `Delta_GPA` có dạng **ngưỡng**: nhóm sụt mạnh nhất 19,5% so với ~9%.
  * `Delta_Stress` có dạng **chữ U**: ổn định 6,5%, tăng mạnh 15,9%, giảm mạnh 10,9%.
* `CGPA`: 21,7% → 3,1% theo ngũ phân vị. `Financial_Burden_Index`: 4,8% → 20,2%.
* Nhóm GPA trùng thông tin (ρ 0,92 – 0,98); nhóm biến cố tài chính gần như không có tín hiệu. Giá trị **thêm vào** của đặc trưng chiều dọc sẽ được đo bằng ablation ở B11.

## 6. Công cụ / File thực hiện
* `src/analysis/features.py`: chạy `python -m src.analysis.features`. `GPA_Slope` tính theo công thức OLS bằng tổng tích lũy (vector hóa, không lặp từng sinh viên); toàn bộ bước chạy khoảng 12 giây.
* `tests/test_features.py`: 6 unit test.
* `notebooks/02_feature_engineering.ipynb`: kiểm tra tín hiệu.

## 7. Tiêu chí hoàn thành (đã kiểm tra 2026-10-26)
- [x] Unit test trên `STU_00001` (dữ liệu thật): `Delta_GPA` kỳ 2 = **−0,12**; `Cum_Failed_Courses` kỳ 4 = **5**; `CGPA`, `GPA_Roll3` đúng; `GPA_Slope` khớp `numpy.polyfit`.
- [x] Test "không nhìn tương lai": xóa kỳ cuối của mọi sinh viên rồi tính lại, đặc trưng các kỳ trước **không đổi**. Thêm: kỳ 1 không mượn dữ liệu của sinh viên khác; thứ tự dòng đầu vào không ảnh hưởng kết quả.
- [x] Chạy 2 lần cho file giống hệt (MD5 `4212ecc9f9502ec70761510758b5c750`).

> **Phát hiện trong lúc làm B7:** `Delta_Attendance` ban đầu dao động −96 đến +97 điểm. Truy ngược lại, B4 đã clip mã lỗi `Attendance = −2` về 0%, tạo cú sụt giả. Đã sửa B4: giá trị âm → thiếu, điền bằng kỳ trước. Sau khi sửa, `Delta_Attendance` nằm trong khoảng −28,8 đến +27,0.

---

## 8. Câu hỏi bảo vệ thường gặp
**Hỏi:** Điểm mới của đề tài so với dự đoán bỏ học thông thường là gì?  
**Đáp:** Nhóm xây dựng đặc trưng **quỹ đạo** (sụt giảm GPA, nợ môn tích lũy, tốc độ sa sút…) và **kiểm chứng** giá trị của chúng bằng ablation ở B11 (3 seed × 5 fold). Kết quả: chúng không tăng PR-AUC (0,4090 so với 0,4098) vì thông tin đã có trong trạng thái hiện tại; riêng chúng vẫn đạt 0,354. Điểm mới là nhóm **đo** giá trị của dữ liệu chiều dọc thay vì giả định, và dùng chúng cho mô tả / giải thích.

**Hỏi:** Làm sao đảm bảo không dùng dữ liệu tương lai?  
**Đáp:** Chỉ dùng `shift`, `cumsum`, `expanding`, `rolling` lùi trong từng sinh viên, và có unit test "xóa kỳ cuối, đặc trưng kỳ trước không đổi".
