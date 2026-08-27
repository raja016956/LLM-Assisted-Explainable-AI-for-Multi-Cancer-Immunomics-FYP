from __future__ import annotations

from pathlib import Path

import numpy as np
import scipy.sparse as sp

from app.pipeline.io import inspect_expression_matrix

from app.pipeline.qc import (
    QCConfig,
    calculate_streaming_qc,
)

from app.pipeline.normalization import (
    run_memory_safe_normalization,
)

from app.pipeline.feature_selection import (
    FeatureSelectionConfig,
    select_highly_variable_genes,
)

from app.pipeline.pca import (
    PCAConfig,
    run_pca,
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DATASET = (
    BASE_DIR
    / "GSM5161291_D37_2_counts.txt.gz"
)

ANALYSIS_DIR = (
    BASE_DIR
    / "analysis_data"
)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print(
        "IMMUNO-XAI QC + NORMALIZATION + "
        "FEATURE SELECTION + PCA TEST"
    )
    print("=" * 70)

    # ========================================================
    # DATASET
    # ========================================================

    info = inspect_expression_matrix(
        DATASET
    )

    original_cells = info.n_cells
    original_genes = info.n_genes

    print()
    print("DATASET")
    print("-" * 70)

    print(
        f"Genes:  {original_genes:,}"
    )

    print(
        f"Cells:  {original_cells:,}"
    )

    # ========================================================
    # STEP 1 — QC
    # ========================================================

    print()
    print("STEP 1 — QUALITY CONTROL")
    print("-" * 70)

    qc_config = QCConfig(
        min_umis=1000,
        min_genes=200,
        max_mito_fraction=0.20,
    )

    qc_result = calculate_streaming_qc(
        DATASET,
        config=qc_config,
    )

    keep_cell_indices = qc_result.get(
        "keep_cell_indices",
        [],
    )

    cells_after_qc = qc_result.get(
        "cells_after",
        qc_result.get(
            "retained_cell_count",
            len(keep_cell_indices),
        ),
    )

    cells_before_qc = qc_result.get(
        "cells_before",
        original_cells,
    )

    cells_removed = (
        cells_before_qc
        - cells_after_qc
    )

    print(
        f"Cells before QC: {cells_before_qc:,}"
    )

    print(
        f"Cells after QC:  {cells_after_qc:,}"
    )

    print(
        f"Cells removed:   {cells_removed:,}"
    )

    print(
        f"Passing cells:   {len(keep_cell_indices):,}"
    )

    # ========================================================
    # STEP 2 — NORMALIZATION
    # ========================================================

    print()
    print(
        "STEP 2 — MEMORY-SAFE NORMALIZATION"
    )
    print("-" * 70)

    normalization_dir = (
        ANALYSIS_DIR
        / "normalization"
    )

    normalization_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    normalization_result = (
        run_memory_safe_normalization(
            DATASET,
            normalization_dir,
            chunk_cells=250,
            target_sum=10_000,
            keep_cell_indices=keep_cell_indices,
        )
    )

    normalized_output = (
        normalization_result[
            "normalized"
        ][
            "output_file"
        ]
    )

    normalized_matrix = sp.load_npz(
        normalized_output
    )

    normalized_cells = (
        normalized_matrix.shape[1]
    )

    print()
    print(
        "Normalized matrix:"
    )

    print(
        normalized_output
    )

    print()
    print(
        f"Normalized cells: "
        f"{normalized_cells:,}"
    )

    print(
        f"Expected QC cells: "
        f"{cells_after_qc:,}"
    )

    if normalized_cells != cells_after_qc:

        raise RuntimeError(
            "Normalization cell count does not "
            "match QC retained cell count."
        )

    # ========================================================
    # STEP 3 — FEATURE SELECTION
    # ========================================================

    print()
    print(
        "STEP 3 — HIGHLY VARIABLE GENE SELECTION"
    )
    print("-" * 70)

    feature_dir = (
        ANALYSIS_DIR
        / "feature_selection"
    )

    feature_config = FeatureSelectionConfig(
        n_top_genes=2000,
        min_cells=3,
    )

    feature_result = (
        select_highly_variable_genes(
            normalized_output,
            feature_dir,
            config=feature_config,
        )
    )

    selected_output = (
        feature_result[
            "matrix_output"
        ]
    )

    selected_genes = (
        feature_result[
            "selected_genes"
        ]
    )

    eligible_genes = (
        feature_result[
            "eligible_genes"
        ]
    )

    feature_cells = (
        feature_result[
            "cells"
        ]
    )

    print()
    print(
        f"Original genes:   "
        f"{original_genes:,}"
    )

    print(
        f"Eligible genes:   "
        f"{eligible_genes:,}"
    )

    print(
        f"Selected genes:   "
        f"{selected_genes:,}"
    )

    print(
        f"Cells:            "
        f"{feature_cells:,}"
    )

    print()
    print(
        "Selected matrix:"
    )

    print(
        selected_output
    )

    # ========================================================
    # STEP 4 — PCA
    # ========================================================

    print()
    print(
        "STEP 4 — PRINCIPAL COMPONENT ANALYSIS"
    )
    print("-" * 70)

    pca_dir = (
        ANALYSIS_DIR
        / "pca"
    )

    pca_config = PCAConfig(
        n_components=50,
        random_state=42,
    )

    pca_result = run_pca(
        selected_output,
        pca_dir,
        config=pca_config,
    )

    print()
    print(
        f"PCA input genes:  "
        f"{pca_result['input_genes']:,}"
    )

    print(
        f"PCA input cells:  "
        f"{pca_result['input_cells']:,}"
    )

    print(
        f"Components:        "
        f"{pca_result['n_components']:,}"
    )

    print(
        f"Embedding shape:   "
        f"{pca_result['embedding_shape']}"
    )

    print(
        f"Loading shape:     "
        f"{pca_result['loading_shape']}"
    )

    print()
    print(
        "PCA coordinates:"
    )

    print(
        pca_result[
            "embeddings_output"
        ]
    )

    print()
    print(
        "PCA loadings:"
    )

    print(
        pca_result[
            "loadings_output"
        ]
    )

    print()
    print(
        "Explained variance ratio:"
    )

    print(
        f"{pca_result['explained_variance_ratio_sum']:.6f}"
    )

    # ========================================================
    # STEP 5 — CONSISTENCY CHECK
    # ========================================================

    print()
    print(
        "STEP 5 — CONSISTENCY CHECK"
    )
    print("-" * 70)

    consistency_ok = True

    # QC → normalization
    if normalized_cells != cells_after_qc:
        consistency_ok = False

    # Normalization → feature selection
    if feature_cells != normalized_cells:
        consistency_ok = False

    # Feature selection gene count
    if selected_genes != feature_config.n_top_genes:
        consistency_ok = False

    # PCA input dimensions
    if pca_result["input_cells"] != normalized_cells:
        consistency_ok = False

    if pca_result["input_genes"] != selected_genes:
        consistency_ok = False

    # PCA embedding dimensions
    if pca_result["embedding_shape"][0] != cells_after_qc:
        consistency_ok = False

    if pca_result["embedding_shape"][1] != 50:
        consistency_ok = False

    # PCA loading dimensions
    if pca_result["loading_shape"][0] != 50:
        consistency_ok = False

    if pca_result["loading_shape"][1] != selected_genes:
        consistency_ok = False

    if consistency_ok:

        print()
        print(
            "✓ QC → normalization → "
            "feature selection → PCA "
            "consistency check PASSED"
        )

    else:

        print()
        print(
            "✗ Pipeline consistency check FAILED"
        )

        raise RuntimeError(
            "QC, normalization, feature selection "
            "and PCA dimensions are inconsistent."
        )

    # ========================================================
    # PIPELINE DIMENSIONS
    # ========================================================

    print()
    print("Pipeline dimensions:")

    print(
        f"  Original cells:       "
        f"{original_cells:,}"
    )

    print(
        f"  QC retained cells:    "
        f"{cells_after_qc:,}"
    )

    print(
        f"  Normalized cells:     "
        f"{normalized_cells:,}"
    )

    print(
        f"  Original genes:       "
        f"{original_genes:,}"
    )

    print(
        f"  Eligible genes:       "
        f"{eligible_genes:,}"
    )

    print(
        f"  Selected genes:       "
        f"{selected_genes:,}"
    )

    print(
        f"  PCA components:       "
        f"{pca_result['n_components']:,}"
    )

    print(
        f"  PCA embedding:        "
        f"{pca_result['embedding_shape']}"
    )

    print()
    print("=" * 70)
    print(
        "PCA TEST COMPLETE"
    )
    print("=" * 70)


if __name__ == "__main__":
    main()