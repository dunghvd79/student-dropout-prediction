# BƯỚC 16. LẬP LỊCH, GIÁM SÁT, HUẤN LUYỆN LẠI & SAO LƯU
**Giai đoạn E – Triển khai & Vận hành** · [← Bước 15](./B15_TRUC_QUAN_HOA_DASHBOARD.md) · [Giai đoạn F →](../GIAI_DOAN_F_KET_THUC/README.md)

---

## 1. Nhiệm vụ
Giúp hệ thống **tự chạy định kỳ**, **ổn định**, **phát hiện sớm khi mô hình xuống cấp**, và **phục hồi được khi có sự cố**.

---

## 2. Cơ sở lý thuyết

### 2.1. MLOps
* MLOps = áp dụng nguyên tắc DevOps (tự động hóa, giám sát, phiên bản hóa) cho hệ thống ML.
* Khác phần mềm thông thường: hệ thống ML có thể **hỏng mà không báo lỗi**. Code vẫn chạy, nhưng dữ liệu thay đổi khiến dự đoán kém đi. Vì vậy cần giám sát **cả hệ thống lẫn mô hình**.
* Vòng đời: *Dữ liệu → Huấn luyện → Đánh giá → Triển khai → Giám sát → (Huấn luyện lại)*.

### 2.2. Điều phối pipeline (Orchestration) và DAG
* Pipeline được biểu diễn dưới dạng **DAG** (Directed Acyclic Graph, đồ thị có hướng không chu trình): mỗi nút là một bước, mỗi cạnh là quan hệ phụ thuộc.
  ```text
  ingest → validate → clean → load → features → predict → monitor
  ```
* Bộ điều phối lo việc chạy đúng thứ tự, **dừng khi một bước lỗi**, chạy lại (retry), ghi log, lập lịch.
* **Công cụ:** cron / Windows Task Scheduler (đơn giản, đủ cho dự án) và **Apache Airflow** (DAG viết bằng Python, giao diện theo dõi; dùng khi mở rộng).

### 2.3. Các loại "trôi" (Drift)

| Loại | Định nghĩa | Ví dụ |
|---|---|---|
| **Data drift** (covariate shift) | Phân phối **đầu vào** $P(X)$ thay đổi | Khóa mới có `Financial_Stress` cao hơn hẳn do kinh tế khó khăn |
| **Concept drift** | Quan hệ **đầu vào – nhãn** $P(y \mid X)$ thay đổi | Chính sách học bổng mới khiến cùng mức áp lực nhưng ít bỏ học hơn |
| **Label drift** (prior shift) | Tỷ lệ nhãn $P(y)$ thay đổi | Tỷ lệ bỏ học chung tăng từ 10% lên 15% |

* Data drift **phát hiện được ngay** (chỉ cần đầu vào). Concept drift chỉ phát hiện được **khi có nhãn thật** (cuối học kỳ sau).

### 2.4. Chỉ số PSI (Population Stability Index)
* Chia biến thành các bin (ví dụ 10 bin theo phân vị của tập huấn luyện); so sánh tỷ lệ mẫu trong từng bin giữa tập huấn luyện (expected, $e_i$) và dữ liệu mới (actual, $a_i$):
  $$PSI = \sum_{i=1}^{B} (a_i - e_i)\,\ln\frac{a_i}{e_i}$$
* **Quy ước diễn giải:**

  | PSI | Ý nghĩa |
  |---|---|
  | < 0,1 | Ổn định |
  | 0,1 – 0,2 | Thay đổi nhẹ, cần theo dõi |
  | > 0,2 | **Thay đổi đáng kể**, cân nhắc huấn luyện lại |

### 2.5. Chiến lược huấn luyện lại
* **Theo lịch (scheduled):** cuối mỗi học kỳ khi có nhãn mới.
* **Theo sự kiện (triggered):** khi PSI > 0,2 hoặc Recall giảm vượt ngưỡng.
* **Champion – Challenger:** mô hình mới (challenger) chỉ thay mô hình đang chạy (champion) nếu **tốt hơn hoặc bằng** trên cùng tập đánh giá. Tránh "cập nhật cho có" làm hệ thống tệ đi.

### 2.6. Sao lưu: quy tắc 3-2-1, RPO và RTO
* **3-2-1:** **3** bản sao dữ liệu, trên **2** loại phương tiện khác nhau, **1** bản ở ngoài site.
* **RPO** (Recovery Point Objective): chấp nhận mất tối đa bao nhiêu dữ liệu, ví dụ 1 tuần, tương ứng sao lưu hàng tuần.
* **RTO** (Recovery Time Objective): phải khôi phục xong trong bao lâu, ví dụ < 1 giờ.
* **Sao lưu chưa từng khôi phục thử = chưa có sao lưu.** Cần diễn tập khôi phục.
* Chỉ cần sao lưu **dữ liệu nguồn và trạng thái** (MinIO raw, PostgreSQL, MongoDB, MLflow). Dữ liệu trung gian (parquet, đặc trưng) tái tạo được từ dữ liệu thô.

---

## 3. Input
Toàn bộ script `src/*.py`, bảng `predictions`, MLflow, dữ liệu kỳ mới.

---

## 4. Biến đổi
1. **Điều phối:** `src/ops/run_pipeline.py` gọi tuần tự `ingest → validate → clean → load → features → predict → publish → monitor`.
   * Mỗi bước chạy đúng lệnh `python -m …` như khi chạy tay, trong một tiến trình riêng.
   * Một bước lỗi thì dừng; `--from STEP` cho phép chạy lại từ bước đó.
   * Không chạy chồng hai lần.
   * Kết quả ghi vào bảng `pipeline_runs`, log chi tiết ở `logs/pipeline/`.
2. **Lập lịch:** Windows Task Scheduler chạy `scripts/chay_dinh_ky.ps1` **hàng tuần** (đăng ký bằng `scripts/dang_ky_lich.ps1`), và chạy tay sau mỗi đợt thi. Script làm 3 việc:
   * Kiểm tra Docker, bật container.
   * Chạy pipeline.
   * Sao lưu.
   
   Khi mở rộng có thể chuyển sang Airflow DAG.
3. **Giám sát 5 metrics** (ghi vào bảng `pipeline_runs`):

   | Metric | Ngưỡng cảnh báo |
   |---|---|
   | Thời gian chạy toàn pipeline | > 2 phút |
   | Tỷ lệ bản ghi lỗi schema | > 0,1% |
   | Tỷ lệ thiếu dữ liệu (`Family_Income`, `LMS_Logins`) | > 10% (mốc hiện tại 4,5% và 1,1%) |
   | Recall / PR-AUC trên dữ liệu kỳ mới đã có nhãn | Giảm > 5 điểm % so với lúc triển khai |
   | Data drift: PSI của `Sem_GPA`, `Financial_Stress`, `Attendance` | PSI > 0,2 |

4. **Huấn luyện lại (quy trình, chưa tự động hóa):** cuối mỗi học kỳ, hoặc khi PSI > 0,2, hoặc khi hiệu năng trên nhãn mới giảm quá ngưỡng:
   * Chạy lại B9 → B11 trên dữ liệu đã có thêm nhãn.
   * Đánh giá **cả champion** (`dropout_model@production`) **lẫn challenger** trên cùng tập Test mới.
   * Chỉ chuyển alias `production` sang challenger nếu PR-AUC **không thấp hơn** champion và Recall tại mốc Trung bình vẫn ≥ 0,80.
   * Phiên bản cũ vẫn nằm trong Registry để quay lại khi cần.
5. **Sao lưu 3-2-1** hàng tuần và sau mỗi đợt nạp cuối kỳ: `pg_dump`, `mongodump`, đồng bộ bucket MinIO, artifact MLflow. Lưu trên máy chính + ổ cứng rời + một bản ngoài site (Google Drive / S3 Glacier). Giữ 4 bản tuần gần nhất + 1 bản cuối mỗi học kỳ.
6. **Diễn tập khôi phục** ít nhất 1 lần: dựng container mới, khôi phục từ bản sao lưu, chạy lại B14 và so sánh kết quả.

---

## 5. Output
* Bảng `pipeline_runs` (`sql/04_pipeline_runs.sql`): mỗi lần chạy một dòng. Gồm:
  * `trigger` (manual / scheduled), `status`, `failed_step`, `seconds`.
  * `steps`: trạng thái và thời gian từng bước.
  * `metrics`: kết quả giám sát.
  * `alerts`: các ngưỡng bị vượt.
* `reports/monitoring_report.md` sinh lại sau mỗi lần chạy. Cảnh báo hiện ở đầu báo cáo, trong `pipeline_runs.alerts` và ở log của Task Scheduler (chưa gửi email).
* Bản sao lưu `backups/<thời điểm>/` (không commit), mỗi bản gồm:
  * 2 dump PostgreSQL.
  * 1 archive MongoDB.
  * Toàn bộ object MinIO.
  * `manifest.json` (SHA-256 và số lượng lúc sao lưu).
  * Giữ 4 bản gần nhất.

**Kết quả** (2026-10-27, dữ liệu hiện tại):

| Chỉ số | Giá trị | Ngưỡng |
|---|---:|---|
| Thời gian pipeline (7 bước + monitor) | 60 – 64 giây | < 120 giây |
| Tỷ lệ lỗi schema của lô thô | 0,00% | ≤ 0,1% |
| Thiếu `Family_Income` / `LMS_Logins` | 4,5% / 1,1% | ≤ 10% |
| PSI `Sem_GPA` / `Financial_Stress` / `Attendance` | 0,014 / 0,010 / 0,011 (ổn định) | ≤ 0,2 |
| PSI lớn nhất trong 35 biến số | `Semester` 0,098 | sinh viên đang học tập trung ở các kỳ đầu hơn Train; vẫn < 0,1 |
| Mức Cao: lần chấm mới nhất / Test | 3,9% / 5,7% | lệch ≤ 50% |
| Hiệu năng trên nhãn mới | chưa có (0 dòng có kết cục) | cần dữ liệu học kỳ sau |

* Sao lưu: 69 file, 11,8 MB, 3 – 4 giây.
* Diễn tập khôi phục: dữ liệu được nạp vào `postgres:16.6` và `mongo:7.0.16` **tạm**, không mở cổng và tự xóa khi xong. Đạt **14/14** kiểm tra:
  * SHA-256 của 69 file.
  * 7 bảng PostgreSQL.
  * MLflow Model Registry (2 phiên bản `dropout_model`).
  * 79.239 document MongoDB.
  * 3 bucket MinIO.
  * RTO đo được **12 giây** (mục tiêu < 1 giờ).

## 6. Công cụ / File thực hiện
* `src/ops/run_pipeline.py`: `python -m src.ops.run_pipeline [--trigger scheduled] [--from STEP] [--file CSV]`. Dùng `--file` để nạp dữ liệu kỳ mới.
* `src/ops/monitor.py`: `collect()` và `write_report()`; chạy riêng bằng `python -m src.ops.monitor`.
  * Hàm thuần: `psi`, `schema_error_rate`, `performance_on_new_labels`.
  * Ngưỡng nằm trong `settings.yaml` → `monitoring`.
* `src/ops/backup.py`: `python -m src.ops.backup` để sao lưu, `python -m src.ops.backup verify [DIR]` để diễn tập khôi phục. Cấu hình ở `settings.yaml` → `backup`.
* `scripts/chay_dinh_ky.ps1` (lần chạy định kỳ, log UTF-8 ở `logs/`) và `scripts/dang_ky_lich.ps1` (đăng ký / gỡ tác vụ `DropoutEWS-HangTuan`: thứ Hai 07:00, chạy bù nếu máy tắt, không cần quyền Admin).
* `tests/test_monitor.py` (6 test) và `tests/test_backup.py` (2 test); tổng 130/130 đạt.
* **Lưu ý vận hành:**
  * Tác vụ chỉ chạy khi người dùng đã đăng nhập và Docker Desktop đang bật. Docker tắt thì script báo lỗi mã 3.
  * Bước `ingest` ghi một dòng `SKIPPED` vào `ingestion_log` mỗi lần chạy với cùng file. Đây là log, không phải lỗi.
  * Bản sao lưu thứ 3 (ngoài site, quy tắc 3-2-1) là chép thủ công thư mục `backups/<thời điểm>` ra ổ rời / Drive.

## 7. Tiêu chí hoàn thành (đã kiểm tra 2026-10-27)
- [x] Pipeline chạy tự động thành công ít nhất 1 lần theo lịch: đăng ký `DropoutEWS-HangTuan` và kích hoạt bằng Task Scheduler → `LastTaskResult = 0`, `run_20261027T091452` (`trigger = scheduled`), pipeline 61 giây + sao lưu 3 giây. Sau đó **đã gỡ tác vụ** theo quyết định của nhóm; đăng ký lại bằng `scripts\dang_ky_lich.ps1`.
- [x] Tính được PSI và ghi vào `pipeline_runs` (`metrics.psi`, `metrics.psi_all_numeric`).
- [x] Khôi phục thử từ bản sao lưu thành công (14/14 kiểm tra, RTO 12 giây).
- [x] Một bước lỗi thì pipeline dừng, ghi `FAILED` và tên bước, trả mã ≠ 0. Đã thử bằng một bước giả không tồn tại; dòng thử đã xóa.

---

## 8. Câu hỏi bảo vệ thường gặp
**Hỏi:** Làm sao biết mô hình đã "cũ" và cần huấn luyện lại?  
**Đáp:** Theo dõi data drift bằng PSI (phát hiện ngay khi có dữ liệu mới) và Recall / PR-AUC trên nhãn thật khi kết thúc học kỳ. Vượt ngưỡng thì huấn luyện lại, và chỉ thay mô hình khi bản mới tốt hơn.

**Hỏi:** Vì sao không sao lưu file đặc trưng?  
**Đáp:** Vì tái tạo được hoàn toàn từ dữ liệu thô bằng code. Sao lưu chỉ cần dữ liệu không tái tạo được: dữ liệu thô, CSDL, mô hình.
