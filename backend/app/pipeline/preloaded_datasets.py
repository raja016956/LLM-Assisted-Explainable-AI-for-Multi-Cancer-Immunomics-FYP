from __future__ import annotations

from dataclasses import dataclass


// Describes one public dataset that can be selected from the Upload page.
@dataclass(frozen=True)
class PreloadedDataset:
    id: str
    cancer_type: str
    name: str
    description: str
    accession: str
    source_url: str
    filename: str


# Curated public GEO expression matrices. Files are cached locally
# after the first selection so subsequent analyses do not redownload them.
// Curated datasets exposed to the frontend. The files are downloaded and cached on first use.
PRELOADED_DATASETS = (
    PreloadedDataset(
        id="brca-gse180286-p1",
        cancer_type="BRCA",
        name="Breast Cancer — GSE180286",
        description="Primary breast cancer single-cell RNA expression matrix (GSM5457199).",
        accession="GSE180286 / GSM5457199",
        source_url="https://ftp.ncbi.nlm.nih.gov/geo/samples/GSM5457nnn/GSM5457199/suppl/GSM5457199_A2019-1.expression_matrix.txt.gz",
        filename="GSM5457199_A2019-1.expression_matrix.txt.gz",
    ),
    PreloadedDataset(
        id="skcm-gse72056",
        cancer_type="SKCM",
        name="Melanoma — GSE72056",
        description="Human melanoma single-cell RNA expression matrix from the GEO processed dataset.",
        accession="GSE72056",
        source_url="https://ftp.ncbi.nlm.nih.gov/geo/series/GSE72nnn/GSE72056/suppl/GSE72056_melanoma_single_cell_revised_v2.txt.gz",
        filename="GSE72056_melanoma_single_cell_revised_v2.txt.gz",
    ),
    PreloadedDataset(
        id="luad-gse192708",
        cancer_type="LUAD",
        name="Lung Adenocarcinoma — GSE192708",
        description="Human lung adenocarcinoma cell-line single-cell RNA expression matrix.",
        accession="GSE192708",
        source_url="https://ftp.ncbi.nlm.nih.gov/geo/series/GSE192nnn/GSE192708/suppl/GSE192708_Well-paired-seq_five_human_lung_adenocarcinoma_cell_lines_raw_dge.txt.gz",
        filename="GSE192708_Well-paired-seq_five_human_lung_adenocarcinoma_cell_lines_raw_dge.txt.gz",
    ),
)


// Fast lookup used by the preloaded-dataset API when the frontend sends a dataset ID.
PRELOADED_BY_ID = {dataset.id: dataset for dataset in PRELOADED_DATASETS}
