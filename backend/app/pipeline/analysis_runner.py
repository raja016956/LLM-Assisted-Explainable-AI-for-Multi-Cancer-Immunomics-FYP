from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable

from app.pipeline.io import (
    inspect_expression_matrix,
    validate_expression_matrix,
)

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

from app.pipeline.umap import (
    UMAPConfig,
    run_umap,
)

from app.pipeline.clustering import (
    ClusteringConfig,
    run_clustering,
)

from app.pipeline.immune_state_scoring import (
    ImmuneStateScoringConfig,
    run_immune_state_scoring,
)

from app.pipeline.immune_state_assignment import (
    ImmuneStateAssignmentConfig,
    run_immune_state_assignment,
)

from app.pipeline.ml import (
    MLConfig,
    run_ml,
)

from app.pipeline.xai import (
    XAIConfig,
    run_xai,
)

from app.pipeline.pathway_scoring import (
    PathwayScoringConfig,
    run_pathway_scoring,
)

from app.pipeline.pathway_immune_integration import (
    PathwayImmuneIntegrationConfig,
    run_pathway_immune_integration,
)

from app.pipeline.final_analysis import (
    run_final_analysis,
)

from app.pipeline.llm_reasoning import (
    LLMReasoningConfig,
    run_llm_reasoning,
)


# ============================================================
# TYPES
# ============================================================

ProgressCallback = Callable[
    [int, int, str, str],
    None,
]


# ============================================================
# PIPELINE CONFIGURATION
# ============================================================

DEFAULT_QC_CONFIG = QCConfig(
    min_umis=1000,
    min_genes=200,
    max_mito_fraction=0.20,
)


DEFAULT_NORMALIZATION_CHUNK_CELLS = 250
DEFAULT_NORMALIZATION_TARGET_SUM = 10_000


DEFAULT_FEATURE_SELECTION_CONFIG = FeatureSelectionConfig(
    n_top_genes=2000,
    min_cells=3,
)


DEFAULT_PCA_CONFIG = PCAConfig(
    n_components=50,
    random_state=42,
)


DEFAULT_UMAP_CONFIG = UMAPConfig(
    n_components=2,
    n_neighbors=15,
    min_dist=0.5,
    metric="euclidean",
    random_state=42,
)


DEFAULT_CLUSTERING_CONFIG = ClusteringConfig(
    n_clusters=10,
    random_state=42,
    n_init=20,
)


DEFAULT_IMMUNE_SCORING_CONFIG = ImmuneStateScoringConfig()


DEFAULT_IMMUNE_ASSIGNMENT_CONFIG = (
    ImmuneStateAssignmentConfig(
        minimum_supported_signatures=2,
        minimum_signal=0.005,
        dominance_ratio=1.25,
        suppression_ratio=1.25,
        inflammatory_ratio=1.15,
        antigen_presentation_threshold=0.01,
    )
)


DEFAULT_ML_CONFIG = MLConfig()


DEFAULT_XAI_CONFIG = XAIConfig(
    top_n_features=20,
    max_explanation_cells=200,
    random_state=42,
)


DEFAULT_PATHWAY_SCORING_CONFIG = (
    PathwayScoringConfig()
)


DEFAULT_PATHWAY_IMMUNE_CONFIG = (
    PathwayImmuneIntegrationConfig(
        minimum_cells_per_state=2,
        minimum_cells_per_cluster=2,
        minimum_state_fraction=0.01,
        correlation_method="pearson",
    )
)


DEFAULT_LLM_CONFIG = LLMReasoningConfig(
    provider="groq",
    model="openai/gpt-oss-20b",
    temperature=0.2,
    max_tokens=4000,
)


# ============================================================
# HELPERS
# ============================================================


def _emit_progress(
    callback: ProgressCallback | None,
    step_number: int,
    total_steps: int,
    step: str,
    message: str,
) -> None:

    if callback is None:
        return

    callback(
        step_number,
        total_steps,
        step,
        message,
    )


def _require_file(
    path: str | Path,
    description: str,
) -> Path:

    path = Path(path)

    if not path.exists():

        raise FileNotFoundError(
            f"{description} not found: {path}"
        )

    if not path.is_file():

        raise ValueError(
            f"{description} is not a file: {path}"
        )

    return path


def _write_json(
    path: Path,
    data: Any,
) -> None:

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        path,
        "w",
        encoding="utf-8",
    ) as handle:

        json.dump(
            data,
            handle,
            indent=2,
            ensure_ascii=False,
        )


# ============================================================
# MAIN PIPELINE
# ============================================================


def run_full_analysis(
    dataset_path: str | Path,
    analysis_dir: str | Path,
    progress_callback: ProgressCallback | None = None,
    *,
    qc_config: QCConfig | None = None,
    normalization_chunk_cells: int = DEFAULT_NORMALIZATION_CHUNK_CELLS,
    normalization_target_sum: float = DEFAULT_NORMALIZATION_TARGET_SUM,
    feature_selection_config: FeatureSelectionConfig | None = None,
    pca_config: PCAConfig | None = None,
    umap_config: UMAPConfig | None = None,
    clustering_config: ClusteringConfig | None = None,
    immune_scoring_config: ImmuneStateScoringConfig | None = None,
    immune_assignment_config: ImmuneStateAssignmentConfig | None = None,
    ml_config: MLConfig | None = None,
    xai_config: XAIConfig | None = None,
    pathway_scoring_config: PathwayScoringConfig | None = None,
    pathway_immune_config: PathwayImmuneIntegrationConfig | None = None,
    llm_config: LLMReasoningConfig | None = None,
) -> dict[str, Any]:
    """
    Run the complete IMMUNO-XAI analysis pipeline.

    Workflow:

        1. Dataset inspection
        2. Dataset validation
        3. Quality control
        4. Memory-safe normalization
        5. Highly variable gene selection
        6. PCA
        7. UMAP
        8. K-means clustering
        9. Immune-state scoring
        10. Immune-state assignment
        11. Machine learning
        12. Explainable AI / SHAP
        13. Pathway scoring
        14. Pathway-immune integration
        15. Final analysis package
        16. LLM biological reasoning

    The scientific modules themselves remain unchanged.
    This function only orchestrates them.
    """

    start_time = time.perf_counter()

    dataset_path = _require_file(
        dataset_path,
        "Dataset",
    )

    analysis_dir = Path(
        analysis_dir
    )

    analysis_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------------------------------
    # CONFIGURATION
    # --------------------------------------------------------

    qc_config = (
        qc_config
        or DEFAULT_QC_CONFIG
    )

    feature_selection_config = (
        feature_selection_config
        or DEFAULT_FEATURE_SELECTION_CONFIG
    )

    pca_config = (
        pca_config
        or DEFAULT_PCA_CONFIG
    )

    umap_config = (
        umap_config
        or DEFAULT_UMAP_CONFIG
    )

    clustering_config = (
        clustering_config
        or DEFAULT_CLUSTERING_CONFIG
    )

    immune_scoring_config = (
        immune_scoring_config
        or DEFAULT_IMMUNE_SCORING_CONFIG
    )

    immune_assignment_config = (
        immune_assignment_config
        or DEFAULT_IMMUNE_ASSIGNMENT_CONFIG
    )

    ml_config = (
        ml_config
        or DEFAULT_ML_CONFIG
    )

    xai_config = (
        xai_config
        or DEFAULT_XAI_CONFIG
    )

    pathway_scoring_config = (
        pathway_scoring_config
        or DEFAULT_PATHWAY_SCORING_CONFIG
    )

    pathway_immune_config = (
        pathway_immune_config
        or DEFAULT_PATHWAY_IMMUNE_CONFIG
    )

    llm_config = (
        llm_config
        or DEFAULT_LLM_CONFIG
    )

    total_steps = 16

    results: dict[str, Any] = {}

    # ========================================================
    # STEP 1 — DATASET INSPECTION
    # ========================================================

    step = 1

    _emit_progress(
        progress_callback,
        step,
        total_steps,
        "dataset_inspection",
        "Inspecting expression matrix.",
    )

    print()
    print("=" * 70)
    print("STEP 1 — DATASET INSPECTION")
    print("=" * 70)

    info = inspect_expression_matrix(
        dataset_path
    )

    results["dataset"] = {
        "filename": info.filename,
        "format": info.format,
        "compression": info.compression,
        "genes": int(info.n_genes),
        "cells": int(info.n_cells),
        "gene_column": info.gene_column,
        "preview_genes": info.first_genes,
        "preview_cells": info.first_cells,
    }

    print(
        f"Genes: {info.n_genes:,}"
    )

    print(
        f"Cells: {info.n_cells:,}"
    )

    # ========================================================
    # STEP 2 — VALIDATION
    # ========================================================

    step = 2

    _emit_progress(
        progress_callback,
        step,
        total_steps,
        "validation",
        "Validating expression matrix.",
    )

    print()
    print("=" * 70)
    print("STEP 2 — DATASET VALIDATION")
    print("=" * 70)

    validation = validate_expression_matrix(
        dataset_path
    )

    if not validation["valid"]:

        raise ValueError(
            "Dataset validation failed: "
            + "; ".join(
                validation.get(
                    "errors",
                    [],
                )
            )
        )

    results["validation"] = validation

    print(
        "Dataset validation: PASSED"
    )

    # ========================================================
    # STEP 3 — QUALITY CONTROL
    # ========================================================

    step = 3

    _emit_progress(
        progress_callback,
        step,
        total_steps,
        "quality_control",
        "Calculating single-cell quality-control metrics.",
    )

    print()
    print("=" * 70)
    print("STEP 3 — QUALITY CONTROL")
    print("=" * 70)

    qc_result = calculate_streaming_qc(
        dataset_path,
        config=qc_config,
    )

    keep_cell_indices = qc_result[
        "keep_cell_indices"
    ]

    results["qc"] = {
        key: value
        for key, value in qc_result.items()
        if key not in {
            "keep_cells",
            "keep_cell_indices",
            "keep_cell_names",
        }
    }

    results["qc"]["cells_before"] = int(
        qc_result["cells"]["before"]
    )

    results["qc"]["cells_after"] = int(
        qc_result["cells"]["after"]
    )

    results["qc"]["cells_removed"] = int(
        qc_result["cells"]["removed"]
    )

    print(
        f"Cells before QC: "
        f"{qc_result['cells']['before']:,}"
    )

    print(
        f"Cells after QC:  "
        f"{qc_result['cells']['after']:,}"
    )

    print(
        f"Cells removed:   "
        f"{qc_result['cells']['removed']:,}"
    )

    # ========================================================
    # STEP 4 — NORMALIZATION
    # ========================================================

    step = 4

    _emit_progress(
        progress_callback,
        step,
        total_steps,
        "normalization",
        "Normalizing QC-retained cells.",
    )

    print()
    print("=" * 70)
    print("STEP 4 — NORMALIZATION")
    print("=" * 70)

    normalization_dir = (
        analysis_dir
        / "normalization"
    )

    normalization_result = (
        run_memory_safe_normalization(
            dataset_path,
            normalization_dir,
            chunk_cells=normalization_chunk_cells,
            target_sum=normalization_target_sum,
            keep_cell_indices=keep_cell_indices,
        )
    )

    normalized_output = Path(
        normalization_result[
            "normalized"
        ][
            "output_file"
        ]
    )

    genes_output = (
        normalization_dir
        / "genes.json"
    )

    _require_file(
        normalized_output,
        "Normalized expression matrix",
    )

    _require_file(
        genes_output,
        "Gene metadata",
    )

    results["normalization"] = (
        normalization_result
    )

    results["paths"] = {
        "normalized_expression": str(
            normalized_output
        ),
        "genes": str(
            genes_output
        ),
    }

    print(
        "Normalized matrix:",
        normalized_output,
    )

    # ========================================================
    # STEP 5 — FEATURE SELECTION
    # ========================================================

    step = 5

    _emit_progress(
        progress_callback,
        step,
        total_steps,
        "feature_selection",
        "Selecting highly variable genes.",
    )

    print()
    print("=" * 70)
    print("STEP 5 — HIGHLY VARIABLE GENE SELECTION")
    print("=" * 70)

    feature_dir = (
        analysis_dir
        / "feature_selection"
    )

    feature_result = (
        select_highly_variable_genes(
            normalized_output,
            feature_dir,
            config=feature_selection_config,
        )
    )

    selected_output = Path(
        feature_result[
            "matrix_output"
        ]
    )

    _require_file(
        selected_output,
        "Selected feature matrix",
    )

    results["feature_selection"] = (
        feature_result
    )

    print(
        f"Selected genes: "
        f"{feature_result['selected_genes']:,}"
    )

    # ========================================================
    # STEP 6 — PCA
    # ========================================================

    step = 6

    _emit_progress(
        progress_callback,
        step,
        total_steps,
        "pca",
        "Computing principal components.",
    )

    print()
    print("=" * 70)
    print("STEP 6 — PCA")
    print("=" * 70)

    pca_dir = (
        analysis_dir
        / "pca"
    )

    pca_result = run_pca(
        selected_output,
        pca_dir,
        config=pca_config,
    )

    pca_output = Path(
        pca_result[
            "embeddings_output"
        ]
    )

    _require_file(
        pca_output,
        "PCA coordinates",
    )

    results["pca"] = pca_result

    print(
        "PCA embedding:",
        pca_result["embedding_shape"],
    )

    # ========================================================
    # STEP 7 — UMAP
    # ========================================================

    step = 7

    _emit_progress(
        progress_callback,
        step,
        total_steps,
        "umap",
        "Computing UMAP embedding.",
    )

    print()
    print("=" * 70)
    print("STEP 7 — UMAP")
    print("=" * 70)

    umap_dir = (
        analysis_dir
        / "umap"
    )

    umap_result = run_umap(
        pca_output,
        umap_dir,
        config=umap_config,
    )

    umap_output = Path(
        umap_result[
            "embedding_output"
        ]
    )

    _require_file(
        umap_output,
        "UMAP coordinates",
    )

    results["umap"] = umap_result

    # ========================================================
    # STEP 8 — CLUSTERING
    # ========================================================

    step = 8

    _emit_progress(
        progress_callback,
        step,
        total_steps,
        "clustering",
        "Clustering cells using PCA representations.",
    )

    print()
    print("=" * 70)
    print("STEP 8 — CLUSTERING")
    print("=" * 70)

    clustering_dir = (
        analysis_dir
        / "clustering"
    )

    clustering_result = run_clustering(
        pca_output,
        clustering_dir,
        config=clustering_config,
    )

    cluster_labels_output = Path(
        clustering_result[
            "labels_output"
        ]
    )

    _require_file(
        cluster_labels_output,
        "Cluster labels",
    )

    results["clustering"] = (
        clustering_result
    )

    print(
        "Clusters:",
        clustering_result[
            "n_clusters"
        ],
    )

    # ========================================================
    # STEP 9 — IMMUNE STATE SCORING
    # ========================================================

    step = 9

    _emit_progress(
        progress_callback,
        step,
        total_steps,
        "immune_state_scoring",
        "Calculating immune-state gene-set scores.",
    )

    print()
    print("=" * 70)
    print("STEP 9 — IMMUNE-STATE SCORING")
    print("=" * 70)

    immune_scoring_dir = (
        analysis_dir
        / "immune_state_scoring"
    )

    immune_scoring_result = (
        run_immune_state_scoring(
            expression_path=normalized_output,
            genes_path=genes_output,
            cluster_labels_path=cluster_labels_output,
            output_dir=immune_scoring_dir,
            config=immune_scoring_config,
        )
    )

    immune_scores_output = Path(
        immune_scoring_result[
            "score_matrix_output"
        ]
    )

    immune_score_names_output = Path(
        immune_scoring_result[
            "score_names_output"
        ]
    )

    _require_file(
        immune_scores_output,
        "Immune score matrix",
    )

    _require_file(
        immune_score_names_output,
        "Immune score names",
    )

    results["immune_state_scoring"] = (
        immune_scoring_result
    )

    # ========================================================
    # STEP 10 — IMMUNE STATE ASSIGNMENT
    # ========================================================

    step = 10

    _emit_progress(
        progress_callback,
        step,
        total_steps,
        "immune_state_assignment",
        "Assigning evidence-aware immune states.",
    )

    print()
    print("=" * 70)
    print("STEP 10 — IMMUNE-STATE ASSIGNMENT")
    print("=" * 70)

    immune_assignment_dir = (
        analysis_dir
        / "immune_state_assignment"
    )

    immune_assignment_result = (
        run_immune_state_assignment(
            immune_scores_path=immune_scores_output,
            score_names_path=immune_score_names_output,
            cluster_labels_path=cluster_labels_output,
            output_dir=immune_assignment_dir,
            config=immune_assignment_config,
        )
    )

    cell_states_output = Path(
        immune_assignment_dir
        / "cell_immune_states.json"
    )

    cluster_states_output = Path(
        immune_assignment_dir
        / "cluster_immune_states.json"
    )

    _require_file(
        cell_states_output,
        "Cell immune states",
    )

    _require_file(
        cluster_states_output,
        "Cluster immune states",
    )

    results["immune_state_assignment"] = (
        immune_assignment_result
    )

    # ========================================================
    # STEP 11 — MACHINE LEARNING
    # ========================================================

    step = 11

    _emit_progress(
        progress_callback,
        step,
        total_steps,
        "machine_learning",
        "Training immune-state machine-learning models.",
    )

    print()
    print("=" * 70)
    print("STEP 11 — MACHINE LEARNING")
    print("=" * 70)

    ml_dir = (
        analysis_dir
        / "ml"
    )

    ml_result = run_ml(
        pca_coordinates_path=pca_output,
        immune_scores_path=immune_scores_output,
        cell_states_path=cell_states_output,
        output_dir=ml_dir,
        config=ml_config,
    )

    ml_model_output = Path(
        ml_result[
            "model_output"
        ]
    )

    ml_features_output = Path(
        ml_result[
            "features_output"
        ]
    )

    ml_predictions_output = Path(
        ml_result[
            "predictions_output"
        ]
    )

    _require_file(
        ml_model_output,
        "Random Forest model",
    )

    _require_file(
        ml_features_output,
        "ML feature matrix",
    )

    _require_file(
        ml_predictions_output,
        "ML predictions",
    )

    results["machine_learning"] = (
        ml_result
    )

    # ========================================================
    # STEP 12 — XAI
    # ========================================================

    step = 12

    _emit_progress(
        progress_callback,
        step,
        total_steps,
        "explainable_ai",
        "Generating SHAP explanations.",
    )

    print()
    print("=" * 70)
    print("STEP 12 — EXPLAINABLE AI")
    print("=" * 70)

    xai_dir = (
        analysis_dir
        / "xai"
    )

    xai_result = run_xai(
        model_path=ml_model_output,
        features_path=ml_features_output,
        score_names_path=immune_score_names_output,
        predictions_path=ml_predictions_output,
        output_dir=xai_dir,
        config=xai_config,
    )

    xai_global_output = Path(
        xai_result[
            "global_output"
        ]
    )

    _require_file(
        xai_global_output,
        "Global XAI importance",
    )

    results["xai"] = xai_result

    # ========================================================
    # STEP 13 — PATHWAY SCORING
    # ========================================================

    step = 13

    _emit_progress(
        progress_callback,
        step,
        total_steps,
        "pathway_scoring",
        "Calculating metabolic and inflammatory pathway scores.",
    )

    print()
    print("=" * 70)
    print("STEP 13 — PATHWAY SCORING")
    print("=" * 70)

    pathway_dir = (
        analysis_dir
        / "pathway_scoring"
    )

    pathway_result = run_pathway_scoring(
        expression_path=normalized_output,
        genes_path=genes_output,
        output_dir=pathway_dir,
        config=pathway_scoring_config,
    )

    pathway_scores_output = Path(
        pathway_result[
            "scores_output"
        ]
    )

    pathway_names_output = Path(
        pathway_result[
            "names_output"
        ]
    )

    _require_file(
        pathway_scores_output,
        "Pathway scores",
    )

    _require_file(
        pathway_names_output,
        "Pathway names",
    )

    results["pathway_scoring"] = (
        pathway_result
    )

    # ========================================================
    # STEP 14 — PATHWAY / IMMUNE INTEGRATION
    # ========================================================

    step = 14

    _emit_progress(
        progress_callback,
        step,
        total_steps,
        "pathway_immune_integration",
        "Integrating pathway activity with immune states.",
    )

    print()
    print("=" * 70)
    print("STEP 14 — PATHWAY / IMMUNE INTEGRATION")
    print("=" * 70)

    pathway_immune_dir = (
        analysis_dir
        / "pathway_immune_integration"
    )

    pathway_immune_result = (
        run_pathway_immune_integration(
            pathway_scores_path=pathway_scores_output,
            pathway_names_path=pathway_names_output,
            immune_scores_path=immune_scores_output,
            immune_score_names_path=immune_score_names_output,
            cell_states_path=cell_states_output,
            cluster_labels_path=cluster_labels_output,
            output_dir=pathway_immune_dir,
            config=pathway_immune_config,
        )
    )

    results["pathway_immune_integration"] = (
        pathway_immune_result
    )

    # ========================================================
    # STEP 15 — FINAL ANALYSIS
    # ========================================================

    step = 15

    _emit_progress(
        progress_callback,
        step,
        total_steps,
        "final_analysis",
        "Building integrated computational analysis package.",
    )

    print()
    print("=" * 70)
    print("STEP 15 — FINAL ANALYSIS")
    print("=" * 70)

    final_analysis_dir = (
        analysis_dir
        / "final_analysis"
    )

    final_analysis_result = run_final_analysis(
        cell_states_path=cell_states_output,
        cluster_states_path=cluster_states_output,
        immune_scores_path=immune_scores_output,
        immune_score_names_path=immune_score_names_output,
        ml_predictions_path=ml_predictions_output,
        pathway_scores_path=pathway_scores_output,
        pathway_names_path=pathway_names_output,
        xai_global_importance_path=xai_global_output,
        output_dir=final_analysis_dir,
    )

    final_analysis_output = Path(
        final_analysis_dir
        / "final_analysis.json"
    )

    llm_input_output = Path(
        final_analysis_dir
        / "llm_reasoning_input.json"
    )

    _require_file(
        final_analysis_output,
        "Final analysis JSON",
    )

    _require_file(
        llm_input_output,
        "LLM reasoning input",
    )

    results["final_analysis"] = (
        final_analysis_result
    )

    # ========================================================
    # STEP 16 — LLM BIOLOGICAL REASONING
    # ========================================================

    step = 16

    _emit_progress(
        progress_callback,
        step,
        total_steps,
        "llm_reasoning",
        "Generating biological interpretation.",
    )

    print()
    print("=" * 70)
    print("STEP 16 — LLM BIOLOGICAL REASONING")
    print("=" * 70)

    llm_dir = (
        analysis_dir
        / "llm_reasoning"
    )

    llm_result = run_llm_reasoning(
        analysis_input_path=llm_input_output,
        output_dir=llm_dir,
        config=llm_config,
    )

    biological_interpretation_output = (
        llm_dir
        / "biological_interpretation.json"
    )

    biological_report_output = (
        llm_dir
        / "biological_report.md"
    )

    llm_metadata_output = (
        llm_dir
        / "llm_reasoning_metadata.json"
    )

    _require_file(
        biological_interpretation_output,
        "Biological interpretation",
    )

    _require_file(
        biological_report_output,
        "Biological report",
    )

    _require_file(
        llm_metadata_output,
        "LLM metadata",
    )

    results["llm_reasoning"] = (
        llm_result
    )

    # ========================================================
    # FINAL METADATA
    # ========================================================

    runtime_seconds = (
        time.perf_counter()
        - start_time
    )

    results["runtime_seconds"] = (
        float(runtime_seconds)
    )

    results["paths"].update({

        "final_analysis":
            str(final_analysis_output),

        "llm_reasoning_input":
            str(llm_input_output),

        "biological_interpretation":
            str(biological_interpretation_output),

        "biological_report":
            str(biological_report_output),

        "llm_metadata":
            str(llm_metadata_output),

        "umap_coordinates":
            str(umap_output),

        "cluster_labels":
            str(cluster_labels_output),

        "immune_scores":
            str(immune_scores_output),

        "immune_score_names":
            str(immune_score_names_output),

        "cell_immune_states":
            str(cell_states_output),

        "cluster_immune_states":
            str(cluster_states_output),

        "ml_model":
            str(ml_model_output),

        "ml_features":
            str(ml_features_output),

        "ml_predictions":
            str(ml_predictions_output),

        "xai_global_importance":
            str(xai_global_output),

        "pathway_scores":
            str(pathway_scores_output),

        "pathway_names":
            str(pathway_names_output),
    })

    # ========================================================
    # SAVE RUN MANIFEST
    # ========================================================

    manifest_path = (
        analysis_dir
        / "analysis_run_manifest.json"
    )

    manifest = {
        "pipeline": "IMMUNO-XAI",
        "status": "completed",
        "dataset": str(dataset_path),
        "analysis_dir": str(analysis_dir),
        "runtime_seconds": float(
            runtime_seconds
        ),
        "steps_completed": total_steps,
        "total_steps": total_steps,
        "paths": results["paths"],
    }

    _write_json(
        manifest_path,
        manifest,
    )

    results["paths"][
        "run_manifest"
    ] = str(manifest_path)

    _emit_progress(
        progress_callback,
        total_steps,
        total_steps,
        "completed",
        "IMMUNO-XAI analysis completed successfully.",
    )

    print()
    print("=" * 70)
    print("IMMUNO-XAI COMPLETE")
    print("=" * 70)

    print(
        f"Runtime: {runtime_seconds:.2f} seconds"
    )

    print(
        "Final analysis:",
        final_analysis_output,
    )

    print(
        "Biological report:",
        biological_report_output,
    )

    return results