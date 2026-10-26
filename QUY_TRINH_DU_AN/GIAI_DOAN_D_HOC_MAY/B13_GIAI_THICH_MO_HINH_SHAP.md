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

### 2.3. SHAP cho mô hình tuyến tính (LinearSHAP) và cho mô hình cây (TreeSHAP)
* **SHAP** (SHapley Additive exPlanations, Lundberg & Lee, 2017) là khung tính giá trị Shapley cho mô hình ML.
* Tính chính xác theo công thức trên cần duyệt $2^M$ tập con, rất tốn kém. Với hai họ mô hình phổ biến có lời giải chính xác:
  * **Mô hình cây (TreeSHAP):** tận dụng cấu trúc cây, tính chính xác trong thời gian đa thức (XGBoost, LightGBM, RF).
  * **Mô hình tuyến tính (LinearSHAP)**, đúng với **mô hình cuối của dự án (Logistic Regression)**. Trên thang log-odds, khi coi các đặc trưng độc lập (interventional), Shapley có công thức đóng:
    $$\phi_j = \beta_j\,\big(x_j - \mathbb{E}[x_j]\big), \qquad \phi_0 = \beta_0 + \sum_j \beta_j\,\mathbb{E}[x_j]$$
    với $x_j$ là giá trị **sau tiền xử lý** (chuẩn hóa, log1p, One-Hot) và $\mathbb{E}$ lấy trên tập Train. Không cần xấp xỉ, giải thích 13.650 dòng trong chưa tới một giây (`shap.LinearExplainer`).
* SHAP được tính trên **log-odds**, vì ở thang này các đóng góp **cộng** được. Xác suất = sigmoid(φ₀ + Σφ), không cộng tuyến tính.

### 2.4. Gom SHAP theo nhóm khái niệm (grouped SHAP)
* Nhờ tính cộng, tổng φ của một nhóm đặc trưng vẫn là một giải thích hợp lệ: "phần rủi ro đến từ nhóm này".
* Cần gom vì hai lý do:
  1. **One-Hot:** `Gender` thành 3 cột; từng cột có |φ| lớn nhưng cộng lại gần 0. Phải cộng về biến gốc.
  2. **Đa cộng tuyến:** `Sem_GPA`, `CGPA`, `GPA_Roll3`, `GPA_prev` tương quan 0,92 – 0,98. LogReg chia hệ số giữa chúng, có thể có biến mang **dấu ngược**. Ở lần chạy đầu (`C = 1,22`), hệ số `GPA_Roll3` dương; đọc riêng biến này sẽ ra lý do vô lý: "GPA trung bình 3 kỳ cao làm tăng rủi ro". Đọc theo nhóm "Kết quả học tập" thì đúng. Mô hình hiện tại vẫn có `Work_prev` ngược dấu `Work_Hours`.
* Dự án dùng 13 nhóm (học tập, trượt môn, chuyên cần, LMS, áp lực tài chính, thu nhập & học phí, chi phí đột xuất, học bổng, làm thêm, gặp cố vấn, thế hệ đầu, tiến trình & tải học, nhân khẩu & nơi ở). Mỗi đặc trưng thuộc đúng một nhóm.

### 2.5. Các biểu đồ SHAP

| Biểu đồ | Loại | Đọc như thế nào |
|---|---|---|
| **Bar plot** | Toàn cục | Trung bình $\lvert\phi_i\rvert$: đặc trưng nào quan trọng nhất |
| **Beeswarm / Summary** | Toàn cục | Mỗi chấm là một dòng; màu = giá trị đặc trưng (đỏ cao, xanh thấp); vị trí ngang = tác động. Cho thấy cả **chiều** tác động |
| **Dependence plot** | Toàn cục | SHAP của một đặc trưng theo giá trị của nó; thấy được ngưỡng, quan hệ phi tuyến, tương tác |
| **Waterfall** | Cục bộ | Từ giá trị cơ sở, từng đặc trưng cộng/trừ đến dự đoán cuối cho **một sinh viên** |

### 2.6. Giới hạn cần nói rõ
* SHAP giải thích **mô hình**, **không** giải thích **nhân quả trong thực tế**. "Giờ làm thêm đẩy rủi ro lên" nghĩa là mô hình dựa vào nó, chưa chứng minh giảm giờ làm thêm sẽ giảm bỏ học.
* Khi hai đặc trưng tương quan mạnh (ví dụ `Sem_GPA` và `CGPA`), đóng góp có thể bị **chia nhau**, khiến từng đặc trưng trông kém quan trọng hơn thực tế.

* Cũng vì không phải nhân quả, hai nhóm vẫn được tính vào điểm rủi ro nhưng **không được nêu làm lý do cảnh báo**: *Nhân khẩu & nơi ở* (không can thiệp được; nêu ra dễ thành phân biệt đối xử) và *Gặp cố vấn* (nhân quả ngược: sinh viên gặp khó mới đi gặp cố vấn, insight #8 của B6).

### 2.7. SHAP như công cụ kiểm tra rò rỉ
Nếu một đặc trưng "đáng ngờ" (ví dụ biến chỉ có sau khi sinh viên đã bỏ học) đứng đầu bảng SHAP với tác động áp đảo, đó là dấu hiệu **rò rỉ**. Cần quay lại B7 / B9. Dấu hiệu thứ hai, khó thấy hơn: một biến **hiếm** (ít dòng) nhưng có hệ số cực lớn. Trung bình |φ| của nó nhỏ vì ít dòng, nhưng trên từng dòng nó áp đảo. `explain.py` kiểm tra tự động cả hai.

**Rò rỉ dự án đã phát hiện ở bước này:** `Income_Missing` có hệ số **3,50** (biến mạnh nhất kế tiếp chỉ 0,84), SHAP trung bình +3,45 log-odds trên các dòng mang cờ. Truy ngược về B4: cờ được định nghĩa là "không khai báo thu nhập ở **bất kỳ kỳ nào**" (ffill + bfill), tức là nhìn cả các kỳ tương lai. Sinh viên bỏ học sau kỳ 1 chỉ có một kỳ để khai báo, nên:

| Định nghĩa cờ | Số dòng có nhãn | Tỷ lệ bỏ học |
|---|---:|---:|
| Không khai báo ở *kỳ nào* (bản cũ, nhìn tương lai) | 118 | **84,7%** |
| Chưa khai báo *tính đến kỳ t* (đúng thời điểm) | 931 | 10,7% ≈ mức nền |
| ↳ trong đó: kỳ sau mới khai báo | 813 | 0% (có kỳ sau nghĩa là chưa bỏ) |

Đã sửa B4 (chỉ ffill), B5 (cờ theo kỳ lưu ở MongoDB), chạy lại B7 → B12. Tập Test được đánh giá **lần 2**, có ghi lý do trong `evaluation_report.md` và tag MLflow. Lần này không phải "nhìn Test để chọn": thay đổi xuất phát từ một lỗi rò rỉ phát hiện độc lập với kết quả Test.

---

## 3. Input
Mô hình Production (`data/models/dropout_model.joblib`, giống `dropout_model@production`), `X_test` (13.650 dòng) để giải thích, `X_train` làm nền (tính $\mathbb{E}[x]$), `config/risk_thresholds.json`.

---

## 4. Biến đổi
1. `shap.LinearExplainer(LogReg, masker = Independent(X_train sau tiền xử lý))` → φ trên `X_test`. Kiểm tra **tính cộng**: φ₀ + Σφ = log-odds của mô hình (sai số ~1e-15).
2. Cộng φ của các cột One-Hot về biến gốc (43 đặc trưng), rồi gom thành 13 nhóm.
3. **Toàn cục:** bar plot và beeswarm theo nhóm; beeswarm 15 đặc trưng đơn lẻ (để thấy vấn đề dấu ngược); dependence của 3 nhóm lớn theo biến đại diện.
4. **Cục bộ:** waterfall theo nhóm cho 3 sinh viên điển hình (trung vị xác suất của: rủi ro Cao và bỏ học thật; bị bỏ sót; rủi ro Thấp và ở lại).
5. **Hàm `top_reasons(group_phi, row, k=3)`:** k nhóm có φ dương lớn nhất (bỏ qua hai nhóm không nêu làm lý do), mỗi nhóm kèm mô tả bằng giá trị thật, ví dụ "Trượt môn: Trượt 2 môn kỳ này, tích lũy 2 môn", "Áp lực tài chính: Chỉ số áp lực tài chính 4,2 (tăng 0,7 so với kỳ trước)".
6. **Kiểm tra rò rỉ** tự động và **đối chiếu** với insight EDA (B6) và luật kết hợp (B8).

---

## 5. Output
* `reports/explanation_report.md` (sinh tự động), `reports/shap_group_importance.csv`, 7 biểu đồ `reports/figures/shap_*.png` (bar và beeswarm theo nhóm, beeswarm 15 đặc trưng, dependence, 3 waterfall).
* `GROUPS` (13 nhóm, nhãn tiếng Việt), `DESCRIBE` (câu mô tả theo giá trị thật), `explain()`, `top_reasons()`, `reasons_text()`: dùng lại ở B14 (chấm điểm hằng kỳ) và B16 (dashboard).

**Kết quả** (13.650 dòng Test, mô hình `dropout_model` v2):

| Nhóm | Trung bình \|SHAP\| | % tổng | Là lý do số 1 ở mức Cao |
|---|---:|---:|---:|
| Kết quả học tập | 0,426 | 19,8% | 47,1% |
| Trượt môn | 0,397 | 18,4% | 31,5% |
| Thế hệ đầu vào đại học | 0,344 | 16,0% | 0,5% |
| Áp lực tài chính | 0,343 | 15,9% | 20,8% |
| Học bổng | 0,256 | 11,9% | 0% |
| Chuyên cần | 0,143 | 6,6% | 0,1% |
| 7 nhóm còn lại | ≤ 0,096 mỗi nhóm | 11,4% | 0% |

* **Tính cộng:** φ₀ + Σφ khớp log-odds của mô hình, sai số 1,8e-15. φ₀ = −2,71 (xác suất 6,2% cho "sinh viên trung bình").
* **Nhất quán với EDA và B8:**
  * Học tập mạnh nhất (insight #2, #5), tài chính thứ hai (#3), thế hệ đầu và học bổng (#6).
  * Nhân khẩu chỉ chiếm 0,8% (#9); chi phí đột xuất ≈ 0 (khớp MI ≈ 0 ở B7).
  * Luật mạnh nhất của B8, `Failed_2plus + GPA_Low` (lift 5,5), ứng đúng với hai nhóm dẫn đầu.
* **Lý do số 1 ở mức Cao** chỉ rơi vào 3 nhóm can thiệp được: học tập, trượt môn, tài chính. Ba nhóm này tương ứng với cố vấn học tập, phụ đạo / học lại và hỗ trợ tài chính.
* **Hệ số ngược dấu** (vì vậy phải gom nhóm), liệt kê tự động trong báo cáo:
  * Ở lần chạy đầu (`C = 1,22`): `GPA_Roll3` dương, ngược dấu với `Sem_GPA`.
  * Ở mô hình hiện tại (`C = 0,011`, chính quy hóa mạnh hơn): còn `Work_prev` −0,07 so với `Work_Hours` +0,07 (tương quan 0,87), và `Tuition_Base` so với `Tuition_to_Income`.
* **Kiểm tra rò rỉ: đạt cả 5.**
  * Biến lớn nhất (`First_Generation`) chỉ chiếm 13% tổng |SHAP|.
  * `Income_Missing` chỉ còn +0,11 log-odds (mô hình cũ +3,45).

## 6. Công cụ / File thực hiện
* `src/ml/explain.py`: chạy `python -m src.ml.explain` (đọc `data/models/dropout_model.joblib`, giống `dropout_model@production`). Trả mã lỗi 1 nếu một kiểm tra rò rỉ không đạt.
* `tests/test_explain.py`: 9 unit test:
  * Mỗi đặc trưng thuộc đúng một nhóm; One-Hot được cộng về biến gốc.
  * Tính cộng đúng, và khớp công thức đóng β(x − E[x]).
  * `top_reasons` chỉ lấy φ > 0 và bỏ nhóm không can thiệp được.
  * Định dạng số kiểu Việt Nam; xử lý giá trị thiếu; phát hiện cặp ngược dấu.
* Sửa rò rỉ:
  * `src/etl/clean.py`: `Family_Income` chỉ ffill.
  * `src/etl/load.py`: cờ theo kỳ lưu ở MongoDB; `merge_static`, `static_from_tables`.
  * `src/ml/evaluate.py`: `--reason` và `history` khi đánh giá lại Test.
  * `config/settings.yaml`: `model.final`.
* Notebook `04_machine_learning_models.ipynb`, mục 8.

## 7. Tiêu chí hoàn thành (đã kiểm tra 2026-10-26)
- [x] Top nhóm quan trọng có ý nghĩa nghiệp vụ và nhất quán với EDA (B6) và luật kết hợp (B8).
- [x] Không có đặc trưng đáng ngờ trong top. Kiểm tra tự động **đã bắt được** một rò rỉ (`Income_Missing`); rò rỉ đã được sửa tận gốc ở B4 và các bước sau đã chạy lại.
- [x] `top_reasons()` sinh câu lý do bằng giá trị thật, không nêu nhóm nhân khẩu / gặp cố vấn.

---

## 8. Câu hỏi bảo vệ thường gặp
**Hỏi:** Mô hình là Logistic Regression, sao không đọc thẳng hệ số mà phải dùng SHAP?  
**Đáp:** Hệ số chỉ cho biết tác động của *một đơn vị* thay đổi (sau chuẩn hóa), không cho biết tác động với **từng sinh viên** so với mức trung bình. Với LogReg, SHAP chính là β·(x − E[x]), tức hệ số nhân độ lệch của sinh viên. Thêm nữa, các biến tương quan làm hệ số đơn lẻ có thể ngược dấu; SHAP có tính cộng nên gom theo nhóm vẫn chính xác.

**Hỏi:** SHAP giúp gì ngoài việc giải thích?  
**Đáp:** Phát hiện rò rỉ. Nhóm thấy `Income_Missing` (chỉ 1,5% dòng) có hệ số 3,5, lớn gấp 4 lần biến mạnh kế tiếp. Truy ngược thì cờ này dùng thông tin các kỳ tương lai. Sửa xong, PR-AUC giảm ~0,011: con số thấp hơn nhưng trung thực.

**Hỏi:** Sửa lỗi xong lại đánh giá Test lần nữa, vậy có phải "nhìn Test nhiều lần" không?  
**Đáp:** Nhìn Test nhiều lần chỉ là vấn đề khi kết quả Test được dùng để **chọn** (mô hình, tham số, ngưỡng). Ở đây lý do đánh giá lại là một lỗi phát hiện độc lập trên Train (SHAP). Mô hình và chính sách ngưỡng vẫn chốt trên Train trước khi đánh giá lại. Lần đánh giá cũ, lý do và số lần đều được ghi công khai.

**Hỏi:** Feature importance của XGBoost đã có sẵn, sao còn dùng SHAP?  
**Đáp:** Importance mặc định (gain / split count) chỉ cho thứ hạng toàn cục, không cho biết **chiều** tác động và không giải thích được **từng sinh viên**. SHAP có nền tảng lý thuyết (Shapley), nhất quán, và cho cả giải thích cục bộ.

**Hỏi:** SHAP nói giờ làm thêm làm tăng rủi ro, vậy cấm sinh viên đi làm thêm?  
**Đáp:** Không. SHAP giải thích mô hình, không chứng minh nhân quả. Nó gợi ý **hướng hỗ trợ** (ví dụ hỗ trợ tài chính để sinh viên không phải làm thêm quá nhiều), còn hiệu quả cần được kiểm chứng riêng.
