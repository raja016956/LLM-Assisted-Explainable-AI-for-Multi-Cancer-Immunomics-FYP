import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { onAuthStateChanged, type User } from "firebase/auth";
import {
  ArrowUpRight,
  Database,
  Download,
  FileText,
  FlaskConical,
  Loader2,
  Microscope,
  RefreshCw,
  Upload,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { AppLayout } from "@/components/AppLayout";
import { auth } from "@/lib/firebase";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  "http://127.0.0.1:8000";

type AnalysisHistoryItem = {
  job_id: string;
  status: string;
  progress?: number;
  step?: string | null;
  step_number?: number;
  total_steps?: number;
  message?: string;
  started_at?: string | null;
  completed_at?: string | null;
  dataset_name?: string | null;
  file_size?: number | null;
  owner_uid?: string | null;
  report_available?: boolean;
  legacy?: boolean;
};

type AnalysisHistoryResponse = {
  success?: boolean;
  count?: number;
  jobs?: AnalysisHistoryItem[];
};

export const Route = createFileRoute("/dashboard")({
  head: () => ({
    meta: [
      { title: "Dashboard — ImmunoXAI" },
      {
        name: "description",
        content:
          "Overview of your immunomics datasets, analyses, and generated reports on ImmunoXAI.",
      },
      { property: "og:title", content: "Dashboard — ImmunoXAI" },
      {
        property: "og:description",
        content: "Overview of datasets, analyses and reports.",
      },
    ],
  }),
  component: Dashboard,
});

function formatDate(value?: string | null) {
  if (!value) return "—";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) return "—";

  return new Intl.DateTimeFormat(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(date);
}

function formatFileSize(bytes?: number | null) {
  if (!bytes || bytes <= 0) return "—";

  const units = ["B", "KB", "MB", "GB"];
  let size = bytes;
  let index = 0;

  while (size >= 1024 && index < units.length - 1) {
    size /= 1024;
    index += 1;
  }

  return `${size.toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

function statusStyle(status: string) {
  if (status === "completed") {
    return "bg-[oklch(0.95_0.06_155)] text-[oklch(0.35_0.12_155)]";
  }

  if (status === "running" || status === "queued") {
    return "bg-primary-soft text-primary";
  }

  if (status === "failed") {
    return "bg-destructive/10 text-destructive";
  }

  return "bg-muted text-muted-foreground";
}

function prettyStatus(status: string) {
  if (!status) return "Unknown";
  return status.charAt(0).toUpperCase() + status.slice(1);
}

function Dashboard() {
  const navigate = useNavigate();
  const [user, setUser] = useState<User | null>(auth.currentUser);
  const [jobs, setJobs] = useState<AnalysisHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [downloadingJobId, setDownloadingJobId] = useState<string | null>(null);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (currentUser) => {
      setUser(currentUser);
    });

    return unsubscribe;
  }, []);

  async function loadHistory(showRefreshState = false) {
    try {
      if (showRefreshState) setRefreshing(true);
      else setLoading(true);

      setError("");

      const response = await fetch(
        `${API_BASE_URL}/api/analysis/`,
        {
          method: "GET",
          headers: {
            Accept: "application/json",
          },
        },
      );

      const data =
        (await response.json().catch(() => null)) as
          | AnalysisHistoryResponse
          | { detail?: string }
          | null;

      if (!response.ok) {
        throw new Error(
          typeof data?.detail === "string"
            ? data.detail
            : "Unable to load analysis history.",
        );
      }

      const history =
        "jobs" in (data || {}) && Array.isArray(data?.jobs)
          ? data.jobs
          : [];

      const currentUid = auth.currentUser?.uid;

      const userJobs = history.filter(
        (job) =>
          !job.owner_uid ||
          !currentUid ||
          job.owner_uid === currentUid,
      );

      setJobs(userJobs);
    } catch (err) {
      console.error("[ImmunoXAI] Failed to load dashboard history:", err);
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load your analysis history.",
      );
      setJobs([]);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    if (user) {
      void loadHistory();
    } else {
      setJobs([]);
      setLoading(false);
    }
  }, [user]);

  const stats = useMemo(() => {
    const completed = jobs.filter(
      (job) => job.status === "completed",
    );

    const reportCount = completed.filter(
      (job) => job.report_available,
    ).length;

    const cancerTypes = new Set<string>();

    for (const job of completed) {
      const name = job.dataset_name || "";
      const match = name.toUpperCase().match(
        /(?:^|[^A-Z])(BRCA|LUAD|COAD|SKCM|GBM)(?:[^A-Z]|$)/,
      );

      if (match?.[1]) {
        cancerTypes.add(match[1]);
      }
    }

    return {
      uploaded: jobs.length,
      completed: completed.length,
      reports: reportCount,
      cancerTypes: cancerTypes.size,
    };
  }, [jobs]);

  async function downloadReport(job: AnalysisHistoryItem) {
    if (job.status !== "completed" || !job.report_available) return;

    try {
      setDownloadingJobId(job.job_id);

      const response = await fetch(
        `${API_BASE_URL}/api/analysis/${encodeURIComponent(
          job.job_id,
        )}/report`,
        {
          method: "GET",
          headers: {
            Accept: "application/pdf",
          },
        },
      );

      if (!response.ok) {
        const data = await response.json().catch(() => null);
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
      anchor.download = `IMMUNO_XAI_Report_${job.job_id}.pdf`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("[ImmunoXAI] PDF download failed:", err);
      setError(
        err instanceof Error
          ? err.message
          : "Unable to download the PDF report.",
      );
    } finally {
      setDownloadingJobId(null);
    }
  }

  async function openAnalysis(job: AnalysisHistoryItem) {
    if (job.status !== "completed") return;

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/analysis/${encodeURIComponent(
          job.job_id,
        )}/result`,
        {
          headers: {
            Accept: "application/json",
          },
        },
      );

      const data = await response.json().catch(() => null);

      if (!response.ok) {
        throw new Error(
          typeof data?.detail === "string"
            ? data.detail
            : "Unable to load this analysis.",
        );
      }

      sessionStorage.setItem(
        "immunoxai-analysis",
        JSON.stringify(data),
      );
      sessionStorage.setItem(
        "immunoxai-job-id",
        job.job_id,
      );

      await navigate({ to: "/results" });
    } catch (err) {
      console.error("[ImmunoXAI] Failed to open analysis:", err);
      setError(
        err instanceof Error
          ? err.message
          : "Unable to open this analysis.",
      );
    }
  }

  const recentJobs = jobs.slice(0, 10);

  return (
    <AppLayout
      title="Dashboard"
      subtitle="Your immunomics workspace"
    >
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-foreground">
            Welcome back,{" "}
            {user?.displayName?.trim()?.split(/\s+/)[0] ||
              user?.email?.split("@")[0] ||
              "there"}
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Your previous datasets, analyses, and downloadable reports.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => void loadHistory(true)}
            disabled={refreshing}
            className="inline-flex h-10 items-center gap-2 rounded-lg border border-border bg-card px-3 text-sm font-medium text-foreground hover:bg-muted disabled:cursor-not-allowed disabled:opacity-60"
          >
            <RefreshCw
              className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`}
            />
            Refresh
          </button>

          <Link
            to="/upload"
            className="inline-flex h-10 items-center gap-2 rounded-lg bg-primary px-4 text-sm font-medium text-primary-foreground shadow-sm hover:bg-primary/90"
          >
            <Upload className="h-4 w-4" />
            New Analysis
          </Link>
        </div>
      </div>

      <div className="mt-8 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        {[
          {
            label: "Uploaded Datasets",
            value: stats.uploaded,
            detail: "Analysis history",
            icon: Database,
          },
          {
            label: "Completed Analyses",
            value: stats.completed,
            detail: "Ready to review",
            icon: FlaskConical,
          },
          {
            label: "Cancer Types",
            value: stats.cancerTypes,
            detail:
              stats.cancerTypes > 0
                ? "Detected from dataset names"
                : "Available after analysis",
            icon: Microscope,
          },
          {
            label: "Generated Reports",
            value: stats.reports,
            detail: "PDF reports available",
            icon: FileText,
          },
        ].map((stat) => {
          const Icon = stat.icon;

          return (
            <div
              key={stat.label}
              className="rounded-xl border border-border bg-card p-5 shadow-sm"
            >
              <div className="flex items-start justify-between">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-soft text-primary">
                  <Icon className="h-5 w-5" />
                </div>
                <ArrowUpRight className="h-4 w-4 text-muted-foreground" />
              </div>

              <div className="mt-4 text-3xl font-semibold tracking-tight text-foreground">
                {stat.value}
              </div>

              <div className="mt-1 text-sm text-foreground">
                {stat.label}
              </div>

              <div className="mt-0.5 text-xs text-muted-foreground">
                {stat.detail}
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-8 rounded-xl border border-border bg-card shadow-sm">
        <div className="flex flex-col gap-3 border-b border-border px-6 py-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h3 className="text-sm font-semibold text-foreground">
              Previous Analyses
            </h3>
            <p className="text-xs text-muted-foreground">
              Real analyses stored by the backend
            </p>
          </div>

          <Link
            to="/reports"
            className="text-xs font-medium text-primary hover:underline"
          >
            View reports
          </Link>
        </div>

        {error && (
          <div className="mx-6 mt-4 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
            {error}
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center gap-2 p-10 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading your analysis history...
          </div>
        ) : recentJobs.length === 0 ? (
          <div className="p-10 text-center">
            <Database className="mx-auto h-8 w-8 text-muted-foreground" />
            <h4 className="mt-3 text-sm font-semibold text-foreground">
              No analyses yet
            </h4>
            <p className="mt-1 text-xs text-muted-foreground">
              Upload your first expression matrix to see it here.
            </p>
            <Link
              to="/upload"
              className="mt-4 inline-flex h-9 items-center gap-2 rounded-lg bg-primary px-3 text-xs font-medium text-primary-foreground hover:bg-primary/90"
            >
              <Upload className="h-3.5 w-3.5" />
              Upload Dataset
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[820px] text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs uppercase tracking-wider text-muted-foreground">
                  <th className="px-6 py-3 font-medium">Dataset</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Size</th>
                  <th className="px-4 py-3 font-medium">Date</th>
                  <th className="px-6 py-3 text-right font-medium">Actions</th>
                </tr>
              </thead>

              <tbody>
                {recentJobs.map((job) => (
                  <tr
                    key={job.job_id}
                    className="border-b border-border last:border-0"
                  >
                    <td className="px-6 py-4">
                      <div className="max-w-[360px] truncate font-medium text-foreground">
                        {job.dataset_name || job.job_id}
                      </div>
                      <div className="mt-0.5 text-xs text-muted-foreground">
                        {job.job_id}
                      </div>
                    </td>

                    <td className="px-4 py-4">
                      <span
                        className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${statusStyle(
                          job.status,
                        )}`}
                      >
                        {prettyStatus(job.status)}
                      </span>
                    </td>

                    <td className="px-4 py-4 text-xs text-muted-foreground">
                      {formatFileSize(job.file_size)}
                    </td>

                    <td className="px-4 py-4 text-xs text-muted-foreground">
                      {formatDate(
                        job.completed_at || job.started_at,
                      )}
                    </td>

                    <td className="px-6 py-4">
                      <div className="flex justify-end gap-2">
                        {job.status === "completed" && (
                          <button
                            type="button"
                            onClick={() => void openAnalysis(job)}
                            className="inline-flex h-8 items-center gap-1.5 rounded-md border border-border bg-card px-2.5 text-xs font-medium text-foreground hover:bg-muted"
                          >
                            View
                          </button>
                        )}

                        {job.status === "completed" &&
                          job.report_available && (
                            <button
                              type="button"
                              onClick={() => void downloadReport(job)}
                              disabled={
                                downloadingJobId === job.job_id
                              }
                              className="inline-flex h-8 items-center gap-1.5 rounded-md bg-primary px-2.5 text-xs font-medium text-primary-foreground hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
                            >
                              {downloadingJobId === job.job_id ? (
                                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                              ) : (
                                <Download className="h-3.5 w-3.5" />
                              )}
                              PDF
                            </button>
                          )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {jobs.length > 10 && (
          <div className="border-t border-border px-6 py-3 text-xs text-muted-foreground">
            Showing the 10 most recent analyses.
          </div>
        )}
      </div>
    </AppLayout>
  );
}
