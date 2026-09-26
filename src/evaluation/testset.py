from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import compact_join, first_sentence, normalize_whitespace, write_json


def _extract_field(row: dict[str, Any], joined_col: str, list_col: str) -> str:
    """Extract a joined string representation from a joined column or list column."""
    val = row.get(joined_col)
    if val is not None and not (isinstance(val, float) and pd.isna(val)):
        s = str(val).strip()
        if s.lower() != "nan":
            return s
    raw_list = row.get(list_col)
    if isinstance(raw_list, (list, tuple)):
        return compact_join(str(x).strip() for x in raw_list if str(x).strip())
    return ""


def _extract_summary(row: dict[str, Any]) -> str:
    val = row.get("summary", "")
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    return normalize_whitespace(str(val))


def _extract_published(row: dict[str, Any]) -> str:
    val = row.get("published", "")
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    s = str(val).strip()
    return "" if s.lower() == "nan" else s


def _extract_authors(row: dict[str, Any]) -> str:
    return _extract_field(row, "authors_joined", "authors")


def _extract_categories(row: dict[str, Any]) -> str:
    val = _extract_field(row, "categories_joined", "categories")
    if val:
        return val
    primary = row.get("primary_category")
    if primary is not None and not (isinstance(primary, float) and pd.isna(primary)):
        s = str(primary).strip()
        if s and s.lower() != "nan":
            return s
    return ""


def build_test_set(
    df: pd.DataFrame,
    output_path: Path | str | None = None,
    num_questions: int = 10,
) -> list[dict[str, Any]]:
    """Build evaluation test set from cleaned dataframe.

    Pseudo-code:
    1. Kiem tra so luong document toi thieu.
    2. Chon mot so paper dai dien.
    3. Tao nhieu loai cau hoi:
       - summary
       - authors
       - date
       - categories
    4. Moi row can co:
       - id
       - question_type
       - question
       - ground_truth
       - ground_truth_doc_ids
    5. Ghi file JSON vao output_path.
    """
    # 1. Kiem tra so luong document toi thieu
    if df is None or len(df) == 0:
        raise ValueError("Input dataframe is empty or None. Cannot build test set.")

    min_required_docs = 4
    if len(df) < min_required_docs:
        raise ValueError(
            f"Input dataframe must have at least {min_required_docs} documents, got {len(df)}."
        )

    # 2. Chon mot so paper dai dien
    records = df.to_dict(orient="records")
    valid_records = [
        r
        for r in records
        if str(r.get("paper_id", "")).strip() and str(r.get("title", "")).strip()
    ]
    if len(valid_records) < min_required_docs:
        raise ValueError(
            f"Found only {len(valid_records)} valid records with paper_id and title; "
            f"need at least {min_required_docs}."
        )

    # Question types plan covering all 4 categories: summary, authors, date, categories
    question_types = ["summary", "authors", "date", "categories"]
    if num_questions == 10:
        type_plan = [
            "summary",
            "authors",
            "date",
            "categories",
            "summary",
            "authors",
            "date",
            "categories",
            "summary",
            "authors",
        ]
    else:
        type_plan = [question_types[i % len(question_types)] for i in range(num_questions)]

    # 3 & 4. Tao cau hoi va format row
    test_set: list[dict[str, Any]] = []
    for idx in range(num_questions):
        q_type = type_plan[idx]
        paper = valid_records[idx % len(valid_records)]

        paper_id = str(paper.get("paper_id", "")).strip()
        title = normalize_whitespace(str(paper.get("title", "")))

        if q_type == "summary":
            summary = _extract_summary(paper)
            ground_truth = first_sentence(summary)
            question = f"What is the summary of the paper '{title}'?"
        elif q_type == "authors":
            ground_truth = _extract_authors(paper)
            question = f"Who authored the paper '{title}'?"
        elif q_type == "date":
            ground_truth = _extract_published(paper)
            question = f"When was the paper '{title}' published?"
        elif q_type == "categories":
            ground_truth = _extract_categories(paper)
            question = f"What categories does the paper '{title}' belong to?"
        else:
            raise ValueError(f"Unknown question type: {q_type}")

        test_set.append(
            {
                "id": f"q_{idx + 1:02d}",
                "question_type": q_type,
                "question": question,
                "ground_truth": ground_truth,
                "ground_truth_doc_ids": [paper_id],
            }
        )

    # 5. Ghi file JSON vao output_path
    if output_path is not None:
        target_path = Path(output_path)
        write_json(target_path, test_set)

    return test_set
