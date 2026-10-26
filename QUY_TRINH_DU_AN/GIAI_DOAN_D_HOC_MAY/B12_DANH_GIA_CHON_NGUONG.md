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
* `reports/evaluation_report.md` (sinh tự động) + `reports/test_metrics.json` + 4 biểu đồ `reports/figures/eval_*.png`.
* `config/risk_thresholds.json`: 2 mốc rủi ro chọn trên OOF Train (B14 đọc file này). Chính sách nằm trong `config/settings.yaml` → `risk_levels`.
* MLflow Model Registry: **`dropout_model` v1, alias `production`** (MLflow 2.x khuyến nghị alias thay cho "stage"; B14 tải bằng `models:/dropout_model@production`). Kèm bản sao `data/models/dropout_model.joblib`.

**Quyết định trước khi nhìn Test (đều chọn trên Train):**
1. **Hiệu chỉnh xác suất:** so sánh 5 phương án trên OOF (CV lồng nhau). LogReg **không trọng số lớp** đã hiệu chỉnh sẵn (Brier 0,0742, xác suất TB 0,101 = tỷ lệ thật) với PR-AUC cao nhất (0,4090). Trọng số lớp làm xác suất lệch (TB 0,388, Brier 0,176), và isotonic / sigmoid chỉ đưa về đúng mức đó. ⇒ Dùng LogReg không trọng số, **không thêm bước hiệu chỉnh**; mất cân bằng xử lý bằng ngưỡng.
2. **Chính sách 3 mức** (nhóm chốt): Trung bình = ngưỡng lớn nhất đạt Recall ≥ 0,80 → **0,0704**; Cao = ngưỡng nhỏ nhất đạt Precision ≥ 0,50 → **0,3153**.

**Kết quả trên Test** (13.650 dòng, 3.604 sinh viên, đánh giá **một lần**):

| Chỉ số | OOF Train | **Test** |
|---|---:|---:|
| PR-AUC | 0,4090 | **0,4002** |
| ROC-AUC | 0,8028 | **0,8101** |
| Brier | 0,0742 | **0,0772** |
| Recall / Precision @ Trung bình | 0,800 / 0,195 | **0,827 / 0,208** |
| Recall / Precision @ Cao | 0,323 / 0,500 | **0,284 / 0,493** |

| Mức | % sinh viên (Test) | Tỷ lệ bỏ học thực tế | % ca bỏ học thuộc mức |
|---|---:|---:|---:|
| Cao | 6,0% | **49,3%** | 28,4% |
| Trung bình | 35,5% | 15,9% | 54,2% |
| Thấp | 58,5% | 3,1% | 17,3% |

* **Không overfit:** Test sát OOF; reliability diagram sát đường chéo trên cả hai.
* **Công bằng (Recall tại mốc Trung bình):**
  * Nữ 0,828 / Nam 0,821, không thiên lệch theo giới.
  * Thấp hơn mục tiêu ở nhóm rủi ro nền thấp: có học bổng 0,762, không phải thế hệ đầu 0,781, kỳ 1 0,785, sống cùng bố mẹ 0,788.
* **Ca bỏ sót** có hồ sơ như sinh viên bình thường (GPA 2,80, trượt 0,41 môn, áp lực 2,03): nguyên nhân bỏ học nằm ngoài dữ liệu.
* **Đối chứng phụ** (không dùng để chọn): chỉ đặc trưng gốc 0,3960; XGBoost 0,3997. Kết luận B11 giữ nguyên.

## 6. Công cụ / File thực hiện
* `src/ml/evaluate.py`: chạy `python -m src.ml.evaluate [--force] [--no-register]`. **Chốt chặn:** nếu `reports/test_metrics.json` đã tồn tại thì từ chối đánh giá lại Test (trừ khi `--force`; số lần đánh giá được ghi trong `test_runs`). Gồm `oof_predictions`, `choose_thresholds`, `risk_level`, `fairness_table`, `missed_cases`, `register` (log mô hình kèm `code_paths=src`, gắn alias, tải lại kiểm tra).
* `tests/test_evaluate.py`: 6 unit test (ngưỡng đúng chính sách, ngưỡng "lớn nhất / nhỏ nhất", báo lỗi khi chính sách không thỏa hoặc mức Cao ≤ Trung bình, bảng mức rủi ro, công bằng); tổng 102/102 đạt.
* Notebook `04_machine_learning_models.ipynb`, mục 7 (chỉ đọc kết quả đã lưu).

## 7. Tiêu chí hoàn thành (đã kiểm tra 2026-10-26)
- [x] Đạt tiêu chí B0: PR-AUC Test 0,400 (gấp ~4 lần mốc ngẫu nhiên 0,10); **Recall 0,827 ≥ 0,80** ở mốc Trung bình; giải thích được (B13).
- [x] Tải lại mô hình từ Registry (`models:/dropout_model@production`) và dự đoán khớp với mô hình gốc.
- [x] Tập Test chỉ đánh giá **một lần** (`test_runs = 1`).

---

## 8. Câu hỏi bảo vệ thường gặp
**Hỏi:** Vì sao không dùng ngưỡng 0,5?  
**Đáp:** Lớp dương chỉ ~10% và bỏ sót tốn kém hơn báo động giả. Ngưỡng được chọn trên OOF để đạt Recall ≥ 0,80, sau đó mới đánh giá trên Test.

**Hỏi:** "Risk score 0,7" có thật sự nghĩa là 70% khả năng bỏ học không?  
**Đáp:** Chỉ đúng khi mô hình đã được hiệu chỉnh. Nhóm dùng isotonic calibration và kiểm tra bằng reliability diagram và Brier score.
