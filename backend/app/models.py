from pydantic import BaseModel
from typing import Optional


class UploadResponse(BaseModel):
    job_id: str
    filename: str
    file_size: int
    status: str
    message: str


class AnalysisProgress(BaseModel):
    job_id: str
    status: str
    step: str
    step_number: int
    total_steps: int
    progress: float
    message: str
    elapsed_seconds: float
    estimated_remaining_seconds: Optional[float] = None


class AnalysisResult(BaseModel):
    job_id: str
    status: str
    filename: str

    total_cells: Optional[int] = None
    total_genes: Optional[int] = None

    qc_cells_before: Optional[int] = None
    qc_cells_after: Optional[int] = None

    qc_genes_before: Optional[int] = None
    qc_genes_after: Optional[int] = None

    normalization: Optional[str] = None

    immune_states: Optional[dict] = None

    model_name: Optional[str] = None

    accuracy: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1_score: Optional[float] = None

    runtime_seconds: Optional[float] = None

    message: Optional[str] = None