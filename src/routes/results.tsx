import { createFileRoute, Link } from "@tanstack/react-router";
import { AppLayout } from "@/components/AppLayout";
import { Sparkles, FileDown, Activity, Info } from "lucide-react";

export const Route = createFileRoute("/results")({
  head: () => ({
    meta: [
      { title: "Analysis Results — ImmunoXAI" },
      {
        name: "description",
        content:
          "Explainable AI results for TCGA-BRCA Cohort A: predicted immune phenotype, SHAP feature importance, and LLM-generated biological interpretation.",
      },
      { property: "og:title", content: "Analysis Results — ImmunoXAI" },
      {
        property: "og:description",
        content: "Predicted immune phenotype with SHAP explanations.",
      },
    ],
  }),
  component: Results,
});

const shap = [
  { gene: "CXCL9", val: 0.34 },
  { gene: "CD8A", val: 0.28 },
  { gene: "GZMB", val: 0.22 },
  { gene: "IFNG", val: 0.18 },
  { gene: "PDCD1", val: 0.14 },
  { gene: "LAG3", val: 0.11 },
];

function Results() {
  const max = Math.max(...shap.map((s) => s.val));
  return (
    <AppLayout
      title="Analysis Results"
      subtitle="TCGA-BRCA Cohort A · Random Forest · 412 samples"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <span className="rounded-md border border-border bg-card px-2 py-0.5 text-xs font-medium text-foreground">
            BRCA
          </span>
          <span>·</span>
          <span>Run #A-2098</span>
          <span>·</span>
          <span>Completed Jul 22, 2026</span>
        </div>
        <Link
          to="/reports"
          className="inline-flex h-10 items-center gap-2 rounded-lg bg-primary px-5 text-sm font-medium text-primary-foreground shadow-sm hover:bg-primary/90"
        >
          <FileDown className="h-4 w-4" />
          Generate Report
        </Link>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-3">
        {/* Prediction card */}
        <div className="rounded-xl border border-border bg-card p-6 shadow-sm xl:col-span-1">
          <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
            <Activity className="h-3.5 w-3.5" /> Prediction
          </div>
          <div className="mt-4 text-xs text-muted-foreground">
            Predicted Tumor Immune Phenotype
          </div>
          <div className="mt-1 text-2xl font-semibold text-foreground">
            Inflamed
          </div>
          <div className="text-sm text-muted-foreground">Immune-Active</div>

          <div className="mt-6">
            <div className="flex items-baseline justify-between">
              <span className="text-xs text-muted-foreground">Confidence Score</span>
              <span className="text-2xl font-semibold text-primary">94.2%</span>
            </div>
            <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-muted">
              <div className="h-full rounded-full bg-primary" style={{ width: "94.2%" }} />
            </div>
          </div>

          <div className="mt-6 grid grid-cols-3 gap-2 border-t border-border pt-5 text-center">
            {[
              { k: "Inflamed", v: "94.2%", active: true },
              { k: "Excluded", v: "3.8%" },
              { k: "Desert", v: "2.0%" },
            ].map((p) => (
              <div
                key={p.k}
                className={`rounded-lg border px-2 py-3 ${
                  p.active
                    ? "border-primary/30 bg-primary-soft"
                    : "border-border bg-background"
                }`}
              >
                <div
                  className={`text-sm font-semibold ${
                    p.active ? "text-primary" : "text-foreground"
                  }`}
                >
                  {p.v}
                </div>
                <div className="mt-0.5 text-[10px] uppercase tracking-wider text-muted-foreground">
                  {p.k}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* SHAP chart */}
        <div className="rounded-xl border border-border bg-card p-6 shadow-sm xl:col-span-2">
          <div className="flex items-start justify-between">
            <div>
              <h3 className="text-sm font-semibold text-foreground">
                SHAP Feature Importance
              </h3>
              <p className="text-xs text-muted-foreground">
                Mean |SHAP value| contribution to the Inflamed prediction
              </p>
            </div>
            <span className="rounded-md border border-border bg-muted px-2 py-1 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
              Top 6 genes
            </span>
          </div>

          <div className="mt-6 space-y-3.5">
            {shap.map((s) => (
              <div key={s.gene} className="grid grid-cols-[80px_1fr_56px] items-center gap-3">
                <div className="text-sm font-medium text-foreground">{s.gene}</div>
                <div className="h-6 overflow-hidden rounded-md bg-muted">
                  <div
                    className="h-full rounded-md bg-gradient-to-r from-primary to-[oklch(0.7_0.15_220)]"
                    style={{ width: `${(s.val / max) * 100}%` }}
                  />
                </div>
                <div className="text-right text-xs font-mono text-muted-foreground">
                  {s.val.toFixed(2)}
                </div>
              </div>
            ))}
          </div>

          <div className="mt-6 flex items-center gap-4 border-t border-border pt-4 text-xs text-muted-foreground">
            <div className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-sm bg-primary" /> Cytotoxic markers
            </div>
            <div className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-sm bg-[oklch(0.7_0.15_220)]" /> Checkpoint
              activation
            </div>
          </div>
        </div>
      </div>

      {/* Interpretation */}
      <div className="mt-6 rounded-xl border border-border bg-card p-6 shadow-sm">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary-soft text-primary">
            <Sparkles className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-foreground">
              Biological Interpretation
            </h3>
            <p className="text-xs text-muted-foreground">
              LLM-assisted explanation grounded in curated immuno-oncology literature
            </p>
          </div>
        </div>

        <p className="mt-5 text-sm leading-relaxed text-foreground">
          The model predicts an <span className="font-semibold text-primary">Inflamed (Immune-Active)</span> tumor
          microenvironment with <span className="font-semibold">94.2%</span> confidence. High expression of{" "}
          <Gene>CXCL9</Gene>, <Gene>CD8A</Gene>, <Gene>GZMB</Gene>, and <Gene>IFNG</Gene> suggests
          strong cytotoxic T-cell infiltration. Elevated <Gene>PDCD1</Gene> and <Gene>LAG3</Gene>{" "}
          indicate immune checkpoint activation and potential responsiveness to immune checkpoint
          inhibitor therapy.
        </p>

        <div className="mt-5 flex items-start gap-2 rounded-lg border border-border bg-muted/60 p-3 text-xs text-muted-foreground">
          <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          Interpretation is generated for research use. Clinical decisions should be
          corroborated with orthogonal assays and multidisciplinary review.
        </div>
      </div>
    </AppLayout>
  );
}

function Gene({ children }: { children: React.ReactNode }) {
  return (
    <span className="rounded bg-primary-soft px-1 py-0.5 font-mono text-[0.85em] font-medium text-primary">
      {children}
    </span>
  );
}
