from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import json

import numpy as np
from scipy import sparse


# ============================================================
# CONFIGURATION
# ============================================================

@dataclass
class ImmuneStateScoringConfig:

    # --------------------------------------------------------
    # T-CELL ACTIVITY
    # --------------------------------------------------------

    t_cell_markers: tuple[str, ...] = (
        "CD3D",
        "CD3E",
        "CD3G",
        "TRBC1",
        "TRBC2",
        "IL7R",
        "LTB",
    )

    # --------------------------------------------------------
    # CYTOTOXIC ACTIVITY
    # --------------------------------------------------------

    cytotoxic_markers: tuple[str, ...] = (
        "NKG7",
        "GNLY",
        "GZMB",
        "GZMH",
        "GZMK",
        "PRF1",
        "CTSW",
    )

    # --------------------------------------------------------
    # MYELOID SIGNAL
    # --------------------------------------------------------

    myeloid_markers: tuple[str, ...] = (
        "LST1",
        "LYZ",
        "FCER1G",
        "TYROBP",
        "CTSS",
        "AIF1",
        "LGALS3",
    )

    # --------------------------------------------------------
    # IMMUNE SUPPRESSION
    # --------------------------------------------------------

    immune_suppression_markers: tuple[str, ...] = (
        "CD274",
        "PDCD1",
        "CTLA4",
        "HAVCR2",
        "LAG3",
        "TIGIT",
        "VSIR",
    )

    # --------------------------------------------------------
    # INFLAMMATORY SIGNAL
    # --------------------------------------------------------

    inflammatory_markers: tuple[str, ...] = (
        "CXCL9",
        "CXCL10",
        "CXCL11",
        "CCL2",
        "CCL3",
        "CCL4",
        "IL1B",
        "TNF",
    )

    # --------------------------------------------------------
    # ANTIGEN PRESENTATION
    # --------------------------------------------------------

    antigen_presentation_markers: tuple[str, ...] = (
        "HLA-DRA",
        "HLA-DRB1",
        "HLA-DPA1",
        "HLA-DPB1",
        "HLA-DQA1",
        "HLA-DQB1",
        "CD74",
    )

    min_genes_per_signature: int = 1


# ============================================================
# LOAD EXPRESSION
# ============================================================

def _load_expression(
    expression_path: str | Path,
) -> sparse.spmatrix:

    expression_path = Path(
        expression_path
    )

    if not expression_path.exists():

        raise FileNotFoundError(
            f"Expression matrix not found: "
            f"{expression_path}"
        )

    matrix = sparse.load_npz(
        expression_path
    )

    if matrix.ndim != 2:

        raise ValueError(
            "Expression matrix must be "
            "2-dimensional."
        )

    if (
        matrix.shape[0] == 0
        or matrix.shape[1] == 0
    ):

        raise ValueError(
            "Expression matrix is empty."
        )

    return matrix


# ============================================================
# LOAD JSON
# ============================================================

def _load_json(
    path: str | Path,
) -> Any:

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

        return json.load(f)


# ============================================================
# LOAD GENES
# ============================================================

def _load_genes(
    genes_path: str | Path,
) -> list[str]:

    data = _load_json(
        genes_path
    )

    if isinstance(data, dict):

        if "genes" not in data:

            raise ValueError(
                "Gene metadata dictionary "
                "must contain a 'genes' field."
            )

        data = data["genes"]

    if not isinstance(
        data,
        list,
    ):

        raise ValueError(
            "Gene metadata must be a list."
        )

    genes = [
        str(gene).strip()
        for gene in data
    ]

    if not genes:

        raise ValueError(
            "Gene metadata is empty."
        )

    return genes


# ============================================================
# LOAD CLUSTER LABELS
# ============================================================

def _load_cluster_labels(
    cluster_labels_path: str | Path,
) -> np.ndarray:

    cluster_labels_path = Path(
        cluster_labels_path
    )

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

    if labels.size == 0:

        raise ValueError(
            "Cluster labels are empty."
        )

    return labels


# ============================================================
# ORIENTATION HANDLING
# ============================================================

def _orient_expression_matrix(
    expression: sparse.spmatrix,
    genes: list[str],
    cluster_labels: np.ndarray,
) -> sparse.spmatrix:
    """
    Convert expression matrix internally to:

        cells × genes

    The stored matrix in this project is currently:

        genes × cells

    Example:

        28,928 genes × 913 cells

    This function detects the orientation from the
    supplied metadata instead of assuming it.
    """

    rows, columns = expression.shape

    n_genes = len(genes)

    n_cells = len(cluster_labels)

    # --------------------------------------------------------
    # CASE 1
    #
    # Matrix already is:
    #
    # cells × genes
    # --------------------------------------------------------

    if (
        rows == n_cells
        and columns == n_genes
    ):

        return expression

    # --------------------------------------------------------
    # CASE 2
    #
    # Matrix is:
    #
    # genes × cells
    #
    # This is the orientation used by your
    # normalized_log1p.npz.
    # --------------------------------------------------------

    if (
        rows == n_genes
        and columns == n_cells
    ):

        return expression.T.tocsr()

    # --------------------------------------------------------
    # INVALID DIMENSIONS
    # --------------------------------------------------------

    raise ValueError(
        "Expression matrix dimensions do not "
        "match the supplied metadata.\n"
        f"Expression matrix: "
        f"{rows} × {columns}\n"
        f"Gene metadata: "
        f"{n_genes}\n"
        f"Cluster labels: "
        f"{n_cells}\n\n"
        "Expected either:\n"
        f"  cells × genes = "
        f"{n_cells} × {n_genes}\n"
        "or:\n"
        f"  genes × cells = "
        f"{n_genes} × {n_cells}"
    )


# ============================================================
# GENE INDEX
# ============================================================

def _build_gene_index(
    genes: list[str],
) -> dict[str, int]:

    gene_index: dict[str, int] = {}

    for index, gene in enumerate(
        genes
    ):

        gene = gene.strip()

        if (
            gene
            and gene not in gene_index
        ):

            gene_index[gene] = index

    return gene_index


# ============================================================
# RESOLVE SIGNATURE
# ============================================================

def _resolve_signature(
    signature: tuple[str, ...],
    gene_index: dict[str, int],
) -> tuple[
    list[str],
    list[int],
]:

    found_genes: list[str] = []

    found_indices: list[int] = []

    for gene in signature:

        if gene in gene_index:

            found_genes.append(
                gene
            )

            found_indices.append(
                gene_index[gene]
            )

    return (
        found_genes,
        found_indices,
    )


# ============================================================
# SCORE SIGNATURE
# ============================================================

def _score_signature(
    expression: sparse.spmatrix,
    gene_indices: list[int],
) -> np.ndarray:

    n_cells = expression.shape[0]

    if not gene_indices:

        return np.zeros(
            n_cells,
            dtype=np.float64,
        )

    values = expression[
        :,
        gene_indices,
    ]

    scores = np.asarray(
        values.mean(
            axis=1
        )
    ).reshape(-1)

    return np.asarray(
        scores,
        dtype=np.float64,
    )


# ============================================================
# MAIN SCORING FUNCTION
# ============================================================

def run_immune_state_scoring(
    expression_path: str | Path,
    genes_path: str | Path,
    cluster_labels_path: str | Path,
    output_dir: str | Path,
    config: ImmuneStateScoringConfig | None = None,
) -> dict[str, Any]:

    if config is None:

        config = (
            ImmuneStateScoringConfig()
        )

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

    raw_expression = _load_expression(
        expression_path
    )

    genes = _load_genes(
        genes_path
    )

    cluster_labels = (
        _load_cluster_labels(
            cluster_labels_path
        )
    )

    # --------------------------------------------------------
    # DETERMINE ORIENTATION
    # --------------------------------------------------------

    expression = (
        _orient_expression_matrix(
            raw_expression,
            genes,
            cluster_labels,
        )
    )

    n_cells, n_genes = (
        expression.shape
    )

    # --------------------------------------------------------
    # BUILD GENE INDEX
    # --------------------------------------------------------

    gene_index = (
        _build_gene_index(
            genes
        )
    )

    # --------------------------------------------------------
    # SIGNATURES
    # --------------------------------------------------------

    signatures = {

        "t_cell_activity":
            config.t_cell_markers,

        "cytotoxic_activity":
            config.cytotoxic_markers,

        "myeloid_signal":
            config.myeloid_markers,

        "immune_suppression":
            config.immune_suppression_markers,

        "inflammatory_signal":
            config.inflammatory_markers,

        "antigen_presentation":
            config.antigen_presentation_markers,
    }

    # --------------------------------------------------------
    # SCORE SIGNATURES
    # --------------------------------------------------------

    score_arrays: dict[
        str,
        np.ndarray,
    ] = {}

    signature_metadata: dict[
        str,
        dict[str, Any],
    ] = {}

    for (
        signature_name,
        marker_genes,
    ) in signatures.items():

        (
            found_genes,
            found_indices,
        ) = _resolve_signature(
            marker_genes,
            gene_index,
        )

        scores = _score_signature(
            expression,
            found_indices,
        )

        score_arrays[
            signature_name
        ] = scores

        signature_metadata[
            signature_name
        ] = {

            "requested_genes":
                list(marker_genes),

            "available_genes":
                found_genes,

            "missing_genes": [
                gene
                for gene in marker_genes
                if gene not in gene_index
            ],

            "available_gene_count":
                len(found_genes),

            "score_supported":
                (
                    len(found_genes)
                    >= config.min_genes_per_signature
                ),
        }

    # --------------------------------------------------------
    # SCORE MATRIX
    # --------------------------------------------------------

    score_names = list(
        score_arrays.keys()
    )

    score_matrix = np.column_stack(
        [
            score_arrays[name]
            for name in score_names
        ]
    )

    score_matrix = np.asarray(
        score_matrix,
        dtype=np.float64,
    )

    expected_shape = (
        n_cells,
        len(score_names),
    )

    if (
        score_matrix.shape
        != expected_shape
    ):

        raise RuntimeError(
            "Unexpected immune score "
            "matrix shape. "
            f"Expected {expected_shape}, "
            f"got {score_matrix.shape}"
        )

    if not np.all(
        np.isfinite(
            score_matrix
        )
    ):

        raise RuntimeError(
            "Immune score matrix contains "
            "non-finite values."
        )

    # --------------------------------------------------------
    # SAVE NUMPY MATRIX
    # --------------------------------------------------------

    score_matrix_output = (
        output_dir
        / "immune_scores.npy"
    )

    np.save(
        score_matrix_output,
        score_matrix,
    )

    # --------------------------------------------------------
    # SAVE SCORE NAMES
    # --------------------------------------------------------

    score_names_output = (
        output_dir
        / "score_names.json"
    )

    with open(
        score_names_output,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            score_names,
            f,
            indent=2,
        )

    # --------------------------------------------------------
    # CELL-LEVEL RESULTS
    # --------------------------------------------------------

    cells = []

    for cell_index in range(
        n_cells
    ):

        cell_scores = {}

        for (
            score_index,
            score_name,
        ) in enumerate(
            score_names
        ):

            cell_scores[
                score_name
            ] = float(
                score_matrix[
                    cell_index,
                    score_index,
                ]
            )

        cells.append(
            {
                "cell_index":
                    int(cell_index),

                "cluster":
                    int(
                        cluster_labels[
                            cell_index
                        ]
                    ),

                "scores":
                    cell_scores,
            }
        )

    # --------------------------------------------------------
    # CLUSTER SUMMARIES
    # --------------------------------------------------------

    cluster_summary = {}

    unique_clusters = np.unique(
        cluster_labels
    )

    for cluster in unique_clusters:

        mask = (
            cluster_labels
            == cluster
        )

        cluster_scores = (
            score_matrix[mask]
        )

        means = np.mean(
            cluster_scores,
            axis=0,
        )

        medians = np.median(
            cluster_scores,
            axis=0,
        )

        cluster_summary[
            str(int(cluster))
        ] = {

            "n_cells":
                int(
                    np.sum(mask)
                ),

            "mean_scores": {

                score_name:
                    float(
                        means[index]
                    )

                for index, score_name
                in enumerate(
                    score_names
                )
            },

            "median_scores": {

                score_name:
                    float(
                        medians[index]
                    )

                for index, score_name
                in enumerate(
                    score_names
                )
            },
        }

    # --------------------------------------------------------
    # RESULT
    # --------------------------------------------------------

    result = {

        "method":
            "Quantitative immune-state "
            "gene-set scoring",

        "input_cells":
            int(n_cells),

        "input_genes":
            int(n_genes),

        "n_clusters":
            int(
                len(unique_clusters)
            ),

        "score_names":
            score_names,

        "score_matrix_shape": [

            int(
                score_matrix.shape[0]
            ),

            int(
                score_matrix.shape[1]
            ),
        ],

        "expression_original_shape": [

            int(
                raw_expression.shape[0]
            ),

            int(
                raw_expression.shape[1]
            ),
        ],

        "expression_internal_shape": [

            int(
                expression.shape[0]
            ),

            int(
                expression.shape[1]
            ),
        ],

        "signatures":
            signature_metadata,

        "clusters":
            cluster_summary,

        "cells":
            cells,

        "score_matrix_output":
            str(
                score_matrix_output
            ),

        "score_names_output":
            str(
                score_names_output
            ),
    }

    # --------------------------------------------------------
    # SAVE JSON
    # --------------------------------------------------------

    json_output = (
        output_dir
        / "immune_scores.json"
    )

    with open(
        json_output,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            result,
            f,
            indent=2,
        )

    result[
        "json_output"
    ] = str(
        json_output
    )

    return result