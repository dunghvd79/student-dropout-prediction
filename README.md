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

---

## 🚀 Kiến trúc Pipeline tổng thể

```text
SIS / LMS / Survey (CSV/API)
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

## 📊 Tập dữ liệu (Dataset)
* Tệp dữ liệu gốc: `academic_survival_longitudinal.csv`
* Quy mô: **79.239 bản ghi** của gần **20.000 sinh viên**, theo dõi qua tối đa 8 học kỳ.
