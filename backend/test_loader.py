from pathlib import Path

from app.pipeline.io import (
    inspect_expression_matrix,
    calculate_qc_stats,
    validate_expression_matrix,
)


DATASET = Path(
    "GSM5161291_D37_2_counts.txt.gz"
)


def main():

    if not DATASET.exists():
        print()
        print("Dataset not found:")
        print(DATASET.resolve())
        print()
        print(
            "Put GSM5161291_D37_2_counts.txt.gz "
            "inside the backend folder."
        )
        return

    print("=" * 70)
    print("IMMUNO-XAI DATASET LOADER TEST")
    print("=" * 70)

    print()
    print("Dataset:")
    print(DATASET)

    print()
    print("1. Structural validation")
    print("-" * 70)

    validation = validate_expression_matrix(
        DATASET
    )

    print(validation)

    if not validation["valid"]:
        print()
        print("Dataset validation failed.")
        return

    print()
    print("2. Matrix inspection")
    print("-" * 70)

    info = inspect_expression_matrix(
        DATASET
    )

    print(
        f"Genes: {info.n_genes:,}"
    )

    print(
        f"Cells: {info.n_cells:,}"
    )

    print(
        f"Gene column: {info.gene_column}"
    )

    print(
        f"Compression: {info.compression}"
    )

    print()
    print("First genes:")

    for gene in info.first_genes:
        print(f"  {gene}")

    print()
    print("First cells:")

    for cell in info.first_cells:
        print(f"  {cell}")

    print()
    print("3. Streaming QC")
    print("-" * 70)

    print(
        "Reading matrix row-by-row..."
    )

    qc = calculate_qc_stats(
        DATASET
    )

    print()
    print(
        f"Genes:                 {qc.n_genes:,}"
    )

    print(
        f"Cells:                 {qc.n_cells:,}"
    )

    print(
        f"Total UMIs:            {qc.total_umis:,}"
    )

    print(
        f"Median UMIs/cell:      {qc.median_umis_per_cell:,.2f}"
    )

    print(
        f"Mean UMIs/cell:        {qc.mean_umis_per_cell:,.2f}"
    )

    print(
        f"Median genes/cell:     {qc.median_genes_per_cell:,.2f}"
    )

    print(
        f"Mean genes/cell:       {qc.mean_genes_per_cell:,.2f}"
    )

    print(
        f"Minimum UMIs/cell:     {qc.min_umis_per_cell:,}"
    )

    print(
        f"Maximum UMIs/cell:     {qc.max_umis_per_cell:,}"
    )

    print(
        f"Minimum genes/cell:    {qc.min_genes_per_cell:,}"
    )

    print(
        f"Maximum genes/cell:    {qc.max_genes_per_cell:,}"
    )

    print(
        f"Mitochondrial UMI:     {qc.mitochondrial_umis:,}"
    )

    print(
        f"Mitochondrial fraction: {qc.mitochondrial_fraction:.4%}"
    )

    print()
    print("=" * 70)
    print("LOADER TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()