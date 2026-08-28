from __future__ import annotations

from pathlib import Path
import json

from app.pipeline.immune_state_scoring import (
    run_immune_state_scoring,
    ImmuneStateScoringConfig,
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

CLUSTER_LABELS_PATH = (
    ANALYSIS_DIR
    / "clustering"
    / "cluster_labels.npy"
)

OUTPUT_DIR = (
    ANALYSIS_DIR
    / "immune_state_scoring"
)


# ============================================================
# TEST
# ============================================================

def main():

    print("=" * 70)

    print(
        "IMMUNO-XAI IMMUNE-STATE SCORING TEST"
    )

    print("=" * 70)

    # --------------------------------------------------------
    # INPUTS
    # --------------------------------------------------------

    print()
    print("INPUT FILES")
    print("-" * 70)

    print(
        "Expression:",
        EXPRESSION_PATH,
    )

    print(
        "Genes:",
        GENES_PATH,
    )

    print(
        "Cluster labels:",
        CLUSTER_LABELS_PATH,
    )

    print(
        "Output:",
        OUTPUT_DIR,
    )

    # --------------------------------------------------------
    # RUN
    # --------------------------------------------------------

    result = run_immune_state_scoring(

        expression_path=EXPRESSION_PATH,

        genes_path=GENES_PATH,

        cluster_labels_path=CLUSTER_LABELS_PATH,

        output_dir=OUTPUT_DIR,

        config=ImmuneStateScoringConfig(),
    )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    print()
    print("PIPELINE SUMMARY")
    print("-" * 70)

    print(
        "Cells:",
        result["input_cells"],
    )

    print(
        "Genes:",
        result["input_genes"],
    )

    print(
        "Clusters:",
        result["n_clusters"],
    )

    print(
        "Scores:",
        len(result["score_names"]),
    )

    print(
        "Score matrix:",
        result["score_matrix_shape"],
    )

    # --------------------------------------------------------
    # SIGNATURE VALIDATION
    # --------------------------------------------------------

    print()
    print("SIGNATURES")
    print("-" * 70)

    for (
        signature_name,
        metadata,
    ) in result["signatures"].items():

        print()
        print(
            signature_name
        )

        print(
            "  Available genes:",
            metadata[
                "available_gene_count"
            ],
        )

        print(
            "  Available:",
            ", ".join(
                metadata[
                    "available_genes"
                ]
            ),
        )

        if metadata["missing_genes"]:

            print(
                "  Missing:",
                ", ".join(
                    metadata[
                        "missing_genes"
                    ]
                ),
            )

        else:

            print(
                "  Missing: none"
            )

        print(
            "  Supported:",
            metadata[
                "score_supported"
            ],
        )

    # --------------------------------------------------------
    # CLUSTER SUMMARY
    # --------------------------------------------------------

    print()
    print("CLUSTER SCORE SUMMARY")
    print("-" * 70)

    for (
        cluster_id,
        cluster_data,
    ) in result["clusters"].items():

        print()
        print(
            f"Cluster {cluster_id} "
            f"({cluster_data['n_cells']} cells)"
        )

        for (
            score_name,
            score,
        ) in cluster_data[
            "mean_scores"
        ].items():

            print(
                f"  {score_name}: "
                f"{score:.6f}"
            )

    # --------------------------------------------------------
    # OUTPUT VALIDATION
    # --------------------------------------------------------

    print()
    print("OUTPUT VALIDATION")
    print("-" * 70)

    json_output = Path(
        result["json_output"]
    )

    score_output = Path(
        result["score_matrix_output"]
    )

    names_output = Path(
        result["score_names_output"]
    )

    if not json_output.exists():

        raise RuntimeError(
            "JSON output was not created."
        )

    if not score_output.exists():

        raise RuntimeError(
            "NumPy score output was not created."
        )

    if not names_output.exists():

        raise RuntimeError(
            "Score names output was not created."
        )

    print(
        "✓ immune_scores.json exists"
    )

    print(
        "✓ immune_scores.npy exists"
    )

    print(
        "✓ score_names.json exists"
    )

    # --------------------------------------------------------
    # RELOAD SCORE MATRIX
    # --------------------------------------------------------

    import numpy as np

    scores = np.load(
        score_output
    )

    expected_shape = tuple(
        result[
            "score_matrix_shape"
        ]
    )

    if scores.shape != expected_shape:

        raise RuntimeError(
            "Saved score matrix shape "
            "does not match result metadata. "
            f"Expected {expected_shape}, "
            f"got {scores.shape}"
        )

    if not np.all(
        np.isfinite(scores)
    ):

        raise RuntimeError(
            "Saved immune scores contain "
            "non-finite values."
        )

    print(
        "✓ Score matrix shape validated"
    )

    print(
        "✓ All score values are finite"
    )

    # --------------------------------------------------------
    # FINAL
    # --------------------------------------------------------

    print()
    print("=" * 70)

    print(
        "IMMUNE-STATE SCORING TEST COMPLETE"
    )

    print("=" * 70)


if __name__ == "__main__":
    main()