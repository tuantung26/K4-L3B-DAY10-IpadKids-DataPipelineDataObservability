from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import requests

from core.config import Settings

CROSSREF_BASE_URL = "https://api.crossref.org/works"
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2.0


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def _clean_abstract_text(raw_abstract: str) -> str:
    """Loai bo cac the JATS/XML rac nhu <jats:p>, <jats:title>, ... khoi abstract."""
    if not raw_abstract:
        return ""
    text = re.sub(r"<[^>]+>", " ", raw_abstract)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _date_parts_to_str(date_field: dict | None) -> str:
    """Chuyen doi truong 'published'/'published-print'/'published-online' cua Crossref
    (dang {"date-parts": [[year, month, day]]}) thanh chuoi ISO 'YYYY-MM-DD'."""
    if not date_field:
        return ""
    parts_list = date_field.get("date-parts")
    if not parts_list or not parts_list[0]:
        return ""
    parts = parts_list[0]
    year = parts[0] if len(parts) > 0 else 1
    month = parts[1] if len(parts) > 1 else 1
    day = parts[2] if len(parts) > 2 else 1
    return f"{year:04d}-{month:02d}-{day:02d}"


def _extract_pdf_url(item: dict) -> str:
    for link in item.get("link", []) or []:
        content_type = (link.get("content-type") or "").lower()
        if "pdf" in content_type:
            return link.get("URL", "")
    return ""


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref payload thanh list PaperRecord."""
    items = payload.get("message", {}).get("items", [])
    records: list[PaperRecord] = []

    for item in items:
        doi = item.get("DOI")
        title_list = item.get("title") or []
        title = title_list[0].strip() if title_list else ""
        summary = _clean_abstract_text(item.get("abstract", ""))

        # Bo qua record khong hop le: thieu DOI, title hoac abstract
        if not doi or not title or not summary:
            continue

        authors = [
            f"{a.get('given', '')} {a.get('family', '')}".strip()
            for a in item.get("author", []) or []
            if a.get("given") or a.get("family")
        ]

        categories = item.get("subject", []) or []
        primary_category = categories[0] if categories else ""

        published_field = (
            item.get("published")
            or item.get("published-print")
            or item.get("published-online")
            or item.get("created")
        )
        published = _date_parts_to_str(published_field)

        updated_field = item.get("deposited") or item.get("indexed")
        updated = updated_field.get("date-time", "") if updated_field else ""

        abs_url = item.get("URL", "")
        pdf_url = _extract_pdf_url(item)
        comment = (item.get("container-title") or [""])[0]

        records.append(
            PaperRecord(
                paper_id=doi,
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=primary_category,
                published=published,
                updated=updated,
                abs_url=abs_url,
                pdf_url=pdf_url,
                comment=comment,
            )
        )

    return records


def _fetch_from_api(settings: Settings) -> dict:
    """Goi Crossref API voi retry cho cac status code loi tam thoi (429/5xx)."""
    params = {
        "query.bibliographic": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }
    headers = {"User-Agent": "K4-L3B-DAY10-Lab (mailto:student@example.com)"}

    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(CROSSREF_BASE_URL, params=params, headers=headers, timeout=15)
            if response.status_code in RETRYABLE_STATUS_CODES:
                raise requests.HTTPError(f"Retryable status code: {response.status_code}")
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)

    raise RuntimeError(f"Failed to fetch from Crossref API after {MAX_RETRIES} attempts: {last_error}")


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Goi source API, luu raw response, parse thanh records.

    Neu API loi (mang chap chon, 429, timeout, ...), tu dong fallback doc
    snapshot co san tai settings.paths.raw_api_response de khong lam gian doan bai lab.
    """
    raw_response_path = settings.paths.raw_api_response
    raw_records_path = settings.paths.raw_records_json

    payload: dict
    try:
        payload = _fetch_from_api(settings)
        raw_response_path.parent.mkdir(parents=True, exist_ok=True)
        raw_response_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        if raw_response_path.exists():
            payload = json.loads(raw_response_path.read_text(encoding="utf-8"))
        else:
            raise RuntimeError(
                "Crossref API call failed and no offline snapshot found at "
                f"{raw_response_path}. Cannot proceed."
            )

    records = parse_crossref_payload(payload)

    raw_records_path.parent.mkdir(parents=True, exist_ok=True)
    raw_records_path.write_text(
        json.dumps([asdict(r) for r in records], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Tín hiệu hoàn thành: Đã tải {len(records)} bài báo")
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Doc JSON snapshot va map thanh PaperRecord."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return [PaperRecord(**item) for item in data]