# BƯỚC 0. XÁC ĐỊNH BÀI TOÁN & TIÊU CHÍ THÀNH CÔNG
**Giai đoạn A – Chuẩn bị** · [← Giai đoạn A](./README.md) · [Bước 1 →](./B01_DUNG_MOI_TRUONG.md)

---

## 1. Nhiệm vụ
Thống nhất trong nhóm "**dự đoán cái gì, cho ai, đo bằng gì**" trước khi viết dòng code đầu tiên. Mọi quyết định kỹ thuật về sau (chia tập, chọn mô hình, chọn ngưỡng) đều xuất phát từ định nghĩa ở bước này.

---

## 2. Cơ sở lý thuyết

### 2.1. Quy trình chuẩn CRISP-DM
CRISP-DM (Cross-Industry Standard Process for Data Mining) là khung quy trình phổ biến nhất cho dự án dữ liệu, gồm 6 pha lặp lại:

```text
Business Understanding → Data Understanding → Data Preparation
        ↑                                              ↓
   Deployment  ←  Evaluation  ←  Modeling  ←───────────┘
```

| Pha CRISP-DM | Tương ứng trong dự án |
|---|---|
| Business Understanding | B0 |
| Data Understanding | B2, B3, B6 |
| Data Preparation | B4, B5, B7, B9, B10 |
| Modeling | B8, B11 |
| Evaluation | B12, B13 |
| Deployment | B14 – B16 |

Bước 0 chính là pha **Business Understanding**: chuyển một vấn đề nghiệp vụ ("sinh viên bỏ học gây tổn thất") thành một bài toán dữ liệu có thể đo lường.

### 2.2. Hệ thống Cảnh báo Sớm (Early Warning System – EWS)
* EWS là hệ thống **phát hiện rủi ro trước khi sự kiện xảy ra**, để có thời gian can thiệp (proactive), thay vì phản ứng khi đã muộn (reactive).
* Trong giáo dục, EWS thường dựa trên bộ chỉ báo "ABC": **A**ttendance (chuyên cần), **B**ehavior (hành vi, tương tác), **C**ourse performance (kết quả học tập). Dataset của nhóm có đủ cả ba, cộng thêm nhóm **tài chính – xã hội**.
* Giá trị của EWS nằm ở **hành động** sau cảnh báo (cố vấn, học bổng, hỗ trợ tài chính), nên mô hình phải vừa **dự báo đúng** vừa **giải thích được lý do**.

### 2.3. Dữ liệu theo chiều dọc và dạng "person-period"
* **Dữ liệu cắt ngang (cross-sectional):** mỗi cá thể quan sát **một lần**.
* **Dữ liệu theo chiều dọc (longitudinal / panel):** mỗi cá thể quan sát **nhiều lần theo thời gian**. Ở đây mỗi sinh viên có 1 – 8 dòng, mỗi dòng là một học kỳ.
* Định dạng "một dòng = một cá thể tại một thời điểm" gọi là **person-period**. Bài toán "kỳ sau có bỏ học không" trên dữ liệu person-period chính là mô hình **rủi ro thời gian rời rạc (discrete-time hazard model)**: dự đoán xác suất sự kiện xảy ra ở kỳ *t+1* với điều kiện còn theo học đến kỳ *t*.
* **Hệ quả:**
  1. Các dòng của cùng một sinh viên **không độc lập**, nên phải chia tập theo sinh viên (B9).
  2. Có thể khai thác **quỹ đạo thay đổi** (Delta, tích lũy) làm đặc trưng (B7).
  3. Có hiện tượng **dữ liệu bị cắt (right-censoring)**: với sinh viên đang học, ta chưa biết kết cục (B3, B9).

### 2.4. Phân loại nhị phân & ma trận nhầm lẫn
Mô hình trả về xác suất $p$; chọn ngưỡng $\tau$: dự đoán "bỏ học" nếu $p \ge \tau$.

| | Dự đoán: Bỏ học (1) | Dự đoán: Ở lại (0) |
|---|:---:|:---:|
| **Thực tế: Bỏ học (1)** | TP (bắt đúng) | **FN (bỏ sót)** |
| **Thực tế: Ở lại (0)** | **FP (báo động giả)** | TN |

$$\text{Precision} = \frac{TP}{TP+FP} \qquad \text{Recall} = \frac{TP}{TP+FN} \qquad F_1 = \frac{2 \cdot P \cdot R}{P + R}$$

### 2.5. Vì sao không dùng Accuracy mà dùng PR-AUC?
* Với lớp dương chỉ ~10%, một mô hình **luôn đoán "ở lại"** vẫn đạt Accuracy ≈ 90% nhưng **vô dụng** (Recall = 0).
* **ROC-AUC** (TPR theo FPR) có thể trông "đẹp" khi lớp âm rất lớn, vì FPR = FP/(FP+TN) bị TN khổng lồ "pha loãng".
* **PR-AUC** (Precision theo Recall) tập trung vào lớp dương. Mốc ngẫu nhiên của PR-AUC **bằng tỷ lệ lớp dương** (≈ 0,10), nên dễ đánh giá mô hình hơn baseline bao nhiêu.

### 2.6. Chi phí lỗi không đối xứng
* **FN** (bỏ sót sinh viên sắp bỏ học): mất sinh viên, mất học phí, ảnh hưởng tương lai người học. Chi phí **rất cao**.
* **FP** (báo động giả): tốn thời gian cố vấn cho một sinh viên không cần. Chi phí **thấp hơn**.
* ⇒ Ưu tiên **Recall**, nhưng giữ Precision ở mức chấp nhận được để nguồn lực hỗ trợ không bị quá tải.

---

## 3. Input
* Đề bài học phần, bài giảng (Lecture 3 – Các loại CSDL).
* Tệp `academic_survival_longitudinal.csv` và từ điển dữ liệu trong [`PROJECT_OVERVIEW.md`](../../PROJECT_OVERVIEW.md).

---

## 4. Biến đổi (các việc cần làm)
1. **Đơn vị dự đoán:** một dòng = một sinh viên tại cuối một học kỳ *t*.
2. **Nhãn:** `Target_Dropout_Next_Sem` (1 = bỏ học ở kỳ *t+1*).
3. **Thời điểm dự đoán:** cuối kỳ *t*, chỉ dùng thông tin có sẵn đến hết kỳ *t*.
4. **Người dùng kết quả:** Phòng Đào tạo, Phòng Công tác sinh viên, cố vấn học tập.
5. **Chỉ số đánh giá:** PR-AUC (chính), Recall, Precision, F1, ROC-AUC.
6. **Tiêu chí thành công** (đề xuất ở B0; **kết quả ở B12:** PR-AUC Test 0,391 so với mốc 0,10; Recall 0,820 tại mốc Trung bình, đổi lại theo dõi 41,7% sinh viên; mức Cao 5,7% sinh viên với Precision 0,50; lý do cảnh báo theo nhóm SHAP ở B13):
   * PR-AUC vượt xa mức ngẫu nhiên (≈ 0,10).
   * Recall ≥ 0,80 ở ngưỡng cảnh báo.
   * Giải thích được lý do cảnh báo cho từng sinh viên (SHAP).
7. **Phân công** công việc theo 6 giai đoạn.

---

## 5. Output
* Mục "Problem Statement" và "Tiêu chí thành công" trong báo cáo cuối kỳ.
* Bảng phân công công việc của nhóm.

## 6. Công cụ / File thực hiện
Tài liệu nhóm (Markdown / Google Docs); không cần code.

## 7. Tiêu chí hoàn thành
- [ ] Cả nhóm thống nhất định nghĩa nhãn, đơn vị dự đoán, thời điểm dự đoán.
- [ ] Chốt chỉ số chính (PR-AUC) và mục tiêu Recall.

---

## 8. Câu hỏi bảo vệ thường gặp
**Hỏi:** Mô hình đạt Accuracy 91% có tốt không?  
**Đáp:** Chưa chắc. Tỷ lệ bỏ học ~10% nên đoán "ở lại" cho tất cả đã đạt ~90%. Nhóm đánh giá bằng PR-AUC và Recall.

**Hỏi:** Vì sao ưu tiên Recall hơn Precision?  
**Đáp:** Bỏ sót một sinh viên sắp bỏ học (FN) gây tổn thất lớn hơn nhiều so với một cuộc gặp cố vấn không cần thiết (FP).
