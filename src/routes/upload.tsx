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
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { AppLayout } from "@/components/AppLayout";

export const Route = createFileRoute("/upload")({
  head: () => ({
    meta: [
      { title: "Analyze Dataset — ImmunoXAI" },
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
// ANALYSIS PIPELINE STEPS
// ============================================================

type AnalysisStep = {
  id: string;
  label: string;
  description: string;
  icon: typeof Database;
};

const ANALYSIS_STEPS: AnalysisStep[] = [
  {
    id: "validation",
    label: "Dataset validation",
    description:
      "Checking file format, dimensions, genes, and samples.",
    icon: Database,
  },
  {
    id: "loading",
    label: "Loading expression matrix",
    description:
      "Reading the expression data into the analysis pipeline.",
    icon: FileText,
  },
  {
    id: "qc",
    label: "Quality control",
    description:
      "Evaluating sequencing quality and filtering low-quality cells.",
    icon: FlaskConical,
  },
  {
    id: "normalization",
    label: "Normalization",
    description:
      "Normalizing counts and applying log transformation.",
    icon: BarChart3,
  },
  {
    id: "features",
    label: "Feature selection",
    description:
      "Identifying informative genes for downstream analysis.",
    icon: Dna,
  },
  {
    id: "embedding",
    label: "Dimensionality reduction",
    description:
      "Computing PCA and low-dimensional representations.",
    icon: BarChart3,
  },
  {
    id: "clustering",
    label: "Cell-state analysis",
    description:
      "Identifying transcriptionally distinct cellular populations.",
    icon: Dna,
  },
  {
    id: "immune",
    label: "Immune-state scoring",
    description:
      "Calculating T-cell, PD-L1/myeloid, and immune-state scores.",
    icon: FlaskConical,
  },
  {
    id: "de",
    label: "Differential expression",
    description:
      "Identifying genes associated with immune states.",
    icon: BarChart3,
  },
  {
    id: "enrichment",
    label: "Functional enrichment",
    description:
      "Characterizing biological pathways and processes.",
    icon: FlaskConical,
  },
  {
    id: "ml",
    label: "Machine learning",
    description:
      "Training and evaluating the immune-state classifier.",
    icon: BrainCircuit,
  },
  {
    id: "xai",
    label: "Explainable AI",
    description:
      "Generating model feature importance and explanations.",
    icon: BrainCircuit,
  },
  {
    id: "report",
    label: "Report generation",
    description:
      "Assembling the complete analysis summary.",
    icon: FileText,
  },
];


// ============================================================
// TYPES
// ============================================================

type AnalysisStatus =
  | "idle"
  | "ready"
  | "running"
  | "error";


// ============================================================
// SHARED TIME FORMATTER
// IMPORTANT:
// This must be OUTSIDE UploadPage so AnalysisProgressCard
// can also use it.
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

  const [currentStep, setCurrentStep] =
    useState(0);

  const [progress, setProgress] =
    useState(0);

  const [elapsedSeconds, setElapsedSeconds] =
    useState(0);

  const [estimatedTotalSeconds, setEstimatedTotalSeconds] =
    useState<number | null>(null);


  // ==========================================================
  // RUNNING STATE
  // ==========================================================

  const isRunning =
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
        setElapsedSeconds(
          (seconds) => seconds + 1,
        );
      }, 1000);

    return () =>
      window.clearInterval(interval);
  }, [isRunning]);


  // ==========================================================
  // REMAINING TIME ESTIMATE
  // ==========================================================

  const remainingSeconds =
    useMemo(() => {
      if (
        !estimatedTotalSeconds ||
        progress <= 0
      ) {
        return null;
      }

      const estimatedElapsed =
        estimatedTotalSeconds *
        (progress / 100);

      return Math.max(
        0,
        Math.round(
          estimatedTotalSeconds -
            estimatedElapsed,
        ),
      );
    }, [
      estimatedTotalSeconds,
      progress,
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
    setStatus("ready");
    setCurrentStep(0);
    setProgress(0);
    setElapsedSeconds(0);
    setEstimatedTotalSeconds(null);
  }


  // ==========================================================
  // CLEAR DATASET
  // ==========================================================

  function clearFile() {
    if (isRunning) {
      return;
    }

    setFile(null);
    setStatus("idle");
    setError("");
    setCurrentStep(0);
    setProgress(0);
    setElapsedSeconds(0);
    setEstimatedTotalSeconds(null);
  }


  // ==========================================================
  // ANALYZE DATASET
  // ==========================================================
  //
  // CURRENTLY THIS IS STILL THE FRONTEND SIMULATION.
  //
  // We will replace this with:
  //
  // POST /api/analysis/run
  //
  // followed by polling of the real analysis job.
  //
  // ==========================================================

  async function handleAnalyze() {
    if (!file) {
      setError(
        "Please upload a dataset first.",
      );

      return;
    }

    setError("");
    setStatus("running");
    setCurrentStep(0);
    setProgress(2);
    setElapsedSeconds(0);


    // ----------------------------------------------------------
    // Temporary estimate
    // ----------------------------------------------------------

    const estimatedSeconds =
      estimateAnalysisTime(file);

    setEstimatedTotalSeconds(
      estimatedSeconds,
    );


    // ----------------------------------------------------------
    // Temporary frontend pipeline
    // ----------------------------------------------------------

    for (
      let i = 0;
      i < ANALYSIS_STEPS.length;
      i++
    ) {
      setCurrentStep(i);

      const stepProgress =
        Math.round(
          (i /
            ANALYSIS_STEPS.length) *
            92,
        ) + 4;

      setProgress(
        Math.min(
          stepProgress,
          96,
        ),
      );

      await wait(
        getStepDelay(i),
      );
    }


    // ----------------------------------------------------------
    // Complete
    // ----------------------------------------------------------

    setProgress(100);

    setCurrentStep(
      ANALYSIS_STEPS.length - 1,
    );

    await wait(700);


    // ----------------------------------------------------------
    // TEMPORARY
    // ----------------------------------------------------------

    setStatus("ready");

    setError(
      "Analysis interface is ready. The next step is connecting this progress screen to the Python/FastAPI analysis pipeline.",
    );
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
          <UploadCard
            file={file}
            status={status}
            error={error}
            onFileChange={
              handleFileChange
            }
            onClear={clearFile}
            onAnalyze={
              handleAnalyze
            }
          />
        ) : (
          <AnalysisProgressCard
            file={file}
            currentStep={
              currentStep
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


// ============================================================
// UPLOAD CARD
// ============================================================

function UploadCard({
  file,
  status,
  error,
  onFileChange,
  onClear,
  onAnalyze,
}: {
  file: File | null;
  status: AnalysisStatus;
  error: string;

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
              Upload a single-cell gene expression matrix.
              ImmunoXAI will automatically validate the
              dataset and run the appropriate analysis workflow.
            </p>
          </div>

        </div>
      </div>


      <div className="p-8">

        {!file ? (

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
              onChange={onFileChange}
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
                  {file.name}
                </div>

                <div className="mt-1 text-xs text-muted-foreground">
                  {formatFileSize(
                    file.size,
                  )}
                </div>

              </div>

              {status === "ready" && (
                <div className="flex items-center gap-1.5 text-xs font-medium text-[oklch(0.5_0.14_155)]">
                  <CheckCircle2 className="h-4 w-4" />
                  Ready
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
                value="Expression matrix"
              />

              <InfoItem
                label="Processing"
                value="Automatic"
              />

              <InfoItem
                label="Analysis"
                value="Full pipeline"
              />

            </div>

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

          {file && (
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
            disabled={!file}
            onClick={onAnalyze}
            className="inline-flex h-11 items-center justify-center gap-2 rounded-lg bg-primary px-6 text-sm font-medium text-primary-foreground shadow-sm transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <FlaskConical className="h-4 w-4" />
            Analyze Dataset
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
  currentStep,
  progress,
  elapsedSeconds,
  remainingSeconds,
}: {
  file: File | null;
  currentStep: number;
  progress: number;
  elapsedSeconds: number;
  remainingSeconds: number | null;
}) {
  const activeStep =
    ANALYSIS_STEPS[
      Math.min(
        currentStep,
        ANALYSIS_STEPS.length - 1,
      )
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
                {file?.name}
              </p>

            </div>

          </div>


          <div className="flex shrink-0 items-center gap-2 rounded-lg border border-border bg-background px-3 py-2 text-xs text-muted-foreground">

            <Clock3 className="h-4 w-4" />

            <span>
              {remainingSeconds === null
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
              className="h-full rounded-full bg-primary transition-all duration-700"
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
            value={`${currentStep + 1}/${ANALYSIS_STEPS.length}`}
          />

          <StatBox
            label="Pipeline"
            value="Automated"
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

            </div>

          </div>

        </div>


        <div className="mt-7">

          <div className="mb-4 text-sm font-semibold text-foreground">
            Analysis pipeline
          </div>


          <div className="space-y-1">

            {ANALYSIS_STEPS.map(
              (step, index) => {
                const Icon =
                  step.icon;

                const completed =
                  index <
                  currentStep;

                const active =
                  index ===
                  currentStep;

                return (
                  <div
                    key={step.id}
                    className={[
                      "flex items-center gap-3 rounded-lg px-3 py-3 transition",
                      active
                        ? "bg-primary-soft"
                        : "bg-transparent",
                    ].join(" ")}
                  >

                    <div
                      className={[
                        "flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
                        completed
                          ? "bg-[oklch(0.65_0.16_155)] text-white"
                          : active
                            ? "bg-primary text-primary-foreground"
                            : "bg-muted text-muted-foreground",
                      ].join(" ")}
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
                        ].join(" ")}
                      >
                        {step.label}
                      </div>


                      {active && (
                        <div className="mt-0.5 text-xs text-muted-foreground">
                          {step.description}
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
                Analysis time
              </div>

              <p className="mt-1 text-xs leading-5 text-muted-foreground">
                The remaining-time estimate will become
                dynamic once the Python analysis service
                is connected. It will use actual processing
                progress rather than a fixed countdown.
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
    1024 * 1024 * 1024
  ) {
    return `${(
      bytes /
      (1024 * 1024)
    ).toFixed(2)} MB`;
  }

  return `${(
    bytes /
    (1024 * 1024 * 1024)
  ).toFixed(2)} GB`;
}


// ============================================================
// TEMPORARY ANALYSIS TIME ESTIMATE
// ============================================================

function estimateAnalysisTime(
  file: File,
) {
  const sizeMB =
    file.size /
    (1024 * 1024);

  if (sizeMB < 20) {
    return 90;
  }

  if (sizeMB < 100) {
    return 150;
  }

  if (sizeMB < 500) {
    return 300;
  }

  if (sizeMB < 1000) {
    return 480;
  }

  return 720;
}


// ============================================================
// TEMPORARY STEP DELAYS
// ============================================================

function getStepDelay(
  index: number,
) {
  const delays = [
    700,
    900,
    1300,
    1100,
    1000,
    1000,
    1200,
    1400,
    1100,
    1100,
    1300,
    1000,
    900,
  ];

  return (
    delays[index] ?? 1000
  );
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