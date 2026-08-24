import { createFileRoute, useNavigate } from "@tanstack/react-router";
import {
  UploadCloud,
  FileSpreadsheet,
  CheckCircle2,
  ChevronDown,
  AlertCircle,
  Loader2,
  FileText,
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
          "Upload and validate gene expression datasets for immune phenotype analysis.",
      },
    ],
  }),
  component: UploadPage,
});

type FileFormat =
  | "csv"
  | "tsv"
  | "txt"
  | "csv.gz"
  | "tsv.gz"
  | "txt.gz";

type DatasetType = "expression" | "single-cell-umi";

function getFileFormat(fileName: string): FileFormat | null {
  const name = fileName.toLowerCase();

  if (name.endsWith(".csv.gz")) return "csv.gz";
  if (name.endsWith(".tsv.gz")) return "tsv.gz";
  if (name.endsWith(".txt.gz")) return "txt.gz";

  if (name.endsWith(".csv")) return "csv";
  if (name.endsWith(".tsv")) return "tsv";
  if (name.endsWith(".txt")) return "txt";

  return null;
}

function isGzipFormat(format: FileFormat) {
  return format.endsWith(".gz");
}

function getBaseFormat(format: FileFormat) {
  return format.replace(".gz", "") as "csv" | "tsv" | "txt";
}

function formatFileSize(bytes: number) {
  if (bytes < 1024) {
    return `${bytes} B`;
  }

  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }

  if (bytes < 1024 * 1024 * 1024) {
    return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
  }

  return `${(bytes / 1024 / 1024 / 1024).toFixed(2)} GB`;
}

async function validateGzip(file: File) {
  const header = new Uint8Array(await file.slice(0, 2).arrayBuffer());

  // gzip magic bytes: 1F 8B
  if (header.length < 2 || header[0] !== 0x1f || header[1] !== 0x8b) {
    throw new Error(
      "The file has a .gz extension but does not contain a valid gzip header.",
    );
  }
}

async function validateTextFile(file: File) {
  const sampleSize = Math.min(file.size, 1024 * 1024);

  const sample = await file.slice(0, sampleSize).text();

  if (!sample.trim()) {
    throw new Error("The uploaded file appears to be empty.");
  }

  const lines = sample
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);

  if (lines.length < 2) {
    throw new Error(
      "The file does not appear to contain a matrix with multiple rows.",
    );
  }

  return {
    linesChecked: lines.length,
    sampleSize,
  };
}

async function validateGzipTextFile(file: File) {
  if (typeof DecompressionStream === "undefined") {
    throw new Error(
      "This browser does not support gzip decompression. Please use a modern version of Chrome, Edge, Firefox, or Safari.",
    );
  }

  const stream = file
    .stream()
    .pipeThrough(new DecompressionStream("gzip"));

  const reader = stream.getReader();

  let received = 0;
  const chunks: Uint8Array[] = [];

  const MAX_SAMPLE_BYTES = 1024 * 1024;

  while (received < MAX_SAMPLE_BYTES) {
    const { done, value } = await reader.read();

    if (done) {
      break;
    }

    if (!value) {
      continue;
    }

    const remaining = MAX_SAMPLE_BYTES - received;
    const chunk = value.slice(0, remaining);

    chunks.push(chunk);
    received += chunk.length;

    if (received >= MAX_SAMPLE_BYTES) {
      try {
        await reader.cancel();
      } catch {
        // Ignore cancellation errors.
      }

      break;
    }
  }

  const combined = new Uint8Array(received);

  let offset = 0;

  for (const chunk of chunks) {
    combined.set(chunk, offset);
    offset += chunk.length;
  }

  const text = new TextDecoder().decode(combined);

  if (!text.trim()) {
    throw new Error("The compressed dataset appears to be empty.");
  }

  const lines = text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);

  if (lines.length < 2) {
    throw new Error(
      "The compressed file does not appear to contain a valid expression matrix.",
    );
  }

  return {
    linesChecked: lines.length,
    decompressedSampleBytes: received,
  };
}

function detectDatasetType(fileName: string): DatasetType {
  const name = fileName.toLowerCase();

  if (
    name.includes("raw_umi") ||
    name.includes("raw-count") ||
    name.includes("raw_count") ||
    name.includes("single-cell") ||
    name.includes("single_cell") ||
    name.includes("scrna") ||
    name.includes("sc_rna")
  ) {
    return "single-cell-umi";
  }

  return "expression";
}

function UploadPage() {
  const navigate = useNavigate();

  const [datasetName, setDatasetName] = useState(
    "My Gene Expression Dataset",
  );

  const [cancerType, setCancerType] = useState("BRCA");

  const [model, setModel] = useState("Random Forest");

  const [file, setFile] = useState<File | null>(null);

  const [fileFormat, setFileFormat] = useState<FileFormat | null>(
    null,
  );

  const [datasetType, setDatasetType] =
    useState<DatasetType>("expression");

  const [status, setStatus] = useState<
    "idle" | "validating" | "success" | "error"
  >("idle");

  const [error, setError] = useState("");

  const [validationMessage, setValidationMessage] = useState("");

  const [analysisMessage, setAnalysisMessage] = useState("");

  async function handleFileChange(
    event: React.ChangeEvent<HTMLInputElement>,
  ) {
    const selectedFile = event.target.files?.[0];

    if (!selectedFile) {
      return;
    }

    setError("");
    setValidationMessage("");
    setAnalysisMessage("");
    setStatus("validating");

    const format = getFileFormat(selectedFile.name);

    if (!format) {
      setFile(null);
      setFileFormat(null);
      setStatus("error");

      setError(
        "Unsupported file format. Please upload CSV, TSV, TXT, or a gzip-compressed CSV/TSV/TXT file.",
      );

      return;
    }

    setFile(selectedFile);
    setFileFormat(format);

    const detectedType = detectDatasetType(selectedFile.name);
    setDatasetType(detectedType);

    try {
      if (isGzipFormat(format)) {
        await validateGzip(selectedFile);

        const result = await validateGzipTextFile(selectedFile);

        setValidationMessage(
          `Gzip archive is valid. Checked ${formatFileSize(
            result.decompressedSampleBytes,
          )} of decompressed data.`,
        );
      } else {
        const result = await validateTextFile(selectedFile);

        setValidationMessage(
          `Text matrix detected. Checked approximately ${formatFileSize(
            result.sampleSize,
          )} of the file.`,
        );
      }

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
    if (!file || !fileFormat) {
      setError("Please select a dataset first.");
      return;
    }

    setError("");
    setAnalysisMessage("");
    setStatus("validating");

    /*
     * The current analysis engine is CSV-based.
     *
     * We therefore only send uncompressed CSV files to analyzeCSV()
     * for now. Single-cell UMI matrices such as GSE131907 will be
     * handled by the dedicated single-cell processing pipeline.
     */
    if (
      datasetType === "single-cell-umi" ||
      isGzipFormat(fileFormat) ||
      getBaseFormat(fileFormat) !== "csv"
    ) {
      setStatus("success");

      setAnalysisMessage(
        "Dataset validated successfully. This single-cell/raw UMI dataset will be processed by the single-cell analysis pipeline.",
      );

      /*
       * We intentionally do not call analyzeCSV() here.
       *
       * The next implementation step will connect this dataset
       * to the single-cell processing pipeline.
       */
      return;
    }

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

  function clearFile() {
    setFile(null);
    setFileFormat(null);
    setStatus("idle");
    setError("");
    setValidationMessage("");
    setAnalysisMessage("");
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
            Upload a gene-expression or single-cell expression
            matrix and provide the dataset metadata.
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
                Analysis Model
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
              Expression Matrix
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
                Drag & drop dataset, or{" "}
                <span className="text-primary">
                  browse
                </span>
              </div>

              <div className="mt-1 text-xs text-muted-foreground">
                CSV · TSV · TXT · CSV.GZ · TSV.GZ · TXT.GZ
              </div>

              <div className="mt-1 text-xs text-muted-foreground">
                Genes × cells/samples expression matrix
              </div>

              <input
                type="file"
                accept=".csv,.tsv,.txt,.csv.gz,.tsv.gz,.txt.gz"
                className="hidden"
                onChange={handleFileChange}
              />
            </label>

            {file && fileFormat && (
              <div className="mt-4 rounded-lg border border-border bg-background p-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-md bg-primary-soft text-primary">
                    {isGzipFormat(fileFormat) ? (
                      <FileText className="h-5 w-5" />
                    ) : (
                      <FileSpreadsheet className="h-5 w-5" />
                    )}
                  </div>

                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium text-foreground">
                      {file.name}
                    </div>

                    <div className="mt-0.5 text-xs text-muted-foreground">
                      {formatFileSize(file.size)} ·{" "}
                      {fileFormat.toUpperCase()}
                    </div>
                  </div>

                  {status === "success" && (
                    <span className="inline-flex items-center gap-1 text-xs font-medium text-[oklch(0.5_0.14_155)]">
                      <CheckCircle2 className="h-4 w-4" />
                      Validated
                    </span>
                  )}
                </div>

                <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
                  <div className="rounded-md bg-muted/40 p-2.5">
                    <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
                      Format
                    </div>

                    <div className="mt-0.5 text-sm font-medium text-foreground">
                      {fileFormat.toUpperCase()}
                    </div>
                  </div>

                  <div className="rounded-md bg-muted/40 p-2.5">
                    <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
                      Dataset type
                    </div>

                    <div className="mt-0.5 text-sm font-medium text-foreground">
                      {datasetType === "single-cell-umi"
                        ? "Single-cell raw UMI"
                        : "Expression matrix"}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {validationMessage && status === "success" && (
              <div className="mt-3 flex items-start gap-2 rounded-lg border border-green-500/20 bg-green-500/5 p-3 text-sm text-muted-foreground">
                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-[oklch(0.5_0.14_155)]" />
                <span>{validationMessage}</span>
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
              onClick={clearFile}
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
                ? "Validating..."
                : "Continue"}
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
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>

      <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
    </div>
  );
}