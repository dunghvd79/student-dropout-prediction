# BƯỚC 2. THU THẬP & NẠP DỮ LIỆU THÔ (EXTRACT / INGESTION)
**Giai đoạn B – Kỹ thuật dữ liệu (ETL)** · [← Giai đoạn B](./README.md) · [Bước 3 →](./B03_KIEM_TRA_CHAT_LUONG_DU_LIEU.md)

---

## 1. Nhiệm vụ
Đưa dữ liệu gốc vào Raw Data Lake **nguyên trạng, không sửa**, có lưu vết, để có thể chạy lại toàn bộ pipeline bất cứ lúc nào.

---

## 2. Cơ sở lý thuyết

### 2.1. Data Ingestion là gì?
Ingestion là quá trình **di chuyển dữ liệu từ hệ thống nguồn vào hệ thống lưu trữ / phân tích**. Có hai kiểu chính:

| | **Batch (theo lô)** | **Streaming (luồng)** |
|---|---|---|
| Cách chạy | Gom dữ liệu rồi xử lý theo chu kỳ (giờ / ngày / tuần) | Xử lý từng sự kiện ngay khi phát sinh |
| Độ trễ | Phút → ngày | Mili giây → giây |
| Công cụ | cron, Airflow, Pandas, Spark | Kafka, Flink, Spark Streaming |
| Phù hợp | Báo cáo định kỳ, huấn luyện mô hình | Phát hiện gian lận, IoT, giám sát thời gian thực |

**Dự án chọn Batch** vì quyết định can thiệp học vụ diễn ra theo tuần / học kỳ, không cần phản hồi tức thời. Batch cũng rẻ và đơn giản hơn.

### 2.2. Data Lake và Data Warehouse

| | **Data Lake** | **Data Warehouse** |
|---|---|---|
| Lưu gì | Mọi dạng dữ liệu (CSV, JSON, ảnh, log), **thô** | Dữ liệu **đã làm sạch, có cấu trúc** |
| Schema | *Schema-on-read* (áp schema khi đọc) | *Schema-on-write* (áp schema khi ghi) |
| Mục đích | Lưu trữ rẻ, giữ nguyên bản gốc, khám phá | Truy vấn phân tích, báo cáo BI |

Dự án dùng **MinIO làm Data Lake** (tầng thô) và **PostgreSQL + MongoDB làm tầng phục vụ** (dữ liệu sạch).

### 2.3. Object Storage (MinIO / Amazon S3)
* Lưu dữ liệu dưới dạng **object** = nội dung file + metadata + **key** (đường dẫn), nằm trong các **bucket**.
* Không có thư mục thật; "thư mục" chỉ là tiền tố của key (ví dụ `raw/academic/ingest_date=2026-10-11/...`).
* Ưu điểm: rẻ, gần như không giới hạn dung lượng, bền vững, truy cập qua HTTP (S3 API). MinIO chạy local nhưng **tương thích S3**, nên code chuyển lên AWS mà không phải sửa.

### 2.4. Kiến trúc Medallion (Bronze → Silver → Gold)
Mô hình phân tầng dữ liệu phổ biến trong Data Lake:

| Tầng | Ý nghĩa | Trong dự án |
|---|---|---|
| **Bronze (raw)** | Dữ liệu gốc, bất biến | MinIO `raw/` (B2) |
| **Silver (processed)** | Đã làm sạch, chuẩn hóa | `clean_semesters.parquet`, PostgreSQL, MongoDB (B4, B5) |
| **Gold (curated)** | Đã tổng hợp / đặc trưng, sẵn sàng cho phân tích & ML | `feature_table.parquet`, `predictions` (B7, B14) |

**Nguyên tắc bất biến (immutability):** không bao giờ sửa tầng Bronze. Nếu logic làm sạch sai, chỉ cần sửa code và chạy lại từ Bronze.

### 2.5. Partitioning, Checksum và Idempotency
* **Partition theo ngày nạp** (`ingest_date=YYYY-MM-DD`): mỗi lô là một "ngăn" riêng, dễ truy vết và dễ chạy lại một lô cụ thể.
* **Checksum (MD5 / SHA-256):** "dấu vân tay" của file. Hai file có cùng checksum thì nội dung giống hệt nhau, nhờ đó phát hiện được việc nạp trùng và kiểm tra file không bị hỏng khi truyền.
* **Idempotency (tính lũy đẳng):** chạy một thao tác nhiều lần cho cùng kết quả như chạy một lần. Đây là yêu cầu bắt buộc với pipeline chạy định kỳ.

### 2.6. Liên hệ 6V của Big Data (Lecture)
* **Volume:** 79.239 dòng, ~7,4 MB. Nhỏ so với Big Data, nên không cần Spark (xem [`THIET_KE_PIPELINE.md`](../../THIET_KE_PIPELINE.md) mục 6).
* **Variety:** 3 nguồn (SIS, LMS, Khảo sát), có cả dữ liệu cấu trúc và bán cấu trúc.
* **Velocity:** cập nhật theo đợt (batch).
* **Veracity:** có dữ liệu bẩn (B3), là lý do cần bước kiểm tra chất lượng.
* **Value:** cảnh báo sớm sinh viên bỏ học.

---

## 3. Input
`academic_survival_longitudinal.csv` (79.239 dòng × 22 cột, ~7,4 MB). Trong hệ thống thực, file này được ghép từ:
* **SIS:** `Sem_GPA`, `Course_Load`, `Failed_Courses`, `Tuition_Base`, `Scholarship`.
* **LMS:** `LMS_Logins`, `Attendance`.
* **Khảo sát / Phòng CTSV:** `Family_Income`, `Financial_Stress`, `Work_Hours`, `Emergency_Expense`, `Advising_Visits`.

---

## 4. Biến đổi
1. **Tính checksum MD5** của file. Nếu trùng MD5 với một lô đã `SUCCESS` thì bỏ qua và ghi `SKIPPED` (idempotent).
2. **Kiểm tra schema đầu vào** theo `src/core/schema.py`: đủ 22 cột đúng tên, đúng thứ tự; các cột số đọc được thành số (ô trống được phép, xử lý ở B3/B4). Sai schema → ghi `FAILED`, không upload.
3. **Đặt key theo lô:** bucket `raw`, key `academic/ingest_date=YYYY-MM-DD/batch_id=<batch_id>/academic_survival_longitudinal.csv`. Mỗi lần nạp có `batch_id` riêng (`<thời điểm UTC>_<6 ký tự ngẫu nhiên>`), nên không bao giờ ghi đè lô cũ.
4. **Upload lên MinIO** kèm metadata (`md5`, `row-count`, `batch-id`), sau đó **tải ngược và so MD5** để chắc file không hỏng khi truyền.
5. **Ghi nhật ký** vào bảng `ingestion_log` (PostgreSQL, tạo bởi `sql/01_ingestion_log.sql`): `batch_id`, `source_file`, `bucket`, `object_key`, `row_count`, `column_count`, `file_size_bytes`, `md5`, `status` (`SUCCESS` / `FAILED` / `SKIPPED`), `message`, `ingested_at`.

---

## 5. Output
* Object CSV gốc trong MinIO bucket `raw`.
* 1 dòng mới trong `ingestion_log` (ví dụ `row_count = 79239`, `status = SUCCESS`).

## 6. Công cụ / File thực hiện
* `src/etl/ingest.py`: chạy `python -m src.etl.ingest [--file PATH] [--date YYYY-MM-DD]`.
* `src/core/schema.py` (hợp đồng 22 cột), `src/core/db.py` (kết nối), `sql/01_ingestion_log.sql`.
* `tests/test_ingest.py`: 8 unit test cho kiểm tra schema và MD5 (`python -m pytest tests`).

## 7. Tiêu chí hoàn thành (đã kiểm tra 2026-10-11)
- [x] `row_count` trong log = 79.239; object `s3://raw/academic/ingest_date=2026-10-11/batch_id=20261011T085849Z_7df267/academic_survival_longitudinal.csv` (MD5 `94f87baf205fb7f1446639749a2dd852`).
- [x] Tải ngược file từ MinIO có MD5 trùng với file gốc (kiểm tra tự động trong `ingest.py`).
- [x] Chạy `ingest.py` lần hai → `SKIPPED`, không tạo lô trùng.
- [x] File hỏng (đổi tên cột `Sem_GPA` → `GPA`) → `FAILED`, không upload, mã thoát 1.

---

## 8. Câu hỏi bảo vệ thường gặp
**Hỏi:** Dữ liệu chỉ 7 MB, vì sao còn cần MinIO?  
**Đáp:** MinIO không phục vụ hiệu năng mà phục vụ **lưu vết và tái lập**. Nó giữ bản gốc bất biến của từng đợt nạp, để khi logic làm sạch thay đổi có thể chạy lại từ đầu. Code dùng S3 API nên mở rộng lên cloud không phải sửa.

**Hỏi:** Vì sao chọn Batch mà không dùng Streaming?  
**Đáp:** Nhãn là "bỏ học ở **kỳ sau**" và can thiệp diễn ra theo tuần / học kỳ. Streaming chỉ thêm chi phí và độ phức tạp mà không đem lại giá trị.
