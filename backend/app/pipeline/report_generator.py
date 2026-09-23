from __future__ import annotations

import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


NAVY = "#172033"
TEAL = "#147D82"
BLUE = "#3B82F6"
ORANGE = "#E59A23"
PURPLE = "#7C63C9"
RED = "#D95C5C"
LIGHT = "#F4F7FA"
MID = "#DCE3EA"
TEXT = "#273142"
MUTED = "#687386"


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _safe_text(value: Any) -> str:
    if value is None:
        return "Not available"
    text = str(value)
    replacements = {
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
        "\u2022": "-",
        "\u00b7": "-",
        "\u2265": ">=",
        "\u2264": "<=",
        "\u2248": "~",
        "\u2192": "->",
        "\u201c": '"',
        "\u201d": '"',
        "\u2018": "'",
        "\u2019": "'",
        "\u00a0": " ",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return re.sub(r"\s+", " ", text).strip() or "Not available"


def _clean_markdown(text: str) -> str:
    text = _safe_text(text)
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
    text = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", text)
    text = text.replace("**", "").replace("__", "")
    text = text.replace("\`", "")
    text = re.sub(r"^#{1,6}\s*", "", text)
    text = re.sub(r"^\s*[-*]\s*", "", text)
    return text.strip()


def _escape(text: Any) -> str:
    value = _safe_text(text)
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _number(value: Any, digits: int = 4) -> str:
    try:
        number = float(value)
        return f"{number:.{digits}f}" if math.isfinite(number) else "-"
    except (TypeError, ValueError):
        return "-"


def _percent(value: Any, digits: int = 1) -> str:
    try:
        return f"{float(value) * 100:.{digits}f}%"
    except (TypeError, ValueError):
        return "-"


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("ReportTitle", parent=base["Title"], fontName="Helvetica-Bold",
                                fontSize=24, leading=28, alignment=TA_CENTER,
                                textColor=colors.HexColor(NAVY), spaceAfter=5),
        "subtitle": ParagraphStyle("ReportSubtitle", parent=base["Normal"], fontName="Helvetica",
                                   fontSize=10, leading=14, alignment=TA_CENTER,
                                   textColor=colors.HexColor(MUTED), spaceAfter=15),
        "section": ParagraphStyle("Section", parent=base["Heading2"], fontName="Helvetica-Bold",
                                  fontSize=14, leading=18, textColor=colors.HexColor(NAVY),
                                  spaceBefore=8, spaceAfter=8),
        "subsection": ParagraphStyle("Subsection", parent=base["Heading3"], fontName="Helvetica-Bold",
                                     fontSize=10.5, leading=14, textColor=colors.HexColor(TEAL),
                                     spaceBefore=7, spaceAfter=4),
        "body": ParagraphStyle("Body", parent=base["BodyText"], fontName="Helvetica",
                               fontSize=9, leading=13, textColor=colors.HexColor(TEXT), spaceAfter=6),
        "small": ParagraphStyle("Small", parent=base["BodyText"], fontName="Helvetica",
                                fontSize=7.5, leading=10, textColor=colors.HexColor(MUTED)),
        "table": ParagraphStyle("Table", parent=base["BodyText"], fontName="Helvetica",
                                fontSize=7.6, leading=9.5, textColor=colors.HexColor(TEXT)),
        "table_bold": ParagraphStyle("TableBold", parent=base["BodyText"], fontName="Helvetica-Bold",
                                     fontSize=7.6, leading=9.5, textColor=colors.HexColor(TEXT)),
        "card_label": ParagraphStyle("CardLabel", parent=base["BodyText"], fontName="Helvetica-Bold",
                                     fontSize=7.5, leading=9, textColor=colors.HexColor(MUTED)),
        "card_value": ParagraphStyle("CardValue", parent=base["BodyText"], fontName="Helvetica-Bold",
                                     fontSize=14, leading=17, textColor=colors.HexColor(NAVY)),
    }


def _p(text: Any, style: ParagraphStyle) -> Paragraph:
    return Paragraph(_escape(text), style)


def _section(text: str, styles: dict[str, ParagraphStyle]) -> Paragraph:
    return _p(text, styles["section"])


def _table(rows: list[list[Any]], widths: list[float], styles: dict[str, ParagraphStyle], header: bool = True) -> Table:
    converted = []
    for row_index, row in enumerate(rows):
        converted.append([
            value if isinstance(value, Paragraph) else Paragraph(
                _escape(value),
                styles["table_bold"] if header and row_index == 0 else styles["table"],
            )
            for value in row
        ])

    table = Table(converted, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor(MID)),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    if header:
        commands += [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(LIGHT)),
            ("LINEBELOW", (0, 0), (-1, 0), 0.8, colors.HexColor(MID)),
        ]
    table.setStyle(TableStyle(commands))
    return table


def _card(label: str, value: str, styles: dict[str, ParagraphStyle]) -> Table:
    table = Table(
        [[_p(label.upper(), styles["card_label"])], [_p(value, styles["card_value"])]],
        colWidths=[52 * mm],
        rowHeights=[8 * mm, 12 * mm],
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(LIGHT)),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor(MID)),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor(MID)),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def _save_figure(fig, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def _make_state_chart(data: dict[str, Any], path: Path) -> Path | None:
    items = [(label, int(value.get("cell_count", 0))) for label, value in data.items()
             if int(value.get("cell_count", 0)) > 0]
    if not items:
        return None
    items.sort(key=lambda x: x[1], reverse=True)
    labels = [_safe_text(x[0]) for x in items]
    values = [x[1] for x in items]
    fig, ax = plt.subplots(figsize=(6.2, 3.5), dpi=180)
    palette = [TEAL, BLUE, ORANGE, PURPLE, RED, "#7B8794"]
    wedges, _ = ax.pie(values, startangle=90, counterclock=False,
                       colors=palette[:len(values)],
                       wedgeprops={"width": 0.38, "edgecolor": "white"})
    ax.text(0, 0, f"{sum(values):,}\ncells", ha="center", va="center",
            fontsize=12, fontweight="bold", color=NAVY)
    ax.legend(wedges,
              [f"{label}: {value:,} ({value/sum(values)*100:.1f}%)"
               for label, value in zip(labels, values)],
              loc="center left", bbox_to_anchor=(1.0, 0.5), frameon=False, fontsize=8)
    ax.set_title("Immune-state composition", fontsize=12, fontweight="bold", color=NAVY, pad=10)
    ax.axis("equal")
    return _save_figure(fig, path)


def _make_score_chart(data: dict[str, Any], path: Path) -> Path | None:
    items = []
    for name, value in data.items():
        try:
            items.append((_safe_text(name).replace("_", " ").title(), float(value.get("mean", 0))))
        except (TypeError, ValueError):
            pass
    if not items:
        return None
    items.sort(key=lambda x: x[1])
    fig, ax = plt.subplots(figsize=(6.5, 3.8), dpi=180)
    ax.barh([x[0] for x in items], [x[1] for x in items], color=TEAL, alpha=0.9)
    ax.set_title("Mean immune activity scores", fontsize=12, fontweight="bold", color=NAVY, pad=10)
    ax.set_xlabel("Mean score", fontsize=8, color=MUTED)
    ax.tick_params(axis="both", labelsize=8, colors=MUTED)
    ax.grid(axis="x", alpha=0.18)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_visible(False)
    return _save_figure(fig, path)


def _make_shap_chart(features: list[dict[str, Any]], path: Path) -> Path | None:
    values = []
    for feature in features:
        try:
            values.append((_safe_text(feature.get("feature")), float(feature.get("mean_absolute_shap", 0))))
        except (TypeError, ValueError):
            pass
    if not values:
        return None
    values = sorted(values, key=lambda x: x[1], reverse=True)[:12]
    values.reverse()
    fig, ax = plt.subplots(figsize=(6.7, 4.7), dpi=180)
    ax.barh([x[0] for x in values], [x[1] for x in values], color=BLUE, alpha=0.9)
    ax.set_title("Top XAI features by mean absolute SHAP", fontsize=12, fontweight="bold", color=NAVY, pad=10)
    ax.set_xlabel("Mean absolute SHAP", fontsize=8, color=MUTED)
    ax.tick_params(axis="both", labelsize=7.5, colors=MUTED)
    ax.grid(axis="x", alpha=0.18)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_visible(False)
    return _save_figure(fig, path)


def _make_pathway_chart(data: dict[str, Any], path: Path) -> Path | None:
    items = []
    for name, value in data.items():
        try:
            items.append((_safe_text(name).replace("_", " ").title(), float(value.get("mean", 0))))
        except (TypeError, ValueError):
            pass
    if not items:
        return None
    items.sort(key=lambda x: x[1])
    fig, ax = plt.subplots(figsize=(6.7, 3.8), dpi=180)
    ax.barh([x[0] for x in items], [x[1] for x in items], color=ORANGE, alpha=0.9)
    ax.axvline(0, color="#9AA4B2", linewidth=0.8)
    ax.set_title("Mean pathway scores", fontsize=12, fontweight="bold", color=NAVY, pad=10)
    ax.set_xlabel("Mean score", fontsize=8, color=MUTED)
    ax.tick_params(axis="both", labelsize=8, colors=MUTED)
    ax.grid(axis="x", alpha=0.18)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_visible(False)
    return _save_figure(fig, path)


def _make_cluster_chart(data: dict[str, Any], path: Path) -> Path | None:
    rows = []
    state_names = set()
    for value in data.values():
        distribution = value.get("state_distribution") or {}
        if distribution:
            rows.append((int(value.get("cluster", 0)), distribution))
            state_names.update(distribution.keys())
    if not rows:
        return None
    rows.sort()
    states = sorted(state_names)
    x = np.arange(len(rows))
    bottom = np.zeros(len(rows))
    fig, ax = plt.subplots(figsize=(6.7, 4.0), dpi=180)
    palette = [TEAL, BLUE, ORANGE, PURPLE, RED, "#7B8794"]
    for idx, state in enumerate(states):
        vals = np.array([float(dist.get(state, 0)) for _, dist in rows])
        ax.bar(x, vals, bottom=bottom, label=_safe_text(state),
               color=palette[idx % len(palette)], width=0.72)
        bottom += vals
    ax.set_title("Cell-state composition by cluster", fontsize=12, fontweight="bold", color=NAVY, pad=10)
    ax.set_xlabel("Cluster", fontsize=8, color=MUTED)
    ax.set_ylabel("Cells", fontsize=8, color=MUTED)
    ax.set_xticks(x, [str(cluster) for cluster, _ in rows])
    ax.tick_params(axis="both", labelsize=8, colors=MUTED)
    ax.grid(axis="y", alpha=0.18)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=6.5, loc="upper left", bbox_to_anchor=(1.01, 1))
    for spine in ax.spines.values():
        spine.set_visible(False)
    return _save_figure(fig, path)


def _make_umap_chart(analysis_dir: Path, path: Path) -> Path | None:
    umap_path = analysis_dir / "umap" / "umap_coordinates.npy"
    cluster_path = analysis_dir / "clustering" / "cluster_labels.npy"
    if not umap_path.exists() or not cluster_path.exists():
        return None
    try:
        embedding = np.load(umap_path)
        clusters = np.load(cluster_path)
    except Exception:
        return None
    if embedding.ndim != 2 or embedding.shape[1] < 2 or clusters.ndim != 1 or clusters.shape[0] != embedding.shape[0]:
        return None
    n = embedding.shape[0]
    indices = np.linspace(0, n - 1, 12000, dtype=int) if n > 12000 else np.arange(n)
    x, y, c = embedding[indices, 0], embedding[indices, 1], clusters[indices]
    fig, ax = plt.subplots(figsize=(7.0, 5.0), dpi=180)
    unique = sorted(set(int(v) for v in c))
    cmap = plt.get_cmap("tab20", max(1, len(unique)))
    for idx, cluster in enumerate(unique):
        mask = c == cluster
        ax.scatter(x[mask], y[mask], s=7, alpha=0.55, color=cmap(idx),
                   label=f"Cluster {cluster}", linewidths=0)
    ax.set_title(f"UMAP projection by cluster ({len(indices):,} plotted cells)",
                 fontsize=12, fontweight="bold", color=NAVY, pad=10)
    ax.set_xlabel("UMAP 1", fontsize=8, color=MUTED)
    ax.set_ylabel("UMAP 2", fontsize=8, color=MUTED)
    ax.tick_params(labelsize=7, colors=MUTED)
    ax.grid(alpha=0.12)
    ax.legend(frameon=False, fontsize=6.5, markerscale=2,
              loc="upper left", bbox_to_anchor=(1.01, 1))
    for spine in ax.spines.values():
        spine.set_visible(False)
    return _save_figure(fig, path)


def _markdown_story(text: str, styles: dict[str, ParagraphStyle]) -> list[Any]:
    story: list[Any] = []
    lines = text.replace("\r\n", "\n").split("\n")
    i = 0
    while i < len(lines):
        raw = lines[i].strip()
        if not raw:
            i += 1
            continue

        if "|" in raw and i + 1 < len(lines) and "|" in lines[i + 1] and re.search(r"-{2,}", lines[i + 1]):
            header = [_clean_markdown(x.strip()) for x in raw.strip("|").split("|")]
            rows = [header]
            i += 2
            while i < len(lines) and "|" in lines[i]:
                row = [_clean_markdown(x.strip()) for x in lines[i].strip().strip("|").split("|")]
                if len(row) == len(header):
                    rows.append(row)
                i += 1
            if len(rows) > 1:
                story.append(_table(rows, [170 * mm / len(header)] * len(header), styles))
                story.append(Spacer(1, 2 * mm))
            continue

        heading = re.match(r"^#{1,6}\s+(.*)$", raw)
        bold_number = re.match(r"^\*\*\s*(\d+)\.\s*(.*?)\*\*$", raw)
        if heading:
            story.append(_p(_clean_markdown(heading.group(1)), styles["subsection"]))
        elif bold_number:
            story.append(_p(_clean_markdown(bold_number.group(2)), styles["subsection"]))
        elif raw.startswith("- ") or raw.startswith("* "):
            story.append(_p(f"- {_clean_markdown(raw)}", styles["body"]))
        else:
            story.append(_p(_clean_markdown(raw), styles["body"]))
        i += 1
    return story


def _footer(canvas, doc) -> None:
    canvas.saveState()
    width, _ = A4
    canvas.setStrokeColor(colors.HexColor(MID))
    canvas.line(18 * mm, 13 * mm, width - 18 * mm, 13 * mm)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor(MUTED))
    canvas.drawString(18 * mm, 8 * mm, "IMMUNO-XAI | Explainable single-cell analysis")
    canvas.drawRightString(width - 18 * mm, 8 * mm, f"Page {doc.page}")
    canvas.restoreState()


def generate_analysis_report(
    *,
    job_id: str,
    analysis_dir: str | Path,
    output_path: str | Path | None = None,
    dataset_name: str | None = None,
) -> Path:
    analysis_dir = Path(analysis_dir)
    final_path = analysis_dir / "final_analysis" / "final_analysis.json"
    interpretation_path = analysis_dir / "llm_reasoning" / "biological_interpretation.json"
    manifest_path = analysis_dir / "analysis_run_manifest.json"

    final_analysis = _load_json(final_path)
    interpretation = _load_json(interpretation_path) if interpretation_path.exists() else {}
    manifest = _load_json(manifest_path) if manifest_path.exists() else {}

    if output_path is None:
        output_path = analysis_dir / f"IMMUNO_XAI_Report_{job_id}.pdf"
    else:
        output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    styles = _styles()
    assets = analysis_dir / "report_assets"
    assets.mkdir(parents=True, exist_ok=True)

    state_summary = final_analysis.get("immune_state_summary") or {}
    score_summary = final_analysis.get("immune_score_summary") or {}
    cluster_summary = final_analysis.get("cluster_summary") or {}
    pathway_summary = final_analysis.get("pathway_summary") or {}
    xai_summary = final_analysis.get("xai_summary") or {}
    features = xai_summary.get("features") or []
    ml = final_analysis.get("ml_summary") or {}

    charts = {
        "states": _make_state_chart(state_summary, assets / "immune_states.png"),
        "scores": _make_score_chart(score_summary, assets / "immune_scores.png"),
        "shap": _make_shap_chart(features, assets / "shap_features.png"),
        "pathways": _make_pathway_chart(pathway_summary, assets / "pathways.png"),
        "clusters": _make_cluster_chart(cluster_summary, assets / "cluster_composition.png"),
        "umap": _make_umap_chart(analysis_dir, assets / "umap.png"),
    }

    dataset_value = dataset_name or manifest.get("dataset") or "Not available"
    total_cells = int(final_analysis.get("input_cells", 0) or 0)
    cluster_count = len(cluster_summary)
    prediction_count = int(ml.get("prediction_count", 0) or 0)

    story: list[Any] = [
        Spacer(1, 10 * mm),
        _p("IMMUNO-XAI", styles["title"]),
        _p("Explainable single-cell immune-state analysis report", styles["subtitle"]),
    ]

    cards = Table(
        [[
            _card("Input cells", f"{total_cells:,}", styles),
            _card("Clusters", f"{cluster_count:,}", styles),
            _card("ML predictions", f"{prediction_count:,}", styles),
        ]],
        colWidths=[55 * mm, 55 * mm, 55 * mm],
    )
    cards.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.extend([cards, Spacer(1, 7 * mm)])

    metadata = [
        ["Dataset", dataset_value],
        ["Job ID", job_id],
        ["Pipeline", final_analysis.get("pipeline", "IMMUNO-XAI")],
        ["Purpose", final_analysis.get("purpose", "Integrated immune-state analysis and biological reasoning.")],
        ["Generated", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")],
    ]
    story.append(_table(metadata, [35 * mm, 135 * mm], styles, header=False))

    story.append(_section("Executive overview", styles))
    if charts["states"]:
        story.append(Image(str(charts["states"]), width=150 * mm, height=76 * mm))

    if state_summary:
        dominant = max(state_summary.items(), key=lambda item: item[1].get("cell_count", 0))
        story.append(_p(
            f"The largest reported immune-state category is {_safe_text(dominant[0])}, "
            f"representing {int(dominant[1].get('cell_count', 0)):,} cells "
            f"({_percent(dominant[1].get('fraction'))}). All QC-retained cells remain "
            "part of the quantitative analysis.",
            styles["body"],
        ))

    story.append(PageBreak())

    story.append(_section("1. Immune-state analysis", styles))
    state_rows = [["Immune state", "Cells", "Fraction", "Mean confidence"]]
    for state, data in sorted(state_summary.items(), key=lambda item: item[1].get("cell_count", 0), reverse=True):
        state_rows.append([
            state,
            f"{int(data.get('cell_count', 0)):,}",
            _percent(data.get("fraction")),
            _percent(data.get("mean_confidence")),
        ])
    if len(state_rows) > 1:
        story.append(_table(state_rows, [65 * mm, 30 * mm, 35 * mm, 40 * mm], styles))

    story.append(_section("2. Immune activity scores", styles))
    if charts["scores"]:
        story.append(Image(str(charts["scores"]), width=155 * mm, height=88 * mm))
    score_rows = [["Score", "Mean", "Median", "Std", "Min", "Max"]]
    for name, data in score_summary.items():
        score_rows.append([
            _safe_text(name).replace("_", " ").title(),
            _number(data.get("mean")), _number(data.get("median")),
            _number(data.get("std")), _number(data.get("min")), _number(data.get("max")),
        ])
    if len(score_rows) > 1:
        story.append(_table(score_rows, [49 * mm, 24 * mm, 24 * mm, 24 * mm, 24 * mm, 25 * mm], styles))

    story.append(PageBreak())

    story.append(_section("3. Cluster analysis and UMAP", styles))
    story.append(_p(
        f"The analysis contains {cluster_count:,} clusters. The UMAP figure is an exploratory "
        "two-dimensional view of the cell representation, with points colored by cluster.",
        styles["body"],
    ))
    if charts["umap"]:
        story.append(Image(str(charts["umap"]), width=155 * mm, height=111 * mm))
        story.append(_p(
            "UMAP is shown for visualization of cell structure and cluster organization. "
            "For datasets larger than 12,000 cells, the displayed points are a deterministic sample; "
            "the underlying pipeline still analyzes the full retained dataset.",
            styles["small"],
        ))
    if charts["clusters"]:
        story.append(Spacer(1, 4 * mm))
        story.append(Image(str(charts["clusters"]), width=155 * mm, height=86 * mm))

    story.append(PageBreak())

    cluster_rows = [["Cluster", "Cells", "Dominant state", "Fraction", "Mean confidence"]]
    for cluster in sorted(cluster_summary.values(), key=lambda item: item.get("cluster", 0)):
        cluster_rows.append([
            str(cluster.get("cluster", "-")),
            f"{int(cluster.get('n_cells', 0)):,}",
            cluster.get("dominant_state", "Not available"),
            _percent(cluster.get("dominant_state_fraction")),
            _percent(cluster.get("mean_cell_confidence")),
        ])
    story.append(_section("4. Cluster summary", styles))
    if len(cluster_rows) > 1:
        story.append(_table(cluster_rows, [22 * mm, 28 * mm, 56 * mm, 32 * mm, 32 * mm], styles))

    story.append(_section("5. Pathway analysis", styles))
    if charts["pathways"]:
        story.append(Image(str(charts["pathways"]), width=155 * mm, height=86 * mm))
    pathway_rows = [["Pathway", "Mean", "Median", "Std"]]
    for name, data in pathway_summary.items():
        pathway_rows.append([
            _safe_text(name).replace("_", " ").title(),
            _number(data.get("mean")), _number(data.get("median")), _number(data.get("std")),
        ])
    if len(pathway_rows) > 1:
        story.append(_table(pathway_rows, [85 * mm, 28 * mm, 28 * mm, 29 * mm], styles))

    story.append(PageBreak())

    story.append(_section("6. Machine-learning analysis", styles))
    ml_rows = [
        ["Metric", "Value"],
        ["Prediction count", f"{prediction_count:,}"],
        ["Target source", ml.get("target_source", "immune_state")],
    ]
    distribution = ml.get("class_distribution") or {}
    if distribution:
        ml_rows.append(["Class distribution", "; ".join(
            f"{_safe_text(key)}: {int(value):,}" for key, value in distribution.items()
        )])
    if ml.get("target_fallback_reason"):
        ml_rows.append(["Technical fallback", ml.get("target_fallback_reason")])
    story.append(_table(ml_rows, [45 * mm, 125 * mm], styles))

    story.append(_section("7. Explainable AI feature importance", styles))
    if charts["shap"]:
        story.append(Image(str(charts["shap"]), width=155 * mm, height=104 * mm))
    feature_rows = [["Feature", "Mean absolute SHAP"]]
    for feature in features:
        feature_rows.append([feature.get("feature", "Not available"), _number(feature.get("mean_absolute_shap"))])
    if len(feature_rows) > 1:
        story.append(_table(feature_rows, [125 * mm, 45 * mm], styles))
    story.append(_p(
        "SHAP values describe the contribution of features to model predictions; they are not evidence of biological causation.",
        styles["small"],
    ))

    story.append(PageBreak())

    story.append(_section("8. Biological interpretation", styles))
    reasoning = interpretation.get("reasoning") or final_analysis.get("biological_interpretation", {}).get("reasoning") or ""
    if reasoning:
        story.extend(_markdown_story(str(reasoning), styles))
    else:
        story.append(_p("No biological interpretation was returned by the reasoning layer.", styles["body"]))

    story.append(_section("9. Interpretation notes", styles))
    for note in [
        "This report summarizes computational results produced by the IMMUNO-XAI pipeline.",
        "Unclassified cells remain part of the quantitative analysis; the label does not mean that cells were removed.",
        "When immune-state labels do not provide enough usable classes for supervised learning, cluster labels may be used as a technical ML target fallback. The target source is reported above.",
        "Model feature importance reflects predictive contribution and does not establish biological causality, clinical diagnosis, treatment response, or experimental validation.",
        "UMAP is included for exploratory visualization of cell structure and cluster organization.",
    ]:
        story.append(_p(f"- {note}", styles["body"]))

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=18 * mm,
        title="IMMUNO-XAI Analysis Report",
        author="IMMUNO-XAI",
        subject="Explainable single-cell immune-state analysis",
    )
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return Path(output_path)
