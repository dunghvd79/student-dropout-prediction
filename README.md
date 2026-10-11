# 🎓 Student Dropout Prediction & Longitudinal Analytics

> **Dự đoán nguy cơ bỏ học của sinh viên đại học dựa trên dữ liệu theo chiều dọc**  
> *Học phần: Tích hợp và Phân tích Dữ liệu Lớn | Trường Đại học Phenikaa*

---

## 📌 Giới thiệu đề tài
Dự án tập trung xây dựng **Hệ thống Cảnh báo Sớm (Early Warning System - EWS)** nhằm phát hiện sớm sinh viên có nguy cơ bỏ học ở học kỳ kế tiếp. Điểm độc đáo của dự án là tiếp cận theo **quỹ đạo thời gian (Longitudinal Trajectory)** qua tối đa 8 học kỳ liên tiếp, kết hợp các khía cạnh:
* **Học tập:** Điểm trung bình (`Sem_GPA`), số môn trượt (`Failed_Courses`), số tín chỉ (`Course_Load`).
* **Hành vi & Tương tác:** Chuyên cần (`Attendance`), đăng nhập LMS (`LMS_Logins`), gặp cố vấn (`Advising_Visits`).
* **Kinh tế - Xã hội:** Áp lực tài chính (`Financial_Stress`), giờ làm thêm (`Work_Hours`), thu nhập gia đình (`Family_Income`).

---

## 📂 Danh mục tài liệu dự án

1. 📄 [**PROJECT_OVERVIEW.md**](./PROJECT_OVERVIEW.md): Tài liệu tổng quan toàn diện về đề tài, từ điển dữ liệu (22 thuộc tính), phương pháp luận và kịch bản bảo vệ trước hội đồng.
2. 🗄️ [**BAO_CAO_CSDL_GIUA_KY.md**](./BAO_CAO_CSDL_GIUA_KY.md): Báo cáo thiết kế cơ sở dữ liệu (PostgreSQL + MongoDB theo kiến trúc Polyglot Persistence) và phân tích quy mô dữ liệu tối thiểu cho Machine Learning.
3. ⚙️ [**THIET_KE_PIPELINE.md**](./THIET_KE_PIPELINE.md): Thiết kế Data Pipeline end-to-end (`Raw Data → Ingestion → ETL → Storage → ML → Visualization`).
4. 🧭 [**QUY_TRINH_DU_AN/**](./QUY_TRINH_DU_AN/README.md): Quy trình thực hiện chi tiết **6 giai đoạn / 18 bước** từ lúc bắt đầu đến khi kết thúc. Mỗi giai đoạn là một thư mục, mỗi bước là một file gồm Nhiệm vụ, Cơ sở lý thuyết, Input, Biến đổi, Output, Tiêu chí hoàn thành và Câu hỏi bảo vệ.
   * [A – Chuẩn bị](./QUY_TRINH_DU_AN/GIAI_DOAN_A_CHUAN_BI/README.md) (B0 – B1)
   * [B – Kỹ thuật dữ liệu (ETL)](./QUY_TRINH_DU_AN/GIAI_DOAN_B_KY_THUAT_DU_LIEU_ETL/README.md) (B2 – B5)
   * [C – Phân tích & Khai phá](./QUY_TRINH_DU_AN/GIAI_DOAN_C_PHAN_TICH_KHAI_PHA/README.md) (B6 – B8)
   * [D – Học máy](./QUY_TRINH_DU_AN/GIAI_DOAN_D_HOC_MAY/README.md) (B9 – B13)
   * [E – Triển khai & Vận hành](./QUY_TRINH_DU_AN/GIAI_DOAN_E_TRIEN_KHAI_VAN_HANH/README.md) (B14 – B16)
   * [F – Kết thúc](./QUY_TRINH_DU_AN/GIAI_DOAN_F_KET_THUC/README.md) (B17)

---

## 🚀 Kiến trúc Pipeline tổng thể

```text
SIS / LMS / Survey (CSV/API)
           │
           ▼
Raw Data Lake (MinIO Object Storage)
           │
           ▼
Python ETL Pipeline (Pandas / Data Cleaning)
           │
           ▼
Polyglot Storage (PostgreSQL + MongoDB)
           │
           ▼
Machine Learning & Tracking (XGBoost / Random Forest + MLflow)
           │
           ▼
Early Warning Dashboard (Power BI / Streamlit)
```

---

## 🛠️ Cài đặt & chạy môi trường

Yêu cầu: Docker Desktop, [uv](https://docs.astral.sh/uv/) (hoặc Python 3.12).

```powershell
# 1. Biến môi trường (đổi mật khẩu trong .env)
copy .env.example .env

# 2. Hạ tầng: MinIO, PostgreSQL, MongoDB, MLflow
docker compose up -d

# 3. Môi trường Python 3.12
uv venv --python 3.12 --seed .venv
.venv\Scripts\activate
uv pip install -r requirements.txt

# 4. Kiểm tra mọi thứ đã sẵn sàng
python -m src.check_env
```

| Dịch vụ | Địa chỉ |
|---|---|
| MinIO console | http://localhost:9001 (tài khoản trong `.env`) |
| MLflow UI | http://localhost:5000 |
| PostgreSQL | `localhost:5433` (database `dropout_ews`, `mlflow`) |
| MongoDB | `localhost:27018` |

> PostgreSQL và MongoDB dùng cổng 5433 / 27018 để không trùng với bản cài sẵn trên máy (5432 / 27017).

---

## 📊 Tập dữ liệu (Dataset)
* Tệp dữ liệu gốc: `academic_survival_longitudinal.csv`
* Quy mô: **79.239 bản ghi** của **20.000 sinh viên**, theo dõi qua 1 - 8 học kỳ (trung bình ~4 kỳ).
* Nhãn: `Target_Dropout_Next_Sem`, lớp bỏ học chiếm **8,7%** toàn bộ (10,2% trên tập có nhãn sau khi loại các dòng `Censored = 1`).
