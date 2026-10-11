# BƯỚC 6. PHÂN TÍCH KHÁM PHÁ DỮ LIỆU (EDA)
**Giai đoạn C – Phân tích & Khai phá** · [← Giai đoạn C](./README.md) · [Bước 7 →](./B07_TRICH_XUAT_DAC_TRUNG.md)

---

## 1. Nhiệm vụ
Hiểu dữ liệu và tìm các yếu tố liên quan đến bỏ học, làm **cơ sở để thiết kế đặc trưng** (B7) và **diễn giải kết quả** mô hình.

---

## 2. Cơ sở lý thuyết

### 2.1. EDA là gì?
**Exploratory Data Analysis** (John Tukey, 1977) là quá trình dùng thống kê mô tả và trực quan hóa để **khám phá cấu trúc dữ liệu, phát hiện mẫu, bất thường và hình thành giả thuyết** trước khi xây mô hình. EDA trả lời câu hỏi "dữ liệu đang nói gì?", chứ không chứng minh giả thuyết.

### 2.2. Ba cấp độ phân tích

| Cấp độ | Mục đích | Công cụ |
|---|---|---|
| **Đơn biến** (univariate) | Phân phối của từng biến: trung tâm, độ phân tán, độ lệch | Histogram, boxplot, bảng tần suất; mean, median, std, phân vị, skewness |
| **Hai biến** (bivariate) | Quan hệ giữa một biến và nhãn / biến khác | Tỷ lệ bỏ học theo nhóm, boxplot theo nhãn, scatter, hệ số tương quan |
| **Đa biến** (multivariate) | Quan hệ đồng thời nhiều biến | Ma trận tương quan, pair plot, phân tích theo nhiều chiều |

### 2.3. Hệ số tương quan
* **Pearson** đo quan hệ **tuyến tính**, nhạy với ngoại lai:
  $$r = \frac{\sum (x_i - \bar{x})(y_i - \bar{y})}{\sqrt{\sum (x_i - \bar{x})^2}\sqrt{\sum (y_i - \bar{y})^2}}$$
* **Spearman** là Pearson tính trên **thứ hạng**; đo quan hệ **đơn điệu** (không cần tuyến tính) và bền với ngoại lai. Phù hợp hơn cho các biến lệch như `Family_Income`, `Financial_Stress`.
* Với nhãn nhị phân, so sánh **tỷ lệ bỏ học theo nhóm / theo khoảng giá trị** thường dễ hiểu hơn hệ số tương quan.

### 2.4. Tương quan không phải là nhân quả
* EDA chỉ cho thấy **sự liên quan**. Ví dụ: "sinh viên gặp cố vấn nhiều có tỷ lệ bỏ học cao" **không** có nghĩa là gặp cố vấn gây ra bỏ học; nhiều khả năng sinh viên **đang gặp khó khăn** mới đi gặp cố vấn (nhân quả ngược).
* **Biến gây nhiễu (confounder):** một biến thứ ba ảnh hưởng cả hai biến đang xét.
* **Nghịch lý Simpson:** xu hướng xuất hiện trong từng nhóm con có thể **đảo ngược** khi gộp tất cả lại. Vì vậy cần phân tích theo các nhóm quan trọng (theo học kỳ, theo học bổng).

### 2.5. Phân tích quỹ đạo (Trajectory Analysis)
* Với dữ liệu theo chiều dọc, vẽ **giá trị trung bình của một biến theo học kỳ**, tách theo kết cục (sắp bỏ học / ở lại).
* Nếu hai đường **tách dần** trước thời điểm bỏ học (ví dụ GPA của nhóm sắp bỏ học giảm dần), đó là bằng chứng rằng **xu hướng thay đổi** (Delta) có sức dự báo. Đây là căn cứ cho B7.

### 2.6. Đường cong sống sót Kaplan–Meier (tùy chọn)
* Ước lượng xác suất **còn theo học sau kỳ *t*** khi có dữ liệu bị cắt:
  $$\hat{S}(t) = \prod_{t_i \le t}\left(1 - \frac{d_i}{n_i}\right)$$
  trong đó $d_i$ là số sinh viên bỏ học tại kỳ $t_i$, $n_i$ là số sinh viên còn "trong diện theo dõi" ngay trước $t_i$.
* Điểm mạnh: **dùng đúng thông tin của dữ liệu bị cắt**. Sinh viên bị cắt vẫn đóng góp vào $n_i$ cho đến kỳ cuối họ được quan sát.

### 2.7. Mất cân bằng lớp
Đo tỷ lệ lớp dương ngay từ đầu, vì nó quyết định chỉ số đánh giá (PR-AUC), chiến lược chia tập (stratified) và kỹ thuật cân bằng (B10).

---

## 3. Input
Bảng ghép từ `load_analytic_table()` (79.239 dòng). Các tỷ lệ bỏ học được tính trên **tập có nhãn** (`Censored = 0`, 68.124 dòng).

---

## 4. Biến đổi (các phân tích cần làm)
1. **Mất cân bằng nhãn:** 8,7% toàn bộ; 10,2% trên tập có nhãn.
2. **Phân bố số kỳ theo dõi:** 3.404 sinh viên chỉ có 1 kỳ; 2.172 sinh viên đủ 8 kỳ.
3. **Tỷ lệ bỏ học theo học kỳ:** kỳ 1 ≈ 6,7%; kỳ 2 – 8 ≈ 9 – 10%.
4. **Tỷ lệ bỏ học theo nhóm** (đã đo):
   * `First_Generation`: 13,6% (có) so với 8,4% (không).
   * `Scholarship`: 7,3% (có) so với 11,2% (không).
   * `Housing_Status`: With Parents 8,8%; On-Campus 10,7%; Off-Campus 10,8%.
   * `Financial_Stress`: tăng đều từ 4,6% (mức 1) lên 47% (mức ≥ 10).
5. **Phân phối** `Sem_GPA`, `Attendance`, `Work_Hours`, `Failed_Courses`, `LMS_Logins` tách theo nhãn (histogram, boxplot).
6. **Ma trận tương quan** Spearman giữa các biến số và nhãn; phát hiện cặp biến tương quan rất cao (đa cộng tuyến).
7. **Quỹ đạo theo thời gian:** trung bình `Sem_GPA`, `Attendance`, `Financial_Stress` theo học kỳ, tách nhóm sắp bỏ học / ở lại.
8. *(Tùy chọn)* **Kaplan–Meier** tổng thể và tách theo `Scholarship`, `First_Generation`.

---

## 5. Output
* Thư mục `reports/figures/eda_*.png`.
* Danh sách **5 – 10 insight**, ví dụ: "Áp lực tài chính và thế hệ đầu là hai yếu tố gắn với tỷ lệ bỏ học cao".
* Danh sách giả thuyết đặc trưng cần tạo ở B7.

## 6. Công cụ / File thực hiện
Notebook `01_data_cleaning_eda.ipynb` (phần 2) – `pandas`, `seaborn`, `plotly`, `lifelines` (Kaplan–Meier).

## 7. Tiêu chí hoàn thành
- [ ] Mỗi nhóm biến (học tập, hành vi, tài chính, nhân khẩu) có ít nhất 1 biểu đồ và 1 nhận xét.
- [ ] Có ít nhất 1 biểu đồ quỹ đạo chứng minh giá trị của dữ liệu theo chiều dọc.

---

## 8. Câu hỏi bảo vệ thường gặp
**Hỏi:** Sinh viên có học bổng ít bỏ học hơn. Vậy cấp học bổng sẽ giảm bỏ học?  
**Đáp:** EDA chỉ cho thấy liên quan, chưa chứng minh nhân quả. Sinh viên có học bổng thường cũng học tốt hơn (biến gây nhiễu). Muốn kết luận nhân quả cần thiết kế thực nghiệm hoặc phương pháp suy luận nhân quả.

**Hỏi:** Vì sao dùng Spearman thay vì Pearson?  
**Đáp:** Nhiều biến lệch mạnh và có giá trị cực đoan (`Family_Income`, `Financial_Stress`). Spearman dựa trên thứ hạng nên bền hơn và bắt được quan hệ đơn điệu không tuyến tính.
