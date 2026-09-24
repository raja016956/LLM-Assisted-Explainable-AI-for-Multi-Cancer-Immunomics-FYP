from __future__ import annotations

import json
import shutil
import threading
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.pipeline.analysis_runner import run_full_analysis
from app.pipeline.report_generator import generate_analysis_report


# ============================================================
# ROUTER
# ============================================================

# Group all analysis-related endpoints under /analysis.
router = APIRouter(
    prefix="/analysis",
    tags=["analysis"],
)


# ============================================================
# PATHS
# ============================================================

# Define the main directories used for analysis outputs and uploads.

# backend/
BACKEND_DIR = Path(__file__).resolve().parents[2]

# backend/analysis_data/
ANALYSIS_DATA_DIR = BACKEND_DIR / "analysis_data"

# backend/backend_data/uploads/
UPLOADS_DIR = BACKEND_DIR / "backend_data" / "uploads"

# Create required directories if they do not already exist.
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

# Total number of steps in the IMMUNO-XAI analysis pipeline.
TOTAL_STEPS = 16

# Names of the analysis stages reported to the frontend.
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

def recover_completed_job(
    job_id: str,
) -> Dict[str, Any] | None:
    """
    Recover a completed analysis job from disk.

    Jobs are normally stored in the in-memory JOBS dictionary.
    After a Uvicorn restart, that dictionary is empty even though
    analysis output may still exist on disk.

    If the expected completed output files exist, reconstruct
    the job metadata so status/result endpoints continue to work.
    """

    analysis_dir = (
        ANALYSIS_DATA_DIR / job_id
    )

    if not analysis_dir.exists():
        return None

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

    required_files = [
        final_analysis_path,
        interpretation_path,
        report_path,
        metadata_path,
    ]

    if not all(
        path.exists()
        for path in required_files
    ):
        return None

    job = {
        "job_id": job_id,

        "status": "completed",

        "step": "llm_reasoning",

        "step_number": TOTAL_STEPS,

        "total_steps": TOTAL_STEPS,

        "progress": 100.0,

        "message": (
            "Analysis completed successfully."
        ),

        "dataset": None,

        "analysis_dir": str(
            analysis_dir
        ),

        "started_at": None,

        "completed_at": None,

        "error": None,

        "result": None,
    }

    with JOBS_LOCK:
        JOBS[job_id] = job

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

def analysis_files_exist(job_id: str) -> bool:
    """
    Check whether a completed analysis exists on disk.

    This allows completed jobs to survive a Uvicorn restart.
    """

    analysis_dir = ANALYSIS_DATA_DIR / job_id

    required_files = [
        analysis_dir
        / "final_analysis"
        / "final_analysis.json",

        analysis_dir
        / "final_analysis"
        / "llm_reasoning_input.json",

        analysis_dir
        / "llm_reasoning"
        / "biological_interpretation.json",

        analysis_dir
        / "llm_reasoning"
        / "biological_report.md",

        analysis_dir
        / "llm_reasoning"
        / "llm_reasoning_metadata.json",
    ]

    return all(
        path.exists()
        for path in required_files
    )


def recover_completed_job(
    job_id: str,
) -> Dict[str, Any] | None:
    """
    Recover a completed analysis job from disk.

    JOBS is in-memory and disappears after a server restart.
    The analysis output directory is therefore used as the
    persistent source of truth for completed analyses.
    """

    analysis_dir = ANALYSIS_DATA_DIR / job_id

    if not analysis_dir.exists():
        return None

    if not analysis_files_exist(job_id):
        return None

    return {
        "job_id": job_id,

        "status": "completed",

        "step": "llm_reasoning",

        "step_number": TOTAL_STEPS,

        "total_steps": TOTAL_STEPS,

        "progress": 100.0,

        "message": (
            "Analysis completed successfully."
        ),

        "dataset": "",

        "analysis_dir": str(
            analysis_dir
        ),

        "started_at": None,

        "completed_at": None,

        "error": None,

        "result": None,
    }


def analysis_files_exist(job_id: str) -> bool:
    """
    Check whether a completed analysis exists on disk.

    This allows completed jobs to survive a Uvicorn restart.
    """

    analysis_dir = ANALYSIS_DATA_DIR / job_id

    required_files = [
        analysis_dir
        / "final_analysis"
        / "final_analysis.json",

        analysis_dir
        / "final_analysis"
        / "llm_reasoning_input.json",

        analysis_dir
        / "llm_reasoning"
        / "biological_interpretation.json",

        analysis_dir
        / "llm_reasoning"
        / "biological_report.md",

        analysis_dir
        / "llm_reasoning"
        / "llm_reasoning_metadata.json",
    ]

    return all(
        path.exists()
        for path in required_files
    )


def recover_completed_job(
    job_id: str,
) -> Dict[str, Any] | None:
    """
    Recover a completed analysis job from disk.

    JOBS is in-memory and disappears after a server restart.
    The analysis output directory is therefore used as the
    persistent source of truth for completed analyses.
    """

    analysis_dir = ANALYSIS_DATA_DIR / job_id

    if not analysis_dir.exists():
        return None

    if not analysis_files_exist(job_id):
        return None

    return {
        "job_id": job_id,

        "status": "completed",

        "step": "llm_reasoning",

        "step_number": TOTAL_STEPS,

        "total_steps": TOTAL_STEPS,

        "progress": 100.0,

        "message": (
            "Analysis completed successfully."
        ),

        "dataset": "",

        "analysis_dir": str(
            analysis_dir
        ),

        "started_at": None,

        "completed_at": None,

        "error": None,

        "result": None,
    }


def get_job_or_recover(
    job_id: str,
) -> Dict[str, Any] | None:
    """
    Retrieve a job from memory.

    If it is not present in memory, attempt to recover
    a completed job from persistent analysis output.
    """

    job = get_job(job_id)

    if job is not None:
        return job

    recovered = recover_completed_job(
        job_id
    )

    if recovered is None:
        return None

    # Restore it into the in-memory store so subsequent
    # requests behave normally.
    with JOBS_LOCK:
        JOBS[job_id] = recovered

    return dict(recovered)

def recover_completed_job(
    job_id: str,
) -> Dict[str, Any] | None:
    """
    Recover a completed analysis job from disk after
    the in-memory JOBS store has been lost, for example
    after a Uvicorn restart.
    """

    analysis_dir = ANALYSIS_DATA_DIR / job_id

    # --------------------------------------------------------
    # ANALYSIS DIRECTORY MUST EXIST
    # --------------------------------------------------------

    if not analysis_dir.exists():
        return None

    # --------------------------------------------------------
    # REQUIRED COMPLETION FILE
    # --------------------------------------------------------

    final_analysis_path = (
        analysis_dir
        / "final_analysis"
        / "final_analysis.json"
    )

    if not final_analysis_path.exists():
        return None

    # --------------------------------------------------------
    # OPTIONAL TIMESTAMP FROM MANIFEST
    # --------------------------------------------------------

    completed_at = None

    manifest_path = (
        analysis_dir
        / "analysis_run_manifest.json"
    )

    if manifest_path.exists():

        try:

            with open(
                manifest_path,
                "r",
                encoding="utf-8",
            ) as handle:

                manifest = json.load(handle)

            completed_at = (
                manifest.get("completed_at")
                or manifest.get("finished_at")
                or manifest.get("timestamp")
            )

        except Exception:
            completed_at = None

    # --------------------------------------------------------
    # FALLBACK TIMESTAMP
    # --------------------------------------------------------

    if completed_at is None:

        try:

            completed_at = datetime.fromtimestamp(
                final_analysis_path.stat().st_mtime,
                tz=timezone.utc,
            ).isoformat()

        except Exception:
            completed_at = None

    # --------------------------------------------------------
    # RECONSTRUCT JOB
    # --------------------------------------------------------

    recovered_job: Dict[str, Any] = {

        "job_id": job_id,

        "status": "completed",

        "step": "llm_reasoning",

        "step_number": TOTAL_STEPS,

        "total_steps": TOTAL_STEPS,

        "progress": 100.0,

        "message": (
            "Analysis completed successfully."
        ),

        "dataset": None,

        "analysis_dir": str(analysis_dir),

        "started_at": None,

        "completed_at": completed_at,

        "error": None,

        "result": None,
    }

    # --------------------------------------------------------
    # PUT RECOVERED JOB BACK INTO MEMORY
    # --------------------------------------------------------

    with JOBS_LOCK:

        JOBS[job_id] = recovered_job

    return dict(recovered_job)

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

# Starts the background scientific analysis for a prepared upload job.
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

# Returns the current pipeline step and progress for one analysis job.
@router.get("/{job_id}/status")
def get_analysis_status(
    job_id: str,
):
    """
    Return the current analysis progress.
    """

    job = get_job(job_id)

    if job is None:
        job = recover_completed_job(job_id)

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

# Returns the completed analysis result used by the Results page.
@router.get("/{job_id}/result")
def get_analysis_result(
    job_id: str,
):
    """
    Return complete analysis results after the pipeline
    has finished.

    Completed results are loaded from disk so they remain
    available even after the API process restarts.
    """

    # --------------------------------------------------------
    # TRY IN-MEMORY JOB FIRST
    # --------------------------------------------------------

    job = get_job_or_recover(
        job_id
    )

    # --------------------------------------------------------
    # LOCATE PERSISTED ANALYSIS DIRECTORY
    # --------------------------------------------------------

    analysis_dir = (
        ANALYSIS_DATA_DIR
        / job_id
    )

    # --------------------------------------------------------
    # JOB DOES NOT EXIST IN MEMORY
    #
    # This can happen after Uvicorn restarts.
    # If the completed analysis directory exists, recover it
    # from disk.
    # --------------------------------------------------------

    if job is None:

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

        # ----------------------------------------------------
        # A completed analysis must have the final analysis
        # file.
        # ----------------------------------------------------

        if not final_analysis_path.exists():

            raise HTTPException(
                status_code=404,
                detail=(
                    f"Analysis job not found: {job_id}"
                ),
            )

        # ----------------------------------------------------
        # RECOVER COMPLETED JOB
        # ----------------------------------------------------

        job = {
            "job_id": job_id,

            "status": "completed",

            "step": "llm_reasoning",

            "step_number": TOTAL_STEPS,

            "total_steps": TOTAL_STEPS,

            "progress": 100.0,

            "message": (
                "Analysis completed successfully."
            ),

            "dataset": None,

            "analysis_dir": str(
                analysis_dir
            ),

            "started_at": None,

            "completed_at": None,

            "error": None,

            "result": None,
        }

        # ----------------------------------------------------
        # RECOVER COMPLETED RESULT FROM DISK
        # ----------------------------------------------------

        response: Dict[str, Any] = {

            "success": True,

            "job_id": job_id,

            "status": "completed",

            "progress": 100.0,

            "message": (
                "Analysis completed successfully."
            ),
        }

        # ----------------------------------------------------
        # FINAL ANALYSIS
        # ----------------------------------------------------

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

            raise HTTPException(
                status_code=500,
                detail=(
                    f"Failed to read final analysis: {exc}"
                ),
            )

        # ----------------------------------------------------
        # BIOLOGICAL INTERPRETATION
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # BIOLOGICAL REPORT
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # LLM METADATA
        # ----------------------------------------------------

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

    # ========================================================
    # NORMAL IN-MEMORY JOB
    # ========================================================

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

    # ========================================================
    # COMPLETED
    # ========================================================

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

    # IMPORTANT:
    # Do NOT include job["result"] here.
    # The raw pipeline result can contain NumPy/sklearn/
    # other Python objects that FastAPI cannot JSON encode.

    # --------------------------------------------------------
    # FINAL ANALYSIS
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # BIOLOGICAL INTERPRETATION
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # BIOLOGICAL REPORT
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # LLM METADATA
    # --------------------------------------------------------

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

def _read_upload_metadata(job_id: str) -> Dict[str, Any]:
    """
    Read persistent upload metadata for a job.

    Older uploads may not have metadata; those records are
    treated as legacy history entries.
    """
    metadata_path = (
        UPLOADS_DIR
        / job_id
        / "upload_metadata.json"
    )

    if not metadata_path.exists():
        return {}

    try:
        with metadata_path.open(
            "r",
            encoding="utf-8",
        ) as handle:
            data = json.load(handle)

        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _persistent_analysis_history() -> list[Dict[str, Any]]:
    """
    Scan persisted analysis directories so history survives
    Uvicorn restarts.
    """
    history: list[Dict[str, Any]] = []

    if not ANALYSIS_DATA_DIR.exists():
        return history

    for analysis_dir in ANALYSIS_DATA_DIR.iterdir():
        if not analysis_dir.is_dir():
            continue

        job_id = analysis_dir.name
        final_path = (
            analysis_dir
            / "final_analysis"
            / "final_analysis.json"
        )

        if not final_path.exists():
            continue

        metadata = _read_upload_metadata(job_id)
        completed_at = None

        manifest_path = (
            analysis_dir
            / "analysis_run_manifest.json"
        )

        if manifest_path.exists():
            try:
                with manifest_path.open(
                    "r",
                    encoding="utf-8",
                ) as handle:
                    manifest = json.load(handle)

                completed_at = (
                    manifest.get("completed_at")
                    or manifest.get("finished_at")
                )
            except Exception:
                completed_at = None

        if completed_at is None:
            try:
                completed_at = datetime.fromtimestamp(
                    final_path.stat().st_mtime,
                    tz=timezone.utc,
                ).isoformat()
            except Exception:
                completed_at = None

        dataset_name = metadata.get("filename")
        if not dataset_name:
            upload_dir = UPLOADS_DIR / job_id
            if upload_dir.exists():
                candidates = [
                    path
                    for path in upload_dir.iterdir()
                    if path.is_file()
                    and path.name.lower().endswith(
                        (
                            ".txt",
                            ".txt.gz",
                            ".csv",
                            ".csv.gz",
                            ".tsv",
                            ".tsv.gz",
                        )
                    )
                ]
                if len(candidates) == 1:
                    dataset_name = candidates[0].name

        history.append(
            {
                "job_id": job_id,
                "status": "completed",
                "progress": 100.0,
                "step": "llm_reasoning",
                "step_number": TOTAL_STEPS,
                "total_steps": TOTAL_STEPS,
                "message": "Analysis completed successfully.",
                "started_at": None,
                "completed_at": completed_at,
                "dataset_name": dataset_name or job_id,
                "file_size": metadata.get("file_size"),
                "owner_uid": metadata.get("user_id"),
                "report_available": True,
                "legacy": not bool(metadata.get("user_id")),
            }
        )

    return history


# Returns persisted analysis history used by the Dashboard and Reports pages.
@router.get("/")
def list_analysis_jobs():
    """
    Return persisted analysis history plus currently running jobs.

    Completed analyses are discovered from disk so dashboard history
    remains available after the API process restarts.
    """
    persisted = _persistent_analysis_history()

    by_job_id = {
        item["job_id"]: item
        for item in persisted
    }

    with JOBS_LOCK:
        memory_jobs = list(JOBS.values())

    for job in memory_jobs:
        job_id = job["job_id"]
        metadata = _read_upload_metadata(job_id)
        dataset_name = metadata.get("filename")

        if not dataset_name:
            dataset_value = job.get("dataset")
            if dataset_value:
                dataset_name = Path(str(dataset_value)).name

        entry = {
            "job_id": job_id,
            "status": job["status"],
            "step": job.get("step"),
            "step_number": job.get("step_number", 0),
            "total_steps": job.get("total_steps", TOTAL_STEPS),
            "progress": job.get("progress", 0.0),
            "message": job.get("message"),
            "started_at": job.get("started_at"),
            "completed_at": job.get("completed_at"),
            "dataset_name": dataset_name or job_id,
            "file_size": metadata.get("file_size"),
            "owner_uid": metadata.get("user_id") or job.get("owner_uid"),
            "report_available": job["status"] == "completed",
            "legacy": not bool(
                metadata.get("user_id") or job.get("owner_uid")
            ),
        }

        by_job_id[job_id] = entry

    jobs = sorted(
        by_job_id.values(),
        key=lambda item: (
            item.get("completed_at")
            or item.get("started_at")
            or "",
        ),
        reverse=True,
    )

    return {
        "success": True,
        "count": len(jobs),
        "jobs": jobs,
    }


# ============================================================
# PDF REPORT
# ============================================================

# Generates/returns the PDF report for a completed analysis.
@router.get("/{job_id}/report")
def download_analysis_report(job_id: str):
    """
    Generate and download the completed analysis as a PDF.
    """

    job = get_job_or_recover(job_id)

    if job is None:
        raise HTTPException(
            status_code=404,
            detail=f"Analysis job not found: {job_id}",
        )

    if job["status"] != "completed":
        raise HTTPException(
            status_code=409,
            detail=(
                "PDF report is available only after the analysis "
                f"has completed. Current status: {job['status']}."
            ),
        )

    analysis_dir = ANALYSIS_DATA_DIR / job_id
    final_analysis_path = (
        analysis_dir / "final_analysis" / "final_analysis.json"
    )

    if not final_analysis_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Completed analysis output was not found.",
        )

    dataset_name = None
    dataset_value = job.get("dataset")

    if dataset_value:
        dataset_name = Path(str(dataset_value)).name

    if not dataset_name:
        upload_dir = UPLOADS_DIR / job_id
        if upload_dir.exists():
            candidates = [
                path
                for path in upload_dir.iterdir()
                if path.is_file()
                and path.name.lower().endswith(
                    (".txt", ".txt.gz", ".csv", ".csv.gz", ".tsv", ".tsv.gz")
                )
            ]
            if len(candidates) == 1:
                dataset_name = candidates[0].name

    try:
        pdf_path = generate_analysis_report(
            job_id=job_id,
            analysis_dir=analysis_dir,
            dataset_name=dataset_name,
        )
    except Exception as exc:
        traceback_text = traceback.format_exc()
        print("PDF REPORT GENERATION FAILED")
        print(traceback_text)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate PDF report: {exc}",
        )

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=f"IMMUNO_XAI_Report_{job_id}.pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="IMMUNO_XAI_Report_{job_id}.pdf"'
            )
        },
    )

# ============================================================
# UMAP VISUALIZATION
# ============================================================

# Returns UMAP coordinates, cluster labels, and immune states for the frontend chart.
@router.get("/{job_id}/visualizations/umap")
def get_umap_visualization(job_id: str):
    """Return UMAP coordinates with cluster and immune-state labels."""

    analysis_dir = ANALYSIS_DATA_DIR / job_id
    umap_path = analysis_dir / "umap" / "umap_coordinates.npy"
    cluster_path = analysis_dir / "clustering" / "cluster_labels.npy"
    states_path = analysis_dir / "immune_state_assignment" / "cell_immune_states.json"

    if not analysis_dir.exists():
        raise HTTPException(status_code=404, detail=f"Analysis job not found: {job_id}")

    missing = [
        str(path.relative_to(analysis_dir))
        for path in (umap_path, cluster_path, states_path)
        if not path.exists()
    ]
    if missing:
        raise HTTPException(
            status_code=404,
            detail="UMAP visualization data is incomplete: " + ", ".join(missing),
        )

    try:
        import numpy as np

        embedding = np.load(umap_path)
        clusters = np.load(cluster_path)

        if embedding.ndim != 2 or embedding.shape[1] < 2:
            raise ValueError("UMAP coordinates must contain at least two dimensions.")
        if clusters.ndim != 1 or clusters.shape[0] != embedding.shape[0]:
            raise ValueError("UMAP coordinates and cluster labels have different cell counts.")

        with open(states_path, "r", encoding="utf-8") as handle:
            state_payload = json.load(handle)
        cells = state_payload.get("cells", [])

        if len(cells) != embedding.shape[0]:
            raise ValueError("UMAP coordinates and immune-state assignments have different cell counts.")

        n_cells = int(embedding.shape[0])
        max_points = 12000
        if n_cells > max_points:
            indices = np.linspace(0, n_cells - 1, max_points, dtype=int)
        else:
            indices = np.arange(n_cells)

        points = [
            {
                "x": float(embedding[int(index), 0]),
                "y": float(embedding[int(index), 1]),
                "cluster": int(clusters[int(index)]),
                "state": str(cells[int(index)].get("state", "Unclassified")),
            }
            for index in indices
        ]

        return {
            "success": True,
            "n_cells": n_cells,
            "plotted_cells": len(points),
            "points": points,
        }

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load UMAP visualization: {exc}")
