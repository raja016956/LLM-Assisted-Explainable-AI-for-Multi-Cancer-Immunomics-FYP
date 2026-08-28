from __future__ import annotations

from pathlib import Path
import json

import numpy as np

from app.pipeline.ml import (
    run_ml,
    MLConfig,
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

PCA_PATH = (
    ANALYSIS_DIR
    / "pca"
    / "pca_coordinates.npy"
)

IMMUNE_SCORES_PATH = (
    ANALYSIS_DIR
    / "immune_state_scoring"
    / "immune_scores.npy"
)

CELL_STATES_PATH = (
    ANALYSIS_DIR
    / "immune_state_assignment"
    / "cell_immune_states.json"
)

OUTPUT_DIR = (
    ANALYSIS_DIR
    / "ml"
)


# ============================================================
# TEST
# ============================================================

def main():

    print("=" * 70)

    print(
        "IMMUNO-XAI MACHINE LEARNING TEST"
    )

    print("=" * 70)

    print()

    print(
        "INPUT FILES"
    )

    print("-" * 70)

    print(
        "PCA:",
        PCA_PATH
    )

    print(
        "Immune scores:",
        IMMUNE_SCORES_PATH
    )

    print(
        "Cell states:",
        CELL_STATES_PATH
    )

    print(
        "Output:",
        OUTPUT_DIR
    )

    print()

    # ========================================================
    # RUN ML
    # ========================================================

    result = run_ml(

        pca_coordinates_path=PCA_PATH,

        immune_scores_path=IMMUNE_SCORES_PATH,

        cell_states_path=CELL_STATES_PATH,

        output_dir=OUTPUT_DIR,

        config=MLConfig(

            test_size=0.20,

            random_state=42,

            n_estimators=300,

            minimum_class_size=2,
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
        "Usable cells:",
        result["usable_cells"]
    )

    print(
        "Excluded cells:",
        result["excluded_cells"]
    )

    print(
        "Features:",
        result["feature_count"]
    )

    # ========================================================
    # CLASSES
    # ========================================================

    print()

    print(
        "CLASS DISTRIBUTION"
    )

    print("-" * 70)

    for state, count in (
        result[
            "class_distribution"
        ].items()
    ):

        print(
            f"{state}: {count} cells"
        )

    # ========================================================
    # RANDOM FOREST
    # ========================================================

    print()

    print(
        "RANDOM FOREST"
    )

    print("-" * 70)

    rf = result[
        "random_forest"
    ]

    print(
        "Accuracy:",
        f"{rf['accuracy']:.4f}"
    )

    print(
        "Balanced accuracy:",
        f"{rf['balanced_accuracy']:.4f}"
    )

    print(
        "Macro precision:",
        f"{rf['precision_macro']:.4f}"
    )

    print(
        "Macro recall:",
        f"{rf['recall_macro']:.4f}"
    )

    print(
        "Macro F1:",
        f"{rf['f1_macro']:.4f}"
    )

    # ========================================================
    # XGBOOST
    # ========================================================

    print()

    print(
        "XGBOOST"
    )

    print("-" * 70)

    xgb = result[
        "xgboost"
    ]

    if (
        isinstance(
            xgb,
            dict,
        )
        and xgb.get(
            "available"
        ) is False
    ):

        print(
            "Not available:",
            xgb["reason"]
        )

    else:

        print(
            "Accuracy:",
            f"{xgb['accuracy']:.4f}"
        )

        print(
            "Balanced accuracy:",
            f"{xgb['balanced_accuracy']:.4f}"
        )

        print(
            "Macro precision:",
            f"{xgb['precision_macro']:.4f}"
        )

        print(
            "Macro recall:",
            f"{xgb['recall_macro']:.4f}"
        )

        print(
            "Macro F1:",
            f"{xgb['f1_macro']:.4f}"
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

        OUTPUT_DIR
        / "random_forest.pkl",

        OUTPUT_DIR
        / "random_forest_predictions.npy",

        OUTPUT_DIR
        / "ml_features.npy",

        OUTPUT_DIR
        / "ml_labels.npy",

        OUTPUT_DIR
        / "feature_names.json",

        OUTPUT_DIR
        / "feature_importance.json",

        OUTPUT_DIR
        / "evaluation.json",

        OUTPUT_DIR
        / "ml_metadata.json",
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
    # LOAD AND VALIDATE FEATURE MATRIX
    # ========================================================

    print()

    print(
        "FEATURE MATRIX VALIDATION"
    )

    print("-" * 70)

    ml_features = np.load(
        OUTPUT_DIR
        / "ml_features.npy"
    )

    ml_labels = np.load(
        OUTPUT_DIR
        / "ml_labels.npy"
    )

    predictions = np.load(
        OUTPUT_DIR
        / "random_forest_predictions.npy"
    )

    with open(
        OUTPUT_DIR
        / "feature_names.json",
        "r",
        encoding="utf-8",
    ) as handle:

        feature_names = json.load(
            handle
        )

    # --------------------------------------------------------
    # Feature dimensions
    # --------------------------------------------------------

    if ml_features.ndim != 2:

        raise RuntimeError(
            "ml_features.npy must be a "
            "2-dimensional matrix."
        )

    if ml_features.shape[0] != result[
        "usable_cells"
    ]:

        raise RuntimeError(
            "ML feature row count does not match "
            "usable cell count. "
            f"Features: {ml_features.shape[0]}, "
            f"usable cells: {result['usable_cells']}"
        )

    if ml_features.shape[1] != result[
        "feature_count"
    ]:

        raise RuntimeError(
            "ML feature column count does not match "
            "feature count."
        )

    print(
        "✓ ML feature matrix shape:",
        ml_features.shape
    )

    # --------------------------------------------------------
    # Labels
    # --------------------------------------------------------

    if ml_labels.shape[0] != ml_features.shape[0]:

        raise RuntimeError(
            "ML labels are not aligned with "
            "ML feature rows."
        )

    print(
        "✓ ML labels aligned:",
        ml_labels.shape
    )

    # --------------------------------------------------------
    # Predictions
    # --------------------------------------------------------

    if predictions.shape[0] != ml_features.shape[0]:

        raise RuntimeError(
            "Random Forest predictions are not "
            "aligned with ml_features.npy. "
            f"Predictions: {predictions.shape[0]}, "
            f"features: {ml_features.shape[0]}"
        )

    print(
        "✓ Random Forest predictions aligned:",
        predictions.shape
    )

    # --------------------------------------------------------
    # Feature names
    # --------------------------------------------------------

    if len(feature_names) != ml_features.shape[1]:

        raise RuntimeError(
            "Feature-name count does not match "
            "feature matrix columns. "
            f"Names: {len(feature_names)}, "
            f"features: {ml_features.shape[1]}"
        )

    print(
        "✓ Feature names aligned:",
        len(feature_names)
    )

    # --------------------------------------------------------
    # Finite values
    # --------------------------------------------------------

    if not np.all(
        np.isfinite(ml_features)
    ):

        raise RuntimeError(
            "ML feature matrix contains "
            "non-finite values."
        )

    print(
        "✓ All feature values are finite"
    )

    # ========================================================
    # DISPLAY TOP FEATURES
    # ========================================================

    print()

    print(
        "TOP RANDOM FOREST FEATURES"
    )

    print("-" * 70)

    with open(
        OUTPUT_DIR
        / "feature_importance.json",
        "r",
        encoding="utf-8",
    ) as handle:

        importance = json.load(
            handle
        )

    ranked = sorted(
        importance.items(),
        key=lambda item: item[1],
        reverse=True,
    )

    for feature, value in ranked[:20]:

        print(
            f"{feature}: {value:.6f}"
        )

    # ========================================================
    # FINAL
    # ========================================================

    print()

    print("=" * 70)

    print(
        "MACHINE LEARNING TEST COMPLETE"
    )

    print("=" * 70)


if __name__ == "__main__":
    main()