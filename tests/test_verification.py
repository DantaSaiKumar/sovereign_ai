from sovereign.verification import (
    analyze_document_evidence,
    compare_to_range,
    compare_to_threshold,
    prepare_verified_answer,
    validate_citations,
)
from sovereign.agent import run_workflow
from sovereign.ingestion import ingest_bytes


def test_numeric_threshold_comparisons_are_independent():
    assert compare_to_threshold(4.8, 4.5) == "EXCEEDED"
    assert compare_to_threshold(76, 80) == "BELOW THRESHOLD"
    assert compare_to_threshold(4.5, 4.5) == "AT THRESHOLD"
    assert compare_to_threshold(76, 80, direction="lower") == "BELOW THRESHOLD"


def test_range_comparisons_include_boundary_values():
    assert compare_to_range(4.2, 4.0, 4.5) == "WITHIN RANGE"
    assert compare_to_range(4.0, 4.0, 4.5) == "WITHIN RANGE"
    assert compare_to_range(3.9, 4.0, 4.5) == "BELOW RANGE"
    assert compare_to_range(4.6, 4.0, 4.5) == "ABOVE RANGE"


def test_numeric_evidence_is_classified_from_the_excerpt():
    sources = [
        {
            "id": "S1",
            "filename": "vibration.txt",
            "excerpt": "Vibration reading: 4.8 mm/s; upper threshold is 4.5 mm/s.",
        },
        {
            "id": "S2",
            "filename": "pressure.txt",
            "excerpt": "Measured value: 76; lower threshold: 80.",
        },
        {
            "id": "S3",
            "filename": "range.txt",
            "excerpt": "Vibration reading: 4.2 mm/s; acceptable range is 4.0 to 4.5 mm/s.",
        },
        {
            "id": "S4",
            "filename": "comparison.txt",
            "excerpt": "Recorded value 76 against 80.",
        },
    ]
    analysis = analyze_document_evidence("Check recorded values", sources)
    assert [finding["status"] for finding in analysis["numeric_checks"]] == [
        "EXCEEDED",
        "BELOW THRESHOLD",
        "WITHIN RANGE",
        "BELOW THRESHOLD",
    ]

    sop_sentence = (
        "The recorded vibration of 4.8 mm/s RMS exceeds the sample alert "
        "threshold of 4.5 mm/s RMS by 0.3 mm/s."
    )
    analysis = analyze_document_evidence("Check vibration", [{
        "id": "S5",
        "filename": "sample_sop.docx",
        "section": "8",
        "excerpt": sop_sentence,
    }])
    assert len(analysis["numeric_checks"]) == 1
    finding = analysis["numeric_checks"][0]
    assert (finding["value"], finding["threshold"], finding["status"]) == (
        "4.8",
        "4.5",
        "EXCEEDED",
    )
    assert finding["document"] == "sample_sop.docx, section 8"

    table_analysis = analyze_document_evidence("Check inspection readings", [
        {
            "id": "S6",
            "filename": "sample_sop.docx",
            "excerpt": "Bearing temperature | 76 °C | Alert at ≥ 80 °C | Below alert threshold",
        },
        {
            "id": "S7",
            "filename": "sample_sop.docx",
            "excerpt": "Overall vibration | 4.8 mm/s RMS | Alert at ≥ 4.5 mm/s RMS | ABOVE alert threshold",
        },
    ])
    assert [finding["status"] for finding in table_analysis["numeric_checks"]] == [
        "BELOW THRESHOLD",
        "EXCEEDED",
    ]

    temperature_analysis = analyze_document_evidence("Check bearing temperature", [{
        "id": "S8",
        "filename": "sample_sop.docx",
        "excerpt": (
            "The recorded bearing temperature of 76 °C is 4 °C below "
            "the sample alert threshold of 80 °C."
        ),
    }])
    assert len(temperature_analysis["numeric_checks"]) == 1
    assert temperature_analysis["numeric_checks"][0]["value"] == "76"
    assert temperature_analysis["numeric_checks"][0]["status"] == "BELOW THRESHOLD"


def test_missing_maintenance_history_is_unknown_not_verified():
    analysis = analyze_document_evidence("Review maintenance history", [])
    assert analysis["maintenance_history"]["status"] == "UNKNOWN"

    instructed = [{
        "id": "S1",
        "filename": "procedure.txt",
        "excerpt": "Review maintenance history before returning the pump to service.",
    }]
    analysis = analyze_document_evidence("Check maintenance history", instructed)
    assert analysis["maintenance_history"]["status"] == "UNKNOWN"

    explicitly_missing = [{
        "id": "S2",
        "filename": "inspection.txt",
        "excerpt": "Maintenance history was not reviewed because records were unavailable.",
    }]
    analysis = analyze_document_evidence("Check maintenance history", explicitly_missing)
    assert analysis["maintenance_history"]["status"] == "UNKNOWN"


def test_intermittent_seal_dripping_requires_investigation():
    source = {
        "id": "S1",
        "filename": "inspection.txt",
        "page": 2,
        "excerpt": "Intermittent seal dripping was observed during inspection.",
    }
    analysis = analyze_document_evidence("Assess the seal", [source])
    finding = analysis["condition_findings"][0]
    assert finding["status"] == "REQUIRES INVESTIGATION"
    assert finding["document"] == "inspection.txt, page 2"


def test_foundation_bolt_recheck_requires_follow_up():
    source = {
        "id": "S1",
        "filename": "inspection.txt",
        "excerpt": "Foundation bolt B-12 is marked for re-check.",
    }
    analysis = analyze_document_evidence("Review foundation", [source])
    assert analysis["condition_findings"][0]["status"] == "FOLLOW-UP REQUIRED"


def test_defect_section_heading_is_not_reported_as_a_condition():
    analysis = analyze_document_evidence("Is the sample real or fake?", [{
        "id": "S1",
        "filename": "pump.docx",
        "excerpt": "7. Defect escalation rules",
    }])

    assert analysis["condition_findings"] == []


def test_contradictory_no_issues_conclusion_is_flagged():
    sources = [{
        "id": "S1",
        "filename": "vibration.txt",
        "excerpt": "Vibration reading: 4.8 mm/s; upper threshold is 4.5 mm/s.",
    }]
    analysis = analyze_document_evidence("Check vibration", sources)
    result = validate_citations(
        "No issues were found [S1]. The vibration is acceptable [S1].",
        sources,
        analysis,
    )
    assert not result["valid"]
    assert result["contradictions"]

    wrong_comparison = validate_citations(
        "The 4.8 mm/s reading is below the 4.5 mm/s threshold [S1].",
        sources,
        analysis,
    )
    assert wrong_comparison["contradictions"]


def test_unsupported_citation_and_instruction_as_completed_action_are_rejected():
    source = {
        "id": "S1",
        "filename": "procedure.txt",
        "excerpt": "Review maintenance history before returning the pump to service.",
    }
    unsupported = validate_citations("The pump was repaired [S1].", [source])
    assert not unsupported["valid"]
    assert unsupported["unsupported_claims"]

    instruction_only = validate_citations(
        "Maintenance history was reviewed [S1].",
        [source],
    )
    assert not instruction_only["valid"]
    assert "completed action" in instruction_only["unsupported_claims"][0]["reason"]

    unknown_id = validate_citations("The pump needs inspection [S9].", [source])
    assert not unknown_id["valid"]
    assert "S9" in unknown_id["unsupported_claims"][0]["reason"]

    unrelated_clauses = {
        "id": "S2",
        "filename": "inspection.txt",
        "excerpt": "Foundation bolt B-12 was rechecked. The seal was intermittently dripping.",
    }
    unrelated_claim = validate_citations(
        "The foundation bolt was dripping [S2].",
        [unrelated_clauses],
        analyze_document_evidence("Inspect bolt and seal", [unrelated_clauses]),
    )
    assert not unrelated_claim["valid"]


def test_markdown_headings_and_verified_source_metadata_are_not_claims():
    source = {
        "id": "S1",
        "filename": "pump.docx",
        "page": None,
        "excerpt": "Asset tag P-204.",
    }
    answer = (
        "## Executive Summary\n"
        "1.\n"
        "- **Source ID**: S1\n"
        "- **Document**: pump.docx\n"
        "- **Excerpt [S1]:** Asset tag P-204.\n"
        "The asset tag is P-204 [S1]."
    )

    result = validate_citations(answer, [source])

    assert result["valid"]
    assert result["unsupported_claims"] == []


def test_markdown_emphasis_does_not_exempt_a_factual_claim():
    result = validate_citations(
        "**The pump was repaired.**",
        [{"id": "S1", "filename": "pump.docx", "excerpt": "Pump P-204."}],
    )

    assert not result["valid"]
    assert result["unsupported_claims"][0]["claim"] == "**The pump was repaired.**"


def test_unrequested_findings_do_not_enter_a_direct_answer():
    sources = [{
        "id": "S1",
        "filename": "pump.docx",
        "excerpt": "Asset tag P-204. Vibration reading: 4.8 mm/s; upper threshold is 4.5 mm/s.",
    }]
    analysis = analyze_document_evidence("What is the asset tag?", sources)

    answer, validation = prepare_verified_answer(
        "The asset tag is P-204 [S1].",
        sources,
        analysis,
        question="What is the asset tag?",
    )

    assert validation["valid"]
    assert answer == "The asset tag is P-204 [S1]."
    assert analysis["numeric_checks"][0]["status"] == "EXCEEDED"


def test_asset_tag_table_row_supports_only_the_value_under_its_header():
    source = {
        "id": "S1",
        "filename": "pump.docx",
        "excerpt": (
            "Equipment | Asset tag | Location | Service\n"
            "Centrifugal process-water pump | P-204 | Training Plant / Utility Bay 2 | Process water transfer"
        ),
    }

    answer, validation = prepare_verified_answer(
        "The asset tag for the centrifugal process-water pump is P-204.",
        [source],
        analyze_document_evidence("What is the asset tag?", [source]),
        question="What is the asset tag?",
    )
    wrong_answer, wrong_validation = prepare_verified_answer(
        "The asset tag for the centrifugal process-water pump is Training Plant.",
        [source],
        analyze_document_evidence("What is the asset tag?", [source]),
        question="What is the asset tag?",
    )

    assert answer == "The asset tag for the centrifugal process-water pump is P-204 [S1]."
    assert validation["valid"]
    assert not wrong_validation["valid"]
    assert "Verifier withheld" in wrong_answer


def test_workflow_withholds_contradictory_model_conclusion():
    class ContradictoryClient:
        def generate(self, prompt, system=None, model=None):
            return "No issues were found [S1]. The vibration is acceptable [S1].", "fake-model"

    ingest_bytes(
        "vibration.txt",
        b"Vibration reading: 4.8 mm/s; upper threshold is 4.5 mm/s.",
    )
    result = run_workflow("Check vibration against the threshold", client=ContradictoryClient())

    assert "No issues were found" not in result["answer"]
    assert "EXCEEDED" in result["answer"]
    assert result["verification"]["numeric_checks"][0]["status"] == "EXCEEDED"
    assert result["verification"]["citation_check"]["contradictions"]
    assert result["verification"]["real_world_verification"] == "NOT_PERFORMED"
