from __future__ import annotations

from pathlib import Path
import json

from app.pipeline.final_analysis import (
    run_final_analysis,
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


# ------------------------------------------------------------
# IMMUNE-STATE ASSIGNMENT
# ------------------------------------------------------------

CELL_STATES_PATH = (
    ANALYSIS_DIR
    / "immune_state_assignment"
    / "cell_immune_states.json"
)

CLUSTER_STATES_PATH = (
    ANALYSIS_DIR
    / "immune_state_assignment"
    / "cluster_immune_states.json"
)


# ------------------------------------------------------------
# IMMUNE SCORES
# ------------------------------------------------------------

IMMUNE_SCORES_PATH = (
    ANALYSIS_DIR
    / "immune_state_scoring"
    / "immune_scores.npy"
)

IMMUNE_SCORE_NAMES_PATH = (
    ANALYSIS_DIR
    / "immune_state_scoring"
    / "score_names.json"
)


# ------------------------------------------------------------
# MACHINE LEARNING
# ------------------------------------------------------------

ML_PREDICTIONS_PATH = (
    ANALYSIS_DIR
    / "ml"
    / "random_forest_predictions.npy"
)


# ------------------------------------------------------------
# PATHWAY SCORING
# ------------------------------------------------------------

PATHWAY_SCORES_PATH = (
    ANALYSIS_DIR
    / "pathway_scoring"
    / "pathway_scores.npy"
)

PATHWAY_NAMES_PATH = (
    ANALYSIS_DIR
    / "pathway_scoring"
    / "pathway_names.json"
)


# ------------------------------------------------------------
# XAI
# ------------------------------------------------------------

XAI_IMPORTANCE_PATH = (
    ANALYSIS_DIR
    / "xai"
    / "global_feature_importance.json"
)


# ------------------------------------------------------------
# OUTPUT
# ------------------------------------------------------------

OUTPUT_DIR = (
    ANALYSIS_DIR
    / "final_analysis"
)


# ============================================================
# TEST
# ============================================================

def main():

    print("=" * 70)

    print(
        "IMMUNO-XAI FINAL ANALYSIS TEST"
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
        "Cell states:",
        CELL_STATES_PATH
    )

    print(
        "Cluster states:",
        CLUSTER_STATES_PATH
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
        "ML predictions:",
        ML_PREDICTIONS_PATH
    )

    print(
        "Pathway scores:",
        PATHWAY_SCORES_PATH
    )

    print(
        "Pathway names:",
        PATHWAY_NAMES_PATH
    )

    print(
        "XAI importance:",
        XAI_IMPORTANCE_PATH
    )

    print(
        "Output:",
        OUTPUT_DIR
    )

    print()

    # ========================================================
    # PRE-FLIGHT VALIDATION
    # ========================================================

    print(
        "INPUT VALIDATION"
    )

    print("-" * 70)

    required_inputs = [

        (
            CELL_STATES_PATH,
            "Cell immune states",
        ),

        (
            CLUSTER_STATES_PATH,
            "Cluster immune states",
        ),

        (
            IMMUNE_SCORES_PATH,
            "Immune scores",
        ),

        (
            IMMUNE_SCORE_NAMES_PATH,
            "Immune score names",
        ),

        (
            ML_PREDICTIONS_PATH,
            "ML predictions",
        ),

        (
            PATHWAY_SCORES_PATH,
            "Pathway scores",
        ),

        (
            PATHWAY_NAMES_PATH,
            "Pathway names",
        ),

        (
            XAI_IMPORTANCE_PATH,
            "XAI feature importance",
        ),
    ]

    for path, description in required_inputs:

        if not path.exists():

            raise FileNotFoundError(
                f"{description} not found:\n{path}"
            )

        print(
            "✓",
            description,
        )

    print()

    # ========================================================
    # RUN FINAL ANALYSIS
    # ========================================================

    result = run_final_analysis(

        cell_states_path=(
            CELL_STATES_PATH
        ),

        cluster_states_path=(
            CLUSTER_STATES_PATH
        ),

        immune_scores_path=(
            IMMUNE_SCORES_PATH
        ),

        immune_score_names_path=(
            IMMUNE_SCORE_NAMES_PATH
        ),

        ml_predictions_path=(
            ML_PREDICTIONS_PATH
        ),

        pathway_scores_path=(
            PATHWAY_SCORES_PATH
        ),

        pathway_names_path=(
            PATHWAY_NAMES_PATH
        ),

        xai_global_importance_path=(
            XAI_IMPORTANCE_PATH
        ),

        output_dir=(
            OUTPUT_DIR
        ),
    )

    # ========================================================
    # PIPELINE SUMMARY
    # ========================================================

    print(
        "PIPELINE SUMMARY"
    )

    print("-" * 70)

    print(
        "Input cells:",
        result["input_cells"],
    )

    print(
        "Clusters:",
        len(
            result[
                "cluster_summary"
            ]
        ),
    )

    print(
        "Immune scores:",
        len(
            result[
                "immune_score_summary"
            ]
        ),
    )

    # ========================================================
    # IMMUNE STATE SUMMARY
    # ========================================================

    print()

    print(
        "FINAL IMMUNE-STATE SUMMARY"
    )

    print("-" * 70)

    for state, summary in (
        result[
            "state_summary"
        ].items()
    ):

        print(
            f"{state}: "
            f"{summary['cell_count']} cells "
            f"("
            f"{summary['fraction'] * 100:.2f}%"
            f") "
            f"| mean confidence = "
            f"{summary['mean_confidence']:.3f}"
        )

    # ========================================================
    # CLUSTER SUMMARY
    # ========================================================

    print()

    print(
        "CLUSTER SUMMARY"
    )

    print("-" * 70)

    for cluster_id, cluster in sorted(
        result[
            "cluster_summary"
        ].items(),
        key=lambda item: (
            int(item[0])
            if str(item[0]).isdigit()
            else 999999
        ),
    ):

        print()

        print(
            f"Cluster {cluster_id}"
            f" ({cluster['n_cells']} cells)"
        )

        print(
            "  Dominant state:",
            cluster[
                "dominant_state"
            ],
        )

        print(
            "  Dominant fraction:",
            f"{cluster['dominant_state_fraction']:.3f}",
        )

        print(
            "  Mean confidence:",
            f"{cluster['mean_cell_confidence']:.3f}",
        )

        print(
            "  Distribution:",
            cluster[
                "state_distribution"
            ],
        )

    # ========================================================
    # ML SUMMARY
    # ========================================================

    print()

    print(
        "MACHINE LEARNING SUMMARY"
    )

    print("-" * 70)

    ml_summary = result[
        "ml_summary"
    ]

    if ml_summary is None:

        print(
            "ML prediction data unavailable."
        )

    else:

        print(
            "Prediction count:",
            ml_summary[
                "prediction_count"
            ],
        )

        print(
            "Prediction distribution:"
        )

        for state, count in (
            ml_summary[
                "class_distribution"
            ].items()
        ):

            print(
                f"  {state}: {count}"
            )

    # ========================================================
    # PATHWAY SUMMARY
    # ========================================================

    print()

    print(
        "PATHWAY SUMMARY"
    )

    print("-" * 70)

    pathway_summary = result[
        "pathway_summary"
    ]

    if pathway_summary is None:

        print(
            "Pathway data unavailable."
        )

    else:

        for pathway, values in (
            pathway_summary.items()
        ):

            print(
                f"{pathway}: "
                f"mean={values['mean']:.4f}, "
                f"median={values['median']:.4f}, "
                f"std={values['std']:.4f}"
            )

    # ========================================================
    # XAI SUMMARY
    # ========================================================

    print()

    print(
        "XAI SUMMARY"
    )

    print("-" * 70)

    xai_summary = result[
        "xai_summary"
    ]

    if xai_summary is None:

        print(
            "XAI data unavailable."
        )

    else:

        if isinstance(
            xai_summary,
            dict,
        ):

            ranked_features = sorted(
                xai_summary.items(),
                key=lambda item: (
                    float(item[1])
                    if isinstance(
                        item[1],
                        (int, float),
                    )
                    else 0.0
                ),
                reverse=True,
            )

            print(
                "Top XAI features:"
            )

            for feature, value in (
                ranked_features[:10]
            ):

                if isinstance(
                    value,
                    (int, float),
                ):

                    print(
                        f"  {feature}: "
                        f"{value:.6f}"
                    )

                else:

                    print(
                        f"  {feature}: "
                        f"{value}"
                    )

        else:

            print(
                "XAI importance loaded."
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

        (
            OUTPUT_DIR
            / "final_analysis.json",
            "Final analysis",
        ),

        (
            OUTPUT_DIR
            / "llm_reasoning_input.json",
            "LLM reasoning input",
        ),

        (
            OUTPUT_DIR
            / "final_analysis_metadata.json",
            "Final analysis metadata",
        ),
    ]

    for output, description in (
        required_outputs
    ):

        if not output.exists():

            raise RuntimeError(
                f"Missing output: {output}"
            )

        print(
            "✓",
            output.name,
            "exists",
        )

    # ========================================================
    # VALIDATE FINAL JSON
    # ========================================================

    print()

    print(
        "FINAL ANALYSIS CONTENT"
    )

    print("-" * 70)

    with open(
        OUTPUT_DIR
        / "final_analysis.json",
        "r",
        encoding="utf-8",
    ) as handle:

        final_data = json.load(
            handle
        )

    print(
        "Top-level keys:"
    )

    for key in final_data.keys():

        print(
            f"  {key}"
        )

    # ========================================================
    # VALIDATE LLM INPUT
    # ========================================================

    print()

    print(
        "LLM REASONING INPUT"
    )

    print("-" * 70)

    with open(
        OUTPUT_DIR
        / "llm_reasoning_input.json",
        "r",
        encoding="utf-8",
    ) as handle:

        llm_data = json.load(
            handle
        )

    print(
        "Task:",
        llm_data.get(
            "task",
            "N/A",
        ),
    )

    print(
        "Instructions:",
        len(
            llm_data.get(
                "instructions",
                [],
            )
        ),
    )

    print(
        "Analysis package:",
        (
            "present"
            if "analysis"
            in llm_data
            else "missing"
        ),
    )

    # ========================================================
    # METADATA
    # ========================================================

    print()

    print(
        "FINAL METADATA"
    )

    print("-" * 70)

    with open(
        OUTPUT_DIR
        / "final_analysis_metadata.json",
        "r",
        encoding="utf-8",
    ) as handle:

        metadata = json.load(
            handle
        )

    print(
        "Input cells:",
        metadata.get(
            "input_cells"
        ),
    )

    print(
        "Immune scores:",
        metadata.get(
            "immune_score_count"
        ),
    )

    print(
        "Clusters:",
        metadata.get(
            "cluster_count"
        ),
    )

    print(
        "ML available:",
        metadata.get(
            "ml_available"
        ),
    )

    print(
        "Pathway available:",
        metadata.get(
            "pathway_available"
        ),
    )

    print(
        "XAI available:",
        metadata.get(
            "xai_available"
        ),
    )

    # ========================================================
    # FINAL
    # ========================================================

    print()

    print("=" * 70)

    print(
        "FINAL ANALYSIS TEST COMPLETE"
    )

    print("=" * 70)

    print()

    print(
        "The computational analysis package is ready "
        "for downstream LLM biological reasoning."
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()