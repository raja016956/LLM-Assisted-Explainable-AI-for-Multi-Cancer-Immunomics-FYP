from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json

import numpy as np
from scipy import sparse


# ============================================================
# CONFIGURATION
# ============================================================

@dataclass(frozen=True)
class PathwayScoringConfig:
    minimum_genes: int = 2
    minimum_expression: float = 0.0


# ============================================================
# DEFAULT BIOLOGICAL SIGNATURES
# ============================================================

PATHWAY_SIGNATURES = {
    "glycolysis": [
        "ALDOA",
        "ENO1",
        "GAPDH",
        "GPI",
        "HK1",
        "HK2",
        "LDHA",
        "PFKL",
        "PFKM",
        "PGAM1",
        "PKM",
        "TPI1",
    ],

    "oxidative_phosphorylation": [
        "ATP5F1A",
        "ATP5F1B",
        "COX4I1",
        "COX5A",
        "COX6C",
        "NDUFA1",
        "NDUFA2",
        "NDUFB8",
        "NDUFS1",
        "NDUFS2",
        "SDHA",
        "SDHB",
        "UQCRC1",
        "UQCRC2",
    ],

    "fatty_acid_metabolism": [
        "ACACA",
        "ACLY",
        "CPT1A",
        "CPT2",
        "FABP5",
        "FASN",
        "HADHA",
        "HADHB",
        "HMGCR",
        "SCD",
    ],

    "interferon_response": [
        "IFIT1",
        "IFIT2",
        "IFIT3",
        "ISG15",
        "MX1",
        "MX2",
        "OAS1",
        "OAS2",
        "OAS3",
        "STAT1",
        "IRF7",
    ],

    "inflammatory_signaling": [
        "CCL2",
        "CCL3",
        "CCL4",
        "CXCL9",
        "CXCL10",
        "CXCL11",
        "IL1B",
        "TNF",
        "NFKB1",
        "NFKBIA",
    ],

    "chemokine_activity": [
        "CCL2",
        "CCL3",
        "CCL4",
        "CCL5",
        "CXCL9",
        "CXCL10",
        "CXCL11",
        "CXCL13",
    ],
}


# ============================================================
# HELPERS
# ============================================================

def _load_json_list(path: Path) -> list[str]:

    if not path.exists():
        raise FileNotFoundError(
            f"Gene metadata file not found: {path}"
        )

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as handle:

        data = json.load(handle)

    if isinstance(data, list):

        genes = data

    elif isinstance(data, dict):

        if "genes" in data:

            genes = data["genes"]

        elif "gene_names" in data:

            genes = data["gene_names"]

        else:

            raise ValueError(
                f"Unsupported gene metadata format: {path}"
            )

    else:

        raise ValueError(
            f"Gene metadata must be a list or dictionary: {path}"
        )

    genes = [
        str(gene)
        for gene in genes
    ]

    if not genes:

        raise ValueError(
            f"Gene metadata is empty: {path}"
        )

    return genes


def _load_expression(
    path: Path,
    gene_count: int,
) -> np.ndarray:

    """
    Load the normalized expression matrix.

    The project internally uses:

        rows    = cells
        columns = genes

    However, the normalization output currently stores:

        rows    = genes
        columns = cells

    Therefore this loader detects the orientation using
    the number of genes in genes.json and transposes when
    necessary.

    This prevents downstream pipelines from silently using
    genes as cells.
    """

    if not path.exists():

        raise FileNotFoundError(
            f"Expression matrix not found: {path}"
        )

    matrix = sparse.load_npz(path)

    if matrix.ndim != 2:

        raise ValueError(
            "Expression matrix must be two-dimensional."
        )

    rows, columns = matrix.shape

    # --------------------------------------------------------
    # Already cells × genes
    # --------------------------------------------------------

    if columns == gene_count:

        expression = matrix

        orientation = "cells_by_genes"

    # --------------------------------------------------------
    # Stored as genes × cells
    # --------------------------------------------------------

    elif rows == gene_count:

        expression = matrix.T.tocsr()

        orientation = "genes_by_cells_transposed"

    # --------------------------------------------------------
    # Neither orientation matches metadata
    # --------------------------------------------------------

    else:

        raise ValueError(
            "Expression matrix dimensions are incompatible "
            "with gene metadata. "
            f"Matrix shape: {matrix.shape}, "
            f"metadata genes: {gene_count}"
        )

    expression = expression.toarray().astype(
        np.float32,
        copy=False,
    )

    # --------------------------------------------------------
    # Final validation
    # --------------------------------------------------------

    if expression.shape[1] != gene_count:

        raise ValueError(
            "Expression matrix could not be converted "
            "to cells × genes orientation. "
            f"Final shape: {expression.shape}, "
            f"metadata genes: {gene_count}"
        )

    print(
        "Expression orientation:",
        orientation
    )

    print(
        "Expression matrix shape:",
        expression.shape
    )

    return expression


def _zscore(
    matrix: np.ndarray,
) -> np.ndarray:

    mean = np.mean(
        matrix,
        axis=0,
        keepdims=True,
    )

    std = np.std(
        matrix,
        axis=0,
        keepdims=True,
    )

    std[std == 0] = 1.0

    return (
        matrix - mean
    ) / std


def _score_signature(
    expression: np.ndarray,
    gene_to_index: dict[str, int],
    genes: list[str],
    config: PathwayScoringConfig,
) -> tuple[
    np.ndarray,
    list[str],
    list[str],
]:

    available = [
        gene
        for gene in genes
        if gene in gene_to_index
    ]

    missing = [
        gene
        for gene in genes
        if gene not in gene_to_index
    ]

    if len(available) < config.minimum_genes:

        return (
            np.zeros(
                expression.shape[0],
                dtype=np.float32,
            ),
            available,
            missing,
        )

    indices = [
        gene_to_index[gene]
        for gene in available
    ]

    values = expression[:, indices]

    values = np.maximum(
        values,
        config.minimum_expression,
    )

    # Standardize each gene across cells.
    standardized = _zscore(
        values
    )

    score = np.mean(
        standardized,
        axis=1,
    )

    return (
        score.astype(
            np.float32
        ),
        available,
        missing,
    )


# ============================================================
# MAIN PIPELINE
# ============================================================

def run_pathway_scoring(
    expression_path: str | Path,
    genes_path: str | Path,
    output_dir: str | Path,
    config: PathwayScoringConfig | None = None,
) -> dict:

    config = (
        config
        or PathwayScoringConfig()
    )

    expression_path = Path(
        expression_path
    )

    genes_path = Path(
        genes_path
    )

    output_dir = Path(
        output_dir
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------------------------------
    # LOAD GENE METADATA FIRST
    # --------------------------------------------------------

    genes = _load_json_list(
        genes_path
    )

    # --------------------------------------------------------
    # LOAD EXPRESSION WITH ORIENTATION DETECTION
    # --------------------------------------------------------

    expression = _load_expression(
        expression_path,
        gene_count=len(genes),
    )

    n_cells, n_genes = expression.shape

    # --------------------------------------------------------
    # FINAL DIMENSION VALIDATION
    # --------------------------------------------------------

    if len(genes) != n_genes:

        raise ValueError(
            "Gene metadata does not match expression "
            "matrix dimensions after orientation correction. "
            f"Expression genes: {n_genes}, "
            f"metadata genes: {len(genes)}"
        )

    gene_to_index = {
        gene: index
        for index, gene in enumerate(genes)
    }

    # --------------------------------------------------------
    # SCORE PATHWAYS
    # --------------------------------------------------------

    score_names = []

    score_vectors = []

    signature_metadata = {}

    for pathway_name, signature in (
        PATHWAY_SIGNATURES.items()
    ):

        score, available, missing = (
            _score_signature(
                expression=expression,
                gene_to_index=gene_to_index,
                genes=signature,
                config=config,
            )
        )

        score_names.append(
            pathway_name
        )

        score_vectors.append(
            score
        )

        signature_metadata[pathway_name] = {

            "requested_genes": len(
                signature
            ),

            "available_genes": len(
                available
            ),

            "available": available,

            "missing": missing,

            "supported": (
                len(available)
                >= config.minimum_genes
            ),
        }

    # --------------------------------------------------------
    # BUILD SCORE MATRIX
    # --------------------------------------------------------

    score_matrix = np.column_stack(
        score_vectors
    ).astype(
        np.float32
    )

    # --------------------------------------------------------
    # OUTPUT PATHS
    # --------------------------------------------------------

    scores_path = (
        output_dir
        / "pathway_scores.npy"
    )

    names_path = (
        output_dir
        / "pathway_names.json"
    )

    metadata_path = (
        output_dir
        / "pathway_metadata.json"
    )

    # --------------------------------------------------------
    # SAVE SCORES
    # --------------------------------------------------------

    np.save(
        scores_path,
        score_matrix,
    )

    # --------------------------------------------------------
    # SAVE NAMES
    # --------------------------------------------------------

    with open(
        names_path,
        "w",
        encoding="utf-8",
    ) as handle:

        json.dump(
            score_names,
            handle,
            indent=2,
        )

    # --------------------------------------------------------
    # SAVE METADATA
    # --------------------------------------------------------

    metadata = {

        "input_cells": int(
            n_cells
        ),

        "input_genes": int(
            n_genes
        ),

        "pathway_count": len(
            score_names
        ),

        "score_shape": list(
            score_matrix.shape
        ),

        "expression_orientation": (
            "cells_by_genes"
        ),

        "pathways": signature_metadata,
    }

    with open(
        metadata_path,
        "w",
        encoding="utf-8",
    ) as handle:

        json.dump(
            metadata,
            handle,
            indent=2,
        )

    # --------------------------------------------------------
    # RETURN
    # --------------------------------------------------------

    return {

        "input_cells": n_cells,

        "input_genes": n_genes,

        "pathway_count": len(
            score_names
        ),

        "n_pathways": len(
            score_names
        ),

        "score_shape": list(
            score_matrix.shape
        ),

        "score_names": score_names,

        "scores": score_matrix,

        "signature_metadata": (
            signature_metadata
        ),

        "scores_output": str(
            scores_path
        ),

        "names_output": str(
            names_path
        ),

        "metadata_output": str(
            metadata_path
        ),
    }