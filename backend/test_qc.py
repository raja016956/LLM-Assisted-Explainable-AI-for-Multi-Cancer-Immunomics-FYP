from pathlib import Path

from app.pipeline.qc import (
    QCConfig,
    calculate_streaming_qc,
    print_qc_report,
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DATASET = (
    BASE_DIR
    / "GSM5161291_D37_2_counts.txt.gz"
)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("IMMUNO-XAI QC TEST")
    print("=" * 70)

    print()
    print("Dataset:")
    print(DATASET.name)

    # --------------------------------------------------------
    # Check dataset
    # --------------------------------------------------------

    if not DATASET.exists():

        print()
        print("Dataset not found:")
        print(DATASET)

        print()
        print("Expected location:")
        print(BASE_DIR)

        return

    # --------------------------------------------------------
    # QC configuration
    # --------------------------------------------------------

    config = QCConfig(
        min_umis=1000,
        min_genes=200,
        max_mito_fraction=0.20,
    )

    print()
    print("QC configuration:")
    print(
        f"  Minimum UMIs/cell:       "
        f"{config.min_umis:,}"
    )

    print(
        f"  Minimum genes/cell:      "
        f"{config.min_genes:,}"
    )

    print(
        f"  Maximum mitochondrial:   "
        f"{config.max_mito_fraction:.1%}"
    )

    print()
    print("Running streaming QC...")
    print(
        "The expression matrix will be processed "
        "row-by-row without loading the full matrix into RAM."
    )
    print()

    # --------------------------------------------------------
    # Run QC
    # --------------------------------------------------------

    result = calculate_streaming_qc(
        DATASET,
        config=config,
    )

    # --------------------------------------------------------
    # Print full QC report
    # --------------------------------------------------------

    print_qc_report(result)

    # --------------------------------------------------------
    # Verify retained cells
    # --------------------------------------------------------

    keep_indices = result[
        "keep_cell_indices"
    ]

    keep_names = result[
        "keep_cell_names"
    ]

    print()
    print("DOWNSTREAM FILTERING INFORMATION")
    print("-" * 70)

    print(
        f"Original cells:          "
        f"{len(result['cell_names']):,}"
    )

    print(
        f"Retained cells:          "
        f"{len(keep_indices):,}"
    )

    print(
        f"Removed cells:           "
        f"{len(result['cell_names']) - len(keep_indices):,}"
    )

    print()
    print("First retained cell indices:")

    for index in keep_indices[:10]:
        print(f"  {int(index)}")

    print()
    print("First retained cell names:")

    for name in keep_names[:10]:
        print(f"  {name}")

    print()
    print("=" * 70)
    print("QC TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()