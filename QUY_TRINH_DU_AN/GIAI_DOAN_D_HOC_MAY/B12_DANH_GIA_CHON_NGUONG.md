# BƯỚC 12. ĐÁNH GIÁ TRÊN TẬP TEST, CHỌN NGƯỠNG & ĐĂNG KÝ MÔ HÌNH
**Giai đoạn D – Học máy** · [← Bước 11](./B11_HUAN_LUYEN_TINH_CHINH.md) · [Bước 13 →](./B13_GIAI_THICH_MO_HINH_SHAP.md)

---

## 1. Nhiệm vụ
Đo hiệu năng **khách quan** trên tập Test chưa từng dùng; biến xác suất thành **mức rủi ro có ý nghĩa**; đưa mô hình vào Production.

---

## 2. Cơ sở lý thuyết

### 2.1. Đường cong PR và ROC
* **Đường ROC:** trục tung TPR (= Recall), trục hoành FPR = $\frac{FP}{FP+TN}$, khi quét ngưỡng từ 1 về 0. **ROC-AUC** = xác suất một mẫu dương ngẫu nhiên được chấm điểm cao hơn một mẫu âm ngẫu nhiên. Mốc ngẫu nhiên là 0,5.
* **Đường Precision–Recall:** trục tung Precision, trục hoành Recall. **PR-AUC / Average Precision (AP)** = $\sum_n (R_n - R_{n-1}) P_n$. Mốc ngẫu nhiên = **tỷ lệ lớp dương** (≈ 0,10).
* Khi lớp dương hiếm, PR-AUC **nhạy hơn** với chất lượng trên lớp dương, nên là chỉ số chính.

### 2.2. Chọn ngưỡng quyết định
* Ngưỡng mặc định 0,5 **không tối ưu** khi lớp mất cân bằng và chi phí lỗi không đối xứng.
* **Các cách chọn:**
  * Đạt Recall mục tiêu (≥ 0,80) với Precision cao nhất có thể. **Nhóm dùng cách này.**
  * Tối đa F1 (hoặc $F_\beta$ với β > 1 để ưu tiên Recall).
  * Tối thiểu chi phí kỳ vọng: $C_{FN}\cdot FN + C_{FP}\cdot FP$.
  * Theo năng lực can thiệp: chọn top-K sinh viên mà phòng CTSV có thể hỗ trợ.
* **Chọn ngưỡng trên dự đoán OOF của Train**, không phải trên Test. Chọn trên Test là "dùng Test để tinh chỉnh", khiến kết quả Test lạc quan giả tạo.

### 2.3. Hiệu chỉnh xác suất (Calibration)
* Mô hình **được hiệu chỉnh tốt** nếu trong các sinh viên được dự đoán 0,6 thì thực tế có ~60% bỏ học.
* Boosting, class weighting, SMOTE thường làm xác suất **lệch** (thường bị đẩy lên cao). Muốn diễn giải mức rủi ro Thấp/TB/Cao theo xác suất thì phải hiệu chỉnh.

| Phương pháp | Cách làm | Khi nào dùng |
|---|---|---|
| **Platt scaling** | Khớp một hàm sigmoid trên điểm số | Dữ liệu ít, lệch dạng chữ S |
| **Isotonic regression** | Khớp một hàm đơn điệu không tham số | Dữ liệu đủ nhiều (dự án có > 50.000 dòng) |

* **Đánh giá:**
  * **Reliability diagram:** xác suất dự đoán trung bình so với tỷ lệ thực tế theo từng bin; lý tưởng là nằm trên đường chéo.
  * **Brier score:** $\frac{1}{N}\sum (p_i - y_i)^2$, càng nhỏ càng tốt.

### 2.4. Chỉ dùng tập Test một lần
Mỗi lần nhìn kết quả Test rồi quay lại sửa mô hình là một lần "rò" thông tin của Test vào quá trình phát triển. Nhóm **khóa** mọi lựa chọn (mô hình, tham số, ngưỡng) trước, rồi mới đánh giá Test **một lần duy nhất** và báo cáo trung thực con số đó.

### 2.5. Công bằng của mô hình (Fairness)
* Mô hình có thể hoạt động **kém đều** giữa các nhóm (giới tính, thế hệ đầu, nơi ở).
* **Equal opportunity:** Recall (TPR) nên xấp xỉ nhau giữa các nhóm. Nếu mô hình bỏ sót sinh viên thế hệ đầu nhiều hơn hẳn, nhóm này sẽ bị thiệt về cơ hội được hỗ trợ.
* Cũng cần xem hiệu năng **theo học kỳ**: kỳ 1 không có lịch sử nên thường khó dự đoán hơn.

### 2.6. Model Registry
* Kho quản lý **phiên bản mô hình** với các trạng thái: `None` → `Staging` (đang kiểm tra) → `Production` (đang phục vụ) → `Archived` (đã thay thế).
* Bước dự đoán (B14) luôn tải mô hình theo tên + trạng thái `Production`, nên thay mô hình **không phải sửa code**.

---

## 3. Input
Mô hình + tham số tốt nhất, dự đoán OOF (từ B11), `X_test, y_test`.

---

## 4. Biến đổi
1. **Calibration:** `CalibratedClassifierCV(method='isotonic')` với CV theo nhóm trên Train; vẽ reliability curve, tính Brier score trước/sau.
2. **Chọn ngưỡng trên OOF:** ngưỡng lớn nhất vẫn đạt **Recall ≥ 0,80**; ghi lại Precision tương ứng. Đối chiếu với các mốc rủi ro: **Thấp** < 0,3 · **Trung bình** 0,3 – 0,6 · **Cao** ≥ 0,6. Nếu ngưỡng khác 0,3 thì cập nhật mốc "Trung bình" trong `settings.yaml`.
3. **Huấn luyện lại** trên toàn bộ Train với tham số tốt nhất.
4. **Đánh giá Test một lần:** PR-AUC, ROC-AUC, Recall, Precision, F1 tại ngưỡng; ma trận nhầm lẫn; đường PR, ROC.
5. **Phân tích lỗi & công bằng:** Recall theo học kỳ, `Gender`, `First_Generation`, `Housing_Status`; xem các ca bỏ sót (FN) điển hình.
6. **Đăng ký** `dropout_model` vào MLflow Model Registry, chuyển sang `Production` (phiên bản cũ sang `Archived`).

---

## 5. Output
* `reports/evaluation_report.md` + biểu đồ (PR, ROC, confusion matrix, calibration).
* `dropout_model` phiên bản N ở trạng thái **Production**.
* Ngưỡng và mốc rủi ro trong `config/settings.yaml`.

## 6. Công cụ / File thực hiện
`src/train.py` (hàm `evaluate`, `register`), notebook `04_machine_learning_models.ipynb` (`scikit-learn`, `mlflow`).

## 7. Tiêu chí hoàn thành
- [ ] Đạt tiêu chí thành công ở B0 trên Test (hoặc có giải thích rõ nếu chưa đạt).
- [ ] Tải lại mô hình từ Registry (`models:/dropout_model/Production`) và dự đoán được.

---

## 8. Câu hỏi bảo vệ thường gặp
**Hỏi:** Vì sao không dùng ngưỡng 0,5?  
**Đáp:** Lớp dương chỉ ~10% và bỏ sót tốn kém hơn báo động giả. Ngưỡng được chọn trên OOF để đạt Recall ≥ 0,80, sau đó mới đánh giá trên Test.

**Hỏi:** "Risk score 0,7" có thật sự nghĩa là 70% khả năng bỏ học không?  
**Đáp:** Chỉ đúng khi mô hình đã được hiệu chỉnh. Nhóm dùng isotonic calibration và kiểm tra bằng reliability diagram và Brier score.
