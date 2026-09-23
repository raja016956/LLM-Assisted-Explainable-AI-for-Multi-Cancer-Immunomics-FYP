import {
  createFileRoute,
  Link,
  useNavigate,
} from "@tanstack/react-router";

import {
  Sparkles,
  FileDown,
  Activity,
  Info,
  ArrowLeft,
  Database,
  Brain,
  Dna,
  BarChart3,
  Layers,
} from "lucide-react";

import {
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { useEffect, useMemo, useState } from "react";

import { AppLayout } from "@/components/AppLayout";


// ============================================================
// API CONFIGURATION
// ============================================================

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  "http://127.0.0.1:8000";


// ============================================================
// TYPES
// ============================================================

type ImmuneStateSummary = {
  cell_count: number;
  fraction: number;
  mean_confidence: number;
};

type ClusterSummary = {
  cluster: number;
  n_cells: number;
  dominant_state: string;
  dominant_state_count: number;
  dominant_state_fraction: number;
  state_distribution: Record<string, number>;
  mean_cell_confidence: number;
};

type ScoreSummary = {
  mean: number;
  median: number;
  std: number;
  min: number;
  max: number;
};

type PathwaySummary = {
  mean: number;
  median: number;
  std: number;
};

type XAIFeature = {
  feature: string;
  mean_absolute_shap: number;
  feature_index: number;
};

type XAISummary = {
  features?: XAIFeature[];
  n_cells_explained?: number;
  n_features?: number;
};

type UMAPPoint = {
  x: number;
  y: number;
  cluster: number;
  state: string;
};

type UMAPResponse = {
  success: boolean;
  n_cells: number;
  plotted_cells: number;
  points: UMAPPoint[];
};

type BiologicalInterpretation = {
  pipeline?: string;
  task?: string;
  input_cells?: number;
  provider?: string;
  model?: string;
  reasoning?: string;
  [key: string]: unknown;
};

type FinalAnalysis = {
  pipeline?: string;
  purpose?: string;
  input_cells: number;

  immune_state_summary: Record<
    string,
    ImmuneStateSummary
  >;

  cluster_summary: Record<
    string,
    ClusterSummary
  >;

  cluster_states?: Record<
    string,
    {
      cluster: number;
      n_cells: number;
      state: string;
      dominant_cell_state: string;
      dominant_cell_fraction: number;
      confidence: number;
      reason: string;
      mean_scores: Record<string, number>;
      cell_state_distribution: Record<string, number>;
    }
  >;

  immune_score_summary: Record<
    string,
    ScoreSummary
  >;

  ml_summary?: {
    prediction_count?: number;
    class_distribution?: Record<string, number>;
    [key: string]: unknown;
  };

  pathway_summary: Record<
    string,
    PathwaySummary
  >;

  xai_summary: XAISummary;

  biological_interpretation?: BiologicalInterpretation;

  [key: string]: unknown;
};

type BackendResult = {
  success: boolean;
  job_id: string;
  status: string;
  progress?: number;
  message?: string;
  final_analysis: FinalAnalysis;
};


// ============================================================
// ROUTE
// ============================================================

export const Route = createFileRoute("/results")({
  head: () => ({
    meta: [
      {
        title: "Analysis Results — ImmunoXAI",
      },
      {
        name: "description",
        content:
          "Explainable AI results for immune phenotype analysis.",
      },
    ],
  }),

  component: Results,
});


// ============================================================
// RESULTS PAGE
// ============================================================

function Results() {
  const navigate = useNavigate();

  const [result, setResult] =
    useState<BackendResult | null>(null);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState<string | null>(null);

  const [umapData, setUmapData] =
    useState<UMAPResponse | null>(null);

  const [umapLoading, setUmapLoading] =
    useState(false);

  const [umapError, setUmapError] =
    useState<string | null>(null);


  // ==========================================================
  // LOAD REAL BACKEND RESULT
  // ==========================================================

  useEffect(() => {
    let cancelled = false;

    async function loadResult() {
      try {
        setLoading(true);
        setError(null);

        const jobId =
          sessionStorage.getItem(
            "immunoxai-job-id",
          );

        const stored =
          sessionStorage.getItem(
            "immunoxai-analysis",
          );


        // ------------------------------------------------------
        // PREFERRED METHOD:
        // Fetch fresh result from backend using job ID.
        // ------------------------------------------------------

        if (jobId) {
          const response =
            await fetch(
              `${API_BASE_URL}/api/analysis/${encodeURIComponent(
                jobId,
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
            throw new Error(
              typeof data?.detail === "string"
                ? data.detail
                : "Failed to load analysis results.",
            );
          }

          if (
            !data ||
            !data.final_analysis
          ) {
            throw new Error(
              "The backend returned an invalid analysis result.",
            );
          }

          if (!cancelled) {
            setResult(
              data as BackendResult,
            );
          }

          return;
        }


        // ------------------------------------------------------
        // FALLBACK:
        // Use the result already stored in sessionStorage.
        // ------------------------------------------------------

        if (stored) {
          const parsed =
            JSON.parse(stored);

          if (
            parsed?.final_analysis
          ) {
            if (!cancelled) {
              setResult(
                parsed as BackendResult,
              );
            }

            return;
          }
        }


        // ------------------------------------------------------
        // NOTHING AVAILABLE
        // ------------------------------------------------------

        if (!cancelled) {
          setError(
            "No completed analysis was found. Please run an analysis first.",
          );
        }

      } catch (err) {
        console.error(
          "Failed to load analysis results:",
          err,
        );

        if (!cancelled) {
          setError(
            err instanceof Error
              ? err.message
              : "Unable to load analysis results.",
          );
        }

      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadResult();

    return () => {
      cancelled = true;
    };

  }, []);

  useEffect(() => {
    const jobId = result?.job_id;
    if (!jobId) return;

    let cancelled = false;

    async function loadUmap() {
      try {
        setUmapLoading(true);
        setUmapError(null);

        const response = await fetch(
          `${API_BASE_URL}/api/analysis/${encodeURIComponent(jobId)}/visualizations/umap`,
          { headers: { Accept: "application/json" } },
        );

        const data = await response.json().catch(() => null);
        if (!response.ok) {
          throw new Error(
            typeof data?.detail === "string"
              ? data.detail
              : "Failed to load UMAP visualization.",
          );
        }

        if (!cancelled) setUmapData(data as UMAPResponse);
      } catch (err) {
        console.error("Failed to load UMAP visualization:", err);
        if (!cancelled) {
          setUmapError(
            err instanceof Error
              ? err.message
              : "Unable to load UMAP visualization.",
          );
        }
      } finally {
        if (!cancelled) setUmapLoading(false);
      }
    }

    loadUmap();
    return () => {
      cancelled = true;
    };
  }, [result?.job_id]);


  // ==========================================================
  // LOADING
  // ==========================================================

  if (loading) {
    return (
      <AppLayout
        title="Analysis Results"
        subtitle="Loading completed analysis..."
      >
        <div className="rounded-xl border border-border bg-card p-8 text-sm text-muted-foreground">
          Loading analysis results...
        </div>
      </AppLayout>
    );
  }


  // ==========================================================
  // ERROR
  // ==========================================================

  if (error || !result) {
    return (
      <AppLayout
        title="Analysis Results"
        subtitle="Unable to load analysis"
      >
        <div className="rounded-xl border border-destructive/30 bg-card p-8">

          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-destructive/10 text-destructive">
              <Info className="h-5 w-5" />
            </div>

            <div>
              <h2 className="text-base font-semibold text-foreground">
                Results could not be loaded
              </h2>

              <p className="mt-1 text-sm text-muted-foreground">
                {error ||
                  "No analysis result is available."}
              </p>
            </div>
          </div>

          <div className="mt-6 flex gap-3">

            <Link
              to="/upload"
              className="inline-flex h-10 items-center gap-2 rounded-lg bg-primary px-4 text-sm font-medium text-primary-foreground"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to Analysis
            </Link>

            <button
              type="button"
              onClick={() =>
                window.location.reload()
              }
              className="inline-flex h-10 items-center rounded-lg border border-border bg-card px-4 text-sm font-medium text-foreground hover:bg-muted"
            >
              Try Again
            </button>

          </div>
        </div>
      </AppLayout>
    );
  }


  const analysis =
    result.final_analysis;


  // ==========================================================
  // DERIVED DATA
  // ==========================================================

  const stateEntries =
    Object.entries(
      analysis.immune_state_summary || {},
    ).sort(
      ([, a], [, b]) =>
        b.cell_count - a.cell_count,
    );


  const clusterEntries =
    Object.entries(
      analysis.cluster_summary || {},
    )
      .map(
        ([key, value]) => [
          key,
          value,
        ] as const,
      )
      .sort(
        ([, a], [, b]) =>
          a.cluster - b.cluster,
      );


  const scoreEntries =
    Object.entries(
      analysis.immune_score_summary || {},
    );


  const pathwayEntries =
    Object.entries(
      analysis.pathway_summary || {},
    );


  const xaiFeatures =
    analysis.xai_summary?.features || [];


  const maxShap =
    xaiFeatures.length > 0
      ? Math.max(
          ...xaiFeatures.map(
            (feature) =>
              feature.mean_absolute_shap,
          ),
        )
      : 1;


  const dominantState =
    stateEntries.length > 0
      ? stateEntries[0]
      : null;


  const totalCells =
    analysis.input_cells || 0;


  const mlDistribution =
    analysis.ml_summary
      ?.class_distribution || {};


  const biologicalReasoning =
    analysis.biological_interpretation
      ?.reasoning || "";


  return (
    <AppLayout
      title="Analysis Results"
      subtitle={`IMMUNO-XAI · ${totalCells.toLocaleString()} cells · ${result.job_id}`}
    >

      {/* ======================================================
          TOP ACTION BAR
      ====================================================== */}

      <div className="flex flex-wrap items-center justify-between gap-3">

        <div className="flex items-center gap-2 text-sm text-muted-foreground">

          <span className="rounded-md border border-border bg-card px-2 py-1 text-xs font-medium text-foreground">
            {analysis.pipeline ||
              "IMMUNO-XAI"}
          </span>

          <span>·</span>

          <span>
            {totalCells.toLocaleString()} cells
          </span>

          <span>·</span>

          <span className="text-green-600">
            Completed
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


      {/* ======================================================
          OVERVIEW
      ====================================================== */}

      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-3">


        {/* ----------------------------------------------------
            PIPELINE
        ---------------------------------------------------- */}

        <div className="rounded-xl border border-border bg-card p-6 shadow-sm">

          <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
            <Activity className="h-3.5 w-3.5" />
            Pipeline
          </div>

          <div className="mt-4 text-2xl font-semibold text-foreground">
            {analysis.pipeline ||
              "IMMUNO-XAI"}
          </div>

          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
            {analysis.purpose ||
              "Integrated immune-state prediction and evidence package for downstream biological reasoning."}
          </p>

          <div className="mt-6 grid grid-cols-2 gap-3">

            <MetricCard
              label="Input Cells"
              value={totalCells.toLocaleString()}
            />

            <MetricCard
              label="Clusters"
              value={clusterEntries.length.toString()}
            />

          </div>

        </div>


        {/* ----------------------------------------------------
            DOMINANT STATE
        ---------------------------------------------------- */}

        <div className="rounded-xl border border-border bg-card p-6 shadow-sm">

          <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
            <Brain className="h-3.5 w-3.5" />
            Dominant Immune State
          </div>

          <div className="mt-4 text-2xl font-semibold text-foreground">
            {dominantState
              ? dominantState[0]
              : "Unavailable"}
          </div>

          {dominantState && (
            <>
              <div className="mt-2 text-sm text-muted-foreground">
                {dominantState[1].cell_count.toLocaleString()} cells
                {" · "}
                {(
                  dominantState[1].fraction *
                  100
                ).toFixed(1)}
                %
              </div>

              <div className="mt-5 h-2 w-full overflow-hidden rounded-full bg-muted">

                <div
                  className="h-full rounded-full bg-primary"
                  style={{
                    width: `${Math.min(
                      dominantState[1].fraction *
                        100,
                      100,
                    )}%`,
                  }}
                />

              </div>
            </>
          )}

        </div>


        {/* ----------------------------------------------------
            ML
        ---------------------------------------------------- */}

        <div className="rounded-xl border border-border bg-card p-6 shadow-sm">

          <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
            <BarChart3 className="h-3.5 w-3.5" />
            Machine Learning
          </div>

          <div className="mt-4 text-2xl font-semibold text-foreground">
            {(
              analysis.ml_summary
                ?.prediction_count ||
              0
            ).toLocaleString()}
          </div>

          <p className="mt-1 text-sm text-muted-foreground">
            Predictions generated
          </p>

          <div className="mt-5 space-y-2">

            {Object.entries(
              mlDistribution,
            ).map(
              ([state, count]) => (
                <div
                  key={state}
                  className="flex items-center justify-between text-sm"
                >
                  <span className="text-muted-foreground">
                    {state}
                  </span>

                  <span className="font-medium text-foreground">
                    {Number(count).toLocaleString()}
                  </span>
                </div>
              ),
            )}

          </div>

        </div>

      </div>


      {/* ======================================================
          IMMUNE STATE SUMMARY
      ====================================================== */}

      <section className="mt-6 rounded-xl border border-border bg-card p-6 shadow-sm">

        <div className="flex items-center gap-2">

          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary-soft text-primary">
            <Dna className="h-4 w-4" />
          </div>

          <div>
            <h3 className="text-sm font-semibold text-foreground">
              Immune-State Summary
            </h3>

            <p className="text-xs text-muted-foreground">
              Distribution and confidence across analyzed cells
            </p>
          </div>

        </div>


        <div className="mt-6 space-y-4">

          {stateEntries.map(
            ([state, data]) => (

              <div key={state}>

                <div className="flex items-center justify-between text-sm">

                  <span className="font-medium text-foreground">
                    {state}
                  </span>

                  <span className="text-muted-foreground">
                    {data.cell_count.toLocaleString()} cells
                    {" · "}
                    {(data.fraction * 100).toFixed(2)}%
                    {" · "}
                    confidence{" "}
                    {(
                      data.mean_confidence *
                      100
                    ).toFixed(1)}%
                  </span>

                </div>


                <div className="mt-2 h-2 overflow-hidden rounded-full bg-muted">

                  <div
                    className="h-full rounded-full bg-primary"
                    style={{
                      width: `${Math.min(
                        data.fraction *
                          100,
                        100,
                      )}%`,
                    }}
                  />

                </div>

              </div>

            ),
          )}

        </div>

      </section>


      {/* ======================================================
          IMMUNE SCORES
      ====================================================== */}

      <section className="mt-6 rounded-xl border border-border bg-card p-6 shadow-sm">

        <div className="flex items-center gap-2">

          <Activity className="h-4 w-4 text-primary" />

          <div>
            <h3 className="text-sm font-semibold text-foreground">
              Immune Scores
            </h3>

            <p className="text-xs text-muted-foreground">
              Summary statistics calculated across analyzed cells
            </p>
          </div>

        </div>


        <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">

          {scoreEntries.map(
            ([name, score]) => (

              <div
                key={name}
                className="rounded-lg border border-border bg-background p-4"
              >

                <div className="text-sm font-medium text-foreground">
                  {formatLabel(name)}
                </div>

                <div className="mt-3 text-2xl font-semibold text-primary">
                  {score.mean.toFixed(3)}
                </div>

                <div className="mt-2 space-y-1 text-xs text-muted-foreground">

                  <div className="flex justify-between">
                    <span>Median</span>
                    <span>
                      {score.median.toFixed(3)}
                    </span>
                  </div>

                  <div className="flex justify-between">
                    <span>Std</span>
                    <span>
                      {score.std.toFixed(3)}
                    </span>
                  </div>

                  <div className="flex justify-between">
                    <span>Range</span>
                    <span>
                      {score.min.toFixed(3)}
                      {" – "}
                      {score.max.toFixed(3)}
                    </span>
                  </div>

                </div>

              </div>

            ),
          )}

        </div>

      </section>


      {/* ======================================================
          CLUSTER SUMMARY
      ====================================================== */}

      <section className="mt-6 rounded-xl border border-border bg-card p-6 shadow-sm">

        <div className="flex items-center gap-2">

          <Layers className="h-4 w-4 text-primary" />

          <div>
            <h3 className="text-sm font-semibold text-foreground">
              Cluster Summary
            </h3>

            <p className="text-xs text-muted-foreground">
              Cluster-level immune-state composition
            </p>
          </div>

        </div>


        <div className="mt-6 overflow-x-auto">

          <table className="w-full text-left text-sm">

            <thead>
              <tr className="border-b border-border text-xs text-muted-foreground">
                <th className="pb-3 pr-4">
                  Cluster
                </th>

                <th className="pb-3 pr-4">
                  Cells
                </th>

                <th className="pb-3 pr-4">
                  Dominant State
                </th>

                <th className="pb-3 pr-4">
                  Fraction
                </th>

                <th className="pb-3">
                  Confidence
                </th>
              </tr>
            </thead>


            <tbody>

              {clusterEntries.map(
                ([key, cluster]) => (

                  <tr
                    key={key}
                    className="border-b border-border last:border-0"
                  >

                    <td className="py-3 pr-4 font-medium text-foreground">
                      {cluster.cluster}
                    </td>

                    <td className="py-3 pr-4 text-muted-foreground">
                      {cluster.n_cells.toLocaleString()}
                    </td>

                    <td className="py-3 pr-4 text-foreground">
                      {cluster.dominant_state}
                    </td>

                    <td className="py-3 pr-4 text-muted-foreground">
                      {(
                        cluster.dominant_state_fraction *
                        100
                      ).toFixed(1)}
                      %
                    </td>

                    <td className="py-3 text-muted-foreground">
                      {(
                        cluster.mean_cell_confidence *
                        100
                      ).toFixed(1)}
                      %
                    </td>

                  </tr>

                ),
              )}

            </tbody>

          </table>

        </div>

      </section>


      {/* ======================================================
          PATHWAYS
      ====================================================== */}

      <section className="mt-6 rounded-xl border border-border bg-card p-6 shadow-sm">

        <div className="flex items-center gap-2">

          <Database className="h-4 w-4 text-primary" />

          <div>
            <h3 className="text-sm font-semibold text-foreground">
              Pathway Summary
            </h3>

            <p className="text-xs text-muted-foreground">
              Metabolic, inflammatory, interferon and chemokine pathway scores
            </p>
          </div>

        </div>


        <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">

          {pathwayEntries.map(
            ([name, pathway]) => (

              <div
                key={name}
                className="rounded-lg border border-border bg-background p-4"
              >

                <div className="text-sm font-medium text-foreground">
                  {formatLabel(name)}
                </div>

                <div className="mt-3 text-xl font-semibold text-primary">
                  {pathway.mean.toFixed(4)}
                </div>

                <div className="mt-2 text-xs text-muted-foreground">
                  Median {pathway.median.toFixed(4)}
                  {" · "}
                  SD {pathway.std.toFixed(4)}
                </div>

              </div>

            ),
          )}

        </div>

      </section>


      {/* ======================================================
          UMAP VISUALIZATION
      ====================================================== */}

      <section className="mt-6 rounded-xl border border-border bg-card p-6 shadow-sm">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary-soft text-primary">
            <Layers className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-foreground">UMAP Visualization</h3>
            <p className="text-xs text-muted-foreground">
              QC-retained cells projected into two dimensions and colored by cluster.
            </p>
          </div>
        </div>

        {umapLoading && (
          <div className="mt-6 rounded-lg border border-border bg-background p-6 text-sm text-muted-foreground">
            Loading UMAP coordinates...
          </div>
        )}

        {umapError && !umapLoading && (
          <div className="mt-6 rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
            {umapError}
          </div>
        )}

        {umapData && !umapLoading && !umapError && (
          <>
            <div className="mt-4 flex flex-wrap gap-3 text-xs text-muted-foreground">
              <span>{umapData.n_cells.toLocaleString()} analyzed cells</span>
              <span>·</span>
              <span>{umapData.plotted_cells.toLocaleString()} cells plotted</span>
              {umapData.plotted_cells < umapData.n_cells && (
                <span>· visualization sampled for browser performance</span>
              )}
            </div>

            <div className="mt-5 h-[520px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <ScatterChart margin={{ top: 16, right: 24, bottom: 24, left: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" dataKey="x" name="UMAP 1" tick={{ fontSize: 11 }} />
                  <YAxis type="number" dataKey="y" name="UMAP 2" tick={{ fontSize: 11 }} />
                  <Tooltip
                    cursor={{ strokeDasharray: "3 3" }}
                    content={({ active, payload }) => {
                      if (!active || !payload?.length) return null;
                      const point = payload[0]?.payload as UMAPPoint;
                      return (
                        <div className="rounded-lg border border-border bg-card p-3 text-xs shadow-lg">
                          <div className="font-semibold text-foreground">Cluster {point.cluster}</div>
                          <div className="mt-1 text-muted-foreground">State: {point.state}</div>
                          <div className="mt-1 text-muted-foreground">UMAP 1: {point.x.toFixed(3)}</div>
                          <div className="text-muted-foreground">UMAP 2: {point.y.toFixed(3)}</div>
                        </div>
                      );
                    }}
                  />
                  <Legend />
                  {Array.from(new Set(umapData.points.map((point) => point.cluster)))
                    .sort((a, b) => a - b)
                    .map((cluster, index) => (
                      <Scatter
                        key={cluster}
                        name={`Cluster ${cluster}`}
                        data={umapData.points.filter((point) => point.cluster === cluster)}
                        fill={[
                          "#2563eb", "#16a34a", "#dc2626", "#9333ea", "#ea580c",
                          "#0891b2", "#db2777", "#65a30d", "#7c3aed", "#0f766e",
                        ][index % 10]}
                        line={false}
                      />
                    ))}
                </ScatterChart>
              </ResponsiveContainer>
            </div>
          </>
        )}
      </section>


      {/* ======================================================
          XAI
      ====================================================== */}

      <section className="mt-6 rounded-xl border border-border bg-card p-6 shadow-sm">

        <div className="flex items-center gap-2">

          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary-soft text-primary">
            <Sparkles className="h-4 w-4" />
          </div>

          <div>
            <h3 className="text-sm font-semibold text-foreground">
              Explainable AI — Feature Importance
            </h3>

            <p className="text-xs text-muted-foreground">
              Mean absolute SHAP contribution of the most important features
            </p>
          </div>

        </div>


        <div className="mt-6 space-y-3">

          {xaiFeatures.map(
            (feature) => (

              <div
                key={`${feature.feature}-${feature.feature_index}`}
                className="grid grid-cols-1 items-center gap-2 md:grid-cols-[minmax(260px,1.4fr)_minmax(220px,2fr)_90px] md:gap-4"
              >

                <div className="min-w-0 whitespace-normal break-words text-sm font-medium leading-5 text-foreground">
                  {feature.feature}
                </div>

                <div className="h-6 min-w-0 overflow-hidden rounded-md bg-muted">
                  <div
                    className="h-full rounded-md bg-primary"
                    style={{
                      width: `${Math.min(
                        (feature.mean_absolute_shap / maxShap) * 100,
                        100,
                      )}%`,
                    }}
                  />
                </div>

                <div className="text-right font-mono text-xs tabular-nums text-muted-foreground">
                  {feature.mean_absolute_shap.toFixed(4)}
                </div>

              </div>
            ),
          )}

        </div>


        <div className="mt-5 flex items-start gap-2 rounded-lg border border-border bg-muted/60 p-3 text-xs text-muted-foreground">

          <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />

          SHAP feature importance reflects model contribution to
          predictions; it should not be interpreted as evidence of
          biological causation.

        </div>

      </section>


      {/* ======================================================
          BIOLOGICAL INTERPRETATION
      ====================================================== */}

      <section className="mt-6 rounded-xl border border-border bg-card p-6 shadow-sm">

        <div className="flex items-center gap-2">

          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary-soft text-primary">
            <Sparkles className="h-4 w-4" />
          </div>

          <div>

            <h3 className="text-sm font-semibold text-foreground">
              Biological Interpretation
            </h3>

            <p className="text-xs text-muted-foreground">
              Generated by the biological reasoning layer
            </p>

          </div>

        </div>


        {biologicalReasoning ? (
          <div className="mt-5 whitespace-pre-wrap text-sm leading-relaxed text-foreground">
            {biologicalReasoning}
          </div>
        ) : (
          <p className="mt-5 text-sm text-muted-foreground">
            No biological interpretation was returned by the backend.
          </p>
        )}


        <div className="mt-5 flex items-start gap-2 rounded-lg border border-border bg-muted/60 p-3 text-xs text-muted-foreground">

          <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />

          This interpretation summarizes computational single-cell
          RNA-seq evidence. It does not establish causality, clinical
          diagnosis, treatment response, or experimental validation.

        </div>

      </section>

    </AppLayout>
  );
}


// ============================================================
// METRIC CARD
// ============================================================

function MetricCard({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-lg border border-border bg-background px-3 py-3">
      <div className="text-xs text-muted-foreground">
        {label}
      </div>

      <div className="mt-1 text-lg font-semibold text-foreground">
        {value}
      </div>
    </div>
  );
}


// ============================================================
// FORMAT LABEL
// ============================================================

function formatLabel(
  value: string,
): string {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) =>
      char.toUpperCase(),
    );
}