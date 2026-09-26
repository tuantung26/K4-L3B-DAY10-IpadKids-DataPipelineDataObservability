# Bao Cao Pha 1: Baseline Pipeline & Data Observability

## 1. Tong Quan Trang Thai (Executive Summary)

- **Trang thai Pipeline:** PASSED
- **Quality Gate (GX 1.x):** PASS
- **Freshness SLA:** FRESH
- **Retrieval Hit Rate:** 100.00%
- **Mean Token F1:** 0.8000

---

## 2. Du Lieu Nguon & Tien Xu Ly (Data Ingestion & Cleaning)

| Thong so | Gia tri |
| :--- | :--- |
| **Nguon du lieu (Source API)** | Crossref REST API |
| **Truy van tim kiem (Query)** | `agentic retrieval augmented generation large language model` |
| **Bo loc (Filter)** | `from-pub-date:2026-03-30,has-abstract:true` |
| **So ban ghi tho (Raw Records)** | 24 |
| **So ban ghi sach (Clean Rows)** | 24 |

---

## 3. Hieu Nang Danh Gia Nen (Baseline Evaluation & Benchmarks)

| Chi so (Metric) | Ket qua | Y nghia / Nguong ky vong |
| :--- | :--- | :--- |
| **So cau hoi benchmark (`samples`)** | 10 | Tap testset 10 cau phu 4 nhom nghiep vu |
| **Ty le truy xuat trung (`retrieval_hit_rate`)** | **100.00%** | Do luong ty le tai lieu ground truth nam trong top retrieved |
| **Do trung khop tu khoa (`mean_token_f1`)** | **0.8000** | Do luong muc do trung khop giua cau tra loi va ground truth |
| **Do chinh xac cua Giam khao (`judge_accuracy`)** | 80.00% | Ty le cau tra loi duoc LLM/Heuristic Judge xac nhan Materially Correct |
| **Diem trung binh Giam khao (`mean_judge_score`)** | 4.20 / 5.0 | Thang diem tu 1 den 5 danh gia chat luong cau tra loi |

### Danh gia chuyen sau voi Ragas
- **Ragas Status:** Skipped (Set RUN_RAGAS=1 to enable the slower Ragas pass.)

---

## 4. Chot Kiem Dich Chat Luong Du Lieu (Data Quality Gate - Great Expectations 1.x)

- **Ket qua tong quat GX:** DAT (PASS)

| Expectation Type | Tham so / Dieu kien | Trang thai |
| :--- | :--- | :--- |
| `expect_table_row_count_to_be_between` | batch_id=papers_source_baseline-papers_asset_baseline, min_value=5, max_value=5000 | PASS |
| `expect_column_values_to_not_be_null` | batch_id=papers_source_baseline-papers_asset_baseline, column=paper_id | PASS |
| `expect_column_values_to_be_unique` | batch_id=papers_source_baseline-papers_asset_baseline, column=paper_id | PASS |
| `expect_column_values_to_not_be_null` | batch_id=papers_source_baseline-papers_asset_baseline, column=title | PASS |
| `expect_column_values_to_not_be_null` | batch_id=papers_source_baseline-papers_asset_baseline, column=text_for_embedding | PASS |
| `expect_column_value_lengths_to_be_between` | batch_id=papers_source_baseline-papers_asset_baseline, column=summary, min_value=30 | PASS |

---

## 5. Giam Sat Do Tuoi Moi (Freshness SLA Monitoring)

- **Trang thai Freshness SLA:** FRESH
- **Tieu chuan SLA:** Ty le bai bao qua han (`age_days > 180`) khong duoc vuot qua 25%.

| Tieu chi | Gia tri thuc te | Nguong SLA |
| :--- | :--- | :--- |
| **Nguong tuoi toi da (`threshold_days`)** | 180 ngay | 180 ngay |
| **Tong so bai bao theo doi** | 24 | - |
| **So bai bao qua han (`stale_rows`)** | 0 | - |
| **Ty le qua han (`stale_ratio`)** | **0.00%** | <= 25.00% |
| **Ngay xuat ban moi nhat (`latest_published`)** | 2026-09-15 | - |
| **Ngay xuat ban cu nhat (`oldest_published`)** | 2026-04-01 | - |

---

## 6. Ket Luan & San Sang Cho Pha 2 (Conclusion)

- Toan bo du lieu sach da duoc lap chi muc vector tren ChromaDB collection `papers-baseline`.
- Cac chi so nen (Baseline Benchmarks) phan anh day du nang luc truy xuat va tra loi cua RAG Agent tren du lieu chuan.
- Chot kiem dich chat luong du lieu va Freshness SLA da duoc thiet lap thanh cong lam can cu phat hien su co (Silent Failure) khi tiem du lieu ban tai Pha 2.
