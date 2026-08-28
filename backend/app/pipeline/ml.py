from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import json
import pickle

import numpy as np


# ============================================================
# CONFIGURATION
# ============================================================

@dataclass
class MLConfig:
    test_size: float = 0.20
    random_state: int = 42

    # Random Forest
    n_estimators: int = 300
    max_depth: int | None = None
    min_samples_leaf: int = 1

    # XGBoost
    xgb_n_estimators: int = 300
    xgb_max_depth: int = 6
    xgb_learning_rate: float = 0.05
    xgb_subsample: float = 0.8
    xgb_colsample_bytree: float = 0.8

    # Classes
    minimum_class_size: int = 2

    # Model selection
    primary_model: str = "random_forest"


# ============================================================
# HELPERS
# ============================================================

def _load_numpy(
    path: str | Path,
) -> np.ndarray:

    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            f"NumPy file not found: {path}"
        )

    array = np.load(path)

    return np.asarray(array)


def _load_json(
    path: str | Path,
) -> Any:

    path = Path(path)

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
        )


# ============================================================
# FEATURE MATRIX
# ============================================================

def _build_feature_matrix(
    pca_coordinates: np.ndarray,
    immune_scores: np.ndarray,
) -> np.ndarray:

    if pca_coordinates.ndim != 2:
        raise ValueError(
            "PCA coordinates must be a 2-dimensional matrix."
        )

    if immune_scores.ndim != 2:
        raise ValueError(
            "Immune scores must be a 2-dimensional matrix."
        )

    if (
        pca_coordinates.shape[0]
        != immune_scores.shape[0]
    ):
        raise ValueError(
            "PCA coordinates and immune scores "
            "must contain the same number of cells. "
            f"PCA cells: {pca_coordinates.shape[0]}, "
            f"immune-score cells: {immune_scores.shape[0]}"
        )

    features = np.concatenate(
        [
            pca_coordinates,
            immune_scores,
        ],
        axis=1,
    )

    if not np.all(
        np.isfinite(features)
    ):
        raise ValueError(
            "Feature matrix contains non-finite values."
        )

    return features.astype(
        np.float64,
        copy=False,
    )


# ============================================================
# LABEL PREPARATION
# ============================================================

def _extract_state(
    item: Any,
) -> str:

    if isinstance(
        item,
        dict,
    ):

        state = item.get(
            "state"
        )

        if state is None:
            state = item.get(
                "immune_state"
            )

    else:

        state = item

    if state is None:
        raise ValueError(
            "A cell immune-state record has no state value."
        )

    return str(state)


def _prepare_labels(
    cell_states: Any,
    minimum_class_size: int,
) -> tuple[np.ndarray, dict[str, int], np.ndarray]:

    if not isinstance(
        cell_states,
        list,
    ):

        raise ValueError(
            "Cell immune states must be stored as a JSON list."
        )

    labels = np.asarray(
        [
            _extract_state(item)
            for item in cell_states
        ],
        dtype=str,
    )

    unique, counts = np.unique(
        labels,
        return_counts=True,
    )

    original_distribution = {
        str(label): int(count)
        for label, count
        in zip(unique, counts)
    }

    valid_classes = {
        label
        for label, count
        in original_distribution.items()
        if count >= minimum_class_size
    }

    if len(valid_classes) < 2:

        raise ValueError(
            "ML training requires at least two classes "
            f"with at least {minimum_class_size} cells each. "
            f"Observed classes: {original_distribution}"
        )

    keep_mask = np.array(
        [
            label in valid_classes
            for label in labels
        ],
        dtype=bool,
    )

    filtered_labels = labels[
        keep_mask
    ]

    filtered_distribution = {
        label: int(
            np.sum(
                filtered_labels == label
            )
        )
        for label in sorted(valid_classes)
    }

    return (
        filtered_labels,
        filtered_distribution,
        keep_mask,
    )


# ============================================================
# METRICS
# ============================================================

def _evaluate_model(
    model,
    x_test: np.ndarray,
    y_test: np.ndarray,
) -> dict[str, Any]:

    from sklearn.metrics import (
        accuracy_score,
        balanced_accuracy_score,
        classification_report,
        confusion_matrix,
        f1_score,
        precision_score,
        recall_score,
    )

    predictions = model.predict(
        x_test
    )

    labels = sorted(
        np.unique(
            np.concatenate(
                [
                    y_test,
                    predictions,
                ]
            )
        ).tolist()
    )

    return {

        "accuracy": float(
            accuracy_score(
                y_test,
                predictions,
            )
        ),

        "balanced_accuracy": float(
            balanced_accuracy_score(
                y_test,
                predictions,
            )
        ),

        "precision_macro": float(
            precision_score(
                y_test,
                predictions,
                average="macro",
                zero_division=0,
            )
        ),

        "recall_macro": float(
            recall_score(
                y_test,
                predictions,
                average="macro",
                zero_division=0,
            )
        ),

        "f1_macro": float(
            f1_score(
                y_test,
                predictions,
                average="macro",
                zero_division=0,
            )
        ),

        "confusion_matrix": (
            confusion_matrix(
                y_test,
                predictions,
                labels=labels,
            ).tolist()
        ),

        "classification_report": (
            classification_report(
                y_test,
                predictions,
                labels=labels,
                output_dict=True,
                zero_division=0,
            )
        ),

        "labels": labels,

        "predictions": predictions.tolist(),
    }


# ============================================================
# RANDOM FOREST
# ============================================================

def _train_random_forest(
    x_train: np.ndarray,
    y_train: np.ndarray,
    config: MLConfig,
):

    from sklearn.ensemble import (
        RandomForestClassifier,
    )

    model = RandomForestClassifier(
        n_estimators=config.n_estimators,
        max_depth=config.max_depth,
        min_samples_leaf=config.min_samples_leaf,
        random_state=config.random_state,
        n_jobs=-1,
        class_weight="balanced",
    )

    model.fit(
        x_train,
        y_train,
    )

    return model


# ============================================================
# XGBOOST
# ============================================================

def _train_xgboost(
    x_train: np.ndarray,
    y_train: np.ndarray,
    config: MLConfig,
):

    try:

        from xgboost import (
            XGBClassifier,
        )

    except ImportError as exc:

        raise ImportError(
            "XGBoost is required for the XGBoost model. "
            "Install it with:\n"
            "python -m pip install xgboost"
        ) from exc

    classes = sorted(
        np.unique(
            y_train
        ).tolist()
    )

    class_to_int = {
        label: index
        for index, label
        in enumerate(classes)
    }

    y_encoded = np.asarray(
        [
            class_to_int[label]
            for label in y_train
        ],
        dtype=np.int64,
    )

    model = XGBClassifier(
        n_estimators=config.xgb_n_estimators,
        max_depth=config.xgb_max_depth,
        learning_rate=config.xgb_learning_rate,
        subsample=config.xgb_subsample,
        colsample_bytree=config.xgb_colsample_bytree,
        random_state=config.random_state,
        objective="multi:softprob",
        eval_metric="mlogloss",
        n_jobs=-1,
    )

    model.fit(
        x_train,
        y_encoded,
    )

    return model, class_to_int


# ============================================================
# MAIN ML PIPELINE
# ============================================================

def run_ml(
    pca_coordinates_path: str | Path,
    immune_scores_path: str | Path,
    cell_states_path: str | Path,
    output_dir: str | Path,
    config: MLConfig | None = None,
) -> dict[str, Any]:

    if config is None:
        config = MLConfig()

    output_dir = Path(
        output_dir
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------------------------------
    # LOAD INPUTS
    # --------------------------------------------------------

    pca_coordinates = _load_numpy(
        pca_coordinates_path
    )

    immune_scores = _load_numpy(
        immune_scores_path
    )

    cell_state_data = _load_json(
        cell_states_path
    )

    # --------------------------------------------------------
    # EXTRACT CELL STATES
    # --------------------------------------------------------

    if isinstance(
        cell_state_data,
        dict,
    ):

        if "cells" in cell_state_data:

            cell_states = cell_state_data[
                "cells"
            ]

        elif "cell_states" in cell_state_data:

            cell_states = cell_state_data[
                "cell_states"
            ]

        else:

            raise ValueError(
                "Could not find cell-state list in "
                "cell immune-state JSON."
            )

    else:

        cell_states = cell_state_data

    # --------------------------------------------------------
    # BUILD COMPLETE FEATURE MATRIX
    # --------------------------------------------------------

    full_features = _build_feature_matrix(
        pca_coordinates,
        immune_scores,
    )

    input_cells = full_features.shape[0]

    # --------------------------------------------------------
    # PREPARE LABELS
    # --------------------------------------------------------

    labels, class_distribution, keep_mask = (
        _prepare_labels(
            cell_states,
            config.minimum_class_size,
        )
    )

    if len(cell_states) != input_cells:

        raise ValueError(
            "Cell-state labels do not match feature matrix. "
            f"Features: {input_cells}, "
            f"labels: {len(cell_states)}"
        )

    # --------------------------------------------------------
    # FILTER FEATURES TO VALID CLASSES
    # --------------------------------------------------------

    features = full_features[
        keep_mask
    ]

    usable_cells = features.shape[0]

    if usable_cells != len(labels):

        raise RuntimeError(
            "Filtered feature matrix and labels "
            "have inconsistent dimensions."
        )

    # --------------------------------------------------------
    # FEATURE NAMES
    # --------------------------------------------------------

    feature_names = [

        f"PC{i + 1}"

        for i in range(
            pca_coordinates.shape[1]
        )
    ]

    immune_score_names = [

        f"immune_score_{i + 1}"

        for i in range(
            immune_scores.shape[1]
        )
    ]

    feature_names.extend(
        immune_score_names
    )

    if len(feature_names) != features.shape[1]:

        raise RuntimeError(
            "Feature-name count does not match "
            "feature matrix dimensions."
        )

    # --------------------------------------------------------
    # SAVE FEATURES FOR DOWNSTREAM XAI
    # --------------------------------------------------------

    features_output = (
        output_dir
        / "ml_features.npy"
    )

    np.save(
        features_output,
        features,
    )

    # --------------------------------------------------------
    # SAVE LABELS USED BY ML
    # --------------------------------------------------------

    labels_output = (
        output_dir
        / "ml_labels.npy"
    )

    np.save(
        labels_output,
        labels,
    )

    # --------------------------------------------------------
    # SAVE FEATURE NAMES
    # --------------------------------------------------------

    feature_names_output = (
        output_dir
        / "feature_names.json"
    )

    _save_json(
        feature_names_output,
        feature_names,
    )

    # --------------------------------------------------------
    # TRAIN / TEST SPLIT
    # --------------------------------------------------------

    from sklearn.model_selection import (
        train_test_split,
    )

    x_train, x_test, y_train, y_test = (
        train_test_split(
            features,
            labels,
            test_size=config.test_size,
            random_state=config.random_state,
            stratify=labels,
        )
    )

    # --------------------------------------------------------
    # RANDOM FOREST
    # --------------------------------------------------------

    rf_model = _train_random_forest(
        x_train,
        y_train,
        config,
    )

    rf_evaluation = _evaluate_model(
        rf_model,
        x_test,
        y_test,
    )

    rf_model_path = (
        output_dir
        / "random_forest.pkl"
    )

    with open(
        rf_model_path,
        "wb",
    ) as handle:

        pickle.dump(
            rf_model,
            handle,
        )

    # --------------------------------------------------------
    # RANDOM FOREST PREDICTIONS
    # --------------------------------------------------------
    #
    # IMPORTANT:
    # Save predictions for ALL usable cells.
    #
    # This makes predictions row-aligned with
    # ml_features.npy and therefore suitable
    # for downstream XAI.
    # --------------------------------------------------------

    rf_all_predictions = np.asarray(
        rf_model.predict(
            features
        ),
        dtype=str,
    )

    if rf_all_predictions.shape[0] != usable_cells:

        raise RuntimeError(
            "Random Forest prediction count does not "
            "match the number of ML feature rows."
        )

    rf_predictions_path = (
        output_dir
        / "random_forest_predictions.npy"
    )

    np.save(
        rf_predictions_path,
        rf_all_predictions,
    )

    # --------------------------------------------------------
    # FEATURE IMPORTANCE
    # --------------------------------------------------------

    rf_importances = (
        rf_model.feature_importances_
    )

    feature_importance = {

        feature_names[index]: float(value)

        for index, value
        in enumerate(
            rf_importances
        )
    }

    feature_importance_path = (
        output_dir
        / "feature_importance.json"
    )

    _save_json(
        feature_importance_path,
        feature_importance,
    )

    # --------------------------------------------------------
    # XGBOOST
    # --------------------------------------------------------

    xgb_evaluation = None
    xgb_model_path = None
    xgb_class_mapping = None

    try:

        xgb_model, xgb_class_mapping = (
            _train_xgboost(
                x_train,
                y_train,
                config,
            )
        )

        encoded_predictions = (
            xgb_model.predict(
                x_test
            )
        )

        int_to_class = {
            value: key
            for key, value
            in xgb_class_mapping.items()
        }

        xgb_predictions = np.asarray(
            [
                int_to_class[
                    int(value)
                ]
                for value in encoded_predictions
            ],
            dtype=str,
        )

        from sklearn.metrics import (
            accuracy_score,
            balanced_accuracy_score,
            classification_report,
            confusion_matrix,
            f1_score,
            precision_score,
            recall_score,
        )

        evaluation_labels = sorted(
            np.unique(
                np.concatenate(
                    [
                        y_test,
                        xgb_predictions,
                    ]
                )
            ).tolist()
        )

        xgb_evaluation = {

            "accuracy": float(
                accuracy_score(
                    y_test,
                    xgb_predictions,
                )
            ),

            "balanced_accuracy": float(
                balanced_accuracy_score(
                    y_test,
                    xgb_predictions,
                )
            ),

            "precision_macro": float(
                precision_score(
                    y_test,
                    xgb_predictions,
                    average="macro",
                    zero_division=0,
                )
            ),

            "recall_macro": float(
                recall_score(
                    y_test,
                    xgb_predictions,
                    average="macro",
                    zero_division=0,
                )
            ),

            "f1_macro": float(
                f1_score(
                    y_test,
                    xgb_predictions,
                    average="macro",
                    zero_division=0,
                )
            ),

            "confusion_matrix": (
                confusion_matrix(
                    y_test,
                    xgb_predictions,
                    labels=evaluation_labels,
                ).tolist()
            ),

            "classification_report": (
                classification_report(
                    y_test,
                    xgb_predictions,
                    labels=evaluation_labels,
                    output_dict=True,
                    zero_division=0,
                )
            ),

            "labels": evaluation_labels,

            "predictions": (
                xgb_predictions.tolist()
            ),
        }

        xgb_model_path = (
            output_dir
            / "xgboost.pkl"
        )

        with open(
            xgb_model_path,
            "wb",
        ) as handle:

            pickle.dump(
                xgb_model,
                handle,
            )

    except ImportError:

        xgb_evaluation = {
            "available": False,
            "reason": "XGBoost is not installed.",
        }

    # --------------------------------------------------------
    # EVALUATION
    # --------------------------------------------------------

    evaluation = {

        "random_forest": rf_evaluation,

        "xgboost": xgb_evaluation,
    }

    evaluation_path = (
        output_dir
        / "evaluation.json"
    )

    _save_json(
        evaluation_path,
        evaluation,
    )

    # --------------------------------------------------------
    # METADATA
    # --------------------------------------------------------

    metadata = {

        "method": (
            "Immune-state classification using "
            "PCA coordinates and immune-state scores"
        ),

        "input_cells": int(
            input_cells
        ),

        "usable_cells": int(
            usable_cells
        ),

        "excluded_cells": int(
            input_cells - usable_cells
        ),

        "pca_components": int(
            pca_coordinates.shape[1]
        ),

        "immune_scores": int(
            immune_scores.shape[1]
        ),

        "feature_count": int(
            features.shape[1]
        ),

        "class_distribution": (
            class_distribution
        ),

        "test_size": float(
            config.test_size
        ),

        "random_state": int(
            config.random_state
        ),

        "feature_names": feature_names,

        "models": [
            "random_forest",
            "xgboost",
        ],

        "primary_model": config.primary_model,

        "random_forest_model": str(
            rf_model_path
        ),

        "xgboost_model": (
            str(xgb_model_path)
            if xgb_model_path
            else None
        ),

        "ml_features": str(
            features_output
        ),

        "ml_labels": str(
            labels_output
        ),

        "feature_names_output": str(
            feature_names_output
        ),

        "predictions_output": str(
            rf_predictions_path
        ),

        "evaluation": str(
            evaluation_path
        ),

        "feature_importance": str(
            feature_importance_path
        ),
    }

    metadata_path = (
        output_dir
        / "ml_metadata.json"
    )

    _save_json(
        metadata_path,
        metadata,
    )

    # --------------------------------------------------------
    # RESULT
    # --------------------------------------------------------

    return {

        "input_cells": int(
            input_cells
        ),

        "usable_cells": int(
            usable_cells
        ),

        "excluded_cells": int(
            input_cells - usable_cells
        ),

        "feature_count": int(
            features.shape[1]
        ),

        "class_distribution": (
            class_distribution
        ),

        "random_forest": rf_evaluation,

        "xgboost": xgb_evaluation,

        "model_output": str(
            rf_model_path
        ),

        "features_output": str(
            features_output
        ),

        "labels_output": str(
            labels_output
        ),

        "predictions_output": str(
            rf_predictions_path
        ),

        "feature_names_output": str(
            feature_names_output
        ),

        "evaluation_output": str(
            evaluation_path
        ),

        "feature_importance_output": str(
            feature_importance_path
        ),

        "metadata_output": str(
            metadata_path
        ),
    }