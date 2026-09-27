"""Agent 3 Layer 1 — tests for the deterministic clinical validator.

Covers the negation-scope regressions fixed in validator.py:
  - "no pneumothorax and consolidation in the RLL" must NOT negate the
    consolidation (it is asserted after "and");
  - a bare "normal" earlier in the sentence must not negate later findings;
  - "no X or Y" must still negate both labels.
Also verifies the omission / contradiction / hallucination verdicts.
"""

import pytest

from validator import extract_findings, validate_report

# (text, label, expected) — expected True = present, False = negated/absent,
# None = not mentioned at all.
NEGATION_CASES = [
    # The three that were extracted backwards before the fix:
    ("FINDINGS: The lungs show no pneumothorax and consolidation in the right lower lobe.",
     "Consolidation", True),
    ("FINDINGS: The heart size is normal and there is a small pleural effusion.",
     "Pleural Effusion", True),
    ("IMPRESSION: Normal chest with a left basilar atelectasis.",
     "Atelectasis", True),
    # Already-correct behaviour that must not regress:
    ("FINDINGS: There is no pneumothorax and no consolidation.",
     "Consolidation", False),
    ("FINDINGS: No pneumothorax or consolidation.",
     "Consolidation", False),
    ("FINDINGS: No pneumothorax. Consolidation in the right lower lobe.",
     "Consolidation", True),
    ("FINDINGS: No edema. Small bilateral pleural effusions are present.",
     "Pleural Effusion", True),
    ("FINDINGS: There is no evidence of edema and no pleural effusion.",
     "Pleural Effusion", False),
    ("FINDINGS: There is no pneumothorax, however a consolidation is seen.",
     "Consolidation", True),
    ("FINDINGS: The lungs are clear of consolidation but a mass is noted.",
     "Lung Lesion", True),
    ("FINDINGS: No pneumothorax, pleural effusion or consolidation.",
     "Consolidation", False),
    # "No Finding" phrasing, including the interleaved form:
    ("FINDINGS: No acute cardiopulmonary findings.",
     "No Finding", True),
    ("IMPRESSION: No acute cardiopulmonary findings.",
     "Pneumonia", None),  # simply not mentioned
]


@pytest.mark.parametrize("text,label,expected", NEGATION_CASES,
                         ids=[f"case{i}" for i in range(1, len(NEGATION_CASES) + 1)])
def test_negation_scope(text, label, expected):
    assert extract_findings(text)[label] is expected


# ---------------------------------------------------------------------------
# Verdicts
# ---------------------------------------------------------------------------

PREDICTIONS = {"Cardiomegaly": 0.85, "Pleural Effusion": 0.72}


def test_correct_report_passes():
    predictions = {"Cardiomegaly": 0.85, "Pleural Effusion": 0.72, "Consolidation": 0.91}
    report = ("FINDINGS: The lungs show no pneumothorax and consolidation in the "
              "right lower lobe. There is cardiomegaly and a right pleural "
              "effusion. IMPRESSION: Consolidation present.")
    result = validate_report(report, predictions)
    assert result["verdict"] == "PASS", result["errors"]


def test_hallucination_is_detected():
    report = "FINDINGS: There is a pneumothorax. IMPRESSION: Pneumothorax present."
    result = validate_report(report, PREDICTIONS)
    assert result["verdict"] == "FAIL"
    assert any("Hallucination" in e and "Pneumothorax" in e for e in result["errors"])


def test_omission_is_detected():
    report = "FINDINGS: The lungs are clear. IMPRESSION: No acute cardiopulmonary findings."
    result = validate_report(report, PREDICTIONS)
    assert result["verdict"] == "FAIL"
    assert any("Omission" in e for e in result["errors"])


def test_contradiction_is_detected():
    report = "FINDINGS: There is no cardiomegaly. IMPRESSION: Normal heart size."
    result = validate_report(report, PREDICTIONS)
    assert result["verdict"] == "FAIL"
    assert any("Contradiction" in e for e in result["errors"])
