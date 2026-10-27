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
* **PostgreSQL cho Power BI** (`python -m src.etl.publish`):
  * Bảng `semester_summary`: mỗi học kỳ một dòng, gồm số SV, tỷ lệ bỏ học, GPA, chuyên cần, áp lực tài chính, làm thêm, số môn trượt. Bảng này tổng hợp dữ liệu theo kỳ ở MongoDB mà Power BI không đọc được.
  * View `v_canh_bao`: lần chấm điểm mới nhất ghép với hồ sơ và cụm.
  * View `v_rui_ro_theo_nhom`: tỷ lệ mức Cao / Trung bình theo 5 chiều.
* **Power BI:** [`dashboards/HUONG_DAN_POWER_BI.md`](../../dashboards/HUONG_DAN_POWER_BI.md) gồm kết nối, measure DAX, quy ước màu, cách dựng 4 trang và bảng số liệu để đối chiếu. File `dashboards/ews_dashboard.pbix` do nhóm dựng bằng Power BI Desktop, vì máy làm dự án chưa cài.
* **Streamlit** `app/streamlit_app.py` (http://localhost:8501), 4 trang đi từ tổng quan tới chi tiết:

  | Trang | Trả lời câu hỏi | Nội dung |
  |---|---|---|
  | Cần liên hệ (mặc định) | Tuần này liên hệ ai? | Thanh tỷ trọng 3 mức; 7 bộ lọc (mức, kỳ, lý do chính, cụm, học bổng, thế hệ đầu, nơi ở); bảng xếp theo nguy cơ kèm 3 lý do; chọn dòng → mở hồ sơ; tải CSV |
  | Hồ sơ sinh viên | Vì sao, và nên làm gì? | Câu kết luận ("Nguy cơ bỏ học kỳ tới 92%, mức cao", so với mức chung 10,2%); 3 dòng **Vì sao → Nên làm**; waterfall SHAP theo nhóm (trục ghi bằng xác suất); hồ sơ tĩnh; quỹ đạo 4 chỉ số qua các kỳ so với trung bình cùng kỳ |
  | Toàn trường | Nhóm nào rủi ro nhất? | Tỷ lệ mức Cao / Trung bình theo 5 chiều (cùng view với Power BI); xu hướng theo học kỳ |
  | Nhóm và quy luật | Đặc điểm nào hay đi cùng bỏ học? | 4 cụm (B8A) và 15 luật kết hợp (B8B) viết thành câu tiếng Việt |
* Ảnh chụp cho báo cáo: `reports/figures/app_*.png`, gồm 4 trang và bản hồ sơ trên điện thoại.

**Thiết kế** (theo mục 2.2):
* **Màu cảnh báo chỉ dành cho mức rủi ro:** Cao `#B83227`, Trung bình `#C7821A`. Mức Thấp và mọi thứ khác dùng màu mực `#1E2B2F` hoặc chì `#66767B` trên nền "giấy kẻ" `#F3F5F4`.
* **Font:** Be Vietnam Pro (font được thiết kế cho tiếng Việt), số dạng tabular cho các cột thẳng hàng.
* **Điểm nhấn duy nhất** là câu kết luận chữ lớn ở trang hồ sơ, thay cho thẻ KPI hay đồng hồ đo. Còn lại phân tách bằng đường kẻ, không dùng thẻ hay bóng đổ.
* Viết theo ngôn ngữ của cố vấn:
  * "Nguy cơ", "Vì sao", "Nên làm".
  * Số thập phân dùng dấu phẩy.
  * Giới tính / nơi ở hiển thị tiếng Việt.
  * Mã item của luật kết hợp dịch thành câu.
* **Gợi ý can thiệp** (`app/data.py` → `ACTIONS`):
  * Áp lực tài chính → học bổng / quỹ hỗ trợ / giãn học phí.
  * Trượt môn → học lại / phụ đạo / giảm tín chỉ.
  * Chuyên cần → liên hệ trực tiếp.
* Waterfall tính lại bằng **đúng phiên bản mô hình** đã chấm (`predictions.model_version`), nên khớp `risk_score` (92% ≈ 91,8% trên biểu đồ).
* Đã kiểm tra trên màn hình rộng 1400px và điện thoại 420px. Trên điện thoại, "Vì sao → Nên làm" xếp thành một cột và quỹ đạo dạng lưới 2×2.

## 6. Công cụ / File thực hiện
* `src/etl/publish.py`: `python -m src.etl.publish`. Gồm `semester_summary()` (hàm thuần, Streamlit dùng chung qua bảng) và `VIEWS`; có 3 kiểm tra sau khi ghi.
* `app/streamlit_app.py` (4 trang, `st.navigation`), `app/data.py` (đọc PostgreSQL / MongoDB / mô hình, có cache), `app/style.py` (màu, font, mẫu Plotly), `.streamlit/config.toml` (theme).
* Chạy: `streamlit run app/streamlit_app.py`.
  * Lần mở trang hồ sơ đầu tiên mất ~15 giây để nạp mô hình từ MLflow và tính SHAP cho 11.115 sinh viên; các lần sau dùng cache.
  * Dữ liệu `predictions` được cache 5 phút.
* `dashboards/HUONG_DAN_POWER_BI.md`.
* `tests/test_publish.py` (3 test) và `tests/test_app.py` (`AppTest` chạy trang mặc định; tự bỏ qua nếu không có PostgreSQL). Tổng 122/122 đạt.
* **Giới hạn đã biết:** nếu request **đầu tiên sau khi khởi động server** là đường dẫn trang con (ví dụ `/ho-so`), Streamlit 1.41 hiện hộp thoại "Page not found" (lúc đó danh sách trang chưa được đăng ký); trang vẫn chạy đúng sau khi đóng. Mở từ địa chỉ gốc thì không gặp.

## 7. Tiêu chí hoàn thành (đã kiểm tra 2026-10-26)
- [x] Từ dashboard tìm được một sinh viên rủi ro cao trong < 3 thao tác và xem được lý do: trang "Cần liên hệ" mặc định lọc mức Cao, xếp theo nguy cơ, lý do hiện ngay trong bảng (0 thao tác); chọn dòng → "Mở hồ sơ" (2 thao tác) để xem waterfall và việc nên làm.
- [x] Dashboard cập nhật sau khi B14 chạy lại: app và view đều đọc `run_id` mới nhất. Power BI cần bấm Refresh sau `predict` + `publish`.
- [ ] `dashboards/ews_dashboard.pbix`: nhóm dựng theo hướng dẫn (cần Power BI Desktop).

---

## 8. Câu hỏi bảo vệ thường gặp
**Hỏi:** Sao phải dùng cả Power BI lẫn Streamlit?  
**Đáp:** Hai nhóm người dùng khác nhau. Power BI mạnh về báo cáo tổng hợp cho quản lý, kết nối trực tiếp PostgreSQL. Streamlit cần cho phần tra cứu từng sinh viên và biểu đồ SHAP mà Power BI không hỗ trợ.

**Hỏi:** Power BI đọc dữ liệu MongoDB thế nào?  
**Đáp:** Không đọc trực tiếp. ETL tổng hợp dữ liệu học kỳ thành bảng `semester_summary` trong PostgreSQL cho Power BI; còn Streamlit đọc MongoDB bằng `pymongo`.
