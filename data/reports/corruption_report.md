# Bao Cao Doi Chieu 3 Trang Thai: Baseline vs Corrupted vs Repaired

## 1. Bang Tong Hop Doi Chieu 3 Trang Thai (Executive Comparison Table)

| Chi so / Tin hieu | Baseline (Sieu chuan) | Corrupted (Bi tiem loi) | Repaired (Sau phuc hoi) | Thay doi do Corruption | Muc do phuc hoi | Nhan xet |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| **`retrieval_hit_rate`** | **100.00%** | **60.00%** | **100.00%** | `-40.00%` | `+40.00%` | Sut giam manh khi du lieu bi hong |
| **`mean_token_f1`** | **0.8000** | **0.4000** | **0.8000** | `-0.4000` | `+0.4000` | Nhieu va rong summary lam hong cau tra loi |
| **`judge_accuracy`** | 80.00% | 40.00% | 80.00% | `-40.00%` | `+40.00%` | Giam khao danh gia do chinh xac tut giam |
| **`mean_judge_score`** | 4.20 / 5.0 | 2.60 / 5.0 | 4.20 / 5.0 | `-1.60` | `+1.60` | Thang diem danh gia 1 - 5 |
| **Quality Gate (GX 1.x)** | **PASS** | **FAIL** | **PASS** | Vi pham kiem dinh | Phuc hoi thanh cong | Chot kiem dich chat luong |
| **Freshness SLA** | **FRESH** | **FRESH** | **FRESH** | Dat | Phuc hoi do tuoi moi | Nguong toi da 180 ngay |
| **Trang thai Pipeline Tong The** | **PASSED** | **FAILED (BLOCKED)** | **PASSED** | Bao dong do du lieu ban | Vuot qua toan bo chot kiem dich | Chi pass khi ca GX va SLA dat |

---

## 2. Chi Tiet Kiem Dinh Chat Luong Du Lieu (Great Expectations 1.x)

Bang doi chieu tung Expectation qua 3 trang thai:

| Expectation Type | Baseline | Corrupted | Repaired | Nhan xet |
| :--- | :--- | :--- | :--- | :--- |
| `expect_table_row_count_to_be_between` | PASS | PASS | PASS | On dinh |
| `expect_column_values_to_not_be_null` | PASS | PASS | PASS | On dinh |
| `expect_column_values_to_be_unique` | PASS | FAIL | PASS | Da duoc phuc hoi sau repair |
| `expect_column_value_lengths_to_be_between` | PASS | FAIL | PASS | Da duoc phuc hoi sau repair |

- **Giai thich nguyen nhan vi pham:**
  - `ExpectColumnValueLengthsToBeBetween`: Phat hien cac dong bi xoa rong summary (blank summary) hoac truncate khong du do dai toi thieu 30 ky tu.
  - `ExpectColumnValuesToBeUnique`: Phat hien cac dong trung lap `paper_id` do hanh vi nhan ban ban ghi (duplicate rows).
  - `ExpectColumnValuesToNotBeNull`: Phat hien cac ban ghi thieu thong tin cot bat buoc.

---

## 3. Giam Sat Do Tuoi Moi (Freshness SLA Monitoring)

| Thong so Freshness | Baseline | Corrupted | Repaired | Nguong SLA |
| :--- | ---: | ---: | ---: | :--- |
| **So dong qua han (`stale_rows`)** | 0 | 3 | 0 | - |
| **Ty le qua han (`stale_ratio`)** | 0.00% | **13.64%** | **0.00%** | <= 25.00% |
| **Ngay xuat ban moi nhat** | - | 2026-09-04 | 2026-09-15 | - |
| **Ngay xuat ban cu nhat** | - | 2025-04-01 | 2026-04-01 | - |
| **Danh gia trang thai Freshness** | **FRESH** | **FRESH** | **FRESH** | **FRESH** |

---

## 4. Phan Tich Quan He Nhan Qua & Su Co Suy Thoai (Causality & Impact Analysis)

### 4.1. Chuoi Nguyen Nhan - He Qua (Sut Giam do Data Corruption)
```text
[Tiem 6 Kich Ban Loi Du Lieu]
  │
  ├──> Drop latest records (20%) & Duplicate rows ──> GX: Vi pham Unique & Count Expectation
  ├──> Blank summary & Truncate title (<8 chars)  ──> GX: Vi pham Length & NotNull Expectation
  └──> Stale publication date (>180 days)         ──> Freshness SLA: Ty le >25% bi bao dong (STALE)
  │
  ▼
[Hien Tuong Silent Failure tren RAG Agent]
  - Retrieval Hit Rate sut giam: Vector Embeddings bi lech huong do title bi cat ngan va noi dung bi mat.
  - Token F1 suy thoai nang ne: Tra ve thong tin sai lech hoac fallback cau tra loi mac dinh do khong tim thay context.
  - LLM Judge Accuracy & Score giam manh: Chat luong phan hoi xuong cap nghiem trong.
```

### 4.2. Chuoi Phuc Hoi (Idempotent Repair tu Raw Snapshot)
```text
[Kich Hoat Idempotent Repair tu data/raw/crossref_records.json]
  │
  ├──> Load lai snapshot nguyen ban (Data Lineage bao toan tuyet doi)
  ├──> Tai chay pipeline lam sach: normalize, parse dates, tao text_for_embedding
  └──> Xoa collection ChromaDB loi, tai tao collection vector papers-repaired
  │
  ▼
[Phuc Hoi Hoan Toan (Recovery)]
  - Quality Gate (GX 1.x): 100% Expectations chuyen trang thai PASS.
  - Freshness SLA: Ty le qua han tro ve <=25%, trang thai FRESH tro lai.
  - RAG Agent Performance: Retrieval Hit Rate va Token F1 phuc hoi ve muc tuong duong Baseline ban dau.
```

---

## 5. Ket Luan & Khuyen Nghi Kien Truc (Architecture Takeaways)

1. **Tam quan trong cua Data Observability**: Neu khong co Data Quality Gate va Freshness SLA o tang Data Pipeline, he thong RAG van chay binh thuong ma khong bao loi runtime (Silent Failure), gay nguy hai lon den do tin cay cua ung dung nghiep vu.
2. **Kien truc Idempotent Repair**: Viec luu tru bat bien snapshot du lieu goc (`data/raw/`) la chot chan song con, cho phep he thong tu phuc hoi trang thai sach bat cu luc nao ma khong gay drift du lieu.
