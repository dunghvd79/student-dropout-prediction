# GIAI ĐOẠN C – PHÂN TÍCH & KHAI PHÁ DỮ LIỆU
[← Giai đoạn B](../GIAI_DOAN_B_KY_THUAT_DU_LIEU_ETL/README.md) · [Về tổng quan](../README.md) · [Giai đoạn D →](../GIAI_DOAN_D_HOC_MAY/README.md)

## Mục tiêu giai đoạn
**Hiểu dữ liệu** (EDA), **biến lịch sử nhiều kỳ thành đặc trưng có sức dự báo** (Feature Engineering), và **khám phá tri thức ẩn** (Data Mining: phân cụm, luật kết hợp). Kết quả của giai đoạn này vừa là đầu vào cho Học máy (Giai đoạn D), vừa là một nửa giá trị học thuật của đề tài (phần **Khai phá dữ liệu**).

```text
PostgreSQL + MongoDB ──► [B6 EDA] ──► insight, giả thuyết đặc trưng
                                            │
clean_semesters.parquet ──► [B7 Feature Engineering] ──► feature_table.parquet
                                                               │
                                                  ┌────────────┴────────────┐
                                                  ▼                         ▼
                                       [B8A Phân cụm K-Means]   [B8B Luật kết hợp Apriori]
                                                  │                         │
                                           student_clusters        association_rules.csv
```

## Các bước

| Bước | Tên | Lý thuyết chính | Output |
|:---:|---|---|---|
| [**B6**](./B06_PHAN_TICH_KHAM_PHA_EDA.md) | Phân tích khám phá (EDA) | Phân tích đơn/đa biến, Pearson & Spearman, tương quan ≠ nhân quả, nghịch lý Simpson, phân tích quỹ đạo, Kaplan–Meier | Biểu đồ, insight |
| [**B7**](./B07_TRICH_XUAT_DAC_TRUNG.md) | Trích xuất đặc trưng theo chiều dọc | Dữ liệu bảng (panel), lag, difference, cumulative, rolling window, slope OLS, point-in-time correctness | `feature_table.parquet` + `feature_spec.json` |
| [**B8**](./B08_KHAI_PHA_DU_LIEU.md) | Khai phá dữ liệu | K-Means, Elbow, Silhouette, DBSCAN, PCA; Support / Confidence / Lift, nguyên lý Apriori, FP-Growth | Nhãn cụm, bảng luật kết hợp |

## Data Mining và Machine Learning khác nhau thế nào?

| | **Data Mining (B8)** | **Machine Learning (Giai đoạn D)** |
|---|---|---|
| Mục tiêu | **Mô tả**, khám phá tri thức ẩn | **Dự báo** định lượng |
| Câu hỏi | "Có những nhóm sinh viên nào? Yếu tố nào hay đi cùng bỏ học?" | "Sinh viên X có xác suất bỏ học kỳ sau là bao nhiêu?" |
| Kỹ thuật | Học không giám sát (phân cụm), luật kết hợp | Học có giám sát (phân loại) |
| Kết quả | Hồ sơ nhóm, luật dạng "Nếu … thì …" | Điểm rủi ro cho từng sinh viên |

## Input → Output của cả giai đoạn
* **Input:** Dữ liệu sạch (`clean_semesters.parquet` hoặc `load_analytic_table()`).
* **Output:** Báo cáo EDA, `feature_table.parquet` (79.239 × ~45), `feature_spec.json`, bảng `student_clusters`, `association_rules.csv`.

## Điều kiện để sang Giai đoạn D
- [ ] Đặc trưng qua unit test, không dùng dữ liệu kỳ sau.
- [ ] Có hồ sơ cụm và top luật kết hợp có diễn giải.
