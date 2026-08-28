from __future__ import annotations

import json
import shutil
import threading
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.pipeline.analysis_runner import run_full_analysis


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/analysis",
    tags=["analysis"],
)


# ============================================================
# PATHS
# ============================================================

# backend/
BACKEND_DIR = Path(__file__).resolve().parents[2]

# backend/analysis_data/
ANALYSIS_DATA_DIR = BACKEND_DIR / "analysis_data"

# backend/backend_data/uploads/
UPLOADS_DIR = BACKEND_DIR / "backend_data" / "uploads"


ANALYSIS_DATA_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

UPLOADS_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# PIPELINE CONFIGURATION
# ============================================================

TOTAL_STEPS = 16


STEP_NAMES = [
    "dataset_inspection",
    "validation",
    "quality_control",
    "normalization",
    "feature_selection",
    "pca",
    "umap",
    "clustering",
    "immune_state_scoring",
    "immune_state_assignment",
    "machine_learning",
    "explainable_ai",
    "pathway_scoring",
    "pathway_immune_integration",
    "final_analysis",
    "llm_reasoning",
]


# ============================================================
# IN-MEMORY JOB STORE
# ============================================================

JOBS: Dict[str, Dict[str, Any]] = {}

JOBS_LOCK = threading.Lock()


# ============================================================
# REQUEST MODELS
# ============================================================

class AnalysisRunRequest(BaseModel):
    job_id: str


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def utc_now() -> str:
    """
    Return current UTC timestamp in ISO format.
    """

    return datetime.now(timezone.utc).isoformat()


def get_job(job_id: str) -> Dict[str, Any] | None:
    """
    Safely retrieve an analysis job.
    """

    with JOBS_LOCK:

        job = JOBS.get(job_id)

        if job is None:
            return None

        return dict(job)


def update_job(
    job_id: str,
    **updates: Any,
) -> None:
    """
    Safely update an analysis job.
    """

    with JOBS_LOCK:

        if job_id in JOBS:

            JOBS[job_id].update(updates)


def create_job(
    job_id: str,
    dataset_path: Path,
    analysis_dir: Path,
) -> None:
    """
    Create a new analysis job.
    """

    with JOBS_LOCK:

        JOBS[job_id] = {

            "job_id": job_id,

            "status": "queued",

            "step": None,

            "step_number": 0,

            "total_steps": TOTAL_STEPS,

            "progress": 0.0,

            "message": "Analysis queued.",

            "dataset": str(dataset_path),

            "analysis_dir": str(analysis_dir),

            "started_at": None,

            "completed_at": None,

            "error": None,

            "result": None,
        }


# ============================================================
# PROGRESS CALLBACK
# ============================================================

def make_progress_callback(job_id: str):
    """
    Create a callback that converts pipeline progress
    into API job progress.
    """

    def progress_callback(
        step_number: int,
        total_steps: int,
        step: str,
        message: str,
    ) -> None:

        if total_steps <= 0:

            progress = 0.0

        else:

            progress = (
                step_number
                / total_steps
                * 100.0
            )

        update_job(

            job_id,

            status="running",

            step=step,

            step_number=step_number,

            total_steps=total_steps,

            progress=round(
                progress,
                2,
            ),

            message=message,
        )

    return progress_callback


# ============================================================
# BACKGROUND PIPELINE
# ============================================================

def run_analysis_background(
    job_id: str,
    dataset_path: Path,
    analysis_dir: Path,
) -> None:
    """
    Execute the complete IMMUNO-XAI pipeline in a
    background thread.
    """

    update_job(

        job_id,

        status="running",

        started_at=utc_now(),

        step=None,

        step_number=0,

        total_steps=TOTAL_STEPS,

        progress=0.0,

        message="Starting IMMUNO-XAI analysis.",
    )

    try:

        # ----------------------------------------------------
        # PROGRESS CALLBACK
        # ----------------------------------------------------

        progress_callback = make_progress_callback(
            job_id
        )

        # ----------------------------------------------------
        # RUN COMPLETE PIPELINE
        # ----------------------------------------------------

        result = run_full_analysis(

            dataset_path=dataset_path,

            analysis_dir=analysis_dir,

            progress_callback=progress_callback,
        )

        # ----------------------------------------------------
        # SUCCESS
        # ----------------------------------------------------

        update_job(

            job_id,

            status="completed",

            step="llm_reasoning",

            step_number=TOTAL_STEPS,

            total_steps=TOTAL_STEPS,

            progress=100.0,

            message=(
                "IMMUNO-XAI analysis "
                "completed successfully."
            ),

            completed_at=utc_now(),

            result=result,
        )

        print()
        print("=" * 70)
        print(
            f"IMMUNO-XAI JOB COMPLETED: {job_id}"
        )
        print("=" * 70)
        print()

    except Exception as exc:

        traceback_text = traceback.format_exc()

        print()
        print("=" * 70)
        print(
            f"IMMUNO-XAI JOB FAILED: {job_id}"
        )
        print("=" * 70)
        print(traceback_text)
        print("=" * 70)
        print()

        update_job(

            job_id,

            status="failed",

            completed_at=utc_now(),

            message=(
                f"Analysis failed: {exc}"
            ),

            error={

                "type": type(exc).__name__,

                "message": str(exc),

                "traceback": traceback_text,
            },
        )


# ============================================================
# START ANALYSIS
# ============================================================

@router.post("/run")
def start_analysis(
    request: AnalysisRunRequest,
):
    """
    Start the complete IMMUNO-XAI pipeline.

    The endpoint returns immediately with a job ID.
    The actual analysis runs in a background thread.
    """

    job_id = request.job_id.strip()

    # --------------------------------------------------------
    # VALIDATE JOB ID
    # --------------------------------------------------------

    if not job_id:

        raise HTTPException(

            status_code=400,

            detail="job_id is required.",
        )

    # --------------------------------------------------------
    # FIND UPLOAD DIRECTORY
    # --------------------------------------------------------

    upload_dir = UPLOADS_DIR / job_id

    if not upload_dir.exists():

        raise HTTPException(

            status_code=404,

            detail=(
                f"Upload job not found: {job_id}"
            ),
        )

    if not upload_dir.is_dir():

        raise HTTPException(

            status_code=400,

            detail=(
                f"Upload path is not a directory: "
                f"{upload_dir}"
            ),
        )

    # --------------------------------------------------------
    # FIND DATASET
    # --------------------------------------------------------

    supported_extensions = (

        ".txt",
        ".txt.gz",

        ".csv",
        ".csv.gz",

        ".tsv",
        ".tsv.gz",
    )

    dataset_files = [

        path

        for path in upload_dir.iterdir()

        if path.is_file()

        and path.name.lower().endswith(
            supported_extensions
        )
    ]

    # --------------------------------------------------------
    # NO DATASET
    # --------------------------------------------------------

    if not dataset_files:

        raise HTTPException(

            status_code=404,

            detail=(
                "No supported expression "
                "matrix was found in the upload."
            ),
        )

    # --------------------------------------------------------
    # MULTIPLE DATASETS
    # --------------------------------------------------------

    if len(dataset_files) > 1:

        raise HTTPException(

            status_code=400,

            detail=(
                "Multiple expression datasets "
                "were found. Please upload "
                "exactly one dataset."
            ),
        )

    dataset_path = dataset_files[0]

    # --------------------------------------------------------
    # PREVENT DUPLICATE RUN
    # --------------------------------------------------------

    existing_job = get_job(job_id)

    if existing_job is not None:

        existing_status = existing_job["status"]

        if existing_status in {
            "queued",
            "running",
        }:

            return {

                "success": True,

                "job_id": job_id,

                "status": existing_status,

                "message": (
                    "Analysis is already running."
                ),
            }

        if existing_status == "completed":

            return {

                "success": True,

                "job_id": job_id,

                "status": "completed",

                "progress": 100.0,

                "message": (
                    "Analysis already completed."
                ),
            }

    # --------------------------------------------------------
    # CREATE JOB-SPECIFIC ANALYSIS DIRECTORY
    # --------------------------------------------------------

    analysis_dir = (
        ANALYSIS_DATA_DIR / job_id
    )

    # Remove previous incomplete output
    if analysis_dir.exists():

        shutil.rmtree(
            analysis_dir
        )

    analysis_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------------------------------
    # CREATE JOB
    # --------------------------------------------------------

    create_job(

        job_id=job_id,

        dataset_path=dataset_path,

        analysis_dir=analysis_dir,
    )

    # --------------------------------------------------------
    # START BACKGROUND THREAD
    # --------------------------------------------------------

    worker = threading.Thread(

        target=run_analysis_background,

        kwargs={

            "job_id": job_id,

            "dataset_path": dataset_path,

            "analysis_dir": analysis_dir,
        },

        daemon=True,

        name=f"immuno-xai-{job_id}",
    )

    worker.start()

    # --------------------------------------------------------
    # RETURN IMMEDIATELY
    # --------------------------------------------------------

    return {

        "success": True,

        "job_id": job_id,

        "status": "queued",

        "message": (
            "IMMUNO-XAI analysis started."
        ),

        "total_steps": TOTAL_STEPS,
    }


# ============================================================
# GET ANALYSIS STATUS
# ============================================================

@router.get("/{job_id}/status")
def get_analysis_status(
    job_id: str,
):
    """
    Return the current analysis progress.
    """

    job = get_job(job_id)

    if job is None:

        raise HTTPException(

            status_code=404,

            detail=(
                f"Analysis job not found: {job_id}"
            ),
        )

    response = {

        "success": True,

        "job_id": job["job_id"],

        "status": job["status"],

        "step": job["step"],

        "step_number": job["step_number"],

        "total_steps": job["total_steps"],

        "progress": job["progress"],

        "message": job["message"],

        "started_at": job["started_at"],

        "completed_at": job["completed_at"],
    }

    # --------------------------------------------------------
    # ERROR INFORMATION
    # --------------------------------------------------------

    if job["status"] == "failed":

        response["error"] = job["error"]

    return response


# ============================================================
# GET ANALYSIS RESULT
# ============================================================

@router.get("/{job_id}/result")
def get_analysis_result(
    job_id: str,
):
    """
    Return complete analysis results after the pipeline
    has finished.
    """

    job = get_job(job_id)

    if job is None:

        raise HTTPException(

            status_code=404,

            detail=(
                f"Analysis job not found: {job_id}"
            ),
        )

    # --------------------------------------------------------
    # QUEUED
    # --------------------------------------------------------

    if job["status"] == "queued":

        return {

            "success": True,

            "job_id": job_id,

            "status": "queued",

            "message": (
                "Analysis is queued."
            ),
        }

    # --------------------------------------------------------
    # RUNNING
    # --------------------------------------------------------

    if job["status"] == "running":

        return {

            "success": True,

            "job_id": job_id,

            "status": "running",

            "step": job["step"],

            "step_number": job["step_number"],

            "total_steps": job["total_steps"],

            "progress": job["progress"],

            "message": job["message"],
        }

    # --------------------------------------------------------
    # FAILED
    # --------------------------------------------------------

    if job["status"] == "failed":

        raise HTTPException(

            status_code=500,

            detail={

                "job_id": job_id,

                "message": job["message"],

                "error": job["error"],
            },
        )

    # --------------------------------------------------------
    # COMPLETED
    # --------------------------------------------------------

    analysis_dir = Path(
        job["analysis_dir"]
    )

    final_analysis_path = (
        analysis_dir
        / "final_analysis"
        / "final_analysis.json"
    )

    interpretation_path = (
        analysis_dir
        / "llm_reasoning"
        / "biological_interpretation.json"
    )

    report_path = (
        analysis_dir
        / "llm_reasoning"
        / "biological_report.md"
    )

    metadata_path = (
        analysis_dir
        / "llm_reasoning"
        / "llm_reasoning_metadata.json"
    )

    response: Dict[str, Any] = {
        "success": True,
        "job_id": job_id,
        "status": "completed",
        "progress": 100.0,
        "message": (
            "Analysis completed successfully."
        ),
    }

    # ========================================================
    # FINAL ANALYSIS
    # ========================================================

    if final_analysis_path.exists():

        try:

            with open(
                final_analysis_path,
                "r",
                encoding="utf-8",
            ) as handle:

                response["final_analysis"] = json.load(
                    handle
                )

        except Exception as exc:

            response[
                "final_analysis_error"
            ] = str(exc)

    # ========================================================
    # BIOLOGICAL INTERPRETATION
    # ========================================================

    if interpretation_path.exists():

        try:

            with open(
                interpretation_path,
                "r",
                encoding="utf-8",
            ) as handle:

                response[
                    "biological_interpretation"
                ] = json.load(handle)

        except Exception as exc:

            response[
                "biological_interpretation_error"
            ] = str(exc)

    # ========================================================
    # BIOLOGICAL REPORT
    # ========================================================

    if report_path.exists():

        try:

            response[
                "biological_report"
            ] = report_path.read_text(
                encoding="utf-8"
            )

        except Exception as exc:

            response[
                "biological_report_error"
            ] = str(exc)

    # ========================================================
    # LLM METADATA
    # ========================================================

    if metadata_path.exists():

        try:

            with open(
                metadata_path,
                "r",
                encoding="utf-8",
            ) as handle:

                response[
                    "llm_reasoning_metadata"
                ] = json.load(handle)

        except Exception as exc:

            response[
                "llm_reasoning_metadata_error"
            ] = str(exc)

    return response


# ============================================================
# LIST ANALYSIS JOBS
# ============================================================

@router.get("/")
def list_analysis_jobs():
    """
    Return all analysis jobs known to this API process.
    """

    with JOBS_LOCK:

        jobs = [

            {

                "job_id": job["job_id"],

                "status": job["status"],

                "step": job["step"],

                "step_number": job["step_number"],

                "total_steps": job["total_steps"],

                "progress": job["progress"],

                "message": job["message"],

                "started_at": job["started_at"],

                "completed_at": job["completed_at"],
            }

            for job in JOBS.values()
        ]

    return {

        "success": True,

        "count": len(jobs),

        "jobs": jobs,
    }