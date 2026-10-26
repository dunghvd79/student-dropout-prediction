# BÁO CÁO ĐÁNH GIÁ MÔ HÌNH (B12)
*Sinh tự động bởi `python -m src.ml.evaluate` lúc 2026-10-26 21:41. Tập Test được dùng **một lần**; mọi lựa chọn chốt trên Train trước đó.*

* **Mô hình:** Logistic Regression, `C = 1.221`, không trọng số lớp, 43 đặc trưng.
* **Train:** 54,474 dòng · **Test:** 13,650 dòng (3,604 sinh viên), tỷ lệ bỏ học 10.4%.
* **Mốc rủi ro** (chọn trên OOF Train): Trung bình ≥ **0.0704** (Recall OOF ≥ 0,80) · Cao ≥ **0.3153** (Precision OOF ≥ 0,50).

## 1. Kết quả tổng thể

| Chỉ số | OOF Train (để chọn) | **Test (một lần)** |
|---|---:|---:|
| PR-AUC | 0.4090 | **0.4002** |
| ROC-AUC | 0.8028 | **0.8101** |
| Brier score | 0.0742 | **0.0772** |
| Xác suất TB / tỷ lệ thật | 0.1009 / 0.1008 | 0.0983 / 0.1043 |
| Recall @ Trung bình | 0.800 | **0.827** |
| Precision @ Trung bình | 0.195 | **0.208** |
| % dòng ≥ Trung bình | 41.4% | 41.5% |
| Recall @ Cao | 0.323 | **0.284** |
| Precision @ Cao | 0.500 | **0.493** |
| % dòng ở mức Cao | 6.5% | 6.0% |

## 2. Ba mức rủi ro trên Test

| Mức | Số dòng | % dòng | Tỷ lệ bỏ học thực tế | % ca bỏ học thuộc mức này |
|---|---:|---:|---:|---:|
| Thấp | 7,985 | 58.5% | 3.1% | 17.3% |
| Trung bình | 4,843 | 35.5% | 15.9% | 54.2% |
| Cao | 822 | 6.0% | 49.3% | 28.4% |

## 3. Công bằng theo nhóm (Test, tại mốc Trung bình)

| chieu            | nhom           |   so_dong |   ty_le_bo_hoc |   recall |   precision |   pr_auc |
|:-----------------|:---------------|----------:|---------------:|---------:|------------:|---------:|
| Học kỳ           | Kỳ 1           |      3604 |          0.071 |    0.785 |       0.189 |    0.382 |
| Học kỳ           | Kỳ 2           |      2974 |          0.116 |    0.826 |       0.245 |    0.434 |
| Học kỳ           | Kỳ ≥ 3         |      7072 |          0.117 |    0.84  |       0.201 |    0.394 |
| Gender           | Female         |      6819 |          0.106 |    0.828 |       0.209 |    0.401 |
| Gender           | Male           |      6574 |          0.101 |    0.821 |       0.205 |    0.396 |
| Gender           | Other/Unknown  |       257 |          0.136 |    0.886 |       0.242 |    0.49  |
| First_Generation | Không          |      9020 |          0.088 |    0.781 |       0.202 |    0.375 |
| First_Generation | Thế hệ đầu     |      4630 |          0.136 |    0.884 |       0.215 |    0.434 |
| Housing_Status   | Off-Campus     |      4010 |          0.107 |    0.829 |       0.206 |    0.38  |
| Housing_Status   | On-Campus      |      5283 |          0.108 |    0.853 |       0.21  |    0.424 |
| Housing_Status   | With Parents   |      4357 |          0.098 |    0.788 |       0.206 |    0.393 |
| Scholarship      | Có học bổng    |      3941 |          0.072 |    0.762 |       0.186 |    0.334 |
| Scholarship      | Không học bổng |      9709 |          0.118 |    0.842 |       0.213 |    0.419 |

## 4. Ca bỏ sót (bỏ học nhưng dưới mốc Trung bình) so với ca bắt được

|                  |   bo_sot_FN |   bat_duoc_TP |    o_lai |
|:-----------------|------------:|--------------:|---------:|
| Sem_GPA          |        2.8  |          2.27 |     2.74 |
| Failed_Courses   |        0.41 |          1.35 |     0.6  |
| Financial_Stress |        2.03 |          4.19 |     2.44 |
| Work_Hours       |       15.18 |         22.95 |    16.46 |
| Attendance       |       85.58 |         82.69 |    85.51 |
| Semester         |        3.01 |          3.37 |     3.03 |
| Family_Income    |    69611.3  |      44662.9  | 63013.9  |

## 5. Đối chứng phụ trên Test (KHÔNG dùng để chọn mô hình; mô hình đã chốt trước)

| Mô hình | PR-AUC Test |
|---|---:|
| LogReg – 43 đặc trưng (mô hình được chọn) | 0.4002 |
| LogReg – chỉ 20 đặc trưng gốc (ablation) | 0.3960 |
| XGBoost tinh chỉnh (dự phòng) | 0.3997 |

## 6. Biểu đồ

**Đường PR và ROC trên tập Test, kèm 2 mốc rủi ro**

![eval_pr_roc.png](figures/eval_pr_roc.png)

**Độ hiệu chỉnh xác suất: OOF trên Train và Test**

![eval_calibration.png](figures/eval_calibration.png)

**Ma trận nhầm lẫn trên Test tại 2 mốc**

![eval_confusion.png](figures/eval_confusion.png)

**Recall theo nhóm trên Test (đường xám: mục tiêu 0,80)**

![eval_fairness.png](figures/eval_fairness.png)
