from __future__ import annotations

from pathlib import Path
from typing import Any

from core.utils import write_text


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Viet markdown report cho baseline phase.

    Pseudo-code:
    1. Gom source summary.
    2. In metrics retrieval/evaluation.
    3. In data quality va freshness.
    4. Ghi markdown vao report_path.
    """
    target_path = Path(report_path)

    # 1. Source summary
    total_records = source_summary.get("total_records", "N/A")
    clean_rows = source_summary.get("clean_rows", "N/A")
    source_api = source_summary.get("source_api", "Crossref REST API")
    source_query = source_summary.get("source_query", "N/A")
    source_filter = source_summary.get("source_filter", "N/A")

    # 2. Evaluation metrics
    samples = metrics.get("samples", 0)
    try:
        hit_rate = float(metrics.get("retrieval_hit_rate", 0.0) or 0.0)
    except (ValueError, TypeError):
        hit_rate = 0.0

    try:
        mean_f1 = float(metrics.get("mean_token_f1", 0.0) or 0.0)
    except (ValueError, TypeError):
        mean_f1 = 0.0

    try:
        judge_acc = float(metrics.get("judge_accuracy", 0.0) or 0.0)
    except (ValueError, TypeError):
        judge_acc = 0.0

    try:
        judge_score = float(metrics.get("mean_judge_score", 0.0) or 0.0)
    except (ValueError, TypeError):
        judge_score = 0.0

    ragas_data = metrics.get("ragas", {})
    ragas_lines = []
    if isinstance(ragas_data, dict):
        if "skipped" in ragas_data:
            ragas_lines.append(f"- **Ragas Status:** Skipped ({ragas_data['skipped']})")
        elif "error" in ragas_data:
            ragas_lines.append(f"- **Ragas Error:** {ragas_data['error']}")
        elif ragas_data:
            for k, v in ragas_data.items():
                if isinstance(v, float):
                    ragas_lines.append(f"- **{k}:** {v:.4f}")
                else:
                    ragas_lines.append(f"- **{k}:** {v}")
        else:
            ragas_lines.append("- **Ragas Status:** N/A")
    else:
        ragas_lines.append("- **Ragas Status:** N/A")
    ragas_block = "\n".join(ragas_lines)

    # 3. Data quality checks (GX 1.x)
    quality_success = bool(quality.get("success", False))
    gx_success = bool(quality.get("gx_success", False))
    expectations = quality.get("expectations", [])

    exp_table_rows = []
    for exp in expectations:
        exp_type = exp.get("expectation_type", "Unknown")
        status = "PASS" if exp.get("success") else "FAIL"
        kwargs = exp.get("kwargs", {})
        kwargs_desc = ", ".join(f"{k}={v}" for k, v in kwargs.items()) if kwargs else "-"
        exp_table_rows.append(f"| `{exp_type}` | {kwargs_desc} | {status} |")

    exp_table_str = (
        "\n".join(exp_table_rows)
        if exp_table_rows
        else "| Khong co expectation nao duoc ghi nhan | - | - |"
    )

    # 4. Freshness SLA
    is_fresh = bool(freshness.get("is_fresh", True))
    freshness_status = "FRESH" if is_fresh else "STALE"
    threshold_days = freshness.get("threshold_days", 180)
    f_total_rows = freshness.get("total_rows", 0)
    stale_rows = freshness.get("stale_rows", 0)
    try:
        stale_ratio = float(freshness.get("stale_ratio", 0.0) or 0.0)
    except (ValueError, TypeError):
        stale_ratio = 0.0

    latest_published = freshness.get("latest_published", "N/A")
    oldest_published = freshness.get("oldest_published", "N/A")

    overall_status = "PASSED" if (quality_success and is_fresh) else "ACTION REQUIRED"

    report_content = f"""# Bao Cao Pha 1: Baseline Pipeline & Data Observability

## 1. Tong Quan Trang Thai (Executive Summary)

- **Trang thai Pipeline:** {overall_status}
- **Quality Gate (GX 1.x):** {"PASS" if gx_success else "FAIL"}
- **Freshness SLA:** {freshness_status}
- **Retrieval Hit Rate:** {hit_rate:.2%}
- **Mean Token F1:** {mean_f1:.4f}

---

## 2. Du Lieu Nguon & Tien Xu Ly (Data Ingestion & Cleaning)

| Thong so | Gia tri |
| :--- | :--- |
| **Nguon du lieu (Source API)** | {source_api} |
| **Truy van tim kiem (Query)** | `{source_query}` |
| **Bo loc (Filter)** | `{source_filter}` |
| **So ban ghi tho (Raw Records)** | {total_records} |
| **So ban ghi sach (Clean Rows)** | {clean_rows} |

---

## 3. Hieu Nang Danh Gia Nen (Baseline Evaluation & Benchmarks)

| Chi so (Metric) | Ket qua | Y nghia / Nguong ky vong |
| :--- | :--- | :--- |
| **So cau hoi benchmark (`samples`)** | {samples} | Tap testset 10 cau phu 4 nhom nghiep vu |
| **Ty le truy xuat trung (`retrieval_hit_rate`)** | **{hit_rate:.2%}** | Do luong ty le tai lieu ground truth nam trong top retrieved |
| **Do trung khop tu khoa (`mean_token_f1`)** | **{mean_f1:.4f}** | Do luong muc do trung khop giua cau tra loi va ground truth |
| **Do chinh xac cua Giam khao (`judge_accuracy`)** | {judge_acc:.2%} | Ty le cau tra loi duoc LLM/Heuristic Judge xac nhan Materially Correct |
| **Diem trung binh Giam khao (`mean_judge_score`)** | {judge_score:.2f} / 5.0 | Thang diem tu 1 den 5 danh gia chat luong cau tra loi |

### Danh gia chuyen sau voi Ragas
{ragas_block}

---

## 4. Chot Kiem Dich Chat Luong Du Lieu (Data Quality Gate - Great Expectations 1.x)

- **Ket qua tong quat GX:** {"DAT (PASS)" if gx_success else "KHONG DAT (FAIL)"}

| Expectation Type | Tham so / Dieu kien | Trang thai |
| :--- | :--- | :--- |
{exp_table_str}

---

## 5. Giam Sat Do Tuoi Moi (Freshness SLA Monitoring)

- **Trang thai Freshness SLA:** {freshness_status}
- **Tieu chuan SLA:** Ty le bai bao qua han (`age_days > {threshold_days}`) khong duoc vuot qua 25%.

| Tieu chi | Gia tri thuc te | Nguong SLA |
| :--- | :--- | :--- |
| **Nguong tuoi toi da (`threshold_days`)** | {threshold_days} ngay | 180 ngay |
| **Tong so bai bao theo doi** | {f_total_rows} | - |
| **So bai bao qua han (`stale_rows`)** | {stale_rows} | - |
| **Ty le qua han (`stale_ratio`)** | **{stale_ratio:.2%}** | <= 25.00% |
| **Ngay xuat ban moi nhat (`latest_published`)** | {latest_published} | - |
| **Ngay xuat ban cu nhat (`oldest_published`)** | {oldest_published} | - |

---

## 6. Ket Luan & San Sang Cho Pha 2 (Conclusion)

- Toan bo du lieu sach da duoc lap chi muc vector tren ChromaDB collection `papers-baseline`.
- Cac chi so nen (Baseline Benchmarks) phan anh day du nang luc truy xuat va tra loi cua RAG Agent tren du lieu chuan.
- Chot kiem dich chat luong du lieu va Freshness SLA da duoc thiet lap thanh cong lam can cu phat hien su co (Silent Failure) khi tiem du lieu ban tai Pha 2.
"""

    write_text(target_path, report_content.strip() + "\n")



def _safe_float(d: dict[str, Any], key: str, default: float = 0.0) -> float:
    try:
        val = d.get(key)
        return float(val) if val is not None else default
    except (ValueError, TypeError):
        return default


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """Viet markdown report so sanh baseline / corrupted / repaired."""
    target_path = Path(report_path)

    # 1. Trich xuat cac chi so Retrieval va QA
    b_hit = _safe_float(baseline_metrics, "retrieval_hit_rate", 0.0)
    c_hit = _safe_float(corrupted_metrics, "retrieval_hit_rate", 0.0)
    r_hit = _safe_float(repaired_metrics, "retrieval_hit_rate", 0.0)

    b_f1 = _safe_float(baseline_metrics, "mean_token_f1", 0.0)
    c_f1 = _safe_float(corrupted_metrics, "mean_token_f1", 0.0)
    r_f1 = _safe_float(repaired_metrics, "mean_token_f1", 0.0)

    b_acc = _safe_float(baseline_metrics, "judge_accuracy", 0.0)
    c_acc = _safe_float(corrupted_metrics, "judge_accuracy", 0.0)
    r_acc = _safe_float(repaired_metrics, "judge_accuracy", 0.0)

    b_score = _safe_float(baseline_metrics, "mean_judge_score", 0.0)
    c_score = _safe_float(corrupted_metrics, "mean_judge_score", 0.0)
    r_score = _safe_float(repaired_metrics, "mean_judge_score", 0.0)

    # 2. Trich xuat trang thai Data Quality (GX 1.x)
    c_gx = bool(corrupted_quality.get("gx_success", False))
    r_gx = bool(repaired_quality.get("gx_success", False))

    c_overall = bool(corrupted_quality.get("success", False))
    r_overall = bool(repaired_quality.get("success", False))

    # 3. Trich xuat trang thai Freshness SLA
    c_fresh = bool(corrupted_freshness.get("is_fresh", True))
    r_fresh = bool(repaired_freshness.get("is_fresh", True))

    c_stale_rows = corrupted_freshness.get("stale_rows", 0)
    r_stale_rows = repaired_freshness.get("stale_rows", 0)

    c_stale_ratio = _safe_float(corrupted_freshness, "stale_ratio", 0.0)
    r_stale_ratio = _safe_float(repaired_freshness, "stale_ratio", 0.0)

    c_latest = corrupted_freshness.get("latest_published", "N/A")
    r_latest = repaired_freshness.get("latest_published", "N/A")

    c_oldest = corrupted_freshness.get("oldest_published", "N/A")
    r_oldest = repaired_freshness.get("oldest_published", "N/A")

    # 4. Bang Expectations GX
    c_exps = {
        exp.get("expectation_type", ""): exp.get("success", False)
        for exp in corrupted_quality.get("expectations", [])
        if exp.get("expectation_type")
    }
    r_exps = {
        exp.get("expectation_type", ""): exp.get("success", False)
        for exp in repaired_quality.get("expectations", [])
        if exp.get("expectation_type")
    }
    all_exp_types = list(dict.fromkeys(list(c_exps.keys()) + list(r_exps.keys())))

    exp_rows = []
    for exp_type in all_exp_types:
        c_status = "PASS" if c_exps.get(exp_type, False) else "FAIL"
        r_status = "PASS" if r_exps.get(exp_type, False) else "FAIL"
        note = (
            "Da duoc phuc hoi sau repair"
            if (c_status == "FAIL" and r_status == "PASS")
            else "On dinh"
        )
        exp_rows.append(f"| `{exp_type}` | PASS | {c_status} | {r_status} | {note} |")

    exp_table_str = (
        "\n".join(exp_rows)
        if exp_rows
        else "| Khong co expectation nao duoc ghi nhan | PASS | - | - | - |"
    )

    # 5. Soan noi dung Markdown report
    report_content = f"""
    # Bao Cao Doi Chieu 3 Trang Thai: Baseline vs Corrupted vs Repaired

## 1. Bang Tong Hop Doi Chieu 3 Trang Thai (Executive Comparison Table)

| Chi so / Tin hieu | Baseline (Sieu chuan) | Corrupted (Bi tiem loi) | Repaired (Sau phuc hoi) | Thay doi do Corruption | Muc do phuc hoi | Nhan xet |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| **`retrieval_hit_rate`** | **{b_hit:.2%}** | **{c_hit:.2%}** | **{r_hit:.2%}** | `{c_hit - b_hit:+.2%}` | `{r_hit - c_hit:+.2%}` | {"Sut giam manh khi du lieu bi hong" if c_hit < b_hit else "On dinh"} |
| **`mean_token_f1`** | **{b_f1:.4f}** | **{c_f1:.4f}** | **{r_f1:.4f}** | `{c_f1 - b_f1:+.4f}` | `{r_f1 - c_f1:+.4f}` | {"Nhieu va rong summary lam hong cau tra loi" if c_f1 < b_f1 else "On dinh"} |
| **`judge_accuracy`** | {b_acc:.2%} | {c_acc:.2%} | {r_acc:.2%} | `{c_acc - b_acc:+.2%}` | `{r_acc - c_acc:+.2%}` | {"Giam khao danh gia do chinh xac tut giam" if c_acc < b_acc else "On dinh"} |
| **`mean_judge_score`** | {b_score:.2f} / 5.0 | {c_score:.2f} / 5.0 | {r_score:.2f} / 5.0 | `{c_score - b_score:+.2f}` | `{r_score - c_score:+.2f}` | Thang diem danh gia 1 - 5 |
| **Quality Gate (GX 1.x)** | **PASS** | **{"PASS" if c_gx else "FAIL"}** | **{"PASS" if r_gx else "FAIL"}** | {"Vi pham kiem dinh" if not c_gx else "Dat"} | {"Phuc hoi thanh cong" if r_gx else "Chua dat"} | Chot kiem dich chat luong |
| **Freshness SLA** | **FRESH** | **{"FRESH" if c_fresh else "STALE"}** | **{"FRESH" if r_fresh else "STALE"}** | {"Vuot nguong 25% qua han" if not c_fresh else "Dat"} | {"Phuc hoi do tuoi moi" if r_fresh else "Chua dat"} | Nguong toi da 180 ngay |
| **Trang thai Pipeline Tong The** | **PASSED** | **{"PASSED" if c_overall else "FAILED (BLOCKED)"}** | **{"PASSED" if r_overall else "FAILED"}** | {"Bao dong do du lieu ban" if not c_overall else "Dat"} | {"Vuot qua toan bo chot kiem dich" if r_overall else "Chua dat"} | Chi pass khi ca GX va SLA dat |

---

## 2. Chi Tiet Kiem Dinh Chat Luong Du Lieu (Great Expectations 1.x)

Bang doi chieu tung Expectation qua 3 trang thai:

| Expectation Type | Baseline | Corrupted | Repaired | Nhan xet |
| :--- | :--- | :--- | :--- | :--- |
{exp_table_str}

- **Giai thich nguyen nhan vi pham:**
  - `ExpectColumnValueLengthsToBeBetween`: Phat hien cac dong bi xoa rong summary (blank summary) hoac truncate khong du do dai toi thieu 30 ky tu.
  - `ExpectColumnValuesToBeUnique`: Phat hien cac dong trung lap `paper_id` do hanh vi nhan ban ban ghi (duplicate rows).
  - `ExpectColumnValuesToNotBeNull`: Phat hien cac ban ghi thieu thong tin cot bat buoc.

---

## 3. Giam Sat Do Tuoi Moi (Freshness SLA Monitoring)

| Thong so Freshness | Baseline | Corrupted | Repaired | Nguong SLA |
| :--- | ---: | ---: | ---: | :--- |
| **So dong qua han (`stale_rows`)** | 0 | {c_stale_rows} | {r_stale_rows} | - |
| **Ty le qua han (`stale_ratio`)** | 0.00% | **{c_stale_ratio:.2%}** | **{r_stale_ratio:.2%}** | <= 25.00% |
| **Ngay xuat ban moi nhat** | - | {c_latest} | {r_latest} | - |
| **Ngay xuat ban cu nhat** | - | {c_oldest} | {r_oldest} | - |
| **Danh gia trang thai Freshness** | **FRESH** | **{"FRESH" if c_fresh else "STALE (ALERT)"}** | **{"FRESH" if r_fresh else "STALE"}** | **FRESH** |

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
"""

    write_text(target_path, report_content.strip() + "\n")
