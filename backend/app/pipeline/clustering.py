from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.cluster import KMeans


# ============================================================
# CONFIGURATION
# ============================================================

@dataclass
class ClusteringConfig:
    n_clusters: int = 10
    random_state: int = 42
    n_init: int = 20


# ============================================================
# CLUSTERING
# ============================================================

def run_clustering(
    pca_coordinates_path: str | Path,
    output_dir: str | Path,
    config: ClusteringConfig | None = None,
) -> dict[str, Any]:
    """
    Cluster cells using their PCA representation.

    Expected input:
        pca_coordinates.npy

    Matrix orientation:
        cells x PCA components

    Example:
        913 cells x 50 PCA components

    Output:
        one cluster label per cell.
    """

    if config is None:
        config = ClusteringConfig()

    pca_coordinates_path = Path(
        pca_coordinates_path
    )

    output_dir = Path(output_dir)

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------------------------------
    # VALIDATE INPUT
    # --------------------------------------------------------

    if not pca_coordinates_path.exists():
        raise FileNotFoundError(
            f"PCA coordinates not found: "
            f"{pca_coordinates_path}"
        )

    # --------------------------------------------------------
    # LOAD PCA EMBEDDING
    # --------------------------------------------------------

    coordinates = np.load(
        pca_coordinates_path
    )

    if coordinates.ndim != 2:
        raise ValueError(
            "PCA coordinates must be a 2-dimensional "
            "cells × components matrix."
        )

    n_cells, n_components = coordinates.shape

    if n_cells == 0 or n_components == 0:
        raise ValueError(
            "PCA coordinates are empty."
        )

    # --------------------------------------------------------
    # VALIDATE CLUSTER COUNT
    # --------------------------------------------------------

    if config.n_clusters < 2:
        raise ValueError(
            "n_clusters must be at least 2."
        )

    if config.n_clusters >= n_cells:
        raise ValueError(
            "n_clusters must be smaller than the "
            "number of cells."
        )

    # --------------------------------------------------------
    # RUN K-MEANS
    # --------------------------------------------------------

    model = KMeans(
        n_clusters=config.n_clusters,
        random_state=config.random_state,
        n_init=config.n_init,
    )

    labels = model.fit_predict(
        coordinates
    )

    # --------------------------------------------------------
    # CLUSTER CENTERS
    # --------------------------------------------------------

    cluster_centers = model.cluster_centers_

    # --------------------------------------------------------
    # CLUSTER SIZES
    # --------------------------------------------------------

    unique_labels, counts = np.unique(
        labels,
        return_counts=True,
    )

    cluster_sizes = {
        str(int(label)): int(count)
        for label, count
        in zip(unique_labels, counts)
    }

    # --------------------------------------------------------
    # SAVE CLUSTER LABELS
    # --------------------------------------------------------

    labels_output = (
        output_dir
        / "cluster_labels.npy"
    )

    centers_output = (
        output_dir
        / "cluster_centers.npy"
    )

    np.save(
        labels_output,
        labels,
    )

    np.save(
        centers_output,
        cluster_centers,
    )

    # --------------------------------------------------------
    # RESULT
    # --------------------------------------------------------

    return {
        "method": "K-means clustering on PCA coordinates",

        "input_cells": int(
            n_cells
        ),

        "input_components": int(
            n_components
        ),

        "n_clusters": int(
            config.n_clusters
        ),

        "random_state": int(
            config.random_state
        ),

        "cluster_sizes": cluster_sizes,

        "labels_shape": [
            int(labels.shape[0])
        ],

        "centers_shape": [
            int(cluster_centers.shape[0]),
            int(cluster_centers.shape[1]),
        ],

        "labels_output": str(
            labels_output
        ),

        "centers_output": str(
            centers_output
        ),
    }