import { createFileRoute, Link } from "@tanstack/react-router";
import { onAuthStateChanged, type User } from "firebase/auth";
import { useEffect, useState } from "react";
import { auth } from "@/lib/firebase";
import { AppLayout } from "@/components/AppLayout";
import {
  Database,
  FlaskConical,
  Microscope,
  FileText,
  ArrowUpRight,
  Plus,
} from "lucide-react";

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

const stats = [
  {
    label: "Uploaded Datasets",
    value: "24",
    delta: "+3 this week",
    icon: Database,
  },
  {
    label: "Completed Analyses",
    value: "18",
    delta: "+5 this week",
    icon: FlaskConical,
  },
  { label: "Cancer Types", value: "5", delta: "BRCA · LUAD · COAD · SKCM · GBM", icon: Microscope },
  { label: "Generated Reports", value: "12", delta: "4 downloaded", icon: FileText },
];

const rows = [
  {
    name: "TCGA-BRCA Cohort A",
    type: "BRCA",
    status: "Completed",
    date: "Jul 22, 2026",
  },
  {
    name: "TCGA-LUAD Cohort B",
    type: "LUAD",
    status: "Completed",
    date: "Jul 21, 2026",
  },
  {
    name: "TCGA-COAD Cohort C",
    type: "COAD",
    status: "Running",
    date: "Jul 21, 2026",
  },
  {
    name: "TCGA-SKCM Cohort D",
    type: "SKCM",
    status: "Completed",
    date: "Jul 19, 2026",
  },
  {
    name: "TCGA-GBM Cohort E",
    type: "GBM",
    status: "Queued",
    date: "Jul 18, 2026",
  },
];

function statusStyle(s: string) {
  if (s === "Completed") return "bg-[oklch(0.95_0.06_155)] text-[oklch(0.35_0.12_155)]";
  if (s === "Running") return "bg-primary-soft text-primary";
  return "bg-muted text-muted-foreground";
}

function Dashboard() {
  const [user, setUser] = useState<User | null>(auth.currentUser);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (currentUser) => {
      setUser(currentUser);
    });

    return unsubscribe;
  }, []);

  const firstName =
    user?.displayName?.trim()?.split(/\s+/)[0] ||
    user?.email?.split("@")[0] ||
    "there";

  return (
    <AppLayout title="Dashboard" subtitle="Overview of your immunomics workspace">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-foreground">
            Welcome back, {firstName}
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            5 cohorts across 3 cancer types are ready for review.
          </p>
        </div>
        <Link
          to="/upload"
          className="inline-flex h-10 items-center gap-2 rounded-lg bg-primary px-4 text-sm font-medium text-primary-foreground shadow-sm hover:bg-primary/90"
        >
          <Plus className="h-4 w-4" /> New Analysis
        </Link>
      </div>

      <div className="mt-8 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        {stats.map((s) => {
          const Icon = s.icon;
          return (
            <div
              key={s.label}
              className="rounded-xl border border-border bg-card p-5 shadow-sm"
            >
              <div className="flex items-start justify-between">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-soft text-primary">
                  <Icon className="h-5 w-5" />
                </div>
                <ArrowUpRight className="h-4 w-4 text-muted-foreground" />
              </div>
              <div className="mt-4 text-3xl font-semibold tracking-tight text-foreground">
                {s.value}
              </div>
              <div className="mt-1 text-sm text-foreground">{s.label}</div>
              <div className="mt-0.5 text-xs text-muted-foreground">{s.delta}</div>
            </div>
          );
        })}
      </div>

      <div className="mt-8 grid grid-cols-1 gap-6 xl:grid-cols-3">
        <div className="rounded-xl border border-border bg-card shadow-sm xl:col-span-2">
          <div className="flex items-center justify-between border-b border-border px-6 py-4">
            <div>
              <h3 className="text-sm font-semibold text-foreground">Recent Analyses</h3>
              <p className="text-xs text-muted-foreground">
                Latest cohort runs across your workspace
              </p>
            </div>
            <Link to="/results" className="text-xs font-medium text-primary hover:underline">
              View all
            </Link>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs uppercase tracking-wider text-muted-foreground">
                  <th className="px-6 py-3 font-medium">Dataset Name</th>
                  <th className="px-6 py-3 font-medium">Cancer Type</th>
                  <th className="px-6 py-3 font-medium">Status</th>
                  <th className="px-6 py-3 font-medium">Date</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.name} className="border-b border-border last:border-0">
                    <td className="px-6 py-3.5 font-medium text-foreground">{r.name}</td>
                    <td className="px-6 py-3.5">
                      <span className="rounded-md border border-border bg-muted px-2 py-0.5 text-xs font-medium text-foreground">
                        {r.type}
                      </span>
                    </td>
                    <td className="px-6 py-3.5">
                      <span
                        className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${statusStyle(
                          r.status,
                        )}`}
                      >
                        {r.status}
                      </span>
                    </td>
                    <td className="px-6 py-3.5 text-muted-foreground">{r.date}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="rounded-xl border border-border bg-card p-6 shadow-sm">
          <h3 className="text-sm font-semibold text-foreground">Cohort Distribution</h3>
          <p className="text-xs text-muted-foreground">
            Samples analyzed by cancer type
          </p>
          <div className="mt-5 space-y-4">
            {[
              { k: "BRCA", v: 42, n: 5240 },
              { k: "LUAD", v: 24, n: 2980 },
              { k: "COAD", v: 15, n: 1870 },
              { k: "SKCM", v: 12, n: 1490 },
              { k: "GBM", v: 7, n: 900 },
            ].map((c) => (
              <div key={c.k}>
                <div className="flex items-center justify-between text-xs">
                  <span className="font-medium text-foreground">{c.k}</span>
                  <span className="text-muted-foreground">{c.n.toLocaleString()} samples</span>
                </div>
                <div className="mt-1.5 h-2 w-full overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full bg-primary"
                    style={{ width: `${c.v * 2}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
