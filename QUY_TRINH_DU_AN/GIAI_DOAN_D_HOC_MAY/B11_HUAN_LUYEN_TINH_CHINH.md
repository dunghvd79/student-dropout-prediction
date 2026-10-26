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
* **Ablation study:** bỏ đi một thành phần để đo đóng góp của nó. Ở đây so sánh **chỉ đặc trưng gốc** với **đặc trưng gốc + đặc trưng chiều dọc**, để **đo** (không giả định) giá trị của B7 bằng số liệu.

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
* `reports/model_comparison.csv`, `reports/tuning_logreg.csv`, `reports/tuning_xgb.csv`, `reports/tuned_models.json`, `reports/ablation.csv`, `reports/best_model.json`.
* `data/models/oof_best.parquet`: dự đoán out-of-fold của mô hình được chọn, dùng cho B12.
* MLflow experiment `dropout_ews` (http://localhost:5000): mỗi cấu hình một run, gồm tham số, metric trung bình / std, metric từng fold, tag `data_md5` và `git_commit`.
* Notebook [`notebooks/04_machine_learning_models.ipynb`](../../notebooks/04_machine_learning_models.ipynb) (phần B9 – B11) + 4 biểu đồ `reports/figures/ml_*.png`.

> Số liệu dưới đây là lần chạy lại **sau khi sửa rò rỉ `Income_Missing`** (phát hiện ở B13, sửa ở B4). Lần chạy đầu cao hơn ~0,011 PR-AUC ở mọi mô hình; thứ hạng không đổi.

**So sánh mô hình** (CV 5 fold theo sinh viên, tham số mặc định, trọng số lớp):

| Mô hình | PR-AUC | ROC-AUC | Thời gian CV |
|---|---:|---:|---:|
| **LogReg** | **0,3980 ± 0,0054** | 0,801 | 8 giây |
| XGBoost | 0,3800 ± 0,0054 | 0,787 | 17 giây |
| LightGBM | 0,3797 ± 0,0058 | 0,786 | 14 giây |
| Random Forest | 0,3732 ± 0,0053 | 0,787 | 38 giây |
| Decision Tree | 0,3204 ± 0,0071 | 0,755 | 8 giây |
| Dummy (mốc) | 0,1008 | 0,500 | – |

* **Trọng số lớp và không xử lý** cho cùng PR-AUC: PR-AUC chỉ phụ thuộc thứ hạng; trọng số chỉ đổi Recall / Precision tại ngưỡng 0,5.
* **SMOTE** (đã sửa thành SMOTENC) **giảm** PR-AUC ở cả 3 mô hình: LogReg 0,371, XGBoost 0,358, LightGBM 0,367; chậm hơn 7 – 14 lần. ⇒ Dùng trọng số lớp.

**Tinh chỉnh** (Optuna TPE + MedianPruner, 40 thử nghiệm): LogReg 0,3980 → **0,3982** (`C = 0,011`; mặt PR-AUC theo `C` rất phẳng); XGBoost 0,3800 → **0,3998** (`max_depth = 2`, `learning_rate = 0,019`, `n_estimators = 850`). Sau tinh chỉnh XGBoost nhỉnh hơn 0,0016, nhỏ hơn độ lệch chuẩn giữa các fold.

**Ablation** (cùng tham số đã tinh chỉnh):

| Mô hình | Chỉ gốc (20) | Gốc + chiều dọc (43) | Số fold đầy đủ tốt hơn |
|---|---:|---:|---:|
| LogReg | 0,3978 | 0,3982 | 2 / 5 |
| XGBoost | 0,4006 | 0,3998 | 1 / 5 |

* Kể cả sinh viên có lịch sử dài (kỳ ≥ 3): 0,4161 so với 0,4163 (LogReg). ⇒ **Đặc trưng chiều dọc không cải thiện dự báo.** Quỹ đạo sa sút thấy ở EDA đã thể hiện sẵn trong giá trị hiện tại.

**Kiểm chứng độ vững của kết quả ablation** (chạy lại y hệt sẽ cho kết quả giống từng chữ số nên không kiểm chứng được gì; thay vào đó kiểm tra theo cách có thể làm kết luận thay đổi):

| Kiểm tra | Kết quả | Kết luận |
|---|---|---|
| Lặp CV với 3 seed khác (15 cặp fold) | LogReg: +0,0003, khoảng tin cậy ~95% [−0,0018; +0,0023], tốt hơn 8/15 fold. XGBoost: −0,0014 [−0,0024; −0,0004], tốt hơn 4/15 fold | Không phụ thuộc cách chia fold. Với XGBoost, thêm đặc trưng trùng còn làm kém đi nhẹ |
| Pipeline có dùng đặc trưng chiều dọc? | Gốc 24 cột, đầy đủ 47 cột sau xử lý; LogReg gán tổng \|hệ số\| 1,18 cho nhóm chiều dọc so với 3,08 cho nhóm gốc | Không có lỗi làm rơi cột; mô hình **chủ động** gán trọng số nhỏ |
| Chỉ dùng 23 đặc trưng chiều dọc | PR-AUC 0,352 (mốc ngẫu nhiên 0,10) | Có thông tin nhưng **trùng** với đặc trưng gốc |

> **Phạm vi kết luận:** đúng với bộ dữ liệu này, có thể là dữ liệu được sinh ra sao cho rủi ro phụ thuộc trạng thái hiện tại. Với dữ liệu thật của một trường, cần kiểm tra lại bằng đúng thí nghiệm này.

**Mô hình được chọn:** **Logistic Regression**, `C = 0,011`, 43 đặc trưng; PR-AUC CV **0,3982 ± 0,0054** (ghi trong `config/settings.yaml` → `model.final`; `best_model.json` ghi thêm `best_by_cv`).
* So sánh theo cặp, 3 seed × 5 fold: XGBoost tinh chỉnh (không trọng số lớp) hơn LogReg **+0,0028**, khoảng tin cậy 95% [+0,0011; +0,0046], thắng 13/15 fold. Có ý nghĩa thống kê nhưng **rất nhỏ** (~0,7%, nhỏ hơn nhiều dao động giữa các fold ~0,015).
* Nhóm **giữ LogReg** vì đơn giản, nhanh, ổn định và giải thích chính xác (LinearSHAP, B13). XGBoost là phương án dự phòng.
* Trước khi sửa rò rỉ, LogReg nhỉnh hơn (0,4097 so với 0,4090): rò rỉ là một cờ nhị phân hệ số lớn, loại tín hiệu mô hình tuyến tính khai thác rất dễ.

## 6. Công cụ / File thực hiện
* `src/ml/experiments.py`: chạy `python -m src.ml.experiments [--stage all|compare|tune|ablation] [--trials 40] [--no-mlflow]`. Tách khỏi `train.py`: `train.py` dựng Pipeline, `experiments.py` chạy thí nghiệm. Gồm `cross_validate` (mỗi fold dựng Pipeline mới, `scale_pos_weight` tính lại trên fold), `Tracker` (MLflow; lỗi ghi log không dừng thí nghiệm), `stage_compare`, `tune`, `stage_ablation`.
* `src/ml/train.py`: bổ sung `DiscreteAwareSMOTE` (SMOTENC cho cột rời rạc); sửa `build_model` để `params` ghi đè tham số mặc định.
* `tests/test_experiments.py` (6 test), `tests/test_train_pipeline.py` (+6 test: SMOTE giữ cột rời rạc, ghi đè tham số cho 5 mô hình); tổng 96/96 đạt.
* Thời gian chạy (lần chạy lại): compare ~10 phút; tune LogReg ~4 phút, XGBoost ~22 phút; ablation ~1 phút.

## 7. Tiêu chí hoàn thành (đã kiểm tra 2026-10-26)
- [x] Mô hình tốt nhất vượt baseline rõ rệt: PR-AUC 0,40 so với 0,10 (Dummy). LogReg vừa là baseline "thật" vừa là mô hình tốt nhất. Đây là một phát hiện, không phải thiếu sót: mô hình cây sau tinh chỉnh chỉ đuổi kịp.
- [x] Độ lệch chuẩn PR-AUC giữa các fold nhỏ (0,005 – 0,007), nên mô hình ổn định.
- [x] Có kết quả ablation cho đặc trưng chiều dọc (kết quả âm, kiểm chứng theo cặp fold và theo độ dài lịch sử).

**Lỗi phát hiện và sửa trong bước này:**
1. SMOTE nội suy cột nhị phân / đếm, nên mô hình cây tách được dòng tổng hợp và SMOTE mất tác dụng mà không báo lỗi → `DiscreteAwareSMOTE` (SMOTENC). Kết quả compare cũ đã xóa khỏi MLflow.
2. `build_model` đặt cứng `C`, `max_depth`… nên Optuna truyền trùng tham số bị lỗi → mặc định + ghi đè; thêm test.
3. (Phát hiện ở B13) Rò rỉ `Income_Missing` từ B4 làm PR-AUC cao hơn thật ~0,011 → sửa B4, chạy lại toàn bộ B11.

---

## 8. Câu hỏi bảo vệ thường gặp
**Hỏi:** Vì sao chọn Logistic Regression mà không phải XGBoost?
**Đáp:** Nhóm không chọn trước mà so sánh 6 mô hình bằng CV 5 fold theo sinh viên. Với tham số mặc định, LogReg dẫn đầu (0,3980 so với 0,3800 của XGBoost). Sau khi tinh chỉnh cả hai bằng Optuna, XGBoost nhỉnh hơn 0,003 (có ý nghĩa thống kê qua 15 cặp fold, nhưng chỉ ~0,7%, nhỏ hơn nhiều dao động giữa các fold). Với chênh lệch không đáng kể về thực tế, nhóm chọn mô hình **đơn giản, ổn định, nhanh và giải thích chính xác** hơn. Optuna chọn cho XGBoost cây rất nông (`max_depth = 2`), cũng cho thấy quan hệ trong dữ liệu gần tuyến tính.

**Hỏi:** Đặc trưng theo chiều dọc có giúp không?
**Đáp:** Không làm tăng độ chính xác: thêm 23 đặc trưng chiều dọc vào 20 đặc trưng gốc cho chênh lệch +0,0003, khoảng tin cậy chứa 0 (3 seed × 5 fold). Riêng chúng vẫn đạt PR-AUC 0,352, tức là có thông tin nhưng trùng với trạng thái hiện tại. Nhóm giữ chúng vì giá trị mô tả và giải thích.

**Hỏi:** Tinh chỉnh siêu tham số có làm overfit không?  
**Đáp:** Có thể overfit vào tập kiểm định nếu thử quá nhiều. Nhóm tinh chỉnh bằng CV 5-fold theo nhóm trên Train, và không dùng Test để chọn (Test được đánh giá lại một lần duy nhất vì sửa rò rỉ, có ghi lý do).
