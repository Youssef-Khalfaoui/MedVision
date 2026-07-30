"""
Agent 3 - Layer 1: Deterministic Clinical Validator.
Extracts 14 CheXpert pathologies from generated text, detects negation,
and compares them to Agent 1's predictions to flag hallucinations/omissions.
"""
import re
import json

CATEGORIES = [
    "No Finding", "Enlarged Cardiomediastinum", "Cardiomegaly", "Lung Opacity",
    "Lung Lesion", "Edema", "Consolidation", "Pneumonia", "Atelectasis",
    "Pneumothorax", "Pleural Effusion", "Pleural Other", "Fracture",
    "Support Devices",
]

# Synonyms and regex patterns for each label
LABEL_PATTERNS = {
    "No Finding": r"no (?:acute|active|significant)?\s*finding|clear (?:lungs|chest)|normal chest",
    "Enlarged Cardiomediastinum": r"enlarged cardiomediastinum|widened mediastinum",
    "Cardiomegaly": r"cardiomegaly|enlarged heart|cardiac enlargement|heart size is enlarged",
    "Lung Opacity": r"lung opacity|pulmonary opacity|opacit(?:y|ies)",
    "Lung Lesion": r"lung lesion|pulmonary lesion|mass|nodule|tumor",
    "Edema": r"edema|fluid overload|congestion",
    "Consolidation": r"consolidation",
    "Pneumonia": r"pneumonia|infection|infiltrate",
    "Atelectasis": r"atelectasis|collapse",
    "Pneumothorax": r"pneumothorax",
    "Pleural Effusion": r"pleural effusion|effusion|fluid in the (?:left|right|both) pleural",
    "Pleural Other": r"pleural (?:thickening|calcification|plaque)",
    "Fracture": r"fracture|broken (?:rib|bone)",
    "Support Devices": r"support devices|pacemaker|endotracheal tube|central line|picc line|chest tube"
}

# Negation triggers
NEGATIONS = [
    r"no (?:evidence of|signs of)?",
    r"without (?:evidence of|signs of)?",
    r"absence of",
    r"rule out",
    r"not seen",
    r"clear of",
    r"normal"
]

# Markers that end a negation's scope (whatever comes after is a new clause,
# so a negation earlier in the sentence should not apply past these).
SCOPE_ENDERS = [r"\bbut\b", r"\bhowever\b", r"\balthough\b", r";", r":"]


def is_negated(sentence, match_start):
    """
    Checks if a match is negated by scanning the whole clause preceding it
    (not just the last 3 words), so constructions like "no X or Y" correctly
    negate both X and Y. Stops at scope-reversing markers (e.g. "but") so a
    negation earlier in the sentence doesn't leak past a contradiction.
    """
    pre_text = sentence[:match_start].lower()

    # Find the rightmost scope-ending marker; only search the clause after it.
    scope_start = 0
    for ender_pattern in SCOPE_ENDERS:
        for m in re.finditer(ender_pattern, pre_text):
            scope_start = max(scope_start, m.end())

    clause = pre_text[scope_start:]
    for neg_pattern in NEGATIONS:
        if re.search(neg_pattern, clause):
            return True
    return False


def extract_findings(text):
    """
    Extracts the 14 CheXpert labels from text.
    Returns a dict: {label: True (present) / False (absent/negated) / None (not mentioned)}
    """
    text = text.lower()
    # Split into sentences to scope negation properly
    sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', text)
    extracted = {cat: None for cat in CATEGORIES}
    for sentence in sentences:
        for label, pattern in LABEL_PATTERNS.items():
            for match in re.finditer(pattern, sentence):
                negated = is_negated(sentence, match.start())
                if extracted[label] is None:
                    extracted[label] = not negated
                else:
                    # If mentioned multiple times, if any sentence says it's present, mark as present
                    if not negated:
                        extracted[label] = True
    return extracted


def validate_report(generated_text, agent1_predictions, threshold=0.5):
    """
    Compares extracted findings from Agent 2's text against Agent 1's predictions.
    """
    extracted = extract_findings(generated_text)
    agent1_labels = {}
    for label, prob in agent1_predictions.items():
        agent1_labels[label] = prob >= threshold
    errors = []
    missing_or_contradicted = []
    for label in CATEGORIES:
        ai_detected = agent1_labels.get(label, False)
        llm_mentioned = extracted[label]
        # Case 1: Agent 1 detected it, but LLM didn't mention it (Omission)
        if ai_detected and llm_mentioned is None:
            errors.append(f"Omission: Agent 1 detected {label}, but it was not mentioned in the report.")
            missing_or_contradicted.append(label)
        # Case 2: Agent 1 detected it, but LLM explicitly said it's absent (Contradiction)
        elif ai_detected and llm_mentioned is False:
            errors.append(f"Contradiction: Agent 1 detected {label}, but the report states it is absent.")
            missing_or_contradicted.append(label)
        # Case 3: Agent 1 did NOT detect it, but LLM says it is present (Hallucination)
        elif not ai_detected and llm_mentioned is True:
            # "No Finding" is a special case, often mentioned if others are absent
            if label == "No Finding" and not any(agent1_labels.values()):
                continue
            errors.append(f"Hallucination: Agent 1 did not detect {label}, but the report states it is present.")
    verdict = "PASS" if len(errors) == 0 else "FAIL"
    return {
        "verdict": verdict,
        "errors": errors,
        "missing_or_contradicted": missing_or_contradicted,
        "extracted_findings": {k: v for k, v in extracted.items() if v is not None}
    }


def force_correct_report(text, labels_to_force):
    """
    Deterministic safety-net correction (used when the LLM correction, Layer 2,
    fails to remove a contradiction/omission for a clinically significant finding).
    For each label in labels_to_force: strips any sentence in FINDINGS that
    explicitly negates it (reusing the same negation-scoping logic as the
    validator), then appends a plain factual sentence asserting its presence.
    This never touches labels that are not in labels_to_force.
    """
    if not labels_to_force:
        return text

    findings_match = re.search(r'(FINDINGS:.*?)(?=IMPRESSION:|$)', text, re.IGNORECASE | re.DOTALL)
    impression_match = re.search(r'(IMPRESSION:.*)', text, re.IGNORECASE | re.DOTALL)
    findings_section = findings_match.group(1) if findings_match else text
    impression_section = impression_match.group(1) if impression_match else ""

    def strip_negated_sentences(section, label):
        pattern = LABEL_PATTERNS[label]
        sentences = re.split(r'(?<=\.)\s+', section)
        kept = []
        for sentence in sentences:
            has_match = False
            negated_here = False
            for match in re.finditer(pattern, sentence, re.IGNORECASE):
                has_match = True
                if is_negated(sentence.lower(), match.start()):
                    negated_here = True
            if has_match and negated_here:
                continue  # drop this sentence: it contradicts a confirmed finding
            kept.append(sentence)
        return " ".join(kept).strip()

    for label in labels_to_force:
        findings_section = strip_negated_sentences(findings_section, label)

    additions = " ".join(
        f"{label} is present, correlating with the AI-detected finding on imaging."
        for label in labels_to_force
    )
    findings_section = findings_section.rstrip()
    if findings_section and not findings_section.endswith((".", ":")):
        findings_section += "."
    findings_section = (findings_section + " " + additions).strip()

    corrected = findings_section
    if impression_section:
        corrected += "\n" + impression_section.strip()

    return corrected


# --- Example Usage / Smoke Test ---
if __name__ == "__main__":
    # Mock data: Agent 1 detected Cardiomegaly and Pleural Effusion
    mock_agent1_preds = {
        "Cardiomegaly": 0.85,
        "Pleural Effusion": 0.72,
        "Edema": 0.12,
        "Pneumonia": 0.08
    }
    # Mock Report 1: Perfect match
    report_1 = "FINDINGS: The cardiac silhouette is enlarged. There is a right pleural effusion. IMPRESSION: Cardiomegaly and pleural effusion."
    # Mock Report 2: Hallucination and Omission
    report_2 = "FINDINGS: The lungs are clear. There is no pneumonia. IMPRESSION: No acute cardiopulmonary findings."
    print("=== Validating Report 1 (Should Pass) ===")
    result_1 = validate_report(report_1, mock_agent1_preds)
    print(json.dumps(result_1, indent=2))

    print("\n=== Validating Report 2 (Should Fail) ===")
    result_2 = validate_report(report_2, mock_agent1_preds)
    print(json.dumps(result_2, indent=2))
