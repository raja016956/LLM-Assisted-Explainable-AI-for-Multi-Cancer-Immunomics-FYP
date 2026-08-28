from __future__ import annotations

from pathlib import Path
import json

from app.pipeline.pathway_immune_integration import (
    run_pathway_immune_integration,
    PathwayImmuneIntegrationConfig,
)


# ============================================================
# PATHS
# ============================================================

# This test file is located at:
#
# immuno-xai-insight/
# └── backend/
#     └── test_pathway_immune_integration.py
#
# Therefore BASE_DIR = backend/

BASE_DIR = Path(__file__).resolve().parent

ANALYSIS_DIR = BASE_DIR / "analysis_data"


# ------------------------------------------------------------
# PATHWAY SCORING
# ------------------------------------------------------------

PATHWAY_DIR = (
    ANALYSIS_DIR
    / "pathway_scoring"
)

PATHWAY_SCORES_PATH = (
    PATHWAY_DIR
    / "pathway_scores.npy"
)

PATHWAY_NAMES_PATH = (
    PATHWAY_DIR
    / "pathway_names.json"
)


# ------------------------------------------------------------
# IMMUNE STATE SCORING
# ------------------------------------------------------------

IMMUNE_SCORING_DIR = (
    ANALYSIS_DIR
    / "immune_state_scoring"
)

IMMUNE_SCORES_PATH = (
    IMMUNE_SCORING_DIR
    / "immune_scores.npy"
)

IMMUNE_SCORE_NAMES_PATH = (
    IMMUNE_SCORING_DIR
    / "score_names.json"
)


# ------------------------------------------------------------
# IMMUNE STATE ASSIGNMENT
# ------------------------------------------------------------

IMMUNE_ASSIGNMENT_DIR = (
    ANALYSIS_DIR
    / "immune_state_assignment"
)

CELL_STATES_PATH = (
    IMMUNE_ASSIGNMENT_DIR
    / "cell_immune_states.json"
)


# ------------------------------------------------------------
# CLUSTERING
# ------------------------------------------------------------

CLUSTERING_DIR = (
    ANALYSIS_DIR
    / "clustering"
)

CLUSTER_LABELS_PATH = (
    CLUSTERING_DIR
    / "cluster_labels.npy"
)


# ------------------------------------------------------------
# OUTPUT
# ------------------------------------------------------------

OUTPUT_DIR = (
    ANALYSIS_DIR
    / "pathway_immune_integration"
)


# ============================================================
# TEST
# ============================================================

def main():

    print("=" * 70)

    print(
        "IMMUNO-XAI PATHWAY + IMMUNE-STATE INTEGRATION TEST"
    )

    print("=" * 70)

    print()

    print(
        "INPUT FILES"
    )

    print("-" * 70)

    print(
        "Pathway scores:",
        PATHWAY_SCORES_PATH
    )

    print(
        "Pathway names:",
        PATHWAY_NAMES_PATH
    )

    print(
        "Immune scores:",
        IMMUNE_SCORES_PATH
    )

    print(
        "Immune score names:",
        IMMUNE_SCORE_NAMES_PATH
    )

    print(
        "Cell states:",
        CELL_STATES_PATH
    )

    print(
        "Cluster labels:",
        CLUSTER_LABELS_PATH
    )

    print(
        "Output:",
        OUTPUT_DIR
    )

    print()


    # ========================================================
    # INPUT VALIDATION
    # ========================================================

    required_inputs = [

        PATHWAY_SCORES_PATH,

        PATHWAY_NAMES_PATH,

        IMMUNE_SCORES_PATH,

        IMMUNE_SCORE_NAMES_PATH,

        CELL_STATES_PATH,

        CLUSTER_LABELS_PATH,
    ]


    for path in required_inputs:

        if not path.exists():

            raise FileNotFoundError(
                f"Required input file not found:\n{path}"
            )


    # ========================================================
    # RUN PIPELINE
    # ========================================================

    result = run_pathway_immune_integration(

        pathway_scores_path=PATHWAY_SCORES_PATH,

        pathway_names_path=PATHWAY_NAMES_PATH,

        immune_scores_path=IMMUNE_SCORES_PATH,

        immune_score_names_path=IMMUNE_SCORE_NAMES_PATH,

        cell_states_path=CELL_STATES_PATH,

        cluster_labels_path=CLUSTER_LABELS_PATH,

        output_dir=OUTPUT_DIR,

        config=PathwayImmuneIntegrationConfig(),
    )


    # ========================================================
    # PIPELINE SUMMARY
    # ========================================================

    print(
        "PIPELINE SUMMARY"
    )

    print("-" * 70)

    if "input_cells" in result:

        print(
            "Cells:",
            result["input_cells"]
        )

    if "pathway_count" in result:

        print(
            "Pathways:",
            result["pathway_count"]
        )

    if "immune_score_count" in result:

        print(
            "Immune scores:",
            result["immune_score_count"]
        )

    if "n_clusters" in result:

        print(
            "Clusters:",
            result["n_clusters"]
        )


    # ========================================================
    # DISPLAY RESULT KEYS
    # ========================================================

    print()

    print(
        "RESULT"
    )

    print("-" * 70)

    print(
        "Returned keys:"
    )

    for key in result.keys():

        print(
            " ",
            key
        )


    # ========================================================
    # OUTPUT VALIDATION
    # ========================================================

    print()

    print(
        "OUTPUT VALIDATION"
    )

    print("-" * 70)


    # Try to obtain output paths returned by pipeline.
    # If a particular implementation does not return them,
    # validate the output directory itself.

    output_paths = []


    for key, value in result.items():

        if (
            key.endswith("_output")
            and isinstance(value, str)
        ):

            output_paths.append(
                Path(value)
            )


    if output_paths:

        for output in output_paths:

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

        if not OUTPUT_DIR.exists():

            raise RuntimeError(
                f"Output directory was not created: "
                f"{OUTPUT_DIR}"
            )

        files = list(
            OUTPUT_DIR.iterdir()
        )

        if not files:

            raise RuntimeError(
                f"Output directory is empty: "
                f"{OUTPUT_DIR}"
            )

        for output in sorted(files):

            print(
                "✓",
                output.name,
                "exists"
            )


    # ========================================================
    # OPTIONAL METADATA DISPLAY
    # ========================================================

    metadata_candidates = [

        OUTPUT_DIR
        / "pathway_immune_metadata.json",

        OUTPUT_DIR
        / "integration_metadata.json",

        OUTPUT_DIR
        / "metadata.json",
    ]


    for metadata_path in metadata_candidates:

        if metadata_path.exists():

            print()

            print(
                "METADATA"
            )

            print("-" * 70)

            with open(
                metadata_path,
                "r",
                encoding="utf-8",
            ) as handle:

                metadata = json.load(
                    handle
                )

            print(
                "Keys:",
                ", ".join(
                    metadata.keys()
                )
            )

            break


    # ========================================================
    # FINAL
    # ========================================================

    print()

    print("=" * 70)

    print(
        "PATHWAY + IMMUNE-STATE INTEGRATION TEST COMPLETE"
    )

    print("=" * 70)


if __name__ == "__main__":

    main()