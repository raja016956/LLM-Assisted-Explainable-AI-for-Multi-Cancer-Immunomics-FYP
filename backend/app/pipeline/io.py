from __future__ import annotations

import csv
import gzip
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import numpy as np


# ============================================================
# DATA STRUCTURES
# ============================================================

@dataclass
class MatrixInfo:
    filename: str
    format: str
    compression: str
    n_genes: int
    n_cells: int
    gene_column: str
    first_genes: list[str]
    first_cells: list[str]


@dataclass
class QCStats:
    n_genes: int
    n_cells: int
    total_umis: int

    median_umis_per_cell: float
    mean_umis_per_cell: float

    median_genes_per_cell: float
    mean_genes_per_cell: float

    mitochondrial_umis: int
    mitochondrial_fraction: float

    min_umis_per_cell: int
    max_umis_per_cell: int

    min_genes_per_cell: int
    max_genes_per_cell: int


# ============================================================
# OPEN MATRIX
# ============================================================

def open_expression_matrix(path: str | Path):
    """
    Open a plain-text or gzip-compressed expression matrix.
    """

    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            f"Expression matrix not found: {path}"
        )

    if path.suffix.lower() == ".gz":
        return gzip.open(
            path,
            mode="rt",
            encoding="utf-8",
            newline="",
        )

    return path.open(
        mode="r",
        encoding="utf-8",
        newline="",
    )


# ============================================================
# INSPECT MATRIX
# ============================================================

def inspect_expression_matrix(
    path: str | Path,
    preview_genes: int = 5,
    preview_cells: int = 5,
) -> MatrixInfo:
    """
    Inspect a gene × cell expression matrix.

    Expected structure:

        Index    Cell1    Cell2    Cell3 ...
        GeneA    10       5        0
        GeneB    2        8        4

    The first column contains gene identifiers.
    The remaining columns represent cells.
    """

    path = Path(path)

    with open_expression_matrix(path) as handle:

        reader = csv.reader(
            handle,
            delimiter="\t",
        )

        try:
            header = next(reader)
        except StopIteration:
            raise ValueError(
                "The expression matrix is empty."
            )

        if len(header) < 2:
            raise ValueError(
                "The expression matrix must contain "
                "a gene column and at least one cell column."
            )

        gene_column = header[0]

        cell_names = header[1:]

        first_cells = cell_names[:preview_cells]

        first_genes: list[str] = []

        # Read first few genes
        for _ in range(preview_genes):

            try:
                row = next(reader)
            except StopIteration:
                break

            if not row:
                continue

            first_genes.append(
                row[0]
            )

        # We already consumed the preview rows.
        # Count the remaining rows.
        n_genes = len(first_genes)

        for row in reader:

            if row:
                n_genes += 1

    return MatrixInfo(
        filename=path.name,
        format="tab-delimited",
        compression=(
            "gzip"
            if path.suffix.lower() == ".gz"
            else "none"
        ),
        n_genes=n_genes,
        n_cells=len(cell_names),
        gene_column=gene_column,
        first_genes=first_genes,
        first_cells=first_cells,
    )


# ============================================================
# GET CELL NAMES
# ============================================================

def get_cell_names(
    path: str | Path,
) -> list[str]:
    """
    Return cell/barcode identifiers from the matrix header.
    """

    with open_expression_matrix(path) as handle:

        reader = csv.reader(
            handle,
            delimiter="\t",
        )

        try:
            header = next(reader)
        except StopIteration:
            raise ValueError(
                "The expression matrix is empty."
            )

    if len(header) < 2:
        raise ValueError(
            "No cell columns were found."
        )

    return header[1:]


# ============================================================
# STREAM EXPRESSION ROWS
# ============================================================

def iter_expression_rows(
    path: str | Path,
) -> Iterator[tuple[str, np.ndarray]]:
    """
    Stream the expression matrix one gene at a time.

    This is important for large single-cell datasets.

    We DO NOT load the complete matrix into RAM.
    """

    with open_expression_matrix(path) as handle:

        reader = csv.reader(
            handle,
            delimiter="\t",
        )

        try:
            header = next(reader)
        except StopIteration:
            raise ValueError(
                "The expression matrix is empty."
            )

        expected_cells = len(header) - 1

        for line_number, row in enumerate(
            reader,
            start=2,
        ):

            if not row:
                continue

            gene_name = row[0]

            values = row[1:]

            if len(values) != expected_cells:

                raise ValueError(
                    f"Invalid row at line "
                    f"{line_number}: expected "
                    f"{expected_cells} values, "
                    f"found {len(values)}."
                )

            try:

                counts = np.asarray(
                    values,
                    dtype=np.float64,
                )

            except ValueError as exc:

                raise ValueError(
                    f"Non-numeric expression value "
                    f"at line {line_number} "
                    f"for gene '{gene_name}'."
                ) from exc

            yield gene_name, counts


# ============================================================
# QC
# ============================================================

def calculate_qc_stats(
    path: str | Path,
) -> QCStats:
    """
    Calculate basic single-cell QC metrics.

    Metrics:

        - total UMIs per cell
        - genes detected per cell
        - mitochondrial UMIs
        - mitochondrial fraction
    """

    cell_names = get_cell_names(path)

    n_cells = len(cell_names)

    total_umis = np.zeros(
        n_cells,
        dtype=np.float64,
    )

    detected_genes = np.zeros(
        n_cells,
        dtype=np.int64,
    )

    mitochondrial_umis = np.zeros(
        n_cells,
        dtype=np.float64,
    )

    n_genes = 0

    for gene_name, counts in iter_expression_rows(path):

        n_genes += 1

        # Total UMI count
        total_umis += counts

        # Number of genes detected in each cell
        detected_genes += (
            counts > 0
        )

        # Mitochondrial genes
        normalized_gene = (
            gene_name.strip().upper()
        )

        if (
            normalized_gene.startswith("MT-")
            or normalized_gene.startswith("MT.")
        ):

            mitochondrial_umis += counts

    if n_genes == 0:
        raise ValueError(
            "No genes were found in the expression matrix."
        )

    mitochondrial_fraction = np.divide(
        mitochondrial_umis,
        total_umis,
        out=np.zeros_like(
            mitochondrial_umis
        ),
        where=total_umis > 0,
    )

    return QCStats(

        n_genes=n_genes,

        n_cells=n_cells,

        total_umis=int(
            np.sum(total_umis)
        ),

        median_umis_per_cell=float(
            np.median(total_umis)
        ),

        mean_umis_per_cell=float(
            np.mean(total_umis)
        ),

        median_genes_per_cell=float(
            np.median(detected_genes)
        ),

        mean_genes_per_cell=float(
            np.mean(detected_genes)
        ),

        mitochondrial_umis=int(
            np.sum(mitochondrial_umis)
        ),

        mitochondrial_fraction=float(
            np.sum(mitochondrial_umis)
            / max(
                np.sum(total_umis),
                1,
            )
        ),

        min_umis_per_cell=int(
            np.min(total_umis)
        ),

        max_umis_per_cell=int(
            np.max(total_umis)
        ),

        min_genes_per_cell=int(
            np.min(detected_genes)
        ),

        max_genes_per_cell=int(
            np.max(detected_genes)
        ),
    )


# ============================================================
# VALIDATION
# ============================================================

def validate_expression_matrix(
    path: str | Path,
) -> dict:
    """
    Perform structural validation of the expression matrix.
    """

    info = inspect_expression_matrix(
        path
    )

    errors: list[str] = []
    warnings: list[str] = []

    if info.n_genes == 0:

        errors.append(
            "No genes were detected."
        )

    if info.n_cells == 0:

        errors.append(
            "No cells were detected."
        )

    known_gene_columns = {
        "index",
        "gene",
        "gene_id",
        "geneid",
        "genes",
    }

    if (
        info.gene_column.lower()
        not in known_gene_columns
    ):

        warnings.append(
            f"Gene identifier column is named "
            f"'{info.gene_column}'."
        )

    return {

        "valid": len(errors) == 0,

        "errors": errors,

        "warnings": warnings,

        "matrix": {

            "filename": info.filename,

            "format": info.format,

            "compression": info.compression,

            "genes": info.n_genes,

            "cells": info.n_cells,

            "gene_column": info.gene_column,

            "preview_genes": info.first_genes,

            "preview_cells": info.first_cells,
        },
    }