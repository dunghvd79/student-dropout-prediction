# BƯỚC 14. DỰ ĐOÁN THEO LÔ (BATCH INFERENCE)
**Giai đoạn E – Triển khai & Vận hành** · [← Giai đoạn E](./README.md) · [Bước 15 →](./B15_TRUC_QUAN_HOA_DASHBOARD.md)

---

## 1. Nhiệm vụ
Chấm điểm rủi ro cho **sinh viên đang theo học** và lưu kết quả để dashboard sử dụng.

---

## 2. Cơ sở lý thuyết

### 2.1. Các kiểu phục vụ mô hình (Model Serving)

| | **Batch inference** | **Online (real-time) inference** |
|---|---|---|
| Cách chạy | Chấm điểm **hàng loạt** theo lịch, lưu kết quả vào CSDL | Gọi API, trả kết quả **ngay** cho từng yêu cầu |
| Độ trễ | Phút – giờ (chấp nhận được) | Mili giây |
| Hạ tầng | Script + scheduler | Web service (FastAPI), luôn chạy, cần scale |
| Phù hợp | Báo cáo định kỳ, danh sách cảnh báo | Gợi ý sản phẩm, chống gian lận |

**Dự án chọn Batch:** dữ liệu học kỳ thay đổi theo đợt, nên cán bộ chỉ cần danh sách cập nhật hàng tuần; Batch rẻ, đơn giản và dễ kiểm tra.

### 2.2. Training–serving skew
* Là hiện tượng **dữ liệu lúc dự đoán được xử lý khác với lúc huấn luyện** (khác công thức đặc trưng, khác thứ tự cột, khác cách điền khuyết). Mô hình vẫn chạy nhưng **kết quả sai âm thầm**.
* **Cách phòng tránh trong dự án:**
  1. Dùng **cùng** `src/analysis/features.py` cho huấn luyện và dự đoán.
  2. Dùng **cùng** `feature_spec.json` (danh sách và thứ tự cột) và kiểm tra schema trước khi dự đoán.
  3. Tiền xử lý nằm **bên trong** Pipeline đã lưu (B10), không viết lại ở bước dự đoán.

### 2.3. Feature contract / Feature store (khái niệm)
* **Feature store** là kho trung tâm lưu định nghĩa và giá trị đặc trưng, dùng chung cho huấn luyện và phục vụ.
* Ở quy mô dự án, `feature_spec.json` + `feature_table.parquet` đóng vai trò một **feature store tối giản**: một nguồn sự thật duy nhất cho đặc trưng.

### 2.4. Ghi kết quả lũy đẳng và có phiên bản
* Mỗi lần chạy có `run_id` riêng; khóa `(run_id, student_id)` bảo đảm chạy lại cùng `run_id` **không nhân đôi**.
* Lưu cả `model_version`, nhờ đó luôn biết điểm rủi ro do mô hình nào sinh ra (**truy vết – auditability**), và so sánh được kết quả giữa các phiên bản.
* Giữ lịch sử nhiều lần chạy cho phép theo dõi **rủi ro của một sinh viên thay đổi theo thời gian**.

### 2.5. Phân tầng rủi ro (Risk Stratification)
* Biến xác suất liên tục thành **mức hành động**: Thấp (< 0,3) · Trung bình (0,3 – 0,6) · Cao (≥ 0,6).
* Mỗi mức gắn với một **quy trình can thiệp** khác nhau, ví dụ: Cao thì cố vấn liên hệ trong tuần; Trung bình thì gửi email / theo dõi; Thấp thì không cần làm gì.
* Mốc có thể điều chỉnh theo **năng lực can thiệp** của nhà trường (số cố vấn có hạn).

### 2.6. Đối tượng được chấm điểm
* Mô hình học trên các dòng **đã biết kết cục** và dự đoán cho các dòng **chưa biết kết cục**: kỳ mới nhất của sinh viên đang theo học (`Censored = 1`).
* Không chấm điểm sinh viên đã bỏ học hoặc đã tốt nghiệp.

---

## 3. Input
* **Scoring set:** 11.115 dòng `Censored = 1` (kỳ 1: 2.072 · kỳ 2: 1.892 · kỳ 3: 1.703 · kỳ 4: 1.584 · kỳ 5: 1.380 · kỳ 6: 1.289 · kỳ 7: 1.195).
* Mô hình `models:/dropout_model/Production` từ MLflow; `feature_spec.json`; mốc rủi ro trong `settings.yaml`.

---

## 4. Biến đổi
1. Lấy đặc trưng của scoring set từ `feature_table.parquet`. Ở lần chạy định kỳ thực tế, chạy lại B2 → B5 → B7 cho dữ liệu kỳ mới trước.
2. **Kiểm tra schema** đặc trưng khớp `feature_spec.json` (tên, thứ tự, kiểu).
3. `predict_proba` → `risk_score`.
4. Gán `risk_level` theo mốc trong `settings.yaml`.
5. Gọi `top_reasons()` → `top_reason_1..3`.
6. Ghi vào `predictions` kèm `run_id`, `run_date`, `model_version` (upsert theo `(run_id, student_id)`).
7. **Kiểm tra:** không có `risk_score` NULL; phân bố mức rủi ro hợp lý so với tỷ lệ bỏ học lịch sử (~10%).

---

## 5. Output
* Bảng `predictions`: 11.115 dòng mỗi lần chạy.
* Log lần chạy: thời gian, số dòng, phân bố mức rủi ro (ghi vào `pipeline_runs` ở B16).

## 6. Công cụ / File thực hiện
`src/ml/predict.py` (`mlflow`, `pandas`, `sqlalchemy`, `shap`).

## 7. Tiêu chí hoàn thành
- [ ] Mọi sinh viên trong scoring set có điểm rủi ro và lý do.
- [ ] Thời gian chạy < 2 phút.
- [ ] Chạy lại cùng `run_id` không nhân đôi dòng.

---

## 8. Câu hỏi bảo vệ thường gặp
**Hỏi:** Vì sao không làm API dự đoán thời gian thực?  
**Đáp:** Dữ liệu cập nhật theo đợt và can thiệp diễn ra theo tuần, nên API thời gian thực không đem lại giá trị mà tăng chi phí vận hành. Kiến trúc vẫn mở rộng được: bọc Pipeline đã lưu bằng FastAPI.

**Hỏi:** Làm sao chắc dữ liệu lúc dự đoán được xử lý giống lúc huấn luyện?  
**Đáp:** Dùng chung code đặc trưng, chung `feature_spec.json`, và tiền xử lý nằm trong Pipeline đã lưu cùng mô hình. Trước khi dự đoán có bước kiểm tra schema.
