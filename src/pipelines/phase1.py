from __future__ import annotations

from core.config import Settings, load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex
from retrieval.qa import answer_question


def run_phase1_pipeline(settings: Settings) -> None:
    print(f"Loaded settings: LLM provider={settings.llm_provider}, model={settings.model_name}")

    # 1. Load hoac fetch raw records
    if settings.refresh_source or not settings.paths.raw_records_json.exists():
        print("Fetching raw records from Crossref API...")
        records = fetch_source_records(settings)
    else:
        print(f"Loading existing raw records from {settings.paths.raw_records_json}...")
        records = load_raw_records(settings.paths.raw_records_json)
    print(f"Loaded {len(records)} raw records.")

    # 2. Clean data
    print("Cleaning raw records into DataFrame...")
    df = build_clean_dataframe(records, run_date=now_utc())
    print(f"Cleaned DataFrame contains {len(df)} rows.")

    # 3. Save clean CSV/JSON
    print(f"Saving clean data to {settings.paths.clean_csv} and {settings.paths.clean_json}...")
    write_csv(df, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, df.to_dict(orient="records"))

    # 4. Build Chroma index
    print(f"Building Chroma vector index ({settings.baseline_collection_name})...")
    index = LocalEmbeddingIndex.build(
        df=df,
        settings=settings,
        embeddings_output_path=settings.paths.embeddings_json,
    )

    # 5. Tao hoac load evaluation set
    if settings.refresh_test_set or not settings.paths.eval_testset.exists():
        print(f"Generating benchmark test set at {settings.paths.eval_testset}...")
        test_set = build_test_set(df, settings.paths.eval_testset)
    else:
        print(f"Loading existing test set from {settings.paths.eval_testset}...")
        test_set = read_json(settings.paths.eval_testset)
    print(f"Benchmark test set ready with {len(test_set)} questions.")

    # 6. Evaluate
    print("Running baseline pipeline evaluation...")
    bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    hit_rate = bundle.summary.get("retrieval_hit_rate", 0.0)
    token_f1 = bundle.summary.get("mean_token_f1", 0.0)
    print(f"Baseline metrics: Retrieval Hit Rate = {hit_rate:.2%}, Mean Token F1 = {token_f1:.4f}")

    # 7. Run quality checks va freshness report
    print("Running data quality checks and freshness report...")
    quality_report = run_data_quality_checks(df, settings, stage="baseline")
    freshness_report = build_freshness_report(df, settings, settings.paths.freshness_report)

    # 8. Tao markdown report
    print(f"Generating Phase 1 markdown report at {settings.paths.baseline_report}...")
    source_summary = {
        "total_records": len(records),
        "clean_rows": len(df),
        "source_api": settings.source_api,
        "source_query": settings.source_query,
        "source_filter": settings.source_filter,
    }
    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=bundle.summary,
        quality=quality_report,
        freshness=freshness_report,
    )

    # 9. Co the demo agent tren vai sample question
    print("Running agent demo on sample questions...")
    demo_samples = test_set[:3] if test_set else []
    demo_answers = []
    for item in demo_samples:
        ans = answer_question(item["question"], settings=settings, index=index)
        demo_answers.append(
            {
                "id": item["id"],
                "question": item["question"],
                "answer": ans.answer,
                "retrieved_doc_ids": ans.retrieved_doc_ids,
                "retrieved_titles": ans.retrieved_titles,
            }
        )
    write_json(settings.paths.demo_answers, demo_answers)
    print("Phase 1 baseline pipeline completed successfully.")


def main() -> None:
    settings = load_settings()
    run_phase1_pipeline(settings)
