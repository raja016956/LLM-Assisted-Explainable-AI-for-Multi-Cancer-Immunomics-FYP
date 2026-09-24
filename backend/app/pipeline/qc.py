from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import gzip
import math

import numpy as np

# ============================================================
# QC CONFIGURATION
# ============================================================

@dataclass
class QCConfig:
    """
    Quality-control thresholds for single-cell RNA-seq data.
    """

    min_umis: int = 1_000
    min_genes: int = 200
    max_mito_fraction: float = 0.20

# ============================================================
# FILE HANDLING
# ============================================================

def _open_text(path: Path):
    """
    Open a plain-text or gzip-compressed expression matrix.
    """

    path = Path(path)

    if path.suffix.lower() == ".gz":
        return gzip.open(
            path,
            "rt",
            encoding="utf-8",
        )

    return open(
        path,
        "r",
        encoding="utf-8",
    )

# ============================================================
# DELIMITER DETECTION
# ============================================================

def _detect_delimiter(header: str) -> str:
    """
    Detect the delimiter used by the expression matrix.
    """

    if "\t" in header:
        return "\t"

    if "," in header:
        return ","

    return "\t"

# ============================================================
# STREAMING QC
# ============================================================

# Calculates quality-control metrics from the expression matrix using a memory-conscious streaming approach.
def calculate_streaming_qc(
    matrix_path: Path,
    config: QCConfig | None = None,
) -> dict[str, Any]:
    """
    Calculate single-cell QC statistics without loading
    the complete expression matrix into RAM.

    Expected matrix orientation:

        genes × cells

    with genes in rows and cells in columns.

    Returns both QC statistics and the actual cells that
    pass QC so downstream filtering can use exactly the
    same QC decisions.
    """

    matrix_path = Path(matrix_path)

    if not matrix_path.exists():
        raise FileNotFoundError(
            f"Dataset not found: {matrix_path}"
        )

    if config is None:
        config = QCConfig()

    # --------------------------------------------------------
    # Read matrix header
    # --------------------------------------------------------

    with _open_text(matrix_path) as handle:

        header = handle.readline().rstrip("\r\n")

        if not header:
            raise ValueError(
                "Expression matrix is empty."
            )

        delimiter = _detect_delimiter(header)

        columns = header.split(delimiter)

        if len(columns) < 2:
            raise ValueError(
                "Expression matrix must contain "
                "a gene column and at least one cell."
            )

        gene_column = columns[0]
        cells = columns[1:]

    n_cells = len(cells)

    # --------------------------------------------------------
    # Per-cell statistics
    # --------------------------------------------------------

    umi_per_cell = np.zeros(
        n_cells,
        dtype=np.int64,
    )

    genes_per_cell = np.zeros(
        n_cells,
        dtype=np.int32,
    )

    mito_umi_per_cell = np.zeros(
        n_cells,
        dtype=np.int64,
    )

    n_genes = 0

    # --------------------------------------------------------
    # Stream genes row-by-row
    # --------------------------------------------------------

    with _open_text(matrix_path) as handle:

        handle.readline()

        for line in handle:

            line = line.rstrip("\r\n")

            if not line:
                continue

            parts = line.split(delimiter)

            if len(parts) < 2:
                continue

            gene = parts[0]

            is_mito = gene.upper().startswith("MT-")

            values = parts[1:]

            n_genes += 1

            limit = min(
                len(values),
                n_cells,
            )

            for cell_index in range(limit):

                raw_value = values[cell_index]

                if not raw_value:
                    continue

                try:
                    value = float(raw_value)

                except ValueError:
                    continue

                if not math.isfinite(value):
                    continue

                if value <= 0:
                    continue

                # UMI counts are normally integers.
                count = int(round(value))

                if count <= 0:
                    continue

                umi_per_cell[cell_index] += count

                genes_per_cell[cell_index] += 1

                if is_mito:
                    mito_umi_per_cell[cell_index] += count

    # ========================================================
    # DERIVED QC METRICS
    # ========================================================

    total_umis = int(
        umi_per_cell.sum()
    )

    mito_total = int(
        mito_umi_per_cell.sum()
    )

    if total_umis > 0:

        global_mito_fraction = (
            mito_total / total_umis
        )

    else:

        global_mito_fraction = 0.0

    # --------------------------------------------------------
    # Per-cell mitochondrial fraction
    # --------------------------------------------------------

    mito_fraction_per_cell = np.divide(
        mito_umi_per_cell.astype(np.float64),
        umi_per_cell.astype(np.float64),
        out=np.zeros(
            n_cells,
            dtype=np.float64,
        ),
        where=umi_per_cell > 0,
    )

    # ========================================================
    # QC PASS / FAIL
    # ========================================================

    below_min_umis = (
        umi_per_cell < config.min_umis
    )

    below_min_genes = (
        genes_per_cell < config.min_genes
    )

    above_max_mito = (
        mito_fraction_per_cell
        > config.max_mito_fraction
    )

    # True = retain
    # False = remove
    keep_cells = ~(
        below_min_umis
        | below_min_genes
        | above_max_mito
    )

    # --------------------------------------------------------
    # IMPORTANT:
    # Convert the boolean mask into actual original
    # column indices.
    #
    # Example:
    #
    # original cells:
    # 0 1 2 3 4
    #
    # keep:
    # T T F T F
    #
    # retained indices:
    # [0, 1, 3]
    # --------------------------------------------------------

    keep_cell_indices = np.flatnonzero(
        keep_cells
    ).astype(np.int32)

    keep_cell_names = [
        cells[index]
        for index in keep_cell_indices
    ]

    cells_before = n_cells

    cells_after = int(
        keep_cells.sum()
    )

    cells_removed = (
        cells_before - cells_after
    )

    # ========================================================
    # QUANTILES
    # ========================================================

    def quantiles(
        values: np.ndarray,
    ) -> dict[str, float]:

        if values.size == 0:

            return {
                "q01": 0.0,
                "q05": 0.0,
                "q25": 0.0,
                "q50": 0.0,
                "q75": 0.0,
                "q95": 0.0,
                "q99": 0.0,
            }

        q = np.percentile(
            values,
            [
                1,
                5,
                25,
                50,
                75,
                95,
                99,
            ],
        )

        return {
            "q01": float(q[0]),
            "q05": float(q[1]),
            "q25": float(q[2]),
            "q50": float(q[3]),
            "q75": float(q[4]),
            "q95": float(q[5]),
            "q99": float(q[6]),
        }

    umi_quantiles = quantiles(
        umi_per_cell
    )

    gene_quantiles = quantiles(
        genes_per_cell
    )

    mito_quantiles = quantiles(
        mito_fraction_per_cell
    )

    # ========================================================
    # RESULT
    # ========================================================

    return {

        "dataset": {
            "filename": matrix_path.name,
            "format": (
                "tab-delimited"
                if delimiter == "\t"
                else "comma-delimited"
            ),
            "compression": (
                "gzip"
                if matrix_path.suffix.lower() == ".gz"
                else "none"
            ),
            "gene_column": gene_column,
        },

        "cells": {
            "before": cells_before,
            "after": cells_after,
            "removed": cells_removed,
            "retained_fraction": (
                cells_after / cells_before
                if cells_before
                else 0.0
            ),
        },

        "expression": {
            "genes": n_genes,
            "total_umis": total_umis,

            "median_umis_per_cell": float(
                np.median(umi_per_cell)
            ),

            "mean_umis_per_cell": float(
                np.mean(umi_per_cell)
            ),

            "min_umis_per_cell": int(
                np.min(umi_per_cell)
            )
            if n_cells
            else 0,

            "max_umis_per_cell": int(
                np.max(umi_per_cell)
            )
            if n_cells
            else 0,

            "median_genes_per_cell": float(
                np.median(genes_per_cell)
            ),

            "mean_genes_per_cell": float(
                np.mean(genes_per_cell)
            ),

            "min_genes_per_cell": int(
                np.min(genes_per_cell)
            )
            if n_cells
            else 0,

            "max_genes_per_cell": int(
                np.max(genes_per_cell)
            )
            if n_cells
            else 0,
        },

        "distributions": {
            "umis_per_cell": umi_quantiles,
            "genes_per_cell": gene_quantiles,
            "mitochondrial_fraction": mito_quantiles,
        },

        "threshold_diagnostics": {
            "below_min_umis": int(
                below_min_umis.sum()
            ),

            "below_min_genes": int(
                below_min_genes.sum()
            ),

            "above_max_mito": int(
                above_max_mito.sum()
            ),
        },

        "mitochondrial": {
            "umis": mito_total,
            "fraction": global_mito_fraction,
        },

        "filtering": {
            "min_umis": config.min_umis,
            "min_genes": config.min_genes,
            "max_mito_fraction": (
                config.max_mito_fraction
            ),
        },

        # Internal boolean mask.
        "keep_cells": keep_cells,

        # Actual retained column indices.
        "keep_cell_indices": keep_cell_indices,

        # Names of retained cells.
        "keep_cell_names": keep_cell_names,

        # Original cell names.
        "cell_names": cells,
    }

# ============================================================
# REPORT
# ============================================================

def print_qc_report(
    result: dict[str, Any],
) -> None:

    dataset = result["dataset"]
    cells = result["cells"]
    expression = result["expression"]
    distributions = result["distributions"]
    diagnostics = result["threshold_diagnostics"]
    mitochondrial = result["mitochondrial"]
    filtering = result["filtering"]

    print()
    print("=" * 70)
    print("IMMUNO-XAI QUALITY CONTROL REPORT")
    print("=" * 70)

    print(
        f"Dataset:                "
        f"{dataset['filename']}"
    )

    print()
    print("CELL SUMMARY")
    print("-" * 70)

    print(
        f"Cells before QC:        "
        f"{cells['before']:,}"
    )

    print(
        f"Cells after QC:         "
        f"{cells['after']:,}"
    )

    print(
        f"Cells removed:          "
        f"{cells['removed']:,}"
    )

    print(
        f"Cells retained:         "
        f"{cells['retained_fraction']:.2%}"
    )

    print()
    print("EXPRESSION SUMMARY")
    print("-" * 70)

    print(
        f"Genes:                  "
        f"{expression['genes']:,}"
    )

    print(
        f"Total UMIs:             "
        f"{expression['total_umis']:,}"
    )

    print(
        f"Median UMIs/cell:       "
        f"{expression['median_umis_per_cell']:,.2f}"
    )

    print(
        f"Mean UMIs/cell:         "
        f"{expression['mean_umis_per_cell']:,.2f}"
    )

    print(
        f"Median genes/cell:      "
        f"{expression['median_genes_per_cell']:,.2f}"
    )

    print(
        f"Mean genes/cell:        "
        f"{expression['mean_genes_per_cell']:,.2f}"
    )

    print()
    print("QC DISTRIBUTIONS")
    print("-" * 70)

    print("UMIs/cell:")

    for key, value in distributions[
        "umis_per_cell"
    ].items():

        print(
            f"  {key.upper():>3}: "
            f"{value:,.2f}"
        )

    print()
    print("Detected genes/cell:")

    for key, value in distributions[
        "genes_per_cell"
    ].items():

        print(
            f"  {key.upper():>3}: "
            f"{value:,.2f}"
        )

    print()
    print("Mitochondrial fraction/cell:")

    for key, value in distributions[
        "mitochondrial_fraction"
    ].items():

        print(
            f"  {key.upper():>3}: "
            f"{value:.4%}"
        )

    print()
    print("THRESHOLD DIAGNOSTICS")
    print("-" * 70)

    print(
        f"Below minimum UMIs:    "
        f"{diagnostics['below_min_umis']:,}"
    )

    print(
        f"Below minimum genes:   "
        f"{diagnostics['below_min_genes']:,}"
    )

    print(
        f"Above maximum mito:    "
        f"{diagnostics['above_max_mito']:,}"
    )

    print()
    print("MITOCHONDRIAL QC")
    print("-" * 70)

    print(
        f"Mitochondrial UMIs:     "
        f"{mitochondrial['umis']:,}"
    )

    print(
        f"Global mitochondrial:   "
        f"{mitochondrial['fraction']:.4%}"
    )

    print()
    print("CURRENT FILTERING CRITERIA")
    print("-" * 70)

    print(
        f"Minimum UMIs/cell:     "
        f"{filtering['min_umis']:,}"
    )

    print(
        f"Minimum genes/cell:    "
        f"{filtering['min_genes']:,}"
    )

    print(
        f"Maximum mitochondrial: "
        f"{filtering['max_mito_fraction']:.1%}"
    )

    print()
    print(
        f"Retained cell indices:  "
        f"{len(result['keep_cell_indices']):,}"
    )

    print()
    print("=" * 70)
    print("QC COMPLETE")
    print("=" * 70)