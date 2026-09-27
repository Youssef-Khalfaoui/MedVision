"""Agent 1.5 — tests for the clinical trend comparator.

The headline regression: `prior_exam` reaches this module as JSON, so
`exam_date` is an ISO *string*. The comparator used to call .strftime() on it
directly, raising AttributeError for every exam that had a prior study — which
failed the entire pipeline (the backend then marked the exam FAILED).
"""

import json
from datetime import datetime

import pytest

from comparator import Agent1_5_Comparator

CURRENT = {
    "No Finding": 0.02,
    "Cardiomegaly": 0.85,
    "Pleural Effusion": 0.72,
    "Edema": 0.45,
    "Pneumonia": 0.10,
    "Fracture": 0.0,
}


@pytest.fixture()
def comparator():
    return Agent1_5_Comparator()


# ---------------------------------------------------------------------------
# H1 regression: exam_date arrives as an ISO string over HTTP
# ---------------------------------------------------------------------------

def test_prior_exam_with_iso_string_date(comparator):
    """Used to raise AttributeError: 'str' object has no attribute 'strftime'."""
    prior = {
        "exam_id": 7,
        "exam_date": "2026-05-14T10:30:00+00:00",
        "findings": {"Cardiomegaly": 0.80, "Pleural Effusion": 0.20},
    }
    out = comparator.analyze(CURRENT, prior, {}, {})

    assert out["summary"]["has_prior_exam"] is True
    assert out["summary"]["prior_exam_date"] == "2026-05-14"


def test_prior_exam_with_datetime_still_works(comparator):
    prior = {"exam_date": datetime(2026, 5, 14), "findings": {"Cardiomegaly": 0.80}}
    out = comparator.analyze(CURRENT, prior, {}, {})
    assert out["summary"]["prior_exam_date"] == "2026-05-14"


def test_prior_findings_as_json_string(comparator):
    prior = {"exam_date": "2026-05-14", "findings": json.dumps({"Cardiomegaly": 0.80})}
    out = comparator.analyze(CURRENT, prior, {}, {})
    assert out["summary"]["has_prior_exam"] is True


def test_invalid_findings_json_degrades_to_no_prior(comparator):
    prior = {"exam_date": "2026-05-14", "findings": "not-json"}
    out = comparator.analyze(CURRENT, prior, {}, {})
    assert out["summary"]["has_prior_exam"] is False


def test_no_prior_at_all(comparator):
    out = comparator.analyze(CURRENT, {}, {}, {})
    assert out["summary"]["has_prior_exam"] is False
    assert out["summary"]["prior_exam_date"] is None
    assert "No prior exams" in out["llm_prompt_summary"]


# ---------------------------------------------------------------------------
# Trend classification
# ---------------------------------------------------------------------------

def test_trend_classification(comparator):
    trend = comparator._calculate_trend
    assert trend(0.90, 0.00) == "New Finding"
    assert trend(0.10, 0.90) == "Resolving"
    assert trend(0.90, 0.70) == "Worsening"
    assert trend(0.70, 0.90) == "Improving"
    assert trend(0.80, 0.75) == "Stable"
    assert trend(0.10, 0.05) == "Absent"


def test_worsening_is_reported_in_llm_summary(comparator):
    prior = {"exam_date": "2026-01-01", "findings": {"Pleural Effusion": 0.50}}
    out = comparator.analyze(CURRENT, prior, {}, {})
    assert "Worsening compared to prior exam." in out["llm_prompt_summary"]


# ---------------------------------------------------------------------------
# History / context correlation
# ---------------------------------------------------------------------------

def test_chronic_history_correlation(comparator):
    out = comparator.analyze(CURRENT, None, {"heart_failure": True}, {})

    entry = next(e for e in out["findings_breakdown"] if e["label"] == "Cardiomegaly")
    assert entry["is_chronic"] is True
    assert out["summary"]["chronic_conditions_active"]


def test_acute_symptom_correlation(comparator):
    out = comparator.analyze(CURRENT, None, {}, {"shortness_of_breath": True})

    correlations = out["summary"]["acute_symptoms_correlated"]
    assert any(c["symptom"] == "shortness of breath" for c in correlations)
    all_triggered = sum((c["correlated_findings"] for c in correlations), [])
    assert "Pleural Effusion" in all_triggered
