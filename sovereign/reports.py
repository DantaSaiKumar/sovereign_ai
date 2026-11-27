from pathlib import Path
from datetime import datetime
import json
from .config import REPORT_DIR, ensure_dirs
from .audit import append_event

def _safe_report_name(task_id, ext):
    return f"industrial_review_{task_id[:12]}.{ext}"

def generate_docx(task, sources, verification, reviewer_decision=None):
    from docx import Document
    from docx.shared import Inches, Pt
    ensure_dirs()
    doc = Document()
    section = doc.sections[0]
    section.top_margin = Inches(0.7)
    section.bottom_margin = Inches(0.7)
    doc.add_heading("Sovereign AI Workbench", 0)
    doc.add_paragraph("Confidential Industrial Analysis — Draft for Qualified Human Review")
    doc.add_heading("Task", level=1)
    doc.add_paragraph(task["question"])
    doc.add_heading("Analysis", level=1)
    doc.add_paragraph(task.get("answer") or "No answer available.")
    doc.add_heading("Evidence register", level=1)
    if sources:
        table = doc.add_table(rows=1, cols=4)
        table.style = "Light Shading Accent 1"
        for cell, text in zip(table.rows[0].cells, ["ID", "Document", "Page", "Excerpt"]):
            cell.text = text
        for src in sources:
            cells = table.add_row().cells
            cells[0].text = src.get("id", "")
            cells[1].text = src.get("filename", "")
            cells[2].text = str(src.get("page") or "N/A")
            cells[3].text = src.get("excerpt", "")[:500]
    else:
        doc.add_paragraph("No matching local document evidence was retrieved.")
    doc.add_heading("Verification and limitations", level=1)
    doc.add_paragraph(json.dumps(verification, indent=2, ensure_ascii=False))
    doc.add_heading("Human review", level=1)
    doc.add_paragraph(str(reviewer_decision or "Pending — not approved"))
    doc.add_paragraph("This AI-generated document is decision support only. It is not an engineering certification, safety authorization, or substitute for approved site procedures.")
    path = REPORT_DIR / _safe_report_name(task["id"], "docx")
    doc.save(path)
    append_event("report_generated", {"task_id": task["id"], "format": "docx", "filename": path.name})
    return path

def generate_xlsx(task, sources, verification):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    ensure_dirs()
    wb = Workbook()
    ws = wb.active
    ws.title = "Evidence"
    ws.append(["Evidence ID", "Filename", "Page", "Score", "Excerpt"])
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="24476B")
    for src in sources:
        ws.append([src.get("id"), src.get("filename"), src.get("page"),
                   src.get("score"), src.get("excerpt", "")[:1000]])
    meta = wb.create_sheet("Task")
    meta.append(["Field", "Value"])
    meta.append(["Task ID", task["id"]])
    meta.append(["Question", task["question"]])
    meta.append(["Verification", json.dumps(verification, ensure_ascii=False)])
    path = REPORT_DIR / _safe_report_name(task["id"], "xlsx")
    wb.save(path)
    append_event("report_generated", {"task_id": task["id"], "format": "xlsx", "filename": path.name})
    return path

def generate_pptx(task, sources, verification):
    from pptx import Presentation
    from pptx.util import Inches, Pt
    ensure_dirs()
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = "Industrial Analysis"
    slide.placeholders[1].text = "Sovereign AI Workbench — Draft for Human Review"
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = "Task"
    slide.placeholders[1].text = task["question"][:1000]
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = "Executive Summary"
    slide.placeholders[1].text = (task.get("answer") or "No analysis available.")[:2500]
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = "Evidence & Verification"
    summary = [f"{s['id']}: {s['filename']} (page {s.get('page') or 'N/A'})" for s in sources]
    summary += ["", f"Status: {verification.get('status', 'unknown')}",
                "Human review required. Not an operational authorization."]
    slide.placeholders[1].text = "\n".join(summary)[:2500]
    path = REPORT_DIR / _safe_report_name(task["id"], "pptx")
    prs.save(path)
    append_event("report_generated", {"task_id": task["id"], "format": "pptx", "filename": path.name})
    return path
