# BƯỚC 1. DỰNG MÔI TRƯỜNG LÀM VIỆC
**Giai đoạn A – Chuẩn bị** · [← Bước 0](./B00_XAC_DINH_BAI_TOAN.md) · [Giai đoạn B →](../GIAI_DOAN_B_KY_THUAT_DU_LIEU_ETL/README.md)

---

## 1. Nhiệm vụ
Chuẩn bị **môi trường giống hệt nhau** cho mọi thành viên, để ai cũng chạy lại được toàn bộ pipeline và ra cùng kết quả (**tính tái lập – reproducibility**).

---

## 2. Cơ sở lý thuyết

### 2.1. Vấn đề "chạy trên máy em thì được"
Kết quả của một dự án dữ liệu phụ thuộc vào: phiên bản Python, phiên bản thư viện, phiên bản CSDL, cấu hình hệ điều hành. Nếu mỗi người cài một kiểu, cùng một đoạn code có thể cho kết quả khác nhau hoặc không chạy. Giải pháp gồm hai tầng:

| Tầng | Công cụ | Cô lập cái gì |
|---|---|---|
| Thư viện Python | **Môi trường ảo** (`venv`) + `requirements.txt` ghim phiên bản | Gói Python của dự án tách khỏi hệ thống |
| Dịch vụ hạ tầng (CSDL, MinIO, MLflow) | **Container** (Docker) + `docker-compose.yml` | Toàn bộ phần mềm dịch vụ và cấu hình của nó |

### 2.2. Container và Máy ảo (VM)
* **Máy ảo:** giả lập cả phần cứng, mỗi VM chạy một hệ điều hành riêng, nên nặng (GB) và khởi động chậm (phút).
* **Container:** dùng chung nhân (kernel) hệ điều hành của máy chủ, chỉ đóng gói ứng dụng và thư viện, nên nhẹ (MB) và khởi động trong vài giây.
* **Khái niệm Docker:**
  * **Image:** bản mẫu chỉ đọc (ví dụ `postgres:16`).
  * **Container:** một tiến trình đang chạy từ image.
  * **Volume:** vùng lưu dữ liệu bền vững bên ngoài container. Xóa container không mất dữ liệu CSDL.
  * **Network:** các container trong cùng compose gọi nhau bằng tên dịch vụ (ví dụ `postgres:5432`).
* Bài giảng Lecture 3 có phần thực hành "chạy Docker trên các hệ thống CSDL khác nhau". Bước này áp dụng trực tiếp phần đó.

### 2.3. Infrastructure as Code (IaC) với docker-compose
* Toàn bộ hạ tầng được **mô tả bằng một file văn bản** (`docker-compose.yml`), commit vào Git cùng mã nguồn.
* Lợi ích: dựng lại hệ thống bằng **một lệnh** (`docker compose up -d`), theo dõi được lịch sử thay đổi hạ tầng, và chuyển lên cloud dễ dàng.

### 2.4. Quản lý cấu hình và bí mật (12-Factor App)
* **Cấu hình** (đường dẫn, ngưỡng, `random_state`) tách khỏi code, đặt trong `config/settings.yaml`.
* **Bí mật** (mật khẩu CSDL, access key MinIO) đặt trong biến môi trường / file `.env`, **không commit** lên Git. Chỉ commit `.env.example` làm mẫu.

### 2.5. Vai trò của 5 dịch vụ trong kiến trúc

| Dịch vụ | Loại hệ thống (theo Lecture 3) | Vai trò |
|---|---|---|
| **MinIO** | Object Storage (tương thích S3) | Raw Data Lake; nơi lưu artifact của MLflow |
| **PostgreSQL** | Relational DB (ACID) | Dữ liệu tĩnh, kết quả dự đoán, nhật ký, backend store của MLflow |
| **MongoDB** | Document DB (schema linh hoạt) | Dữ liệu theo từng học kỳ |
| **MLflow** | Nền tảng MLOps | Theo dõi thí nghiệm, Model Registry |
| **Streamlit** | Web app Python | Tra cứu sinh viên và giải thích SHAP |

---

## 3. Input
Máy cá nhân (khuyến nghị ≥ 8 GB RAM), Docker Desktop, Python ≥ 3.10, repo Git.

---

## 4. Biến đổi
1. Tạo môi trường ảo **Python 3.12** bằng `uv`: `uv venv --python 3.12 --seed .venv` → kích hoạt `.venv\Scripts\activate`. Không dùng Python 3.14 vì một số thư viện (shap, lightgbm, mlflow) chưa hỗ trợ ổn định.
2. Tạo `requirements.txt` (ghim phiên bản) và cài đặt bằng `uv pip install -r requirements.txt`:
   * Xử lý dữ liệu: `pandas`, `numpy`, `pyarrow`
   * Kết nối CSDL: `sqlalchemy`, `psycopg2-binary`, `pymongo`, `minio`
   * Học máy: `scikit-learn`, `imbalanced-learn`, `xgboost`, `lightgbm`, `shap`, `optuna`
   * Khai phá dữ liệu: `mlxtend`
   * Theo dõi mô hình: `mlflow`
   * Trực quan hóa: `matplotlib`, `seaborn`, `plotly`, `streamlit`, `jupyter`
3. Tạo `docker-compose.yml` gồm các dịch vụ:

   | Dịch vụ | Image | Cổng trên máy | Volume |
   |---|---|---|---|
   | MinIO | `bitnamilegacy/minio:2024.12.18` | 9000 (API), 9001 (console) | `minio_data` |
   | PostgreSQL | `postgres:16.6` | **5433** | `pg_data` |
   | MongoDB | `mongo:7.0.16` | **27018** | `mongo_data` |
   | MLflow Tracking Server | build từ `docker/mlflow/Dockerfile` | 5000 | (dùng PostgreSQL + MinIO) |
   | Streamlit | – | 8501 | Thêm ở B15; khi phát triển chạy trực tiếp từ `.venv` |

   **Ghi chú thực tế khi dựng:**
   * Image chính thức `minio/minio` đã bị gỡ khỏi Docker Hub và quay.io, nên dùng bản đóng gói của Bitnami (cùng phiên bản MinIO). Biến `MINIO_DEFAULT_BUCKETS=raw,processed,mlflow` tự tạo 3 bucket khi khởi động.
   * Cổng **5433** và **27018** được chọn vì 5432 và 27017 thường đã bị PostgreSQL / MongoDB khác trên máy chiếm. Đổi trong `.env` nếu cần.
   * PostgreSQL có thêm database `mlflow` (tạo bởi `docker/postgres-init/01_create_mlflow_db.sql`) để bảng của MLflow tách khỏi bảng nghiệp vụ.
   * Ghim `alembic==1.14.0` và `sqlalchemy==2.0.36`: bản Alembic mới hơn không chạy được với MLflow 2.19.

4. Tạo `.env` từ `.env.example` (không commit; đổi mật khẩu).
5. Tạo `config/settings.yaml`: đường dẫn, `random_state = 42`, ngưỡng rủi ro (0,3 / 0,6), tỷ lệ Test (0,2); `src/config.py` đọc settings + `.env` và tạo chuỗi kết nối dùng chung.
6. Tạo cấu trúc thư mục dự án; thêm `data/`, `mlruns/`, `mlartifacts/` vào `.gitignore`.
7. Chạy `python -m src.check_env` để kiểm tra thư viện, dữ liệu gốc, MinIO, PostgreSQL, MongoDB và MLflow.

---

## 5. Output
* `requirements.txt`, `docker-compose.yml`, `docker/`, `.env.example`, `config/settings.yaml`, `src/config.py`, `src/check_env.py`.
* 4 container đang chạy (MinIO, PostgreSQL, MongoDB, MLflow); các thư mục `src/`, `notebooks/`, `config/`, `sql/`, `app/`, `dashboards/`, `reports/`, `data/`.

## 6. Công cụ / File thực hiện
Docker Desktop, `docker compose`, `pip`, Git.

## 7. Tiêu chí hoàn thành
- [x] Chạy `docker compose up -d` và `uv pip install -r requirements.txt` thành công.
- [x] `python -m src.check_env` báo "Tất cả đều sẵn sàng" (đã kiểm tra 2026-10-11).
- [x] MLflow ghi được artifact vào bucket `mlflow` của MinIO.
- [ ] Mọi thành viên khác trong nhóm lặp lại được trên máy của mình.

---

## 8. Câu hỏi bảo vệ thường gặp
**Hỏi:** Vì sao dùng Docker mà không cài trực tiếp PostgreSQL, MongoDB lên máy?  
**Đáp:** Để mọi thành viên có cùng phiên bản và cấu hình; dựng lại cả hệ thống bằng một lệnh; dễ chuyển lên cloud; không làm "bẩn" máy cá nhân.

**Hỏi:** Xóa container thì có mất dữ liệu không?  
**Đáp:** Không. Dữ liệu CSDL nằm trong Docker volume, tách khỏi vòng đời của container.
