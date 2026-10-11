# BƯỚC 8. KHAI PHÁ DỮ LIỆU (DATA MINING): PHÂN CỤM & LUẬT KẾT HỢP
**Giai đoạn C – Phân tích & Khai phá** · [← Bước 7](./B07_TRICH_XUAT_DAC_TRUNG.md) · [Giai đoạn D →](../GIAI_DOAN_D_HOC_MAY/README.md)

---

## 1. Nhiệm vụ
**Mô tả và khám phá tri thức ẩn** (khác với ML là dự báo):
* **8A – Phân cụm:** chia sinh viên thành các nhóm có đặc điểm chung.
* **8B – Luật kết hợp:** tìm các tổ hợp yếu tố hay đi kèm với bỏ học.

---

## 2. Cơ sở lý thuyết – 8A. Phân cụm (Clustering)

### 2.1. Học không giám sát
Phân cụm **không dùng nhãn**: thuật toán tự gom các điểm "giống nhau" (gần nhau theo một độ đo khoảng cách) vào cùng một nhóm. Nhãn bỏ học chỉ được dùng **sau đó** để mô tả cụm.

### 2.2. Thuật toán K-Means
* **Mục tiêu:** chia *n* điểm thành *k* cụm sao cho tổng bình phương khoảng cách tới tâm cụm (WCSS / inertia) là nhỏ nhất:
  $$J = \sum_{j=1}^{k}\sum_{x \in C_j}\lVert x - \mu_j\rVert^2$$
* **Các bước (thuật toán Lloyd):**
  1. Khởi tạo *k* tâm (dùng **k-means++** để chọn tâm ban đầu xa nhau, hội tụ tốt hơn).
  2. **Gán:** mỗi điểm vào cụm có tâm gần nhất.
  3. **Cập nhật:** tâm mới = trung bình các điểm trong cụm.
  4. Lặp lại 2 – 3 đến khi tâm không đổi.
* **Lưu ý:**
  * Phải **chuẩn hóa** dữ liệu (StandardScaler), nếu không biến có thang lớn như `Family_Income` sẽ lấn át các biến khác.
  * K-Means giả định cụm có dạng "cầu" và kích thước tương đương; nhạy với ngoại lai, nên `log1p` các biến lệch trước.

### 2.3. Chọn số cụm *k*
* **Elbow:** vẽ WCSS theo *k*, chọn điểm "khuỷu tay" nơi WCSS bắt đầu giảm chậm.
* **Silhouette:** với mỗi điểm *i*, $a(i)$ = khoảng cách trung bình tới các điểm cùng cụm, $b(i)$ = khoảng cách trung bình tới cụm gần nhất khác:
  $$s(i) = \frac{b(i) - a(i)}{\max\{a(i), b(i)\}} \in [-1, 1]$$
  Silhouette trung bình càng gần 1 thì cụm càng tách biệt. Chọn *k* có silhouette cao **và** diễn giải được về nghiệp vụ.

### 2.4. DBSCAN
* Phân cụm dựa trên **mật độ**, với 2 tham số: `eps` (bán kính lân cận) và `min_samples`.
* Phân loại điểm: **core** (có ≥ `min_samples` điểm trong `eps`), **border** (trong lân cận của core), **noise** (còn lại).
* Ưu điểm: không cần biết trước *k*, tìm được cụm hình dạng bất kỳ, **phát hiện điểm nhiễu / bất thường**. Nhược: khó chọn `eps`, kém với dữ liệu nhiều chiều.

### 2.5. PCA để trực quan hóa
**Principal Component Analysis** chiếu dữ liệu nhiều chiều xuống 2 trục giữ được nhiều phương sai nhất, để vẽ các cụm trên mặt phẳng.

---

## 3. Cơ sở lý thuyết – 8B. Luật kết hợp (Association Rules)

### 3.1. Khái niệm
* **Item:** một thuộc tính nhị phân (ví dụ `Stress_High`). **Itemset:** tập các item. **Giao dịch (transaction):** một dòng dữ liệu = tập item đúng ở dòng đó.
* **Luật** $X \Rightarrow Y$: "nếu có X thì thường có Y" (ví dụ `{Stress_High, Work_High} ⇒ {DROPOUT}`).

### 3.2. Ba độ đo

| Độ đo | Công thức | Ý nghĩa |
|---|---|---|
| **Support** | $\text{supp}(X \cup Y) = \frac{\#\{X \cup Y\}}{N}$ | Tổ hợp phổ biến đến mức nào |
| **Confidence** | $\text{conf}(X \Rightarrow Y) = \frac{\text{supp}(X \cup Y)}{\text{supp}(X)} = P(Y \mid X)$ | Khi có X thì xác suất có Y |
| **Lift** | $\text{lift} = \frac{\text{conf}(X \Rightarrow Y)}{\text{supp}(Y)} = \frac{P(Y \mid X)}{P(Y)}$ | X làm Y **tăng bao nhiêu lần** so với bình thường. Lift > 1: liên quan dương; = 1: độc lập |

**Ví dụ diễn giải:** tỷ lệ bỏ học chung là 10,2%. Nếu luật `{Stress_High, Work_High} ⇒ {DROPOUT}` có confidence 0,35 thì lift ≈ 0,35 / 0,102 ≈ 3,4: nhóm này có nguy cơ bỏ học **gấp ~3,4 lần** mức chung.

### 3.3. Thuật toán Apriori
* **Nguyên lý Apriori (tính phản đơn điệu):** *mọi tập con của một itemset phổ biến đều phổ biến*. Tương đương: nếu một itemset **không** phổ biến thì mọi tập cha của nó cũng không phổ biến, nên có thể **cắt tỉa** khỏi không gian tìm kiếm.
* **Các bước:** tìm itemset 1 phần tử phổ biến → ghép thành ứng viên 2 phần tử → đếm support, loại bỏ → … → sinh luật từ các itemset phổ biến và lọc theo confidence / lift.

### 3.4. FP-Growth
Nén dữ liệu thành cây **FP-tree** và khai phá trực tiếp trên cây, **không sinh ứng viên**. Chỉ cần quét dữ liệu 2 lần nên nhanh hơn Apriori nhiều khi dữ liệu lớn. Kết quả giống Apriori.

### 3.5. Rời rạc hóa (Discretization)
Luật kết hợp chỉ làm việc với item nhị phân, nên các biến liên tục phải được chia thành khoảng (theo ngưỡng nghiệp vụ hoặc theo phân vị). Ngưỡng nên **có ý nghĩa** (GPA < 2,0 là diện cảnh báo học vụ) để luật dễ diễn giải.

### 3.6. Chọn `min_support` khi lớp hiếm
Lớp bỏ học chỉ ~10%, nên mọi luật có vế phải `{DROPOUT}` có support ≤ 0,10. Đặt `min_support` quá cao (ví dụ 0,1) sẽ không tìm được luật nào. Nhóm dùng **0,01**.

---

## 4. Input
* **8A:** `feature_table.parquet` → tổng hợp lên **mức sinh viên** (20.000 dòng): GPA trung bình, GPA thấp nhất, chuyên cần trung bình, tổng môn trượt, giờ làm thêm trung bình, áp lực tài chính lớn nhất, `First_Generation`, `Scholarship`, số kỳ theo dõi.
* **8B:** tập có nhãn (`Censored = 0`, 68.124 dòng) từ `feature_table.parquet`.

---

## 5. Biến đổi

### 8A. Phân cụm
1. Chọn ~8 – 10 biến; `log1p` các biến lệch; `StandardScaler`.
2. K-Means với *k* = 2 … 10 (`k-means++`, `n_init=10`); vẽ Elbow và Silhouette (trên mẫu 5.000 sinh viên).
3. *(So sánh)* DBSCAN để tìm nhóm bất thường / nhiễu.
4. **Mô tả từng cụm:** trung bình mỗi biến + **tỷ lệ bỏ học của cụm**.
5. **Đặt tên cụm**, ví dụ: "Học tốt – ổn định", "Áp lực tài chính cao", "Sa sút học tập", "Ít tương tác".
6. Vẽ PCA 2 chiều tô màu theo cụm.

> Nếu muốn dùng `cluster_id` làm đặc trưng cho ML thì phải fit K-Means **chỉ trên tập Train** (B9). Mặc định nhóm **không** dùng nó làm đặc trưng.

### 8B. Luật kết hợp
1. **Rời rạc hóa** thành item: `GPA_Low` (< 2,0) · `Failed_2plus` (≥ 2) · `Attendance_Low` (< 75%) · `Stress_High` (≥ 5) · `Work_High` (≥ 25 giờ) · `GPA_Drop` (`Delta_GPA` ≤ −0,3) · `First_Gen` · `No_Scholarship` · `Has_Emergency` · `LMS_Low` (< P25) · `DROPOUT`.
2. Tạo ma trận giao dịch One-Hot.
3. Chạy Apriori / FP-Growth (`mlxtend`), `min_support = 0,01`.
4. Sinh luật; **lọc vế phải = {DROPOUT}**, `confidence ≥ 0,3`, `lift ≥ 2`.
5. Sắp xếp theo lift, diễn giải top 10 – 20 luật, đề xuất hành động can thiệp tương ứng.

---

## 6. Output
* Bảng `student_clusters (student_id, cluster_id, cluster_name)` trong PostgreSQL; bảng hồ sơ cụm; biểu đồ Elbow, Silhouette, PCA.
* `reports/association_rules.csv` + bảng diễn giải và đề xuất chính sách (học bổng, giảm giờ làm thêm, cố vấn).

## 7. Công cụ / File thực hiện
Notebook `03_data_mining_patterns.ipynb` (`scikit-learn`, `mlxtend`).

## 8. Tiêu chí hoàn thành
- [ ] Các cụm có tỷ lệ bỏ học khác biệt rõ và đặt tên được.
- [ ] Có ít nhất 5 luật với lift ≥ 2 được diễn giải.

---

## 9. Câu hỏi bảo vệ thường gặp
**Hỏi:** Confidence cao có đủ để nói luật tốt không?  
**Đáp:** Không. Nếu vế phải vốn đã phổ biến thì confidence cao cũng không có ý nghĩa. Phải xem **lift**: lift > 1 mới chứng tỏ vế trái thực sự làm tăng khả năng của vế phải.

**Hỏi:** Vì sao phải chuẩn hóa trước K-Means?  
**Đáp:** K-Means dùng khoảng cách Euclid. Nếu không chuẩn hóa, `Family_Income` (hàng chục nghìn) sẽ lấn át hoàn toàn `Sem_GPA` (0 – 4).
