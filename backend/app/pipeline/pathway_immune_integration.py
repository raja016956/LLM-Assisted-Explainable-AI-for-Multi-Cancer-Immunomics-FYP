from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json

import numpy as np


# ============================================================
# CONFIGURATION
# ============================================================

@dataclass(frozen=True)
class PathwayImmuneIntegrationConfig:
    minimum_cells_per_state: int = 2
    minimum_cells_per_cluster: int = 2
    minimum_state_fraction: float = 0.01
    correlation_method: str = "pearson"


# ============================================================
# HELPERS
# ============================================================

def _load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {path}")

    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _load_array(path: Path, description: str) -> np.ndarray:
    if not path.exists():
        raise FileNotFoundError(
            f"{description} not found: {path}"
        )

    array = np.load(path)

    if array.ndim != 2:
        raise ValueError(
            f"{description} must be a 2D matrix. "
            f"Received shape: {array.shape}"
        )

    return array.astype(np.float32, copy=False)


def _load_cluster_labels(path: Path) -> np.ndarray:
    if not path.exists():
        raise FileNotFoundError(
            f"Cluster labels not found: {path}"
        )

    labels = np.load(path)

    if labels.ndim != 1:
        raise ValueError(
            "Cluster labels must be one-dimensional."
        )

    return labels


def _mean(values: np.ndarray) -> float:
    if values.size == 0:
        return 0.0

    return float(np.mean(values))


def _median(values: np.ndarray) -> float:
    if values.size == 0:
        return 0.0

    return float(np.median(values))


def _std(values: np.ndarray) -> float:
    if values.size <= 1:
        return 0.0

    return float(np.std(values))


def _safe_pearson(x: np.ndarray, y: np.ndarray) -> float:
    if x.size < 2 or y.size < 2:
        return 0.0

    if np.std(x) == 0 or np.std(y) == 0:
        return 0.0

    correlation = np.corrcoef(x, y)[0, 1]

    if not np.isfinite(correlation):
        return 0.0

    return float(correlation)


# ============================================================
# CELL STATE EXTRACTION
# ============================================================

def _extract_cell_states(data) -> list[str]:
    """
    Supports common cell_immune_states.json structures.
    """

    if isinstance(data, list):
        return [str(x) for x in data]

    if isinstance(data, dict):

        # Direct mapping:
        # {
        #   "0": "Immune-Excluded",
        #   "1": "Insufficient-Evidence"
        # }
        if all(
            isinstance(value, str)
            for value in data.values()
        ):
            return [
                str(data[key])
                for key in sorted(
                    data.keys(),
                    key=lambda x: int(x)
                    if str(x).isdigit()
                    else str(x),
                )
            ]

        # Common nested structure:
        # {
        #   "cells": {
        #       "0": {"state": "..."}
        #   }
        # }
        if "cells" in data:

            cells = data["cells"]

            if isinstance(cells, list):
                states = []

                for cell in cells:
                    if isinstance(cell, dict):
                        states.append(
                            str(
                                cell.get(
                                    "state",
                                    "Insufficient-Evidence",
                                )
                            )
                        )
                    else:
                        states.append(str(cell))

                return states

            if isinstance(cells, dict):
                states = []

                ordered_keys = sorted(
                    cells.keys(),
                    key=lambda x: int(x)
                    if str(x).isdigit()
                    else str(x),
                )

                for key in ordered_keys:
                    cell = cells[key]

                    if isinstance(cell, dict):
                        states.append(
                            str(
                                cell.get(
                                    "state",
                                    "Insufficient-Evidence",
                                )
                            )
                        )
                    else:
                        states.append(str(cell))

                return states

        # Another possible structure:
        # {
        #   "cell_states": [...]
        # }
        if "cell_states" in data:
            return [
                str(x)
                for x in data["cell_states"]
            ]

    raise ValueError(
        "Unsupported cell immune-state JSON format."
    )


# ============================================================
# STATE SUMMARY
# ============================================================

def _build_state_summary(
    pathway_scores: np.ndarray,
    pathway_names: list[str],
    cell_states: list[str],
    config: PathwayImmuneIntegrationConfig,
):
    states = sorted(set(cell_states))

    total_cells = len(cell_states)

    summary = {}

    for state in states:

        indices = np.array(
            [
                i
                for i, cell_state in enumerate(cell_states)
                if cell_state == state
            ],
            dtype=np.int64,
        )

        n_cells = len(indices)

        supported = (
            n_cells
            >= config.minimum_cells_per_state
            and (
                n_cells / total_cells
                >= config.minimum_state_fraction
            )
        )

        pathways = {}

        for pathway_index, pathway_name in enumerate(
            pathway_names
        ):

            values = pathway_scores[
                indices,
                pathway_index,
            ]

            pathways[pathway_name] = {
                "mean": _mean(values),
                "median": _median(values),
                "std": _std(values),
            }

        summary[state] = {
            "n_cells": n_cells,
            "fraction": (
                float(n_cells / total_cells)
                if total_cells > 0
                else 0.0
            ),
            "supported": supported,
            "pathways": pathways,
        }

    return summary


# ============================================================
# CLUSTER SUMMARY
# ============================================================

def _build_cluster_summary(
    pathway_scores: np.ndarray,
    pathway_names: list[str],
    cluster_labels: np.ndarray,
    cell_states: list[str],
    config: PathwayImmuneIntegrationConfig,
):
    clusters = sorted(
        np.unique(cluster_labels),
        key=lambda x: int(x)
        if np.issubdtype(
            type(x),
            np.integer,
        )
        else str(x),
    )

    summary = {}

    for cluster in clusters:

        indices = np.where(
            cluster_labels == cluster
        )[0]

        n_cells = len(indices)

        pathways = {}

        for pathway_index, pathway_name in enumerate(
            pathway_names
        ):

            values = pathway_scores[
                indices,
                pathway_index,
            ]

            pathways[pathway_name] = {
                "mean": _mean(values),
                "median": _median(values),
                "std": _std(values),
            }

        state_counts = {}

        for index in indices:

            state = cell_states[index]

            state_counts[state] = (
                state_counts.get(state, 0)
                + 1
            )

        summary[str(cluster)] = {
            "n_cells": n_cells,
            "supported": (
                n_cells
                >= config.minimum_cells_per_cluster
            ),
            "immune_state_distribution": state_counts,
            "pathways": pathways,
        }

    return summary


# ============================================================
# PATHWAY RANKING
# ============================================================

def _build_pathway_rankings(
    state_summary: dict,
    pathway_names: list[str],
):
    rankings = {}

    for state, state_data in state_summary.items():

        if not state_data["supported"]:
            rankings[state] = []
            continue

        pathway_values = []

        for pathway_name in pathway_names:

            mean_value = state_data[
                "pathways"
            ][pathway_name]["mean"]

            pathway_values.append(
                (
                    pathway_name,
                    mean_value,
                )
            )

        pathway_values.sort(
            key=lambda x: x[1],
            reverse=True,
        )

        rankings[state] = [
            {
                "pathway": pathway,
                "mean_score": score,
                "rank": rank,
            }
            for rank, (
                pathway,
                score,
            ) in enumerate(
                pathway_values,
                start=1,
            )
        ]

    return rankings


# ============================================================
# PATHWAY–IMMUNE SCORE ASSOCIATIONS
# ============================================================

def _build_associations(
    pathway_scores: np.ndarray,
    pathway_names: list[str],
    immune_scores: np.ndarray,
    immune_score_names: list[str],
):
    associations = {}

    for pathway_index, pathway_name in enumerate(
        pathway_names
    ):

        associations[pathway_name] = {}

        pathway_vector = pathway_scores[
            :,
            pathway_index,
        ]

        for immune_index, immune_name in enumerate(
            immune_score_names
        ):

            immune_vector = immune_scores[
                :,
                immune_index,
            ]

            correlation = _safe_pearson(
                pathway_vector,
                immune_vector,
            )

            associations[pathway_name][
                immune_name
            ] = {
                "pearson_correlation": correlation,
                "absolute_correlation": abs(
                    correlation
                ),
            }

    return associations


# ============================================================
# STATE MATRIX
# ============================================================

def _build_state_matrix(
    state_summary: dict,
    pathway_names: list[str],
):
    supported_states = [
        state
        for state, data in state_summary.items()
        if data["supported"]
    ]

    matrix = np.zeros(
        (
            len(supported_states),
            len(pathway_names),
        ),
        dtype=np.float32,
    )

    for state_index, state in enumerate(
        supported_states
    ):

        for pathway_index, pathway in enumerate(
            pathway_names
        ):

            matrix[
                state_index,
                pathway_index,
            ] = state_summary[state][
                "pathways"
            ][pathway]["mean"]

    return matrix, supported_states


# ============================================================
# MAIN PIPELINE
# ============================================================

def run_pathway_immune_integration(
    pathway_scores_path: str | Path,
    pathway_names_path: str | Path,
    immune_scores_path: str | Path,
    immune_score_names_path: str | Path,
    cell_states_path: str | Path,
    cluster_labels_path: str | Path,
    output_dir: str | Path,
    config: PathwayImmuneIntegrationConfig | None = None,
) -> dict:

    config = (
        config
        or PathwayImmuneIntegrationConfig()
    )

    pathway_scores_path = Path(
        pathway_scores_path
    )

    pathway_names_path = Path(
        pathway_names_path
    )

    immune_scores_path = Path(
        immune_scores_path
    )

    immune_score_names_path = Path(
        immune_score_names_path
    )

    cell_states_path = Path(
        cell_states_path
    )

    cluster_labels_path = Path(
        cluster_labels_path
    )

    output_dir = Path(output_dir)

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------------------------------
    # LOAD
    # --------------------------------------------------------

    pathway_scores = _load_array(
        pathway_scores_path,
        "Pathway score matrix",
    )

    immune_scores = _load_array(
        immune_scores_path,
        "Immune score matrix",
    )

    pathway_names = [
        str(x)
        for x in _load_json(
            pathway_names_path
        )
    ]

    immune_score_names = [
        str(x)
        for x in _load_json(
            immune_score_names_path
        )
    ]

    cell_state_data = _load_json(
        cell_states_path
    )

    cell_states = _extract_cell_states(
        cell_state_data
    )

    cluster_labels = _load_cluster_labels(
        cluster_labels_path
    )

    # --------------------------------------------------------
    # DIMENSION VALIDATION
    # --------------------------------------------------------

    n_cells = pathway_scores.shape[0]

    if len(pathway_names) != pathway_scores.shape[1]:
        raise ValueError(
            "Pathway metadata does not match "
            "pathway score dimensions. "
            f"Scores: {pathway_scores.shape[1]}, "
            f"names: {len(pathway_names)}"
        )

    if immune_scores.shape[0] != n_cells:
        raise ValueError(
            "Immune score matrix does not contain "
            "the same number of cells as pathway scores. "
            f"Pathway cells: {n_cells}, "
            f"immune cells: {immune_scores.shape[0]}"
        )

    if len(immune_score_names) != immune_scores.shape[1]:
        raise ValueError(
            "Immune score metadata does not match "
            "immune score dimensions."
        )

    if len(cell_states) != n_cells:
        raise ValueError(
            "Cell immune-state count does not match "
            "pathway score cells. "
            f"Pathway cells: {n_cells}, "
            f"cell states: {len(cell_states)}"
        )

    if len(cluster_labels) != n_cells:
        raise ValueError(
            "Cluster label count does not match "
            "pathway score cells. "
            f"Pathway cells: {n_cells}, "
            f"clusters: {len(cluster_labels)}"
        )

    if not np.all(np.isfinite(pathway_scores)):
        raise ValueError(
            "Pathway score matrix contains "
            "non-finite values."
        )

    if not np.all(np.isfinite(immune_scores)):
        raise ValueError(
            "Immune score matrix contains "
            "non-finite values."
        )

    # --------------------------------------------------------
    # ANALYSIS
    # --------------------------------------------------------

    state_summary = _build_state_summary(
        pathway_scores,
        pathway_names,
        cell_states,
        config,
    )

    cluster_summary = _build_cluster_summary(
        pathway_scores,
        pathway_names,
        cluster_labels,
        cell_states,
        config,
    )

    pathway_rankings = _build_pathway_rankings(
        state_summary,
        pathway_names,
    )

    associations = _build_associations(
        pathway_scores,
        pathway_names,
        immune_scores,
        immune_score_names,
    )

    state_matrix, supported_states = (
        _build_state_matrix(
            state_summary,
            pathway_names,
        )
    )

    # --------------------------------------------------------
    # OUTPUTS
    # --------------------------------------------------------

    state_summary_path = (
        output_dir
        / "pathway_state_summary.json"
    )

    cluster_summary_path = (
        output_dir
        / "pathway_cluster_summary.json"
    )

    association_path = (
        output_dir
        / "pathway_immune_associations.json"
    )

    ranking_path = (
        output_dir
        / "pathway_state_rankings.json"
    )

    state_matrix_path = (
        output_dir
        / "pathway_state_matrix.npy"
    )

    state_names_path = (
        output_dir
        / "supported_immune_states.json"
    )

    metadata_path = (
        output_dir
        / "integration_metadata.json"
    )

    with open(
        state_summary_path,
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(
            state_summary,
            handle,
            indent=2,
        )

    with open(
        cluster_summary_path,
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(
            cluster_summary,
            handle,
            indent=2,
        )

    with open(
        association_path,
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(
            associations,
            handle,
            indent=2,
        )

    with open(
        ranking_path,
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(
            pathway_rankings,
            handle,
            indent=2,
        )

    np.save(
        state_matrix_path,
        state_matrix,
    )

    with open(
        state_names_path,
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(
            supported_states,
            handle,
            indent=2,
        )

    metadata = {
        "input_cells": int(n_cells),
        "pathway_count": len(pathway_names),
        "immune_score_count": len(
            immune_score_names
        ),
        "cluster_count": int(
            len(np.unique(cluster_labels))
        ),
        "immune_state_count": len(
            state_summary
        ),
        "supported_immune_state_count": len(
            supported_states
        ),
        "state_matrix_shape": list(
            state_matrix.shape
        ),
        "pathways": pathway_names,
        "immune_scores": immune_score_names,
        "immune_states": sorted(
            state_summary.keys()
        ),
        "configuration": {
            "minimum_cells_per_state":
                config.minimum_cells_per_state,
            "minimum_cells_per_cluster":
                config.minimum_cells_per_cluster,
            "minimum_state_fraction":
                config.minimum_state_fraction,
            "correlation_method":
                config.correlation_method,
        },
    }

    with open(
        metadata_path,
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(
            metadata,
            handle,
            indent=2,
        )

    return {
        "input_cells": n_cells,
        "pathway_count": len(pathway_names),
        "immune_score_count": len(
            immune_score_names
        ),
        "cluster_count": int(
            len(np.unique(cluster_labels))
        ),
        "immune_state_count": len(
            state_summary
        ),
        "supported_immune_state_count": len(
            supported_states
        ),
        "state_summary": state_summary,
        "cluster_summary": cluster_summary,
        "pathway_rankings": pathway_rankings,
        "associations": associations,
        "state_matrix": state_matrix,
        "supported_states": supported_states,
        "state_summary_output": str(
            state_summary_path
        ),
        "cluster_summary_output": str(
            cluster_summary_path
        ),
        "association_output": str(
            association_path
        ),
        "ranking_output": str(
            ranking_path
        ),
        "state_matrix_output": str(
            state_matrix_path
        ),
        "state_names_output": str(
            state_names_path
        ),
        "metadata_output": str(
            metadata_path
        ),
    }