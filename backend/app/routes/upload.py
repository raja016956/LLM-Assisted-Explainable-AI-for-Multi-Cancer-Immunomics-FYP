import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.models import UploadResponse


router = APIRouter(
    prefix="/upload",
    tags=["Upload"],
)


UPLOAD_DIR = Path("backend_data/uploads")
UPLOAD_DIR.mkdir(
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