from __future__ import annotations

from pathlib import Path

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
# MAIN TEST
# ============================================================

def main():

    print("=" * 70)
    print(
        "IMMUNO-XAI QC + NORMALIZATION + "
        "FEATURE SELECTION TEST"
    )
    print("=" * 70)

    # ========================================================
    # STEP 0 — DATASET INSPECTION
    # ========================================================

    info = inspect_expression_matrix(
        DATASET
    )

    original_cells = int(
        info.n_cells
    )

    original_genes = int(
        info.n_genes
    )

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
    # STEP 1 — QUALITY CONTROL
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

    # --------------------------------------------------------
    # Get retained cells
    # --------------------------------------------------------

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

    cells_after_qc = int(
        cells_after_qc
    )

    cells_before_qc = qc_result.get(
        "cells_before",
        original_cells,
    )

    cells_before_qc = int(
        cells_before_qc
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

    # --------------------------------------------------------
    # QC consistency
    # --------------------------------------------------------

    if cells_after_qc != len(
        keep_cell_indices
    ):
        raise RuntimeError(
            "QC inconsistency: "
            "cells_after does not match "
            "keep_cell_indices."
        )

    # ========================================================
    # STEP 2 — MEMORY-SAFE NORMALIZATION
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

    # --------------------------------------------------------
    # Extract normalization results
    # --------------------------------------------------------

    raw_result = normalization_result[
        "raw"
    ]

    normalized_result = normalization_result[
        "normalized"
    ]

    normalized_output = (
        normalized_result[
            "output_file"
        ]
    )

    normalized_cells = int(
        normalized_result.get(
            "cells",
            raw_result["cells"],
        )
    )

    raw_cells = int(
        raw_result["cells"]
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

    # --------------------------------------------------------
    # Normalization consistency
    # --------------------------------------------------------

    if normalized_cells != cells_after_qc:
        raise RuntimeError(
            "Normalization inconsistency: "
            "normalized cell count does not "
            "match QC retained cells."
        )

    if raw_cells != cells_after_qc:
        raise RuntimeError(
            "Normalization inconsistency: "
            "raw filtered matrix cell count "
            "does not match QC retained cells."
        )

    # ========================================================
    # STEP 3 — HIGHLY VARIABLE GENE SELECTION
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

    feature_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    feature_config = (
        FeatureSelectionConfig(
            n_top_genes=2000,
            min_cells=3,
        )
    )

    feature_result = (
        select_highly_variable_genes(
            normalized_output,
            feature_dir,
            config=feature_config,
        )
    )

    # --------------------------------------------------------
    # Extract feature-selection results
    # --------------------------------------------------------

    selected_genes = int(
        feature_result[
            "selected_genes"
        ]
    )

    eligible_genes = int(
        feature_result[
            "eligible_genes"
        ]
    )

    feature_cells = int(
        feature_result[
            "cells"
        ]
    )

    nonzero_entries = int(
        feature_result[
            "nonzero_entries"
        ]
    )

    selected_output = (
        feature_result[
            "matrix_output"
        ]
    )

    indices_output = (
        feature_result[
            "indices_output"
        ]
    )

    variance_output = (
        feature_result[
            "variance_output"
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

    print(
        f"Non-zero entries: "
        f"{nonzero_entries:,}"
    )

    print()
    print(
        "Selected matrix:"
    )

    print(
        selected_output
    )

    print()
    print(
        "Selected gene indices:"
    )

    print(
        indices_output
    )

    print()
    print(
        "Gene variances:"
    )

    print(
        variance_output
    )

    # ========================================================
    # STEP 4 — CONSISTENCY CHECK
    # ========================================================

    print()
    print(
        "STEP 4 — CONSISTENCY CHECK"
    )
    print("-" * 70)

    consistency_ok = True

    # --------------------------------------------------------
    # QC → normalization
    # --------------------------------------------------------

    if cells_after_qc != len(
        keep_cell_indices
    ):
        consistency_ok = False

    if normalized_cells != cells_after_qc:
        consistency_ok = False

    # --------------------------------------------------------
    # normalization → feature selection
    # --------------------------------------------------------

    if feature_cells != normalized_cells:
        consistency_ok = False

    # --------------------------------------------------------
    # feature count
    # --------------------------------------------------------

    expected_selected = min(
        feature_config.n_top_genes,
        eligible_genes,
    )

    if selected_genes != expected_selected:
        consistency_ok = False

    # --------------------------------------------------------
    # gene count
    # --------------------------------------------------------

    if eligible_genes > original_genes:
        consistency_ok = False

    if selected_genes > eligible_genes:
        consistency_ok = False

    # ========================================================
    # RESULT
    # ========================================================

    if consistency_ok:

        print()
        print(
            "✓ QC → normalization → "
            "feature selection consistency "
            "check PASSED"
        )

    else:

        print()
        print(
            "✗ Pipeline consistency check FAILED"
        )

        raise RuntimeError(
            "QC, normalization and feature "
            "selection dimensions are inconsistent."
        )

    # ========================================================
    # PIPELINE DIMENSIONS
    # ========================================================

    print()
    print(
        "Pipeline dimensions:"
    )

    print(
        f"  Original cells:       "
        f"{cells_before_qc:,}"
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

    # ========================================================
    # FINAL
    # ========================================================

    print()
    print("=" * 70)
    print(
        "FEATURE SELECTION TEST COMPLETE"
    )
    print("=" * 70)


if __name__ == "__main__":
    main()