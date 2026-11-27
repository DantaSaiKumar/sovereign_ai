from io import BytesIO
from pathlib import Path
import re

import pytest
from docx import Document

from demo_content import (
    EVIDENCE,
    QUESTIONS,
    SAMPLE_DOCUMENT,
    build_sample_report,
    compare_threshold,
    get_prepared_answer,
)


def test_prepared_answers_reference_existing_evidence():
    evidence_ids = {item["id"] for item in EVIDENCE}

    for question in QUESTIONS:
        answer = get_prepared_answer(question)
        assert answer["evidence_ids"]
        assert set(answer["evidence_ids"]) <= evidence_ids


def test_threshold_comparison_classifies_boundary_and_exceedance():
    assert compare_threshold(7.1, 7.1)["status"] == "PASS"
    result = compare_threshold(7.8, 7.1)
    assert result["status"] == "FAIL — investigation required"
    assert result["exceeded"] is True


def test_unknown_question_is_rejected():
    with pytest.raises(ValueError, match="Unknown sample question"):
        get_prepared_answer("What happened to the real pump?")


def test_sample_report_contains_only_demo_marking_and_sample_source():
    report = Document(BytesIO(build_sample_report()))
    text = "\n".join(paragraph.text for paragraph in report.paragraphs)

    assert "SYNTHETIC TRAINING DATA" in text
    assert SAMPLE_DOCUMENT in text
    assert "7.8 mm/s RMS vs 7.1 mm/s RMS" in text


def test_demo_dependency_files_are_minimal_and_cloud_compatible():
    root = Path(__file__).resolve().parents[1]
    demo_requirements = (root / "requirements-demo.txt").read_text(encoding="utf-8")
    cloud_requirements = (root / "public_demo" / "requirements.txt").read_text(encoding="utf-8")
    dependency_lines = [
        line.strip().lower()
        for line in demo_requirements.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]

    assert cloud_requirements == demo_requirements
    assert len(dependency_lines) == 2
    assert any(line.startswith("streamlit") for line in dependency_lines)
    assert any(line.startswith("python-docx") for line in dependency_lines)
    assert not re.search(r"torch|cuda|ollama|pymupdf|openpyxl|python-pptx", demo_requirements, re.I)
