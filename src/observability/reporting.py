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
    """TODO(student): viet markdown report so sanh baseline/corrupted/repaired."""
    raise NotImplementedError("Student task: implement corruption comparison report.")
