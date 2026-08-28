from __future__ import annotations

from pathlib import Path
import json


from app.pipeline.immune_state_assignment import (
    run_immune_state_assignment,
    ImmuneStateAssignmentConfig,
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(
    __file__
).resolve().parent

ANALYSIS_DIR = (
    BASE_DIR
    / "analysis_data"
)

SCORES_PATH = (
    ANALYSIS_DIR
    / "immune_state_scoring"
    / "immune_scores.npy"
)

SCORE_NAMES_PATH = (
    ANALYSIS_DIR
    / "immune_state_scoring"
    / "score_names.json"
)

CLUSTER_LABELS_PATH = (
    ANALYSIS_DIR
    / "clustering"
    / "cluster_labels.npy"
)

OUTPUT_DIR = (
    ANALYSIS_DIR
    / "immune_state_assignment"
)


# ============================================================
# TEST
# ============================================================

def main():

    print("=" * 70)

    print(
        "IMMUNO-XAI IMMUNE-STATE ASSIGNMENT TEST"
    )

    print("=" * 70)

    print()
    print(
        "INPUT FILES"
    )

    print("-" * 70)

    print(
        "Scores:",
        SCORES_PATH
    )

    print(
        "Score names:",
        SCORE_NAMES_PATH
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

    result = run_immune_state_assignment(

        immune_scores_path=SCORES_PATH,

        score_names_path=SCORE_NAMES_PATH,

        cluster_labels_path=CLUSTER_LABELS_PATH,

        output_dir=OUTPUT_DIR,

        config=ImmuneStateAssignmentConfig(
            minimum_supported_signatures=2,
            minimum_signal=0.005,
            dominance_ratio=1.25,
            suppression_ratio=1.25,
            inflammatory_ratio=1.15,
            antigen_presentation_threshold=0.01,
        ),
    )

    # ========================================================
    # SUMMARY
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
        "Scores:",
        result["input_scores"]
    )

    print(
        "Clusters:",
        result["n_clusters"]
    )

    # ========================================================
    # STATE DISTRIBUTION
    # ========================================================

    print()
    print(
        "CELL STATE DISTRIBUTION"
    )

    print("-" * 70)

    for state, count in sorted(
        result["state_distribution"].items()
    ):

        print(
            f"{state}: {count} cells"
        )

    # ========================================================
    # CLUSTER STATES
    # ========================================================

    print()
    print(
        "CLUSTER IMMUNE STATES"
    )

    print("-" * 70)

    with open(
        result["cluster_output"],
        "r",
        encoding="utf-8",
    ) as handle:

        data = json.load(handle)

    for cluster_id, cluster in data[
        "clusters"
    ].items():

        print()

        print(
            f"Cluster {cluster_id} "
            f"({cluster['n_cells']} cells)"
        )

        print(
            "  Assigned state:",
            cluster["state"]
        )

        print(
            "  Dominant cell state:",
            cluster[
                "dominant_cell_state"
            ]
        )

        print(
            "  Confidence:",
            f"{cluster['confidence']:.3f}"
        )

        print(
            "  Reason:",
            cluster["reason"]
        )

        print(
            "  Cell distribution:",
            cluster[
                "cell_state_distribution"
            ]
        )

    # ========================================================
    # OUTPUT VALIDATION
    # ========================================================

    print()
    print(
        "OUTPUT VALIDATION"
    )

    print("-" * 70)

    required_outputs = [

        Path(
            result["cell_output"]
        ),

        Path(
            result["cluster_output"]
        ),

        Path(
            result["distribution_output"]
        ),

        Path(
            result["summary_output"]
        ),
    ]

    for output in required_outputs:

        if not output.exists():

            raise RuntimeError(
                f"Missing output: {output}"
            )

        print(
            "✓",
            output.name,
            "exists"
        )

    # ========================================================
    # FINAL
    # ========================================================

    print()
    print("=" * 70)

    print(
        "IMMUNE-STATE ASSIGNMENT TEST COMPLETE"
    )

    print("=" * 70)


if __name__ == "__main__":
    main()