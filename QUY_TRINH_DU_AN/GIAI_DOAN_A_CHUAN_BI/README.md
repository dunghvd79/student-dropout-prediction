# GIAI ĐOẠN A – CHUẨN BỊ
[← Về tổng quan quy trình](../README.md) · Giai đoạn tiếp theo: [B – Kỹ thuật dữ liệu (ETL) →](../GIAI_DOAN_B_KY_THUAT_DU_LIEU_ETL/README.md)

## Mục tiêu giai đoạn
Trước khi chạm vào dữ liệu, nhóm cần **thống nhất bài toán** (dự đoán cái gì, cho ai, đo bằng gì) và **dựng một môi trường giống nhau cho mọi thành viên**, để mọi kết quả về sau đều tái lập được.

## Các bước

| Bước | Tên | Lý thuyết chính | Output |
|:---:|---|---|---|
| [**B0**](./B00_XAC_DINH_BAI_TOAN.md) | Xác định bài toán & tiêu chí thành công | CRISP-DM, Early Warning System, dữ liệu person-period, ma trận nhầm lẫn, Precision/Recall/PR-AUC | Problem statement, chỉ số & tiêu chí thành công |
| [**B1**](./B01_DUNG_MOI_TRUONG.md) | Dựng môi trường làm việc | Container & Docker, docker-compose, môi trường ảo, Infrastructure as Code, quản lý bí mật | `requirements.txt`, `docker-compose.yml`, 4 dịch vụ chạy |

## Input → Output của cả giai đoạn
* **Input:** Đề bài học phần, bài giảng, tệp `academic_survival_longitudinal.csv`, máy cá nhân.
* **Output:** Định nghĩa bài toán đã chốt + môi trường chạy được (MinIO, PostgreSQL, MongoDB, MLflow; Streamlit thêm ở B15) + cấu trúc thư mục dự án.

## Điều kiện để sang Giai đoạn B
- [ ] Cả nhóm thống nhất nhãn, đơn vị dự đoán, chỉ số chính (PR-AUC) và tiêu chí thành công.
- [ ] `docker compose ps` cho thấy đủ 4 dịch vụ (MinIO, PostgreSQL, MongoDB, MLflow) đang chạy và `python -m src.ops.check_env` báo sẵn sàng trên máy mọi thành viên. Streamlit được thêm ở B15.
