import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowLeft, Download, FileText, Info, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";
import { AppLayout } from "@/components/AppLayout";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  "http://127.0.0.1:8000";

type AnalysisSummary = {
  job_id: string;
  status: string;
  final_analysis?: {
    pipeline?: string;
    input_cells?: number;
  };
};

export const Route = createFileRoute("/reports")({
  head: () => ({
    meta: [
      { title: "PDF Report — ImmunoXAI" },
      {
        name: "description",
        content: "Download the PDF report generated from a completed IMMUNO-XAI analysis.",
      },
    ],
  }),
  component: Reports,
});

function Reports() {
  const [analysis, setAnalysis] =
    useState<AnalysisSummary | null>(null);
  const [loading, setLoading] =
    useState(true);
  const [downloading, setDownloading] =
    useState(false);
  const [error, setError] =
    useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadAnalysis() {
      try {
        setLoading(true);
        setError(null);

        const jobId =
          sessionStorage.getItem(
            "immunoxai-job-id",
          );

        if (!jobId) {
          throw new Error(
            "No analysis job was found. Please complete an analysis first.",
          );
        }

        const response = await fetch(
          `${API_BASE_URL}/api/analysis/${encodeURIComponent(jobId)}/result`,
          {
            headers: {
              Accept: "application/json",
            },
          },
        );

        const data =
          await response.json().catch(() => null);

        if (!response.ok) {
          throw new Error(
            typeof data?.detail === "string"
              ? data.detail
              : "Unable to load the completed analysis.",
          );
        }

        if (!cancelled) {
          setAnalysis(
            data as AnalysisSummary,
          );
        }
      } catch (err) {
        console.error(
          "Failed to load report information:",
          err,
        );

        if (!cancelled) {
          setError(
            err instanceof Error
              ? err.message
              : "Unable to load report information.",
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadAnalysis();

    return () => {
      cancelled = true;
    };
  }, []);

  async function downloadPdf() {
    if (!analysis?.job_id) return;

    try {
      setDownloading(true);
      setError(null);

      const response = await fetch(
        `${API_BASE_URL}/api/analysis/${encodeURIComponent(
          analysis.job_id,
        )}/report`,
        {
          method: "GET",
          headers: {
            Accept: "application/pdf",
          },
        },
      );

      if (!response.ok) {
        const data =
          await response.json().catch(() => null);

        throw new Error(
          typeof data?.detail === "string"
            ? data.detail
            : "Failed to generate the PDF report.",
        );
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");

      anchor.href = url;
      anchor.download =
        `IMMUNO_XAI_Report_${analysis.job_id}.pdf`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error(
        "Failed to download PDF report:",
        err,
      );

      setError(
        err instanceof Error
          ? err.message
          : "Unable to download the PDF report.",
      );
    } finally {
      setDownloading(false);
    }
  }

  if (loading) {
    return (
      <AppLayout
        title="PDF Report"
        subtitle="Preparing report information..."
      >
        <div className="rounded-xl border border-border bg-card p-8 text-sm text-muted-foreground">
          Loading completed analysis...
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout
      title="PDF Report"
      subtitle="Download the completed IMMUNO-XAI analysis as a PDF"
    >
      <div className="mx-auto max-w-3xl">
        <div className="rounded-xl border border-border bg-card p-8 shadow-sm">
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary-soft text-primary">
              <FileText className="h-6 w-6" />
            </div>

            <div className="min-w-0">
              <h2 className="text-lg font-semibold text-foreground">
                IMMUNO-XAI Analysis Report
              </h2>

              <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
                Generate a PDF containing the completed analysis summary,
                immune-state results, immune scores, clusters, pathways,
                machine-learning results, XAI feature importance, and
                biological interpretation.
              </p>
            </div>
          </div>

          {analysis && (
            <div className="mt-7 grid grid-cols-1 gap-3 sm:grid-cols-3">
              <div className="rounded-lg border border-border bg-background p-4">
                <div className="text-xs text-muted-foreground">
                  Status
                </div>
                <div className="mt-1 text-sm font-semibold text-green-600">
                  {analysis.status}
                </div>
              </div>

              <div className="rounded-lg border border-border bg-background p-4">
                <div className="text-xs text-muted-foreground">
                  Input cells
                </div>
                <div className="mt-1 text-sm font-semibold text-foreground">
                  {(
                    analysis.final_analysis?.input_cells ||
                    0
                  ).toLocaleString()}
                </div>
              </div>

              <div className="rounded-lg border border-border bg-background p-4">
                <div className="text-xs text-muted-foreground">
                  Pipeline
                </div>
                <div className="mt-1 text-sm font-semibold text-foreground">
                  {analysis.final_analysis?.pipeline ||
                    "IMMUNO-XAI"}
                </div>
              </div>
            </div>
          )}

          {error && (
            <div className="mt-6 flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
              <Info className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div className="mt-7 flex flex-wrap gap-3">
            <Link
              to="/results"
              className="inline-flex h-10 items-center gap-2 rounded-lg border border-border bg-card px-4 text-sm font-medium text-foreground hover:bg-muted"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to Results
            </Link>

            <button
              type="button"
              onClick={downloadPdf}
              disabled={
                !analysis ||
                analysis.status !== "completed" ||
                downloading
              }
              className="inline-flex h-10 items-center gap-2 rounded-lg bg-primary px-5 text-sm font-medium text-primary-foreground shadow-sm hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {downloading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Download className="h-4 w-4" />
              )}
              {downloading
                ? "Generating PDF..."
                : "Download PDF"}
            </button>
          </div>

          <div className="mt-6 rounded-lg border border-border bg-muted/60 p-4 text-xs leading-relaxed text-muted-foreground">
            The report is generated directly from the completed analysis
            stored by the backend. Only PDF download is provided here.
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
