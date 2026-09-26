from __future__ import annotations

import json
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd

NOISE_TOKEN = "###@@@GARBAGE_DATA_XXXX@@@###"
CORRUPTION_SEED = 42


def _format_field(value) -> str:
    """Chuyen list (authors, categories) hoac gia tri khac thanh string de ghep text."""
    if isinstance(value, (list, tuple)):
        return ", ".join(str(v) for v in value)
    return "" if pd.isna(value) else str(value)


def _build_text_for_embedding(row: pd.Series) -> str:
    """Rebuild text_for_embedding theo dung format cua Buoc 3, dung du lieu (da bi corrupt) hien tai."""
    return (
        f"Title: {_format_field(row.get('title'))}\n"
        f"Authors: {_format_field(row.get('authors'))}\n"
        f"Published: {_format_field(row.get('published'))}\n"
        f"Categories: {_format_field(row.get('categories'))}\n"
        f"Summary: {_format_field(row.get('summary'))}"
    )


def _make_stale_date(date_str: str, days_back: int = 365) -> str:
    """Lui ngay xuat ban ve `days_back` ngay truoc, giu nguyen dinh dang ISO YYYY-MM-DD."""
    try:
        d = datetime.fromisoformat(str(date_str))
    except (ValueError, TypeError):
        d = datetime.now(UTC)
    return (d - timedelta(days=days_back)).date().isoformat()


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Simulate 6 dang data corruption thuc te tren clean_df va ghi log chi tiet.

    1. Drop 20% ban ghi moi nhat.
    2. Blank summary o mot so dong.
    3. Inject noise (chuoi ky tu rac) vao summary.
    4. Truncate title xuong duoi 8 ky tu.
    5. Lui published date ve 365 ngay truoc.
    6. Nhan doi mot so dong de tao trung lap.
    7. Rebuild text_for_embedding sau khi corrupt.
    8. Ghi log toan bo cac dong bi bien doi vao output_log_path.
    """
    rng = random.Random(CORRUPTION_SEED)
    working_df = df.copy().reset_index(drop=True)
    log: dict[str, list[str]] = {}
    n = len(working_df)

    if n == 0:
        raise ValueError("Input dataframe is empty, cannot corrupt.")

    # 1. Drop latest records: bo roi 20% cac bai bao moi nhat (theo published)
    sorted_by_date = working_df.sort_values("published", ascending=False)
    n_drop = max(1, int(n * 0.20))
    dropped_ids = sorted_by_date.iloc[:n_drop]["paper_id"].tolist()
    working_df = working_df[~working_df["paper_id"].isin(dropped_ids)].reset_index(drop=True)
    log["drop_latest_records"] = dropped_ids

    remaining_ids = working_df["paper_id"].tolist()

    # 2. Blank summary o mot so dong
    n_blank = max(1, int(len(working_df) * 0.15))
    blank_ids = rng.sample(remaining_ids, min(n_blank, len(remaining_ids)))
    mask_blank = working_df["paper_id"].isin(blank_ids)
    working_df.loc[mask_blank, "summary"] = ""
    log["blank_summary"] = blank_ids

    # 3. Inject noise vao summary cua mot so dong khac
    remaining_for_noise = [pid for pid in remaining_ids if pid not in blank_ids]
    n_noise = max(1, int(len(working_df) * 0.15))
    noise_ids = rng.sample(remaining_for_noise, min(n_noise, len(remaining_for_noise)))
    mask_noise = working_df["paper_id"].isin(noise_ids)
    working_df.loc[mask_noise, "summary"] = (
        working_df.loc[mask_noise, "summary"].astype(str) + " " + NOISE_TOKEN
    )
    log["inject_noise"] = noise_ids

    # 4. Truncate title xuong duoi 8 ky tu
    n_truncate = max(1, int(len(working_df) * 0.15))
    truncate_ids = rng.sample(remaining_ids, min(n_truncate, len(remaining_ids)))
    mask_truncate = working_df["paper_id"].isin(truncate_ids)
    working_df.loc[mask_truncate, "title"] = (
        working_df.loc[mask_truncate, "title"].astype(str).str.slice(0, 7)
    )
    log["truncate_title"] = truncate_ids

    # 5. Lui published date ve 365 ngay truoc
    n_stale = max(1, int(len(working_df) * 0.15))
    stale_ids = rng.sample(remaining_ids, min(n_stale, len(remaining_ids)))
    mask_stale = working_df["paper_id"].isin(stale_ids)
    working_df.loc[mask_stale, "published"] = working_df.loc[mask_stale, "published"].apply(
        _make_stale_date
    )
    log["stale_date"] = stale_ids

    # Cap nhat lai age_days neu co cot nay (de nhat quan sau khi doi published)
    if "age_days" in working_df.columns:
        run_date = datetime.now(UTC).date()
        working_df["age_days"] = working_df["published"].apply(
            lambda p: (run_date - datetime.fromisoformat(str(p)).date()).days if p else None
        )

    # 6. Nhan doi mot so dong de tao trung lap
    n_dup = max(1, int(len(working_df) * 0.10))
    dup_ids = rng.sample(remaining_ids, min(n_dup, len(remaining_ids)))
    dup_rows = working_df[working_df["paper_id"].isin(dup_ids)]
    working_df = pd.concat([working_df, dup_rows], ignore_index=True)
    log["duplicate_rows"] = dup_ids

    # 7. Rebuild text_for_embedding sau khi corrupt
    if "text_for_embedding" in working_df.columns:
        working_df["text_for_embedding"] = working_df.apply(_build_text_for_embedding, axis=1)

    # 8. Ghi corruption log
    output_log_path = Path(output_log_path)
    output_log_path.parent.mkdir(parents=True, exist_ok=True)
    log_with_meta = {
        "original_row_count": n,
        "final_row_count": len(working_df),
        "corruptions": log,
    }
    output_log_path.write_text(
        json.dumps(log_with_meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    return working_df