# BƯỚC 13. GIẢI THÍCH MÔ HÌNH (EXPLAINABLE AI – SHAP)
**Giai đoạn D – Học máy** · [← Bước 12](./B12_DANH_GIA_CHON_NGUONG.md) · [Giai đoạn E →](../GIAI_DOAN_E_TRIEN_KHAI_VAN_HANH/README.md)

---

## 1. Nhiệm vụ
Trả lời câu hỏi "**Vì sao** sinh viên này bị cảnh báo?". Đây là điều kiện để cán bộ **tin** và **hành động** theo kết quả, đồng thời là bước kiểm tra cuối cùng xem mô hình có học "đúng" hay không.

---

## 2. Cơ sở lý thuyết

### 2.1. Explainable AI (XAI)
* Các mô hình mạnh (Random Forest, XGBoost) là **"hộp đen"**: hàng trăm cây, không thể đọc trực tiếp.
* XAI cung cấp hai loại giải thích:
  * **Toàn cục (global):** nhìn chung, mô hình dựa vào những yếu tố nào?
  * **Cục bộ (local):** với **một sinh viên cụ thể**, yếu tố nào đẩy rủi ro lên hoặc xuống?
* Trong giáo dục, giải thích cục bộ quyết định **cách can thiệp**: sinh viên rủi ro vì tài chính cần học bổng, sinh viên rủi ro vì nợ môn cần cố vấn học tập.

### 2.2. Giá trị Shapley (Lý thuyết trò chơi hợp tác)
* Bài toán gốc (Lloyd Shapley, 1953): chia "phần thưởng" của một liên minh cho các người chơi **công bằng** theo đóng góp.
* Áp vào ML: "người chơi" là các đặc trưng, "phần thưởng" là chênh lệch giữa dự đoán cho sinh viên này và dự đoán trung bình.
* Đóng góp của đặc trưng *i* là **trung bình đóng góp biên** của nó trên **mọi thứ tự** thêm đặc trưng vào:
  $$\phi_i = \sum_{S \subseteq F \setminus \{i\}} \frac{|S|!\,(|F|-|S|-1)!}{|F|!}\Big[f(S \cup \{i\}) - f(S)\Big]$$
* **Tính chất cộng (local accuracy):**
  $$f(x) = \phi_0 + \sum_{i=1}^{M} \phi_i$$
  Dự đoán = giá trị cơ sở (trung bình) + tổng đóng góp của từng đặc trưng. Giá trị $\phi_i > 0$ đẩy rủi ro lên, $\phi_i < 0$ kéo rủi ro xuống.
* Các tính chất khác bảo đảm "công bằng": **đối xứng** (hai đặc trưng đóng góp như nhau nhận giá trị như nhau), **vô hiệu** (đặc trưng không ảnh hưởng nhận 0), **tuyến tính**.

### 2.3. SHAP và TreeSHAP
* **SHAP** (SHapley Additive exPlanations, Lundberg & Lee, 2017) là khung tính giá trị Shapley cho mô hình ML.
* Tính chính xác theo công thức trên cần duyệt $2^M$ tập con, rất tốn kém. **TreeSHAP** tận dụng cấu trúc cây để tính **chính xác** trong thời gian đa thức, nên với XGBoost / LightGBM / RF có thể giải thích hàng nghìn dòng trong vài giây.
* Với mô hình đã calibration, giải thích thường được tính trên **mô hình cây gốc** (thang log-odds). Thứ tự và chiều tác động của các đặc trưng không đổi.

### 2.4. Các biểu đồ SHAP

| Biểu đồ | Loại | Đọc như thế nào |
|---|---|---|
| **Bar plot** | Toàn cục | Trung bình $\lvert\phi_i\rvert$: đặc trưng nào quan trọng nhất |
| **Beeswarm / Summary** | Toàn cục | Mỗi chấm là một dòng; màu = giá trị đặc trưng (đỏ cao, xanh thấp); vị trí ngang = tác động. Cho thấy cả **chiều** tác động |
| **Dependence plot** | Toàn cục | SHAP của một đặc trưng theo giá trị của nó; thấy được ngưỡng, quan hệ phi tuyến, tương tác |
| **Waterfall** | Cục bộ | Từ giá trị cơ sở, từng đặc trưng cộng/trừ đến dự đoán cuối cho **một sinh viên** |

### 2.5. Giới hạn cần nói rõ
* SHAP giải thích **mô hình**, **không** giải thích **nhân quả trong thực tế**. "Giờ làm thêm đẩy rủi ro lên" nghĩa là mô hình dựa vào nó, chưa chứng minh giảm giờ làm thêm sẽ giảm bỏ học.
* Khi hai đặc trưng tương quan mạnh (ví dụ `Sem_GPA` và `CGPA`), đóng góp có thể bị **chia nhau**, khiến từng đặc trưng trông kém quan trọng hơn thực tế.

### 2.6. SHAP như công cụ kiểm tra rò rỉ
Nếu một đặc trưng "đáng ngờ" (ví dụ biến chỉ có sau khi sinh viên đã bỏ học) đứng đầu bảng SHAP với tác động áp đảo, đó là dấu hiệu **rò rỉ**. Cần quay lại B7 / B9.

---

## 3. Input
Mô hình Production (cây), `X_test` (hoặc mẫu 2.000 – 5.000 dòng).

---

## 4. Biến đổi
1. `shap.TreeExplainer(model)` → tính SHAP values trên `X_test`.
2. **Toàn cục:** bar plot, beeswarm; dependence plot cho 3 – 5 đặc trưng hàng đầu (ví dụ `Financial_Stress`, `Cum_Failed_Courses`, `Delta_GPA`).
3. **Cục bộ:** waterfall cho vài sinh viên điển hình (rủi ro cao, bị bỏ sót, rủi ro thấp).
4. **Hàm `top_reasons(row, k=3)`:** lấy 3 đặc trưng có $\phi_i$ dương lớn nhất, dịch sang tiếng Việt kèm giá trị (ví dụ "Nợ tích lũy 5 môn", "Áp lực tài chính tăng 2,1 điểm so với kỳ trước").
5. **Đối chiếu** SHAP với insight EDA (B6) và luật kết hợp (B8B) để kiểm tra tính nhất quán.

---

## 5. Output
* `reports/figures/shap_*.png`.
* Hàm `top_reasons()` (dùng ở B14 và Streamlit) + bảng ánh xạ tên đặc trưng sang mô tả tiếng Việt.

## 6. Công cụ / File thực hiện
`src/explain.py`, notebook `04_machine_learning_models.ipynb` (`shap`).

## 7. Tiêu chí hoàn thành
- [ ] Top đặc trưng quan trọng có ý nghĩa nghiệp vụ và nhất quán với EDA.
- [ ] Không có đặc trưng đáng ngờ (rò rỉ) trong top.

---

## 8. Câu hỏi bảo vệ thường gặp
**Hỏi:** Feature importance của XGBoost đã có sẵn, sao còn dùng SHAP?  
**Đáp:** Importance mặc định (gain / split count) chỉ cho thứ hạng toàn cục, không cho biết **chiều** tác động và không giải thích được **từng sinh viên**. SHAP có nền tảng lý thuyết (Shapley), nhất quán, và cho cả giải thích cục bộ.

**Hỏi:** SHAP nói giờ làm thêm làm tăng rủi ro, vậy cấm sinh viên đi làm thêm?  
**Đáp:** Không. SHAP giải thích mô hình, không chứng minh nhân quả. Nó gợi ý **hướng hỗ trợ** (ví dụ hỗ trợ tài chính để sinh viên không phải làm thêm quá nhiều), còn hiệu quả cần được kiểm chứng riêng.
