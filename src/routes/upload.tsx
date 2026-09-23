import { createFileRoute, useNavigate } from "@tanstack/react-router";
import {
  UploadCloud,
  FileText,
  CheckCircle2,
  AlertCircle,
  Loader2,
  X,
  Clock3,
  Database,
  FlaskConical,
  BrainCircuit,
  BarChart3,
  Dna,
  Microscope,
  Network,
  Sparkles,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { AppLayout } from "@/components/AppLayout";
import { auth } from "@/lib/firebase";


// ============================================================
// ROUTE
// ============================================================

export const Route = createFileRoute("/upload")({
  head: () => ({
    meta: [
      {
        title: "Analyze Dataset — ImmunoXAI",
      },
      {
        name: "description",
        content:
          "Upload a single-cell gene expression dataset and run the complete ImmunoXAI analysis pipeline.",
      },
    ],
  }),
  component: UploadPage,
});


// ============================================================
// BACKEND API
// ============================================================

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  "http://127.0.0.1:8000";


// ============================================================
// REAL BACKEND PIPELINE STEPS
// ============================================================

type AnalysisStep = {
  id: string;
  label: string;
  description: string;
  icon: typeof Database;
};

const ANALYSIS_STEPS: AnalysisStep[] = [
  {
    id: "dataset_inspection",
    label: "Dataset inspection",
    description:
      "Inspecting the expression matrix structure, genes, and cells.",
    icon: Database,
  },
  {
    id: "validation",
    label: "Dataset validation",
    description:
      "Validating the expression matrix and checking data integrity.",
    icon: CheckCircle2,
  },
  {
    id: "quality_control",
    label: "Quality control",
    description:
      "Calculating QC metrics and filtering low-quality cells.",
    icon: FlaskConical,
  },
  {
    id: "normalization",
    label: "Normalization",
    description:
      "Applying library-size normalization and log transformation.",
    icon: BarChart3,
  },
  {
    id: "feature_selection",
    label: "Feature selection",
    description:
      "Selecting highly variable genes for downstream analysis.",
    icon: Dna,
  },
  {
    id: "pca",
    label: "PCA",
    description:
      "Computing principal components from the selected features.",
    icon: BarChart3,
  },
  {
    id: "umap",
    label: "UMAP",
    description:
      "Computing a low-dimensional representation of cellular profiles.",
    icon: Network,
  },
  {
    id: "clustering",
    label: "Clustering",
    description:
      "Identifying transcriptionally distinct cellular populations.",
    icon: Microscope,
  },
  {
    id: "immune_state_scoring",
    label: "Immune-state scoring",
    description:
      "Calculating immune-related gene-set activity scores.",
    icon: FlaskConical,
  },
  {
    id: "immune_state_assignment",
    label: "Immune-state assignment",
    description:
      "Assigning evidence-aware immune states to cells and clusters.",
    icon: Microscope,
  },
  {
    id: "machine_learning",
    label: "Machine learning",
    description:
      "Training the immune-state machine-learning classifier.",
    icon: BrainCircuit,
  },
  {
    id: "explainable_ai",
    label: "Explainable AI",
    description:
      "Generating SHAP-based model explanations and feature importance.",
    icon: BrainCircuit,
  },
  {
    id: "pathway_scoring",
    label: "Pathway scoring",
    description:
      "Calculating metabolic and inflammatory pathway activity.",
    icon: BarChart3,
  },
  {
    id: "pathway_immune_integration",
    label: "Pathway / immune integration",
    description:
      "Integrating pathway activity with immune-state information.",
    icon: Network,
  },
  {
    id: "final_analysis",
    label: "Final analysis",
    description:
      "Building the integrated computational analysis package.",
    icon: Microscope,
  },
  {
    id: "llm_reasoning",
    label: "Biological interpretation",
    description:
      "Generating the biological interpretation of the computational analysis.",
    icon: Sparkles,
  },
];


// ============================================================
// TYPES
// ============================================================

type AnalysisStatus =
  | "idle"
  | "ready"
  | "uploading"
  | "starting"
  | "queued"
  | "running"
  | "completed"
  | "failed"
  | "error";

type BackendStatusResponse = {
  success?: boolean;
  job_id: string;
  status: string;
  step?: string | null;
  step_number?: number;
  total_steps?: number;
  progress?: number;
  message?: string;
  started_at?: string | null;
  completed_at?: string | null;
  error?: unknown;
};

type UploadResponse = {
  success?: boolean;
  job_id: string;
  filename: string;
  file_size: number;
  status: string;
  message: string;
};

type PreloadedDataset = {
  id: string;
  cancer_type: string;
  name: string;
  description: string;
  accession: string;
};


// ============================================================
// TIME FORMATTER
// ============================================================

function formatTime(seconds: number | null) {
  if (seconds === null) {
    return "Calculating...";
  }

  const safeSeconds = Math.max(
    0,
    Math.round(seconds),
  );

  const minutes = Math.floor(
    safeSeconds / 60,
  );

  const remaining = safeSeconds % 60;

  if (minutes === 0) {
    return `${remaining}s`;
  }

  return `${minutes}m ${remaining
    .toString()
    .padStart(2, "0")}s`;
}


// ============================================================
// UPLOAD PAGE
// ============================================================

function UploadPage() {
  const navigate = useNavigate();

  const [file, setFile] =
    useState<File | null>(null);

  const [status, setStatus] =
    useState<AnalysisStatus>("idle");

  const [error, setError] =
    useState("");

  const [jobId, setJobId] =
    useState<string | null>(null);

  const [currentStep, setCurrentStep] =
    useState(0);

  const [backendStep, setBackendStep] =
    useState<string | null>(null);

  const [progress, setProgress] =
    useState(0);

  const [elapsedSeconds, setElapsedSeconds] =
    useState(0);

  const [startedAt, setStartedAt] =
    useState<string | null>(null);

  const [preloadedDatasets, setPreloadedDatasets] =
    useState<PreloadedDataset[]>([]);

  const [selectedPreloaded, setSelectedPreloaded] =
    useState<PreloadedDataset | null>(null);


  useEffect(() => {
    async function loadPreloadedDatasets() {
      try {
        const response = await fetch(
          `${API_BASE_URL}/api/upload/preloaded`,
          { headers: { Accept: "application/json" } },
        );

        if (!response.ok) return;

        const data = (await response.json()) as {
          datasets?: PreloadedDataset[];
        };

        setPreloadedDatasets(
          Array.isArray(data.datasets) ? data.datasets : [],
        );
      } catch (err) {
        console.error(
          "[ImmunoXAI] Failed to load preloaded datasets:",
          err,
        );
      }
    }

    void loadPreloadedDatasets();
  }, []);

  // ==========================================================
  // RUNNING
  // ==========================================================

  const isRunning =
    status === "uploading" ||
    status === "starting" ||
    status === "queued" ||
    status === "running";


  // ==========================================================
  // ELAPSED TIMER
  // ==========================================================

  useEffect(() => {
    if (!isRunning) {
      return;
    }

    const interval =
      window.setInterval(() => {
        if (startedAt) {
          const start =
            new Date(startedAt).getTime();

          const now =
            Date.now();

          setElapsedSeconds(
            Math.max(
              0,
              Math.floor(
                (now - start) / 1000,
              ),
            ),
          );
        } else {
          setElapsedSeconds(
            (seconds) => seconds + 1,
          );
        }
      }, 1000);

    return () =>
      window.clearInterval(interval);
  }, [
    isRunning,
    startedAt,
  ]);


  // ==========================================================
  // ESTIMATED REMAINING TIME
  //
  // This is only an estimate.
  // The progress itself comes from the backend.
  // ==========================================================

  const remainingSeconds =
    useMemo(() => {
      if (
        progress <= 0 ||
        progress >= 100 ||
        elapsedSeconds <= 0
      ) {
        return null;
      }

      const totalEstimated =
        elapsedSeconds *
        (100 / progress);

      return Math.max(
        0,
        Math.round(
          totalEstimated -
            elapsedSeconds,
        ),
      );
    }, [
      progress,
      elapsedSeconds,
    ]);


  // ==========================================================
  // FILE SELECTION
  // ==========================================================

  function handleFileChange(
    event: React.ChangeEvent<HTMLInputElement>,
  ) {
    const selectedFile =
      event.target.files?.[0];

    if (!selectedFile) {
      return;
    }

    setError("");

    const lowerName =
      selectedFile.name.toLowerCase();

    const supported =
      lowerName.endsWith(".csv") ||
      lowerName.endsWith(".tsv") ||
      lowerName.endsWith(".txt") ||
      lowerName.endsWith(".gz");

    if (!supported) {
      setFile(null);
      setStatus("error");

      setError(
        "Unsupported file format. Upload a CSV, TSV, TXT, or GZ expression matrix.",
      );

      return;
    }

    setFile(selectedFile);
    setSelectedPreloaded(null);
    setStatus("ready");
    setJobId(null);
    setBackendStep(null);
    setCurrentStep(0);
    setProgress(0);
    setElapsedSeconds(0);
    setStartedAt(null);
  }


  // ==========================================================
  // CLEAR DATASET
  // ==========================================================

  function clearFile() {
    if (isRunning) {
      return;
    }

    setFile(null);
    setSelectedPreloaded(null);
    setStatus("idle");
    setError("");
    setJobId(null);
    setBackendStep(null);
    setCurrentStep(0);
    setProgress(0);
    setElapsedSeconds(0);
    setStartedAt(null);
  }


  // ==========================================================
  // UPLOAD TO BACKEND
  // ==========================================================

  async function uploadDataset(
    selectedFile: File,
  ): Promise<UploadResponse> {
    const formData =
      new FormData();

    formData.append(
      "file",
      selectedFile,
    );

    const userId = auth.currentUser?.uid;

    if (userId) {
      formData.append("user_id", userId);
    }

    const response =
      await fetch(
        `${API_BASE_URL}/api/upload`,
        {
          method: "POST",
          body: formData,
        },
      );

    const data =
      await response.json()
        .catch(() => null);

    if (!response.ok) {
      const message =
        typeof data?.detail === "string"
          ? data.detail
          : "Dataset upload failed.";

      throw new Error(message);
    }

    return data as UploadResponse;
  }


  // ==========================================================
  // START BACKEND ANALYSIS
  // ==========================================================

  async function startAnalysis(
    uploadedJobId: string,
  ) {
    const response =
      await fetch(
        `${API_BASE_URL}/api/analysis/run`,
        {
          method: "POST",
          headers: {
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify({
            job_id: uploadedJobId,
          }),
        },
      );

    const data =
      await response.json()
        .catch(() => null);

    if (!response.ok) {
      const message =
        typeof data?.detail === "string"
          ? data.detail
          : "Failed to start analysis.";

      throw new Error(message);
    }

    return data;
  }


  // ==========================================================
  // POLL BACKEND STATUS
  // ==========================================================

  async function pollAnalysisStatus(
    uploadedJobId: string,
  ) {
    const response =
      await fetch(
        `${API_BASE_URL}/api/analysis/${encodeURIComponent(
          uploadedJobId,
        )}/status`,
        {
          method: "GET",
          headers: {
            Accept:
              "application/json",
          },
        },
      );

    const data =
      await response.json()
        .catch(() => null);

    if (!response.ok) {
      const message =
        typeof data?.detail === "string"
          ? data.detail
          : "Unable to retrieve analysis status.";

      throw new Error(message);
    }

    return data as BackendStatusResponse;
  }


  // ==========================================================
  // GET FINAL RESULT
  // ==========================================================

  async function getAnalysisResult(
    uploadedJobId: string,
  ) {
    const response =
      await fetch(
        `${API_BASE_URL}/api/analysis/${encodeURIComponent(
          uploadedJobId,
        )}/result`,
        {
          method: "GET",
          headers: {
            Accept:
              "application/json",
          },
        },
      );

    const data =
      await response.json()
        .catch(() => null);

    if (!response.ok) {
      const detail =
        data?.detail;

      if (
        typeof detail === "string"
      ) {
        throw new Error(detail);
      }

      if (
        detail?.message
      ) {
        throw new Error(
          detail.message,
        );
      }

      throw new Error(
        "Unable to retrieve final analysis result.",
      );
    }

    return data;
  }


  // ==========================================================
  // CONVERT BACKEND STEP TO UI INDEX
  // ==========================================================

  function getStepIndex(
    step: string | null | undefined,
    stepNumber?: number,
  ) {
    if (step) {
      const index =
        ANALYSIS_STEPS.findIndex(
          (item) =>
            item.id === step,
        );

      if (index >= 0) {
        return index;
      }
    }

    if (
      typeof stepNumber === "number" &&
      stepNumber > 0
    ) {
      return Math.min(
        stepNumber - 1,
        ANALYSIS_STEPS.length - 1,
      );
    }

    return 0;
  }


  // ==========================================================
  // RUN COMPLETE ANALYSIS
  // ==========================================================

  function selectPreloadedDataset(dataset: PreloadedDataset) {
    if (isRunning) return;

    setSelectedPreloaded(dataset);
    setFile(null);
    setStatus("ready");
    setError("");
    setJobId(null);
    setBackendStep(null);
    setCurrentStep(0);
    setProgress(0);
    setElapsedSeconds(0);
    setStartedAt(null);
  }

  async function handleAnalyze() {
    if (!file && !selectedPreloaded) {
      setError(
        "Please upload a dataset or select a preloaded dataset first.",
      );

      return;
    }

    setError("");
    setStatus("uploading");
    setProgress(0);
    setCurrentStep(0);
    setBackendStep(null);
    setElapsedSeconds(0);
    setStartedAt(null);


    try {
      // --------------------------------------------------------
      // STEP A — UPLOAD DATASET
      // --------------------------------------------------------

      let uploadedJobId: string;

      if (selectedPreloaded) {
        const userId = auth.currentUser?.uid;
        const query = userId
          ? `?user_id=${encodeURIComponent(userId)}`
          : "";

        const response = await fetch(
          `${API_BASE_URL}/api/upload/preloaded/${encodeURIComponent(
            selectedPreloaded.id,
          )}${query}`,
          { method: "POST", headers: { Accept: "application/json" } },
        );

        const data = await response.json().catch(() => null);

        if (!response.ok) {
          throw new Error(
            typeof data?.detail === "string"
              ? data.detail
              : "Unable to prepare the preloaded dataset.",
          );
        }

        uploadedJobId = (data as UploadResponse).job_id;
      } else {
        const upload = await uploadDataset(file as File);
        uploadedJobId = upload.job_id;
      }

      setJobId(
        uploadedJobId,
      );


      // --------------------------------------------------------
      // STEP B — START ANALYSIS
      // --------------------------------------------------------

      setStatus("starting");

      await startAnalysis(
        uploadedJobId,
      );


      // --------------------------------------------------------
      // STEP C — INITIAL STATUS
      // --------------------------------------------------------

      setStatus("queued");

      let finished = false;

      while (!finished) {
        const statusData =
          await pollAnalysisStatus(
            uploadedJobId,
          );

        const backendStatus =
          statusData.status;

        const backendProgress =
          Number(
            statusData.progress ?? 0,
          );

        const stepIndex =
          getStepIndex(
            statusData.step,
            statusData.step_number,
          );

        setBackendStep(
          statusData.step ??
            null,
        );

        setCurrentStep(
          stepIndex,
        );

        setProgress(
          Math.min(
            100,
            Math.max(
              0,
              Math.round(
                backendProgress,
              ),
            ),
          ),
        );

        if (
          statusData.started_at
        ) {
          setStartedAt(
            statusData.started_at,
          );
        }

        if (
          backendStatus ===
            "running" ||
          backendStatus ===
            "queued"
        ) {
          setStatus(
            backendStatus ===
              "running"
              ? "running"
              : "queued",
          );
        }


        // ------------------------------------------------------
        // COMPLETED
        // ------------------------------------------------------

        if (
          backendStatus ===
          "completed"
        ) {
          setProgress(100);
          setCurrentStep(
            ANALYSIS_STEPS.length - 1,
          );
          setBackendStep(
            "completed",
          );

          setStatus(
            "completed",
          );

          finished = true;

          break;
        }


        // ------------------------------------------------------
        // FAILED
        // ------------------------------------------------------

        if (
          backendStatus ===
          "failed"
        ) {
          const errorMessage =
            extractBackendError(
              statusData.error,
            );

          throw new Error(
            errorMessage ||
              statusData.message ||
              "The analysis pipeline failed.",
          );
        }


        // ------------------------------------------------------
        // WAIT BEFORE NEXT POLL
        // ------------------------------------------------------

        await wait(1500);
      }


      // --------------------------------------------------------
      // STEP D — GET FINAL RESULT
      // --------------------------------------------------------

      const finalResult =
        await getAnalysisResult(
          uploadedJobId,
        );


      // --------------------------------------------------------
      // SAVE REAL BACKEND RESULT
      // --------------------------------------------------------

      sessionStorage.setItem(
        "immunoxai-analysis",
        JSON.stringify(
          finalResult,
        ),
      );

      sessionStorage.setItem(
        "immunoxai-job-id",
        uploadedJobId,
      );


      // --------------------------------------------------------
      // GO TO RESULTS
      // --------------------------------------------------------

      await wait(500);

      navigate({
        to: "/results",
      });
    } catch (err) {
      console.error(
        "IMMUNO-XAI analysis error:",
        err,
      );

      const message =
        err instanceof Error
          ? err.message
          : "An unexpected analysis error occurred.";

      setStatus("failed");
      setError(message);
    }
  }


  // ==========================================================
  // RENDER
  // ==========================================================

  return (
    <AppLayout
      title="Analyze Dataset"
      subtitle="Run the complete ImmunoXAI single-cell analysis pipeline"
    >
      <div className="mx-auto max-w-5xl">

        {!isRunning ? (
          <>
            <PreloadedDatasetCard
              datasets={preloadedDatasets}
              selectedId={selectedPreloaded?.id ?? null}
              onSelect={selectPreloadedDataset}
            />

            <div className="mt-6">
              <UploadCard
                file={file}
                selectedPreloaded={selectedPreloaded}
                status={status}
                error={error}
                jobId={jobId}
                onFileChange={
                  handleFileChange
                }
                onClear={clearFile}
                onAnalyze={
                  handleAnalyze
                }
              />
            </div>
          </>
        ) : (
          <AnalysisProgressCard
            file={file}
            datasetName={selectedPreloaded?.name ?? null}
            jobId={jobId}
            currentStep={
              currentStep
            }
            backendStep={
              backendStep
            }
            progress={progress}
            elapsedSeconds={
              elapsedSeconds
            }
            remainingSeconds={
              remainingSeconds
            }
          />
        )}

      </div>
    </AppLayout>
  );
}



function PreloadedDatasetCard({
  datasets,
  selectedId,
  onSelect,
}: {
  datasets: PreloadedDataset[];
  selectedId: string | null;
  onSelect: (dataset: PreloadedDataset) => void;
}) {
  if (datasets.length === 0) return null;

  return (
    <div className="rounded-2xl border border-border bg-card p-6 shadow-sm">
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary-soft text-primary">
          <Database className="h-5 w-5" />
        </div>
        <div>
          <h2 className="text-base font-semibold text-foreground">
            Preloaded cancer datasets
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Select a curated public dataset and run the same analysis pipeline without uploading a file.
          </p>
        </div>
      </div>

      <div className="mt-5 grid grid-cols-1 gap-3 md:grid-cols-3">
        {datasets.map((dataset) => (
          <div
            key={dataset.id}
            className={[
              "rounded-xl border p-4 transition",
              selectedId === dataset.id
                ? "border-primary bg-primary-soft/40"
                : "border-border bg-background",
            ].join(" ")}
          >
            <div className="text-xs font-semibold uppercase tracking-wide text-primary">
              {dataset.cancer_type}
            </div>
            <div className="mt-1 text-sm font-semibold text-foreground">
              {dataset.name}
            </div>
            <p className="mt-2 min-h-10 text-xs leading-5 text-muted-foreground">
              {dataset.description}
            </p>
            <div className="mt-3 text-[10px] text-muted-foreground">
              {dataset.accession}
            </div>
            <button
              type="button"
              onClick={() => onSelect(dataset)}
              className="mt-3 inline-flex h-9 w-full items-center justify-center rounded-lg border border-border bg-card px-3 text-xs font-medium text-foreground hover:bg-muted disabled:cursor-not-allowed disabled:opacity-60"
            >
              {selectedId === dataset.id ? "Selected" : "Use Dataset"}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

// ============================================================
// UPLOAD CARD
// ============================================================

function UploadCard({
  file,
  selectedPreloaded,
  status,
  error,
  jobId,
  onFileChange,
  onClear,
  onAnalyze,
}: {
  file: File | null;
  selectedPreloaded: PreloadedDataset | null;
  status: AnalysisStatus;
  error: string;
  jobId: string | null;

  onFileChange: (
    event: React.ChangeEvent<HTMLInputElement>,
  ) => void;

  onClear: () => void;

  onAnalyze: () => void;
}) {
  return (
    <div className="rounded-2xl border border-border bg-card shadow-sm">

      <div className="border-b border-border p-8">

        <div className="flex items-start gap-4">

          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary-soft text-primary">
            <Dna className="h-6 w-6" />
          </div>

          <div>

            <h2 className="text-xl font-semibold text-foreground">
              Upload your dataset
            </h2>

            <p className="mt-1 max-w-2xl text-sm leading-6 text-muted-foreground">
              Upload a single-cell gene expression
              matrix. ImmunoXAI will validate the
              dataset and run the complete computational
              analysis pipeline.
            </p>

          </div>

        </div>

      </div>


      <div className="p-8">

        {!file && !selectedPreloaded ? (

          <label className="group flex min-h-[300px] cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed border-border bg-primary-soft/30 px-6 text-center transition hover:border-primary/50 hover:bg-primary-soft/60">

            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-card text-primary shadow-sm transition group-hover:scale-105">
              <UploadCloud className="h-8 w-8" />
            </div>

            <div className="mt-5 text-base font-medium text-foreground">
              Upload expression matrix
            </div>

            <div className="mt-2 text-sm text-muted-foreground">
              CSV, TSV, TXT, or compressed GZ files
            </div>

            <div className="mt-4 rounded-lg border border-border bg-card px-3 py-2 text-xs text-muted-foreground">
              Raw UMI matrices are supported
            </div>

            <input
              type="file"
              accept=".csv,.tsv,.txt,.gz,text/csv,text/tab-separated-values,text/plain,application/gzip"
              className="hidden"
              onChange={
                onFileChange
              }
            />

          </label>

        ) : (

          <div className="rounded-2xl border border-border bg-background p-5">

            <div className="flex items-center gap-4">

              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary-soft text-primary">
                <FileText className="h-6 w-6" />
              </div>

              <div className="min-w-0 flex-1">

                <div className="truncate text-sm font-semibold text-foreground">
                  {file?.name ?? selectedPreloaded?.name}
                </div>

                <div className="mt-1 text-xs text-muted-foreground">
                  {file
                    ? formatFileSize(file.size)
                    : selectedPreloaded?.accession}
                </div>

              </div>


              {status ===
                "ready" && (
                <div className="flex items-center gap-1.5 text-xs font-medium text-[oklch(0.5_0.14_155)]">
                  <CheckCircle2 className="h-4 w-4" />
                  Ready
                </div>
              )}


              {status ===
                "failed" && (
                <div className="flex items-center gap-1.5 text-xs font-medium text-destructive">
                  <AlertCircle className="h-4 w-4" />
                  Failed
                </div>
              )}


              <button
                type="button"
                onClick={onClear}
                className="flex h-9 w-9 items-center justify-center rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground"
                aria-label="Remove dataset"
              >
                <X className="h-4 w-4" />
              </button>

            </div>


            <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-3">

              <InfoItem
                label="Input"
                value={selectedPreloaded ? selectedPreloaded.cancer_type : "Expression matrix"}
              />

              <InfoItem
                label="Processing"
                value="Python backend"
              />

              <InfoItem
                label="Analysis"
                value="16-step pipeline"
              />

            </div>


            {jobId && (
              <div className="mt-3 rounded-lg border border-border bg-muted/30 px-3 py-2">

                <div className="text-[10px] uppercase tracking-wide text-muted-foreground">
                  Job ID
                </div>

                <div className="mt-1 break-all font-mono text-xs text-foreground">
                  {jobId}
                </div>

              </div>
            )}

          </div>

        )}


        {error && (

          <div className="mt-5 flex items-start gap-3 rounded-xl border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">

            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />

            <span>
              {error}
            </span>

          </div>

        )}


        <div className="mt-8 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">

          {(file || selectedPreloaded) && (
            <button
              type="button"
              onClick={onClear}
              className="h-11 rounded-lg border border-border bg-card px-5 text-sm font-medium text-foreground transition hover:bg-muted"
            >
              Change Dataset
            </button>
          )}


          <button
            type="button"
            disabled={
              (!file && !selectedPreloaded) ||
              status ===
                "uploading" ||
              status ===
                "starting"
            }
            onClick={
              onAnalyze
            }
            className="inline-flex h-11 items-center justify-center gap-2 rounded-lg bg-primary px-6 text-sm font-medium text-primary-foreground shadow-sm transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
          >

            {status ===
              "uploading" ||
            status ===
              "starting" ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <FlaskConical className="h-4 w-4" />
            )}

            {status ===
              "uploading"
              ? "Uploading..."
              : status ===
                  "starting"
                ? "Starting..."
                : status ===
                    "failed"
                  ? "Retry Analysis"
                  : "Analyze Dataset"}

          </button>

        </div>

      </div>

    </div>
  );
}


// ============================================================
// ANALYSIS PROGRESS CARD
// ============================================================

function AnalysisProgressCard({
  file,
  datasetName,
  jobId,
  currentStep,
  backendStep,
  progress,
  elapsedSeconds,
  remainingSeconds,
}: {
  file: File | null;
  datasetName: string | null;
  jobId: string | null;
  currentStep: number;
  backendStep: string | null;
  progress: number;
  elapsedSeconds: number;
  remainingSeconds: number | null;
}) {
  const safeStepIndex =
    Math.min(
      Math.max(
        currentStep,
        0,
      ),
      ANALYSIS_STEPS.length - 1,
    );

  const activeStep =
    ANALYSIS_STEPS[
      safeStepIndex
    ];

  const ActiveIcon =
    activeStep.icon;

  return (
    <div className="rounded-2xl border border-border bg-card shadow-sm">

      <div className="border-b border-border p-8">

        <div className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">

          <div className="flex min-w-0 items-start gap-4">

            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground">
              <Loader2 className="h-6 w-6 animate-spin" />
            </div>

            <div className="min-w-0">

              <h2 className="text-xl font-semibold text-foreground">
                Analyzing dataset
              </h2>

              <p className="mt-1 truncate text-sm text-muted-foreground">
                {file?.name ?? datasetName ?? "Preloaded dataset"}
              </p>

              {jobId && (
                <p className="mt-1 truncate font-mono text-[10px] text-muted-foreground">
                  Job: {jobId}
                </p>
              )}

            </div>

          </div>


          <div className="flex shrink-0 items-center gap-2 rounded-lg border border-border bg-background px-3 py-2 text-xs text-muted-foreground">

            <Clock3 className="h-4 w-4" />

            <span>
              {remainingSeconds ===
              null
                ? "Estimating..."
                : `~${formatTime(
                    remainingSeconds,
                  )} remaining`}
            </span>

          </div>

        </div>


        <div className="mt-8">

          <div className="mb-2 flex items-center justify-between text-xs">

            <span className="font-medium text-foreground">
              Overall progress
            </span>

            <span className="font-medium text-primary">
              {progress}%
            </span>

          </div>


          <div className="h-2 overflow-hidden rounded-full bg-muted">

            <div
              className="h-full rounded-full bg-primary transition-all duration-500"
              style={{
                width: `${progress}%`,
              }}
            />

          </div>

        </div>


        <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-3">

          <StatBox
            label="Elapsed"
            value={formatTime(
              elapsedSeconds,
            )}
          />

          <StatBox
            label="Current stage"
            value={`${safeStepIndex + 1}/${ANALYSIS_STEPS.length}`}
          />

          <StatBox
            label="Pipeline"
            value="Python backend"
          />

        </div>

      </div>


      <div className="p-8">

        <div className="rounded-xl border border-primary/20 bg-primary-soft/30 p-5">

          <div className="flex items-start gap-4">

            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <ActiveIcon className="h-5 w-5" />
            </div>

            <div className="min-w-0">

              <div className="text-xs font-semibold uppercase tracking-wider text-primary">
                Current step
              </div>

              <h3 className="mt-1 text-base font-semibold text-foreground">
                {activeStep.label}
              </h3>

              <p className="mt-1 text-sm text-muted-foreground">
                {activeStep.description}
              </p>

              {backendStep && (
                <p className="mt-2 font-mono text-[10px] text-muted-foreground">
                  Backend: {backendStep}
                </p>
              )}

            </div>

          </div>

        </div>


        <div className="mt-7">

          <div className="mb-4 text-sm font-semibold text-foreground">
            Analysis pipeline
          </div>


          <div className="space-y-1">

            {ANALYSIS_STEPS.map(
              (
                step,
                index,
              ) => {

                const Icon =
                  step.icon;

                const completed =
                  index <
                  safeStepIndex;

                const active =
                  index ===
                  safeStepIndex;

                return (
                  <div
                    key={
                      step.id
                    }
                    className={[
                      "flex items-center gap-3 rounded-lg px-3 py-3 transition",
                      active
                        ? "bg-primary-soft"
                        : "bg-transparent",
                    ].join(
                      " ",
                    )}
                  >

                    <div
                      className={[
                        "flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
                        completed
                          ? "bg-[oklch(0.65_0.16_155)] text-white"
                          : active
                            ? "bg-primary text-primary-foreground"
                            : "bg-muted text-muted-foreground",
                      ].join(
                        " ",
                      )}
                    >

                      {completed ? (
                        <CheckCircle2 className="h-4 w-4" />
                      ) : active ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Icon className="h-4 w-4" />
                      )}

                    </div>


                    <div className="min-w-0 flex-1">

                      <div
                        className={[
                          "text-sm font-medium",
                          completed ||
                          active
                            ? "text-foreground"
                            : "text-muted-foreground",
                        ].join(
                          " ",
                        )}
                      >
                        {step.label}
                      </div>


                      {active && (
                        <div className="mt-0.5 text-xs text-muted-foreground">
                          {
                            step.description
                          }
                        </div>
                      )}

                    </div>


                    <div className="text-xs text-muted-foreground">

                      {completed
                        ? "Complete"
                        : active
                          ? "Running"
                          : "Waiting"}

                    </div>

                  </div>
                );
              },
            )}

          </div>

        </div>


        <div className="mt-7 rounded-xl border border-border bg-muted/30 p-4">

          <div className="flex items-start gap-3">

            <Clock3 className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />

            <div>

              <div className="text-xs font-medium text-foreground">
                Live backend analysis
              </div>

              <p className="mt-1 text-xs leading-5 text-muted-foreground">
                Progress is being reported by the
                Python/FastAPI analysis pipeline.
                The interface is not simulating the
                analysis stages.
              </p>

            </div>

          </div>

        </div>

      </div>

    </div>
  );
}


// ============================================================
// INFO ITEM
// ============================================================

function InfoItem({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-lg border border-border bg-card px-3 py-2.5">

      <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
        {label}
      </div>

      <div className="mt-0.5 text-xs font-medium text-foreground">
        {value}
      </div>

    </div>
  );
}


// ============================================================
// STAT BOX
// ============================================================

function StatBox({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-lg border border-border bg-background p-3">

      <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
        {label}
      </div>

      <div className="mt-1 text-sm font-semibold text-foreground">
        {value}
      </div>

    </div>
  );
}


// ============================================================
// FILE SIZE
// ============================================================

function formatFileSize(
  bytes: number,
) {
  if (bytes < 1024) {
    return `${bytes} B`;
  }

  if (
    bytes <
    1024 * 1024
  ) {
    return `${(
      bytes / 1024
    ).toFixed(1)} KB`;
  }

  if (
    bytes <
    1024 *
      1024 *
      1024
  ) {
    return `${(
      bytes /
      (1024 * 1024)
    ).toFixed(2)} MB`;
  }

  return `${(
    bytes /
    (1024 *
      1024 *
      1024)
  ).toFixed(2)} GB`;
}


// ============================================================
// BACKEND ERROR EXTRACTION
// ============================================================

function extractBackendError(
  error: unknown,
): string | null {
  if (!error) {
    return null;
  }

  if (
    typeof error ===
    "string"
  ) {
    return error;
  }

  if (
    typeof error ===
      "object" &&
    error !== null
  ) {
    const record =
      error as Record<
        string,
        unknown
      >;

    if (
      typeof record.message ===
      "string"
    ) {
      return record.message;
    }

    if (
      typeof record.detail ===
      "string"
    ) {
      return record.detail;
    }
  }

  return null;
}


// ============================================================
// WAIT
// ============================================================

function wait(
  ms: number,
) {
  return new Promise<void>(
    (resolve) => {
      window.setTimeout(
        resolve,
        ms,
      );
    },
  );
}