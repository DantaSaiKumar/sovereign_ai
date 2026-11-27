from sovereign.agent import run_workflow
from sovereign.ingestion import ingest_bytes
from sovereign.db import get_task
import json
from io import BytesIO
from docx import Document

class FakeClient:
    def generate(self, prompt, system=None, model=None):
        assert "Pump" in prompt
        return "The SOP states monthly inspection [S1]. Human review is required.", "fake-local-model"

def test_agent_workflow_uses_local_evidence():
    ingest_bytes("sop.txt", b"Pump P-101 requires monthly inspection.")
    result = run_workflow("What does the SOP say about pump inspection?", client=FakeClient())
    assert result["task_id"]
    assert result["sources"]
    assert result["verification"]["status"] == "requires_human_review"
    assert get_task(result["task_id"])["status"] == "completed"


def test_asset_tag_question_gets_direct_answer_without_unrelated_checks():
    docx = Document()
    table = docx.add_table(rows=2, cols=4)
    for cell, value in zip(
        table.rows[0].cells, ["Equipment", "Asset tag", "Location", "Service"]
    ):
        cell.text = value
    for cell, value in zip(
        table.rows[1].cells,
        ["Centrifugal process-water pump", "P-204", "Training Plant", "Water"],
    ):
        cell.text = value
    docx.add_paragraph(
        "Vibration reading: 4.8 mm/s; upper threshold is 4.5 mm/s."
    )
    docx.add_paragraph(
        "Bearing temperature reading: 76 C; upper threshold is 80 C."
    )
    content = BytesIO()
    docx.save(content)
    ingest_bytes(
        "sample_industrial_pump_sop_test.docx",
        content.getvalue(),
    )

    class AssetTagClient:
        def generate(self, prompt, system=None, model=None):
            assert "What is the asset tag?" in prompt
            assert "Produce:" not in prompt
            assert "\n1. Executive summary" not in prompt
            assert "\n4. Recommended next steps" not in prompt
            assert "Independent deterministic checks" not in prompt
            return (
                "The asset tag is P-204. "
                "The location is Training Plant.",
                "fake-local-model",
            )

    result = run_workflow(
        "What is the asset tag?",
        client=AssetTagClient(),
    )

    assert result["answer"].startswith("The asset tag is P-204")
    assert "[S1]" in result["answer"]
    assert "location" not in result["answer"].lower()
    assert not any(term in result["answer"].lower() for term in (
        "vibration", "temperature", "maintenance history", "executive summary",
        "inspection report",
    ))
    assert result["verification"]["numeric_checks"]


def test_debug_trace_is_local_structured_and_opt_in(tmp_path, monkeypatch):
    import sovereign.config as config

    monkeypatch.setattr(config, "DATA_DIR", tmp_path / "local-data")
    monkeypatch.setenv("SOVEREIGN_DEBUG_TRACE", "1")
    ingest_bytes("asset.txt", b"Asset tag P-204.")

    class TraceClient:
        def generate(self, prompt, system=None, model=None):
            return "The asset tag is P-204 [S1].", "fake-local-model"

    result = run_workflow("What is the asset tag?", client=TraceClient())
    trace = config.DATA_DIR / "debug_trace.jsonl"
    records = [json.loads(line) for line in trace.read_text(encoding="utf-8").splitlines()]

    assert {record["stage"] for record in records} >= {
        "task_input_storage", "retrieval", "numeric_verification", "ollama_request",
        "raw_model_response", "citation_verification", "final_displayed_response",
    }
    assert all(record["task_id"] == result["task_id"] for record in records)
    assert records[0]["question"] == "What is the asset tag?"
