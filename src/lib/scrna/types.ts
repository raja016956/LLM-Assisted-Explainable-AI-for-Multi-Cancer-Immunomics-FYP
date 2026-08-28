// ============================================================
// IMMUNO-XAI FRONTEND API TYPES
// ============================================================

export type AnalysisJobStatus =
  | "queued"
  | "running"
  | "completed"
  | "failed";

export interface UploadResponse {
  job_id: string;
  filename: string;
  file_size: number;
  status: string;
  message: string;
}

export interface StartAnalysisResponse {
  success: boolean;
  job_id: string;
  status: string;
  message: string;
  total_steps?: number;
  progress?: number;
}

export interface AnalysisStatus {
  success: boolean;
  job_id: string;
  status: AnalysisJobStatus;
  step: string | null;
  step_number: number;
  total_steps: number;
  progress: number;
  message: string;
  started_at: string | null;
  completed_at: string | null;
  error?: {
    type?: string;
    message?: string;
    traceback?: string;
  };
}

export interface AnalysisResult {
  success: boolean;
  job_id: string;
  status: string;

  [key: string]: unknown;
}