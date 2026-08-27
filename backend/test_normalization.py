from pathlib import Path

from app.pipeline.qc import (
    QCConfig,
    calculate_streaming_qc,
)

from app.pipeline.normalization import (
    run_memory_safe_normalization,
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DATASET = (
    BASE_DIR
    / "GSM5161291_D37_2_counts.txt.gz"
)

OUTPUT_DIR = (
    BASE_DIR
    / "analysis_data"
)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("IMMUNO-XAI QC + NORMALIZATION TEST")
    print("=" * 70)

    print()
    print("Dataset:")
    print(DATASET.name)

    if not DATASET.exists():

        print()
        print("Dataset not found:")
        print(DATASET)

        return

    # ========================================================
    # STEP 1 — QC
    # ========================================================

    print()
    print("=" * 70)
    print("STEP 1 — QUALITY CONTROL")
    print("=" * 70)

    config = QCConfig(
        min_umis=1000,
        min_genes=200,
        max_mito_fraction=0.20,
    )

    qc_result = calculate_streaming_qc(
        DATASET,
        config=config,
    )

    cells_before = (
        qc_result["cells"]["before"]
    )

    cells_after = (
        qc_result["cells"]["after"]
    )

    cells_removed = (
        qc_result["cells"]["removed"]
    )

    keep_cell_indices = (
        qc_result["keep_cell_indices"]
    )

    print(
        f"Cells before QC: "
        f"{cells_before:,}"
    )

    print(
        f"Cells after QC:  "
        f"{cells_after:,}"
    )

    print(
        f"Cells removed:   "
        f"{cells_removed:,}"
    )

    print()
    print(
        f"Passing cell indices: "
        f"{len(keep_cell_indices):,}"
    )

    # ========================================================
    # STEP 2 — NORMALIZATION
    # ========================================================

    print()
    print("=" * 70)
    print("STEP 2 — MEMORY-SAFE NORMALIZATION")
    print("=" * 70)

    result = run_memory_safe_normalization(
        DATASET,
        OUTPUT_DIR,
        chunk_cells=250,
        target_sum=10_000,
        keep_cell_indices=keep_cell_indices,
    )

    # ========================================================
    # RESULTS
    # ========================================================

    print()
    print("=" * 70)
    print("RESULT")
    print("=" * 70)

    print()

    print(
        f"Raw filtered matrix:     "
        f"{result['raw']['output_file']}"
    )

    print(
        f"Normalized matrix:       "
        f"{result['normalized']['output_file']}"
    )

    print()

    print(
        f"Genes:                   "
        f"{result['raw']['genes']:,}"
    )

    print(
        f"Original cells:          "
        f"{result['raw']['original_cells']:,}"
    )

    print(
        f"Cells after QC:          "
        f"{result['raw']['cells']:,}"
    )

    print(
        f"Cells removed:           "
        f"{result['raw']['cells_removed']:,}"
    )

    print(
        f"Non-zero entries:        "
        f"{result['raw']['nonzero_entries']:,}"
    )

    print()

    print(
        f"Normalized cells:        "
        f"{result['normalized']['cells']:,}"
    )

    print(
        f"Mean library size:       "
        f"{result['normalized']['mean_library_size_before']:,.2f}"
    )

    print(
        f"Median library size:     "
        f"{result['normalized']['median_library_size_before']:,.2f}"
    )

    print()

    # ========================================================
    # CONSISTENCY CHECK
    # ========================================================

    if (
        result["normalized"]["cells"]
        == cells_after
    ):

        print(
            "✓ QC → normalization consistency check PASSED"
        )

        print(
            f"  QC retained {cells_after:,} cells "
            f"and normalization processed "
            f"{result['normalized']['cells']:,} cells."
        )

    else:

        print(
            "✗ QC → normalization consistency check FAILED"
        )

        print(
            f"  QC retained {cells_after:,} cells "
            f"but normalization processed "
            f"{result['normalized']['cells']:,} cells."
        )

        raise RuntimeError(
            "Normalization cell count does not match "
            "the QC-retained cell count."
        )

    print()
    print("=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()