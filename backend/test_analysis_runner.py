from pathlib import Path

from app.pipeline.analysis_runner import (
    run_full_analysis,
)


BASE_DIR = Path(__file__).resolve().parent

DATASET = (
    BASE_DIR
    / "GSM5161291_D37_2_counts.txt.gz"
)

OUTPUT_DIR = (
    BASE_DIR
    / "analysis_data"
    / "runner_test"
)


def progress(
    step_number,
    total_steps,
    step,
    message,
):
    print()
    print(
        f"[{step_number}/{total_steps}] "
        f"{step}: {message}"
    )


def main():

    print("=" * 70)
    print("IMMUNO-XAI FULL PIPELINE RUNNER TEST")
    print("=" * 70)

    print()
    print("Dataset:")
    print(DATASET)

    print()
    print("Output:")
    print(OUTPUT_DIR)

    if not DATASET.exists():

        raise FileNotFoundError(
            f"Dataset not found: {DATASET}"
        )

    result = run_full_analysis(
        dataset_path=DATASET,
        analysis_dir=OUTPUT_DIR,
        progress_callback=progress,
    )

    print()
    print("=" * 70)
    print("PIPELINE SUMMARY")
    print("=" * 70)

    print(
        "Runtime:",
        result["runtime_seconds"],
    )

    print(
        "Final analysis:",
        result["paths"]["final_analysis"],
    )

    print(
        "LLM input:",
        result["paths"]["llm_reasoning_input"],
    )

    print(
        "Biological interpretation:",
        result["paths"]["biological_interpretation"],
    )

    print(
        "Biological report:",
        result["paths"]["biological_report"],
    )

    print()
    print("=" * 70)
    print("FULL PIPELINE TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()