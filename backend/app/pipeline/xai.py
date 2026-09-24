from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json

import numpy as np

# ============================================================
# CONFIGURATION
# ============================================================

@dataclass
class XAIConfig:
    top_n_features: int = 20
    max_explanation_cells: int = 200
    random_state: int = 42

# ============================================================
# HELPERS
# ============================================================

# Loads the ML/analysis metadata needed to explain model predictions.
def _load_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(
            f"JSON file not found: {path}"
        )

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as handle:
        return json.load(handle)

# Saves explainability results for the Results page and PDF report.
def _save_json(
    path: Path,
    data: Any,
) -> None:

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        path,
        "w",
        encoding="utf-8",
    ) as handle:

        json.dump(
            data,
            handle,
            indent=2,
            ensure_ascii=False,
        )

# ============================================================
# FEATURE NAMES
# ============================================================

# Builds readable feature names so model features can be shown to the user.
def _build_feature_names(
    n_features: int,
    score_names_path: Path,
) -> list[str]:

    score_names = _load_json(
        score_names_path
    )

    if not isinstance(
        score_names,
        list,
    ):
        raise ValueError(
            "score_names.json must contain a list."
        )

    feature_names = []

    # PCA features
    for index in range(
        n_features - len(score_names)
    ):

        feature_names.append(
            f"PC{index + 1}"
        )

    # Immune-score features
    for name in score_names:

        feature_names.append(
            f"immune_{name}"
        )

    if len(feature_names) != n_features:

        raise ValueError(
            "Unable to construct feature names. "
            f"Expected {n_features}, "
            f"got {len(feature_names)}."
        )

    return feature_names

# ============================================================
# XAI
# ============================================================

# Runs the explainable-AI stage and calculates SHAP-based feature importance.
def run_xai(
    model_path: str | Path,
    features_path: str | Path,
    score_names_path: str | Path,
    predictions_path: str | Path,
    output_dir: str | Path,
    config: XAIConfig | None = None,
) -> dict[str, Any]:

    if config is None:
        config = XAIConfig()

    model_path = Path(model_path)
    features_path = Path(features_path)
    score_names_path = Path(score_names_path)
    predictions_path = Path(predictions_path)
    output_dir = Path(output_dir)

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------------------------------
    # VALIDATE INPUTS
    # --------------------------------------------------------

    for path, description in [
        (model_path, "Random Forest model"),
        (features_path, "ML feature matrix"),
        (score_names_path, "score names"),
        (predictions_path, "predictions"),
    ]:

        if not path.exists():

            raise FileNotFoundError(
                f"{description} not found: {path}"
            )

    # --------------------------------------------------------
    # LOAD MODEL
    # --------------------------------------------------------

    import joblib

    model = joblib.load(
        model_path
    )

    # --------------------------------------------------------
    # LOAD FEATURES
    # --------------------------------------------------------

    X = np.load(
        features_path
    )

    if X.ndim != 2:

        raise ValueError(
            "Feature matrix must be 2-dimensional."
        )

    n_cells, n_features = X.shape

    if n_cells == 0 or n_features == 0:

        raise ValueError(
            "Feature matrix is empty."
        )

    # --------------------------------------------------------
    # LOAD PREDICTIONS
    # --------------------------------------------------------

    predictions = np.load(
        predictions_path,
        allow_pickle=True,
    )

    if len(predictions) != n_cells:

        raise ValueError(
            "Prediction count does not match "
            "feature matrix cells. "
            f"Cells: {n_cells}, "
            f"Predictions: {len(predictions)}"
        )

    # --------------------------------------------------------
    # FEATURE NAMES
    # --------------------------------------------------------

    feature_names = _build_feature_names(
        n_features=n_features,
        score_names_path=score_names_path,
    )

    # --------------------------------------------------------
    # MODEL FEATURE COUNT
    # --------------------------------------------------------

    if not hasattr(
        model,
        "n_features_in_",
    ):

        raise ValueError(
            "Loaded model does not expose "
            "n_features_in_."
        )

    if model.n_features_in_ != n_features:

        raise ValueError(
            "Model feature count does not match "
            "feature matrix. "
            f"Model: {model.n_features_in_}, "
            f"Features: {n_features}"
        )

    # --------------------------------------------------------
    # SHAP
    # --------------------------------------------------------

    try:

        import shap

    except ImportError as exc:

        raise ImportError(
            "The 'shap' package is required "
            "for XAI. Install it with:\n"
            "python -m pip install shap"
        ) from exc

    # --------------------------------------------------------
    # LIMIT EXPLANATION SIZE
    # --------------------------------------------------------

    rng = np.random.default_rng(
        config.random_state
    )

    if n_cells > config.max_explanation_cells:

        selected_indices = np.sort(
            rng.choice(
                n_cells,
                size=config.max_explanation_cells,
                replace=False,
            )
        )

    else:

        selected_indices = np.arange(
            n_cells
        )

    X_explain = X[
        selected_indices
    ]

    # --------------------------------------------------------
    # CREATE SHAP EXPLAINER
    # --------------------------------------------------------

    explainer = shap.TreeExplainer(
        model
    )

    shap_values = explainer.shap_values(
        X_explain
    )

    # --------------------------------------------------------
    # NORMALIZE SHAP OUTPUT
    # --------------------------------------------------------

    if isinstance(
        shap_values,
        list,
    ):

        # Multi-class classification:
        # list[class] -> cells x features

        shap_array = np.stack(
            shap_values,
            axis=0,
        )

    else:

        shap_array = np.asarray(
            shap_values
        )

        if shap_array.ndim == 2:

            # Binary/single-output case
            shap_array = shap_array[
                np.newaxis,
                :,
                :,
            ]

        elif shap_array.ndim == 3:

            # Some SHAP versions return:
            # cells x features x classes
            if shap_array.shape[1] == n_features:

                shap_array = np.moveaxis(
                    shap_array,
                    2,
                    0,
                )

    if shap_array.ndim != 3:

        raise RuntimeError(
            "Unexpected SHAP output shape: "
            f"{shap_array.shape}"
        )

    n_classes = shap_array.shape[0]

    if shap_array.shape[1] != len(
        selected_indices
    ):

        raise RuntimeError(
            "SHAP cell dimension does not match "
            "selected cells."
        )

    if shap_array.shape[2] != n_features:

        raise RuntimeError(
            "SHAP feature dimension does not match "
            "input features."
        )

    # --------------------------------------------------------
    # GLOBAL FEATURE IMPORTANCE
    # --------------------------------------------------------

    global_importance = np.mean(
        np.abs(shap_array),
        axis=(0, 1),
    )

    ranked_indices = np.argsort(
        global_importance
    )[::-1]

    global_features = []

    for index in ranked_indices[
        :config.top_n_features
    ]:

        global_features.append(
            {
                "feature": feature_names[
                    int(index)
                ],
                "mean_absolute_shap": float(
                    global_importance[index]
                ),
                "feature_index": int(
                    index
                ),
            }
        )

    # --------------------------------------------------------
    # CLASS-SPECIFIC IMPORTANCE
    # --------------------------------------------------------

    class_names = []

    if hasattr(
        model,
        "classes_",
    ):

        class_names = [
            str(value)
            for value in model.classes_
        ]

    else:

        class_names = [
            str(index)
            for index in range(
                n_classes
            )
        ]

    class_importance = {}

    for class_index in range(
        n_classes
    ):

        importance = np.mean(
            np.abs(
                shap_array[
                    class_index
                ]
            ),
            axis=0,
        )

        indices = np.argsort(
            importance
        )[::-1]

        class_features = []

        for index in indices[
            :config.top_n_features
        ]:

            class_features.append(
                {
                    "feature": feature_names[
                        int(index)
                    ],
                    "mean_absolute_shap": float(
                        importance[index]
                    ),
                    "feature_index": int(
                        index
                    ),
                }
            )

        class_name = (
            class_names[class_index]
            if class_index < len(
                class_names
            )
            else str(class_index)
        )

        class_importance[
            class_name
        ] = class_features

    # --------------------------------------------------------
    # PER-CELL EXPLANATIONS
    # --------------------------------------------------------

    cell_explanations = []

    for local_index, original_index in enumerate(
        selected_indices
    ):

        prediction = str(
            predictions[
                original_index
            ]
        )

        # Determine predicted class index
        predicted_class_index = 0

        if hasattr(
            model,
            "classes_",
        ):

            matches = np.where(
                model.classes_
                == predictions[
                    original_index
                ]
            )[0]

            if len(matches) > 0:

                predicted_class_index = int(
                    matches[0]
                )

        values = shap_array[
            predicted_class_index,
            local_index,
            :
        ]

        ranked = np.argsort(
            np.abs(values)
        )[::-1]

        top_features = []

        for feature_index in ranked[
            :config.top_n_features
        ]:

            value = float(
                values[
                    feature_index
                ]
            )

            top_features.append(
                {
                    "feature": feature_names[
                        int(feature_index)
                    ],
                    "value": value,
                    "direction": (
                        "positive"
                        if value > 0
                        else
                        "negative"
                        if value < 0
                        else
                        "neutral"
                    ),
                    "feature_value": float(
                        X[
                            original_index,
                            feature_index
                        ]
                    ),
                }
            )

        cell_explanations.append(
            {
                "cell_index": int(
                    original_index
                ),
                "predicted_state": prediction,
                "top_features": top_features,
            }
        )

    # --------------------------------------------------------
    # SAVE SHAP VALUES
    # --------------------------------------------------------

    shap_values_output = (
        output_dir
        / "shap_values.npy"
    )

    np.save(
        shap_values_output,
        shap_array,
    )

    # --------------------------------------------------------
    # SAVE GLOBAL IMPORTANCE
    # --------------------------------------------------------

    global_output = (
        output_dir
        / "global_feature_importance.json"
    )

    _save_json(
        global_output,
        {
            "features": global_features,
            "n_cells_explained": int(
                len(selected_indices)
            ),
            "n_features": int(
                n_features
            ),
        },
    )

    # --------------------------------------------------------
    # SAVE CLASS IMPORTANCE
    # --------------------------------------------------------

    class_output = (
        output_dir
        / "class_feature_importance.json"
    )

    _save_json(
        class_output,
        class_importance,
    )

    # --------------------------------------------------------
    # SAVE CELL EXPLANATIONS
    # --------------------------------------------------------

    cell_output = (
        output_dir
        / "cell_explanations.json"
    )

    _save_json(
        cell_output,
        {
            "n_cells_explained": int(
                len(cell_explanations)
            ),
            "cells": cell_explanations,
        },
    )

    # --------------------------------------------------------
    # SAVE METADATA
    # --------------------------------------------------------

    metadata_output = (
        output_dir
        / "xai_metadata.json"
    )

    _save_json(
        metadata_output,
        {
            "method": "SHAP TreeExplainer",
            "model": "Random Forest",
            "input_cells": int(
                n_cells
            ),
            "explained_cells": int(
                len(selected_indices)
            ),
            "features": int(
                n_features
            ),
            "classes": class_names,
            "top_n_features": int(
                config.top_n_features
            ),
            "shap_shape": [
                int(value)
                for value in shap_array.shape
            ],
            "explained_cell_indices": [
                int(value)
                for value in selected_indices
            ],
        },
    )

    # --------------------------------------------------------
    # RESULT
    # --------------------------------------------------------

    return {
        "input_cells": int(
            n_cells
        ),
        "explained_cells": int(
            len(selected_indices)
        ),
        "features": int(
            n_features
        ),
        "classes": class_names,
        "shap_shape": [
            int(value)
            for value in shap_array.shape
        ],
        "global_output": str(
            global_output
        ),
        "class_output": str(
            class_output
        ),
        "cell_output": str(
            cell_output
        ),
        "shap_values_output": str(
            shap_values_output
        ),
        "metadata_output": str(
            metadata_output
        ),
    }