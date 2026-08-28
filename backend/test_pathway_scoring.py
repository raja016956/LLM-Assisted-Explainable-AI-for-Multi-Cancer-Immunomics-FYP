from __future__ import annotations

from pathlib import Path
import json

from app.pipeline.pathway_scoring import (
    run_pathway_scoring,
    PathwayScoringConfig,
)


# ============================================================
# PATHS
# ============================================================

# test_pathway_scoring.py is located at:
#
# backend/
#   app/
#     pipeline/
#       test_pathway_scoring.py
#
# Therefore:
# parent      = pipeline
# parents[1]  = app
# parents[2]  = backend
#
BASE_DIR = Path(__file__).resolve().parents[2]

ANALYSIS_DIR = BASE_DIR / "analysis_data"


EXPRESSION_PATH = (
    ANALYSIS_DIR
    / "normalization"
    / "normalized_log1p.npz"
)

GENES_PATH = (
    ANALYSIS_DIR
    / "normalization"
    / "genes.json"
)

OUTPUT_DIR = (
    ANALYSIS_DIR
    / "pathway_scoring"
)


# ============================================================
# TEST
# ============================================================

def main():

    print("=" * 70)

    print(
        "IMMUNO-XAI METABOLIC + INFLAMMATORY PATHWAY SCORING TEST"
    )

    print("=" * 70)

    print()

    # ========================================================
    # INPUT FILES
    # ========================================================

    print(
        "INPUT FILES"
    )

    print("-" * 70)

    print(
        "Expression:",
        EXPRESSION_PATH
    )

    print(
        "Genes:",
        GENES_PATH
    )

    print(
        "Output:",
        OUTPUT_DIR
    )

    print()

    # ========================================================
    # INPUT VALIDATION
    # ========================================================

    for path, description in [
        (
            EXPRESSION_PATH,
            "Expression matrix",
        ),
        (
            GENES_PATH,
            "Gene metadata",
        ),
    ]:

        if not path.exists():

            raise FileNotFoundError(
                f"{description} not found: {path}"
            )

    # ========================================================
    # RUN PATHWAY SCORING
    # ========================================================

    result = run_pathway_scoring(

        expression_path=EXPRESSION_PATH,

        genes_path=GENES_PATH,

        output_dir=OUTPUT_DIR,

        config=PathwayScoringConfig(),
    )

    # ========================================================
    # PIPELINE SUMMARY
    # ========================================================

    print(
        "PIPELINE SUMMARY"
    )

    print("-" * 70)

    print(
        "Cells:",
        result["input_cells"]
    )

    print(
        "Genes:",
        result["input_genes"]
    )

    print(
        "Pathways:",
        result["n_pathways"]
    )

    # ========================================================
    # PATHWAYS
    # ========================================================

    print()

    print(
        "PATHWAYS"
    )

    print("-" * 70)

    for pathway in result.get(
        "pathways",
        []
    ):

        if isinstance(
            pathway,
            dict,
        ):

            name = pathway.get(
                "name",
                pathway.get(
                    "pathway",
                    "Unknown",
                ),
            )

            available = pathway.get(
                "available_genes",
                pathway.get(
                    "available",
                    None,
                ),
            )

            total = pathway.get(
                "total_genes",
                pathway.get(
                    "gene_count",
                    None,
                ),
            )

            print()

            print(
                f"{name}"
            )

            if (
                available is not None
                and total is not None
            ):

                print(
                    f"  Genes available: "
                    f"{available}/{total}"
                )

        else:

            print(
                f"  {pathway}"
            )

    # ========================================================
    # OUTPUT VALIDATION
    # ========================================================

    print()

    print(
        "OUTPUT VALIDATION"
    )

    print("-" * 70)

    # Get output paths returned by the pipeline.
    output_paths = []

    for key, value in result.items():

        if (
            key.endswith("_output")
            and isinstance(
                value,
                str,
            )
        ):

            output_paths.append(
                Path(value)
            )

    # Also validate the output directory.
    if not OUTPUT_DIR.exists():

        raise RuntimeError(
            f"Output directory was not created: "
            f"{OUTPUT_DIR}"
        )

    # Remove duplicates while preserving order.
    unique_outputs = []

    seen = set()

    for path in output_paths:

        path = path.resolve()

        if path not in seen:

            seen.add(path)

            unique_outputs.append(
                path
            )

    if unique_outputs:

        for output in unique_outputs:

            if not output.exists():

                raise RuntimeError(
                    f"Missing output: {output}"
                )

            print(
                "✓",
                output.name,
                "exists"
            )

    else:

        # Fallback validation:
        # make sure the pathway output directory
        # contains at least one generated file.

        generated_files = [
            path
            for path in OUTPUT_DIR.iterdir()
            if path.is_file()
        ]

        if not generated_files:

            raise RuntimeError(
                "Pathway scoring completed but "
                "no output files were generated."
            )

        for output in generated_files:

            print(
                "✓",
                output.name,
                "exists"
            )

    # ========================================================
    # DISPLAY PATHWAY SUMMARY
    # ========================================================

    print()

    print(
        "PATHWAY OUTPUT SUMMARY"
    )

    print("-" * 70)

    # Try to locate a JSON summary generated by the
    # pathway-scoring pipeline.

    json_files = sorted(
        OUTPUT_DIR.glob(
            "*.json"
        )
    )

    if json_files:

        for json_file in json_files:

            try:

                with open(
                    json_file,
                    "r",
                    encoding="utf-8",
                ) as handle:

                    data = json.load(
                        handle
                    )

                print()

                print(
                    json_file.name
                )

                if isinstance(
                    data,
                    dict,
                ):

                    print(
                        "  Keys:",
                        ", ".join(
                            data.keys()
                        )
                    )

            except (
                json.JSONDecodeError,
                OSError,
            ):

                print(
                    "  Unable to inspect JSON."
                )

    else:

        print(
            "No JSON summary files found."
        )

    # ========================================================
    # FINAL
    # ========================================================

    print()

    print("=" * 70)

    print(
        "PATHWAY SCORING TEST COMPLETE"
    )

    print("=" * 70)


if __name__ == "__main__":
    main()