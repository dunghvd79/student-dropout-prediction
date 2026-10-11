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
1. **Kiểm tra schema đầu vào:** đủ 22 cột đúng tên; các cột số đọc được thành số. Sai schema → dừng và ghi lỗi.
2. **Tính checksum MD5** của file. Nếu trùng MD5 với một lô đã `SUCCESS`, bỏ qua (idempotent).
3. **Đặt key theo lô:** `raw/academic/ingest_date=YYYY-MM-DD/academic_survival_longitudinal.csv`.
4. **Upload lên MinIO**, bucket `raw`, không ghi đè lô cũ.
5. **Ghi nhật ký** vào `ingestion_log` (PostgreSQL): `batch_id`, `file_path`, `row_count`, `md5`, `status`, `ingested_at`.

---

## 5. Output
* Object CSV gốc trong MinIO bucket `raw`.
* 1 dòng mới trong `ingestion_log` (ví dụ `row_count = 79239`, `status = SUCCESS`).

## 6. Công cụ / File thực hiện
`src/ingest.py` (thư viện `minio`, `pandas`, `sqlalchemy`, `hashlib`).

## 7. Tiêu chí hoàn thành
- [ ] `row_count` trong log = 79.239.
- [ ] Tải ngược file từ MinIO có MD5 trùng với file gốc.
- [ ] Chạy `ingest.py` lần hai không tạo lô trùng.

---

## 8. Câu hỏi bảo vệ thường gặp
**Hỏi:** Dữ liệu chỉ 7 MB, vì sao còn cần MinIO?  
**Đáp:** MinIO không phục vụ hiệu năng mà phục vụ **lưu vết và tái lập**. Nó giữ bản gốc bất biến của từng đợt nạp, để khi logic làm sạch thay đổi có thể chạy lại từ đầu. Code dùng S3 API nên mở rộng lên cloud không phải sửa.

**Hỏi:** Vì sao chọn Batch mà không dùng Streaming?  
**Đáp:** Nhãn là "bỏ học ở **kỳ sau**" và can thiệp diễn ra theo tuần / học kỳ. Streaming chỉ thêm chi phí và độ phức tạp mà không đem lại giá trị.
