from sovereign.reports import generate_docx, generate_xlsx, generate_pptx
from pathlib import Path

def test_report_generation():
    task = {"id": "1234567890abcdef", "question": "Review pump P-101",
            "answer": "Potential finding [S1]."}
    sources = [{"id": "S1", "filename": "sop.txt", "page": 2,
                "score": 1.2, "excerpt": "Inspect vibration monthly."}]
    verification = {"status": "requires_human_review"}
    for maker, suffix in [(generate_docx, ".docx"), (generate_xlsx, ".xlsx"), (generate_pptx, ".pptx")]:
        path = maker(task, sources, verification)
        assert path.exists() and path.suffix == suffix and path.stat().st_size > 0
