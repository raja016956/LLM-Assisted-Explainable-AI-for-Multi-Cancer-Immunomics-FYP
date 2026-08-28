from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from scipy import sparse


# ============================================================
# CONFIGURATION
# ============================================================

@dataclass
class ClusterCharacterizationConfig:
    top_n_genes: int = 20
    min_cells: int = 5
    min_expression_fraction: float = 0.05


# ============================================================
# HELPERS
# ============================================================

def _load_expression_matrix(
    expression_path: str | Path,
) -> sparse.csr_matrix:

    expression_path = Path(expression_path)

    if not expression_path.exists():
        raise FileNotFoundError(
            f"Expression matrix not found: {expression_path}"
        )

    matrix = sparse.load_npz(
        expression_path
    )

    if matrix.ndim != 2:
        raise ValueError(
            "Expression matrix must be 2-dimensional."
        )

    return matrix.tocsr()


def _load_json_list(
    path: str | Path,
) -> list[str]:

    import json

    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            f"Metadata file not found: {path}"
        )

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as f:

        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(
            f"Expected a list in {path}"
        )

    return [
        str(x)
        for x in data
    ]


# ============================================================
# CLUSTER CHARACTERIZATION
# ============================================================

def run_cluster_characterization(
    expression_path: str | Path,
    cluster_labels_path: str | Path,
    genes_path: str | Path,
    output_dir: str | Path,
    config: ClusterCharacterizationConfig | None = None,
) -> dict[str, Any]:

    if config is None:
        config = ClusterCharacterizationConfig()

    expression_path = Path(
        expression_path
    )

    cluster_labels_path = Path(
        cluster_labels_path
    )

    genes_path = Path(
        genes_path
    )

    output_dir = Path(
        output_dir
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    # ========================================================
    # LOAD CLUSTER LABELS
    # ========================================================

    if not cluster_labels_path.exists():
        raise FileNotFoundError(
            f"Cluster labels not found: "
            f"{cluster_labels_path}"
        )

    labels = np.load(
        cluster_labels_path
    )

    labels = np.asarray(
        labels
    ).reshape(-1)

    n_cells_expected = len(
        labels
    )

    # ========================================================
    # LOAD GENE NAMES
    # ========================================================

    genes = _load_json_list(
        genes_path
    )

    n_genes_expected = len(
        genes
    )

    # ========================================================
    # LOAD EXPRESSION MATRIX
    # ========================================================

    expression = _load_expression_matrix(
        expression_path
    )

    matrix_rows, matrix_columns = (
        expression.shape
    )

    # ========================================================
    # DETERMINE MATRIX ORIENTATION
    # ========================================================

    # Expected orientation:
    #
    # cells × genes
    #
    # But the normalization pipeline may store:
    #
    # genes × cells
    #
    # Therefore determine orientation using
    # the known cell-label and gene counts.

    if (
        matrix_rows == n_cells_expected
        and matrix_columns == n_genes_expected
    ):

        # Already cells × genes
        pass

    elif (
        matrix_rows == n_genes_expected
        and matrix_columns == n_cells_expected
    ):

        # Stored as genes × cells.
        # Convert to cells × genes.
        expression = expression.T.tocsr()

    else:

        raise ValueError(
            "Expression matrix dimensions do not "
            "match the available metadata. "
            f"Matrix shape: {expression.shape}, "
            f"expected cells: {n_cells_expected}, "
            f"expected genes: {n_genes_expected}"
        )

    # ========================================================
    # FINAL DIMENSION VALIDATION
    # ========================================================

    n_cells, n_genes = (
        expression.shape
    )

    if n_cells != n_cells_expected:
        raise ValueError(
            "Cluster labels do not match "
            "the number of expression cells. "
            f"Expression cells: {n_cells}, "
            f"labels: {n_cells_expected}"
        )

    if n_genes != n_genes_expected:
        raise ValueError(
            "Gene list does not match "
            "expression matrix dimensions. "
            f"Genes: {n_genes_expected}, "
            f"matrix genes: {n_genes}"
        )

    # ========================================================
    # VALIDATE CONFIGURATION
    # ========================================================

    if config.top_n_genes < 1:
        raise ValueError(
            "top_n_genes must be at least 1."
        )

    if config.min_cells < 1:
        raise ValueError(
            "min_cells must be at least 1."
        )

    if not 0 <= config.min_expression_fraction <= 1:
        raise ValueError(
            "min_expression_fraction must be "
            "between 0 and 1."
        )

    # ========================================================
    # FIND CLUSTERS
    # ========================================================

    unique_clusters = np.unique(
        labels
    )

    # ========================================================
    # CHARACTERIZE CLUSTERS
    # ========================================================

    cluster_results: dict[str, Any] = {}

    for cluster in unique_clusters:

        cluster = int(cluster)

        cluster_mask = (
            labels == cluster
        )

        background_mask = (
            labels != cluster
        )

        cluster_indices = np.flatnonzero(
            cluster_mask
        )

        background_indices = np.flatnonzero(
            background_mask
        )

        n_cluster_cells = len(
            cluster_indices
        )

        n_background_cells = len(
            background_indices
        )

        if n_cluster_cells < config.min_cells:
            continue

        if n_background_cells == 0:
            continue

        # ----------------------------------------------------
        # CLUSTER EXPRESSION
        # ----------------------------------------------------

        cluster_matrix = expression[
            cluster_indices
        ]

        background_matrix = expression[
            background_indices
        ]

        # ----------------------------------------------------
        # MEAN EXPRESSION
        # ----------------------------------------------------

        cluster_mean = np.asarray(
            cluster_matrix.mean(axis=0)
        ).ravel()

        background_mean = np.asarray(
            background_matrix.mean(axis=0)
        ).ravel()

        # ----------------------------------------------------
        # EXPRESSION FRACTION
        # ----------------------------------------------------

        cluster_detection = np.asarray(
            (cluster_matrix > 0).mean(axis=0)
        ).ravel()

        background_detection = np.asarray(
            (background_matrix > 0).mean(axis=0)
        ).ravel()

        # ----------------------------------------------------
        # LOG FOLD CHANGE
        # ----------------------------------------------------

        pseudocount = 1e-9

        log_fold_change = np.log2(
            (
                cluster_mean
                + pseudocount
            )
            /
            (
                background_mean
                + pseudocount
            )
        )

        # ----------------------------------------------------
        # MARKER SCORE
        # ----------------------------------------------------

        detection_difference = (
            cluster_detection
            - background_detection
        )

        marker_score = (
            log_fold_change
            * np.maximum(
                detection_difference,
                0,
            )
        )

        # ----------------------------------------------------
        # FILTER
        # ----------------------------------------------------

        eligible = (
            cluster_detection
            >= config.min_expression_fraction
        )

        eligible &= (
            log_fold_change > 0
        )

        eligible_indices = np.flatnonzero(
            eligible
        )

        # ----------------------------------------------------
        # RANK GENES
        # ----------------------------------------------------

        if len(eligible_indices) == 0:

            ranked_indices = np.argsort(
                marker_score
            )[::-1][
                :config.top_n_genes
            ]

        else:

            ranked_indices = (
                eligible_indices[
                    np.argsort(
                        marker_score[
                            eligible_indices
                        ]
                    )[::-1]
                ][
                    :config.top_n_genes
                ]
            )

        # ----------------------------------------------------
        # BUILD RESULT
        # ----------------------------------------------------

        markers = []

        for gene_index in ranked_indices:

            markers.append(
                {
                    "gene": genes[
                        int(gene_index)
                    ],

                    "gene_index": int(
                        gene_index
                    ),

                    "cluster_mean_expression": float(
                        cluster_mean[
                            gene_index
                        ]
                    ),

                    "background_mean_expression": float(
                        background_mean[
                            gene_index
                        ]
                    ),

                    "cluster_detection_fraction": float(
                        cluster_detection[
                            gene_index
                        ]
                    ),

                    "background_detection_fraction": float(
                        background_detection[
                            gene_index
                        ]
                    ),

                    "log2_fold_change": float(
                        log_fold_change[
                            gene_index
                        ]
                    ),

                    "marker_score": float(
                        marker_score[
                            gene_index
                        ]
                    ),
                }
            )

        cluster_results[
            str(cluster)
        ] = {
            "cluster": cluster,
            "n_cells": n_cluster_cells,
            "top_markers": markers,
        }

    # ========================================================
    # SAVE RESULTS
    # ========================================================

    import json

    output_file = (
        output_dir
        / "cluster_markers.json"
    )

    with open(
        output_file,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            {
                "n_cells": int(
                    n_cells
                ),

                "n_genes": int(
                    n_genes
                ),

                "n_clusters": int(
                    len(unique_clusters)
                ),

                "clusters": cluster_results,
            },
            f,
            indent=2,
        )

    # ========================================================
    # RESULT
    # ========================================================

    return {

        "method": (
            "Cluster marker characterization "
            "using expression enrichment"
        ),

        "input_cells": int(
            n_cells
        ),

        "input_genes": int(
            n_genes
        ),

        "n_clusters": int(
            len(unique_clusters)
        ),

        "top_n_genes": int(
            config.top_n_genes
        ),

        "output": str(
            output_file
        ),

        "clusters_characterized": [
            int(x)
            for x in cluster_results.keys()
        ],
    }