"""PDF export service — generates downloadable ATS match reports and AI feedback summaries.

Uses ReportLab to format match scores, section ratings, skill gap analyses,
and AI-generated improvement recommendations into a high-quality PDF document.
"""

from io import BytesIO
from datetime import datetime
import logging
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)

from app.models.match import MatchResult
from app.models.resume import Resume
from app.models.job import JobDescription

logger = logging.getLogger(__name__)


def generate_match_report_pdf(
    match: MatchResult,
    resume: Resume,
    job: JobDescription,
) -> bytes:
    """Generate a PDF report for a completed resume-job match.

    Args:
        match: MatchResult database model instance.
        resume: Associated Resume model instance.
        job: Associated JobDescription model instance.

    Returns:
        bytes: Raw PDF file bytes ready for download/streaming.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()
    primary_color = colors.HexColor("#1E3A8A")  # Deep blue
    accent_color = colors.HexColor("#2563EB")   # Bright blue
    success_color = colors.HexColor("#059669")  # Green
    warning_color = colors.HexColor("#D97706")  # Amber
    danger_color = colors.HexColor("#DC2626")   # Red
    dark_gray = colors.HexColor("#1F2937")
    light_bg = colors.HexColor("#F3F4F6")

    # Custom typography styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=26,
        textColor=primary_color,
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#4B5563"),
    )
    heading_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=primary_color,
        spaceBefore=12,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "BodyDark",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=dark_gray,
    )
    bullet_style = ParagraphStyle(
        "BulletText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13.5,
        textColor=dark_gray,
        leftIndent=12,
        spaceAfter=3,
    )

    elements = []

    # ── 1. Document Header ──
    elements.append(Paragraph("AI Resume & Job Matcher — Assessment Report", title_style))
    elements.append(Spacer(1, 4))
    match_date = match.created_at.strftime("%B %d, %Y at %H:%M UTC") if match.created_at else datetime.utcnow().strftime("%B %d, %Y")
    elements.append(Paragraph(f"Generated on {match_date} • Match ID #{match.id}", subtitle_style))
    elements.append(Spacer(1, 10))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=accent_color, spaceAfter=15))

    # ── 2. Candidate & Job Target Overview ──
    info_data = [
        [
            Paragraph("<b>Target Role:</b>", body_style),
            Paragraph(job.title or "Position Not Specified", body_style),
            Paragraph("<b>Candidate File:</b>", body_style),
            Paragraph(resume.file_name or f"Resume #{resume.id}", body_style),
        ],
        [
            Paragraph("<b>Company:</b>", body_style),
            Paragraph(job.company or "Company Not Specified", body_style),
            Paragraph("<b>Status:</b>", body_style),
            Paragraph("Evaluation Completed", body_style),
        ],
    ]
    info_table = Table(info_data, colWidths=[90, 175, 95, 170])
    info_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), light_bg),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
                ("PADDING", (0, 0), (-1, -1), 6),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    elements.append(info_table)
    elements.append(Spacer(1, 15))

    # ── 3. Score Summary Banner ──
    overall = match.overall_score or 0.0
    semantic = match.similarity_score or 0.0
    keyword = match.keyword_score or 0.0

    score_color = success_color if overall >= 75.0 else (warning_color if overall >= 50.0 else danger_color)

    score_card_data = [
        [
            Paragraph("<font size='10'><b>OVERALL MATCH SCORE</b></font>", ParagraphStyle("H", alignment=1, textColor=colors.HexColor("#4B5563"))),
            Paragraph("<font size='10'><b>SEMANTIC SIMILARITY</b></font>", ParagraphStyle("H", alignment=1, textColor=colors.HexColor("#4B5563"))),
            Paragraph("<font size='10'><b>KEYWORD OVERLAP</b></font>", ParagraphStyle("H", alignment=1, textColor=colors.HexColor("#4B5563"))),
        ],
        [
            Paragraph(f"<font size='26' color='{score_color.hexval()}'><b>{overall:.1f}%</b></font>", ParagraphStyle("S1", alignment=1)),
            Paragraph(f"<font size='22' color='{primary_color.hexval()}'><b>{semantic:.1f}%</b></font>", ParagraphStyle("S2", alignment=1)),
            Paragraph(f"<font size='22' color='{accent_color.hexval()}'><b>{keyword:.1f}%</b></font>", ParagraphStyle("S3", alignment=1)),
        ],
        [
            Paragraph("<font size='8' color='#6B7280'>60% Semantic + 40% Keyword</font>", ParagraphStyle("C1", alignment=1)),
            Paragraph("<font size='8' color='#6B7280'>Sentence-Transformers</font>", ParagraphStyle("C2", alignment=1)),
            Paragraph("<font size='8' color='#6B7280'>Direct Skill Overlap</font>", ParagraphStyle("C3", alignment=1)),
        ],
    ]
    score_table = Table(score_card_data, colWidths=[176, 177, 177])
    score_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ]
        )
    )
    elements.append(score_table)
    elements.append(Spacer(1, 15))

    # ── 4. Section-Level Breakdown ──
    if match.section_scores:
        elements.append(Paragraph("Section-Level Breakdown", heading_style))
        section_rows = [
            [
                Paragraph("<b>Evaluation Dimension</b>", body_style),
                Paragraph("<b>Score</b>", body_style),
                Paragraph("<b>Assessment</b>", body_style),
            ]
        ]
        for key, val in match.section_scores.items():
            formatted_name = key.replace("_", " ").title()
            val_pct = f"{float(val):.1f}%"
            rating = "Strong Match" if val >= 75 else ("Moderate Match" if val >= 50 else "Opportunity for Growth")
            section_rows.append([
                Paragraph(formatted_name, body_style),
                Paragraph(val_pct, body_style),
                Paragraph(rating, body_style),
            ])

        sec_table = Table(section_rows, colWidths=[180, 100, 250])
        sec_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                    ("PADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        elements.append(sec_table)
        elements.append(Spacer(1, 15))

    # ── 5. Skills Gap Analysis ──
    elements.append(Paragraph("Skills & Gap Analysis", heading_style))

    resume_skills = set(resume.parsed_skills or [])
    job_skills = set(job.parsed_skills or [])
    matching_skills = sorted(list(resume_skills & job_skills))
    missing_skills = match.missing_keywords or sorted(list(job_skills - resume_skills))

    matched_text = ", ".join(matching_skills) if matching_skills else "No direct matching keywords detected."
    missing_text = ", ".join(missing_skills) if missing_skills else "None! All required skills matched."

    gap_data = [
        [
            Paragraph("<b>Identified Matching Skills:</b>", body_style),
            Paragraph(f"<font color='{success_color.hexval()}'><b>{matched_text}</b></font>", body_style),
        ],
        [
            Paragraph("<b>Missing Required Skills:</b>", body_style),
            Paragraph(f"<font color='{danger_color.hexval()}'><b>{missing_text}</b></font>", body_style),
        ],
    ]
    gap_table = Table(gap_data, colWidths=[160, 370])
    gap_table.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("BACKGROUND", (0, 0), (0, -1), light_bg),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("PADDING", (0, 0), (-1, -1), 6),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    elements.append(gap_table)
    elements.append(Spacer(1, 15))

    # ── 6. AI Recommendations & Bullet Rewrites ──
    if match.ai_feedback:
        elements.append(Paragraph("AI Tailoring & Improvement Suggestions", heading_style))
        import re

        def format_md(t: str) -> str:
            # Escape ampersands
            t = t.replace("&", "&amp;")
            # Convert **bold** to <b>bold</b>
            t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
            # Remove any stray unclosed tags
            if t.count("<b>") > t.count("</b>"):
                t += "</b>"
            elif t.count("</b>") > t.count("<b>"):
                t = "<b>" + t
            return t

        feedback_lines = match.ai_feedback.strip().split("\n")
        for line in feedback_lines:
            line_str = line.strip()
            if not line_str:
                elements.append(Spacer(1, 4))
                continue
            if line_str.startswith("###") or line_str.startswith("##"):
                clean_h = line_str.lstrip("#").strip()
                elements.append(
                    Paragraph(
                        f"<b>{clean_h}</b>",
                        ParagraphStyle(
                            "SubH",
                            fontName="Helvetica-Bold",
                            fontSize=11,
                            leading=15,
                            textColor=primary_color,
                            spaceBefore=6,
                        ),
                    )
                )
            elif line_str.startswith("•") or line_str.startswith("-") or line_str.startswith("*"):
                bullet_content = line_str.lstrip("•-* ").strip()
                formatted_bullet = format_md(bullet_content)
                elements.append(Paragraph(f"• {formatted_bullet}", bullet_style))
            else:
                formatted_line = format_md(line_str)
                elements.append(Paragraph(formatted_line, body_style))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()
