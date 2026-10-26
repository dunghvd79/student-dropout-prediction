# GIAI ĐOẠN B – KỸ THUẬT DỮ LIỆU (ETL)
[← Giai đoạn A](../GIAI_DOAN_A_CHUAN_BI/README.md) · [Về tổng quan](../README.md) · [Giai đoạn C →](../GIAI_DOAN_C_PHAN_TICH_KHAI_PHA/README.md)

## Mục tiêu giai đoạn
Đưa dữ liệu từ nguồn vào hệ thống lưu trữ theo đúng mô hình **ETL (Extract → Transform → Load)**: giữ nguyên bản gốc, đo và sửa lỗi chất lượng, rồi nạp dữ liệu sạch vào kiến trúc **Polyglot Persistence** (PostgreSQL + MongoDB) đã thiết kế ở bài giữa kỳ.

```text
CSV nguồn ──[B2 Extract]──► MinIO raw/ ──[B3 Validate]──► Báo cáo chất lượng
                                  │                              │ (quyết định xử lý)
                                  └────────[B4 Transform]◄───────┘
                                                 │
                                                 ▼
                                  clean_semesters.parquet ──[B5 Load]──► PostgreSQL + MongoDB
```

## Các bước

| Bước | Tên | Lý thuyết chính | Output |
|:---:|---|---|---|
| [**B2**](./B02_THU_THAP_NAP_DU_LIEU_THO.md) | Thu thập & nạp dữ liệu thô | Batch / Streaming, Data Lake / Data Warehouse, Object Storage, kiến trúc Medallion, checksum & idempotency | CSV thô trong MinIO + `ingestion_log` |
| [**B3**](./B03_KIEM_TRA_CHAT_LUONG_DU_LIEU.md) | Kiểm tra chất lượng dữ liệu | 6 chiều chất lượng dữ liệu, MCAR/MAR/MNAR, phát hiện ngoại lai (IQR, z-score), rò rỉ nhãn, right-censoring | `data_quality_report.md` |
| [**B4**](./B04_LAM_SACH_DU_LIEU.md) | Làm sạch dữ liệu | Chiến lược điền khuyết, LOCF, missing indicator, clipping & winsorization, chuẩn hóa phân loại, định dạng Parquet | `clean_semesters.parquet` (79.239 × 24) |
| [**B5**](./B05_NAP_KHO_POLYGLOT.md) | Nạp kho Polyglot | Mô hình quan hệ, chuẩn hóa 1NF–3NF, ACID, mô hình tài liệu (embed / reference), index, upsert | `students`, `financial_profiles`, `academic_semesters` |

## Input → Output của cả giai đoạn
* **Input:** `academic_survival_longitudinal.csv` (79.239 × 22).
* **Output:** PostgreSQL `students` (20.000) + `financial_profiles` (20.000) + `ingestion_log`; MongoDB `academic_semesters` (79.239); file `clean_semesters.parquet`; báo cáo chất lượng dữ liệu.

## Vì sao chọn ETL mà không phải ELT?
* **ETL:** biến đổi **trước** khi nạp. Phù hợp khi dữ liệu vừa phải (~7,4 MB) và muốn kho chỉ chứa dữ liệu sạch.
* **ELT:** nạp thô vào kho rồi biến đổi **bên trong** kho (BigQuery, Snowflake). Chỉ có lợi khi kho có sức tính toán lớn và dữ liệu rất lớn.
* Dự án vẫn giữ một bản thô trong MinIO, nên vẫn có lợi ích "chạy lại từ đầu" của ELT.

## Điều kiện để sang Giai đoạn C
- [x] Số lượng khớp: 20.000 / 20.000 / 79.239; chạy lại pipeline không nhân đôi dữ liệu.
- [x] Mọi vấn đề trong báo cáo chất lượng đều đã được xử lý hoặc có quyết định rõ ràng.
