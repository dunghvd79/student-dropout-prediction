# BƯỚC 10. TIỀN XỬ LÝ TRONG PIPELINE & XỬ LÝ MẤT CÂN BẰNG LỚP
**Giai đoạn D – Học máy** · [← Bước 9](./B09_CHIA_TAP_DU_LIEU.md) · [Bước 11 →](./B11_HUAN_LUYEN_TINH_CHINH.md)

---

## 1. Nhiệm vụ
Đóng gói mọi bước "học từ dữ liệu" vào **một `sklearn Pipeline`**, để chúng **chỉ được fit trên dữ liệu huấn luyện** của từng fold; đồng thời xử lý việc lớp bỏ học chỉ chiếm ~10%.

---

## 2. Cơ sở lý thuyết

### 2.1. Rò rỉ trong tiền xử lý
Nếu tính median / mean / std trên **toàn bộ** dữ liệu rồi mới chia Train/Test, các thống kê này đã "nhìn thấy" Test. Ảnh hưởng thường nhỏ nhưng **sai về nguyên tắc**, và có thể lớn với các kỹ thuật như SMOTE hay chọn đặc trưng.
**Quy tắc:** `fit` trên Train → `transform` cả Train và Test bằng **cùng** tham số đã học.

### 2.2. Pipeline và ColumnTransformer
* **`Pipeline`:** chuỗi các bước `[(tên, bộ biến đổi), …, (tên, mô hình)]`. Gọi `pipeline.fit(X, y)` thì từng bước được fit tuần tự **chỉ trên X đưa vào**. Khi dùng trong `cross_validate` / `GridSearchCV`, mỗi fold tự fit lại, nên **không có rò rỉ giữa các fold**.
* **`ColumnTransformer`:** áp dụng các phép biến đổi **khác nhau cho từng nhóm cột** (số, phân loại, nhị phân) rồi ghép lại.
* Lợi ích phụ: lưu **một object duy nhất** (tiền xử lý + mô hình), nên khi dự đoán (B14) chắc chắn dùng đúng cùng phép biến đổi (tránh **training–serving skew**).

### 2.3. Chuẩn hóa (Scaling)
* **Standardization (z-score):** $z = \frac{x - \mu}{\sigma}$, đưa về trung bình 0 và độ lệch chuẩn 1.
* **Cần cho:** mô hình dựa trên khoảng cách hoặc gradient / hệ số (Logistic Regression có regularization, KNN, SVM, K-Means). Không scale thì biến có thang lớn sẽ chi phối hệ số phạt.
* **Không cần cho mô hình cây:** cây chia theo ngưỡng trên từng biến, và phép biến đổi đơn điệu không làm đổi thứ tự giá trị.

### 2.4. Biến đổi biến lệch
* **`log1p(x) = ln(1+x)`:** nén đuôi phải dài, xử lý được giá trị 0. Giúp mô hình tuyến tính khi quan hệ có dạng "tăng nhanh rồi bão hòa".
* **Winsorization P1–P99:** chặn giá trị cực đoan về phân vị; các phân vị phải được học từ Train.

### 2.5. Mã hóa biến phân loại
* **One-Hot Encoding:** mỗi giá trị trở thành một cột 0/1. Không áp đặt thứ tự giả tạo (khác với Label Encoding 0, 1, 2).
* `handle_unknown='ignore'`: nếu lúc dự đoán xuất hiện giá trị chưa từng thấy, tất cả các cột là 0 thay vì báo lỗi.

### 2.6. Mất cân bằng lớp (Class Imbalance)
Khi lớp dương hiếm, hàm mất mát bị chi phối bởi lớp âm, và mô hình có xu hướng "lười", đoán toàn lớp âm. Các cách xử lý:

| Kỹ thuật | Cơ chế | Ghi chú |
|---|---|---|
| **Class weighting** | Nhân trọng số vào hàm mất mát: lỗi trên lớp dương bị phạt nặng hơn. `class_weight='balanced'`: $w_c = \frac{N}{K \cdot N_c}$ | Không thay đổi dữ liệu; đơn giản, hiệu quả. **Ưu tiên** |
| **`scale_pos_weight`** (XGBoost / LightGBM) | Trọng số cho lớp dương = $\frac{N_{neg}}{N_{pos}}$ | ≈ 61.207 / 6.917 ≈ **8,85** |
| **Random undersampling** | Bỏ bớt mẫu lớp âm | Mất thông tin |
| **Random oversampling** | Nhân bản mẫu lớp dương | Dễ overfit |
| **SMOTE** | Tạo mẫu dương **tổng hợp** bằng nội suy giữa một mẫu và láng giềng gần: $x_{new} = x_i + \lambda (x_{nn} - x_i),\ \lambda \in [0,1]$ | Chỉ áp dụng trên **fold huấn luyện**; dùng `imblearn.Pipeline` |
| **Điều chỉnh ngưỡng** | Giữ mô hình, hạ ngưỡng quyết định thấp hơn 0,5 | Làm ở B12 |

**Cảnh báo:** **không bao giờ** SMOTE / oversample trước khi chia tập, hoặc lên tập Validation / Test. Làm vậy thì các mẫu tổng hợp "na ná" mẫu Test sẽ nằm trong Train (rò rỉ), và tập đánh giá không còn phản ánh phân phối thật.

**Lưu ý:** class weighting và SMOTE làm **lệch xác suất dự đoán** lên cao, nên cần **calibration** ở B12 trước khi diễn giải "0,6 = 60%".

---

## 3. Input
Danh sách đặc trưng (`feature_spec.json`), `X_train`.

---

## 4. Biến đổi (thiết kế `ColumnTransformer`)

| Nhóm cột | Mô hình tuyến tính (LogReg) | Mô hình cây (DT, RF, XGBoost, LightGBM) |
|---|---|---|
| Số liệu có thiếu (`Family_Income`, `LMS_Logins`, Lag/Delta) | `SimpleImputer(median)`; Delta điền 0 | Giữ `NaN` (XGBoost/LightGBM) hoặc `SimpleImputer(median)` (RF, DT) |
| Biến lệch (`Family_Income`, `Financial_Stress`, `Emergency_Expense`, `Financial_Burden_Index`) | Winsorize P1–P99 → `log1p` | Giữ giá trị gốc |
| Biến số còn lại | `StandardScaler` | Không cần scale |
| `Gender`, `Housing_Status` | `OneHotEncoder(handle_unknown='ignore')` | `OneHotEncoder` |
| Nhị phân (0/1) | `passthrough` | `passthrough` |

**Xử lý mất cân bằng** (so sánh ở B11): `class_weight='balanced'` (LogReg/DT/RF); `scale_pos_weight` tính trên Train (XGBoost/LightGBM); *(thử nghiệm)* SMOTE trong `imblearn.Pipeline`.

Viết hàm `build_pipeline(model_name, imbalance='weight')` trả về Pipeline **chưa fit**.

---

## 5. Output
Hàm `build_pipeline(name, spec, imbalance, y_train, params)` trong `src/ml/train.py` trả về Pipeline **chưa fit**:

```text
CastTypes  →  ColumnTransformer (tiền xử lý)  →  [SMOTE]  →  mô hình
(ép kiểu cố định,  (mọi tham số học từ fold       (chỉ khi fit,
 không học gì)      huấn luyện)                     trên fold huấn luyện)
```

| Loại tiền xử lý | Dùng cho | Nội dung |
|---|---|---|
| `linear` | LogReg | 6 biến lệch: median → winsorize P1–P99 → `log1p` → scale; `Delta_*`, `GPA_Slope`: điền 0 → scale; số còn lại: median → scale; nhị phân giữ nguyên; One-Hot |
| `native` | XGBoost, LightGBM | Giữ `NaN` (mô hình tự xử lý); One-Hot |
| `impute` | DT, RF và mọi mô hình khi dùng SMOTE | Median cho cột số; One-Hot |

* **Mất cân bằng lớp:**
  * `weight`: `class_weight='balanced'` (LogReg, DT), `'balanced_subsample'` (RF), `scale_pos_weight = âm / dương` tính từ `y_train` được truyền vào (XGBoost, LightGBM).
  * `smote`: `imblearn.Pipeline`, SMOTE chỉ chạy lúc `fit`.
  * `none`: không xử lý.
* 6 mô hình: `dummy`, `logreg`, `dtree`, `rf`, `xgb`, `lgbm`, với tham số mặc định hợp lý; B11 tinh chỉnh qua `params`.
* Sau tiền xử lý: 43 đặc trưng → **47 cột** (One-Hot `Gender` và `Housing_Status`, mỗi biến 3 giá trị).

**Chạy thử trên dữ liệu thật** (1 fold CV trong Train: 43.683 / 10.791 dòng; **không dùng tập Test**; chỉ để chắc pipeline chạy đúng, so sánh chính thức ở B11):

| Mô hình | Mất cân bằng | PR-AUC | ROC-AUC | Thời gian |
|---|---|---:|---:|---:|
| dummy | – | 0,106 | 0,500 | 0,3 giây |
| logreg | weight | **0,414** | 0,798 | 0,9 giây |
| dtree | weight | 0,320 | 0,747 | 0,7 giây |
| rf | weight | 0,378 | 0,786 | 6,5 giây |
| xgb | weight | 0,395 | 0,782 | 3,6 giây |
| lgbm | weight | 0,395 | 0,783 | 1,8 giây |
| logreg | smote | 0,412 | 0,797 | 1,6 giây |
| lgbm | smote | 0,398 | 0,785 | 3,3 giây |

* Mọi mô hình vượt xa mốc ngẫu nhiên (PR-AUC 0,106). Với tham số mặc định, **LogReg đang nhỉnh hơn mô hình cây** trên fold này. B11 phải kiểm chứng bằng CV đủ 5 fold và tinh chỉnh, chưa được mặc định chọn XGBoost.
* SMOTE không cải thiện rõ so với trọng số lớp, nhưng làm huấn luyện chậm hơn.

## 6. Công cụ / File thực hiện
* `src/ml/train.py`: `CastTypes`, `Winsorizer` (tự viết, học phân vị khi fit), `column_groups`, `build_preprocessor`, `positive_weight`, `build_model`, `build_pipeline`.
* `tests/test_train_pipeline.py`: 27 unit test, gồm 18 tổ hợp (6 mô hình × 3 cách xử lý mất cân bằng) fit trên dữ liệu có `NaN` / `pd.NA`.
* Ghim `scipy==1.14.1`: bản 1.18 gây cảnh báo `iprint` khi dùng với scikit-learn 1.5.2.

## 7. Tiêu chí hoàn thành (đã kiểm tra 2026-10-26)
- [x] Pipeline `fit` / `predict_proba` được trên dữ liệu có `NaN` (cả `pd.NA` của `LMS_Logins`) cho mọi mô hình và mọi cách xử lý mất cân bằng.
- [x] Không có bước fit nào ngoài Pipeline. Test xác nhận trung vị và mean của imputer / scaler bằng đúng thống kê của dữ liệu huấn luyện, và không đổi khi dự đoán.
- [x] `scale_pos_weight` tính từ `y_train` truyền vào (test kiểm tra đúng tỷ lệ âm / dương); SMOTE chỉ cân bằng lúc fit, dự đoán giữ nguyên số dòng.
- [x] Giá trị phân loại chưa từng thấy (ví dụ `Housing_Status = "Dorm"`) không làm lỗi dự đoán.

---

## 8. Câu hỏi bảo vệ thường gặp
**Hỏi:** Vì sao không dùng SMOTE ngay từ đầu cho cân bằng?  
**Đáp:** SMOTE trước khi chia tập gây rò rỉ và làm tập Test không còn phản ánh thực tế. Nhóm ưu tiên trọng số lớp (không thay đổi dữ liệu), và chỉ thử SMOTE bên trong fold huấn luyện.

**Hỏi:** Random Forest có cần chuẩn hóa không?  
**Đáp:** Không. Cây chia theo ngưỡng trên từng biến nên không phụ thuộc thang đo. Chuẩn hóa chỉ cần cho Logistic Regression.
