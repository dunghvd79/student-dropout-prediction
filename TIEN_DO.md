# TIẾN ĐỘ DỰ ÁN
**Cập nhật lần cuối:** 2026-10-24 · **Commit mới nhất:** "Buoc 4: lam sach du lieu" (xem `git log`)  
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
| | B5 Nạp kho Polyglot | ⏭️ **Làm tiếp theo** |
| **C – Phân tích & Khai phá** | B6 EDA | ⬜ Chưa làm |
| | B7 Trích xuất đặc trưng | ⬜ Chưa làm |
| | B8 Khai phá dữ liệu | ⬜ Chưa làm |
| **D – Học máy** | B9 Chia tập | ⬜ Chưa làm |
| | B10 Tiền xử lý & mất cân bằng | ⬜ Chưa làm |
| | B11 Huấn luyện & tinh chỉnh | ⬜ Chưa làm |
| | B12 Đánh giá & chọn ngưỡng | ⬜ Chưa làm |
| | B13 Giải thích SHAP | ⬜ Chưa làm |
| **E – Triển khai & Vận hành** | B14 Dự đoán theo lô | ⬜ Chưa làm |
| | B15 Dashboard | ⬜ Chưa làm |
| | B16 Giám sát & vận hành | ⬜ Chưa làm |
| **F – Kết thúc** | B17 Báo cáo & bảo vệ | ⬜ Chưa làm |

**Hoàn thành: 5 / 18 bước** (Giai đoạn A xong; Giai đoạn B: 3/4).

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
* Gender đổi cách ghi 4.648 dòng; clip `Attendance` 249; điền `Family_Income` 3.387 (còn 217 dòng / 199 sinh viên → `Income_Missing`); điền `LMS_Logins` 658 (còn 209).
* 7/7 kiểm tra sau làm sạch đạt; chạy 2 lần cho file Parquet giống hệt (MD5 `deacca08…`); file hỏng bị chặn. 31/31 unit test đạt.
* File: `src/etl/clean.py`, `tests/test_clean.py`, `reports/cleaning_log.md`.

---

## 3. Việc tiếp theo: B5 – Nạp kho Polyglot

Chi tiết: [`B05_NAP_KHO_POLYGLOT.md`](./QUY_TRINH_DU_AN/GIAI_DOAN_B_KY_THUAT_DU_LIEU_ETL/B05_NAP_KHO_POLYGLOT.md)

- [ ] `sql/02_core_tables.sql`: bảng `students`, `financial_profiles`, `predictions` (IF NOT EXISTS).
- [ ] `src/etl/load.py`: đọc `clean_semesters.parquet` → `students` (20.000), `financial_profiles` (20.000) bằng upsert; MongoDB `academic_semesters` (79.239 document lồng nhau) bằng `bulk_write` + unique index `(student_id, semester)`.
- [ ] Đối soát số lượng; mọi `student_id` trong MongoDB có trong `students`; chạy lại lần 2 số lượng không đổi.
- [ ] Hàm `load_analytic_table()` trả về dữ liệu giống hệt `clean_semesters.parquet`.
- [ ] Unit test cho phần chuyển dòng → document.

Sau B5: hoàn tất Giai đoạn B, chuyển sang Giai đoạn C (B6 EDA).

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
* MinIO `raw`: 1 object (lô `20261011T085849Z_7df267`).
* PostgreSQL `ingestion_log`: 3 dòng (1 `SUCCESS`, 1 `SKIPPED` khi chạy lại, 1 `FAILED` từ file hỏng dùng để thử).
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

---

## 6. Cách làm tiếp khi quay lại

```powershell
docker compose up -d          # bật lại MinIO, PostgreSQL, MongoDB, MLflow
.venv\Scripts\activate
python -m src.ops.check_env       # phải báo "Tất cả đều sẵn sàng"
python -m pytest              # 31/31 đạt
```

* Muốn giải phóng RAM khi không làm: `docker compose stop` (dữ liệu vẫn giữ trong volume).
* `.env` chỉ có trên máy này (mật khẩu ngẫu nhiên). Thành viên khác: `copy .env.example .env` rồi tự đặt mật khẩu.

---

## 7. Vấn đề còn mở

- [ ] Các thành viên khác chưa thử dựng lại môi trường trên máy của mình (tiêu chí cuối của B1).
- [ ] Tiêu chí thành công ở B0 (Recall ≥ 0,80, PR-AUC) là đề xuất, cần chốt sau khi có baseline ở B11.
- [ ] Dòng `FAILED` thử nghiệm trong `ingestion_log`: giữ làm bằng chứng hay xóa trước khi demo.
