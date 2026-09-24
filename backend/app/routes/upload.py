import json
import shutil
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.models import UploadResponse
from app.pipeline.preloaded_datasets import PRELOADED_BY_ID, PRELOADED_DATASETS


// All dataset upload endpoints are grouped under /api/upload.
router = APIRouter(
    prefix="/upload",
    tags=["Upload"],
)


// Each upload job gets its own directory so the analysis pipeline can find it later.
UPLOAD_DIR = Path("backend_data/uploads")
UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

// Cached copies of public preloaded datasets are stored here after first download.
PRELOADED_DIR = Path("backend_data/preloaded_datasets")
PRELOADED_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


ALLOWED_EXTENSIONS = (
    ".csv",
    ".tsv",
    ".txt",
    ".gz",
)


@router.post(
    "",
    response_model=UploadResponse,
)
async def upload_dataset(
    file: UploadFile = File(...),
    user_id: str | None = Form(default=None),
):
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No filename was provided.",
        )

    filename = file.filename

    lower_filename = filename.lower()

    if not lower_filename.endswith(ALLOWED_EXTENSIONS):
        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported dataset format. "
                "Supported formats: CSV, TSV, TXT, GZ."
            ),
        )

    job_id = str(uuid4())

    job_dir = UPLOAD_DIR / job_id
    job_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination = job_dir / filename

    total_size = 0

    try:
        with destination.open("wb") as output:

            while True:
                chunk = await file.read(1024 * 1024)

                if not chunk:
                    break

                output.write(chunk)
                total_size += len(chunk)

    except Exception as exc:

        if destination.exists():
            destination.unlink()

        raise HTTPException(
            status_code=500,
            detail=f"Failed to save dataset: {exc}",
        )

    metadata = {
        "job_id": job_id,
        "user_id": user_id.strip() if user_id else None,
        "filename": filename,
        "file_size": total_size,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        (job_dir / "upload_metadata.json").write_text(
            json.dumps(metadata, indent=2),
            encoding="utf-8",
        )
    except Exception:
        # Metadata is helpful for dashboard history but must not
        # make an otherwise successful dataset upload fail.
        pass

    return UploadResponse(
        job_id=job_id,
        filename=filename,
        file_size=total_size,
        status="uploaded",
        message="Dataset uploaded successfully.",
    )

// Returns the cancer datasets shown as selectable cards on the Upload page.
@router.get("/preloaded")
def list_preloaded_datasets():
    """Return the curated public datasets available for one-click analysis."""

    return {
        "success": True,
        "datasets": [
            {
                "id": dataset.id,
                "cancer_type": dataset.cancer_type,
                "name": dataset.name,
                "description": dataset.description,
                "accession": dataset.accession,
            }
            for dataset in PRELOADED_DATASETS
        ],
    }


// Prepares a selected public dataset as a normal analysis job so the existing pipeline can process it.
@router.post("/preloaded/{dataset_id}", response_model=UploadResponse)
def use_preloaded_dataset(
    dataset_id: str,
    user_id: str | None = None,
):
    """Cache a curated public dataset and create a normal upload job for it."""

    dataset = PRELOADED_BY_ID.get(dataset_id)

    if dataset is None:
        raise HTTPException(
            status_code=404,
            detail="Preloaded dataset was not found.",
        )

    cache_dir = PRELOADED_DIR / dataset.id
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached_file = cache_dir / dataset.filename

    if not cached_file.exists():
        temporary_file = cache_dir / f"{dataset.filename}.download"

        try:
            request = urllib.request.Request(
                dataset.source_url,
                headers={"User-Agent": "ImmunoXAI/1.0"},
            )

            with urllib.request.urlopen(request, timeout=120) as response:
                with temporary_file.open("wb") as output:
                    shutil.copyfileobj(response, output, length=1024 * 1024)

            temporary_file.replace(cached_file)

        except Exception as exc:
            if temporary_file.exists():
                temporary_file.unlink()

            raise HTTPException(
                status_code=502,
                detail=f"Unable to download the preloaded dataset: {exc}",
            )

    job_id = str(uuid4())
    job_dir = UPLOAD_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    destination = job_dir / dataset.filename

    try:
        shutil.copy2(cached_file, destination)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to prepare the preloaded dataset: {exc}",
        )

    total_size = destination.stat().st_size

    metadata = {
        "job_id": job_id,
        "user_id": user_id.strip() if user_id else None,
        "filename": dataset.filename,
        "file_size": total_size,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "source": "preloaded",
        "preloaded_dataset_id": dataset.id,
        "cancer_type": dataset.cancer_type,
        "accession": dataset.accession,
    }

    try:
        (job_dir / "upload_metadata.json").write_text(
            json.dumps(metadata, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass

    return UploadResponse(
        job_id=job_id,
        filename=dataset.filename,
        file_size=total_size,
        status="uploaded",
        message=f"Preloaded {dataset.cancer_type} dataset is ready for analysis.",
    )
