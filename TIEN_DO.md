# TIẾN ĐỘ DỰ ÁN
**Cập nhật lần cuối:** 2026-10-26 · **Commit mới nhất:** `Buoc 13: giai thich SHAP, sua ro ri Income_Missing`  
**Quy trình chi tiết:** [`QUY_TRINH_DU_AN/`](./QUY_TRINH_DU_AN/README.md)

> Cập nhật file này mỗi khi xong một bước: đổi trạng thái, ghi commit, thêm quyết định / vấn đề mới.

---

## 1. Tổng quan

| Giai đoạn | Bước | Trạng thái |
|---|---|:---:|
| **A – Chuẩn bị** | B0 Xác định bài toán | ✅ Xong |
| | B1 Dựng môi trường | ✅ Xong |
| **B – Kỹ thuật dữ liệu (ETL)** | B2 Nạp dữ liệu thô vào MinIO | ✅ Xong |
| | B3 Kiểm tra chất lượng dữ liệu | ✅ Xong |
| | B4 Làm sạch dữ liệu | ✅ Xong |
| | B5 Nạp kho Polyglot | ✅ Xong |
| **C – Phân tích & Khai phá** | B6 EDA | ✅ Xong |
| | B7 Trích xuất đặc trưng | ✅ Xong |
| | B8 Khai phá dữ liệu | ✅ Xong |
| **D – Học máy** | B9 Chia tập | ✅ Xong |
| | B10 Tiền xử lý & mất cân bằng | ✅ Xong |
| | B11 Huấn luyện & tinh chỉnh | ✅ Xong |
| | B12 Đánh giá & chọn ngưỡng | ✅ Xong |
| | B13 Giải thích SHAP | ✅ Xong |
| **E – Triển khai & Vận hành** | B14 Dự đoán theo lô | ⏭️ **Làm tiếp theo** |
| | B15 Dashboard | ⬜ Chưa làm |
| | B16 Giám sát & vận hành | ⬜ Chưa làm |
| **F – Kết thúc** | B17 Báo cáo & bảo vệ | ⬜ Chưa làm |

**Hoàn thành: 14 / 18 bước** (Giai đoạn A, B, C, D xong).

---

## 2. Nhật ký các bước đã xong

### B0 – Xác định bài toán ✅
* Đã chốt trong [`B00_XAC_DINH_BAI_TOAN.md`](./QUY_TRINH_DU_AN/GIAI_DOAN_A_CHUAN_BI/B00_XAC_DINH_BAI_TOAN.md): đơn vị dự đoán là 1 sinh viên tại cuối kỳ *t*; nhãn `Target_Dropout_Next_Sem`; chỉ số chính PR-AUC; mục tiêu Recall ≥ 0,80 (chốt lại sau baseline ở B11).
* Đã sửa các tài liệu cũ cho khớp dữ liệu thật (commit `c566bc2`).

### B1 – Dựng môi trường ✅ (commit `323315c`)
* `.venv` Python 3.12.13 (tạo bằng `uv`), cài từ `requirements.txt`.
* Docker: MinIO, PostgreSQL, MongoDB, MLflow chạy và qua `python -m src.ops.check_env`.
* File: `docker-compose.yml`, `docker/`, `config/settings.yaml`, `src/core/config.py`, `src/ops/check_env.py`, `.env.example`.

### B2 – Nạp dữ liệu thô ✅ (commit `6b10ec6`)
* `python -m src.etl.ingest` → `s3://raw/academic/ingest_date=2026-10-11/batch_id=20261011T085849Z_7df267/academic_survival_longitudinal.csv`.
* 79.239 dòng × 22 cột, MD5 `94f87baf205fb7f1446639749a2dd852`, đã tải ngược và so MD5.
* Đã kiểm tra: chạy lại → `SKIPPED`; file hỏng → `FAILED`; 8/8 unit test đạt.
* File: `src/etl/ingest.py`, `src/core/schema.py`, `src/core/db.py`, `sql/01_ingestion_log.sql`, `tests/test_ingest.py`.

### B3 – Kiểm tra chất lượng dữ liệu ✅ (commit `62a379c`)
* `python -m src.etl.validate` trên lô `20261011T085849Z_7df267`: data contract **ĐẠT** (4 OK, 5 WARN, 0 ERROR).
* Báo cáo [`reports/data_quality_report.md`](./reports/data_quality_report.md) + 4 biểu đồ `reports/figures/dq_*.png`.
* File cố tình làm hỏng → 5 ERROR, mã thoát 1. Tổng cộng 21/21 unit test đạt.
* Phát hiện: tỷ lệ bỏ học theo `Financial_Stress` tính đúng trên tập có nhãn là **5,3% → 50,2%** (số cũ 4,6% → 47% tính trên toàn bộ dữ liệu); đã sửa trong THIET_KE_PIPELINE, B03, B06.
* File: `src/etl/validate.py`, `src/core/schema.py` (thêm `RANGES`, `STATIC_COLUMNS`, `GENDER_MAP`…), `tests/test_validate.py`, `pytest.ini`; thêm `tabulate` vào requirements.

### B4 – Làm sạch dữ liệu ✅ (commit "Buoc 4: lam sach du lieu")
* `python -m src.etl.clean` → `data/processed/clean_semesters.parquet` (79.239 × 24) + `s3://processed/academic/batch_id=20261011T085849Z_7df267/clean_semesters.parquet`.
* Gender đổi cách ghi 4.648 dòng; `Attendance`: clip 164 dòng > 100, 85 dòng mã lỗi −2 → thiếu, điền bằng kỳ trước (sửa ở B7, trước đó clip về 0); điền `Family_Income` bằng kỳ trước 2.574 (còn 1.030 dòng chưa khai báo đến kỳ đó → `Income_Missing`; 199 sinh viên không khai báo ở kỳ nào; **sửa ở B13**: trước đó ffill + bfill); điền `LMS_Logins` 658 (còn 209).
* 7/7 kiểm tra sau làm sạch đạt; chạy 2 lần cho file Parquet giống hệt (MD5 `deacca08…`); file hỏng bị chặn. 31/31 unit test đạt.
* File: `src/etl/clean.py`, `tests/test_clean.py`, `reports/cleaning_log.md`.

### B5 – Nạp kho Polyglot ✅ (commit "Buoc 5: nap kho Polyglot")
* `python -m src.etl.load`: PostgreSQL `students` 20.000, `financial_profiles` 20.000 (+ `predictions` rỗng); MongoDB `academic_semesters` 79.239 document, unique index `(student_id, semester)`.
* 5/5 đối soát đạt; chạy 2 lần số lượng không đổi; `load_analytic_table()` ghép lại giống hệt `clean_semesters.parquet`. 34/34 unit test đạt.
* File: `src/etl/load.py`, `sql/02_core_tables.sql`, `tests/test_load.py`.

### Rà soát B1 – B5 (2026-10-26)
* **Lỗi code đã sửa** (đều có test hồi quy):
  1. Lô nạp lại có dòng trùng khóa bị báo nhầm ERROR ở "tính liên tục học kỳ" và "logic nhãn" → các kiểm tra chạy trên dữ liệu đã khử trùng; trùng khóa chỉ là WARN.
  2. Thiếu giá trị ở cột không được phép thiếu (ví dụ `Age`) vẫn qua data contract nhưng làm `clean.py` lỗi → thêm `NULLABLE_COLUMNS`, thiếu ở cột khác là ERROR.
  3. Mật khẩu có ký tự đặc biệt (`@ : /`) làm hỏng chuỗi kết nối PostgreSQL / MongoDB → mã hóa bằng `quote_plus`.
  4. Chú thích biểu đồ trong báo cáo chất lượng ghi cứng số liệu (249 dòng, 3.000 → 488.000) → tính từ dữ liệu của lô.
* **Tài liệu đã sửa:** đường dẫn `sql/schema.sql` → `sql/01_…`, `sql/02_…`; Giai đoạn A ghi "5 dịch vụ" → 4; mục "Dữ liệu đang có" ở trên.
* **Giới hạn đã biết (chưa xử lý):** `load.py` chỉ upsert, không xóa sinh viên / document không còn trong lô mới. Đủ cho dữ liệu hiện tại (một lô); cần thêm bước dọn khi có nhiều lô.
* Chạy lại toàn bộ trên dữ liệu thật: kết quả không đổi (hash dữ liệu sạch `d0f62efcf08dc468`, 5/5 đối soát B5 đạt). 38/38 unit test đạt.

### B6 – EDA ✅ (commit "Buoc 6: EDA")
* Notebook `notebooks/01_data_cleaning_eda.ipynb` (đã chạy, 8 biểu đồ nhúng) + `reports/figures/eda_*.png`.
* 10 insight; nổi bật: GPA tụt ≥ 0,5 → 32,5% bỏ học; nợ tích lũy ≥ 6 môn → 21,5%; nhóm bỏ học có áp lực tài chính tăng dần trong 4 kỳ trước khi bỏ (nhóm tốt nghiệp đi ngang); chưa khai báo thu nhập → 10,7% ≈ mức nền (bản đầu báo 84,7% / 118 dòng là do rò rỉ, sửa ở B13); gặp cố vấn nhiều hơn ở nhóm bỏ học (nhân quả ngược).
* Sửa lỗi phát sinh: `src/etl/validate.py` gọi `matplotlib.use("Agg")` khi import, làm notebook không hiển thị được biểu đồ → chuyển sang vẽ bằng `matplotlib.figure.Figure`, không đổi backend toàn cục.

### B7 – Trích xuất đặc trưng ✅ (commit "Buoc 7: trich xuat dac trung")
* `python -m src.analysis.features` → `data/features/feature_table.parquet` (79.239 × 47) + `config/feature_spec.json` (43 đặc trưng = 20 gốc + 23 chiều dọc).
* Notebook `02_feature_engineering.ipynb`: 7 / 10 đặc trưng mạnh nhất (mutual information) là đặc trưng chiều dọc; `Delta_GPA` dạng ngưỡng, `Delta_Stress` dạng chữ U; nhóm GPA trùng thông tin (ρ 0,92 – 0,98).
* 6 unit test mới (gồm test "không nhìn tương lai"); tổng 45/45 đạt. Chạy 2 lần cho file giống hệt.
* **Sửa B4:** `Attendance = −2` là mã lỗi (85 dòng, kỳ trước / sau quanh 86%) chứ không phải 0% chuyên cần → coi là thiếu, điền bằng kỳ trước; trước đó clip về 0 tạo `Delta_Attendance` giả tới −96. Đã nạp lại kho, chạy lại EDA (số liệu chuyên cần đổi 0,1 – 0,2 điểm, đã cập nhật nhận xét).

### B8 – Khai phá dữ liệu ✅ (commit "Buoc 8: khai pha du lieu")
* `python -m src.analysis.mining` → PostgreSQL `student_clusters` (20.000), `reports/cluster_profiles.csv`, `reports/association_rules.csv`; notebook `03_data_mining_patterns.ipynb` (5 biểu đồ).
* **K-Means k = 4:** tỷ lệ bỏ học theo sinh viên 67% (sa sút học tập + áp lực tài chính) / 32% (đi làm nhiều) / 31% (học lực yếu, tài chính ổn) / 17% (học tốt). Silhouette ≈ 0,13 và DBSCAN chỉ ra 1 cụm, nên cụm được hiểu là phân khúc; điểm nhiễu DBSCAN có 65% bỏ học.
* **Apriori:** 15 luật lift ≥ 2; mạnh nhất `GPA_Low + Failed_2plus` → 55,8% (lift 5,5). FP-Growth cùng kết quả nhưng chậm hơn (18 giây so với 0,07 giây, vì chỉ 11 item).
* 5 unit test mới; tổng 50/50 đạt.

### B9 – Chia tập dữ liệu ✅ (commit "Buoc 9: chia tap du lieu")
* `python -m src.ml.split` → Train 54.474 dòng / 14.324 SV (10,08% dương), Test 13.650 dòng / 3.604 SV (10,43%), Scoring 11.115 dòng; 43 đặc trưng.
* 6/6 kiểm tra đạt: không giao sinh viên (kể cả giữa các fold CV), Test 20,0%, không có cột rò rỉ; CV 5 fold có tỷ lệ dương 9,70 – 10,58%.
* `data/splits/test_student_ids.csv` là nguồn sự thật của cách chia; B10 – B14 gọi `load_splits()`.
* File: `src/ml/split.py` (tách khỏi `train.py`), `tests/test_split.py`; tổng 57/57 test đạt.

### Rà soát B6 – B9 (2026-10-26)
* **Kiểm tra rò rỉ tự động:** AUC đơn biến cao nhất trên Train là 0,73 (`Sem_GPA`); không đặc trưng nào > 0,9.
* **Sửa:**
  1. B8 ghi "thu nhập trung bình" của cụm nhưng thực chất là trung bình hình học (exp của trung bình log) → đổi sang trung vị thật (29.000 / 35.000 / 71.000 / 69.000); cập nhật notebook 03 và B08.
  2. B9: kiểm tra "Scoring set" chỉ xét số dòng > 0 → kiểm tra thật: mỗi sinh viên đúng 1 dòng, không trùng dòng nào của Train/Test.
  3. EDA: ghi rõ hạn chế của Kaplan–Meier khi coi tốt nghiệp là "bị cắt" (thực chất là rủi ro cạnh tranh).
  4. Tài liệu: kích thước bảng đặc trưng "~45" → 47 cột (43 đặc trưng); số dòng Train/Test chính xác; ví dụ clipping ở B04; mục "Dữ liệu đang có".
* **Ghi nhận về dữ liệu** (không phải lỗi): mọi dòng nhãn 1 đều là kỳ cuối quan sát của sinh viên; 18% dòng nhãn 0 cũng là kỳ cuối (tốt nghiệp). Toàn bộ 1.968 sinh viên tốt nghiệp ở kỳ 8; kỳ 8 có 204 dòng "bỏ học kỳ sau", nghĩa là không tốt nghiệp đúng hạn. Không đặc trưng nào mã hóa "đây là kỳ cuối", nên không gây rò rỉ.

### B10 – Tiền xử lý & mất cân bằng lớp ✅ (commit "Buoc 10: tien xu ly trong Pipeline")
* `src/ml/train.py`: `build_pipeline(name, spec, imbalance, y_train)` → Pipeline chưa fit (`CastTypes` → tiền xử lý `linear` / `native` / `impute` → [SMOTE] → mô hình); 6 mô hình, 3 cách xử lý mất cân bằng.
* 27 unit test mới (tổng 84/84 đạt): mọi tổ hợp fit được trên dữ liệu có `NaN`; tham số học chỉ từ dữ liệu huấn luyện; SMOTE chỉ chạy lúc fit.
* Chạy thử trên 1 fold CV (không dùng Test): mọi mô hình vượt xa mốc 0,106; **LogReg 0,414 nhỉnh hơn XGBoost / LightGBM 0,395** với tham số mặc định, nên B11 phải kiểm chứng.
* Ghim `scipy==1.14.1` (trước đó chưa ghim, bản 1.18 gây cảnh báo với scikit-learn 1.5.2).

### B11 – Huấn luyện & tinh chỉnh ✅ (commit "Buoc 11: huan luyen, tinh chinh, ablation"; số liệu dưới đây là bản chạy lại ở B13 sau khi sửa rò rỉ)
* `python -m src.ml.experiments`: so sánh 12 cấu hình (CV 5 fold theo sinh viên), Optuna 40 thử nghiệm cho LogReg + XGBoost, ablation; mọi lần chạy ghi vào MLflow `dropout_ews`.
* **Kết quả:** LogReg 0,3980 dẫn đầu khi dùng tham số mặc định; sau tinh chỉnh LogReg 0,3982 (`C = 0,011`), XGBoost 0,3998 (`max_depth = 2`). So theo cặp 3 seed × 5 fold: XGBoost hơn +0,0028 [+0,0011; +0,0046], ~0,7%. **Nhóm chọn giữ LogReg** (`model.final` trong settings.yaml); dự đoán OOF lưu `data/models/oof_best.parquet`. Bản đầu (có rò rỉ): LogReg 0,4097, XGBoost 0,4090.
* **Phát hiện quan trọng:**
  1. **Đặc trưng chiều dọc không cải thiện dự báo** (LogReg 0,3978 → 0,3982, chỉ tốt hơn 2/5 fold; XGBoost còn giảm; kỳ ≥ 3 cũng không khác).
  2. SMOTE làm giảm PR-AUC; ban đầu còn mất tác dụng âm thầm với mô hình cây do nội suy cột rời rạc (đã sửa bằng SMOTENC).
  3. Trọng số lớp không đổi PR-AUC, chỉ đổi ngưỡng.
* **Kiểm chứng độ vững:** lặp CV 3 seed × 5 fold: LogReg +0,0003 (khoảng tin cậy chứa 0), XGBoost −0,0014; pipeline đủ 47 cột; chỉ đặc trưng chiều dọc đạt 0,352 ⇒ có thông tin nhưng trùng với trạng thái hiện tại.
* Sửa lỗi: tham số Optuna trùng tham số đặt cứng trong `build_model`. 12 test mới; tổng 96/96 đạt. Notebook `04_machine_learning_models.ipynb` (phần B9 – B11).

### B12 – Đánh giá trên Test & đăng ký mô hình ✅ (commit `Buoc 12`)
* Chọn trên Train: LogReg **không trọng số lớp** (đã hiệu chỉnh sẵn, Brier OOF 0,0749, không cần isotonic); mốc rủi ro trên OOF: Trung bình ≥ 0,0717 (Recall ≥ 0,80), Cao ≥ 0,3175 (Precision ≥ 0,50) → `config/risk_thresholds.json`.
* **Test (lần 2, sau khi sửa rò rỉ ở B13; lần 1: PR-AUC 0,400, Recall 0,827):** PR-AUC 0,391, ROC-AUC 0,808, Brier 0,078 (sát OOF, không overfit). Recall 0,820 / Precision 0,205 tại mốc Trung bình; mức Cao: 5,7% sinh viên, 49,7% thật sự bỏ học.
* Công bằng: Nữ / Nam như nhau; Recall thấp hơn ở nhóm rủi ro nền thấp (có học bổng 0,76, kỳ 1 0,77). Ca bỏ sót có hồ sơ "bình thường", nguyên nhân nằm ngoài dữ liệu.
* MLflow Registry: `dropout_model` **v2**, alias `production` (tải lại khớp; v1 là bản có rò rỉ). `src/ml/evaluate.py` có chốt chặn: đánh giá lại Test phải có `--force --reason`, lịch sử ghi trong `test_metrics.json` và tag MLflow.

### B13 – Giải thích mô hình (SHAP) ✅ (commit `Buoc 13`)
* `python -m src.ml.explain`: `shap.LinearExplainer` (chính xác, φ = β(x − E[x]) trên log-odds), cộng One-Hot về biến gốc, **gom 13 nhóm khái niệm**; tính cộng sai số 1,8e-15. Báo cáo `reports/explanation_report.md`, `shap_group_importance.csv`, 7 biểu đồ `shap_*.png`; notebook 04 mục 8.
* Nhóm quan trọng nhất: Kết quả học tập 19,8% > Trượt môn 18,4% > Thế hệ đầu 16,0% ≈ Áp lực tài chính 15,9% > Học bổng 11,9%; nhất quán với EDA và luật B8. Lý do số 1 ở mức Cao: học tập 47%, trượt môn 32%, tài chính 21%.
* `top_reasons()` → 3 lý do bằng câu tiếng Việt có giá trị thật; không nêu nhóm nhân khẩu & nơi ở, gặp cố vấn (không can thiệp được / nhân quả ngược). Dùng ở B14 / B16.
* **Phát hiện rò rỉ:** `Income_Missing` hệ số 3,50 (biến kế tiếp 0,84). Cờ cũ "không khai báo ở kỳ nào" (ffill + bfill ở B4) nhìn trước tương lai: 84,7% bỏ học so với 10,7% khi tính đúng thời điểm. **Đã sửa:**
  1. B4 chỉ ffill.
  2. B5 lưu cờ theo kỳ ở MongoDB (`socio_economic.income_missing`), round-trip vẫn khớp.
  3. Chạy lại B7 → B12. PR-AUC giảm ~0,011 ở mọi mô hình; Test đánh giá lại lần 2 có ghi lý do.
* Sau khi sửa, XGBoost nhỉnh hơn LogReg 0,003 (có ý nghĩa thống kê, ~0,7%) → **nhóm chọn giữ LogReg**.
* Hệ số ngược dấu được liệt kê tự động: lần đầu `GPA_Roll3`; hiện tại `Work_prev` / `Work_Hours`.
* 9 test mới (`test_explain.py`) + test B4 / B5 cho thu nhập đúng thời điểm; tổng 112/112 đạt. Notebook 01, 02, 04 chạy lại, 0 lỗi.

---

## 3. Việc tiếp theo: B14 – Dự đoán theo lô (Batch Scoring)

Chi tiết: [`B14_DU_DOAN_THEO_LO.md`](./QUY_TRINH_DU_AN/GIAI_DOAN_E_TRIEN_KHAI_VAN_HANH/B14_DU_DOAN_THEO_LO.md)

- [ ] Tải mô hình từ `models:/dropout_model@production`; chấm 11.115 dòng scoring set (`Censored = 1`).
- [ ] Kiểm tra schema đặc trưng khớp `feature_spec.json` trước khi dự đoán.
- [ ] Mức rủi ro theo `config/risk_thresholds.json` (không đọc mốc cứng trong settings).
- [ ] Lý do bằng `explain()` + `top_reasons()` (nền SHAP = Train); ghi `predictions` (upsert theo `(run_id, student_id)`), kèm `model_version`.
- [ ] Kiểm tra: không có `risk_score` NULL; phân bố mức rủi ro hợp lý.

---

## 4. Môi trường hiện tại

| Thành phần | Phiên bản | Địa chỉ |
|---|---|---|
| Python (`.venv`) | 3.12.13 | – |
| MinIO | 2024.12.18 (`bitnamilegacy/minio`), bucket `raw` / `processed` / `mlflow` | http://localhost:9001 |
| PostgreSQL | 16.6, database `dropout_ews` + `mlflow` | `localhost:5433` |
| MongoDB | 7.0.16 | `localhost:27018` |
| MLflow | 2.19.0 | http://localhost:5000 |

**Dữ liệu đang có trong hệ thống:**
* MinIO `raw`: 1 object (lô `20261011T085849Z_7df267`). MinIO `processed`: `academic/batch_id=20261011T085849Z_7df267/clean_semesters.parquet`.
* PostgreSQL `dropout_ews`: `ingestion_log` 3 dòng (1 `SUCCESS`, 1 `SKIPPED` khi chạy lại, 1 `FAILED` từ file hỏng dùng để thử); `students` 20.000; `financial_profiles` 20.000; `predictions` rỗng.
* MongoDB `dropout_ews.academic_semesters`: 79.239 document, unique index `(student_id, semester)`.
* PostgreSQL `student_clusters`: 20.000 dòng (B8).
* Trên máy (không commit, tạo lại bằng script): `data/processed/clean_semesters.parquet` (B4), `data/features/feature_table.parquet` (B7), `data/splits/test_student_ids.csv` + `split_summary.json` (B9).
* MLflow: experiment `_smoke_test` đã xóa (chỉ dùng để thử ghi artifact).

---

## 5. Quyết định & sai khác so với thiết kế ban đầu

| # | Quyết định | Lý do | Ghi ở |
|:---:|---|---|---|
| 1 | Loại 11.115 dòng `Censored = 1` khỏi Train/Test, dùng làm tập chấm điểm | Nhãn 0 của các dòng này chưa xác nhận | THIET_KE_PIPELINE, B03, B09 |
| 2 | Không chặn `Financial_Stress` về 5 | Tỷ lệ bỏ học tăng đều theo chỉ số (5,3% → 50,2% trên tập có nhãn), giá trị cao là tín hiệu thật | THIET_KE_PIPELINE, B03 |
| 3 | `Family_Income` chỉ ffill theo sinh viên (**sửa ở B13**, trước đó ffill + bfill), còn thiếu thì cờ `Income_Missing` + trung vị | Giá trị không đổi nhưng *việc biết* giá trị phụ thuộc thời gian; bfill tạo rò rỉ (SHAP phát hiện) | THIET_KE_PIPELINE, B04, B13 |
| 4 | `emergency_expense` chuyển sang MongoDB | Thay đổi theo kỳ, không phải thuộc tính tĩnh | BAO_CAO_CSDL_GIUA_KY, B05 |
| 5 | Dùng `bitnamilegacy/minio` thay `minio/minio` | Image chính thức đã bị gỡ khỏi Docker Hub và quay.io | B01, docker-compose |
| 6 | PostgreSQL cổng **5433**, MongoDB cổng **27018** | Máy đã có `sdl_postgres` (5432) và MongoDB service (27017) | B01, `.env.example` |
| 7 | Python 3.12 qua `uv`, không dùng 3.14 | Bản 3.12 đăng ký trên máy bị hỏng; 3.14 chưa ổn với shap/lightgbm/mlflow | B01 |
| 8 | Ghim `alembic==1.14.0` | Bản mới hơn làm MLflow 2.19 không khởi động được | requirements.txt, Dockerfile |
| 9 | Key MinIO thêm `batch_id=…` | Nạp nhiều lần trong cùng ngày không ghi đè lô cũ | B02 |
| 10 | `Attendance = −2` coi là thiếu, điền bằng kỳ trước (chỉ clip > 100) | −2 là mã lỗi (kỳ trước / sau ~86%); clip về 0 tạo cú sụt giả | B03, B04, B07, THIET_KE_PIPELINE |
| 11 | Không dùng SMOTE; dùng trọng số lớp | SMOTE (kể cả SMOTENC) giảm PR-AUC ở cả 3 mô hình vì phá ràng buộc giữa các đặc trưng | B10, B11 |
| 12 | Mô hình cuối là **Logistic Regression** (không phải XGBoost như thiết kế ban đầu); xác nhận lại ở B13 (`model.final`) | Sau khi sửa rò rỉ XGBoost chỉ hơn 0,003 PR-AUC (~0,7%); LogReg đơn giản, ổn định, giải thích chính xác | B11, B13, THIET_KE_PIPELINE, README |
| 13 | Trình bày dữ liệu chiều dọc là giá trị **mô tả / giải thích**, không phải độ chính xác | Ablation 3 seed × 5 fold: không cải thiện PR-AUC | README, PROJECT_OVERVIEW, B06, B07, B11 |
| 14 | LogReg cuối **không dùng trọng số lớp**, không thêm bước hiệu chỉnh | Đã hiệu chỉnh sẵn (Brier bằng isotonic), PR-AUC cao nhất; mất cân bằng xử lý bằng ngưỡng | B12 |
| 15 | 3 mức rủi ro theo chính sách: Cao = Precision ≥ 0,5 (0,318), Trung bình = Recall ≥ 0,80 (0,072) thay cho mốc cố định 0,3 / 0,6 | Mốc cố định 0,3 / 0,6 chỉ bắt ~34% ca bỏ học | B12, settings.yaml, THIET_KE_PIPELINE |
| 16 | Lý do cảnh báo đọc theo **13 nhóm SHAP**, không theo từng biến; không nêu nhân khẩu / gặp cố vấn làm lý do | Biến tương quan làm hệ số ngược dấu; nhân khẩu không can thiệp được, cố vấn là nhân quả ngược | B13 |
| 17 | Đánh giá Test lần 2 (có `--reason`) sau khi sửa rò rỉ | Lỗi phát hiện độc lập trên Train; mô hình và ngưỡng chốt trước, không dùng Test để chọn | B12, B13 |

---

## 6. Cách làm tiếp khi quay lại

```powershell
docker compose up -d          # bật lại MinIO, PostgreSQL, MongoDB, MLflow
.venv\Scripts\activate
python -m src.ops.check_env       # phải báo "Tất cả đều sẵn sàng"
python -m pytest              # 112/112 đạt
```

* Muốn giải phóng RAM khi không làm: `docker compose stop` (dữ liệu vẫn giữ trong volume).
* `.env` chỉ có trên máy này (mật khẩu ngẫu nhiên). Thành viên khác: `copy .env.example .env` rồi tự đặt mật khẩu.

---

## 7. Vấn đề còn mở

- [x] **Cách trình bày "điểm độc đáo":** đã sửa README, PROJECT_OVERVIEW, B06, B07, B11, B17, THIET_KE_PIPELINE theo hướng "quỹ đạo giúp mô tả / giải thích, đã kiểm chứng là không tăng độ chính xác"; bổ sung kiểm chứng độ vững. Nhóm nên đọc lại trước khi bảo vệ.
- [ ] Các thành viên khác chưa thử dựng lại môi trường trên máy của mình (tiêu chí cuối của B1).
- [x] Tiêu chí thành công ở B0: đạt (Recall Test 0,820 tại mốc Trung bình; PR-AUC 0,391 so với mốc 0,10; giải thích từng sinh viên bằng SHAP ở B13).
- [ ] MLflow còn các run của lần chạy đầu (có rò rỉ) và `dropout_model` v1: giữ làm lịch sử hay xóa trước khi demo.
- [ ] Dòng `FAILED` thử nghiệm trong `ingestion_log`: giữ làm bằng chứng hay xóa trước khi demo.
