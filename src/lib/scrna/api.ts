// ============================================================
// IMMUNO-XAI API CLIENT
// ============================================================

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  "http://127.0.0.1:8000";


// ============================================================
// TYPES
// ============================================================

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

export interface AnalysisStatusResponse {
  success: boolean;
  job_id: string;
  status: "queued" | "running" | "completed" | "failed";
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

export interface AnalysisResultResponse {
  success: boolean;
  job_id: string;
  status: string;
  [key: string]: unknown;
}


// ============================================================
// ERROR HANDLING
// ============================================================

async function parseApiError(
  response: Response,
): Promise<string> {
  try {
    const data = await response.json();

    if (typeof data?.detail === "string") {
      return data.detail;
    }

    if (typeof data?.detail?.message === "string") {
      return data.detail.message;
    }

    if (typeof data?.message === "string") {
      return data.message;
    }

    return JSON.stringify(data);
  } catch {
    return response.statusText || "API request failed.";
  }
}


// ============================================================
// GENERIC REQUEST
// ============================================================

async function apiRequest<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const response = await fetch(
    `${API_BASE_URL}${path}`,
    {
      ...options,
      headers: {
        ...(options?.headers || {}),
      },
    },
  );

  if (!response.ok) {
    const message =
      await parseApiError(response);

    throw new Error(
      `API ${response.status}: ${message}`,
    );
  }

  return response.json() as Promise<T>;
}


// ============================================================
// UPLOAD DATASET
// ============================================================

export async function uploadDataset(
  file: File,
): Promise<UploadResponse> {
  const formData = new FormData();

  formData.append("file", file);

  return apiRequest<UploadResponse>(
    "/api/upload",
    {
      method: "POST",
      body: formData,
    },
  );
}


// ============================================================
// START ANALYSIS
// ============================================================

export async function startAnalysis(
  jobId: string,
): Promise<StartAnalysisResponse> {
  return apiRequest<StartAnalysisResponse>(
    "/api/analysis/run",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        job_id: jobId,
      }),
    },
  );
}


// ============================================================
// GET ANALYSIS STATUS
// ============================================================

export async function getAnalysisStatus(
  jobId: string,
): Promise<AnalysisStatusResponse> {
  return apiRequest<AnalysisStatusResponse>(
    `/api/analysis/${encodeURIComponent(jobId)}/status`,
  );
}


// ============================================================
// GET ANALYSIS RESULT
// ============================================================

export async function getAnalysisResult(
  jobId: string,
): Promise<AnalysisResultResponse> {
  return apiRequest<AnalysisResultResponse>(
    `/api/analysis/${encodeURIComponent(jobId)}/result`,
  );
}


// ============================================================
// LIST ANALYSIS JOBS
// ============================================================

export async function listAnalysisJobs(): Promise<
  unknown
> {
  return apiRequest(
    "/api/analysis/",
  );
}


// ============================================================
// HEALTH CHECK
// ============================================================

export async function checkApiHealth(): Promise<{
  status: string;
}> {
  return apiRequest(
    "/health",
  );
}