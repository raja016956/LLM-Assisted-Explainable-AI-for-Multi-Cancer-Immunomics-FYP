import { createFileRoute, Link } from "@tanstack/react-router";
import { AppLayout } from "@/components/AppLayout";
import { UploadCloud, FileSpreadsheet, CheckCircle2, ChevronDown } from "lucide-react";

export const Route = createFileRoute("/upload")({
  head: () => ({
    meta: [
      { title: "Upload Dataset — ImmunoXAI" },
      {
        name: "description",
        content:
          "Upload a gene expression CSV, choose a cancer type and model, and run an explainable immunomics analysis.",
      },
      { property: "og:title", content: "Upload Dataset — ImmunoXAI" },
      { property: "og:description", content: "Upload and analyze a cohort." },
    ],
  }),
  component: UploadPage,
});

function UploadPage() {
  return (
    <AppLayout title="Upload Dataset" subtitle="Prepare a cohort for immune phenotype analysis">
      <div className="mx-auto max-w-4xl">
        <div className="rounded-xl border border-border bg-card p-8 shadow-sm">
          <h2 className="text-lg font-semibold text-foreground">Dataset details</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Provide metadata so downstream analyses and reports remain traceable.
          </p>

          <div className="mt-6 grid grid-cols-1 gap-5 md:grid-cols-2">
            <div>
              <label className="text-xs font-medium text-foreground">Dataset Name</label>
              <input
                defaultValue="TCGA-BRCA Cohort A"
                className="mt-1.5 h-11 w-full rounded-lg border border-input bg-background px-3 text-sm outline-none focus:border-ring focus:ring-2 focus:ring-ring/20"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-foreground">Cancer Type</label>
              <SelectField
                options={["BRCA", "LUAD", "COAD", "SKCM", "GBM"]}
                defaultValue="BRCA"
              />
            </div>
            <div className="md:col-span-2">
              <label className="text-xs font-medium text-foreground">Model</label>
              <SelectField
                options={["Random Forest", "XGBoost", "Logistic Regression"]}
                defaultValue="Random Forest"
              />
            </div>
          </div>

          <div className="mt-8">
            <label className="text-xs font-medium text-foreground">Expression Matrix (CSV)</label>
            <label className="mt-1.5 flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-border bg-primary-soft/40 px-6 py-12 text-center transition-colors hover:bg-primary-soft/70">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-card text-primary shadow-sm">
                <UploadCloud className="h-6 w-6" />
              </div>
              <div className="mt-4 text-sm font-medium text-foreground">
                Drag & drop CSV, or <span className="text-primary">browse</span>
              </div>
              <div className="mt-1 text-xs text-muted-foreground">
                Genes × samples matrix · TPM or normalized counts · up to 2 GB
              </div>
              <input type="file" accept=".csv" className="hidden" />
            </label>

            <div className="mt-4 flex items-center gap-3 rounded-lg border border-border bg-background p-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-md bg-primary-soft text-primary">
                <FileSpreadsheet className="h-5 w-5" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-medium text-foreground">
                  brca_cohort_a_tpm.csv
                </div>
                <div className="text-xs text-muted-foreground">
                  20,533 genes × 412 samples · 184 MB
                </div>
              </div>
              <span className="inline-flex items-center gap-1 text-xs font-medium text-[oklch(0.5_0.14_155)]">
                <CheckCircle2 className="h-4 w-4" /> Validated
              </span>
            </div>
          </div>

          <div className="mt-8 flex items-center justify-end gap-3 border-t border-border pt-6">
            <button className="h-10 rounded-lg border border-border bg-card px-4 text-sm font-medium text-foreground hover:bg-muted">
              Upload Dataset
            </button>
            <Link
              to="/results"
              className="inline-flex h-10 items-center rounded-lg bg-primary px-5 text-sm font-medium text-primary-foreground shadow-sm hover:bg-primary/90"
            >
              Analyze Dataset
            </Link>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}

function SelectField({
  options,
  defaultValue,
}: {
  options: string[];
  defaultValue: string;
}) {
  return (
    <div className="relative mt-1.5">
      <select
        defaultValue={defaultValue}
        className="h-11 w-full appearance-none rounded-lg border border-input bg-background px-3 pr-9 text-sm outline-none focus:border-ring focus:ring-2 focus:ring-ring/20"
      >
        {options.map((o) => (
          <option key={o}>{o}</option>
        ))}
      </select>
      <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
    </div>
  );
}
