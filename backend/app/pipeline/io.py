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
# FILE HELPERS
# ============================================================


def open_expression_matrix(path: str | Path):
    """
    Open a plain-text or gzip-compressed expression matrix.

    Supported:
        .txt
        .tsv
        .csv
        .txt.gz
        .tsv.gz
        .csv.gz
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
            encoding="utf-8-sig",
            newline="",
        )

    return path.open(
        mode="r",
        encoding="utf-8-sig",
        newline="",
    )


def _clean_line(line: str) -> str:
    """
    Remove BOM and surrounding whitespace.
    """

    return line.replace("\ufeff", "").strip()


def _detect_delimiter(line: str) -> str:
    """
    Automatically detect the delimiter used by the matrix.

    Priority:
        1. tab
        2. comma
        3. semicolon
        4. CSV sniffer
        5. tab fallback
    """

    line = line.replace("\ufeff", "")

    tab_count = line.count("\t")
    comma_count = line.count(",")
    semicolon_count = line.count(";")

    counts = {
        "\t": tab_count,
        ",": comma_count,
        ";": semicolon_count,
    }

    delimiter = max(
        counts,
        key=counts.get,
    )

    if counts[delimiter] > 0:
        return delimiter

    try:
        detected = csv.Sniffer().sniff(
            line,
            delimiters="\t,;",
        )

        return detected.delimiter

    except csv.Error:
        return "\t"


def _is_comment_or_empty(line: str) -> bool:
    """
    Detect blank lines and common metadata/comment lines.
    """

    stripped = line.strip()

    if not stripped:
        return True

    if stripped.startswith("#"):
        return True

    return False


def _looks_numeric(value: str) -> bool:
    """
    Determine whether a value looks like a numeric
    expression value.
    """

    value = value.strip()

    if not value:
        return False

    try:
        float(value)
        return True

    except (ValueError, TypeError):
        return False


# ============================================================
# MATRIX LAYOUT DETECTION
# ============================================================


def _read_matrix_layout(
    path: str | Path,
) -> tuple[str, int, list[str]]:
    """
    Detect:

        delimiter
        header line number
        header columns

    The function tolerates:

        - comments
        - blank lines
        - GEO metadata before the matrix
        - UTF-8 BOM
        - comma-separated files
        - tab-separated files
        - semicolon-separated files
    """

    path = Path(path)

    with open_expression_matrix(path) as handle:

        lines: list[str] = []

        for line in handle:

            if _is_comment_or_empty(line):
                continue

            cleaned = line.rstrip("\r\n")

            if cleaned.strip():
                lines.append(cleaned)

            if len(lines) >= 5:
                break

    if not lines:
        raise ValueError(
            "Expression matrix is empty."
        )

    # --------------------------------------------------------
    # Try each candidate line as the header.
    # --------------------------------------------------------

    for index, candidate in enumerate(lines):

        delimiter = _detect_delimiter(
            candidate
        )

        reader = csv.reader(
            [candidate],
            delimiter=delimiter,
        )

        try:
            columns = next(reader)
        except StopIteration:
            continue

        columns = [
            column.strip()
            for column in columns
        ]

        if len(columns) < 2:
            continue

        # ----------------------------------------------------
        # Header plausibility
        # ----------------------------------------------------
        #
        # A valid matrix header should have:
        #
        #   Gene    Cell1    Cell2 ...
        #
        # We reject lines where every field is numeric.
        # ----------------------------------------------------

        if all(
            _looks_numeric(column)
            for column in columns[1:]
        ):
            continue

        return (
            delimiter,
            index,
            columns,
        )

    raise ValueError(
        "Could not detect a valid expression-matrix "
        "header. The file must contain a gene column "
        "followed by one or more cell columns."
    )


def _open_matrix_with_layout(
    path: str | Path,
):
    """
    Open the matrix and return:

        file handle
        CSV reader
        delimiter
        header
    """

    path = Path(path)

    delimiter, header_index, header = (
        _read_matrix_layout(path)
    )

    handle = open_expression_matrix(path)

    # --------------------------------------------------------
    # Skip metadata/comment lines and header position.
    # --------------------------------------------------------

    current_index = -1

    while current_index < header_index:

        line = handle.readline()

        if not line:
            handle.close()

            raise ValueError(
                "Could not locate the expression-matrix header."
            )

        if _is_comment_or_empty(line):
            continue

        current_index += 1

    # The header has already been consumed.
    reader = csv.reader(
        handle,
        delimiter=delimiter,
    )

    return (
        handle,
        reader,
        delimiter,
        header,
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

    Supported examples:

        Gene    Cell1    Cell2    Cell3
        GeneA   10       5        0
        GeneB   2        8        4

    or:

        Gene,Cell1,Cell2,Cell3
        GeneA,10,5,0
        GeneB,2,8,4

    The function automatically detects:
        - delimiter
        - compression
        - metadata/comment lines
    """

    path = Path(path)

    (
        handle,
        reader,
        delimiter,
        header,
    ) = _open_matrix_with_layout(path)

    try:

        if len(header) < 2:
            raise ValueError(
                "The expression matrix must contain "
                "at least one gene column and "
                "one cell column."
            )

        gene_column = (
            header[0].strip()
        )

        cell_names = [
            cell.strip()
            for cell in header[1:]
        ]

        first_cells = cell_names[
            :preview_cells
        ]

        first_genes: list[str] = []

        n_genes = 0

        for row in reader:

            if not row:
                continue

            if not any(
                value.strip()
                for value in row
            ):
                continue

            gene_name = (
                row[0].strip()
                if row
                else ""
            )

            if not gene_name:
                continue

            first_genes.append(
                gene_name
            )

            n_genes += 1

            if len(first_genes) >= preview_genes:
                break

        # ----------------------------------------------------
        # Continue counting remaining genes.
        # ----------------------------------------------------

        for row in reader:

            if not row:
                continue

            if not any(
                value.strip()
                for value in row
            ):
                continue

            if not row[0].strip():
                continue

            n_genes += 1

    finally:
        handle.close()

    format_name = {
        "\t": "tab-delimited",
        ",": "comma-delimited",
        ";": "semicolon-delimited",
    }.get(
        delimiter,
        "delimited",
    )

    return MatrixInfo(
        filename=path.name,
        format=format_name,
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
    Return cell/barcode identifiers from
    the expression-matrix header.
    """

    path = Path(path)

    (
        handle,
        reader,
        delimiter,
        header,
    ) = _open_matrix_with_layout(path)

    try:

        if len(header) < 2:
            raise ValueError(
                "No cell columns were found."
            )

        return [
            cell.strip()
            for cell in header[1:]
        ]

    finally:
        handle.close()


# ============================================================
# STREAM EXPRESSION ROWS
# ============================================================


def iter_expression_rows(
    path: str | Path,
) -> Iterator[tuple[str, np.ndarray]]:
    """
    Stream the expression matrix one gene at a time.

    This keeps the original memory-efficient
    behavior of IMMUNO-XAI.

    The complete matrix is NOT loaded into RAM.
    """

    path = Path(path)

    (
        handle,
        reader,
        delimiter,
        header,
    ) = _open_matrix_with_layout(path)

    expected_cells = len(header) - 1

    try:

        if expected_cells <= 0:
            raise ValueError(
                "No cell columns were found "
                "in the expression matrix."
            )

        for line_number, row in enumerate(
            reader,
            start=2,
        ):

            if not row:
                continue

            if not any(
                value.strip()
                for value in row
            ):
                continue

            gene_name = (
                row[0].strip()
                if row
                else ""
            )

            if not gene_name:
                continue

            values = [
                value.strip()
                for value in row[1:]
            ]

            # ------------------------------------------------
            # Handle accidental trailing empty fields.
            # ------------------------------------------------

            while (
                len(values) > expected_cells
                and values[-1] == ""
            ):
                values.pop()

            if len(values) != expected_cells:

                raise ValueError(
                    f"Invalid expression row for "
                    f"gene '{gene_name}': expected "
                    f"{expected_cells} cell values, "
                    f"found {len(values)}."
                )

            try:

                counts = np.asarray(
                    values,
                    dtype=np.float64,
                )

            except ValueError as exc:

                raise ValueError(
                    "Non-numeric expression value "
                    f"for gene '{gene_name}'."
                ) from exc

            # ------------------------------------------------
            # Reject NaN / infinite values.
            # ------------------------------------------------

            if not np.all(
                np.isfinite(counts)
            ):

                raise ValueError(
                    "Non-finite expression value "
                    f"found for gene '{gene_name}'."
                )

            # ------------------------------------------------
            # Expression counts should not be negative.
            # ------------------------------------------------

            if np.any(counts < 0):

                raise ValueError(
                    "Negative expression value "
                    f"found for gene '{gene_name}'."
                )

            yield (
                gene_name,
                counts,
            )

    finally:
        handle.close()


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

    cell_names = get_cell_names(
        path
    )

    n_cells = len(cell_names)

    if n_cells == 0:
        raise ValueError(
            "No cells were detected."
        )

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

    for gene_name, counts in (
        iter_expression_rows(path)
    ):

        n_genes += 1

        # ----------------------------------------------------
        # Total UMI count
        # ----------------------------------------------------

        total_umis += counts

        # ----------------------------------------------------
        # Number of genes detected
        # ----------------------------------------------------

        detected_genes += (
            counts > 0
        )

        # ----------------------------------------------------
        # Mitochondrial genes
        # ----------------------------------------------------

        normalized_gene = (
            gene_name
            .strip()
            .upper()
        )

        if (
            normalized_gene.startswith("MT-")
            or normalized_gene.startswith("MT.")
            or normalized_gene.startswith("MT_")
        ):

            mitochondrial_umis += counts

    if n_genes == 0:
        raise ValueError(
            "No genes were found in the "
            "expression matrix."
        )

    mitochondrial_fraction = (
        np.divide(
            mitochondrial_umis,
            total_umis,
            out=np.zeros_like(
                mitochondrial_umis
            ),
            where=total_umis > 0,
        )
    )

    total_umi_sum = float(
        np.sum(total_umis)
    )

    mitochondrial_sum = float(
        np.sum(
            mitochondrial_umis
        )
    )

    return QCStats(

        n_genes=n_genes,

        n_cells=n_cells,

        total_umis=int(
            total_umi_sum
        ),

        median_umis_per_cell=float(
            np.median(total_umis)
        ),

        mean_umis_per_cell=float(
            np.mean(total_umis)
        ),

        median_genes_per_cell=float(
            np.median(
                detected_genes
            )
        ),

        mean_genes_per_cell=float(
            np.mean(
                detected_genes
            )
        ),

        mitochondrial_umis=int(
            mitochondrial_sum
        ),

        mitochondrial_fraction=float(
            mitochondrial_sum
            / max(
                total_umi_sum,
                1.0,
            )
        ),

        min_umis_per_cell=int(
            np.min(total_umis)
        ),

        max_umis_per_cell=int(
            np.max(total_umis)
        ),

        min_genes_per_cell=int(
            np.min(
                detected_genes
            )
        ),

        max_genes_per_cell=int(
            np.max(
                detected_genes
            )
        ),
    )


# ============================================================
# VALIDATION
# ============================================================


def validate_expression_matrix(
    path: str | Path,
) -> dict:
    """
    Perform structural validation of the
    expression matrix.

    Validation is intentionally flexible about
    gene-column naming.
    """

    try:

        info = inspect_expression_matrix(
            path
        )

    except Exception as exc:

        return {
            "valid": False,
            "errors": [
                str(exc)
            ],
            "warnings": [],
            "matrix": {
                "filename": Path(path).name,
            },
        }

    errors: list[str] = []
    warnings: list[str] = []

    # --------------------------------------------------------
    # Gene validation
    # --------------------------------------------------------

    if info.n_genes == 0:

        errors.append(
            "No genes were detected."
        )

    # --------------------------------------------------------
    # Cell validation
    # --------------------------------------------------------

    if info.n_cells == 0:

        errors.append(
            "No cells were detected."
        )

    # --------------------------------------------------------
    # Gene-column naming
    # --------------------------------------------------------

    known_gene_columns = {
        "index",
        "gene",
        "gene_id",
        "geneid",
        "gene_ids",
        "genes",
        "gene_name",
        "genename",
        "feature",
        "feature_id",
        "featureid",
        "symbol",
        "gene_symbol",
        "geneid_symbol",
    }

    normalized_gene_column = (
        info.gene_column
        .strip()
        .lower()
        .replace(" ", "_")
    )

    if (
        normalized_gene_column
        not in known_gene_columns
    ):

        warnings.append(
            "Gene identifier column is named "
            f"'{info.gene_column}'. "
            "The column is accepted because "
            "IMMUNO-XAI validates the matrix "
            "structure rather than requiring "
            "a specific column name."
        )

    # --------------------------------------------------------
    # Matrix information
    # --------------------------------------------------------

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

            "preview_genes": (
                info.first_genes
            ),

            "preview_cells": (
                info.first_cells
            ),
        },
    }