import { createFileRoute, useNavigate } from "@tanstack/react-router";
import {
  UploadCloud,
  FileSpreadsheet,
  CheckCircle2,
  ChevronDown,
  AlertCircle,
  Loader2,
} from "lucide-react";
import { useState } from "react";

import { AppLayout } from "@/components/AppLayout";
import { analyzeCSV } from "@/lib/analysis";

export const Route = createFileRoute("/upload")({
  head: () => ({
    meta: [
      { title: "Upload Dataset — ImmunoXAI" },
      {
        name: "description",
        content:
          "Upload a gene expression CSV, validate it, and run immune phenotype analysis.",
      },
    ],
  }),
  component: UploadPage,
});

function UploadPage() {
  const navigate = useNavigate();

  const [datasetName, setDatasetName] = useState(
    "My Gene Expression Dataset",
  );

  const [cancerType, setCancerType] = useState("BRCA");

  const [model, setModel] = useState("Random Forest");

  const [file, setFile] = useState<File | null>(null);

  const [status, setStatus] = useState<
    "idle" | "validating" | "success" | "error"
  >("idle");

  const [error, setError] = useState("");

  const [analysisMessage, setAnalysisMessage] = useState("");

  async function handleFileChange(
    event: React.ChangeEvent<HTMLInputElement>,
  ) {
    const selectedFile = event.target.files?.[0];

    if (!selectedFile) {
      return;
    }

    setError("");
    setStatus("validating");
    setFile(selectedFile);

    if (!selectedFile.name.toLowerCase().endsWith(".csv")) {
      setStatus("error");
      setError("Please upload a CSV file.");
      return;
    }

    try {
      const text = await selectedFile.text();

      // Test the dataset structure immediately.
      analyzeCSV(
        text,
        datasetName,
        cancerType,
        model,
      );

      setStatus("success");
    } catch (err) {
      setStatus("error");

      setError(
        err instanceof Error
          ? err.message
          : "The dataset could not be validated.",
      );
    }
  }

  async function handleAnalyze() {
    if (!file) {
      setError("Please select a CSV dataset first.");
      return;
    }

    setError("");
    setStatus("validating");
    setAnalysisMessage("Processing dataset...");

    try {
      const text = await file.text();

      const result = analyzeCSV(
        text,
        datasetName,
        cancerType,
        model,
      );

      sessionStorage.setItem(
        "immunoxai-analysis",
        JSON.stringify(result),
      );

      setStatus("success");
      setAnalysisMessage(
        `${result.totalSamples} samples and ${result.totalGenes} genes analyzed.`,
      );

      navigate({ to: "/results" });
    } catch (err) {
      setStatus("error");

      setError(
        err instanceof Error
          ? err.message
          : "Analysis failed.",
      );

      setAnalysisMessage("");
    }
  }

  return (
    <AppLayout
      title="Upload Dataset"
      subtitle="Prepare a cohort for immune phenotype analysis"
    >
      <div className="mx-auto max-w-4xl">
        <div className="rounded-xl border border-border bg-card p-8 shadow-sm">
          <h2 className="text-lg font-semibold text-foreground">
            Dataset details
          </h2>

          <p className="mt-1 text-sm text-muted-foreground">
            Upload a gene-expression CSV and provide the dataset metadata.
          </p>

          <div className="mt-6 grid grid-cols-1 gap-5 md:grid-cols-2">
            <div>
              <label className="text-xs font-medium text-foreground">
                Dataset Name
              </label>

              <input
                value={datasetName}
                onChange={(event) =>
                  setDatasetName(event.target.value)
                }
                className="mt-1.5 h-11 w-full rounded-lg border border-input bg-background px-3 text-sm outline-none focus:border-ring focus:ring-2 focus:ring-ring/20"
              />
            </div>

            <div>
              <label className="text-xs font-medium text-foreground">
                Cancer Type
              </label>

              <SelectField
                options={[
                  "BRCA",
                  "LUAD",
                  "COAD",
                  "SKCM",
                  "GBM",
                ]}
                value={cancerType}
                onChange={setCancerType}
              />
            </div>

            <div className="md:col-span-2">
              <label className="text-xs font-medium text-foreground">
                Model
              </label>

              <SelectField
                options={[
                  "Random Forest",
                  "XGBoost",
                  "Logistic Regression",
                ]}
                value={model}
                onChange={setModel}
              />
            </div>
          </div>

          <div className="mt-8">
            <label className="text-xs font-medium text-foreground">
              Expression Matrix (CSV)
            </label>

            <label className="mt-1.5 flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-border bg-primary-soft/40 px-6 py-12 text-center transition-colors hover:bg-primary-soft/70">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-card text-primary shadow-sm">
                {status === "validating" ? (
                  <Loader2 className="h-6 w-6 animate-spin" />
                ) : (
                  <UploadCloud className="h-6 w-6" />
                )}
              </div>

              <div className="mt-4 text-sm font-medium text-foreground">
                Drag & drop CSV, or{" "}
                <span className="text-primary">
                  browse
                </span>
              </div>

              <div className="mt-1 text-xs text-muted-foreground">
                Genes × samples matrix · CSV format
              </div>

              <input
                type="file"
                accept=".csv,text/csv"
                className="hidden"
                onChange={handleFileChange}
              />
            </label>

            {file && (
              <div className="mt-4 flex items-center gap-3 rounded-lg border border-border bg-background p-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-md bg-primary-soft text-primary">
                  <FileSpreadsheet className="h-5 w-5" />
                </div>

                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm font-medium text-foreground">
                    {file.name}
                  </div>

                  <div className="text-xs text-muted-foreground">
                    {(file.size / 1024 / 1024).toFixed(2)} MB
                  </div>
                </div>

                {status === "success" && (
                  <span className="inline-flex items-center gap-1 text-xs font-medium text-[oklch(0.5_0.14_155)]">
                    <CheckCircle2 className="h-4 w-4" />
                    Validated
                  </span>
                )}
              </div>
            )}

            {status === "error" && error && (
              <div className="mt-4 flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {analysisMessage && (
              <div className="mt-4 rounded-lg border border-border bg-muted/40 p-3 text-sm text-muted-foreground">
                {analysisMessage}
              </div>
            )}
          </div>

          <div className="mt-8 flex items-center justify-end gap-3 border-t border-border pt-6">
            <button
              type="button"
              onClick={() => {
                setFile(null);
                setStatus("idle");
                setError("");
              }}
              className="h-10 rounded-lg border border-border bg-card px-4 text-sm font-medium text-foreground hover:bg-muted"
            >
              Clear
            </button>

            <button
              type="button"
              disabled={!file || status === "validating"}
              onClick={handleAnalyze}
              className="inline-flex h-10 items-center rounded-lg bg-primary px-5 text-sm font-medium text-primary-foreground shadow-sm hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {status === "validating"
                ? "Analyzing..."
                : "Analyze Dataset"}
            </button>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}

function SelectField({
  options,
  value,
  onChange,
}: {
  options: string[];
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div className="relative mt-1.5">
      <select
        value={value}
        onChange={(event) =>
          onChange(event.target.value)
        }
        className="h-11 w-full appearance-none rounded-lg border border-input bg-background px-3 pr-9 text-sm outline-none focus:border-ring focus:ring-2 focus:ring-ring/20"
      >
        {options.map((option) => (
          <option key={option}>
            {option}
          </option>
        ))}
      </select>

      <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
    </div>
  );
}