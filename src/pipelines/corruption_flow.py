from __future__ import annotations

import pandas as pd
from core.config import Settings, load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def repair_from_raw_snapshot(settings: Settings) -> pd.DataFrame:
    print("Repairing from raw snapshot...")
    records = load_raw_records(settings.paths.raw_records_json)
    repaired_df = build_clean_dataframe(records, now_utc())
    
    write_csv(repaired_df, settings.paths.repaired_clean_csv)
    write_json(settings.paths.repaired_clean_json, repaired_df.to_dict(orient="records"))
    
    return repaired_df


def run_corruption_flow_pipeline(settings: Settings) -> None:
    print("1. Loading baseline metrics and clean dataset...")
    baseline_metrics = read_json(settings.paths.baseline_metrics)
    clean_df = pd.read_csv(settings.paths.clean_csv, keep_default_na=False).fillna("")

    print("2. Creating corrupted dataframe...")
    corrupted_df = corrupt_clean_dataframe(clean_df, settings.paths.corruption_log)

    print("3. Saving corrupted artifacts...")
    write_csv(corrupted_df, settings.paths.corrupted_clean_csv)
    write_json(settings.paths.corrupted_clean_json, corrupted_df.to_dict(orient="records"))

    print("4. Rebuilding index and evaluating on corrupted data (Silent Failure)...")
    corrupted_index = LocalEmbeddingIndex.build(corrupted_df, settings, settings.paths.corrupted_embeddings_json)
    corrupted_eval = evaluate_pipeline(
        settings, 
        corrupted_index, 
        settings.paths.eval_testset, 
        settings.paths.corrupted_metrics, 
        settings.paths.corrupted_answers
    )

    print("5. Running quality checks and freshness on corrupted data...")
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted")
    corrupted_freshness = build_freshness_report(corrupted_df, settings, settings.paths.freshness_report)

    print("6. Repairing from raw snapshot...")
    repaired_df = repair_from_raw_snapshot(settings)

    print("7. Evaluating repaired dataset...")
    repaired_index = LocalEmbeddingIndex.build(repaired_df, settings, settings.paths.repaired_embeddings_json)
    repaired_eval = evaluate_pipeline(
        settings, 
        repaired_index, 
        settings.paths.eval_testset, 
        settings.paths.repaired_metrics, 
        settings.paths.repaired_answers
    )
    
    print("Running quality checks and freshness on repaired data...")
    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired")
    repaired_freshness = build_freshness_report(repaired_df, settings, settings.paths.freshness_report)

    print("8. Generating comparison report...")
    generate_corruption_report(
        settings.paths.comparison_report,
        baseline_metrics,
        corrupted_eval.summary,
        repaired_eval.summary,
        corrupted_quality,
        repaired_quality,
        corrupted_freshness,
        repaired_freshness,
    )
    print("Corruption flow pipeline completed successfully!")


def main() -> None:
    settings = load_settings()
    run_corruption_flow_pipeline(settings)
