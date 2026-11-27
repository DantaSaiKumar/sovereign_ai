import re
from decimal import Decimal, InvalidOperation


_NUMBER = r"(?<![\w.-])[+-]?\d+(?:\.\d+)?(?![\w])"
_UNIT = (
    r"(?:mm\s*/\s*s|m\s*/\s*s|l\s*/\s*min|°\s*[cf]|"
    r"mm|cm|km|m|inches|inch|psi|kpa|mpa|pa|bar|rpm|hz|"
    r"kg|g|%|c|f)"
)
_NUMBER_MENTION = re.compile(
    rf"(?P<value>{_NUMBER})\s*(?P<unit>{_UNIT})?(?![a-z])", re.IGNORECASE
)
_CITATION = re.compile(r"\[(S\d+)\]")
_TOKEN = re.compile(r"\d+(?:\.\d+)?|[a-zA-Zµμ°]+(?:/[a-zA-Z]+)?")
_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "being", "by",
    "document", "documents", "for", "from", "in", "is", "it", "of", "on",
    "or", "record", "records", "reported", "reports", "says", "shows",
    "source", "states", "that", "the", "this", "to", "was", "were", "with",
    "sop", "finding", "findings", "analysis", "indicates", "indicated",
    "stated", "report", "documented",
}
_RANGE_PATTERN = re.compile(
    rf"\b(?:acceptable\s+|operating\s+|normal\s+)?range\s*(?:is|of|:|=)?\s*"
    rf"(?P<lower>{_NUMBER})\s*(?P<lower_unit>{_UNIT})?\s*"
    rf"(?:and|to|[-–])\s*(?P<upper>{_NUMBER})\s*(?P<upper_unit>{_UNIT})?",
    re.IGNORECASE,
)
_BETWEEN_PATTERN = re.compile(
    rf"\bbetween\s+(?P<lower>{_NUMBER})\s*(?P<lower_unit>{_UNIT})?\s*"
    rf"(?:and|to|[-–])\s*(?P<upper>{_NUMBER})\s*(?P<upper_unit>{_UNIT})?",
    re.IGNORECASE,
)
_ACTION_PAST = {
    "checked", "completed", "found", "inspected", "maintained", "observed",
    "performed", "recorded", "repaired", "replaced", "reviewed", "verified",
}
_STATUS_TERMS = {
    "EXCEEDED": {"exceeded", "exceed", "above"},
    "BELOW THRESHOLD": {"below", "threshold"},
    "AT THRESHOLD": {"threshold", "equal"},
    "WITHIN RANGE": {"within", "range"},
    "BELOW RANGE": {"below", "range"},
    "ABOVE RANGE": {"above", "range"},
    "REQUIRES INVESTIGATION": {"require", "investigation", "investigate"},
    "FOLLOW-UP REQUIRED": {"followup", "require", "recheck"},
}
_NO_ISSUES = re.compile(
    r"\b(?:no\s+(?:(?:relevant\s+)?evidence|findings|issues?|defects?|"
    r"abnormalit(?:y|ies)|violations?|problems?)"
    r"|all\s+(?:readings?|conditions?)\s+(?:are\s+)?"
    r"(?:acceptable|normal|compliant)|nothing\s+(?:abnormal|concerning))\b",
    re.IGNORECASE,
)
_ACCEPTABLE = re.compile(
    r"\b(?:within\s+(?:the\s+)?(?:limits?|range|threshold)|"
    r"acceptable|compliant|below\s+(?:the\s+)?threshold|no\s+exceedance)\b",
    re.IGNORECASE,
)
_GENERIC_DISCLAIMER = re.compile(
    r"^(?:human review is required|"
    r"this (?:draft|analysis) is not (?:an )?operational authorization|"
    r"synthetic (?:data|records).*(?:do not|does not) establish|"
    r"no document-grounded conclusion can be made)\.?$",
    re.IGNORECASE,
)
_ASSESSMENT_REQUEST = re.compile(
    r"\b(?:analy[sz]e|assess|evaluate|inspect|review|check|audit|compare|"
    r"investigate|recommend(?:ation)?s?|risk|safety|issues?|defect(?:s)?|"
    r"findings?|condition|threshold|limits?|maintenance)\b",
    re.IGNORECASE,
)
_QUESTION_FILLER = {
    "what", "which", "who", "where", "when", "why", "how", "much", "many",
    "tell", "give", "show", "me", "the", "a", "an", "is", "are", "was",
    "were", "be", "do", "does", "did", "it", "this", "that", "for", "of",
    "to", "in", "on", "from", "asset", "pump", "document", "sop",
}
_METADATA_LINE = re.compile(
    r"^\s*(?:[-*]\s*)?\*\*(?P<label>source\s*id|document|page|excerpt)"
    r"(?:\s*\[(?P<citation>S\d+)\])?\s*:?\*\*\s*:?\s*(?P<value>.*)$",
    re.IGNORECASE,
)
_INSTRUCTIONAL = re.compile(
    r"\b(?:must|shall|should|need(?:s)? to|review|inspect|check|verify|"
    r"re-?check|reinspect)\b",
    re.IGNORECASE,
)
_THRESHOLD_WORD = re.compile(
    r"\b(?:threshold|limit|maximum|minimum|max(?:imum)?|min(?:imum)?|upper|lower)\b",
    re.IGNORECASE,
)
_THRESHOLD_BEFORE = re.compile(
    r"\b(?:threshold|limit)\b(?:\s+(?:is|of|at))?\s*[:=]?\s*$",
    re.IGNORECASE,
)
_READING_WORD = re.compile(
    r"\b(?:reading|measured|measurement|observed|actual|value|vibration|"
    r"pressure|temperature|flow|speed|clearance|level|voltage|current)\b",
    re.IGNORECASE,
)
_NUMERIC_RELATION = re.compile(
    rf"(?P<left>{_NUMBER})\s*(?:{_UNIT})?(?:\s+\w+){{0,2}}\s*"
    r"(?:(?:is|was|are|were)\s+)?(?P<negation>not\s+)?"
    r"(?P<operator>greater\s+than|less\s+than|higher\s+than|lower\s+than|"
    r"equal(?:s)?(?:\s+to)?|exceed(?:s|ed)?|above|below|under|>=|<=|[><=≥≤])\s*"
    rf"(?:the\s+)?(?:threshold|limit)?\s*(?P<right>{_NUMBER})",
    re.IGNORECASE,
)


def _decimal(value):
    try:
        return Decimal(str(value).replace(",", ""))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Not a valid numeric value: {value!r}") from exc


def compare_to_threshold(value, threshold, direction="upper"):
    """Classify a value against an upper, lower, or direction-neutral threshold."""
    actual, limit = _decimal(value), _decimal(threshold)
    if actual == limit:
        return "AT THRESHOLD"
    direction = direction.lower()
    if direction in {"lower", "minimum", "min"}:
        return "BELOW THRESHOLD" if actual < limit else "MEETS THRESHOLD"
    if direction not in {"upper", "maximum", "max", "neutral"}:
        raise ValueError(f"Unsupported threshold direction: {direction}")
    return "EXCEEDED" if actual > limit else "BELOW THRESHOLD"


def compare_to_range(value, lower, upper):
    """Classify a value against an inclusive numeric range."""
    actual, low, high = map(_decimal, (value, lower, upper))
    if low > high:
        raise ValueError("The lower range bound must not exceed the upper bound.")
    if actual < low:
        return "BELOW RANGE"
    if actual > high:
        return "ABOVE RANGE"
    return "WITHIN RANGE"


def _source_label(source):
    parts = [source.get("filename") or "Retrieved document"]
    if source.get("section"):
        parts.append(f"section {source['section']}")
    if source.get("page"):
        parts.append(f"page {source['page']}")
    return ", ".join(parts)


def _split_evidence_sentences(text):
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", text or "") if part.strip()]


def _unit(value):
    return re.sub(r"\s+", "", value or "").lower()


def _reading_label_distance(sentence, mention):
    prefix_start = max(0, mention.start() - 45)
    prefix = sentence[prefix_start:mention.start()]
    labels = list(_READING_WORD.finditer(prefix))
    return mention.start() - (prefix_start + labels[-1].end()) if labels else float("inf")


def _numeric_findings(sources):
    findings = []
    seen = set()
    for source in sources:
        source_id = source.get("id")
        for sentence in _split_evidence_sentences(source.get("excerpt", "")):
            mentions = list(_NUMBER_MENTION.finditer(sentence))
            if len(mentions) < 2:
                continue
            range_matches = list(_RANGE_PATTERN.finditer(sentence))
            range_matches.extend(_BETWEEN_PATTERN.finditer(sentence))
            for range_match in range_matches:
                lower_unit = _unit(range_match.group("lower_unit"))
                upper_unit = _unit(range_match.group("upper_unit"))
                if lower_unit and upper_unit and lower_unit != upper_unit:
                    continue
                reading_candidates = [
                    item for item in mentions
                    if item.start() < range_match.start()
                    and _READING_WORD.search(sentence[max(0, item.start() - 28):item.start()])
                ]
                if not reading_candidates:
                    continue
                reading = reading_candidates[-1]
                unit = _unit(reading.group("unit") or upper_unit or lower_unit)
                if reading.group("unit") and unit != (upper_unit or lower_unit or unit):
                    continue
                key = (
                    source_id, reading.group("value"), range_match.group("lower"),
                    range_match.group("upper"), unit,
                )
                if key in seen:
                    continue
                seen.add(key)
                findings.append({
                    "type": "numeric_range",
                    "value": reading.group("value"),
                    "lower": range_match.group("lower"),
                    "upper": range_match.group("upper"),
                    "unit": unit,
                    "status": compare_to_range(
                        reading.group("value"),
                        range_match.group("lower"),
                        range_match.group("upper"),
                    ),
                    "source_id": source_id,
                    "document": _source_label(source),
                    "excerpt": sentence,
                })

            threshold_mentions = []
            reading_mentions = []
            for mention in mentions:
                before = sentence[max(0, mention.start() - 32):mention.start()]
                after = sentence[mention.end():mention.end() + 24]
                immediate_marker = bool(_THRESHOLD_WORD.match(after.strip()))
                if _THRESHOLD_BEFORE.search(before) or immediate_marker:
                    threshold_mentions.append(mention)
                elif _READING_WORD.search(before[-28:]):
                    reading_mentions.append(mention)

            if not threshold_mentions:
                if len(mentions) != 2:
                    continue
                reading, threshold_mention = mentions
                relation = sentence[reading.end():threshold_mention.start()]
                if not re.search(
                    r"\b(?:against|versus|vs\.?|compared(?:\s+(?:with|to))?)\b|>=|<=|[><=≥≤]",
                    relation,
                    re.I,
                ):
                    continue
                if (
                    _unit(reading.group("unit"))
                    and _unit(threshold_mention.group("unit"))
                    and _unit(reading.group("unit")) != _unit(threshold_mention.group("unit"))
                ):
                    continue
                direction = "lower" if re.search(
                    r"\b(?:minimum|min|lower|at least|not less than)\b", sentence, re.I
                ) else "upper"
                value = reading.group("value")
                threshold = threshold_mention.group("value")
                unit = _unit(reading.group("unit") or threshold_mention.group("unit"))
                key = (source_id, value, threshold, unit)
                if key not in seen:
                    seen.add(key)
                    findings.append({
                        "type": "numeric_threshold",
                        "value": value,
                        "threshold": threshold,
                        "unit": unit,
                        "direction": direction,
                        "status": compare_to_threshold(value, threshold, direction),
                        "source_id": source_id,
                        "document": _source_label(source),
                        "excerpt": sentence,
                    })
                continue
            for threshold_mention in threshold_mentions:
                candidates = [
                    item for item in mentions
                    if item is not threshold_mention
                    and (
                        not _unit(item.group("unit"))
                        or not _unit(threshold_mention.group("unit"))
                        or _unit(item.group("unit")) == _unit(threshold_mention.group("unit"))
                    )
                ]
                labelled = [item for item in candidates if item in reading_mentions]
                if labelled:
                    reading = min(
                        labelled,
                        key=lambda item: (
                            _reading_label_distance(sentence, item),
                            abs(item.start() - threshold_mention.start()),
                        ),
                    )
                elif len(mentions) == 2 and candidates:
                    reading = candidates[0]
                else:
                    between = sentence[
                        min(threshold_mention.end(), candidates[0].end()):
                        max(threshold_mention.start(), candidates[0].start())
                    ] if candidates else ""
                    if candidates and re.search(r"\b(?:against|versus|vs\.?|compared)\b", between, re.I):
                        reading = candidates[0]
                    else:
                        continue

                context_start = max(0, threshold_mention.start() - 30)
                context_end = min(len(sentence), threshold_mention.end() + 30)
                threshold_context = sentence[context_start:context_end].lower()
                direction = "lower" if re.search(
                    r"\b(?:minimum|min|lower|at least|not less than)\b", threshold_context
                ) else "upper"
                value = reading.group("value")
                threshold = threshold_mention.group("value")
                unit = _unit(reading.group("unit") or threshold_mention.group("unit"))
                key = (source_id, value, threshold, unit)
                if key in seen:
                    continue
                seen.add(key)
                status = compare_to_threshold(value, threshold, direction)
                findings.append({
                    "type": "numeric_threshold",
                    "value": value,
                    "threshold": threshold,
                    "unit": unit,
                    "direction": direction,
                    "status": status,
                    "source_id": source_id,
                    "document": _source_label(source),
                    "excerpt": sentence,
                })
    return findings


def _condition_findings(sources):
    findings = []
    for source in sources:
        for sentence in _split_evidence_sentences(source.get("excerpt", "")):
            if _is_heading_or_boilerplate(sentence):
                continue
            folded = sentence.lower()
            status = None
            description = None
            if (
                re.search(r"\bseal\b", folded)
                and re.search(r"\b(?:intermittent(?:ly)?|sporadic(?:ally)?)\b", folded)
                and re.search(r"\b(?:drip(?:ping|ped|s)?|leak(?:ing|ed|s)?)\b", folded)
            ):
                status = "REQUIRES INVESTIGATION"
                description = "Intermittent seal dripping"
            elif (
                re.search(r"\bfoundation\s+bolts?\b", folded)
                and re.search(r"\b(?:re-?check|reinspect|follow[- ]?up)\b", folded)
            ):
                status = "FOLLOW-UP REQUIRED"
                description = "Foundation bolt marked for re-check"
            elif re.search(
                r"\b(?:crack(?:ed)?|corrod(?:ed|ing)|leak(?:ing|ed)?|"
                r"loose|damaged|defect(?:ive)?|failed)\b",
                folded,
            ) and not re.search(r"\b(?:no|without)\s+(?:visible\s+)?(?:crack|corrosion|leak|defect)", folded):
                status = "REQUIRES INVESTIGATION"
                description = "Documented defect or abnormal condition"
            if status:
                findings.append({
                    "type": "condition",
                    "description": description,
                    "status": status,
                    "source_id": source.get("id"),
                    "document": _source_label(source),
                    "excerpt": sentence,
                })
    return findings


def _maintenance_history_status(question, sources):
    combined = "\n".join(source.get("excerpt", "") for source in sources)
    relevant = bool(re.search(r"\bmaintenance\s+(?:history|records?|logs?)\b", question or "", re.I))
    relevant = relevant or bool(re.search(r"\bmaintenance\s+(?:history|records?|logs?)\b", combined, re.I))
    if not relevant:
        return None

    unavailable = re.search(
        r"\b(?:maintenance\s+(?:history|records?|logs?)\s+)?"
        r"(?:(?:is|was|were|are)\s+)?"
        r"(?:not available|unavailable|missing|not provided|not found|not documented|"
        r"no records?|no history)\b",
        combined,
        re.I,
    )
    negated_review = re.search(
        r"\b(?:maintenance\s+(?:history|records?|logs?)\s+)?"
        r"(?:was\s+|were\s+|has\s+been\s+|have\s+been\s+)?"
        r"(?:not|never)\s+(?:\w+\s+){0,2}(?:reviewed|checked|verified|examined)\b",
        combined,
        re.I,
    )
    completed_review = re.search(
        r"\b(?:maintenance\s+(?:history|records?|logs?)\s+)?"
        r"(?:was|were|has been|have been|had been)?\s*"
        r"(?:reviewed|checked|verified|examined)\b",
        combined,
        re.I,
    )
    if unavailable or negated_review or not completed_review:
        reason = (
            "The retrieved documents identify the maintenance history as unavailable or missing."
            if unavailable
            else "The retrieved documents do not establish that maintenance history was reviewed."
        )
        return {"status": "UNKNOWN", "reason": reason, "source_ids": []}

    matching = [
        source.get("id") for source in sources
        if re.search(r"\bmaintenance\s+(?:history|records?|logs?)\b", source.get("excerpt", ""), re.I)
        and re.search(r"\b(?:reviewed|checked|verified|examined)\b", source.get("excerpt", ""), re.I)
        and not _INSTRUCTIONAL.search(source.get("excerpt", ""))
    ]
    if not matching:
        return {
            "status": "UNKNOWN",
            "reason": "A review instruction is not evidence that the maintenance history was reviewed.",
            "source_ids": [],
        }
    return {
        "status": "DOCUMENTED_IN_SOURCE",
        "reason": "A retrieved document reports a completed maintenance-history review; real-world verification was not performed.",
        "source_ids": matching,
    }


def analyze_document_evidence(question, sources):
    """Create deterministic checks from retrieved excerpts, without relying on model output."""
    numeric = _numeric_findings(sources)
    conditions = _condition_findings(sources)
    maintenance = _maintenance_history_status(question, sources)
    return {
        "numeric_checks": numeric,
        "condition_findings": conditions,
        "maintenance_history": maintenance,
        "evidence_count": len(sources),
        "document_grounding": "DOCUMENT_GROUNDED" if sources else "INSUFFICIENT_EVIDENCE",
        "real_world_verification": "NOT_PERFORMED",
        "synthetic_data_notice": (
            "Synthetic data can support document-grounded conclusions only; "
            "it does not establish the condition of actual industrial equipment."
        ),
    }


def should_include_deterministic_checks(question):
    return bool(_ASSESSMENT_REQUEST.search(question or ""))


def _normalize_token(token):
    token = token.lower().replace("μ", "u").replace("µ", "u").replace("°", "")
    token = token.replace("-", "")
    if token in {"exceeded", "exceeds", "exceeding"}:
        return "exceed"
    if token in {"requires", "required", "requiring"}:
        return "require"
    if token in {"dripping", "dripped", "drips"}:
        return "drip"
    if token in {"leaking", "leaked", "leaks"}:
        return "leak"
    if token.endswith("ies") and len(token) > 4:
        return token[:-3] + "y"
    if token.endswith("ing") and len(token) > 5:
        return token[:-3]
    if token.endswith("ed") and len(token) > 4:
        return token[:-2]
    if token.endswith("s") and len(token) > 3:
        return token[:-1]
    return token


def _claim_tokens(text):
    cleaned = _CITATION.sub("", text).lower().replace("re-check", "recheck").replace("follow-up", "followup")
    return {
        _normalize_token(token)
        for token in _TOKEN.findall(cleaned)
        if token.lower() not in _STOP_WORDS
    }


def _is_heading_or_boilerplate(sentence):
    cleaned = re.sub(r"^[\s#>*-]+", "", sentence).strip()
    cleaned = re.sub(r"^\d+[\.)]\s*", "", cleaned)
    if not cleaned:
        return True
    heading = cleaned.replace("**", "").replace("__", "").strip().rstrip(":").strip()
    if re.fullmatch(
        r"(?:executive summary|evidence(?:-backed)? findings|findings|evidence|"
        r"gaps(?: and uncertainty)?|recommended next steps(?: for qualified human review)?|"
        r"next steps|verification status|conclusion|deterministic numerical results|"
        r"missing or ambiguous evidence|real-world verification status|"
        r"document grounding|synthetic data notice|defect escalation rules|"
        r"bearing temperature check|guard inspection|seal leakage check)",
        heading,
        re.I,
    ):
        return True
    if _GENERIC_DISCLAIMER.fullmatch(heading):
        return True
    return False


def _is_source_metadata(sentence, sources):
    match = _METADATA_LINE.fullmatch(sentence)
    if not match:
        return False
    label = match.group("label").lower().replace(" ", "")
    value = match.group("value").strip().strip("\"'`")
    citation = match.group("citation")
    candidates = [
        source for source in sources
        if not citation or source.get("id") == citation
    ]
    if label == "sourceid":
        return any(source.get("id") == value for source in candidates)
    if label == "document":
        return any(source.get("filename") == value for source in candidates)
    if label == "page":
        return any(str(source.get("page") or "N/A") == value for source in candidates)
    normalized_value = re.sub(r"\s+", " ", value).strip()
    return bool(normalized_value) and any(
        normalized_value in re.sub(
            r"\s+", " ", source.get("excerpt", "")
        ).strip()
        for source in candidates
    )


def _source_supports_completed_action(claim, excerpt):
    past_actions = re.findall(r"\b(?:" + "|".join(sorted(_ACTION_PAST)) + r")\b", claim, re.I)
    if not past_actions:
        return True
    for action in past_actions:
        if not re.search(rf"\b{action}\b", excerpt, re.I):
            return False
        negation = r"(?:not|never|no|(?:was|were|is|are|has|have)n['’]t)"
        claim_is_negative = bool(re.search(rf"\b{negation}\b.{{0,24}}\b{action}\b", claim, re.I))
        source_is_negative = bool(re.search(rf"\b{negation}\b.{{0,24}}\b{action}\b", excerpt, re.I))
        if claim_is_negative != source_is_negative:
            return False
    return True


def _table_supports_claim(claim, source):
    claim_terms = _claim_tokens(claim)
    lines = (source.get("excerpt") or "").splitlines()
    for header_line, value_line in zip(lines, lines[1:]):
        if "|" not in header_line or "|" not in value_line:
            continue
        headers = [cell.strip() for cell in header_line.split("|")]
        values = [cell.strip() for cell in value_line.split("|")]
        if len(headers) != len(values) or any(
            _NUMBER_MENTION.search(header) for header in headers
        ):
            continue
        row_terms = _claim_tokens(" ".join(headers + values))
        if not claim_terms <= row_terms:
            continue
        for header, value in zip(headers, values):
            header_terms = _claim_tokens(header)
            value_terms = _claim_tokens(value)
            if (
                header_terms
                and value_terms
                and header_terms <= claim_terms
                and value_terms <= claim_terms
                and _source_supports_completed_action(claim, " ".join(headers + values))
            ):
                return True
    return False


def _supported_by_sources(sentence, cited_sources, analysis):
    claim_terms = _claim_tokens(sentence)
    derived_by_source = {}
    cited_ids = {source.get("id") for source in cited_sources}
    for finding in analysis.get("numeric_checks", []) + analysis.get("condition_findings", []):
        if finding.get("source_id") in cited_ids:
            derived_by_source.setdefault(finding.get("source_id"), set()).update(
                _STATUS_TERMS.get(finding.get("status"), set())
            )

    missing_terms = claim_terms.copy()
    for source in cited_sources:
        source_id = source.get("id")
        derived_terms = derived_by_source.get(source_id, set())
        if _table_supports_claim(sentence, source):
            return True, ""
        for excerpt_sentence in _split_evidence_sentences(source.get("excerpt", "")):
            evidence_terms = _claim_tokens(excerpt_sentence)
            missing = claim_terms - evidence_terms - derived_terms
            missing_terms.intersection_update(missing)
            if not missing and _source_supports_completed_action(sentence, excerpt_sentence):
                return True, ""

    if missing_terms:
        return False, f"Claim includes details absent from the cited excerpt: {', '.join(sorted(missing_terms))}."
    return False, "The cited excerpt does not document the claimed completed action."


def _attach_supported_citations(answer, sources, analysis):
    annotated = []
    added_citations = []
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", answer or ""):
        if (
            not sentence.strip()
            or _CITATION.search(sentence)
            or _is_heading_or_boilerplate(sentence.strip())
            or _is_source_metadata(sentence.strip(), sources)
        ):
            annotated.append(sentence)
            continue
        supporting = [
            source for source in sources
            if _supported_by_sources(sentence, [source], analysis)[0]
        ]
        if supporting:
            source_id = supporting[0]["id"]
            punctuation = re.search(r"[.!?]+$", sentence)
            if punctuation:
                claim = sentence[:punctuation.start()].rstrip()
                annotated.append(f"{claim} [{source_id}]{punctuation.group()}")
            else:
                annotated.append(f"{sentence} [{source_id}]")
            added_citations.append({"claim": sentence, "source_id": source_id})
        else:
            annotated.append(sentence)
    return "\n".join(annotated), added_citations


def _filter_unrequested_sentences(sentences, question):
    requested_terms = _claim_tokens(question) - _QUESTION_FILLER
    if not requested_terms:
        return sentences, []
    relevant = [
        sentence for sentence in sentences
        if requested_terms & _claim_tokens(sentence)
    ]
    if not relevant:
        return sentences, []
    relevant_set = set(relevant)
    omitted = [sentence for sentence in sentences if sentence not in relevant_set]
    return relevant, omitted


def _sentence_contradiction(sentence, analysis):
    for relation in _NUMERIC_RELATION.finditer(sentence):
        left, right = _decimal(relation.group("left")), _decimal(relation.group("right"))
        operator = relation.group("operator").lower()
        if operator in {"greater than", "higher than", "exceeds", "exceed", "exceeded", "above", ">", ">=", "≥"}:
            relation_is_true = left > right
            if operator in {">=", "≥"}:
                relation_is_true = left >= right
        elif operator in {"less than", "lower than", "below", "under", "<", "<=", "≤"}:
            relation_is_true = left < right
            if operator in {"<=", "≤"}:
                relation_is_true = left <= right
        else:
            relation_is_true = left == right
        if relation.group("negation"):
            relation_is_true = not relation_is_true
        if not relation_is_true:
            return "The numerical relationship stated in the conclusion is mathematically incorrect."

    concerns = analysis.get("numeric_checks", []) + analysis.get("condition_findings", [])
    significant = [
        finding for finding in concerns
        if finding.get("status") in {
            "EXCEEDED", "REQUIRES INVESTIGATION", "FOLLOW-UP REQUIRED",
            "BELOW RANGE", "ABOVE RANGE",
        } or (
            finding.get("status") == "BELOW THRESHOLD"
            and finding.get("direction") == "lower"
        )
    ]
    if significant and _NO_ISSUES.search(sentence):
        return "The conclusion says no issues were found despite a documented violation or condition requiring follow-up."

    for finding in concerns:
        status = finding.get("status")
        if status == "EXCEEDED" and _ACCEPTABLE.search(sentence):
            return "The conclusion describes a reading as acceptable although the independently evaluated value exceeds its threshold."
        if status == "BELOW THRESHOLD" and re.search(
            r"\b(?:above|meets?|satisf(?:y|ies)|at or above)\s+(?:the\s+)?threshold\b",
            sentence,
            re.I,
        ):
            return "The conclusion says the value meets the threshold although the independently evaluated value is below it."
        if status == "BELOW THRESHOLD" and finding.get("direction") == "lower" and _ACCEPTABLE.search(sentence):
            return "The conclusion describes a value as acceptable although it is below a documented minimum threshold."
        if status == "BELOW RANGE" and (
            _ACCEPTABLE.search(sentence)
            or re.search(r"\babove\s+(?:the\s+)?range\b", sentence, re.I)
        ):
            return "The conclusion places a value within or above a range although the document-grounded check is below range."
        if status == "ABOVE RANGE" and (
            _ACCEPTABLE.search(sentence)
            or re.search(r"\bbelow\s+(?:the\s+)?range\b", sentence, re.I)
        ):
            return "The conclusion places a value within or below a range although the document-grounded check is above range."
        if status in {"REQUIRES INVESTIGATION", "FOLLOW-UP REQUIRED"} and re.search(
            r"\b(?:no further action|no follow[- ]?up|fully resolved|verified safe)\b",
            sentence,
            re.I,
        ):
            return "The conclusion dismisses a condition that the document marks for investigation or follow-up."
    return None


def validate_citations(answer, sources, analysis=None):
    """Validate citation IDs and lexical support for each factual sentence."""
    analysis = analysis or {}
    source_by_id = {source.get("id"): source for source in sources if source.get("id")}
    unsupported = []
    contradictions = []
    supported_sentences = []
    citations_used = set()

    for sentence in re.split(r"(?<=[.!?])\s+|\n+", answer or ""):
        sentence = sentence.strip()
        if not sentence:
            continue
        if _is_source_metadata(sentence, sources):
            supported_sentences.append(sentence)
            continue
        citations = _CITATION.findall(sentence)
        if _is_heading_or_boilerplate(sentence) and not citations:
            if sentence:
                supported_sentences.append(sentence)
            continue
        contradiction = _sentence_contradiction(sentence, analysis)
        if contradiction:
            contradictions.append({"claim": sentence, "reason": contradiction})
            continue
        if not citations:
            unsupported.append({
                "claim": sentence,
                "reason": "Factual claims must cite a retrieved document excerpt.",
            })
            continue
        missing_ids = sorted(set(citations) - set(source_by_id))
        if missing_ids:
            unsupported.append({
                "claim": sentence,
                "reason": f"Citation(s) do not refer to retrieved evidence: {', '.join(missing_ids)}.",
            })
            continue
        cited_sources = [source_by_id[source_id] for source_id in dict.fromkeys(citations)]
        supported, reason = _supported_by_sources(sentence, cited_sources, analysis)
        if not supported:
            unsupported.append({"claim": sentence, "reason": reason})
            continue
        citations_used.update(citations)
        supported_sentences.append(sentence)

    return {
        "valid": not unsupported and not contradictions,
        "citations_used": sorted(citations_used),
        "unsupported_claims": unsupported,
        "contradictions": contradictions,
        "supported_sentences": supported_sentences,
    }


def _deterministic_finding_lines(analysis):
    lines = []
    for finding in analysis.get("numeric_checks", []) + analysis.get("condition_findings", []):
        source_id = finding.get("source_id")
        if finding["type"] == "numeric_threshold":
            unit = f" {finding['unit']}" if finding.get("unit") else ""
            description = (
                f"Reading {finding['value']}{unit} against {finding['threshold']}{unit}: "
                f"{finding['status']}."
            )
        elif finding["type"] == "numeric_range":
            unit = f" {finding['unit']}" if finding.get("unit") else ""
            description = (
                f"Reading {finding['value']}{unit} against range "
                f"{finding['lower']}{unit}–{finding['upper']}{unit}: {finding['status']}."
            )
        else:
            description = f"{finding['description']}: {finding['status']}."
        citation = f" [{source_id}]" if source_id else ""
        reference = f" ({finding['document']})" if finding.get("document") else ""
        lines.append(f"- {description}{citation}{reference}")

    maintenance = analysis.get("maintenance_history")
    if maintenance and maintenance.get("status") == "UNKNOWN":
        lines.append(f"- Maintenance history: UNKNOWN. {maintenance['reason']}")
    return lines


def prepare_verified_answer(answer=None, sources=None, analysis=None, question=None):
    """Withhold unsupported or contradictory model claims and add deterministic evidence checks."""
    sources = sources or []
    analysis = analysis or {}
    annotated_answer, added_citations = _attach_supported_citations(
        answer, sources, analysis
    )
    validation = validate_citations(annotated_answer, sources, analysis)
    validation["added_citations"] = added_citations
    retained = validation["supported_sentences"]
    filtered_unrequested = []
    if question is not None and not should_include_deterministic_checks(question):
        retained, omitted = _filter_unrequested_sentences(retained, question)
        filtered_unrequested = [
            {
                "claim": sentence,
                "reason": "Supported statement omitted because it does not address the user question.",
            }
            for sentence in omitted
        ]
        validation["supported_sentences"] = retained
        validation["filtered_unrequested_claims"] = filtered_unrequested
        retained_source_ids = {
            source_id
            for sentence in retained
            for source_id in _CITATION.findall(sentence)
        }
        validation["citations_used"] = sorted(retained_source_ids)
    lines = list(retained)
    if validation["unsupported_claims"] or validation["contradictions"]:
        rejected = len(validation["unsupported_claims"]) + len(validation["contradictions"])
        lines.append(
            f"Verifier withheld {rejected} unsupported or contradictory model statement(s)."
        )

    include_checks = question is None or should_include_deterministic_checks(question)
    findings = _deterministic_finding_lines(analysis) if include_checks else []
    if findings:
        lines.extend(["Document-grounded checks:", *findings])
        validation["citations_used"] = sorted(
            set(validation["citations_used"])
            | {
                finding["source_id"]
                for finding in analysis.get("numeric_checks", []) + analysis.get("condition_findings", [])
                if finding.get("source_id")
            }
        )
    if analysis.get("document_grounding") == "INSUFFICIENT_EVIDENCE":
        lines.append("No retrieved evidence supports a document-grounded conclusion; relevant facts remain UNKNOWN.")
    if include_checks and analysis.get("synthetic_data_notice"):
        lines.append(analysis["synthetic_data_notice"])
    return "\n".join(lines), validation
