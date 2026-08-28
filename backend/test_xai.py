from __future__ import annotations

from pathlib import Path
import json

from app.pipeline.xai import (
    run_xai,
    XAIConfig,
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

MODEL_PATH = (
    ANALYSIS_DIR
    / "ml"
    / "random_forest.pkl"
)

FEATURES_PATH = (
    ANALYSIS_DIR
    / "ml"
    / "ml_features.npy"
)

SCORE_NAMES_PATH = (
    ANALYSIS_DIR
    / "immune_state_scoring"
    / "score_names.json"
)

PREDICTIONS_PATH = (
    ANALYSIS_DIR
    / "ml"
    / "random_forest_predictions.npy"
)

OUTPUT_DIR = (
    ANALYSIS_DIR
    / "xai"
)


# ============================================================
# TEST
# ============================================================

def main():

    print("=" * 70)
    print(
        "IMMUNO-XAI EXPLAINABLE AI TEST"
    )
    print("=" * 70)

    print()
    print(
        "INPUT FILES"
    )
    print("-" * 70)

    print(
        "Model:",
        MODEL_PATH
    )

    print(
        "Features:",
        FEATURES_PATH
    )

    print(
        "Score names:",
        SCORE_NAMES_PATH
    )

    print(
        "Predictions:",
        PREDICTIONS_PATH
    )

    print(
        "Output:",
        OUTPUT_DIR
    )

    print()

    result = run_xai(

        model_path=MODEL_PATH,

        features_path=FEATURES_PATH,

        score_names_path=SCORE_NAMES_PATH,

        predictions_path=PREDICTIONS_PATH,

        output_dir=OUTPUT_DIR,

        config=XAIConfig(
            top_n_features=20,
            max_explanation_cells=200,
            random_state=42,
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
        "Input cells:",
        result["input_cells"]
    )

    print(
        "Explained cells:",
        result["explained_cells"]
    )

    print(
        "Features:",
        result["features"]
    )

    print(
        "Classes:",
        result["classes"]
    )

    print(
        "SHAP shape:",
        result["shap_shape"]
    )

    # ========================================================
    # GLOBAL FEATURES
    # ========================================================

    print()
    print(
        "TOP GLOBAL XAI FEATURES"
    )
    print("-" * 70)

    with open(
        result["global_output"],
        "r",
        encoding="utf-8",
    ) as handle:

        global_data = json.load(
            handle
        )

    for item in global_data[
        "features"
    ]:

        print(
            f"{item['feature']}: "
            f"{item['mean_absolute_shap']:.6f}"
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
            result[
                "shap_values_output"
            ]
        ),

        Path(
            result[
                "global_output"
            ]
        ),

        Path(
            result[
                "class_output"
            ]
        ),

        Path(
            result[
                "cell_output"
            ]
        ),

        Path(
            result[
                "metadata_output"
            ]
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
        "EXPLAINABLE AI TEST COMPLETE"
    )

    print("=" * 70)


if __name__ == "__main__":
    main()