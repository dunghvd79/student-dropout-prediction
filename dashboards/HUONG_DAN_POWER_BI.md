# Hướng dẫn dựng dashboard Power BI (B15)

Dashboard Power BI dành cho **lãnh đạo và Phòng Đào tạo**: xem tình hình chung, nhóm nào rủi ro nhất, và danh sách cảnh báo đỏ. Phần tra cứu từng sinh viên kèm giải thích nằm ở ứng dụng Streamlit (`streamlit run app/streamlit_app.py`).

Toàn bộ dữ liệu đã được chuẩn bị sẵn trong PostgreSQL. Trong Power BI chỉ cần kết nối, kéo thả, không phải viết SQL.

---

## 1. Chuẩn bị (một lần)

1. Cài **Power BI Desktop** (miễn phí, Microsoft Store hoặc https://powerbi.microsoft.com/desktop).
2. Bật kho dữ liệu và làm mới dữ liệu cho dashboard:
   ```powershell
   docker compose up -d
   .venv\Scripts\activate
   python -m src.ml.predict      # B14: chấm điểm lần mới (nếu cần)
   python -m src.etl.publish     # B15: tạo / làm mới bảng và view bên dưới
   ```
   `publish` in ra 3 dòng `[OK]` là sẵn sàng.

## 2. Dữ liệu dùng trong Power BI

| Bảng / view | Một dòng là | Dùng cho trang |
|---|---|---|
| `v_canh_bao` | một sinh viên đang học, ở **lần chấm điểm mới nhất** (điểm rủi ro, mức, 3 lý do, hồ sơ, cụm) | Tổng quan, Danh sách cảnh báo |
| `v_rui_ro_theo_nhom` | một nhóm sinh viên theo 5 chiều: Học kỳ, Học bổng, Thế hệ đầu, Nơi ở, Cụm | Phân bổ rủi ro |
| `semester_summary` | một học kỳ (toàn bộ dữ liệu lịch sử): số SV, tỷ lệ bỏ học, GPA, chuyên cần, áp lực tài chính | Xu hướng |

Cột chính của `v_canh_bao`: `student_id`, `semester`, `risk_score` (0 – 1), `risk_level` (Cao / Trung bình / Thấp), `thu_tu_muc` (1, 2, 3; dùng để sắp xếp mức), `top_reason_1..3`, `nhom_ly_do_1` (tên nhóm của lý do số 1), `gender`, `housing_status`, `scholarship`, `first_generation`, `cluster_name`, `model_version`, `run_date`.

## 3. Kết nối

1. **Home → Get data → PostgreSQL database**.
2. Server: `localhost:5433`. Database: `dropout_ews`. Data Connectivity mode: **Import**.
   * Import nhanh và đủ cho dữ liệu chấm điểm hằng tuần. Sau mỗi lần chạy `predict` + `publish`, bấm **Refresh**.
3. Đăng nhập kiểu **Database**: User và Password lấy trong file `.env` (`POSTGRES_USER`, `POSTGRES_PASSWORD`). Không ghi mật khẩu vào báo cáo hay ảnh chụp.
4. Chọn 3 đối tượng: `v_canh_bao`, `v_rui_ro_theo_nhom`, `semester_summary` → **Load**.
5. Trong **Model view**: 3 bảng độc lập, **không cần** tạo quan hệ.
6. Trong **Data view**, bảng `v_canh_bao`, chọn cột `risk_level` → **Sort by column** → `thu_tu_muc`. Mức sẽ luôn xếp Cao → Trung bình → Thấp.

## 4. Measure (DAX), tạo trong bảng `v_canh_bao`

```DAX
So SV dang hoc = COUNTROWS ( v_canh_bao )
So SV muc Cao = CALCULATE ( [So SV dang hoc], v_canh_bao[risk_level] = "Cao" )
So SV muc Trung binh = CALCULATE ( [So SV dang hoc], v_canh_bao[risk_level] = "Trung bình" )
Ty le muc Cao = DIVIDE ( [So SV muc Cao], [So SV dang hoc] )
Ty le can theo doi = DIVIDE ( [So SV muc Cao] + [So SV muc Trung binh], [So SV dang hoc] )
Nguy co TB = AVERAGE ( v_canh_bao[risk_score] )
Ngay cham diem = FORMAT ( MAX ( v_canh_bao[run_date] ), "dd/mm/yyyy" )
```

Định dạng `Ty le …` và `Nguy co TB` là **Percentage**, 1 chữ số thập phân.

## 5. Quy ước trình bày (giống ứng dụng Streamlit)

* **Màu cảnh báo chỉ dùng cho mức rủi ro:** Cao `#B83227`, Trung bình `#C7821A`, Thấp `#66767B` (xám). Mọi biểu đồ khác dùng màu mực `#1E2B2F` hoặc xám, không dùng bảng màu mặc định nhiều màu.
* Nền trang `#F3F5F4`; font **Segoe UI** (mặc định của Power BI, có đủ dấu tiếng Việt).
* Không dùng biểu đồ tròn, 3D hay bóng đổ. Sắp xếp thanh theo giá trị.
* Mỗi trang có một tiêu đề nói rõ trang trả lời câu hỏi gì, và dòng phụ "Chấm điểm ngày … (mô hình v…)".

Cách gán màu theo mức: chọn biểu đồ → **Format → Columns / Bars → Colors** → bật "Show all" và gán từng giá trị `risk_level`; với thẻ (Card), dùng **Conditional formatting → Font color**.

## 6. Bốn trang

### Trang 1 – Tổng quan: "Tuần này cần theo dõi bao nhiêu sinh viên?"
| Visual | Trường | Ghi chú |
|---|---|---|
| Card | `So SV dang hoc` | |
| Card | `So SV muc Cao`, kèm `Ty le muc Cao` | Màu chữ đỏ `#B83227` |
| Card | `So SV muc Trung binh` | Màu chữ cam `#C7821A` |
| 100% stacked bar | Axis: (trống), Legend: `risk_level`, Values: `So SV dang hoc` | Một thanh duy nhất cho tỷ trọng 3 mức |
| Clustered bar | Axis: `nhom_ly_do_1`, Values: `So SV muc Cao` | "Lý do số 1 của nhóm Cao", sắp giảm dần |
| Text box | `Ngay cham diem`, `model_version` | |

### Trang 2 – Phân bổ rủi ro: "Nhóm nào rủi ro nhất?"
* **Slicer** (dạng dropdown hoặc tile): `v_rui_ro_theo_nhom[chieu]`, chọn một giá trị (Single select), mặc định "Học kỳ".
* **Stacked bar**: Axis `nhom`; Values `ty_le_cao` (đỏ) và `ty_le_trung_binh` (cam); tooltip `so_sinh_vien`. Định dạng phần trăm.
* Ghi chú dưới biểu đồ: tỷ lệ là phần sinh viên đang học thuộc mức đó trong từng nhóm.

### Trang 3 – Danh sách cảnh báo đỏ: "Cần liên hệ ai, vì sao?"
* **Slicer**: `risk_level` (mặc định Cao), `semester`, `cluster_name`, `scholarship`, `first_generation`, `housing_status`, `nhom_ly_do_1`.
* **Table**: `student_id`, `semester`, `risk_score` (định dạng 0,00; Conditional formatting → **Data bars** màu `#1E2B2F`), `risk_level`, `top_reason_1`, `top_reason_2`, `top_reason_3`. Sắp xếp `risk_score` giảm dần.
* Bật **Word wrap** cho cột lý do. Cán bộ tra chi tiết và biểu đồ giải thích của từng sinh viên ở Streamlit (trang "Hồ sơ sinh viên").

### Trang 4 – Xu hướng: "Sinh viên thay đổi thế nào qua các kỳ?" (bảng `semester_summary`)
* 4 **Line chart** nhỏ cạnh nhau, Axis `semester` (kiểu Categorical):
  1. `ty_le_bo_hoc` (phần trăm).
  2. `gpa_tb`.
  3. `chuyen_can_tb`.
  4. `ap_luc_tc_tb`.
* Ghi chú: tỷ lệ bỏ học tính trên các kỳ đã biết kết cục; kỳ 8 thấp vì phần lớn sinh viên tốt nghiệp.

## 7. Lưu và kiểm tra

1. Lưu thành `dashboards/ews_dashboard.pbix`. File này có thể lưu kèm dữ liệu đã Import; không chứa mật khẩu, nhưng nên kiểm tra trước khi commit.
2. Đối chiếu với Streamlit (cùng nguồn dữ liệu nên phải khớp):

| Chỉ số (run `20261026-v2`) | Giá trị đúng |
|---|---|
| Số sinh viên đang học | 11.115 |
| Mức Cao / Trung bình / Thấp | 439 / 3.978 / 6.698 |
| Tỷ lệ mức Cao ở kỳ 1 | 1,5% |
| Tỷ lệ bỏ học kỳ sau ở kỳ 1 / kỳ 7 (`semester_summary`) | 7,4% / 14,7% |

3. Chụp 4 trang (**File → Export → PDF** hoặc ảnh) cho báo cáo cuối kỳ (B17).
