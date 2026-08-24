import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import {
  Sparkles,
  FileDown,
  Activity,
  Info,
  ArrowLeft,
} from "lucide-react";
import { useEffect, useState } from "react";

import { AppLayout } from "@/components/AppLayout";
import type { AnalysisResult } from "@/lib/analysis";

export const Route = createFileRoute("/results")({
  head: () => ({
    meta: [
      { title: "Analysis Results — ImmunoXAI" },
      {
        name: "description",
        content:
          "Explainable AI results for immune phenotype analysis.",
      },
    ],
  }),
  component: Results,
});

function Results() {
  const navigate = useNavigate();

  const [result, setResult] =
    useState<AnalysisResult | null>(null);

  useEffect(() => {
    const stored = sessionStorage.getItem(
      "immunoxai-analysis",
    );

    if (!stored) {
      navigate({ to: "/upload" });
      return;
    }

    try {
      setResult(JSON.parse(stored));
    } catch {
      navigate({ to: "/upload" });
    }
  }, [navigate]);

  if (!result) {
    return (
      <AppLayout
        title="Analysis Results"
        subtitle="Loading analysis..."
      >
        <div className="rounded-xl border border-border bg-card p-8 text-sm text-muted-foreground">
          Loading analysis results...
        </div>
      </AppLayout>
    );
  }

  const firstSample = result.samples[0];

  const inflamedPercentage =
    result.totalSamples > 0
      ? (result.stateDistribution.inflamed /
          result.totalSamples) *
        100
      : 0;

  const excludedPercentage =
    result.totalSamples > 0
      ? (result.stateDistribution.immuneExcluded /
          result.totalSamples) *
        100
      : 0;

  const maxImportance =
    result.topGenes.length > 0
      ? Math.max(
          ...result.topGenes.map(
            (gene) => gene.importance,
          ),
        )
      : 1;

  return (
    <AppLayout
      title="Analysis Results"
      subtitle={`${result.datasetName} · ${result.model} · ${result.totalSamples} samples`}
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <span className="rounded-md border border-border bg-card px-2 py-0.5 text-xs font-medium text-foreground">
            {result.cancerType}
          </span>

          <span>·</span>

          <span>
            {result.totalGenes.toLocaleString()} genes
          </span>

          <span>·</span>

          <span>
            {new Date(
              result.analyzedAt,
            ).toLocaleString()}
          </span>
        </div>

        <div className="flex gap-2">
          <Link
            to="/upload"
            className="inline-flex h-10 items-center gap-2 rounded-lg border border-border bg-card px-4 text-sm font-medium text-foreground hover:bg-muted"
          >
            <ArrowLeft className="h-4 w-4" />
            New Analysis
          </Link>

          <Link
            to="/reports"
            className="inline-flex h-10 items-center gap-2 rounded-lg bg-primary px-5 text-sm font-medium text-primary-foreground shadow-sm hover:bg-primary/90"
          >
            <FileDown className="h-4 w-4" />
            Generate Report
          </Link>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-3">
        <div className="rounded-xl border border-border bg-card p-6 shadow-sm">
          <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
            <Activity className="h-3.5 w-3.5" />
            Prediction
          </div>

          <div className="mt-4 text-xs text-muted-foreground">
            Immune State
          </div>

          <div className="mt-1 text-2xl font-semibold text-foreground">
            {firstSample?.immuneState ?? "Unavailable"}
          </div>

          <div className="mt-1 text-sm text-muted-foreground">
            Based on immune-related expression scores
          </div>

          <div className="mt-6">
            <div className="flex items-baseline justify-between">
              <span className="text-xs text-muted-foreground">
                Confidence
              </span>

              <span className="text-2xl font-semibold text-primary">
                {firstSample
                  ? `${(
                      firstSample.confidence * 100
                    ).toFixed(1)}%`
                  : "N/A"}
              </span>
            </div>

            <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-primary"
                style={{
                  width: firstSample
                    ? `${firstSample.confidence * 100}%`
                    : "0%",
                }}
              />
            </div>
          </div>

          <div className="mt-6 grid grid-cols-2 gap-2 border-t border-border pt-5 text-center">
            <div className="rounded-lg border border-primary/30 bg-primary-soft px-2 py-3">
              <div className="text-sm font-semibold text-primary">
                {inflamedPercentage.toFixed(1)}%
              </div>

              <div className="mt-0.5 text-[10px] uppercase tracking-wider text-muted-foreground">
                Inflamed
              </div>
            </div>

            <div className="rounded-lg border border-border bg-background px-2 py-3">
              <div className="text-sm font-semibold text-foreground">
                {excludedPercentage.toFixed(1)}%
              </div>

              <div className="mt-0.5 text-[10px] uppercase tracking-wider text-muted-foreground">
                Immune-Excluded
              </div>
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-border bg-card p-6 shadow-sm">
          <h3 className="text-sm font-semibold text-foreground">
            Immune Scores
          </h3>

          <p className="text-xs text-muted-foreground">
            Scores calculated from immune marker expression
          </p>

          {firstSample && (
            <div className="mt-6 space-y-6">
              <ScoreBar
                label="T-cell Score"
                value={firstSample.tCellScore}
              />

              <ScoreBar
                label="PD-L1 / Myeloid Score"
                value={firstSample.myeloidScore}
              />
            </div>
          )}
        </div>

        <div className="rounded-xl border border-border bg-card p-6 shadow-sm">
          <h3 className="text-sm font-semibold text-foreground">
            Dataset Summary
          </h3>

          <div className="mt-5 space-y-4 text-sm">
            <SummaryRow
              label="Samples"
              value={result.totalSamples.toLocaleString()}
            />

            <SummaryRow
              label="Genes"
              value={result.totalGenes.toLocaleString()}
            />

            <SummaryRow
              label="Validation"
              value="Passed"
            />

            <SummaryRow
              label="Preprocessing"
              value="Completed"
            />

            <SummaryRow
              label="Cancer Type"
              value={result.cancerType}
            />
          </div>
        </div>
      </div>

      <div className="mt-6 rounded-xl border border-border bg-card p-6 shadow-sm">
        <div className="flex items-start justify-between">
          <div>
            <h3 className="text-sm font-semibold text-foreground">
              Important Immune Genes
            </h3>

            <p className="text-xs text-muted-foreground">
              Highest average transformed expression among the
              immune marker genes used in this analysis.
            </p>
          </div>

          <span className="rounded-md border border-border bg-muted px-2 py-1 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
            Top {result.topGenes.length}
          </span>
        </div>

        <div className="mt-6 space-y-3.5">
          {result.topGenes.map((gene) => (
            <div
              key={gene.gene}
              className="grid grid-cols-[80px_1fr_56px] items-center gap-3"
            >
              <div className="text-sm font-medium text-foreground">
                {gene.gene}
              </div>

              <div className="h-6 overflow-hidden rounded-md bg-muted">
                <div
                  className="h-full rounded-md bg-primary"
                  style={{
                    width: `${
                      (gene.importance /
                        maxImportance) *
                      100
                    }%`,
                  }}
                />
              </div>

              <div className="text-right text-xs font-mono text-muted-foreground">
                {gene.importance.toFixed(2)}
              </div>
            </div>
          ))}
        </div>
      </div>

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
              Analysis summary
            </p>
          </div>
        </div>

        {firstSample && (
          <p className="mt-5 text-sm leading-relaxed text-foreground">
            The analysis classified the sample as{" "}
            <span className="font-semibold text-primary">
              {firstSample.immuneState}
            </span>{" "}
            with an estimated confidence of{" "}
            <span className="font-semibold">
              {(
                firstSample.confidence * 100
              ).toFixed(1)}
              %
            </span>
            . The calculated T-cell score was{" "}
            <span className="font-semibold">
              {firstSample.tCellScore.toFixed(3)}
            </span>
            , while the PD-L1 / myeloid score was{" "}
            <span className="font-semibold">
              {firstSample.myeloidScore.toFixed(3)}
            </span>
            .
          </p>
        )}

        <div className="mt-5 flex items-start gap-2 rounded-lg border border-border bg-muted/60 p-3 text-xs text-muted-foreground">
          <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />

          This prototype analysis is intended for research
          and software-development validation. The final
          classification will use the trained machine-learning
          model specified in the computational pipeline.
        </div>
      </div>
    </AppLayout>
  );
}

function ScoreBar({
  label,
  value,
}: {
  label: string;
  value: number;
}) {
  const percentage = Math.min(
    Math.max(value * 20, 0),
    100,
  );

  return (
    <div>
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-foreground">
          {label}
        </span>

        <span className="font-mono text-sm text-muted-foreground">
          {value.toFixed(3)}
        </span>
      </div>

      <div className="mt-2 h-2 overflow-hidden rounded-full bg-muted">
        <div
          className="h-full rounded-full bg-primary"
          style={{
            width: `${percentage}%`,
          }}
        />
      </div>
    </div>
  );
}

function SummaryRow({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center justify-between border-b border-border pb-3">
      <span className="text-muted-foreground">
        {label}
      </span>

      <span className="font-medium text-foreground">
        {value}
      </span>
    </div>
  );
}