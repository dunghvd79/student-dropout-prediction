# BƯỚC 17. BÁO CÁO TỔNG KẾT & BẢO VỆ ĐỀ TÀI
**Giai đoạn F – Kết thúc** · [← Giai đoạn F](./README.md) · [Về tổng quan](../README.md)

---

## 1. Nhiệm vụ
Tổng hợp toàn bộ kết quả thành báo cáo, slide và demo; đóng gói repo để chạy lại được; chuẩn bị trả lời câu hỏi của giảng viên.

---

## 2. Cơ sở lý thuyết

### 2.1. Tính tái lập (Reproducibility)
Một kết quả khoa học chỉ đáng tin khi **người khác làm lại được**. Với dự án dữ liệu, cần đủ 4 thành phần:

| Thành phần | Cách bảo đảm trong dự án |
|---|---|
| **Dữ liệu** | Bản thô bất biến trong MinIO + MD5 trong `ingestion_log` |
| **Code** | Git, tag phiên bản nộp bài (`v1.0`) |
| **Môi trường** | `requirements.txt` ghim phiên bản + `docker-compose.yml` |
| **Ngẫu nhiên** | `random_state = 42`; danh sách sinh viên tập Test lưu trong `data/splits/` |

### 2.2. Kể chuyện bằng dữ liệu (Data Storytelling)
* Báo cáo tốt không liệt kê mọi thứ đã làm, mà dẫn người đọc theo **một mạch**: *Vấn đề → Dữ liệu → Phát hiện → Giải pháp → Kết quả → Hành động*.
* Mỗi biểu đồ cần **một thông điệp** ghi ngay trên tiêu đề, ví dụ "Áp lực tài chính ≥ 10 làm tỷ lệ bỏ học tăng gấp 10 lần", thay vì chỉ ghi "Biểu đồ Financial_Stress".
* Mở đầu bằng **kết quả chính** (executive summary), chi tiết kỹ thuật để sau.

### 2.3. Báo cáo trung thực
* Báo cáo kết quả **trên tập Test chưa từng dùng**, kể cả khi thấp hơn kỳ vọng.
* Báo cáo **trung bình ± độ lệch chuẩn** của CV, không chỉ con số tốt nhất.
* So sánh với **baseline** để thấy mô hình thực sự đem lại bao nhiêu giá trị.
* Nêu rõ **hạn chế**: dữ liệu có thể là dữ liệu mô phỏng; kết luận là liên quan, không phải nhân quả; các ngưỡng là đề xuất.

### 2.4. Hướng phát triển (nêu trong phần kết luận)
* **Survival Analysis:** mô hình Cox Proportional Hazards hoặc discrete-time hazard để dùng **trực tiếp** dữ liệu bị cắt thay vì loại bỏ; dự đoán **khi nào** sinh viên có nguy cơ bỏ học, không chỉ "kỳ sau có bỏ học không".
* **Mô hình chuỗi:** LSTM / GRU / Transformer trên chuỗi các kỳ.
* **Apache Spark:** khi dữ liệu vượt RAM một máy (log LMS thô nhiều năm, hàng chục GB).
* **Apache Flink / Kafka:** cảnh báo thời gian thực từ luồng sự kiện LMS.
* **Đánh giá can thiệp:** thí nghiệm A/B để đo hiệu quả **thực tế** của việc hỗ trợ sinh viên được cảnh báo.

---

## 3. Input
Output của B0 – B16.

---

## 4. Biến đổi
1. **Viết báo cáo cuối kỳ** theo cấu trúc:
   1. Tóm tắt (kết quả chính trong 1 trang)
   2. Giới thiệu & bài toán (B0)
   3. Dữ liệu & chất lượng dữ liệu (B2 – B3)
   4. Kiến trúc hệ thống & lưu trữ Polyglot (B1, B5)
   5. Làm sạch & đặc trưng chiều dọc (B4, B7)
   6. EDA & khai phá dữ liệu (B6, B8)
   7. Mô hình học máy & đánh giá (B9 – B12)
   8. Giải thích mô hình (B13)
   9. Triển khai, dashboard & vận hành (B14 – B16)
   10. Kết luận, hạn chế, hướng phát triển
2. **Slide** 15 – 20 trang, theo đúng mạch trên; mỗi slide một thông điệp.
3. **Kịch bản demo** (5 phút): chạy `python -m src.ops.run_pipeline` → mở MLflow (so sánh runs, model Production) → mở Power BI (tổng quan, danh sách đỏ) → tra cứu 1 sinh viên rủi ro cao trên Streamlit (quỹ đạo + SHAP).
4. **Quay video demo dự phòng** phòng khi máy trình chiếu gặp sự cố.
5. **Chuẩn bị Q&A:** tổng hợp mục "Câu hỏi bảo vệ" của tất cả các bước, cộng với bảng câu hỏi trong [`PROJECT_OVERVIEW.md`](../../PROJECT_OVERVIEW.md) mục 6.
6. **Đóng gói repo:** README hướng dẫn chạy lại từ đầu (`docker compose up -d` → `pip install -r requirements.txt` → `python src/ops/run_pipeline.py`); gắn tag Git `v1.0`.

---

## 5. Output
* `reports/final_report.docx` / `.pdf`.
* Slide trình bày, video demo.
* Repo hoàn chỉnh có tag `v1.0`.

## 6. Công cụ / File thực hiện
Word / Google Docs, PowerPoint / Google Slides, OBS (quay màn hình), Git.

## 7. Tiêu chí hoàn thành
- [ ] Một người ngoài nhóm làm theo README chạy lại được toàn bộ pipeline và ra cùng kết quả.
- [ ] Mọi thành viên trả lời được các câu hỏi bảo vệ ở mọi bước.

---

## 8. Bộ câu hỏi bảo vệ tổng hợp (ôn tập nhanh)

| Câu hỏi | Xem tại |
|---|---|
| Vì sao chọn đề tài, điểm khác biệt của dữ liệu? | [`PROJECT_OVERVIEW.md`](../../PROJECT_OVERVIEW.md) mục 6, [B0](../GIAI_DOAN_A_CHUAN_BI/B00_XAC_DINH_BAI_TOAN.md) |
| Vì sao không dùng Accuracy? | [B0](../GIAI_DOAN_A_CHUAN_BI/B00_XAC_DINH_BAI_TOAN.md) |
| Vì sao dùng Docker? | [B1](../GIAI_DOAN_A_CHUAN_BI/B01_DUNG_MOI_TRUONG.md) |
| Vì sao Batch, vì sao cần MinIO? | [B2](../GIAI_DOAN_B_KY_THUAT_DU_LIEU_ETL/B02_THU_THAP_NAP_DU_LIEU_THO.md) |
| Vì sao không chặn `Financial_Stress` về 5? | [B3](../GIAI_DOAN_B_KY_THUAT_DU_LIEU_ETL/B03_KIEM_TRA_CHAT_LUONG_DU_LIEU.md) |
| `Family_Income` không đổi qua các kỳ, sao không bfill? (rò rỉ phát hiện nhờ SHAP) | [B4](../GIAI_DOAN_B_KY_THUAT_DU_LIEU_ETL/B04_LAM_SACH_DU_LIEU.md) |
| Vì sao cần cả PostgreSQL và MongoDB? | [B5](../GIAI_DOAN_B_KY_THUAT_DU_LIEU_ETL/B05_NAP_KHO_POLYGLOT.md) |
| Tương quan có phải nhân quả? | [B6](../GIAI_DOAN_C_PHAN_TICH_KHAI_PHA/B06_PHAN_TICH_KHAM_PHA_EDA.md) |
| Điểm mới của đặc trưng chiều dọc? | [B7](../GIAI_DOAN_C_PHAN_TICH_KHAI_PHA/B07_TRICH_XUAT_DAC_TRUNG.md) |
| Confidence và Lift khác nhau thế nào? | [B8](../GIAI_DOAN_C_PHAN_TICH_KHAI_PHA/B08_KHAI_PHA_DU_LIEU.md) |
| Chống overfitting do dữ liệu lặp? Vì sao bỏ dòng Censored? | [B9](../GIAI_DOAN_D_HOC_MAY/B09_CHIA_TAP_DU_LIEU.md) |
| Vì sao không SMOTE từ đầu? | [B10](../GIAI_DOAN_D_HOC_MAY/B10_TIEN_XU_LY_MAT_CAN_BANG.md) |
| Vì sao chọn Logistic Regression mà không phải XGBoost? Đặc trưng chiều dọc có giúp không? | [B11](../GIAI_DOAN_D_HOC_MAY/B11_HUAN_LUYEN_TINH_CHINH.md) |
| Vì sao không dùng ngưỡng 0,5? | [B12](../GIAI_DOAN_D_HOC_MAY/B12_DANH_GIA_CHON_NGUONG.md) |
| SHAP khác feature importance thế nào? | [B13](../GIAI_DOAN_D_HOC_MAY/B13_GIAI_THICH_MO_HINH_SHAP.md) |
| Sửa lỗi xong lại đánh giá Test lần 2, có phải "nhìn Test nhiều lần"? | [B13](../GIAI_DOAN_D_HOC_MAY/B13_GIAI_THICH_MO_HINH_SHAP.md), [B12](../GIAI_DOAN_D_HOC_MAY/B12_DANH_GIA_CHON_NGUONG.md) |
| Vì sao không làm API thời gian thực? | [B14](../GIAI_DOAN_E_TRIEN_KHAI_VAN_HANH/B14_DU_DOAN_THEO_LO.md) |
| Vì sao dùng cả Power BI và Streamlit? | [B15](../GIAI_DOAN_E_TRIEN_KHAI_VAN_HANH/B15_TRUC_QUAN_HOA_DASHBOARD.md) |
| Khi nào huấn luyện lại mô hình? | [B16](../GIAI_DOAN_E_TRIEN_KHAI_VAN_HANH/B16_GIAM_SAT_VAN_HANH.md) |
| Vì sao không dùng Spark / Flink? | [`THIET_KE_PIPELINE.md`](../../THIET_KE_PIPELINE.md) mục 6 |
