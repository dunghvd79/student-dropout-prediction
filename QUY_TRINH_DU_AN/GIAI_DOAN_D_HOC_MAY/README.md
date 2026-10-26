# GIAI ĐOẠN D – HỌC MÁY
[← Giai đoạn C](../GIAI_DOAN_C_PHAN_TICH_KHAI_PHA/README.md) · [Về tổng quan](../README.md) · [Giai đoạn E →](../GIAI_DOAN_E_TRIEN_KHAI_VAN_HANH/README.md)

## Mục tiêu giai đoạn
Xây dựng mô hình **phân loại nhị phân** dự đoán xác suất sinh viên bỏ học ở kỳ kế tiếp, được đánh giá **khách quan, không rò rỉ**, có **xác suất đáng tin** và **giải thích được**; đưa mô hình tốt nhất vào trạng thái **Production** trong MLflow.

```text
feature_table.parquet
      │
      ▼
[B9]  Tách Censored → Scoring set (11.115)
      Tập có nhãn (68.124) ──► chia theo Student_ID ──► Train (~80%) │ Test (~20%)
      │
      ▼
[B10] Pipeline: Imputer → (log/winsorize) → Scaler → One-Hot + trọng số lớp
      │
      ▼
[B11] CV 5-fold theo nhóm trên Train: LogReg, DT, RF, XGBoost, LightGBM → tuning → MLflow
      │
      ▼
[B12] Calibration → chọn ngưỡng trên OOF → đánh giá Test 1 lần → Model Registry (Production)
      │
      ▼
[B13] SHAP: giải thích toàn cục + từng sinh viên
```

## Các bước

| Bước | Tên | Lý thuyết chính | Output |
|:---:|---|---|---|
| [**B9**](./B09_CHIA_TAP_DU_LIEU.md) | Tạo tập có nhãn & chia tập | Giả định i.i.d., rò rỉ theo nhóm, GroupKFold / StratifiedGroupKFold, holdout, xử lý nhãn bị cắt | Train / Test / Scoring |
| [**B10**](./B10_TIEN_XU_LY_MAT_CAN_BANG.md) | Tiền xử lý & mất cân bằng lớp | Pipeline & ColumnTransformer, chuẩn hóa z-score, One-Hot, class weighting, SMOTE | `build_pipeline()` |
| [**B11**](./B11_HUAN_LUYEN_TINH_CHINH.md) | Huấn luyện & tinh chỉnh | Logistic Regression, Decision Tree, Random Forest, Gradient Boosting (XGBoost, LightGBM), bias–variance, Cross-Validation, Random / Bayesian search, MLflow | Bảng so sánh, mô hình tốt nhất |
| [**B12**](./B12_DANH_GIA_CHON_NGUONG.md) | Đánh giá & chọn ngưỡng | Đường PR / ROC, chọn ngưỡng, calibration & Brier score, công bằng (fairness), Model Registry | Báo cáo đánh giá, model Production |
| [**B13**](./B13_GIAI_THICH_MO_HINH_SHAP.md) | Giải thích mô hình | XAI, giá trị Shapley, LinearSHAP (mô hình cuối là LogReg), SHAP theo nhóm, giải thích toàn cục / cục bộ, SHAP để phát hiện rò rỉ | Biểu đồ SHAP, `top_reasons()` |

## Input → Output của cả giai đoạn
* **Input:** `feature_table.parquet`, `feature_spec.json`.
* **Output:** `dropout_model` (Production) trong MLflow; `model_comparison.csv`; `evaluation_report.md`; biểu đồ SHAP; ngưỡng rủi ro trong `settings.yaml`.

## Ba nguyên tắc chống rò rỉ của giai đoạn này
1. **Chia theo `Student_ID`**: không sinh viên nào xuất hiện ở cả Train và Test.
2. **Mọi bước "học từ dữ liệu" nằm trong Pipeline**: chỉ fit trên fold huấn luyện.
3. **Tập Test chỉ dùng một lần** ở B12; mọi lựa chọn (mô hình, tham số, ngưỡng) đều dựa trên CV / OOF của Train.

## Điều kiện để sang Giai đoạn E
- [ ] Mô hình đạt (hoặc giải thích được khi chưa đạt) tiêu chí thành công ở B0 trên tập Test.
- [ ] Mô hình đã được đăng ký ở trạng thái Production; tải lại và dự đoán được.
