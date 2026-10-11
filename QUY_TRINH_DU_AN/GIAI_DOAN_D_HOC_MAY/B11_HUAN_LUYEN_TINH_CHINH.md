# BƯỚC 11. HUẤN LUYỆN, TINH CHỈNH & THEO DÕI BẰNG MLFLOW
**Giai đoạn D – Học máy** · [← Bước 10](./B10_TIEN_XU_LY_MAT_CAN_BANG.md) · [Bước 12 →](./B12_DANH_GIA_CHON_NGUONG.md)

---

## 1. Nhiệm vụ
Huấn luyện và **so sánh công bằng** các mô hình bằng Cross-Validation theo nhóm, tinh chỉnh siêu tham số, ghi lại mọi thí nghiệm, và chọn ra mô hình tốt nhất.

---

## 2. Cơ sở lý thuyết

### 2.1. Các mô hình phân loại được so sánh

#### Logistic Regression (baseline có thể giải thích)
* Mô hình tuyến tính trên thang log-odds: $P(y=1 \mid x) = \sigma(w^\top x + b) = \frac{1}{1 + e^{-(w^\top x + b)}}$.
* Huấn luyện bằng cách tối thiểu **log-loss** (cross-entropy) $-\frac{1}{N}\sum [y\log p + (1-y)\log(1-p)]$, thêm **regularization** L2/L1 để chống overfit.
* Ưu: nhanh, ổn định, hệ số dễ giải thích ($e^{w_j}$ = tỷ số odds). Nhược: chỉ bắt quan hệ tuyến tính (trừ khi tự tạo tương tác).

#### Decision Tree
* Chia dữ liệu đệ quy theo ngưỡng của từng biến, chọn phép chia làm **giảm độ hỗn tạp** nhiều nhất:
  * Gini: $G = 1 - \sum_c p_c^2$
  * Entropy: $H = -\sum_c p_c \log_2 p_c$
* Ưu: trực quan, bắt được quan hệ phi tuyến và tương tác. Nhược: **phương sai cao** (dễ overfit), không ổn định.

#### Random Forest (Bagging)
* Huấn luyện nhiều cây trên **mẫu bootstrap** (lấy mẫu có hoàn lại), mỗi lần chia chỉ xét **một tập con ngẫu nhiên các biến**, rồi **lấy trung bình** dự đoán.
* Trung bình nhiều cây ít tương quan với nhau giúp **giảm phương sai** mà không tăng nhiều độ chệch.

#### Gradient Boosting: XGBoost, LightGBM (Boosting)
* Xây cây **tuần tự**; mỗi cây mới học để **sửa sai số (gradient của hàm mất mát)** của tổng các cây trước: $F_m(x) = F_{m-1}(x) + \eta \cdot h_m(x)$, với $\eta$ là learning rate.
* **XGBoost:** dùng đạo hàm bậc hai, có regularization (L1/L2 trên trọng số lá, `gamma`), xử lý giá trị thiếu tự động, hỗ trợ `scale_pos_weight`.
* **LightGBM:** chia biến thành **histogram** và cây phát triển theo **lá (leaf-wise)**, nên nhanh hơn và tốn ít bộ nhớ; cần giới hạn `num_leaves` để tránh overfit.
* Thường là lựa chọn **mạnh nhất cho dữ liệu dạng bảng**.

### 2.2. Đánh đổi Bias – Variance
* **Bias (độ chệch):** mô hình quá đơn giản, không bắt được quy luật (underfit), ví dụ LogReg trên quan hệ phi tuyến.
* **Variance (phương sai):** mô hình quá nhạy với dữ liệu huấn luyện (overfit), ví dụ cây sâu không giới hạn.
* Bagging chủ yếu **giảm variance**; Boosting chủ yếu **giảm bias** (và cần regularization để kiểm soát variance).

### 2.3. Siêu tham số và cách tinh chỉnh
* **Tham số** (trọng số, ngưỡng chia) được mô hình học từ dữ liệu. **Siêu tham số** (độ sâu cây, learning rate, số cây) do người làm đặt trước.

| Phương pháp | Cách làm | Nhận xét |
|---|---|---|
| Grid Search | Thử **mọi** tổ hợp trên lưới | Tốn kém, bùng nổ tổ hợp |
| **Random Search** | Thử ngẫu nhiên *n* tổ hợp | Hiệu quả hơn Grid khi chỉ vài tham số thực sự quan trọng (Bergstra & Bengio, 2012) |
| **Bayesian Optimization** (Optuna – TPE) | Dùng kết quả các lần thử trước để chọn vùng hứa hẹn tiếp theo | Ít lần thử hơn để đạt kết quả tốt |

* Tinh chỉnh **luôn dùng CV theo nhóm trên Train**, tuyệt đối không dùng Test.

### 2.4. Baseline và Ablation Study
* **Baseline:** mốc tối thiểu để so sánh. `DummyClassifier` có PR-AUC ≈ tỷ lệ lớp dương (≈ 0,10); Logistic Regression là baseline "thật".
* **Ablation study:** bỏ đi một thành phần để đo đóng góp của nó. Ở đây so sánh **chỉ đặc trưng gốc** với **đặc trưng gốc + đặc trưng chiều dọc**, để chứng minh giá trị của B7 bằng số liệu.

### 2.5. Theo dõi thí nghiệm với MLflow
| Khái niệm | Ý nghĩa |
|---|---|
| **Experiment** | Nhóm các lần chạy cho một bài toán (`dropout_ews`) |
| **Run** | Một lần huấn luyện cụ thể |
| **Params** | Siêu tham số, loại mô hình, cách cân bằng lớp |
| **Metrics** | PR-AUC, Recall… theo từng fold và trung bình |
| **Artifacts** | File mô hình, biểu đồ, danh sách đặc trưng |
| **Tags** | Phiên bản dữ liệu (MD5), người chạy, ghi chú |

Nhờ MLflow, mọi kết quả đều **truy vết được**: mô hình X được huấn luyện bằng dữ liệu nào, tham số nào, đạt bao nhiêu.

---

## 3. Input
`X_train, y_train, groups_train`, `build_pipeline()`, MLflow Tracking Server.

---

## 4. Biến đổi
1. **Baseline:** `DummyClassifier(strategy='prior')` và Logistic Regression.
2. **So sánh mô hình:** Logistic Regression, Decision Tree, Random Forest, XGBoost, LightGBM.
3. **CV 5-fold** `StratifiedGroupKFold` theo `Student_ID`; ghi trung bình ± std của PR-AUC (chính), ROC-AUC, Recall, Precision, F1.
4. **Tinh chỉnh** 2 mô hình tốt nhất bằng Optuna / `RandomizedSearchCV` (~50 lần thử), tối ưu **PR-AUC**. Ví dụ không gian cho XGBoost: `max_depth` 3 – 8 · `learning_rate` 0,01 – 0,2 · `n_estimators` 200 – 1.000 · `subsample`, `colsample_bytree` 0,6 – 1,0 · `min_child_weight` 1 – 10.
5. **So sánh cách cân bằng lớp:** trọng số lớp và SMOTE.
6. **Ablation:** có / không có đặc trưng chiều dọc.
7. **Log MLflow** mỗi lần chạy: params, metrics theo fold, `feature_spec`, thời gian huấn luyện, MD5 dữ liệu.
8. Lưu **dự đoán OOF** của mô hình tốt nhất để chọn ngưỡng ở B12.

---

## 5. Output
* `reports/model_comparison.csv` (mô hình × chỉ số, trung bình ± std).
* Mô hình + bộ tham số tốt nhất; dự đoán OOF.
* Các lần chạy trong MLflow experiment `dropout_ews`.

## 6. Công cụ / File thực hiện
`src/train.py`, notebook `04_machine_learning_models.ipynb` (`scikit-learn`, `xgboost`, `lightgbm`, `optuna`, `mlflow`).

## 7. Tiêu chí hoàn thành
- [ ] Mô hình tốt nhất vượt baseline LogReg rõ rệt về PR-AUC.
- [ ] Độ lệch chuẩn PR-AUC giữa các fold nhỏ (mô hình ổn định).
- [ ] Có kết quả ablation cho đặc trưng chiều dọc.

---

## 8. Câu hỏi bảo vệ thường gặp
**Hỏi:** Vì sao chọn XGBoost / LightGBM?  
**Đáp:** Gradient boosting thường mạnh nhất trên dữ liệu bảng, bắt được phi tuyến và tương tác, tự xử lý giá trị thiếu, và có `scale_pos_weight` cho dữ liệu mất cân bằng. Nhóm vẫn so sánh với các mô hình khác bằng CV, nên lựa chọn có căn cứ số liệu.

**Hỏi:** Tinh chỉnh siêu tham số có làm overfit không?  
**Đáp:** Có thể overfit vào tập kiểm định nếu thử quá nhiều. Nhóm tinh chỉnh bằng CV 5-fold theo nhóm trên Train, và chỉ đánh giá **một lần** trên Test chưa từng dùng.
