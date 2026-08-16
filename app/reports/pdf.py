from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.core.exceptions import ReportError

REPORT_TITLE = "LANDLORD MANAGEMENT SYSTEM"

_HEADER_COLOR = colors.HexColor("#1F4E79")
_ZEBRA_COLOR = colors.HexColor("#F2F7FB")
_GRID_COLOR = colors.HexColor("#B0B0B0")
_META_COLOR = colors.HexColor("#555555")


def build_story(
    title: str,
    subtitle: str | None,
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
) -> list:
    """Build the PDF flowable story for a report.

    The renderer is intentionally free of business rules: it receives already
    formatted headers and rows (strings) and lays them out on the page.
    """
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        name="ReportTitle", parent=styles["Title"], fontSize=18, spaceAfter=2, textColor=_HEADER_COLOR
    )
    report_name_style = ParagraphStyle(
        name="ReportName", parent=styles["Heading2"], fontSize=13, spaceAfter=2, textColor=_HEADER_COLOR
    )
    meta_style = ParagraphStyle(name="ReportMeta", parent=styles["Normal"], fontSize=9, leading=11, textColor=_META_COLOR)
    header_cell_style = ParagraphStyle(
        name="ReportHeaderCell", parent=styles["Normal"], fontSize=9, leading=11, textColor=colors.white,
        fontName="Helvetica-Bold",
    )
    cell_style = ParagraphStyle(name="ReportCell", parent=styles["Normal"], fontSize=9, leading=11)

    story: list = [Paragraph(REPORT_TITLE, title_style), Paragraph(title, report_name_style), Spacer(1, 2)]
    if subtitle:
        story.append(Paragraph(subtitle, meta_style))
    story.append(Paragraph(f"Generated: {date.today().isoformat()}", meta_style))
    story.append(Spacer(1, 8))

    data: list[list[Paragraph]] = [[Paragraph(str(header), header_cell_style) for header in headers]]
    for row in rows:
        data.append([Paragraph(str(cell), cell_style) for cell in row])

    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), _HEADER_COLOR),
                ("GRID", (0, 0), (-1, -1), 0.5, _GRID_COLOR),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _ZEBRA_COLOR]),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(table)
    return story


def write_pdf(
    path: str | Path,
    title: str,
    subtitle: str | None,
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
) -> Path:
    """Write a report PDF to ``path`` and return the written path."""
    target = Path(path)
    try:
        doc = SimpleDocTemplate(
            str(target),
            pagesize=A4,
            rightMargin=15 * mm,
            leftMargin=15 * mm,
            topMargin=15 * mm,
            bottomMargin=15 * mm,
            title=title,
            author=REPORT_TITLE,
        )
        doc.build(build_story(title, subtitle, headers, rows))
    except OSError as exc:
        raise ReportError(f"Could not write PDF file {target}: {exc}") from exc
    return target
