from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import scipy.sparse as sp


# ============================================================
# CONFIGURATION
# ============================================================

@dataclass
class FeatureSelectionConfig:
    n_top_genes: int = 2000
    min_cells: int = 3


# ============================================================
# FEATURE SELECTION
# ============================================================

def select_highly_variable_genes(
    normalized_matrix_path: str | Path,
    output_dir: str | Path,
    config: FeatureSelectionConfig | None = None,
) -> dict[str, Any]:
    """
    Select highly variable genes from the normalized log1p matrix.

    Expected input:
        normalized_log1p.npz

    The matrix is expected to be stored as:
        genes x cells

    The function computes variance across cells and selects
    the top variable genes without converting the complete
    matrix to a dense array.
    """

    if config is None:
        config = FeatureSelectionConfig()

    normalized_matrix_path = Path(normalized_matrix_path)
    output_dir = Path(output_dir)

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not normalized_matrix_path.exists():
        raise FileNotFoundError(
            f"Normalized matrix not found: "
            f"{normalized_matrix_path}"
        )

    # --------------------------------------------------------
    # LOAD SPARSE MATRIX
    # --------------------------------------------------------

    matrix = sp.load_npz(
        normalized_matrix_path
    ).tocsr()

    n_genes, n_cells = matrix.shape

    if n_genes == 0 or n_cells == 0:
        raise ValueError(
            "Normalized matrix is empty."
        )

    # --------------------------------------------------------
    # DETERMINE GENE DETECTION
    # --------------------------------------------------------

    detected_cells = np.asarray(
        (matrix > 0).sum(axis=1)
    ).ravel()

    eligible_mask = (
        detected_cells >= config.min_cells
    )

    eligible_indices = np.flatnonzero(
        eligible_mask
    )

    if len(eligible_indices) == 0:
        raise ValueError(
            "No genes satisfy the minimum cell detection "
            "criterion."
        )

    # --------------------------------------------------------
    # VARIANCE ACROSS CELLS
    # --------------------------------------------------------

    eligible_matrix = matrix[
        eligible_indices
    ]

    mean = np.asarray(
        eligible_matrix.mean(axis=1)
    ).ravel()

    squared_mean = np.asarray(
        eligible_matrix.power(2).mean(axis=1)
    ).ravel()

    variance = (
        squared_mean
        - np.square(mean)
    )

    variance = np.maximum(
        variance,
        0.0,
    )

    # --------------------------------------------------------
    # TOP VARIABLE GENES
    # --------------------------------------------------------

    n_select = min(
        config.n_top_genes,
        len(eligible_indices),
    )

    ranking = np.argsort(
        variance
    )[::-1]

    selected_local = ranking[
        :n_select
    ]

    selected_gene_indices = (
        eligible_indices[
            selected_local
        ]
    )

    selected_variances = (
        variance[
            selected_local
        ]
    )

    # Keep genes ordered by original matrix order.
    order = np.argsort(
        selected_gene_indices
    )

    selected_gene_indices = (
        selected_gene_indices[
            order
        ]
    )

    selected_variances = (
        selected_variances[
            order
        ]
    )

    # --------------------------------------------------------
    # CREATE FEATURE MATRIX
    # --------------------------------------------------------

    feature_matrix = matrix[
        selected_gene_indices,
        :
    ].tocsr()

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    matrix_output = (
        output_dir
        / "highly_variable_genes.npz"
    )

    indices_output = (
        output_dir
        / "selected_gene_indices.npy"
    )

    variance_output = (
        output_dir
        / "gene_variances.npy"
    )

    sp.save_npz(
        matrix_output,
        feature_matrix,
    )

    np.save(
        indices_output,
        selected_gene_indices,
    )

    np.save(
        variance_output,
        selected_variances,
    )

    # --------------------------------------------------------
    # RESULT
    # --------------------------------------------------------

    return {
        "method": (
            "Variance-based highly variable "
            "gene selection"
        ),
        "original_genes": int(n_genes),
        "eligible_genes": int(
            len(eligible_indices)
        ),
        "selected_genes": int(
            len(selected_gene_indices)
        ),
        "cells": int(n_cells),
        "min_cells": int(
            config.min_cells
        ),
        "n_top_genes": int(
            config.n_top_genes
        ),
        "nonzero_entries": int(
            feature_matrix.nnz
        ),
        "matrix_output": str(
            matrix_output
        ),
        "indices_output": str(
            indices_output
        ),
        "variance_output": str(
            variance_output
        ),
    }