import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import great_expectations as gx
import great_expectations.expectations as gxe
import pandas as pd

from core.config import Settings


def evaluate_freshness_sla(df: pd.DataFrame, settings: Settings) -> dict[str, Any]:
    """Danh gia Freshness SLA theo nguong tuoi doi du lieu.
    Canh bao is_fresh = False neu ty le bai bao co age_days > 180 vuot qua 25%.
    """
    threshold = getattr(settings, "freshness_threshold_days", 180)
    total_rows = len(df)
    if total_rows == 0:
        return {
            "threshold_days": threshold,
            "total_rows": 0,
            "stale_rows": 0,
            "stale_ratio": 0.0,
            "is_fresh": True,
            "latest_published": "",
            "oldest_published": "",
        }

    if "age_days" in df.columns:
        age_series = pd.to_numeric(df["age_days"], errors="coerce").fillna(0)
    elif "published" in df.columns:
        today = datetime.now(timezone.utc).date()
        pub_dates = pd.to_datetime(df["published"], errors="coerce").dt.date
        age_series = pub_dates.apply(lambda d: max(0, (today - d).days) if pd.notna(d) else 0)
    else:
        age_series = pd.Series([0] * total_rows)

    stale_rows = int((age_series > threshold).sum())
    stale_ratio = float(stale_rows / total_rows)
    is_fresh = bool(stale_ratio <= 0.25)

    published_series = df["published"].dropna().astype(str) if "published" in df.columns else pd.Series([], dtype=str)
    valid_dates = [d for d in published_series if d.strip()]
    latest_published = max(valid_dates) if valid_dates else ""
    oldest_published = min(valid_dates) if valid_dates else ""

    return {
        "threshold_days": threshold,
        "total_rows": total_rows,
        "stale_rows": stale_rows,
        "stale_ratio": round(stale_ratio, 4),
        "is_fresh": is_fresh,
        "latest_published": latest_published,
        "oldest_published": oldest_published,
    }


def build_freshness_report(
    df: pd.DataFrame, settings: Settings, report_path: Path | str | None = None
) -> dict[str, Any]:
    """Tong hop freshness report va ghi ra file JSON."""
    freshness_data = evaluate_freshness_sla(df, settings)
    target_path = Path(report_path) if report_path else settings.paths.freshness_report
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(json.dumps(freshness_data, ensure_ascii=False, indent=2), encoding="utf-8")
    return freshness_data


def run_data_quality_checks(
    df: pd.DataFrame, settings: Settings, stage: str = "baseline"
) -> dict[str, Any]:
    """Chay Data Quality Gate bang Great Expectations 1.x Ephemeral Context.

    4 Expectations bat buoc:
    1. ExpectTableRowCountToBeBetween: 5 den 5000 dong.
    2. ExpectColumnValuesToNotBeNull: paper_id, title, text_for_embedding khong duoc null.
    3. ExpectColumnValuesToBeUnique: paper_id la duy nhat.
    4. ExpectColumnValueLengthsToBeBetween: summary co do dai toi thieu 30 ky tu.

    Ket hop evaluate_freshness_sla kiem tra do tuoi moi (age_days > 180 khong vuot 25%).
    """
    # 1. Ephemeral Context tren GX 1.x
    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas(name=f"papers_source_{stage}")
    data_asset = data_source.add_dataframe_asset(name=f"papers_asset_{stage}")
    batch_def = data_asset.add_batch_definition_whole_dataframe(f"papers_batch_{stage}")
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})

    # 2. Thiet lap 4 Expectations bat buoc
    suite = gx.ExpectationSuite(name=f"papers_quality_{stage}")

    # Hang rao 1: So luong ban ghi nam trong nguong 5 den 5000 dong
    suite.add_expectation(gxe.ExpectTableRowCountToBeBetween(min_value=5, max_value=5000))

    # Hang rao 2: Cac cot quan trong paper_id, title, text_for_embedding khong duoc rong (null)
    suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column="paper_id"))
    suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column="title"))
    suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column="text_for_embedding"))

    # Hang rao 3: Moi bai bao paper_id la duy nhat, khong trung lap
    suite.add_expectation(gxe.ExpectColumnValuesToBeUnique(column="paper_id"))

    # Hang rao 4: Truong summary co do dai toi thieu 30 ky tu
    suite.add_expectation(gxe.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30))

    # 3. Kiem dinh voi batch
    val_res = batch.validate(suite)
    gx_success = bool(val_res.success)

    # 4. Giam sat do tuoi moi (Freshness Monitoring)
    freshness_res = evaluate_freshness_sla(df, settings)
    is_fresh = freshness_res["is_fresh"]

    # 5. Tong hop ket qua (chi pass khi ca GX checks va Freshness SLA deu pass)
    overall_success = bool(gx_success and is_fresh)

    expectations_summary = []
    for r in getattr(val_res, "results", []):
        expectations_summary.append(
            {
                "expectation_type": r.expectation_config.type,
                "success": bool(r.success),
                "kwargs": r.expectation_config.kwargs,
            }
        )

    report_payload = {
        "stage": stage,
        "success": overall_success,
        "gx_success": gx_success,
        "is_fresh": is_fresh,
        "total_rows": len(df),
        "freshness": freshness_res,
        "expectations": expectations_summary,
    }

    # 6. Ghi bao cao vao data/quality/
    if stage in ("baseline", "phase1"):
        report_file = settings.paths.baseline_quality_report
    elif stage in ("corrupted", "corruption"):
        report_file = settings.paths.corrupted_quality_report
    else:
        report_file = settings.paths.quality_dir / f"{stage}_quality_report.json"

    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(json.dumps(report_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # Luu them freshness_report
    build_freshness_report(df, settings, settings.paths.freshness_report)

    return report_payload

