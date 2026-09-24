from __future__ import annotations

from pathlib import Path
import json
from typing import Any

import numpy as np


# ============================================================
# HELPERS
# ============================================================

# Handles the  load json step that combines the completed analysis outputs.
def _load_json(path: Path, description: str) -> Any:

    if not path.exists():
        raise FileNotFoundError(
            f"{description} not found: {path}"
        )

    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


# Handles the  load numpy step that combines the completed analysis outputs.
def _load_numpy(path: Path, description: str) -> np.ndarray:

    if not path.exists():
        raise FileNotFoundError(
            f"{description} not found: {path}"
        )

    array = np.load(path)

    if not np.all(np.isfinite(array)):
        raise ValueError(
            f"{description} contains non-finite values."
        )

    return array


# ============================================================
# CELL STATE EXTRACTION
# ============================================================

# Handles the  extract cell states step that combines the completed analysis outputs.
def _extract_cell_states(data: Any) -> list[dict[str, Any]]:

    # --------------------------------------------------------
    # Current immune_state_assignment format
    #
    # {
    #     "n_cells": 913,
    #     "states": {...},
    #     "cells": [...]
    # }
    # --------------------------------------------------------

    if isinstance(data, dict):

        if "cells" in data:

            cells = data["cells"]

            if not isinstance(cells, list):
                raise ValueError(
                    "'cells' must contain a list."
                )

            return cells

        # ----------------------------------------------------
        # Alternative supported format
        # ----------------------------------------------------

        if "cell_states" in data:

            cells = data["cell_states"]

            if not isinstance(cells, list):
                raise ValueError(
                    "'cell_states' must contain a list."
                )

            return cells

    # --------------------------------------------------------
    # Direct list format
    # --------------------------------------------------------

    if isinstance(data, list):
        return data

    raise ValueError(
        "Unsupported cell immune-state JSON format. "
        "Expected a dictionary containing 'cells' "
        "or 'cell_states', or a direct list."
    )


# ============================================================
# STATE SUMMARY
# ============================================================

# Handles the  build state summary step that combines the completed analysis outputs.
def _build_state_summary(
    cell_states: list[dict[str, Any]],
) -> dict[str, Any]:

    counts: dict[str, int] = {}

    confidence_sum: dict[str, float] = {}

    confidence_count: dict[str, int] = {}

    for cell in cell_states:

        state = str(
            cell.get(
                "state",
                "Unknown",
            )
        )

        confidence = float(
            cell.get(
                "confidence",
                0.0,
            )
        )

        counts[state] = (
            counts.get(state, 0) + 1
        )

        confidence_sum[state] = (
            confidence_sum.get(state, 0.0)
            + confidence
        )

        confidence_count[state] = (
            confidence_count.get(state, 0)
            + 1
        )

    summary = {}

    for state, count in counts.items():

        mean_confidence = (
            confidence_sum[state]
            / confidence_count[state]
        )

        summary[state] = {
            "cell_count": int(count),
            "fraction": float(
                count / len(cell_states)
            ),
            "mean_confidence": float(
                mean_confidence
            ),
        }

    return summary


# ============================================================
# CLUSTER SUMMARY
# ============================================================

# Handles the  build cluster summary step that combines the completed analysis outputs.
def _build_cluster_summary(
    cell_states: list[dict[str, Any]],
) -> dict[str, Any]:

    clusters: dict[str, list[dict[str, Any]]] = {}

    for cell in cell_states:

        cluster = str(
            cell.get(
                "cluster",
                "unknown",
            )
        )

        clusters.setdefault(
            cluster,
            [],
        ).append(cell)

    result = {}

    for cluster, cells in clusters.items():

        state_counts: dict[str, int] = {}

        confidence_values = []

        for cell in cells:

            state = str(
                cell.get(
                    "state",
                    "Unknown",
                )
            )

            state_counts[state] = (
                state_counts.get(state, 0)
                + 1
            )

            confidence_values.append(
                float(
                    cell.get(
                        "confidence",
                        0.0,
                    )
                )
            )

        dominant_state = max(
            state_counts,
            key=state_counts.get,
        )

        result[cluster] = {
            "cluster": int(cluster)
            if cluster != "unknown"
            else cluster,

            "n_cells": len(cells),

            "dominant_state":
                dominant_state,

            "dominant_state_count":
                int(
                    state_counts[
                        dominant_state
                    ]
                ),

            "dominant_state_fraction":
                float(
                    state_counts[
                        dominant_state
                    ] / len(cells)
                ),

            "state_distribution": {
                key: int(value)
                for key, value
                in state_counts.items()
            },

            "mean_cell_confidence":
                float(
                    np.mean(
                        confidence_values
                    )
                ),
        }

    return result


# ============================================================
# LOAD CLUSTER STATES
# ============================================================

# Handles the  extract cluster states step that combines the completed analysis outputs.
def _extract_cluster_states(
    data: Any,
) -> dict[str, Any]:

    if isinstance(data, dict):

        if "clusters" in data:

            clusters = data["clusters"]

            if isinstance(
                clusters,
                dict,
            ):
                return clusters

        # Some possible formats
        if "cluster_states" in data:

            clusters = data["cluster_states"]

            if isinstance(
                clusters,
                dict,
            ):
                return clusters

    return {}


# ============================================================
# IMMUNE SCORE SUMMARY
# ============================================================

# Handles the  summarize scores step that combines the completed analysis outputs.
def _summarize_scores(
    scores: np.ndarray,
    score_names: list[str] | None = None,
) -> dict[str, Any]:

    if scores.ndim != 2:
        raise ValueError(
            "Immune score matrix must be 2-dimensional."
        )

    if score_names is None:

        score_names = [
            f"score_{i + 1}"
            for i in range(
                scores.shape[1]
            )
        ]

    if len(score_names) != scores.shape[1]:

        raise ValueError(
            "Number of score names does not "
            "match score matrix columns."
        )

    result = {}

    for index, name in enumerate(
        score_names
    ):

        values = scores[:, index]

        result[name] = {
            "mean": float(
                np.mean(values)
            ),
            "median": float(
                np.median(values)
            ),
            "std": float(
                np.std(values)
            ),
            "min": float(
                np.min(values)
            ),
            "max": float(
                np.max(values)
            ),
        }

    return result


# ============================================================
# PATHWAY SUMMARY
# ============================================================

# Handles the  summarize pathways step that combines the completed analysis outputs.
def _summarize_pathways(
    pathway_scores: np.ndarray,
    pathway_names: list[str],
) -> dict[str, Any]:

    if pathway_scores.ndim != 2:
        raise ValueError(
            "Pathway score matrix must be 2-dimensional."
        )

    if len(pathway_names) != pathway_scores.shape[1]:

        raise ValueError(
            "Number of pathway names does not "
            "match pathway score columns."
        )

    result = {}

    for index, pathway in enumerate(
        pathway_names
    ):

        values = pathway_scores[:, index]

        result[pathway] = {
            "mean": float(
                np.mean(values)
            ),
            "median": float(
                np.median(values)
            ),
            "std": float(
                np.std(values)
            ),
        }

    return result


# ============================================================
# MAIN PIPELINE
# ============================================================

# Handles the run final analysis step that combines the completed analysis outputs.
def run_final_analysis(
    cell_states_path: str | Path,
    cluster_states_path: str | Path,
    immune_scores_path: str | Path,
    immune_score_names_path: str | Path,
    ml_predictions_path: str | Path | None = None,
    pathway_scores_path: str | Path | None = None,
    pathway_names_path: str | Path | None = None,
    xai_global_importance_path: str | Path | None = None,
    output_dir: str | Path = "final_analysis",
) -> dict[str, Any]:

    cell_states_path = Path(
        cell_states_path
    )

    cluster_states_path = Path(
        cluster_states_path
    )

    immune_scores_path = Path(
        immune_scores_path
    )

    immune_score_names_path = Path(
        immune_score_names_path
    )

    output_dir = Path(
        output_dir
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    # ========================================================
    # LOAD IMMUNE STATES
    # ========================================================

    cell_state_data = _load_json(
        cell_states_path,
        "Cell immune-state file",
    )

    cell_states = _extract_cell_states(
        cell_state_data
    )

    if not cell_states:

        raise ValueError(
            "No cell immune-state assignments found."
        )

    # ========================================================
    # LOAD CLUSTER STATES
    # ========================================================

    cluster_state_data = _load_json(
        cluster_states_path,
        "Cluster immune-state file",
    )

    cluster_states = _extract_cluster_states(
        cluster_state_data
    )

    # ========================================================
    # LOAD IMMUNE SCORES
    # ========================================================

    immune_scores = _load_numpy(
        immune_scores_path,
        "Immune score matrix",
    )

    score_names = _load_json(
        immune_score_names_path,
        "Immune score names",
    )

    if isinstance(score_names, dict):

        if "score_names" in score_names:
            score_names = score_names[
                "score_names"
            ]

        elif "names" in score_names:
            score_names = score_names[
                "names"
            ]

        else:
            score_names = list(
                score_names.keys()
            )

    score_names = [
        str(name)
        for name in score_names
    ]

    if immune_scores.shape[0] != len(
        cell_states
    ):

        raise ValueError(
            "Cell-state count does not match "
            "immune-score matrix."
        )

    # ========================================================
    # BUILD SUMMARIES
    # ========================================================

    state_summary = _build_state_summary(
        cell_states
    )

    cluster_summary = _build_cluster_summary(
        cell_states
    )

    immune_score_summary = _summarize_scores(
        immune_scores,
        score_names,
    )

    # ========================================================
    # ML PREDICTIONS
    # ========================================================

    ml_summary = None

    if ml_predictions_path is not None:

        ml_predictions_path = Path(
            ml_predictions_path
        )

        if ml_predictions_path.exists():

            predictions = np.load(
                ml_predictions_path,
                allow_pickle=True,
            )

            predictions = predictions.tolist()

            prediction_counts: dict[
                str,
                int
            ] = {}

            for prediction in predictions:

                label = str(prediction)

                prediction_counts[label] = (
                    prediction_counts.get(
                        label,
                        0,
                    )
                    + 1
                )

            ml_summary = {
                "prediction_count":
                    len(predictions),

                "class_distribution":
                    prediction_counts,
            }

    # ========================================================
    # PATHWAY SCORES
    # ========================================================

    pathway_summary = None

    if (
        pathway_scores_path is not None
        and pathway_names_path is not None
    ):

        pathway_scores_path = Path(
            pathway_scores_path
        )

        pathway_names_path = Path(
            pathway_names_path
        )

        if (
            pathway_scores_path.exists()
            and pathway_names_path.exists()
        ):

            pathway_scores = _load_numpy(
                pathway_scores_path,
                "Pathway score matrix",
            )

            pathway_names = _load_json(
                pathway_names_path,
                "Pathway names",
            )

            pathway_summary = _summarize_pathways(
                pathway_scores,
                pathway_names,
            )

    # ========================================================
    # XAI
    # ========================================================

    xai_summary = None

    if (
        xai_global_importance_path
        is not None
    ):

        xai_path = Path(
            xai_global_importance_path
        )

        if xai_path.exists():

            xai_summary = _load_json(
                xai_path,
                "XAI feature importance",
            )

    # ========================================================
    # FINAL ANALYSIS PACKAGE
    # ========================================================

    final_analysis = {

        "pipeline": "IMMUNO-XAI",

        "purpose":
            "Integrated immune-state prediction "
            "and evidence package for downstream "
            "LLM biological reasoning.",

        "input_cells":
            int(len(cell_states)),

        "immune_state_summary":
            state_summary,

        "cluster_summary":
            cluster_summary,

        "cluster_states":
            cluster_states,

        "immune_score_summary":
            immune_score_summary,

        "ml_summary":
            ml_summary,

        "pathway_summary":
            pathway_summary,

        "xai_summary":
            xai_summary,
    }

    # ========================================================
    # SAVE FINAL JSON
    # ========================================================

    output_file = (
        output_dir
        / "final_analysis.json"
    )

    with open(
        output_file,
        "w",
        encoding="utf-8",
    ) as handle:

        json.dump(
            final_analysis,
            handle,
            indent=2,
        )

    # ========================================================
    # SAVE LLM INPUT
    # ========================================================

    llm_input = {

        "task":
            "Explain the biological meaning "
            "of the computational immune-state "
            "analysis.",

        "instructions": [
            "Use only the supplied computational evidence.",
            "Do not invent biological findings.",
            "Distinguish evidence from interpretation.",
            "Report uncertainty explicitly.",
            "Explain immune-state patterns.",
            "Use pathway and XAI evidence when available.",
        ],

        "analysis":
            final_analysis,
    }

    llm_file = (
        output_dir
        / "llm_reasoning_input.json"
    )

    with open(
        llm_file,
        "w",
        encoding="utf-8",
    ) as handle:

        json.dump(
            llm_input,
            handle,
            indent=2,
        )

    # ========================================================
    # METADATA
    # ========================================================

    metadata = {

        "input_cells":
            int(len(cell_states)),

        "immune_score_count":
            int(immune_scores.shape[1]),

        "cluster_count":
            int(len(cluster_summary)),

        "ml_available":
            ml_summary is not None,

        "pathway_available":
            pathway_summary is not None,

        "xai_available":
            xai_summary is not None,

        "outputs": {
            "final_analysis":
                str(output_file),

            "llm_reasoning_input":
                str(llm_file),
        },
    }

    metadata_file = (
        output_dir
        / "final_analysis_metadata.json"
    )

    with open(
        metadata_file,
        "w",
        encoding="utf-8",
    ) as handle:

        json.dump(
            metadata,
            handle,
            indent=2,
        )

    # ========================================================
    # RETURN
    # ========================================================

    return {

        "input_cells":
            len(cell_states),

        "state_summary":
            state_summary,

        "cluster_summary":
            cluster_summary,

        "immune_score_summary":
            immune_score_summary,

        "ml_summary":
            ml_summary,

        "pathway_summary":
            pathway_summary,

        "xai_summary":
            xai_summary,

        "final_analysis_output":
            str(output_file),

        "llm_reasoning_input":
            str(llm_file),

        "metadata_output":
            str(metadata_file),
    }