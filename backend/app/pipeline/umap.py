from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


# ============================================================
# CONFIGURATION
# ============================================================

@dataclass
class UMAPConfig:
    n_components: int = 2
    n_neighbors: int = 15
    min_dist: float = 0.5
    metric: str = "euclidean"
    random_state: int = 42


# ============================================================
# UMAP
# ============================================================

# Handles the run umap step in UMAP dimensionality reduction.
def run_umap(
    pca_coordinates_path: str | Path,
    output_dir: str | Path,
    config: UMAPConfig | None = None,
) -> dict[str, Any]:
    """
    Run UMAP on PCA cell embeddings.

    Expected input:
        pca_coordinates.npy

    Input orientation:
        cells x PCA components

    Output:
        cells x UMAP components
    """

    if config is None:
        config = UMAPConfig()

    pca_coordinates_path = Path(
        pca_coordinates_path
    )

    output_dir = Path(output_dir)

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not pca_coordinates_path.exists():
        raise FileNotFoundError(
            "PCA coordinates not found: "
            f"{pca_coordinates_path}"
        )

    # --------------------------------------------------------
    # LOAD PCA EMBEDDING
    # --------------------------------------------------------

    pca_coordinates = np.load(
        pca_coordinates_path
    )

    if pca_coordinates.ndim != 2:
        raise ValueError(
            "PCA coordinates must be a "
            "2-dimensional array."
        )

    n_cells, n_pcs = pca_coordinates.shape

    if n_cells == 0 or n_pcs == 0:
        raise ValueError(
            "PCA coordinates are empty."
        )

    # --------------------------------------------------------
    # VALIDATE UMAP CONFIGURATION
    # --------------------------------------------------------

    if config.n_components < 1:
        raise ValueError(
            "n_components must be at least 1."
        )

    if config.n_neighbors < 2:
        raise ValueError(
            "n_neighbors must be at least 2."
        )

    if config.n_neighbors >= n_cells:
        raise ValueError(
            "n_neighbors must be smaller than "
            "the number of cells."
        )

    if config.min_dist < 0:
        raise ValueError(
            "min_dist must be non-negative."
        )

    # --------------------------------------------------------
    # IMPORT UMAP
    # --------------------------------------------------------

    try:

        import umap.umap_ as umap_module

    except ImportError as exc:

        raise ImportError(
            "The 'umap-learn' package is required "
            "to run UMAP. Install it with:\n"
            "python -m pip install umap-learn"
        ) from exc

    # --------------------------------------------------------
    # RUN UMAP
    # --------------------------------------------------------

    reducer = umap_module.UMAP(
        n_components=config.n_components,
        n_neighbors=config.n_neighbors,
        min_dist=config.min_dist,
        metric=config.metric,
        random_state=config.random_state,
    )

    embedding = reducer.fit_transform(
        pca_coordinates
    )

    embedding = np.asarray(
        embedding,
        dtype=np.float64,
    )

    # --------------------------------------------------------
    # VALIDATE OUTPUT
    # --------------------------------------------------------

    expected_shape = (
        n_cells,
        config.n_components,
    )

    if embedding.shape != expected_shape:
        raise RuntimeError(
            "Unexpected UMAP embedding shape. "
            f"Expected {expected_shape}, "
            f"got {embedding.shape}."
        )

    if not np.all(
        np.isfinite(embedding)
    ):
        raise RuntimeError(
            "UMAP embedding contains "
            "non-finite values."
        )

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    embedding_output = (
        output_dir
        / "umap_coordinates.npy"
    )

    np.save(
        embedding_output,
        embedding,
    )

    # --------------------------------------------------------
    # RESULT
    # --------------------------------------------------------

    return {

        "method": "Uniform Manifold Approximation and Projection",

        "input_cells": int(n_cells),

        "input_pca_components": int(n_pcs),

        "n_components": int(
            config.n_components
        ),

        "n_neighbors": int(
            config.n_neighbors
        ),

        "min_dist": float(
            config.min_dist
        ),

        "metric": config.metric,

        "embedding_shape": [
            int(embedding.shape[0]),
            int(embedding.shape[1]),
        ],

        "embedding_output": str(
            embedding_output
        ),
    }