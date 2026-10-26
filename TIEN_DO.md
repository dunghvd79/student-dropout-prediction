# TIẾN ĐỘ DỰ ÁN
**Cập nhật lần cuối:** 2026-10-26 · **Commit mới nhất:** "Buoc 7: trich xuat dac trung" (xem `git log`)  
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
| | B8 Khai phá dữ liệu | ⏭️ **Làm tiếp theo** |
| **D – Học máy** | B9 Chia tập | ⬜ Chưa làm |
| | B10 Tiền xử lý & mất cân bằng | ⬜ Chưa làm |
| | B11 Huấn luyện & tinh chỉnh | ⬜ Chưa làm |
| | B12 Đánh giá & chọn ngưỡng | ⬜ Chưa làm |
| | B13 Giải thích SHAP | ⬜ Chưa làm |
| **E – Triển khai & Vận hành** | B14 Dự đoán theo lô | ⬜ Chưa làm |
| | B15 Dashboard | ⬜ Chưa làm |
| | B16 Giám sát & vận hành | ⬜ Chưa làm |
| **F – Kết thúc** | B17 Báo cáo & bảo vệ | ⬜ Chưa làm |

**Hoàn thành: 8 / 18 bước** (Giai đoạn A và B xong; Giai đoạn C: 2/3).

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
* Gender đổi cách ghi 4.648 dòng; `Attendance`: clip 164 dòng > 100, 85 dòng mã lỗi −2 → thiếu, điền bằng kỳ trước (sửa ở B7, trước đó clip về 0); điền `Family_Income` 3.387 (còn 217 dòng / 199 sinh viên → `Income_Missing`); điền `LMS_Logins` 658 (còn 209).
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
* 10 insight; nổi bật: GPA tụt ≥ 0,5 → 32,5% bỏ học; nợ tích lũy ≥ 6 môn → 21,5%; nhóm bỏ học có áp lực tài chính tăng dần trong 4 kỳ trước khi bỏ (nhóm tốt nghiệp đi ngang); không khai báo thu nhập → 84,7% (118 dòng); gặp cố vấn nhiều hơn ở nhóm bỏ học (nhân quả ngược).
* Sửa lỗi phát sinh: `src/etl/validate.py` gọi `matplotlib.use("Agg")` khi import, làm notebook không hiển thị được biểu đồ → chuyển sang vẽ bằng `matplotlib.figure.Figure`, không đổi backend toàn cục.

### B7 – Trích xuất đặc trưng ✅ (commit "Buoc 7: trich xuat dac trung")
* `python -m src.analysis.features` → `data/features/feature_table.parquet` (79.239 × 47) + `config/feature_spec.json` (43 đặc trưng = 20 gốc + 23 chiều dọc).
* Notebook `02_feature_engineering.ipynb`: 7 / 10 đặc trưng mạnh nhất (mutual information) là đặc trưng chiều dọc; `Delta_GPA` dạng ngưỡng, `Delta_Stress` dạng chữ U; nhóm GPA trùng thông tin (ρ 0,92 – 0,98).
* 6 unit test mới (gồm test "không nhìn tương lai"); tổng 45/45 đạt. Chạy 2 lần cho file giống hệt.
* **Sửa B4:** `Attendance = −2` là mã lỗi (85 dòng, kỳ trước / sau quanh 86%) chứ không phải 0% chuyên cần → coi là thiếu, điền bằng kỳ trước; trước đó clip về 0 tạo `Delta_Attendance` giả tới −96. Đã nạp lại kho, chạy lại EDA (số liệu chuyên cần đổi 0,1 – 0,2 điểm, đã cập nhật nhận xét).

---

## 3. Việc tiếp theo: B8 – Khai phá dữ liệu

Chi tiết: [`B08_KHAI_PHA_DU_LIEU.md`](./QUY_TRINH_DU_AN/GIAI_DOAN_C_PHAN_TICH_KHAI_PHA/B08_KHAI_PHA_DU_LIEU.md)

- [ ] **8A – Phân cụm:** tổng hợp lên mức sinh viên (20.000), chuẩn hóa, K-Means k = 2 … 10 (Elbow + Silhouette), so sánh DBSCAN, mô tả + đặt tên cụm theo tỷ lệ bỏ học, PCA 2D; ghi bảng `student_clusters` vào PostgreSQL.
- [ ] **8B – Luật kết hợp:** rời rạc hóa thành item, Apriori / FP-Growth (`min_support = 0,01`), lọc vế phải `{DROPOUT}`, `confidence ≥ 0,3`, `lift ≥ 2`; `reports/association_rules.csv` + diễn giải.
- [ ] Notebook `03_data_mining_patterns.ipynb`.

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
* Trên máy: `data/processed/clean_semesters.parquet` (không commit, tạo lại bằng `python -m src.etl.clean`).
* MLflow: experiment `_smoke_test` đã xóa (chỉ dùng để thử ghi artifact).

---

## 5. Quyết định & sai khác so với thiết kế ban đầu

| # | Quyết định | Lý do | Ghi ở |
|:---:|---|---|---|
| 1 | Loại 11.115 dòng `Censored = 1` khỏi Train/Test, dùng làm tập chấm điểm | Nhãn 0 của các dòng này chưa xác nhận | THIET_KE_PIPELINE, B03, B09 |
| 2 | Không chặn `Financial_Stress` về 5 | Tỷ lệ bỏ học tăng đều theo chỉ số (5,3% → 50,2% trên tập có nhãn), giá trị cao là tín hiệu thật | THIET_KE_PIPELINE, B03 |
| 3 | `Family_Income` điền theo sinh viên trước (ffill + bfill), sau đó mới dùng trung vị | Cột không đổi theo kỳ; khôi phục được 94% số dòng thiếu | THIET_KE_PIPELINE, B04 |
| 4 | `emergency_expense` chuyển sang MongoDB | Thay đổi theo kỳ, không phải thuộc tính tĩnh | BAO_CAO_CSDL_GIUA_KY, B05 |
| 5 | Dùng `bitnamilegacy/minio` thay `minio/minio` | Image chính thức đã bị gỡ khỏi Docker Hub và quay.io | B01, docker-compose |
| 6 | PostgreSQL cổng **5433**, MongoDB cổng **27018** | Máy đã có `sdl_postgres` (5432) và MongoDB service (27017) | B01, `.env.example` |
| 7 | Python 3.12 qua `uv`, không dùng 3.14 | Bản 3.12 đăng ký trên máy bị hỏng; 3.14 chưa ổn với shap/lightgbm/mlflow | B01 |
| 8 | Ghim `alembic==1.14.0` | Bản mới hơn làm MLflow 2.19 không khởi động được | requirements.txt, Dockerfile |
| 9 | Key MinIO thêm `batch_id=…` | Nạp nhiều lần trong cùng ngày không ghi đè lô cũ | B02 |
| 10 | `Attendance = −2` coi là thiếu, điền bằng kỳ trước (chỉ clip > 100) | −2 là mã lỗi (kỳ trước / sau ~86%); clip về 0 tạo cú sụt giả | B03, B04, B07, THIET_KE_PIPELINE |

---

## 6. Cách làm tiếp khi quay lại

```powershell
docker compose up -d          # bật lại MinIO, PostgreSQL, MongoDB, MLflow
.venv\Scripts\activate
python -m src.ops.check_env       # phải báo "Tất cả đều sẵn sàng"
python -m pytest              # 45/45 đạt
```

* Muốn giải phóng RAM khi không làm: `docker compose stop` (dữ liệu vẫn giữ trong volume).
* `.env` chỉ có trên máy này (mật khẩu ngẫu nhiên). Thành viên khác: `copy .env.example .env` rồi tự đặt mật khẩu.

---

## 7. Vấn đề còn mở

- [ ] Các thành viên khác chưa thử dựng lại môi trường trên máy của mình (tiêu chí cuối của B1).
- [ ] Tiêu chí thành công ở B0 (Recall ≥ 0,80, PR-AUC) là đề xuất, cần chốt sau khi có baseline ở B11.
- [ ] Dòng `FAILED` thử nghiệm trong `ingestion_log`: giữ làm bằng chứng hay xóa trước khi demo.
