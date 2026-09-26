import re
from dataclasses import asdict, is_dataclass
from datetime import date, datetime, timezone

import pandas as pd

from ingestion.crossref import PaperRecord


def _normalize_whitespace(text: str | None) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", str(text)).strip()


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records thanh dataframe san sang de embed.

    1. Normalize title, summary, authors, categories.
    2. Parse published/updated date.
    3. Tinh age_days = (run_date - published).days.
    4. Tao cot helper:
       - authors_joined
       - categories_joined
       - summary_chars
       - text_for_embedding (chuan 5 phan: Title, Authors, Published, Categories, Summary)
    5. Drop duplicates theo paper_id va filter row xau.
    6. Sort dataframe va return.
    """
    if not records:
        return pd.DataFrame()

    ref_date: date = run_date.date() if isinstance(run_date, (datetime, pd.Timestamp)) else run_date

    cleaned_rows: list[dict] = []
    for rec in records:
        rec_dict = asdict(rec) if is_dataclass(rec) else dict(rec)

        paper_id = str(rec_dict.get("paper_id") or "").strip()
        title = _normalize_whitespace(rec_dict.get("title"))
        summary = _normalize_whitespace(rec_dict.get("summary"))

        # Loc row xau: bat buoc co paper_id, title va summary
        if not paper_id or not title or not summary:
            continue

        raw_authors = rec_dict.get("authors") or []
        if isinstance(raw_authors, list):
            authors = [_normalize_whitespace(a) for a in raw_authors if _normalize_whitespace(a)]
        else:
            authors = [_normalize_whitespace(str(raw_authors))]
        authors_joined = ", ".join(authors)

        raw_categories = rec_dict.get("categories") or []
        if isinstance(raw_categories, list):
            categories = [_normalize_whitespace(c) for c in raw_categories if _normalize_whitespace(c)]
        else:
            categories = [_normalize_whitespace(str(raw_categories))]
        categories_joined = ", ".join(categories)

        primary_category = str(rec_dict.get("primary_category") or (categories[0] if categories else "")).strip()
        published = str(rec_dict.get("published") or "").strip()
        updated = str(rec_dict.get("updated") or "").strip()
        abs_url = str(rec_dict.get("abs_url") or "").strip()
        pdf_url = str(rec_dict.get("pdf_url") or "").strip()
        comment = str(rec_dict.get("comment") or "").strip()

        # Tinh toan tuoi doi du lieu: age_days = (run_date - published).days
        age_days = 0
        if published:
            try:
                pub_dt = pd.to_datetime(published, errors="coerce")
                if pd.notna(pub_dt):
                    pub_date_val = pub_dt.date()
                    age_days = max(0, (ref_date - pub_date_val).days)
            except Exception:
                age_days = 0

        summary_chars = len(summary)

        # Ghep noi cac truong thanh mot doan ngu canh hoan chinh text_for_embedding
        text_for_embedding = (
            f"Title: {title}\n"
            f"Authors: {authors_joined}\n"
            f"Published: {published}\n"
            f"Categories: {categories_joined}\n"
            f"Summary: {summary}"
        )

        cleaned_rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "categories": categories,
                "primary_category": primary_category,
                "published": published,
                "updated": updated,
                "abs_url": abs_url,
                "pdf_url": pdf_url,
                "comment": comment,
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "summary_chars": summary_chars,
                "age_days": age_days,
                "text_for_embedding": text_for_embedding,
            }
        )

    df = pd.DataFrame(cleaned_rows)
    if df.empty:
        return df

    # Khu trung lap ban ghi theo khoa duy nhat paper_id
    df = df.drop_duplicates(subset=["paper_id"], keep="first")
    df = df.reset_index(drop=True)
    return df

