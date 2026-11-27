from io import BytesIO


SAMPLE_DOCUMENT = "Synthetic Pump Inspection Record — DEMO-001"
ASSET = {
    "tag": "P-204",
    "type": "Centrifugal transfer pump",
    "location": "Training Plant / Unit 2",
    "inspection_date": "2025-02-14",
}

EVIDENCE = (
    {
        "id": "E-001",
        "section": "Asset identification",
        "excerpt": "Asset tag: P-204. Equipment: centrifugal transfer pump. Location: Training Plant, Unit 2.",
    },
    {
        "id": "E-002",
        "section": "Equipment rating",
        "excerpt": "Manufacturer-rated flow: 125 m³/h at the documented operating point.",
    },
    {
        "id": "E-003",
        "section": "Vibration measurement",
        "excerpt": "Overall vibration measured at the drive end: 7.8 mm/s RMS on 2025-02-14.",
    },
    {
        "id": "E-004",
        "section": "Training alert criterion",
        "excerpt": "For this synthetic exercise, investigate an overall vibration reading above 7.1 mm/s RMS.",
    },
    {
        "id": "E-005",
        "section": "Observed conditions",
        "excerpt": "Inspector noted a minor seal leak and one missing coupling-guard fastener.",
    },
    {
        "id": "E-006",
        "section": "Inspection disposition",
        "excerpt": "Record the conditions for qualified review. Root cause, leak rate, and equipment fitness were not established.",
    },
)

QUESTIONS = (
    "What is the asset tag?",
    "What is the rated flow?",
    "What is the vibration reading?",
    "Compare vibration against its alert threshold.",
    "Identify the documented defects.",
    "Summarize the inspection findings.",
)

_PREPARED_ANSWERS = {
    QUESTIONS[0]: {
        "answer": "The documented asset tag is P-204.",
        "evidence_ids": ("E-001",),
        "facts": ("Asset tag P-204 is stated in the sample record.",),
        "inferences": (),
        "unknowns": ("The sample does not establish that this asset exists outside the exercise.",),
    },
    QUESTIONS[1]: {
        "answer": "The documented rated flow is 125 m³/h.",
        "evidence_ids": ("E-002",),
        "facts": ("The sample record states a manufacturer-rated flow of 125 m³/h.",),
        "inferences": (),
        "unknowns": ("The record does not verify the current operating flow.",),
    },
    QUESTIONS[2]: {
        "answer": "The recorded drive-end overall vibration is 7.8 mm/s RMS.",
        "evidence_ids": ("E-003",),
        "facts": ("A reading of 7.8 mm/s RMS is documented for 2025-02-14.",),
        "inferences": (),
        "unknowns": ("No later or independently verified measurement is provided.",),
    },
    QUESTIONS[4]: {
        "answer": "The inspection record documents a minor seal leak and one missing coupling-guard fastener.",
        "evidence_ids": ("E-005",),
        "facts": (
            "A minor seal leak was noted.",
            "One coupling-guard fastener was missing.",
        ),
        "inferences": (),
        "unknowns": ("Leak rate and the condition of any other fasteners are not documented.",),
    },
    QUESTIONS[5]: {
        "answer": (
            "The synthetic record identifies P-204, records a drive-end vibration of "
            "7.8 mm/s RMS, and notes a minor seal leak and a missing coupling-guard "
            "fastener. The reading exceeds the exercise's 7.1 mm/s RMS investigation "
            "criterion. These observations require qualified review; the record does "
            "not establish a root cause or equipment fitness."
        ),
        "evidence_ids": ("E-001", "E-003", "E-004", "E-005", "E-006"),
        "facts": (
            "The record documents the asset tag, vibration reading, and two observed conditions.",
            "The sample disposition requests qualified review.",
        ),
        "inferences": (
            "The documented vibration reading exceeds the sample's investigation criterion.",
        ),
        "unknowns": (
            "Root cause, leak rate, current operating state, and equipment fitness are not established.",
        ),
    },
}


def compare_threshold(reading, threshold):
    """Return a deterministic comparison; readings above the limit fail the exercise check."""
    reading = float(reading)
    threshold = float(threshold)
    exceeded = reading > threshold
    return {
        "reading": reading,
        "threshold": threshold,
        "comparison": "above" if exceeded else "at or below",
        "status": "FAIL — investigation required" if exceeded else "PASS",
        "exceeded": exceeded,
    }


def get_prepared_answer(question):
    if question == QUESTIONS[3]:
        comparison = compare_threshold(7.8, 7.1)
        return {
            "answer": (
                f"The recorded reading is {comparison['reading']:.1f} mm/s RMS, "
                f"{comparison['comparison']} the synthetic alert threshold of "
                f"{comparison['threshold']:.1f} mm/s RMS. Result: {comparison['status']}."
            ),
            "evidence_ids": ("E-003", "E-004"),
            "facts": (
                "The record gives a measured value of 7.8 mm/s RMS.",
                "The exercise criterion says to investigate readings above 7.1 mm/s RMS.",
            ),
            "inferences": ("The measured value exceeds the exercise criterion.",),
            "unknowns": ("This training criterion is not an approved site or manufacturer limit.",),
            "comparison": comparison,
        }
    if question not in _PREPARED_ANSWERS:
        raise ValueError(f"Unknown sample question: {question}")
    return dict(_PREPARED_ANSWERS[question])


def build_sample_report():
    from docx import Document

    answer = get_prepared_answer(QUESTIONS[5])
    comparison = compare_threshold(7.8, 7.1)
    report = Document()
    report.add_heading("Sovereign AI Workbench — Sample Report", 0)
    report.add_paragraph("SIMULATED DEMONSTRATION — SYNTHETIC TRAINING DATA ONLY")
    report.add_paragraph(f"Source: {SAMPLE_DOCUMENT}")
    report.add_heading("Prepared sample summary", level=1)
    report.add_paragraph(answer["answer"])
    report.add_heading("Deterministic threshold check", level=1)
    report.add_paragraph(
        f"{comparison['reading']:.1f} mm/s RMS vs "
        f"{comparison['threshold']:.1f} mm/s RMS: {comparison['status']}."
    )
    report.add_heading("Evidence register", level=1)
    for evidence in EVIDENCE:
        report.add_paragraph(
            f"{evidence['id']} — {evidence['section']}: {evidence['excerpt']}",
            style="List Bullet",
        )
    report.add_heading("Review status and limitations", level=1)
    report.add_paragraph("Human review: required and pending.")
    report.add_paragraph(
        "This synthetic sample is not a real inspection, live AI response, "
        "engineering conclusion, or operational authorization."
    )
    output = BytesIO()
    report.save(output)
    return output.getvalue()
