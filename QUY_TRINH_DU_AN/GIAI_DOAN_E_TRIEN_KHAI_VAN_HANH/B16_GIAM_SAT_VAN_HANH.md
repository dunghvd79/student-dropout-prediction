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
1. **Điều phối:** `src/run_pipeline.py` gọi tuần tự `ingest → validate → clean → load → features → predict → monitor`; dừng và ghi lỗi nếu một bước thất bại.
2. **Lập lịch:** Windows Task Scheduler / cron chạy **hàng tuần** và **sau mỗi đợt thi**. Khi mở rộng có thể chuyển sang Airflow DAG.
3. **Giám sát 5 metrics** (ghi vào bảng `pipeline_runs`):

   | Metric | Ngưỡng cảnh báo |
   |---|---|
   | Thời gian chạy toàn pipeline | > 2 phút |
   | Tỷ lệ bản ghi lỗi schema | > 0,1% |
   | Tỷ lệ thiếu dữ liệu (`Family_Income`, `LMS_Logins`) | > 10% (mốc hiện tại 4,5% và 1,1%) |
   | Recall / PR-AUC trên dữ liệu kỳ mới đã có nhãn | Giảm > 5 điểm % so với lúc triển khai |
   | Data drift: PSI của `Sem_GPA`, `Financial_Stress`, `Attendance` | PSI > 0,2 |

4. **Huấn luyện lại:** cuối mỗi học kỳ hoặc khi vượt ngưỡng → chạy lại B9 – B12; chỉ thăng hạng lên Production nếu PR-AUC **không thấp hơn** champion.
5. **Sao lưu 3-2-1** hàng tuần và sau mỗi đợt nạp cuối kỳ: `pg_dump`, `mongodump`, đồng bộ bucket MinIO, artifact MLflow. Lưu trên máy chính + ổ cứng rời + một bản ngoài site (Google Drive / S3 Glacier). Giữ 4 bản tuần gần nhất + 1 bản cuối mỗi học kỳ.
6. **Diễn tập khôi phục** ít nhất 1 lần: dựng container mới, khôi phục từ bản sao lưu, chạy lại B14 và so sánh kết quả.

---

## 5. Output
* Bảng `pipeline_runs`; cảnh báo khi vượt ngưỡng (log / email).
* Các bản sao lưu; phiên bản mô hình mới (nếu có).

## 6. Công cụ / File thực hiện
`src/run_pipeline.py`, `src/monitor.py`, `backup.ps1` / `backup.sh`, Windows Task Scheduler / cron (Airflow khi mở rộng).

## 7. Tiêu chí hoàn thành
- [ ] Pipeline chạy tự động thành công ít nhất 1 lần theo lịch.
- [ ] Tính được PSI và ghi vào `pipeline_runs`.
- [ ] Khôi phục thử từ bản sao lưu thành công.

---

## 8. Câu hỏi bảo vệ thường gặp
**Hỏi:** Làm sao biết mô hình đã "cũ" và cần huấn luyện lại?  
**Đáp:** Theo dõi data drift bằng PSI (phát hiện ngay khi có dữ liệu mới) và Recall / PR-AUC trên nhãn thật khi kết thúc học kỳ. Vượt ngưỡng thì huấn luyện lại, và chỉ thay mô hình khi bản mới tốt hơn.

**Hỏi:** Vì sao không sao lưu file đặc trưng?  
**Đáp:** Vì tái tạo được hoàn toàn từ dữ liệu thô bằng code. Sao lưu chỉ cần dữ liệu không tái tạo được: dữ liệu thô, CSDL, mô hình.
