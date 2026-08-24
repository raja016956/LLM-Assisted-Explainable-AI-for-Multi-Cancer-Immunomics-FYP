export type ImmuneState = "Inflamed" | "Immune-Excluded";

export interface SampleResult {
  sample: string;
  tCellScore: number;
  myeloidScore: number;
  immuneState: ImmuneState;
  confidence: number;
}

export interface AnalysisResult {
  datasetName: string;
  cancerType: string;
  model: string;
  totalSamples: number;
  totalGenes: number;
  validated: boolean;
  normalized: boolean;
  samples: SampleResult[];
  stateDistribution: {
    inflamed: number;
    immuneExcluded: number;
  };
  topGenes: {
    gene: string;
    importance: number;
  }[];
  analyzedAt: string;
}

const T_CELL_MARKERS = [
  "CD3D",
  "CD3E",
  "GZMB",
];

const MYELOID_MARKERS = [
  "CD274",
  "C1QA",
  "LST1",
  "CXCL9",
];

function parseCSV(text: string): string[][] {
  const rows: string[][] = [];
  let row: string[] = [];
  let cell = "";
  let insideQuotes = false;

  for (let i = 0; i < text.length; i++) {
    const char = text[i];
    const next = text[i + 1];

    if (char === '"' && insideQuotes && next === '"') {
      cell += '"';
      i++;
    } else if (char === '"') {
      insideQuotes = !insideQuotes;
    } else if (char === "," && !insideQuotes) {
      row.push(cell.trim());
      cell = "";
    } else if ((char === "\n" || char === "\r") && !insideQuotes) {
      if (char === "\r" && next === "\n") {
        i++;
      }

      row.push(cell.trim());
      cell = "";

      if (row.some((value) => value !== "")) {
        rows.push(row);
      }

      row = [];
    } else {
      cell += char;
    }
  }

  if (cell !== "" || row.length > 0) {
    row.push(cell.trim());

    if (row.some((value) => value !== "")) {
      rows.push(row);
    }
  }

  return rows;
}

function toNumber(value: string | undefined): number {
  if (!value) return 0;

  const number = Number(value);

  return Number.isFinite(number) ? number : 0;
}

function normalizeValue(value: number): number {
  return Math.log1p(Math.max(value, 0));
}

function calculateScore(
  geneExpression: Map<string, number>,
  markers: string[],
): number {
  const values = markers
    .map((gene) => geneExpression.get(gene))
    .filter((value): value is number => value !== undefined);

  if (values.length === 0) {
    return 0;
  }

  const normalizedValues = values.map(normalizeValue);

  return (
    normalizedValues.reduce((sum, value) => sum + value, 0) /
    normalizedValues.length
  );
}

function calculateConfidence(
  tCellScore: number,
  myeloidScore: number,
): number {
  const total = tCellScore + myeloidScore;

  if (total === 0) {
    return 0.5;
  }

  const strongerScore = Math.max(tCellScore, myeloidScore);

  const confidence = strongerScore / total;

  return Math.min(Math.max(confidence, 0.5), 0.99);
}

export function analyzeCSV(
  csvText: string,
  datasetName: string,
  cancerType: string,
  model: string,
): AnalysisResult {
  const rows = parseCSV(csvText);

  if (rows.length < 2) {
    throw new Error("The CSV file does not contain enough data.");
  }

  const header = rows[0];

  if (header.length < 2) {
    throw new Error(
      "The CSV must contain a gene column and at least one sample column.",
    );
  }

  const geneColumn = header[0];

  if (!geneColumn) {
    throw new Error("The first CSV column must contain gene identifiers.");
  }

  const sampleNames = header.slice(1);

  const expression = new Map<string, Map<string, number>>();

  for (const row of rows.slice(1)) {
    const gene = row[0]?.trim();

    if (!gene) {
      continue;
    }

    const values = new Map<string, number>();

    sampleNames.forEach((sample, index) => {
      values.set(sample, toNumber(row[index + 1]));
    });

    expression.set(gene.toUpperCase(), values);
  }

  if (expression.size === 0) {
    throw new Error("No valid gene-expression rows were found.");
  }

  const requiredMarkers = [
    ...T_CELL_MARKERS,
    ...MYELOID_MARKERS,
  ];

  const availableMarkers = requiredMarkers.filter((gene) =>
    expression.has(gene),
  );

  if (availableMarkers.length === 0) {
    throw new Error(
      "The dataset does not contain the required immune marker genes.",
    );
  }

  const samples: SampleResult[] = sampleNames.map((sample) => {
    const geneExpression = new Map<string, number>();

    expression.forEach((sampleValues, gene) => {
      geneExpression.set(gene, sampleValues.get(sample) ?? 0);
    });

    const tCellScore = calculateScore(
      geneExpression,
      T_CELL_MARKERS,
    );

    const myeloidScore = calculateScore(
      geneExpression,
      MYELOID_MARKERS,
    );

    const immuneState: ImmuneState =
      tCellScore >= myeloidScore
        ? "Inflamed"
        : "Immune-Excluded";

    const confidence = calculateConfidence(
      tCellScore,
      myeloidScore,
    );

    return {
      sample,
      tCellScore,
      myeloidScore,
      immuneState,
      confidence,
    };
  });

  const inflamed = samples.filter(
    (sample) => sample.immuneState === "Inflamed",
  ).length;

  const immuneExcluded = samples.filter(
    (sample) => sample.immuneState === "Immune-Excluded",
  ).length;

  const topGenes = requiredMarkers
    .filter((gene) => expression.has(gene))
    .map((gene) => {
      const values = expression.get(gene)!;

      const mean =
        Array.from(values.values()).reduce(
          (sum, value) => sum + normalizeValue(value),
          0,
        ) / values.size;

      return {
        gene,
        importance: mean,
      };
    })
    .sort((a, b) => b.importance - a.importance)
    .slice(0, 6);

  return {
    datasetName,
    cancerType,
    model,
    totalSamples: sampleNames.length,
    totalGenes: expression.size,
    validated: true,
    normalized: true,
    samples,
    stateDistribution: {
      inflamed,
      immuneExcluded,
    },
    topGenes,
    analyzedAt: new Date().toISOString(),
  };
}