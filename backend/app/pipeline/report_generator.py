from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
    PageBreak,
)


def _load_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"Required report file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _safe_text(value: Any) -> str:
    if value is None:
        return "Not available"
    text = str(value)
    text = re.sub(r"\\s+", " ", text).strip()
    return text or "Not available"


def _label(value: Any) -> str:
    text = _safe_text(value)
    return text.replace("_", " ").strip().title()


def _number(value: Any, digits: int = 4) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return "—"


def _percent(value: Any, digits: int = 1) -> str:
    try:
        return f"{float(value) * 100:.{digits}f}%"
    except (TypeError, ValueError):
        return "—"


def _paragraph(text: Any, style: ParagraphStyle) -> Paragraph:
    escaped = (
        _safe_text(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    return Paragraph(escaped, style)


def _section_title(text: str, styles: dict[str, ParagraphStyle]) -> Paragraph:
    return Paragraph(text, styles["Section"])


def _table(
    rows: list[list[Any]],
    widths: list[float] | None = None,
    header: bool = True,
) -> Table:
    converted: list[list[Any]] = []
    for row_index, row in enumerate(rows):
        converted_row: list[Any] = []
        for value in row:
            if isinstance(value, Paragraph):
                converted_row.append(value)
            else:
                converted_row.append(str(value))
        converted.append(converted_row)

    table = Table(
        converted,
        colWidths=widths,
        repeatRows=1 if header else 0,
        hAlign="LEFT",
    )

    style = [
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("LEADING", (0, 0), (-1, -1), 11),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d9dee7")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]

    if header:
        style.extend(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2f7")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
            ]
        )

    table.setStyle(TableStyle(style))
    return table


def _footer(canvas, doc) -> None:
    canvas.saveState()
    width, _ = A4
    canvas.setStrokeColor(colors.HexColor("#d9dee7"))
    canvas.line(18 * mm, 14 * mm, width - 18 * mm, 14 * mm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#6b7280"))
    canvas.drawString(18 * mm, 9 * mm, "IMMUNO-XAI Analysis Report")
    canvas.drawRightString(
        width - 18 * mm,
        9 * mm,
        f"Page {doc.page}",
    )
    canvas.restoreState()


def generate_analysis_report(
    *,
    job_id: str,
    analysis_dir: str | Path,
    output_path: str | Path | None = None,
    dataset_name: str | None = None,
) -> Path:
    """
    Generate a PDF report from the persisted IMMUNO-XAI outputs.

    The report is generated on demand, so it always reflects the
    completed analysis currently stored for the requested job.
    """

    analysis_dir = Path(analysis_dir)

    final_path = analysis_dir / "final_analysis" / "final_analysis.json"
    interpretation_path = (
        analysis_dir
        / "llm_reasoning"
        / "biological_interpretation.json"
    )
    manifest_path = analysis_dir / "analysis_run_manifest.json"

    final_analysis = _load_json(final_path)

    interpretation: dict[str, Any] = {}
    if interpretation_path.exists():
        loaded = _load_json(interpretation_path)
        if isinstance(loaded, dict):
            interpretation = loaded

    manifest: dict[str, Any] = {}
    if manifest_path.exists():
        loaded = _load_json(manifest_path)
        if isinstance(loaded, dict):
            manifest = loaded

    if output_path is None:
        output_path = (
            analysis_dir
            / f"IMMUNO_XAI_Report_{job_id}.pdf"
        )
    else:
        output_path = Path(output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    styles = getSampleStyleSheet()
    styles["Title"].fontName = "Helvetica-Bold"
    styles["Title"].fontSize = 22
    styles["Title"].leading = 26
    styles["Title"].alignment = TA_CENTER
    styles["Title"].textColor = colors.HexColor("#111827")

    styles.add(
        ParagraphStyle(
            name="SubtitleCustom",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#6b7280"),
            spaceAfter=14,
        )
    )

    styles.add(
        ParagraphStyle(
            name="Section",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#111827"),
            spaceBefore=12,
            spaceAfter=7,
        )
    )

    styles.add(
        ParagraphStyle(
            name="BodyCustom",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#374151"),
            spaceAfter=6,
        )
    )

    styles.add(
        ParagraphStyle(
            name="SmallCustom",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#6b7280"),
        )
    )

    styles.add(
        ParagraphStyle(
            name="TableCell",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#374151"),
        )
    )

    story: list[Any] = []

    story.append(Spacer(1, 12 * mm))
    story.append(Paragraph("IMMUNO-XAI Analysis Report", styles["Title"]))
    story.append(
        Paragraph(
            "Explainable single-cell immune-state analysis",
            styles["SubtitleCustom"],
        )
    )

    created_at = datetime.now(timezone.utc).strftime(
        "%Y-%m-%d %H:%M UTC"
    )

    metadata_rows = [
        ["Report field", "Value"],
        ["Job ID", _safe_text(job_id)],
        ["Pipeline", _safe_text(final_analysis.get("pipeline", "IMMUNO-XAI"))],
        ["Purpose", _safe_text(final_analysis.get("purpose"))],
        ["Input cells", f"{int(final_analysis.get('input_cells', 0)):,}"],
        [
            "Report generated",
            created_at,
        ],
    ]

    dataset_value = dataset_name or manifest.get("dataset")
    if dataset_value:
        metadata_rows.append(["Dataset", _safe_text(dataset_value)])

    story.append(_table(metadata_rows, widths=[42 * mm, 128 * mm]))
    story.append(Spacer(1, 4 * mm))

    # ---------------------------------------------------------
    # Executive summary
    # ---------------------------------------------------------
    story.append(_section_title("1. Analysis Summary", styles))

    state_summary = final_analysis.get("immune_state_summary") or {}
    if state_summary:
        state_rows = [["Immune state", "Cells", "Fraction", "Mean confidence"]]
        for state, data in sorted(
            state_summary.items(),
            key=lambda item: item[1].get("cell_count", 0),
            reverse=True,
        ):
            state_rows.append(
                [
                    _safe_text(state),
                    f"{int(data.get('cell_count', 0)):,}",
                    _percent(data.get("fraction")),
                    _percent(data.get("mean_confidence")),
                ]
            )
        story.append(_table(state_rows, widths=[65 * mm, 30 * mm, 35 * mm, 40 * mm]))
    else:
        story.append(_paragraph("No immune-state summary was available.", styles["BodyCustom"]))

    # ---------------------------------------------------------
    # Immune scores
    # ---------------------------------------------------------
    story.append(_section_title("2. Immune Score Summary", styles))

    score_summary = final_analysis.get("immune_score_summary") or {}
    if score_summary:
        score_rows = [["Score", "Mean", "Median", "Std", "Minimum", "Maximum"]]
        for name, data in score_summary.items():
            score_rows.append(
                [
                    _label(name),
                    _number(data.get("mean")),
                    _number(data.get("median")),
                    _number(data.get("std")),
                    _number(data.get("min")),
                    _number(data.get("max")),
                ]
            )
        story.append(
            _table(
                score_rows,
                widths=[49 * mm, 25 * mm, 25 * mm, 25 * mm, 25 * mm, 25 * mm],
            )
        )
    else:
        story.append(_paragraph("No immune-score summary was available.", styles["BodyCustom"]))

    # ---------------------------------------------------------
    # Cluster summary
    # ---------------------------------------------------------
    story.append(_section_title("3. Cluster Summary", styles))

    clusters = final_analysis.get("cluster_summary") or {}
    if clusters:
        cluster_rows = [
            [
                "Cluster",
                "Cells",
                "Dominant state",
                "Fraction",
                "Mean confidence",
            ]
        ]
        ordered_clusters = sorted(
            clusters.values(),
            key=lambda item: item.get("cluster", 0),
        )
        for cluster in ordered_clusters:
            cluster_rows.append(
                [
                    str(cluster.get("cluster", "—")),
                    f"{int(cluster.get('n_cells', 0)):,}",
                    _safe_text(cluster.get("dominant_state")),
                    _percent(cluster.get("dominant_state_fraction")),
                    _percent(cluster.get("mean_cell_confidence")),
                ]
            )
        story.append(
            _table(
                cluster_rows,
                widths=[22 * mm, 27 * mm, 55 * mm, 34 * mm, 36 * mm],
            )
        )
    else:
        story.append(_paragraph("No cluster summary was available.", styles["BodyCustom"]))

    # ---------------------------------------------------------
    # Pathway summary
    # ---------------------------------------------------------
    story.append(_section_title("4. Pathway Summary", styles))

    pathways = final_analysis.get("pathway_summary") or {}
    if pathways:
        pathway_rows = [["Pathway", "Mean", "Median", "Std"]]
        for name, data in pathways.items():
            pathway_rows.append(
                [
                    _label(name),
                    _number(data.get("mean")),
                    _number(data.get("median")),
                    _number(data.get("std")),
                ]
            )
        story.append(
            _table(
                pathway_rows,
                widths=[84 * mm, 30 * mm, 30 * mm, 30 * mm],
            )
        )
    else:
        story.append(_paragraph("No pathway summary was available.", styles["BodyCustom"]))

    # ---------------------------------------------------------
    # Machine learning
    # ---------------------------------------------------------
    story.append(_section_title("5. Machine Learning Summary", styles))

    ml = final_analysis.get("ml_summary") or {}
    if ml:
        target_source = ml.get("target_source", "immune_state")
        ml_rows = [
            ["Metric", "Value"],
            ["Prediction count", f"{int(ml.get('prediction_count', 0)):,}"],
            ["Target source", _safe_text(target_source)],
        ]

        if ml.get("target_fallback_reason"):
            ml_rows.append(
                [
                    "Fallback reason",
                    _safe_text(ml.get("target_fallback_reason")),
                ]
            )

        distribution = ml.get("class_distribution") or {}
        if distribution:
            distribution_text = "; ".join(
                f"{_safe_text(key)}: {int(value):,}"
                for key, value in distribution.items()
            )
            ml_rows.append(["Class distribution", distribution_text])

        story.append(_table(ml_rows, widths=[48 * mm, 122 * mm]))
    else:
        story.append(_paragraph("No machine-learning summary was available.", styles["BodyCustom"]))

    # ---------------------------------------------------------
    # XAI
    # ---------------------------------------------------------
    story.append(_section_title("6. Explainable AI Feature Importance", styles))

    xai = final_analysis.get("xai_summary") or {}
    features = xai.get("features") or []

    if features:
        feature_rows = [["Feature", "Mean absolute SHAP"]]
        for feature in features:
            feature_rows.append(
                [
                    _safe_text(feature.get("feature")),
                    _number(feature.get("mean_absolute_shap")),
                ]
            )
        story.append(
            _table(
                feature_rows,
                widths=[125 * mm, 45 * mm],
            )
        )

        story.append(
            Spacer(1, 2 * mm)
        )
        story.append(
            _paragraph(
                "SHAP feature importance describes the contribution of model features to predictions. "
                "It should not be interpreted as proof of biological causation.",
                styles["SmallCustom"],
            )
        )
    else:
        story.append(_paragraph("No XAI feature-importance results were available.", styles["BodyCustom"]))

    # ---------------------------------------------------------
    # Biological reasoning
    # ---------------------------------------------------------
    story.append(_section_title("7. Biological Interpretation", styles))

    reasoning = (
        interpretation.get("reasoning")
        or final_analysis.get("biological_interpretation", {}).get("reasoning")
        or ""
    )

    if reasoning:
        for block in str(reasoning).split("\n"):
            if block.strip():
                story.append(_paragraph(block, styles["BodyCustom"]))
    else:
        story.append(
            _paragraph(
                "No biological interpretation was returned by the reasoning layer.",
                styles["BodyCustom"],
            )
        )

    # ---------------------------------------------------------
    # Methodological note
    # ---------------------------------------------------------
    story.append(_section_title("8. Interpretation Notes", styles))
    notes = [
        "This report summarizes computational results produced by the IMMUNO-XAI pipeline.",
        "Immune-state labels are evidence-aware assignments and may be reported as Unclassified when the available score pattern does not support a specific state.",
        "Unclassified cells are still part of the quantitative analysis; the label does not mean that the cells were removed from the dataset.",
        "When biological immune-state labels do not provide at least two usable classes, the machine-learning stage may use cluster labels as a technical fallback. The ML target source is reported above.",
        "Model-derived feature importance indicates predictive contribution and does not establish biological causality, clinical diagnosis, treatment response, or experimental validation.",
    ]

    for note in notes:
        story.append(
            _paragraph(f"• {note}", styles["BodyCustom"])
        )

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=17 * mm,
        bottomMargin=19 * mm,
        title="IMMUNO-XAI Analysis Report",
        author="IMMUNO-XAI",
        subject="Single-cell immune-state analysis report",
    )

    doc.build(
        story,
        onFirstPage=_footer,
        onLaterPages=_footer,
    )

    return Path(output_path)
