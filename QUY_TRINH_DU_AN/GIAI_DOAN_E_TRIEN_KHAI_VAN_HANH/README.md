# GIAI ĐOẠN E – TRIỂN KHAI & VẬN HÀNH
[← Giai đoạn D](../GIAI_DOAN_D_HOC_MAY/README.md) · [Về tổng quan](../README.md) · [Giai đoạn F →](../GIAI_DOAN_F_KET_THUC/README.md)

## Mục tiêu giai đoạn
Đưa mô hình từ notebook thành **hệ thống chạy được**: định kỳ chấm điểm rủi ro cho sinh viên đang học, hiển thị cho người dùng cuối, **tự giám sát** và **tự phục hồi** (huấn luyện lại, sao lưu). Đây là phần **Deployment** của CRISP-DM và là trọng tâm của **MLOps**.

```text
           ┌──────────── [B16] Lập lịch hàng tuần / sau mỗi đợt thi ────────────┐
           ▼                                                                    │
 ingest → validate → clean → load → features ──► [B14] Batch Inference           │
                                                    │  (alias production)         │
                                                    ▼                             │
                                          PostgreSQL: predictions                 │
                                                    │                             │
                                                    ▼                             │
                                   [B15] Power BI (quản lý) · Streamlit (cố vấn)   │
                                                    │                             │
                                                    ▼                             │
                         [B16] Giám sát 5 metrics ── vượt ngưỡng? ── Retrain (B9–B12)
                                                    └── Sao lưu 3-2-1
```

## Các bước

| Bước | Tên | Lý thuyết chính | Output |
|:---:|---|---|---|
| [**B14**](./B14_DU_DOAN_THEO_LO.md) | Dự đoán theo lô | Batch / Online serving, training–serving skew, feature contract, ghi lũy đẳng, phân tầng rủi ro | Bảng `predictions` |
| [**B15**](./B15_TRUC_QUAN_HOA_DASHBOARD.md) | Trực quan hóa | Nguyên tắc trực quan hóa, dashboard chiến lược / tác nghiệp, chọn biểu đồ, BI và web app | Power BI `.pbix`, Streamlit app |
| [**B16**](./B16_GIAM_SAT_VAN_HANH.md) | Giám sát & vận hành | MLOps, điều phối DAG, data drift / concept drift, PSI, chiến lược retrain, champion–challenger, sao lưu 3-2-1, RPO/RTO | Log vận hành, bản sao lưu |

## Input → Output của cả giai đoạn
* **Input:** Mô hình `dropout_model@production`, `feature_spec.json`, `config/risk_thresholds.json`, Scoring set, dữ liệu kho.
* **Output:** `predictions` (11.115 dòng / lần chạy), dashboard Power BI, ứng dụng Streamlit, pipeline chạy theo lịch, bảng `pipeline_runs`, bản sao lưu.

## Điều kiện để sang Giai đoạn F
- [ ] Pipeline chạy tự động thành công ít nhất 1 lần theo lịch.
- [ ] Từ dashboard tìm được một sinh viên rủi ro cao và xem được lý do.
- [ ] Khôi phục thử từ bản sao lưu thành công.
