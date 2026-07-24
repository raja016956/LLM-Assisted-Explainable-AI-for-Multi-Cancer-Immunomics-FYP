import { createFileRoute } from "@tanstack/react-router";
import { AppLayout } from "@/components/AppLayout";
import { FileText, Download } from "lucide-react";

export const Route = createFileRoute("/reports")({
  head: () => ({
    meta: [
      { title: "Reports — ImmunoXAI" },
      {
        name: "description",
        content:
          "Download PDF and CSV reports for your ImmunoXAI immune-phenotype analyses.",
      },
      { property: "og:title", content: "Reports — ImmunoXAI" },
      { property: "og:description", content: "Download analysis reports." },
    ],
  }),
  component: Reports,
});

const reports = [
  {
    name: "TCGA-BRCA Cohort A",
    type: "BRCA",
    phenotype: "Inflamed",
    date: "Jul 22, 2026",
  },
  {
    name: "TCGA-LUAD Cohort B",
    type: "LUAD",
    phenotype: "Immune-Excluded",
    date: "Jul 21, 2026",
  },
  {
    name: "TCGA-COAD Cohort C",
    type: "COAD",
    phenotype: "Immune-Desert",
    date: "Jul 20, 2026",
  },
  {
    name: "TCGA-SKCM Cohort D",
    type: "SKCM",
    phenotype: "Inflamed",
    date: "Jul 19, 2026",
  },
];

function phenoStyle(p: string) {
  if (p === "Inflamed") return "bg-[oklch(0.95_0.06_155)] text-[oklch(0.4_0.14_155)]";
  if (p === "Immune-Excluded") return "bg-[oklch(0.96_0.07_75)] text-[oklch(0.45_0.14_65)]";
  return "bg-muted text-muted-foreground";
}

function Reports() {
  return (
    <AppLayout title="Reports" subtitle="Generated analysis exports and shareable documents">
      <div className="rounded-xl border border-border bg-card shadow-sm">
        <div className="flex items-center justify-between border-b border-border px-6 py-4">
          <div>
            <h3 className="text-sm font-semibold text-foreground">Generated Reports</h3>
            <p className="text-xs text-muted-foreground">
              {reports.length} reports available for download
            </p>
          </div>
          <div className="flex items-center gap-2">
            <select className="h-9 rounded-lg border border-input bg-background px-3 text-xs outline-none focus:border-ring">
              <option>All cancer types</option>
              <option>BRCA</option>
              <option>LUAD</option>
              <option>COAD</option>
              <option>SKCM</option>
              <option>GBM</option>
            </select>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs uppercase tracking-wider text-muted-foreground">
                <th className="px-6 py-3 font-medium">Dataset Name</th>
                <th className="px-6 py-3 font-medium">Predicted Immune Phenotype</th>
                <th className="px-6 py-3 font-medium">Generation Date</th>
                <th className="px-6 py-3 text-right font-medium">Download</th>
              </tr>
            </thead>
            <tbody>
              {reports.map((r) => (
                <tr key={r.name} className="border-b border-border last:border-0">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary-soft text-primary">
                        <FileText className="h-4 w-4" />
                      </div>
                      <div>
                        <div className="font-medium text-foreground">{r.name}</div>
                        <div className="text-xs text-muted-foreground">
                          {r.type} · Random Forest
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span
                      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${phenoStyle(
                        r.phenotype,
                      )}`}
                    >
                      {r.phenotype}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-muted-foreground">{r.date}</td>
                  <td className="px-6 py-4">
                    <div className="flex justify-end gap-2">
                      <button className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-border bg-card px-3 text-xs font-medium text-foreground hover:bg-muted">
                        <Download className="h-3.5 w-3.5" /> PDF
                      </button>
                      <button className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-border bg-card px-3 text-xs font-medium text-foreground hover:bg-muted">
                        <Download className="h-3.5 w-3.5" /> CSV
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </AppLayout>
  );
}
