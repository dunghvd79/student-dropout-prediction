# BƯỚC 15. TRỰC QUAN HÓA: POWER BI + STREAMLIT
**Giai đoạn E – Triển khai & Vận hành** · [← Bước 14](./B14_DU_DOAN_THEO_LO.md) · [Bước 16 →](./B16_GIAM_SAT_VAN_HANH.md)

---

## 1. Nhiệm vụ
Đưa kết quả tới người dùng cuối theo hai nhu cầu: **quản lý tổng quan** (Power BI) và **tra cứu từng sinh viên kèm giải thích** (Streamlit). Dự đoán chỉ có giá trị khi dẫn tới **hành động**.

---

## 2. Cơ sở lý thuyết

### 2.1. Thiết kế theo người dùng
| Người dùng | Câu hỏi | Loại dashboard | Công cụ |
|---|---|---|---|
| Lãnh đạo / Phòng Đào tạo | "Tình hình chung thế nào? Nhóm nào rủi ro nhất?" | **Chiến lược / phân tích**: KPI, xu hướng, phân bổ | Power BI |
| Cố vấn học tập / CTSV | "Hôm nay tôi cần liên hệ ai? Vì sao?" | **Tác nghiệp (operational)**: danh sách, chi tiết từng cá nhân | Power BI (danh sách) + Streamlit (chi tiết, SHAP) |

### 2.2. Nguyên tắc trực quan hóa
* **Tỷ lệ dữ liệu / mực (data-ink ratio, Tufte):** bỏ trang trí thừa (3D, bóng đổ, lưới đậm); mỗi nét vẽ phải mang thông tin.
* **Chọn đúng loại biểu đồ:**

  | Mục đích | Biểu đồ phù hợp |
  |---|---|
  | So sánh giữa các nhóm | Cột / thanh ngang (sắp xếp theo giá trị) |
  | Xu hướng theo thời gian (học kỳ) | Đường |
  | Phân phối | Histogram, boxplot |
  | Tỷ trọng ít thành phần | Thanh xếp chồng 100% (hạn chế biểu đồ tròn) |
  | Một con số quan trọng | Thẻ KPI (kèm so sánh kỳ trước) |
  | Giải thích một dự đoán | SHAP waterfall |

* **Màu có ý nghĩa:** dùng màu cảnh báo (đỏ / cam) **chỉ** cho mức rủi ro Cao / Trung bình; còn lại dùng màu trung tính. Không dùng quá nhiều màu.
* **Từ tổng quan đến chi tiết** (Shneiderman): *Overview first, zoom and filter, then details on demand*. KPI → phân bổ → lọc → danh sách → hồ sơ cá nhân.

### 2.3. Power BI và giới hạn kết nối
* Power BI kết nối **trực tiếp** PostgreSQL. Có 2 chế độ: *Import* (nạp dữ liệu vào file, nhanh) hoặc *DirectQuery* (truy vấn trực tiếp mỗi lần xem, luôn mới).
* Power BI **không đọc MongoDB trực tiếp** (cần connector ODBC trả phí). Vì vậy ETL tạo thêm bảng / view tổng hợp trong PostgreSQL. Đây là một ví dụ thực tế của Polyglot Persistence: **mỗi CSDL phục vụ người tiêu thụ phù hợp**.
* Power BI không vẽ SHAP sẵn, nên phần giải thích chi tiết đặt ở Streamlit.

### 2.4. Streamlit
* Thư viện Python biến script thành **ứng dụng web** mà không cần HTML/JS; tương tác bằng widget (ô nhập, bộ lọc).
* Dùng lại trực tiếp code Python của dự án (`load.py`, `explain.py`), nhờ đó hiển thị được quỹ đạo từ MongoDB và biểu đồ SHAP.

### 2.5. Dashboard có thể hành động (Actionable)
Mỗi màn hình nên trả lời được: **ai** cần hỗ trợ, **vì sao**, và **nên làm gì**. Vì vậy danh sách cảnh báo luôn đi kèm `top_reason_1..3` và gợi ý can thiệp tương ứng.

---

## 3. Input
PostgreSQL (`students`, `financial_profiles`, `predictions`, `student_clusters`); MongoDB (`academic_semesters`) cho quỹ đạo từng sinh viên; biểu đồ / hàm SHAP; `association_rules.csv`.

---

## 4. Biến đổi
1. **Chuẩn bị dữ liệu cho Power BI:** ETL tạo bảng `semester_summary` (theo học kỳ: số sinh viên, GPA trung bình, tỷ lệ bỏ học…) trong PostgreSQL, hoặc tạo view SQL.
2. **Dashboard Power BI** (4 trang):
   * *Tổng quan:* KPI số sinh viên đang học, số và tỷ lệ sinh viên rủi ro Cao / Trung bình.
   * *Phân bổ rủi ro:* theo học kỳ, `Housing_Status`, `Scholarship`, `First_Generation`, cụm sinh viên.
   * *Danh sách cảnh báo đỏ:* top sinh viên rủi ro cao kèm 3 lý do, có bộ lọc.
   * *Xu hướng:* GPA, chuyên cần, áp lực tài chính theo học kỳ.
3. **Ứng dụng Streamlit:**
   * Nhập `Student_ID` → hồ sơ tĩnh, quỹ đạo các kỳ (biểu đồ đường), `risk_score`, mức rủi ro.
   * SHAP waterfall + gợi ý can thiệp theo lý do (áp lực tài chính → học bổng / hỗ trợ tài chính; nợ môn → cố vấn học tập; chuyên cần giảm → liên hệ sinh viên).
   * Trang tổng hợp luật kết hợp và hồ sơ cụm.

---

## 5. Output
* `dashboards/ews_dashboard.pbix`.
* `app/streamlit_app.py` chạy tại `http://localhost:8501`.
* Ảnh chụp màn hình cho báo cáo.

## 6. Công cụ / File thực hiện
Power BI Desktop; `app/streamlit_app.py` (`streamlit`, `plotly`, `shap`).

## 7. Tiêu chí hoàn thành
- [ ] Từ dashboard tìm được một sinh viên rủi ro cao trong < 3 thao tác và xem được lý do.
- [ ] Dashboard cập nhật sau khi B14 chạy lại.

---

## 8. Câu hỏi bảo vệ thường gặp
**Hỏi:** Sao phải dùng cả Power BI lẫn Streamlit?  
**Đáp:** Hai nhóm người dùng khác nhau. Power BI mạnh về báo cáo tổng hợp cho quản lý, kết nối trực tiếp PostgreSQL. Streamlit cần cho phần tra cứu từng sinh viên và biểu đồ SHAP mà Power BI không hỗ trợ.

**Hỏi:** Power BI đọc dữ liệu MongoDB thế nào?  
**Đáp:** Không đọc trực tiếp. ETL tổng hợp dữ liệu học kỳ thành bảng `semester_summary` trong PostgreSQL cho Power BI; còn Streamlit đọc MongoDB bằng `pymongo`.
