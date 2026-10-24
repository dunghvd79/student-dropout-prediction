# BƯỚC 9. TẠO TẬP CÓ NHÃN & CHIA TRAIN/TEST THEO STUDENT_ID
**Giai đoạn D – Học máy** · [← Giai đoạn D](./README.md) · [Bước 10 →](./B10_TIEN_XU_LY_MAT_CAN_BANG.md)

---

## 1. Nhiệm vụ
Tạo tập huấn luyện / kiểm thử **không rò rỉ**: không lộ nhãn, không có cùng một sinh viên ở cả hai tập, không dùng nhãn chưa xác định.

---

## 2. Cơ sở lý thuyết

### 2.1. Vì sao phải chia tập?
Mục tiêu của mô hình là **dự đoán tốt trên dữ liệu chưa từng thấy** (khả năng tổng quát hóa – generalization). Đánh giá trên chính dữ liệu đã dùng để huấn luyện sẽ cho kết quả lạc quan giả tạo (overfitting). Vì vậy phải giữ riêng một phần dữ liệu (**holdout test set**) để đo khách quan.

### 2.2. Giả định i.i.d. và vì sao nó bị vi phạm
* `train_test_split` ngẫu nhiên theo dòng ngầm giả định các dòng **độc lập và cùng phân phối (i.i.d.)**.
* Trong dữ liệu theo chiều dọc, các dòng của **cùng một sinh viên tương quan mạnh** với nhau (cùng giới tính, thu nhập, học bổng, GPA gần nhau).
* Nếu kỳ 3 của sinh viên A ở Train và kỳ 4 của A ở Test, mô hình chỉ cần "nhớ" sinh viên A là đoán đúng. Đây là **rò rỉ theo nhóm (group leakage)**, khiến điểm Test cao giả tạo.

### 2.3. Chia theo nhóm (Group-based splitting)

| Kỹ thuật | Mô tả |
|---|---|
| `GroupShuffleSplit` | Chọn ngẫu nhiên một tỷ lệ **nhóm** (sinh viên) làm Test |
| `GroupKFold` | Chia các nhóm thành *K* fold, mỗi nhóm chỉ thuộc đúng một fold |
| **`StratifiedGroupKFold`** | Như GroupKFold nhưng cố gắng giữ **tỷ lệ lớp dương** giống nhau giữa các fold. **Phù hợp nhất** khi vừa có nhóm vừa mất cân bằng lớp |

### 2.4. Cross-Validation (K-fold CV)
* Chia Train thành *K* phần; lần lượt dùng 1 phần để kiểm định, *K−1* phần để huấn luyện; lặp *K* lần rồi lấy trung bình ± độ lệch chuẩn.
* Lợi ích: ước lượng hiệu năng **ổn định hơn** một lần chia duy nhất, và dùng toàn bộ Train cho cả huấn luyện lẫn kiểm định.
* Dự đoán của mỗi dòng khi nó nằm ở fold kiểm định gọi là **dự đoán out-of-fold (OOF)**. OOF được dùng để chọn ngưỡng ở B12 mà không phải "chạm" vào Test.

### 2.5. Phân tầng (Stratification)
Với lớp dương ~10%, chia ngẫu nhiên có thể làm một fold có 8%, fold khác 12%, khiến kết quả dao động. Phân tầng giữ tỷ lệ lớp xấp xỉ nhau ở mọi fold và ở Test.

### 2.6. Xử lý nhãn bị cắt (Censored)
* 11.115 dòng `Censored = 1` có nhãn 0 nhưng **chưa xác nhận**: sinh viên có thể bỏ học ngay kỳ sau mà dữ liệu không ghi nhận.
* Đưa chúng vào Train như "chắc chắn ở lại" sẽ gây **nhiễu nhãn** và làm mô hình đánh giá thấp rủi ro. Đưa vào Test sẽ làm sai lệch các chỉ số.
* ⇒ **Loại khỏi Train/Test**, và dùng chính tập này làm **tập cần chấm điểm** (sinh viên đang theo học). Đây cũng là cách đặt bài toán tự nhiên: học từ quá khứ đã biết kết cục, dự đoán cho hiện tại chưa biết kết cục.

### 2.7. Tính tái lập
Cố định `random_state = 42` và **lưu danh sách `Student_ID` của tập Test** ra file, để mọi thành viên và mọi lần chạy lại đều dùng đúng cùng một cách chia.

---

## 3. Input
`feature_table.parquet` (79.239 dòng) + `config/feature_spec.json`.

---

## 4. Biến đổi
1. **Tách Scoring set:** dòng `Censored = 1` → **11.115 dòng**, để dành cho B14.
2. **Tập có nhãn:** dòng `Censored = 0` → **68.124 dòng, 17.928 sinh viên, 6.917 dòng dương (10,2%)**.
3. **Loại cột rò rỉ:** `End_of_Semester_Status`, `Censored`. Tách riêng khóa (`Student_ID`, `Semester`) và nhãn `y`.
4. **Chia Train/Test 80/20 theo nhóm** (`StratifiedGroupKFold(n_splits=5)`, lấy 1 fold làm Test; `groups = Student_ID`; `random_state = 42`) → khoảng **54.500 dòng Train / 13.600 dòng Test**.
5. **Kiểm tra:**
   * Giao của tập `Student_ID` Train và Test = ∅.
   * Tỷ lệ lớp dương hai tập xấp xỉ 10,2%.
6. Trong Train, khởi tạo `StratifiedGroupKFold(n_splits=5)` cho CV ở B11.

---

## 5. Output
* `X_train, y_train, groups_train`, `X_test, y_test`, `X_score` (+ khóa).
* `data/splits/test_student_ids.csv`.

## 6. Công cụ / File thực hiện
`src/ml/train.py` (hàm `make_splits`), notebook `04_machine_learning_models.ipynb` (`scikit-learn`).

## 7. Tiêu chí hoàn thành
- [ ] Các kiểm tra ở mục 4.5 đều đạt (có `assert` trong code).
- [ ] Chạy lại cho ra đúng cùng một cách chia.

---

## 8. Câu hỏi bảo vệ thường gặp
**Hỏi:** Làm sao nhóm đảm bảo mô hình không bị overfitting do dữ liệu lặp lại?  
**Đáp:** Chia tập và CV theo `Student_ID` (StratifiedGroupKFold), nên toàn bộ lịch sử của một sinh viên chỉ nằm ở Train hoặc ở Test.

**Hỏi:** Bỏ 11.115 dòng Censored có làm mất dữ liệu không?  
**Đáp:** Có mất, nhưng đó là những dòng **nhãn không đáng tin**. Tập có nhãn vẫn còn 68.124 dòng với 6.917 ca bỏ học, dư thừa so với ngưỡng tối thiểu ở bài giữa kỳ. Đổi lại nhãn sạch hơn, và tập này trở thành đối tượng chấm điểm thực tế.
