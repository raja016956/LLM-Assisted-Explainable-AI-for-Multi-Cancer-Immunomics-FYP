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
class ImmuneStateAssignmentConfig:
    """
    Evidence-aware immune-state assignment.

    States:
        - Inflamed
        - Immune-Excluded
        - Immune-Suppressed
        - Myeloid-Dominant
        - Immune-Active
        - Unclassified

    The classifier is intentionally conservative:
        insufficient evidence is preferred over unsupported
        biological interpretation.
    """

    # Minimum number of detectable signatures required
    # before attempting a biological state assignment.
    minimum_supported_signatures: int = 2

    # Minimum score considered biologically detectable.
    minimum_signal: float = 0.005

    # Minimum dominance required for myeloid interpretation.
    dominance_ratio: float = 1.25

    # Minimum dominance required for suppression.
    suppression_ratio: float = 1.25

    # Minimum relative inflammatory contribution.
    inflammatory_ratio: float = 1.15

    # Minimum antigen-presentation signal.
    antigen_presentation_threshold: float = 0.01

    # Minimum fraction of cells required for a cluster-level
    # state to be considered representative.
    cluster_min_fraction: float = 0.50

    # Minimum confidence before reporting a non-insufficient
    # cluster state.
    cluster_min_confidence: float = 0.50


# ============================================================
# CONSTANTS
# ============================================================

REQUIRED_SCORE_NAMES = [
    "t_cell_activity",
    "cytotoxic_activity",
    "myeloid_signal",
    "immune_suppression",
    "inflammatory_signal",
    "antigen_presentation",
]


# ============================================================
# FILE HELPERS
# ============================================================

def _load_json(path: Path) -> Any:

    if not path.exists():
        raise FileNotFoundError(
            f"Metadata file not found: {path}"
        )

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as handle:

        return json.load(handle)


def _load_score_names(
    path: Path,
) -> list[str]:

    data = _load_json(path)

    if not isinstance(data, list):
        raise ValueError(
            "score_names.json must contain a JSON list."
        )

    score_names = [
        str(name)
        for name in data
    ]

    if not score_names:
        raise ValueError(
            "score_names.json is empty."
        )

    return score_names


def _load_cluster_labels(
    path: Path,
) -> np.ndarray:

    if not path.exists():
        raise FileNotFoundError(
            f"Cluster labels not found: {path}"
        )

    labels = np.load(path)

    if labels.ndim != 1:
        raise ValueError(
            "Cluster labels must be a 1-dimensional array."
        )

    if labels.size == 0:
        raise ValueError(
            "Cluster labels are empty."
        )

    return labels


def _load_scores(
    path: Path,
) -> np.ndarray:

    if not path.exists():
        raise FileNotFoundError(
            f"Immune score matrix not found: {path}"
        )

    scores = np.load(path)

    if scores.ndim != 2:
        raise ValueError(
            "Immune score matrix must be 2-dimensional."
        )

    if scores.shape[0] == 0:
        raise ValueError(
            "Immune score matrix contains no cells."
        )

    if not np.all(
        np.isfinite(scores)
    ):
        raise ValueError(
            "Immune score matrix contains non-finite values."
        )

    return np.asarray(
        scores,
        dtype=np.float64,
    )


# ============================================================
# NUMERICAL HELPERS
# ============================================================

def _safe_ratio(
    numerator: float,
    denominator: float,
) -> float:

    denominator = max(
        float(denominator),
        1e-12,
    )

    return float(
        numerator / denominator
    )


def _clip_confidence(
    value: float,
) -> float:

    return float(
        np.clip(
            value,
            0.0,
            1.0,
        )
    )


def _supported_signature_count(
    scores: dict[str, float],
    config: ImmuneStateAssignmentConfig,
) -> int:

    return int(
        sum(
            value >= config.minimum_signal
            for value in scores.values()
        )
    )


# ============================================================
# CELL-LEVEL ASSIGNMENT
# ============================================================

def _assign_cell_state(
    scores: dict[str, float],
    config: ImmuneStateAssignmentConfig,
) -> tuple[str, float, str]:

    t_cell = max(
        0.0,
        float(
            scores["t_cell_activity"]
        ),
    )

    cytotoxic = max(
        0.0,
        float(
            scores["cytotoxic_activity"]
        ),
    )

    myeloid = max(
        0.0,
        float(
            scores["myeloid_signal"]
        ),
    )

    suppression = max(
        0.0,
        float(
            scores["immune_suppression"]
        ),
    )

    inflammatory = max(
        0.0,
        float(
            scores["inflammatory_signal"]
        ),
    )

    antigen = max(
        0.0,
        float(
            scores["antigen_presentation"]
        ),
    )

    # --------------------------------------------------------
    # SUPPORTED SIGNATURES
    # --------------------------------------------------------

    supported = _supported_signature_count(
        {
            "t_cell_activity": t_cell,
            "cytotoxic_activity": cytotoxic,
            "myeloid_signal": myeloid,
            "immune_suppression": suppression,
            "inflammatory_signal": inflammatory,
            "antigen_presentation": antigen,
        },
        config,
    )

    if (
        supported
        < config.minimum_supported_signatures
    ):

        return (
            "Unclassified",
            0.0,
            "Too few immune signatures exceed the minimum signal threshold.",
        )

    # --------------------------------------------------------
    # ADAPTIVE ACTIVITY
    # --------------------------------------------------------

    adaptive_activity = (
        t_cell
        + cytotoxic
    ) / 2.0

    # --------------------------------------------------------
    # INFLAMMATORY / ANTIGEN ACTIVITY
    # --------------------------------------------------------

    inflammatory_activity = (
        inflammatory
        + antigen
    ) / 2.0

    # --------------------------------------------------------
    # TOTAL IMMUNE ACTIVITY
    # --------------------------------------------------------

    immune_activity = (
        t_cell
        + cytotoxic
        + inflammatory
        + antigen
    ) / 4.0

    # ========================================================
    # IMMUNE-SUPPRESSED
    # ========================================================

    if (
        suppression
        >= config.minimum_signal
        and suppression
        >= immune_activity
        * config.suppression_ratio
    ):

        competing = max(
            adaptive_activity,
            inflammatory_activity,
            myeloid,
            config.minimum_signal,
        )

        confidence = _safe_ratio(
            suppression,
            competing,
        )

        confidence = _clip_confidence(
            (confidence - 1.0)
            / max(
                config.suppression_ratio,
                1e-12,
            )
        )

        return (
            "Immune-Suppressed",
            confidence,
            "Immune-suppression signal dominates the broader immune-associated activity.",
        )

    # ========================================================
    # MYELOID-DOMINANT
    # ========================================================

    adaptive_or_inflammatory = max(
        t_cell,
        cytotoxic,
        inflammatory,
        antigen,
    )

    if (
        myeloid
        >= config.minimum_signal
        and myeloid
        >= adaptive_or_inflammatory
        * config.dominance_ratio
    ):

        confidence = _safe_ratio(
            myeloid,
            max(
                adaptive_or_inflammatory,
                config.minimum_signal,
            ),
        )

        confidence = _clip_confidence(
            (confidence - 1.0)
            / max(
                config.dominance_ratio,
                1e-12,
            )
        )

        return (
            "Myeloid-Dominant",
            confidence,
            "Myeloid-associated signal is dominant among the available immune signatures.",
        )

    # ========================================================
    # INFLAMED
    # ========================================================

    adaptive_detected = (
        adaptive_activity
        >= config.minimum_signal
    )

    inflammatory_detected = (
        inflammatory
        >= config.minimum_signal
    )

    antigen_detected = (
        antigen
        >= config.antigen_presentation_threshold
    )

    inflammatory_support = (
        inflammatory_detected
        or antigen_detected
    )

    if (
        adaptive_detected
        and inflammatory_support
    ):

        adaptive_strength = adaptive_activity

        inflammatory_strength = max(
            inflammatory,
            antigen,
        )

        if (
            inflammatory_strength
            >= adaptive_strength
            * config.inflammatory_ratio
            or antigen_detected
        ):

            confidence = _safe_ratio(
                inflammatory_strength,
                max(
                    adaptive_strength,
                    config.minimum_signal,
                ),
            )

            confidence = _clip_confidence(
                (
                    confidence
                    - 1.0
                )
                / max(
                    config.inflammatory_ratio,
                    1e-12,
                )
            )

            return (
                "Inflamed",
                confidence,
                "Adaptive immune activity is accompanied by inflammatory or antigen-presentation activity.",
            )

    # ========================================================
    # IMMUNE-EXCLUDED
    # ========================================================

    if (
        myeloid
        >= config.minimum_signal
        and adaptive_activity
        < config.minimum_signal
        and cytotoxic
        < config.minimum_signal
    ):

        confidence = _safe_ratio(
            myeloid,
            max(
                adaptive_activity,
                config.minimum_signal,
            ),
        )

        confidence = _clip_confidence(
            min(
                1.0,
                (
                    confidence
                    - 1.0
                )
                / max(
                    config.dominance_ratio,
                    1e-12,
                ),
            )
        )

        return (
            "Immune-Excluded",
            confidence,
            "Myeloid-associated activity is present without detectable adaptive or cytotoxic activity.",
        )

    # ========================================================
    # IMMUNE-ACTIVE
    # ========================================================

    adaptive_detected = (
        adaptive_activity
        >= config.minimum_signal
    )

    antigen_or_inflammation = (
        inflammatory
        >= config.minimum_signal
        or antigen
        >= config.antigen_presentation_threshold
    )

    immune_components = int(
        adaptive_detected
    ) + int(
        antigen_or_inflammation
    ) + int(
        myeloid
        >= config.minimum_signal
    )

    if (
        immune_activity
        >= config.minimum_signal
        and immune_components
        >= 2
    ):

        competing = max(
            suppression,
            myeloid,
            config.minimum_signal,
        )

        relative_strength = _safe_ratio(
            immune_activity,
            competing,
        )

        confidence = _clip_confidence(
            min(
                1.0,
                relative_strength
                / 2.0,
            )
        )

        return (
            "Immune-Active",
            confidence,
            "Multiple immune-associated signatures are detectable without a stronger competing state.",
        )

    # ========================================================
    # INSUFFICIENT EVIDENCE
    # ========================================================

    return (
        "Unclassified",
        0.0,
        "Available immune signatures do not provide sufficient evidence for a specific immune-state assignment.",
    )


# ============================================================
# CLUSTER-LEVEL ASSIGNMENT
# ============================================================

def _assign_cluster_state(
    cluster_state_counts: dict[str, int],
    cluster_size: int,
    cluster_mean_scores: dict[str, float],
    config: ImmuneStateAssignmentConfig,
) -> tuple[str, float, str]:

    if cluster_size <= 0:

        return (
            "Unclassified",
            0.0,
            "Cluster contains no cells.",
        )

    # --------------------------------------------------------
    # NORMALIZE COUNTS
    # --------------------------------------------------------

    fractions = {
        state: count / cluster_size
        for state, count
        in cluster_state_counts.items()
    }

    # --------------------------------------------------------
    # IGNORE INSUFFICIENT EVIDENCE WHEN SEARCHING FOR
    # BIOLOGICALLY SUPPORTED STATES.
    # --------------------------------------------------------

    supported_states = {
        state: fraction
        for state, fraction
        in fractions.items()
        if (
            state != "Unclassified"
            and fraction > 0.0
        )
    }

    # --------------------------------------------------------
    # NO SUPPORTED CELL-LEVEL STATE
    # --------------------------------------------------------

    if not supported_states:

        return (
            "Unclassified",
            0.0,
            "No cells in this cluster provide sufficient evidence for a specific immune-state assignment.",
        )

    # --------------------------------------------------------
    # FIND MOST REPRESENTATIVE CELL STATE
    # --------------------------------------------------------

    dominant_state = max(
        supported_states,
        key=supported_states.get,
    )

    dominant_fraction = float(
        supported_states[
            dominant_state
        ]
    )

    # --------------------------------------------------------
    # IMPORTANT SAFETY RULE:
    #
    # A cluster state cannot be stronger than the actual
    # cell-level evidence supporting it.
    # --------------------------------------------------------

    if (
        dominant_fraction
        < config.cluster_min_fraction
    ):

        return (
            "Unclassified",
            dominant_fraction,
            (
                "No specific immune state is represented by "
                "enough cells in the cluster to support a "
                "cluster-level assignment."
            ),
        )

    # --------------------------------------------------------
    # RECHECK CLUSTER MEAN SCORES
    #
    # This prevents a state from being assigned purely from
    # a few cells when the aggregate cluster signal does not
    # support it.
    # --------------------------------------------------------

    mean_state, mean_confidence, mean_reason = (
        _assign_cell_state(
            cluster_mean_scores,
            config,
        )
    )

    # --------------------------------------------------------
    # IF THE CLUSTER MEAN DOES NOT SUPPORT THE DOMINANT
    # CELL STATE, BE CONSERVATIVE.
    # --------------------------------------------------------

    if (
        mean_state
        != dominant_state
    ):

        # Insufficient mean evidence should not override a
        # strong and coherent cell-level state completely,
        # but it should lower confidence.

        if (
            mean_state
            == "Unclassified"
        ):

            confidence = (
                dominant_fraction
                * 0.75
            )

            if (
                confidence
                < config.cluster_min_confidence
            ):

                return (
                    "Unclassified",
                    confidence,
                    (
                        "The dominant cell-level state is "
                        "not sufficiently supported by the "
                        "cluster-level aggregate signal."
                    ),
                )

            return (
                dominant_state,
                confidence,
                (
                    "The dominant cell-level state is "
                    "supported by a majority of cells, "
                    "although aggregate cluster-level signal "
                    "is limited."
                ),
            )

        # Conflicting biological interpretations:
        return (
            "Unclassified",
            dominant_fraction,
            (
                "Cell-level and aggregate cluster-level "
                "immune-state evidence are inconsistent; "
                "the cluster is therefore reported "
                "conservatively."
            ),
        )

    # --------------------------------------------------------
    # FINAL CLUSTER CONFIDENCE
    # --------------------------------------------------------

    confidence = (
        0.70 * dominant_fraction
        + 0.30 * mean_confidence
    )

    confidence = _clip_confidence(
        confidence
    )

    if (
        confidence
        < config.cluster_min_confidence
    ):

        return (
            "Unclassified",
            confidence,
            (
                "Cluster-level confidence is below the "
                "minimum threshold for a specific "
                "immune-state assignment."
            ),
        )

    return (
        dominant_state,
        confidence,
        (
            f"{dominant_state} is the dominant cell-level "
            f"state and is supported by the aggregate "
            f"cluster-level immune scores."
        ),
    )


# ============================================================
# MAIN PIPELINE
# ============================================================

def run_immune_state_assignment(
    immune_scores_path: str | Path,
    score_names_path: str | Path,
    cluster_labels_path: str | Path,
    output_dir: str | Path,
    config: ImmuneStateAssignmentConfig | None = None,
) -> dict[str, Any]:

    if config is None:
        config = ImmuneStateAssignmentConfig()

    immune_scores_path = Path(
        immune_scores_path
    )

    score_names_path = Path(
        score_names_path
    )

    cluster_labels_path = Path(
        cluster_labels_path
    )

    output_dir = Path(
        output_dir
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    # ========================================================
    # LOAD INPUTS
    # ========================================================

    scores = _load_scores(
        immune_scores_path
    )

    score_names = _load_score_names(
        score_names_path
    )

    cluster_labels = _load_cluster_labels(
        cluster_labels_path
    )

    # ========================================================
    # VALIDATE DIMENSIONS
    # ========================================================

    if (
        scores.shape[1]
        != len(score_names)
    ):

        raise ValueError(
            "Immune score matrix does not match "
            "score_names metadata. "
            f"Scores: {scores.shape[1]}, "
            f"Names: {len(score_names)}"
        )

    if (
        scores.shape[0]
        != cluster_labels.shape[0]
    ):

        raise ValueError(
            "Immune scores do not match "
            "cluster labels. "
            f"Score cells: {scores.shape[0]}, "
            f"Labels: {cluster_labels.shape[0]}"
        )

    # ========================================================
    # SCORE INDEX
    # ========================================================

    score_index = {
        name: index
        for index, name
        in enumerate(score_names)
    }

    missing_scores = [
        name
        for name in REQUIRED_SCORE_NAMES
        if name not in score_index
    ]

    if missing_scores:

        raise ValueError(
            "Required immune scores are missing: "
            + ", ".join(
                missing_scores
            )
        )

    # ========================================================
    # CELL-LEVEL ASSIGNMENT
    # ========================================================

    cell_assignments = []

    state_counts: dict[str, int] = {}

    for cell_index in range(
        scores.shape[0]
    ):

        cell_vector = scores[
            cell_index
        ]

        cell_scores = {
            name: float(
                cell_vector[
                    score_index[name]
                ]
            )
            for name in REQUIRED_SCORE_NAMES
        }

        state, confidence, reason = (
            _assign_cell_state(
                cell_scores,
                config,
            )
        )

        state_counts[state] = (
            state_counts.get(
                state,
                0,
            )
            + 1
        )

        cell_assignments.append(
            {
                "cell_index": int(
                    cell_index
                ),
                "cluster": int(
                    cluster_labels[
                        cell_index
                    ]
                ),
                "state": state,
                "confidence": float(
                    confidence
                ),
                "reason": reason,
                "scores": cell_scores,
            }
        )

    # ========================================================
    # CLUSTER-LEVEL ASSIGNMENT
    # ========================================================

    cluster_assignments = {}

    unique_clusters = np.unique(
        cluster_labels
    )

    for cluster in unique_clusters:

        cluster_id = str(
            int(cluster)
        )

        indices = np.where(
            cluster_labels
            == cluster
        )[0]

        cluster_matrix = scores[
            indices
        ]

        # ----------------------------------------------------
        # MEAN SCORE VECTOR
        # ----------------------------------------------------

        mean_scores = {
            name: float(
                np.mean(
                    cluster_matrix[
                        :,
                        score_index[name],
                    ]
                )
            )
            for name in REQUIRED_SCORE_NAMES
        }

        # ----------------------------------------------------
        # CELL-LEVEL STATE DISTRIBUTION
        # ----------------------------------------------------

        cluster_state_counts: dict[
            str,
            int,
        ] = {}

        for index in indices:

            cell_state = (
                cell_assignments[
                    int(index)
                ]["state"]
            )

            cluster_state_counts[
                cell_state
            ] = (
                cluster_state_counts.get(
                    cell_state,
                    0,
                )
                + 1
            )

        # ----------------------------------------------------
        # CLUSTER ASSIGNMENT
        # ----------------------------------------------------

        state, confidence, reason = (
            _assign_cluster_state(
                cluster_state_counts,
                len(indices),
                mean_scores,
                config,
            )
        )

        # ----------------------------------------------------
        # DOMINANT CELL STATE
        # ----------------------------------------------------

        dominant_state = max(
            cluster_state_counts,
            key=cluster_state_counts.get,
        )

        dominant_fraction = (
            cluster_state_counts[
                dominant_state
            ]
            / len(indices)
        )

        # ----------------------------------------------------
        # SAVE
        # ----------------------------------------------------

        cluster_assignments[
            cluster_id
        ] = {

            "cluster": int(
                cluster
            ),

            "n_cells": int(
                len(indices)
            ),

            "state": state,

            "dominant_cell_state":
                dominant_state,

            "dominant_cell_fraction":
                float(
                    dominant_fraction
                ),

            "confidence":
                float(
                    confidence
                ),

            "reason":
                reason,

            "mean_scores":
                mean_scores,

            "cell_state_distribution": {
                key: int(value)
                for key, value
                in cluster_state_counts.items()
            },
        }

    # ========================================================
    # SAVE CELL ASSIGNMENTS
    # ========================================================

    cell_output = (
        output_dir
        / "cell_immune_states.json"
    )

    with open(
        cell_output,
        "w",
        encoding="utf-8",
    ) as handle:

        json.dump(
            {
                "n_cells": int(
                    scores.shape[0]
                ),
                "states": state_counts,
                "cells": cell_assignments,
            },
            handle,
            indent=2,
        )

    # ========================================================
    # SAVE CLUSTER ASSIGNMENTS
    # ========================================================

    cluster_output = (
        output_dir
        / "cluster_immune_states.json"
    )

    with open(
        cluster_output,
        "w",
        encoding="utf-8",
    ) as handle:

        json.dump(
            {
                "n_clusters": int(
                    len(unique_clusters)
                ),
                "clusters":
                    cluster_assignments,
            },
            handle,
            indent=2,
        )

    # ========================================================
    # SAVE STATE DISTRIBUTION
    # ========================================================

    distribution_output = (
        output_dir
        / "state_distribution.json"
    )

    with open(
        distribution_output,
        "w",
        encoding="utf-8",
    ) as handle:

        json.dump(
            state_counts,
            handle,
            indent=2,
        )

    # ========================================================
    # SAVE SUMMARY
    # ========================================================

    summary_output = (
        output_dir
        / "assignment_summary.json"
    )

    summary = {

        "input_cells":
            int(
                scores.shape[0]
            ),

        "input_scores":
            int(
                scores.shape[1]
            ),

        "clusters":
            int(
                len(unique_clusters)
            ),

        "states":
            state_counts,

        "configuration": {

            "minimum_supported_signatures":
                int(
                    config.minimum_supported_signatures
                ),

            "minimum_signal":
                float(
                    config.minimum_signal
                ),

            "dominance_ratio":
                float(
                    config.dominance_ratio
                ),

            "suppression_ratio":
                float(
                    config.suppression_ratio
                ),

            "inflammatory_ratio":
                float(
                    config.inflammatory_ratio
                ),

            "antigen_presentation_threshold":
                float(
                    config.antigen_presentation_threshold
                ),

            "cluster_min_fraction":
                float(
                    config.cluster_min_fraction
                ),

            "cluster_min_confidence":
                float(
                    config.cluster_min_confidence
                ),
        },

        "outputs": {

            "cell_assignments":
                str(
                    cell_output
                ),

            "cluster_assignments":
                str(
                    cluster_output
                ),

            "state_distribution":
                str(
                    distribution_output
                ),
        },
    }

    with open(
        summary_output,
        "w",
        encoding="utf-8",
    ) as handle:

        json.dump(
            summary,
            handle,
            indent=2,
        )

    # ========================================================
    # RESULT
    # ========================================================

    return {

        "input_cells":
            int(
                scores.shape[0]
            ),

        "input_scores":
            int(
                scores.shape[1]
            ),

        "n_clusters":
            int(
                len(unique_clusters)
            ),

        "state_distribution":
            state_counts,

        "cell_output":
            str(
                cell_output
            ),

        "cluster_output":
            str(
                cluster_output
            ),

        "distribution_output":
            str(
                distribution_output
            ),

        "summary_output":
            str(
                summary_output
            ),
    }