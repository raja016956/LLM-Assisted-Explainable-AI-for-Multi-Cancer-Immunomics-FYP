from __future__ import annotations

import gzip
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import scipy.sparse as sp


# ============================================================
# CONFIGURATION
# ============================================================

@dataclass
class NormalizationConfig:
    chunk_cells: int = 500
    target_sum: float = 10_000.0


# ============================================================
# FILE HELPERS
# ============================================================

# Handles the  open text step in the normalization stage.
def _open_text(path: Path):
    """Open plain-text or gzip-compressed text files."""

    path = Path(path)

    if str(path).lower().endswith(".gz"):
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


# Handles the  detect delimiter step in the normalization stage.
def _detect_delimiter(header: str) -> str:
    """Detect common expression-matrix delimiters."""

    if "\t" in header:
        return "\t"

    if "," in header:
        return ","

    return "\t"


# ============================================================
# MATRIX HEADER
# ============================================================

# Handles the read matrix header step in the normalization stage.
def read_matrix_header(
    matrix_path: Path,
) -> dict[str, Any]:
    """
    Read only the header of a gene × cell expression matrix.
    """

    matrix_path = Path(matrix_path)

    with _open_text(matrix_path) as handle:

        header = handle.readline().rstrip(
            "\r\n"
        )

        if not header:
            raise ValueError(
                "Expression matrix is empty."
            )

        delimiter = _detect_delimiter(
            header
        )

        columns = header.split(
            delimiter
        )

        if len(columns) < 2:
            raise ValueError(
                "Expression matrix must contain "
                "at least one gene column and "
                "one cell column."
            )

        gene_column = columns[0]

        cells = columns[1:]

        return {
            "delimiter": delimiter,
            "gene_column": gene_column,
            "cells": cells,
            "cell_count": len(cells),
        }


# ============================================================
# MATRIX METADATA
# ============================================================

# Handles the  read matrix metadata step in the normalization stage.
def _read_matrix_metadata(
    matrix_path: Path,
) -> tuple[str, str, list[str]]:

    info = read_matrix_header(
        matrix_path
    )

    return (
        info["delimiter"],
        info["gene_column"],
        info["cells"],
    )


# Handles the  count genes step in the normalization stage.
def _count_genes(
    matrix_path: Path,
) -> int:
    """Count genes without loading the matrix."""

    count = 0

    with _open_text(matrix_path) as handle:

        handle.readline()

        for line in handle:

            if line.strip():
                count += 1

    return count


# ============================================================
# RETAINED-CELL LOOKUP
# ============================================================

# Handles the  prepare cell selection step in the normalization stage.
def _prepare_cell_selection(
    total_cells: int,
    keep_cell_indices: Sequence[int] | None,
) -> tuple[np.ndarray, np.ndarray]:

    if keep_cell_indices is None:

        original_indices = np.arange(
            total_cells,
            dtype=np.int32,
        )

        selected_mask = np.ones(
            total_cells,
            dtype=bool,
        )

        return (
            selected_mask,
            original_indices,
        )

    indices = np.asarray(
        keep_cell_indices,
        dtype=np.int32,
    )

    if indices.size == 0:
        raise ValueError(
            "No cells passed QC. "
            "Normalization cannot continue."
        )

    if np.any(indices < 0):
        raise ValueError(
            "QC cell indices cannot be negative."
        )

    if np.any(indices >= total_cells):
        raise ValueError(
            "QC cell index exceeds the number "
            "of cells in the expression matrix."
        )

    # Remove duplicates and sort.
    indices = np.unique(indices)

    selected_mask = np.zeros(
        total_cells,
        dtype=bool,
    )

    selected_mask[indices] = True

    return (
        selected_mask,
        indices,
    )


# ============================================================
# STREAMING MATRIX CONVERSION
# ============================================================

# Handles the create disk backed matrix step in the normalization stage.
def create_disk_backed_matrix(
    matrix_path: Path,
    output_dir: Path,
    chunk_cells: int = 500,
    keep_cell_indices: Sequence[int] | None = None,
) -> dict[str, Any]:
    """
    Convert an expression matrix into a sparse NPZ matrix.

    If keep_cell_indices is provided, only those cells are
    retained. This allows QC filtering to happen BEFORE
    normalization.

    Input:

        genes × all cells

    Output:

        genes × retained cells
    """

    matrix_path = Path(matrix_path)
    output_dir = Path(output_dir)

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    delimiter, gene_column, cells = (
        _read_matrix_metadata(
            matrix_path
        )
    )

    total_cell_count = len(cells)

    (
        selected_mask,
        selected_original_indices,
    ) = _prepare_cell_selection(
        total_cell_count,
        keep_cell_indices,
    )

    selected_cells = [
        cells[index]
        for index in selected_original_indices
    ]

    selected_position = np.full(
        total_cell_count,
        -1,
        dtype=np.int32,
    )

    selected_position[
        selected_original_indices
    ] = np.arange(
        len(selected_original_indices),
        dtype=np.int32,
    )

    genes: list[str] = []

    rows: list[int] = []
    cols: list[int] = []
    values: list[float] = []

    nonzero_entries = 0

    gene_index = 0

    with _open_text(matrix_path) as handle:

        # Skip header.
        handle.readline()

        for line in handle:

            line = line.rstrip(
                "\r\n"
            )

            if not line:
                continue

            parts = line.split(
                delimiter
            )

            if len(parts) < 2:
                continue

            gene = parts[0]

            genes.append(gene)

            expression_values = parts[1:]

            if len(expression_values) > total_cell_count:

                expression_values = (
                    expression_values[
                        :total_cell_count
                    ]
                )

            for original_cell_index, raw_value in enumerate(
                expression_values
            ):

                # Ignore cells removed during QC.
                if not selected_mask[
                    original_cell_index
                ]:
                    continue

                if not raw_value:
                    continue

                try:
                    value = float(
                        raw_value
                    )

                except ValueError:
                    value = 0.0

                if value == 0:
                    continue

                # Convert original cell position
                # to its new filtered position.
                filtered_cell_index = (
                    selected_position[
                        original_cell_index
                    ]
                )

                rows.append(
                    gene_index
                )

                cols.append(
                    int(
                        filtered_cell_index
                    )
                )

                values.append(
                    value
                )

                nonzero_entries += 1

            gene_index += 1

    gene_count = len(genes)

    if gene_count == 0:
        raise ValueError(
            "No genes were found in the "
            "expression matrix."
        )

    retained_cell_count = len(
        selected_original_indices
    )

    # --------------------------------------------------------
    # Construct sparse matrix
    # --------------------------------------------------------

    matrix = sp.coo_matrix(
        (
            np.asarray(
                values,
                dtype=np.float32,
            ),
            (
                np.asarray(
                    rows,
                    dtype=np.int32,
                ),
                np.asarray(
                    cols,
                    dtype=np.int32,
                ),
            ),
        ),
        shape=(
            gene_count,
            retained_cell_count,
        ),
        dtype=np.float32,
    ).tocsr()

    # --------------------------------------------------------
    # Save raw sparse matrix
    # --------------------------------------------------------

    raw_matrix_path = (
        output_dir
        / "raw_counts.npz"
    )

    sp.save_npz(
        raw_matrix_path,
        matrix,
    )

    # --------------------------------------------------------
    # Save genes
    # --------------------------------------------------------

    genes_path = (
        output_dir
        / "genes.json"
    )

    with open(
        genes_path,
        "w",
        encoding="utf-8",
    ) as handle:

        json.dump(
            genes,
            handle,
        )

    # --------------------------------------------------------
    # Save RETAINED cells
    # --------------------------------------------------------

    cells_path = (
        output_dir
        / "cells.json"
    )

    with open(
        cells_path,
        "w",
        encoding="utf-8",
    ) as handle:

        json.dump(
            selected_cells,
            handle,
        )

    # --------------------------------------------------------
    # Save original indices
    # --------------------------------------------------------

    indices_path = (
        output_dir
        / "retained_cell_indices.json"
    )

    with open(
        indices_path,
        "w",
        encoding="utf-8",
    ) as handle:

        json.dump(
            selected_original_indices.tolist(),
            handle,
        )

    return {
        "output_file": str(
            raw_matrix_path
        ),

        "genes_file": str(
            genes_path
        ),

        "cells_file": str(
            cells_path
        ),

        "retained_indices_file": str(
            indices_path
        ),

        "genes": gene_count,

        "cells": retained_cell_count,

        "original_cells": total_cell_count,

        "cells_removed": (
            total_cell_count
            - retained_cell_count
        ),

        "nonzero_entries": (
            nonzero_entries
        ),

        "gene_column": gene_column,
    }


# ============================================================
# NORMALIZATION
# ============================================================

# Handles the normalize disk matrix step in the normalization stage.
def normalize_disk_matrix(
    raw_matrix_path: Path,
    output_dir: Path,
    target_sum: float = 10_000.0,
) -> dict[str, Any]:
    """
    Library-size normalization followed by log1p.

    The matrix remains sparse.
    """

    raw_matrix_path = Path(
        raw_matrix_path
    )

    output_dir = Path(
        output_dir
    )

    matrix = sp.load_npz(
        raw_matrix_path
    ).tocsr()

    matrix = matrix.astype(
        np.float32
    )

    # --------------------------------------------------------
    # Library size per retained cell
    # --------------------------------------------------------

    library_sizes = np.asarray(
        matrix.sum(
            axis=0
        )
    ).ravel()

    nonzero_cells = (
        library_sizes > 0
    )

    # --------------------------------------------------------
    # Scale factors
    # --------------------------------------------------------

    scale_factors = np.zeros_like(
        library_sizes,
        dtype=np.float32,
    )

    scale_factors[
        nonzero_cells
    ] = (
        target_sum
        / library_sizes[
            nonzero_cells
        ]
    )

    # --------------------------------------------------------
    # Normalize columns
    # --------------------------------------------------------

    normalized = (
        matrix
        @ sp.diags(
            scale_factors,
            offsets=0,
            format="csr",
        )
    )

    # --------------------------------------------------------
    # log1p only non-zero values
    # --------------------------------------------------------

    normalized.data = (
        np.log1p(
            normalized.data
        ).astype(
            np.float32
        )
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    normalized_path = (
        output_dir
        / "normalized_log1p.npz"
    )

    sp.save_npz(
        normalized_path,
        normalized,
    )

    return {
        "output_file": str(
            normalized_path
        ),

        "cells": int(
            matrix.shape[1]
        ),

        "genes": int(
            matrix.shape[0]
        ),

        "mean_library_size_before": float(
            np.mean(
                library_sizes
            )
        ),

        "median_library_size_before": float(
            np.median(
                library_sizes
            )
        ),

        "min_library_size_before": float(
            np.min(
                library_sizes
            )
        ),

        "max_library_size_before": float(
            np.max(
                library_sizes
            )
        ),

        "target_sum": float(
            target_sum
        ),
    }


# ============================================================
# COMPLETE NORMALIZATION PIPELINE
# ============================================================

# Handles the run memory safe normalization step in the normalization stage.
def run_memory_safe_normalization(
    matrix_path: Path,
    output_dir: Path,
    chunk_cells: int = 500,
    target_sum: float = 10_000.0,
    keep_cell_indices: Sequence[int] | None = None,
) -> dict[str, Any]:
    """
    Complete memory-conscious normalization pipeline.

    If keep_cell_indices is provided, normalization operates
    ONLY on cells that passed QC.

    Steps:

        1. Read expression matrix
        2. Select QC-passing cells
        3. Convert filtered matrix to sparse CSR
        4. Save raw filtered sparse counts
        5. Calculate library sizes
        6. Library-size normalize
        7. Apply log1p
        8. Save normalized sparse matrix
    """

    matrix_path = Path(
        matrix_path
    )

    output_dir = Path(
        output_dir
    )

    if not matrix_path.exists():

        raise FileNotFoundError(
            f"Dataset not found: "
            f"{matrix_path}"
        )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    # ========================================================
    # STEP 1
    # ========================================================

    print()
    print("-" * 70)
    print("STEP 1 — READING MATRIX")
    print("-" * 70)

    header = read_matrix_header(
        matrix_path
    )

    print(
        f"Cells detected: "
        f"{header['cell_count']:,}"
    )

    print(
        f"Gene column:    "
        f"{header['gene_column']}"
    )

    if keep_cell_indices is not None:

        print(
            f"QC-retained cells: "
            f"{len(keep_cell_indices):,}"
        )

    # ========================================================
    # STEP 2
    # ========================================================

    print()
    print("-" * 70)
    print("STEP 2 — BUILDING FILTERED SPARSE MATRIX")
    print("-" * 70)

    raw = create_disk_backed_matrix(
        matrix_path,
        output_dir,
        chunk_cells=chunk_cells,
        keep_cell_indices=keep_cell_indices,
    )

    print(
        f"Genes:          "
        f"{raw['genes']:,}"
    )

    print(
        f"Original cells: "
        f"{raw['original_cells']:,}"
    )

    print(
        f"Retained cells: "
        f"{raw['cells']:,}"
    )

    print(
        f"Removed cells:  "
        f"{raw['cells_removed']:,}"
    )

    print(
        f"Non-zero:       "
        f"{raw['nonzero_entries']:,}"
    )

    # ========================================================
    # STEP 3
    # ========================================================

    print()
    print("-" * 70)
    print("STEP 3 — NORMALIZATION")
    print("-" * 70)

    normalized = (
        normalize_disk_matrix(
            raw["output_file"],
            output_dir,
            target_sum=target_sum,
        )
    )

    print(
        f"Cells normalized: "
        f"{normalized['cells']:,}"
    )

    print(
        f"Mean library:     "
        f"{normalized['mean_library_size_before']:,.2f}"
    )

    print(
        f"Median library:   "
        f"{normalized['median_library_size_before']:,.2f}"
    )

    print()
    print(
        "Normalization complete."
    )

    return {
        "raw": raw,
        "normalized": normalized,
    }


# ============================================================
# DIRECT EXECUTION
# ============================================================

if __name__ == "__main__":

    BASE_DIR = (
        Path(__file__)
        .resolve()
        .parents[2]
    )

    DATASET = (
        BASE_DIR
        / "GSM5161291_D37_2_counts.txt.gz"
    )

    OUTPUT_DIR = (
        BASE_DIR
        / "analysis_data"
    )

    if not DATASET.exists():

        print(
            "Dataset not found:"
        )

        print(DATASET)

        raise SystemExit(1)

    run_memory_safe_normalization(
        DATASET,
        OUTPUT_DIR,
        chunk_cells=500,
        target_sum=10_000,
    )