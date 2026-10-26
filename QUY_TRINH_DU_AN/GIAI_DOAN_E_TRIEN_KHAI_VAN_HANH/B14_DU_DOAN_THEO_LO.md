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
* Biến xác suất liên tục thành **mức hành động**. Dự án **không** dùng mốc cố định kiểu 0,3 / 0,6 (với tỷ lệ bỏ học 10%, mốc này chỉ bắt ~34% ca bỏ học) mà dùng mốc theo chính sách, chọn trên OOF Train ở B12 (`config/risk_thresholds.json`):
  * **Cao** ≥ 0,318: ngưỡng nhỏ nhất đạt Precision ≥ 0,50, tức ít nhất 1/2 cảnh báo là đúng.
  * **Trung bình** ≥ 0,072: ngưỡng lớn nhất vẫn đạt Recall ≥ 0,80.
  * **Thấp**: còn lại.
* Mỗi mức gắn với một **quy trình can thiệp** khác nhau, ví dụ: Cao thì cố vấn liên hệ trong tuần; Trung bình thì gửi email / theo dõi; Thấp thì không cần làm gì.
* Mốc có thể điều chỉnh theo **năng lực can thiệp** của nhà trường (số cố vấn có hạn).

### 2.6. Đối tượng được chấm điểm
* Mô hình học trên các dòng **đã biết kết cục** và dự đoán cho các dòng **chưa biết kết cục**: kỳ mới nhất của sinh viên đang theo học (`Censored = 1`).
* Không chấm điểm sinh viên đã bỏ học hoặc đã tốt nghiệp.

---

## 3. Input
* **Scoring set:** 11.115 dòng `Censored = 1` (kỳ 1: 2.072 · kỳ 2: 1.892 · kỳ 3: 1.703 · kỳ 4: 1.584 · kỳ 5: 1.380 · kỳ 6: 1.289 · kỳ 7: 1.195).
* Mô hình `dropout_model` có alias **`production`** trong MLflow Model Registry (MLflow 2.x dùng alias thay cho stage "Production"); `feature_spec.json`; mốc rủi ro trong `config/risk_thresholds.json`; tập Train làm nền cho SHAP.

---

## 4. Biến đổi
1. Lấy đặc trưng của scoring set từ `feature_table.parquet`. Ở lần chạy định kỳ thực tế, chạy lại B2 → B5 → B7 cho dữ liệu kỳ mới trước.
2. **Kiểm tra schema** (sai thì dừng, không ghi gì):
   * Đặc trưng khớp `feature_spec.json` (tên, thứ tự, kiểu số, cột nhị phân chỉ 0/1).
   * Đặc trưng khớp **cột mô hình đã học** (`feature_names_in_`).
   * Không có nhóm phân loại mà mô hình chưa thấy. `OneHotEncoder(handle_unknown="ignore")` sẽ âm thầm coi nhóm lạ là "không thuộc nhóm nào", nên phải chặn trước.
3. `predict_proba` → `risk_score`.
4. Gán `risk_level` theo mốc trong `config/risk_thresholds.json`.
5. `explain()` + `top_reasons()` (B13) → `top_reason_1..3` dạng "Nhóm: mô tả bằng giá trị thật". Sinh viên không có nhóm nào đẩy rủi ro lên thì ghi "Không có yếu tố nào cao hơn mức trung bình".
6. Ghi vào `predictions` kèm `run_id`, `run_date`, `model_version` (upsert theo `(run_id, student_id)`, trong một transaction). `run_id` mặc định là `<ngày>-v<phiên bản>`: chạy lại trong ngày với cùng mô hình thì ghi đè; khác ngày hoặc khác mô hình thì thành lần chạy mới, giữ lịch sử.
7. **Kiểm tra:** không có `risk_score` NULL; phân bố mức rủi ro hợp lý so với tỷ lệ bỏ học lịch sử (~10%).

---

## 5. Output
* Bảng `predictions`: 11.115 dòng mỗi lần chạy.
* `reports/scoring_report.md` (sinh tự động): phân bố mức rủi ro, theo học kỳ, lý do số 1 của mức Cao, kiểm tra, 5 sinh viên rủi ro cao nhất. Log vào `pipeline_runs` để ở B16.

**Kết quả** (`run_id = 20261026-v2`, `dropout_model` v2):

| Mức | Số sinh viên | Tỷ lệ | Tỷ lệ trên Test (B12) |
|---|---:|---:|---:|
| Cao | 439 | 3,9% | 5,7% |
| Trung bình | 3.978 | 35,8% | 36,0% |
| Thấp | 6.698 | 60,3% | 58,3% |

* Xác suất trung bình 8,9%, so với tỷ lệ bỏ học kỳ sau 10,2% trên tập có nhãn. Mức Cao ít hơn Test, vì sinh viên đang theo học là nhóm "còn trụ lại" ở kỳ mới nhất. Chưa có nhãn để đối chiếu; B16 sẽ so dự đoán với kết cục thật khi có dữ liệu kỳ sau.
* Rủi ro tăng theo học kỳ: xác suất trung bình 6,1% ở kỳ 1, 10,7% ở kỳ 7. Điều này khớp xu hướng ở EDA.
* Lý do số 1 ở mức Cao: kết quả học tập 48,5%, trượt môn 33,7%, áp lực tài chính 16,9%. Tức 3 hướng can thiệp: cố vấn học tập, phụ đạo, hỗ trợ tài chính.
* Ví dụ: `STU_06912` (kỳ 6, rủi ro 0,918) có 3 lý do:
  1. GPA kỳ này 0,79, tích lũy 1,54.
  2. Trượt 3 môn, tích lũy 8 môn.
  3. Áp lực tài chính 7,2 (tăng 0,7).

## 6. Công cụ / File thực hiện
* `src/ml/predict.py`: chạy `python -m src.ml.predict [--run-id ID] [--local]`. `--local` dùng `data/models/dropout_model.joblib` khi MLflow không chạy; đã kiểm tra cho cùng kết quả với bản trong Registry. Gồm:
  * `load_model`: lấy phiên bản đang mang alias `production` rồi tải đúng phiên bản đó.
  * `check_schema`, `build_predictions`, `upsert_predictions`.
  * `reconcile`: đối soát sau khi ghi.
* `tests/test_predict.py`: 6 unit test:
  * Schema đạt; phát hiện thiếu / thừa / sai thứ tự cột.
  * Phát hiện sai kiểu, nhị phân ngoài 0/1, nhóm lạ, `feature_spec` bị đổi sau khi train.
  * Bảng kết quả đúng cột; sinh viên không có lý do vẫn có dòng mặc định.
* Tổng 118/118 test đạt.

## 7. Tiêu chí hoàn thành (đã kiểm tra 2026-10-26)
- [x] Mọi sinh viên trong scoring set có điểm rủi ro và lý do (11.115 / 11.115; không có NULL; `risk_score` trong CSDL khớp kết quả tính).
- [x] Thời gian chạy < 2 phút (15 – 22 giây, gồm tải mô hình từ MLflow và tính SHAP).
- [x] Chạy lại cùng `run_id` không nhân đôi dòng (chạy 3 lần: vẫn 11.115 dòng, 1 `run_id`).

---

## 8. Câu hỏi bảo vệ thường gặp
**Hỏi:** Vì sao không làm API dự đoán thời gian thực?  
**Đáp:** Dữ liệu cập nhật theo đợt và can thiệp diễn ra theo tuần, nên API thời gian thực không đem lại giá trị mà tăng chi phí vận hành. Kiến trúc vẫn mở rộng được: bọc Pipeline đã lưu bằng FastAPI.

**Hỏi:** Làm sao chắc dữ liệu lúc dự đoán được xử lý giống lúc huấn luyện?  
**Đáp:** Dùng chung code đặc trưng, chung `feature_spec.json`, và tiền xử lý nằm trong Pipeline đã lưu cùng mô hình. Trước khi dự đoán có bước kiểm tra schema.
