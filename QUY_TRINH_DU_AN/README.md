# QUY TRÌNH DỰ ÁN: HỆ THỐNG CẢNH BÁO SỚM SINH VIÊN BỎ HỌC
**Môn học:** Tích hợp và Phân tích Dữ liệu Lớn – Phenikaa University  
**Đề tài:** Dự đoán nguy cơ bỏ học của sinh viên đại học dựa trên dữ liệu theo chiều dọc  
**Tài liệu liên quan:** [`PROJECT_OVERVIEW.md`](../PROJECT_OVERVIEW.md) · [`BAO_CAO_CSDL_GIUA_KY.md`](../BAO_CAO_CSDL_GIUA_KY.md) · [`THIET_KE_PIPELINE.md`](../THIET_KE_PIPELINE.md)

> Thư mục này mô tả **toàn bộ quy trình từ lúc bắt đầu đến khi kết thúc dự án**, chia thành **6 giai đoạn / 18 bước**. Mỗi giai đoạn là một thư mục con; mỗi bước là một file riêng gồm: **Nhiệm vụ → Cơ sở lý thuyết → Input → Biến đổi → Output → Công cụ → Tiêu chí hoàn thành → Câu hỏi bảo vệ**. Mọi con số được kiểm tra trực tiếp trên `academic_survival_longitudinal.csv`.

---

## 1. Cấu trúc thư mục

```text
QUY_TRINH_DU_AN/
├── README.md                                   # File này: tổng quan, lineage, nguyên tắc
│
├── GIAI_DOAN_A_CHUAN_BI/
│   ├── README.md
│   ├── B00_XAC_DINH_BAI_TOAN.md
│   └── B01_DUNG_MOI_TRUONG.md
│
├── GIAI_DOAN_B_KY_THUAT_DU_LIEU_ETL/
│   ├── README.md
│   ├── B02_THU_THAP_NAP_DU_LIEU_THO.md
│   ├── B03_KIEM_TRA_CHAT_LUONG_DU_LIEU.md
│   ├── B04_LAM_SACH_DU_LIEU.md
│   └── B05_NAP_KHO_POLYGLOT.md
│
├── GIAI_DOAN_C_PHAN_TICH_KHAI_PHA/
│   ├── README.md
│   ├── B06_PHAN_TICH_KHAM_PHA_EDA.md
│   ├── B07_TRICH_XUAT_DAC_TRUNG.md
│   └── B08_KHAI_PHA_DU_LIEU.md
│
├── GIAI_DOAN_D_HOC_MAY/
│   ├── README.md
│   ├── B09_CHIA_TAP_DU_LIEU.md
│   ├── B10_TIEN_XU_LY_MAT_CAN_BANG.md
│   ├── B11_HUAN_LUYEN_TINH_CHINH.md
│   ├── B12_DANH_GIA_CHON_NGUONG.md
│   └── B13_GIAI_THICH_MO_HINH_SHAP.md
│
├── GIAI_DOAN_E_TRIEN_KHAI_VAN_HANH/
│   ├── README.md
│   ├── B14_DU_DOAN_THEO_LO.md
│   ├── B15_TRUC_QUAN_HOA_DASHBOARD.md
│   └── B16_GIAM_SAT_VAN_HANH.md
│
└── GIAI_DOAN_F_KET_THUC/
    ├── README.md
    └── B17_BAO_CAO_BAO_VE.md
```

---

## 2. Sơ đồ quy trình

```text
GIAI ĐOẠN A – CHUẨN BỊ
  [B0] Xác định bài toán & tiêu chí thành công
  [B1] Dựng môi trường (Python + Docker: MinIO, PostgreSQL, MongoDB, MLflow)
        │
        ▼
GIAI ĐOẠN B – KỸ THUẬT DỮ LIỆU (ETL)
  [B2] Thu thập & nạp dữ liệu thô vào MinIO (Extract / Ingestion)
  [B3] Kiểm tra chất lượng dữ liệu (Data Profiling & Validation)
  [B4] Làm sạch dữ liệu (Transform – Cleaning)
  [B5] Nạp vào kho Polyglot: PostgreSQL + MongoDB (Load)
        │
        ▼
GIAI ĐOẠN C – PHÂN TÍCH & KHAI PHÁ
  [B6] Phân tích khám phá (EDA)
  [B7] Trích xuất đặc trưng theo chiều dọc (Feature Engineering)
  [B8] Khai phá dữ liệu: 8A Phân cụm · 8B Luật kết hợp
        │
        ▼
GIAI ĐOẠN D – HỌC MÁY
  [B9]  Tạo tập có nhãn & chia Train/Test theo Student_ID
  [B10] Tiền xử lý trong Pipeline & xử lý mất cân bằng lớp
  [B11] Huấn luyện, tinh chỉnh & theo dõi bằng MLflow
  [B12] Đánh giá trên tập Test, chọn ngưỡng & đăng ký mô hình
  [B13] Giải thích mô hình (SHAP)
        │
        ▼
GIAI ĐOẠN E – TRIỂN KHAI & VẬN HÀNH
  [B14] Dự đoán theo lô (Batch Inference) → bảng predictions
  [B15] Trực quan hóa: Power BI + Streamlit
  [B16] Lập lịch, giám sát, huấn luyện lại & sao lưu
        │
        ▼
GIAI ĐOẠN F – KẾT THÚC
  [B17] Báo cáo tổng kết & bảo vệ đề tài
```

---

## 3. Bảng tóm tắt một trang

| Bước | Nhiệm vụ chính | Input | Biến đổi cốt lõi | Output |
|:---:|---|---|---|---|
| [**B0**](./GIAI_DOAN_A_CHUAN_BI/B00_XAC_DINH_BAI_TOAN.md) | Xác định bài toán | Đề bài, dataset | Định nghĩa nhãn, đơn vị dự đoán, chỉ số đánh giá | Problem statement, tiêu chí thành công |
| [**B1**](./GIAI_DOAN_A_CHUAN_BI/B01_DUNG_MOI_TRUONG.md) | Dựng môi trường | Máy cá nhân | Cài Python libs, `docker compose up` | 5 dịch vụ chạy, cấu trúc thư mục |
| [**B2**](./GIAI_DOAN_B_KY_THUAT_DU_LIEU_ETL/B02_THU_THAP_NAP_DU_LIEU_THO.md) | Nạp dữ liệu thô | `academic_survival_longitudinal.csv` | Kiểm tra schema, checksum, upload | Object trong bucket `raw` + `ingestion_log` |
| [**B3**](./GIAI_DOAN_B_KY_THUAT_DU_LIEU_ETL/B03_KIEM_TRA_CHAT_LUONG_DU_LIEU.md) | Kiểm tra chất lượng | File thô (79.239 × 22) | Đo thiếu, ngoại lai, sai định dạng, trùng lặp | `data_quality_report.md` + quyết định xử lý |
| [**B4**](./GIAI_DOAN_B_KY_THUAT_DU_LIEU_ETL/B04_LAM_SACH_DU_LIEU.md) | Làm sạch | File thô + quyết định B3 | Khử trùng lặp, chuẩn hóa, clip, điền khuyết | `clean_semesters.parquet` (79.239 × 24) |
| [**B5**](./GIAI_DOAN_B_KY_THUAT_DU_LIEU_ETL/B05_NAP_KHO_POLYGLOT.md) | Nạp kho Polyglot | Dữ liệu sạch | Tách bảng tĩnh / document học kỳ, upsert | `students`, `financial_profiles` (20.000), `academic_semesters` (79.239) |
| [**B6**](./GIAI_DOAN_C_PHAN_TICH_KHAI_PHA/B06_PHAN_TICH_KHAM_PHA_EDA.md) | EDA | Bảng ghép từ 2 CSDL | Thống kê, biểu đồ, tương quan, quỹ đạo | Biểu đồ + danh sách insight |
| [**B7**](./GIAI_DOAN_C_PHAN_TICH_KHAI_PHA/B07_TRICH_XUAT_DAC_TRUNG.md) | Feature Engineering | Dữ liệu sạch đã sắp xếp | Lag, Delta, Cumulative, Rolling, chỉ số tài chính | `feature_table.parquet` (79.239 × 47; 43 đặc trưng) |
| [**B8**](./GIAI_DOAN_C_PHAN_TICH_KHAI_PHA/B08_KHAI_PHA_DU_LIEU.md) | Data Mining | Bảng đặc trưng | K-Means; rời rạc hóa + Apriori | Nhãn cụm, bảng luật kết hợp |
| [**B9**](./GIAI_DOAN_D_HOC_MAY/B09_CHIA_TAP_DU_LIEU.md) | Chia tập | Bảng đặc trưng | Bỏ cột rò rỉ, tách Censored, chia theo nhóm | Train / Test / Scoring set |
| [**B10**](./GIAI_DOAN_D_HOC_MAY/B10_TIEN_XU_LY_MAT_CAN_BANG.md) | Tiền xử lý mô hình | Train set | Imputer, Scaler, One-Hot, trọng số lớp | `sklearn Pipeline` (chưa fit) |
| [**B11**](./GIAI_DOAN_D_HOC_MAY/B11_HUAN_LUYEN_TINH_CHINH.md) | Huấn luyện | Train set + Pipeline | CV 5-fold theo nhóm, tuning, log MLflow | Bảng so sánh mô hình, mô hình tốt nhất |
| [**B12**](./GIAI_DOAN_D_HOC_MAY/B12_DANH_GIA_CHON_NGUONG.md) | Đánh giá & chọn ngưỡng | Mô hình tốt nhất + Test set | Hiệu chỉnh xác suất, chọn ngưỡng, đo trên Test | Báo cáo đánh giá, model `Production` |
| [**B13**](./GIAI_DOAN_D_HOC_MAY/B13_GIAI_THICH_MO_HINH_SHAP.md) | Giải thích | Model + Test set | SHAP global & local | Biểu đồ SHAP, hàm "top 3 lý do" |
| [**B14**](./GIAI_DOAN_E_TRIEN_KHAI_VAN_HANH/B14_DU_DOAN_THEO_LO.md) | Batch Inference | Model Production + Scoring set | Dự đoán xác suất, gán mức rủi ro | Bảng `predictions` (11.115 dòng/lần chạy) |
| [**B15**](./GIAI_DOAN_E_TRIEN_KHAI_VAN_HANH/B15_TRUC_QUAN_HOA_DASHBOARD.md) | Dashboard | `predictions` + dữ liệu kho | Thiết kế báo cáo, app tra cứu | Power BI `.pbix`, Streamlit app |
| [**B16**](./GIAI_DOAN_E_TRIEN_KHAI_VAN_HANH/B16_GIAM_SAT_VAN_HANH.md) | Vận hành | Toàn bộ pipeline | Lập lịch, đo 5 metrics, retrain, backup | Log vận hành, bản sao lưu |
| [**B17**](./GIAI_DOAN_F_KET_THUC/B17_BAO_CAO_BAO_VE.md) | Kết thúc | Toàn bộ output | Viết báo cáo, slide, demo | Báo cáo cuối kỳ, slide, video demo |

---

## 4. Thông số dữ liệu dùng xuyên suốt

| Thông số | Giá trị |
|---|---|
| Tổng số dòng (cặp `Student_ID – Semester`) | **79.239** |
| Số sinh viên | **20.000** (mỗi sinh viên 1 – 8 kỳ liên tục, trung bình 3,96 kỳ) |
| Số cột gốc | 22 |
| Dòng có nhãn bỏ học = 1 | 6.917 (8,7% toàn bộ) |
| Kết cục của sinh viên | 6.917 bỏ học · 1.968 tốt nghiệp · 11.115 bị cắt dữ liệu (`Censored = 1`) |
| Tập có nhãn (`Censored = 0`) | **68.124 dòng**, 17.928 sinh viên, lớp bỏ học **10,2%** |
| Tập cần chấm điểm (`Censored = 1`) | **11.115 dòng** = kỳ mới nhất của sinh viên đang theo học |

---

## 5. Dòng chảy dữ liệu (Data Lineage)

| Dữ liệu / Artifact | Tạo ở bước | Nơi lưu | Kích thước | Dùng ở bước |
|---|:---:|---|---|:---:|
| `academic_survival_longitudinal.csv` (gốc) | – | Repo / nguồn | 79.239 × 22 | B2 |
| CSV thô theo lô | B2 | MinIO `raw/` | 79.239 × 22 | B3, B4 |
| `ingestion_log` | B2 | PostgreSQL | 1 dòng / lần nạp | B11, B16 |
| `data_quality_report.md` | B3 | `reports/` | – | B4, B17 |
| `clean_semesters.parquet` | B4 | `data/processed/`, MinIO `processed/` | 79.239 × 24 | B5, B7 |
| `students`, `financial_profiles` | B5 | PostgreSQL | 20.000 dòng mỗi bảng | B6, B15 |
| `academic_semesters` | B5 | MongoDB | 79.239 document | B6, B15 |
| `feature_table.parquet` + `feature_spec.json` | B7 | `data/features/`, `config/` | 79.239 × 47 (43 đặc trưng) | B8, B9, B14 |
| `student_clusters` | B8A | PostgreSQL | 20.000 | B15 |
| `association_rules.csv` | B8B | `reports/` | top 10 – 20 luật | B15, B17 |
| Train / Test / Scoring | B9 | `data/splits/test_student_ids.csv` + `load_splits()` | 54.474 / 13.650 / 11.115 dòng | B10 – B14 |
| MLflow runs, `dropout_model` | B11 – B12 | MLflow (PostgreSQL + MinIO) | – | B14, B16 |
| `predictions` | B14 | PostgreSQL | 11.115 / lần chạy | B15, B16 |
| `pipeline_runs` | B16 | PostgreSQL | 1 dòng / lần chạy | B16 |

---

## 6. Cấu trúc mã nguồn dự kiến của toàn dự án

```text
Tich_Hop_pTich_DlieuLon/
├── academic_survival_longitudinal.csv     # Dữ liệu gốc
├── README.md · PROJECT_OVERVIEW.md · BAO_CAO_CSDL_GIUA_KY.md · THIET_KE_PIPELINE.md
├── QUY_TRINH_DU_AN/                       # Lý thuyết + quy trình 6 giai đoạn (thư mục này)
│
├── docker-compose.yml                     # B1
├── requirements.txt                       # B1
├── .env.example                           # B1
├── config/
│   ├── settings.yaml                      # B1: đường dẫn, random_state, ngưỡng rủi ro
│   └── feature_spec.json                  # B7
├── sql/01_ingestion_log.sql               # B2
├── sql/02_core_tables.sql                 # B5
├── sql/03_student_clusters.sql            # B8
│
├── src/
│   ├── core/          config.py, db.py, schema.py    # dùng chung
│   ├── etl/           ingest.py (B2), validate.py (B3), clean.py (B4), load.py (B5)
│   ├── analysis/      features.py (B7), mining.py (B8)
│   ├── ml/            split.py (B9), train.py (B10 – B12), explain.py (B13), predict.py (B14)
│   └── ops/           check_env.py (B1), monitor.py, run_pipeline.py (B16)
├── tests/                                 # pytest
│
├── notebooks/
│   ├── 01_data_cleaning_eda.ipynb         # B3, B6
│   ├── 02_feature_engineering.ipynb       # B7
│   ├── 03_data_mining_patterns.ipynb      # B8
│   └── 04_machine_learning_models.ipynb   # B9 – B13
│
├── app/streamlit_app.py                   # B15
├── dashboards/ews_dashboard.pbix          # B15
├── data/                                  # (không commit) raw/ processed/ features/ splits/
└── reports/                               # figures/, data_quality_report.md, model_comparison.csv,
                                           # evaluation_report.md, association_rules.csv, final_report
```

---

## 7. Thứ tự triển khai gợi ý

| Mốc | Nội dung | Bước | Kết quả kiểm chứng |
|:---:|---|:---:|---|
| **M1** | Môi trường & dữ liệu vào kho | B0 – B5 | 3 bảng/collection đủ số lượng, chạy lại không nhân đôi |
| **M2** | Hiểu dữ liệu & đặc trưng | B6 – B7 | Notebook EDA + `feature_table.parquet` qua unit test |
| **M3** | Khai phá tri thức | B8 | Hồ sơ cụm + top luật kết hợp có diễn giải |
| **M4** | Mô hình dự báo | B9 – B13 | Model Production trong MLflow + báo cáo đánh giá + SHAP |
| **M5** | Triển khai | B14 – B16 | Bảng `predictions`, dashboard, pipeline chạy theo lịch |
| **M6** | Kết thúc | B17 | Báo cáo, slide, demo |

---

## 8. Nguyên tắc xuyên suốt

1. **Không bao giờ sửa dữ liệu thô**; mọi thay đổi đều tái lập được bằng code.
2. **Mọi thao tác "học từ dữ liệu"** (trung vị, mean/std, SMOTE, K-Means dùng làm đặc trưng) **chỉ fit trên tập Train**.
3. **Chia tập theo `Student_ID`**; một sinh viên chỉ nằm ở Train hoặc Test.
4. **Đặc trưng tại kỳ *t* chỉ dùng dữ liệu đến hết kỳ *t***.
5. **Mỗi bước có tiêu chí hoàn thành kiểm chứng được** trước khi sang bước sau.
