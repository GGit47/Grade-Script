import os
import datetime
from typing import Dict, Any

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


def generate_pdf_report(submission_data: Dict[str, Any], output_path: str) -> str:
    """
    Builds a professional, cleanly styled evaluation PDF report.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    if not REPORTLAB_AVAILABLE:
        # Generate clean text report fallback
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"GRADE SCRIPT EVALUATION REPORT\n")
            f.write(f"Exam: {submission_data.get('exam_title')}\n")
            f.write(f"Student Roll No: {submission_data.get('student_roll_no')}\n")
            f.write(f"Final Score: {submission_data.get('approved_total')} / {submission_data.get('total_max_marks')}\n")
        return output_path

    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Heading1"],
        fontSize=22,
        leading=26,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        "SubTitleStyle",
        parent=styles["Normal"],
        fontSize=11,
        textColor=colors.HexColor("#64748b"),
        spaceAfter=14,
    )
    body_bold = ParagraphStyle("BodyBold", parent=styles["Normal"], fontSize=10, fontName="Helvetica-Bold")
    table_cell = ParagraphStyle("TableCell", parent=styles["Normal"], fontSize=9, leading=12)

    story = []

    # Title Banner
    story.append(Paragraph("Grade Script — Evaluation Report", title_style))
    story.append(Paragraph("Deep Learning-Powered Handwriting & AI-Assisted Assessment", subtitle_style))
    story.append(Spacer(1, 10))

    # Metadata Table
    exam_title = submission_data.get("exam_title", "N/A")
    subject = submission_data.get("subject", "N/A")
    roll_no = submission_data.get("student_roll_no", "N/A")
    eval_date = datetime.datetime.now().strftime("%B %d, %Y - %H:%M")
    approved_total = submission_data.get("approved_total", 0.0)
    max_total = submission_data.get("total_max_marks", 0.0)
    percentage = (approved_total / max_total * 100) if max_total > 0 else 0.0

    meta_data = [
        [Paragraph("<b>Exam:</b>", body_bold), Paragraph(str(exam_title), table_cell),
         Paragraph("<b>Student Roll No:</b>", body_bold), Paragraph(str(roll_no), table_cell)],
        [Paragraph("<b>Subject:</b>", body_bold), Paragraph(str(subject), table_cell),
         Paragraph("<b>Date Evaluated:</b>", body_bold), Paragraph(eval_date, table_cell)],
        [Paragraph("<b>Final Score:</b>", body_bold), Paragraph(f"<b>{approved_total:.1f} / {max_total:.1f}</b>", body_bold),
         Paragraph("<b>Percentage:</b>", body_bold), Paragraph(f"<b>{percentage:.1f}%</b>", body_bold)],
    ]

    t_meta = Table(meta_data, colWidths=[100, 160, 110, 160])
    t_meta.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 20))

    # Questions Breakdown
    story.append(Paragraph("<b>Question-by-Question Evaluation Breakdown</b>", styles["Heading3"]))
    story.append(Spacer(1, 8))

    q_table_data = [
        [
            Paragraph("<b>Q#</b>", body_bold),
            Paragraph("<b>Question & Reference Solution</b>", body_bold),
            Paragraph("<b>Student Answer & Transcription</b>", body_bold),
            Paragraph("<b>Rationale & Concepts</b>", body_bold),
            Paragraph("<b>AI Marks</b>", body_bold),
            Paragraph("<b>Approved Marks</b>", body_bold),
        ]
    ]

    for item in submission_data.get("items", []):
        q_num = item.get("question_number", "-")
        q_text = item.get("question_text", "")
        ref_text = item.get("reference_answer", "")
        student_ans = item.get("transcribed_answer", "")
        rationale = item.get("rationale", "")
        sug_m = item.get("suggested_marks", 0.0)
        app_m = item.get("approved_marks", 0.0)
        max_m = item.get("max_marks", 0.0)

        q_table_data.append([
            Paragraph(f"<b>Q{q_num}</b>", body_bold),
            Paragraph(f"<b>Q:</b> {q_text}<br/><br/><b>Ref:</b> {ref_text}", table_cell),
            Paragraph(student_ans if student_ans else "<i>[No answer detected]</i>", table_cell),
            Paragraph(rationale, table_cell),
            Paragraph(f"{sug_m:.1f} / {max_m:.1f}", table_cell),
            Paragraph(f"<b>{app_m:.1f} / {max_m:.1f}</b>", body_bold),
        ])

    t_questions = Table(q_table_data, colWidths=[30, 140, 140, 130, 45, 45])
    t_questions.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3b82f6")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t_questions)
    story.append(Spacer(1, 20))

    # Verification Signoff
    signoff_data = [
        [Paragraph("<b>Status:</b> Teacher Approved & Finalized", body_bold),
         Paragraph("<b>Evaluator Signature:</b> ___________________________", body_bold)]
    ]
    t_signoff = Table(signoff_data, colWidths=[265, 265])
    t_signoff.setStyle(TableStyle([
        ("TOPPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(t_signoff)

    doc.build(story)
    return output_path
