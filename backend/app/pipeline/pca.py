from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import scipy.sparse as sp
from sklearn.decomposition import TruncatedSVD


# ============================================================
# CONFIGURATION
# ============================================================

@dataclass
class PCAConfig:
    n_components: int = 50
    random_state: int = 42


# ============================================================
# PCA
# ============================================================

def run_pca(
    feature_matrix_path: str | Path,
    output_dir: str | Path,
    config: PCAConfig | None = None,
) -> dict[str, Any]:
    """
    Run PCA on the selected highly variable gene matrix.

    Expected input:
        highly_variable_genes.npz

    Matrix orientation:
        genes x cells

    PCA is performed across cells.

    Therefore:
        input:  genes x cells
        PCA:    cells x genes
        output: cells x components
    """

    if config is None:
        config = PCAConfig()

    feature_matrix_path = Path(feature_matrix_path)
    output_dir = Path(output_dir)

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not feature_matrix_path.exists():
        raise FileNotFoundError(
            f"Feature matrix not found: "
            f"{feature_matrix_path}"
        )

    # --------------------------------------------------------
    # LOAD SPARSE FEATURE MATRIX
    # --------------------------------------------------------

    matrix = sp.load_npz(
        feature_matrix_path
    ).tocsr()

    n_genes, n_cells = matrix.shape

    if n_genes == 0 or n_cells == 0:
        raise ValueError(
            "Feature matrix is empty."
        )

    # --------------------------------------------------------
    # VALIDATE COMPONENT COUNT
    # --------------------------------------------------------

    max_components = min(
        n_genes,
        n_cells - 1,
    )

    if max_components < 1:
        raise ValueError(
            "Not enough cells or genes for PCA."
        )

    n_components = min(
        config.n_components,
        max_components,
    )

    # --------------------------------------------------------
    # PCA INPUT
    # --------------------------------------------------------
    #
    # Feature-selection matrix:
    #
    #       genes x cells
    #
    # PCA expects:
    #
    #       cells x genes
    #
    # Transpose without creating a dense matrix.
    # --------------------------------------------------------

    cell_by_gene = matrix.T.tocsr()

    # --------------------------------------------------------
    # CENTERING / PCA
    # --------------------------------------------------------
    #
    # TruncatedSVD is used on the sparse matrix so the
    # complete 913 x 2000 matrix does not need to be
    # materialized as a dense array.
    #
    # Because TruncatedSVD does not center the matrix,
    # we explicitly calculate the centered representation
    # in chunks before fitting.
    # --------------------------------------------------------

    # Gene means across cells.
    gene_means = np.asarray(
        cell_by_gene.mean(axis=0)
    ).ravel()

    # --------------------------------------------------------
    # Build centered sparse matrix
    # --------------------------------------------------------
    #
    # Subtracting the mean from every element creates many
    # non-zero values, so centering a sparse matrix destroys
    # sparsity.
    #
    # For this dataset:
    #
    #   913 cells × 2000 genes
    #
    # the dense centered matrix is manageable.
    #
    # This is intentionally limited to the selected HVGs,
    # rather than the original 28,928 genes.
    # --------------------------------------------------------

    centered = (
        cell_by_gene.toarray()
        - gene_means
    )

    # --------------------------------------------------------
    # RUN PCA
    # --------------------------------------------------------

    from sklearn.decomposition import PCA

    pca = PCA(
        n_components=n_components,
        svd_solver="auto",
        random_state=config.random_state,
    )

    cell_embeddings = pca.fit_transform(
        centered
    )

    gene_loadings = pca.components_

    explained_variance = (
        pca.explained_variance_
    )

    explained_variance_ratio = (
        pca.explained_variance_ratio_
    )

    cumulative_variance_ratio = np.cumsum(
        explained_variance_ratio
    )

    # --------------------------------------------------------
    # SAVE PCA RESULTS
    # --------------------------------------------------------

    embeddings_output = (
        output_dir
        / "pca_coordinates.npy"
    )

    loadings_output = (
        output_dir
        / "pca_loadings.npy"
    )

    variance_output = (
        output_dir
        / "pca_explained_variance.npy"
    )

    variance_ratio_output = (
        output_dir
        / "pca_explained_variance_ratio.npy"
    )

    cumulative_variance_output = (
        output_dir
        / "pca_cumulative_variance_ratio.npy"
    )

    np.save(
        embeddings_output,
        cell_embeddings,
    )

    np.save(
        loadings_output,
        gene_loadings,
    )

    np.save(
        variance_output,
        explained_variance,
    )

    np.save(
        variance_ratio_output,
        explained_variance_ratio,
    )

    np.save(
        cumulative_variance_output,
        cumulative_variance_ratio,
    )

    # --------------------------------------------------------
    # RESULT
    # --------------------------------------------------------

    return {
        "method": "Principal Component Analysis",
        "input_genes": int(n_genes),
        "input_cells": int(n_cells),
        "n_components": int(n_components),

        "embedding_shape": [
            int(cell_embeddings.shape[0]),
            int(cell_embeddings.shape[1]),
        ],

        "loading_shape": [
            int(gene_loadings.shape[0]),
            int(gene_loadings.shape[1]),
        ],

        "explained_variance_sum": float(
            explained_variance.sum()
        ),

        "explained_variance_ratio_sum": float(
            explained_variance_ratio.sum()
        ),

        "cumulative_variance_ratio": [
            float(x)
            for x in cumulative_variance_ratio
        ],

        "embeddings_output": str(
            embeddings_output
        ),

        "loadings_output": str(
            loadings_output
        ),

        "variance_output": str(
            variance_output
        ),

        "variance_ratio_output": str(
            variance_ratio_output
        ),

        "cumulative_variance_output": str(
            cumulative_variance_output
        ),
    }