"""
Agent 1.5 — Suite de tests (Issue G).

Couverture :
  - classify_delta() : chaque catégorie (new/worsening/improving/resolved/stable/unchanged_negative)
  - compute_deltas() : avec et sans antérieur, avec plusieurs antérieurs
  - compare_history() : intégration conditions chroniques, mapping clinique→radiologique
  - Cas limites : premier examen, pas d'antérieur, valeurs None

⚠️  Données de test synthétiques — pas de vraies données patients.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from agent_1_5.delta import classify_delta, compute_deltas
from agent_1_5.models import PriorExam, ComparisonResult, LabelDelta
from agent_1_5.config import SIGNIFICANT_MARGIN


# ── Données synthétiques ────────────────────────────────────────────────
# Toutes les probabilités ci-dessous sont fictives, générées pour couvrir
# les cas de test. Aucun patient réel n'est représenté.

T0 = datetime(2025, 6, 15, tzinfo=timezone.utc)  # examen le plus ancien
T1 = datetime(2025, 9, 20, tzinfo=timezone.utc)  # intermédiaire
T2 = datetime(2026, 1, 10, tzinfo=timezone.utc)  # examen "courant"

# Exemple de structured_findings réalistes (probabilités Agent 1 simulées)
FINDINGS_NO_FINDING = {
    "Atelectasis": 0.02, "Cardiomegaly": 0.03, "Consolidation": 0.01,
    "Edema": 0.01, "Enlarged Cardiomediastinum": 0.05, "Fracture": 0.0,
    "Lung Lesion": 0.0, "Lung Opacity": 0.08, "Pleural Effusion": 0.02,
    "Pleural Other": 0.0, "Pneumonia": 0.01, "Pneumothorax": 0.0,
    "Support Devices": 0.0, "No Finding": 0.85,
}

FINDINGS_CARDIO_PNEUMONIA = {
    "Atelectasis": 0.12, "Cardiomegaly": 0.78, "Consolidation": 0.05,
    "Edema": 0.08, "Enlarged Cardiomediastinum": 0.65, "Fracture": 0.01,
    "Lung Lesion": 0.02, "Lung Opacity": 0.72, "Pleural Effusion": 0.15,
    "Pleural Other": 0.0, "Pneumonia": 0.82, "Pneumothorax": 0.0,
    "Support Devices": 0.0, "No Finding": 0.04,
}

FINDINGS_WORSENED = {
    "Atelectasis": 0.12, "Cardiomegaly": 0.88, "Consolidation": 0.45,
    "Edema": 0.55, "Enlarged Cardiomediastinum": 0.75, "Fracture": 0.01,
    "Lung Lesion": 0.02, "Lung Opacity": 0.91, "Pleural Effusion": 0.12,
    "Pleural Other": 0.0, "Pneumonia": 0.92, "Pneumothorax": 0.0,
    "Support Devices": 0.0, "No Finding": 0.02,
}

FINDINGS_IMPROVED = {
    "Atelectasis": 0.08, "Cardiomegaly": 0.55, "Consolidation": 0.02,
    "Edema": 0.03, "Enlarged Cardiomediastinum": 0.40, "Fracture": 0.0,
    "Lung Lesion": 0.01, "Lung Opacity": 0.60, "Pleural Effusion": 0.05,
    "Pleural Other": 0.0, "Pneumonia": 0.52, "Pneumothorax": 0.0,
    "Support Devices": 0.0, "No Finding": 0.30,
}


# ════════════════════════════════════════════════════════════════════════
# Tests unitaires — classify_delta() (Issue B)
# ════════════════════════════════════════════════════════════════════════

class TestClassifyDelta:
    """Chaque catégorie de delta testée individuellement."""

    def test_new(self):
        """prior < θ, current ≥ θ → new"""
        cat = classify_delta("Cardiomegaly", 0.78, 0.12)
        assert cat == "new"

    def test_worsening(self):
        """Les deux ≥ θ, Δp > margin → worsening"""
        cat = classify_delta("Lung Opacity", 0.91, 0.72)
        assert cat == "worsening"

    def test_improving(self):
        """Les deux ≥ θ, Δp < -margin → improving"""
        # Prior=0.85 (≥0.5), current=0.62 (≥0.5), Δp=-0.23 < -0.15
        cat = classify_delta("Lung Opacity", 0.62, 0.85)
        assert cat == "improving"

    def test_resolved(self):
        """prior ≥ θ, current < θ → resolved"""
        # prior=0.72 (≥0.5), current=0.08 (<0.5) → resolved
        cat = classify_delta("Lung Opacity", 0.08, 0.72)
        assert cat == "resolved"

    def test_stable(self):
        """Les deux ≥ θ, |Δp| ≤ margin → stable"""
        cat = classify_delta("Cardiomegaly", 0.78, 0.75)
        assert cat == "stable"

    def test_unchanged_negative(self):
        """Les deux < θ → unchanged_negative"""
        cat = classify_delta("Fracture", 0.01, 0.01)
        assert cat == "unchanged_negative"

    def test_first_exam_no_prior(self):
        """Pas d'antérieur → new si présent, unchanged_negative si absent."""
        assert classify_delta("Cardiomegaly", 0.78, None) == "new"
        assert classify_delta("Fracture", 0.01, None) == "unchanged_negative"

    def test_current_prob_none(self):
        """current_prob=None traité comme 0."""
        cat = classify_delta("Cardiomegaly", None, 0.78)
        assert cat == "resolved"

    def test_boundary_margin_exact(self):
        """Δp dans la marge, les deux ≥ seuil → stable."""
        # prior=0.52 (≥0.5), current=0.65 (≥0.5), Δp=0.13 < 0.15 → stable
        cat = classify_delta("Atelectasis", 0.65, 0.52)
        assert cat == "stable"

    def test_boundary_margin_just_over(self):
        """Δp juste au-dessus de la marge → worsening."""
        # Δp = 0.16 > 0.15 → worsening (prior=0.50, current=0.66)
        cat = classify_delta("Atelectasis", 0.66, 0.50)
        assert cat == "worsening"

    def test_stable_within_margin(self):
        """Δp positif mais dans la marge → stable."""
        cat = classify_delta("Atelectasis", 0.62, 0.50)  # Δp = 0.12 ≤ 0.15
        assert cat == "stable"
        cat = classify_delta("Atelectasis", 0.50, 0.62)  # Δp = -0.12 ≥ -0.15
        assert cat == "stable"


# ════════════════════════════════════════════════════════════════════════
# Tests — compute_deltas() (Issue A + B)
# ════════════════════════════════════════════════════════════════════════

class TestComputeDeltas:
    """compute_deltas() avec et sans antérieur."""

    def test_no_prior_exam(self):
        """Premier examen : tous new/unchanged_negative, prior_date=None."""
        deltas, prior_date, _ = compute_deltas(FINDINGS_CARDIO_PNEUMONIA, [])
        assert prior_date is None

        cardio = next(d for d in deltas if d["label"] == "Cardiomegaly")
        assert cardio["delta_category"] == "new"
        assert cardio["prior_prob"] is None

        fracture = next(d for d in deltas if d["label"] == "Fracture")
        assert fracture["delta_category"] == "unchanged_negative"

    def test_with_prior_exam_worsening(self):
        """Avec un antérieur : détection worsening."""
        prior = PriorExam(exam_date=T1, structured_findings=FINDINGS_CARDIO_PNEUMONIA)
        # current = FINDINGS_WORSENED : Lung Opacity 0.91 vs prior 0.72, Δp=+0.19 → worsening
        deltas, prior_date, _ = compute_deltas(FINDINGS_WORSENED, [prior])

        assert prior_date == T1

        lung_op = next(d for d in deltas if d["label"] == "Lung Opacity")
        assert lung_op["delta_category"] == "worsening"
        assert lung_op["current_prob"] == 0.91
        assert lung_op["prior_prob"] == 0.72

    def test_with_prior_exam_improving(self):
        """Avec un antérieur : détection improving."""
        # current moins grave que prior
        current = FINDINGS_CARDIO_PNEUMONIA
        prior = PriorExam(exam_date=T1, structured_findings=FINDINGS_WORSENED)
        deltas, prior_date, _ = compute_deltas(current, [prior])

        lung_op = next(d for d in deltas if d["label"] == "Lung Opacity")
        assert lung_op["delta_category"] == "improving"
        assert lung_op["current_prob"] == 0.72
        assert lung_op["prior_prob"] == 0.91

    def test_multiple_prior_exams(self):
        """Plusieurs antérieurs : seul le plus récent est utilisé pour le delta."""
        prior_old = PriorExam(exam_date=T0, structured_findings=FINDINGS_NO_FINDING)
        prior_recent = PriorExam(exam_date=T1, structured_findings=FINDINGS_CARDIO_PNEUMONIA)
        deltas, prior_date, _ = compute_deltas(FINDINGS_WORSENED, [prior_recent, prior_old])

        # Le plus récent (T1) doit être la référence
        assert prior_date == T1
        cardio = next(d for d in deltas if d["label"] == "Cardiomegaly")
        assert cardio["prior_prob"] == 0.78  # from T1, not T0

    def test_all_14_labels_present(self):
        """Les deltas couvrent bien les 14 labels standards."""
        prior = PriorExam(exam_date=T1, structured_findings=FINDINGS_CARDIO_PNEUMONIA)
        deltas, _, _ = compute_deltas(FINDINGS_WORSENED, [prior])
        assert len(deltas) == 14


# ════════════════════════════════════════════════════════════════════════
# Tests — reclassify_chronic (Issue C) — pure function, pas de mock DB
# ════════════════════════════════════════════════════════════════════════

class TestReclassifyChronic:
    """reclassify_chronic() est une fonction pure — pas de mock DB nécessaire.

    ⚠️  SÉCURITÉ CLINIQUE (Issue K, Round 3c) :
    - La reclassification ne s'applique QUE sur le premier examen
    - Seules les correspondances directes Heart Disease/Hypertension→Cardiomegaly
      sont retenues (pas de mapping épidémiologique large)
    """

    def test_chronic_reclassifies_new_to_stable(self):
        """Heart Disease → Cardiomegaly reclassé stable sur premier examen."""
        from agent_1_5.comparator import reclassify_chronic

        raw = [
            {"label": "Cardiomegaly", "delta_category": "new",
             "current_prob": 0.78, "prior_prob": None,
             "reference_exam_date": None},
            {"label": "Fracture", "delta_category": "new",
             "current_prob": 0.01, "prior_prob": None,
             "reference_exam_date": None},
        ]
        result = reclassify_chronic(raw, ["Heart Disease"], prior_exam_count=0)

        # Cardiomegaly: new → stable (Heart Disease)
        assert result[0].delta_category == "stable"
        assert result[0].known_chronic is True

        # Fracture: pas associé à Heart Disease → reste new
        assert result[1].delta_category == "new"
        assert result[1].known_chronic is False

    def test_no_chronic_keeps_new(self):
        """Sans condition chronique, les 'new' restent 'new'."""
        from agent_1_5.comparator import reclassify_chronic

        raw = [
            {"label": "Cardiomegaly", "delta_category": "new",
             "current_prob": 0.78, "prior_prob": None,
             "reference_exam_date": None},
            {"label": "Pneumonia", "delta_category": "new",
             "current_prob": 0.82, "prior_prob": None,
             "reference_exam_date": None},
        ]
        result = reclassify_chronic(raw, [], prior_exam_count=0)

        assert result[0].delta_category == "new"
        assert result[0].known_chronic is False
        assert result[1].delta_category == "new"
        assert result[1].known_chronic is False

    def test_multiple_chronic_conditions(self):
        """Plusieurs conditions chroniques s'additionnent."""
        from agent_1_5.comparator import reclassify_chronic

        raw = [
            {"label": "Cardiomegaly", "delta_category": "new",
             "current_prob": 0.78, "prior_prob": None,
             "reference_exam_date": None},
            {"label": "Enlarged Cardiomediastinum", "delta_category": "new",
             "current_prob": 0.65, "prior_prob": None,
             "reference_exam_date": None},
        ]
        # Heart Disease + Hypertension → toutes deux mappent vers les deux labels
        result = reclassify_chronic(raw, ["Heart Disease", "Hypertension"],
                                    prior_exam_count=0)
        assert result[0].delta_category == "stable"  # Heart Disease → Cardiomegaly
        assert result[0].known_chronic is True
        assert result[1].delta_category == "stable"  # Hypertension → Enlarged CM
        assert result[1].known_chronic is True

    def test_non_new_not_affected(self):
        """Les catégories autres que 'new' ne sont pas modifiées."""
        from agent_1_5.comparator import reclassify_chronic

        raw = [
            {"label": "Cardiomegaly", "delta_category": "worsening",
             "current_prob": 0.88, "prior_prob": 0.50,
             "reference_exam_date": None},
            {"label": "Lung Opacity", "delta_category": "improving",
             "current_prob": 0.30, "prior_prob": 0.72,
             "reference_exam_date": None},
        ]
        result = reclassify_chronic(raw, ["Heart Disease", "COPD"],
                                    prior_exam_count=0)
        assert result[0].delta_category == "worsening"  # unchanged
        assert result[1].delta_category == "improving"  # unchanged

    # ── SÉCURITÉ CLINIQUE : complications aiguës non masquées ────────────

    def test_complication_not_masked_by_chronic(self):
        """BPCO + antérieur : Pneumothorax négatif→positif reste 'new'.

        Cas clinique : patient BPCO documenté, examen antérieur sans pneumothorax,
        examen actuel avec pneumothorax. C'est une complication aiguë, pas
        une condition chronique stable. La reclassification ne doit PAS
        s'appliquer car un antérieur existe (prior_exam_count > 0).
        """
        from agent_1_5.comparator import reclassify_chronic

        raw = [
            {"label": "Pneumothorax", "delta_category": "new",
             "current_prob": 0.85, "prior_prob": 0.03,
             "reference_exam_date": "2026-07-01"},
        ]
        # COPD noté dans known_conditions, mais prior_exam_count > 0 → pas de reclassif
        result = reclassify_chronic(raw, ["COPD"], prior_exam_count=1)

        assert result[0].delta_category == "new", \
            "Un pneumothorax aigu chez un BPCO ne doit pas être masqué"
        assert result[0].known_chronic is False

    def test_heart_disease_edema_not_masked(self):
        """Cardiopathie + antérieur : Oedème négatif→positif reste 'new'.

        Cas clinique : patient avec cardiopathie connue, examen antérieur sans
        oedème, examen actuel avec oedème pulmonaire. Décompensation cardiaque
        = urgence réelle. Le mapping Heart Disease n'inclut PAS Edema, donc
        même sur premier examen ce serait 'new'. Avec antérieur, c'est aussi 'new'.
        """
        from agent_1_5.comparator import reclassify_chronic

        raw = [
            {"label": "Edema", "delta_category": "new",
             "current_prob": 0.82, "prior_prob": 0.05,
             "reference_exam_date": "2026-07-01"},
        ]
        result = reclassify_chronic(raw, ["Heart Disease"], prior_exam_count=1)

        assert result[0].delta_category == "new", \
            "Un oedème aigu chez un cardiaque ne doit pas être masqué"
        assert result[0].known_chronic is False

    def test_copd_not_in_mapping_at_all(self):
        """COPD n'a plus de mapping direct → même sur premier examen reste 'new'.

        La condition COPD n'a pas de correspondance RX directe parmi les 14
        labels CheXpert. Sur le premier examen, un label comme Lung Opacity
        chez un patient BPCO doit rester 'new' car il pourrait être une
        pneumopathie infectieuse, pas seulement la BPCO.
        """
        from agent_1_5.comparator import reclassify_chronic

        raw = [
            {"label": "Lung Opacity", "delta_category": "new",
             "current_prob": 0.72, "prior_prob": None,
             "reference_exam_date": None},
        ]
        result = reclassify_chronic(raw, ["COPD"], prior_exam_count=0)

        # COPD n'est plus dans le mapping → reste 'new'
        assert result[0].delta_category == "new"
        assert result[0].known_chronic is False

    def test_prior_exam_blocks_all_reclassification(self):
        """Même avec Heart Disease, un antérieur bloque toute reclassification."""
        from agent_1_5.comparator import reclassify_chronic

        raw = [
            {"label": "Cardiomegaly", "delta_category": "new",
             "current_prob": 0.78, "prior_prob": 0.08,
             "reference_exam_date": "2026-07-01"},
        ]
        result = reclassify_chronic(raw, ["Heart Disease"], prior_exam_count=1)

        # prior_exam_count > 0 → pas de reclassif, même pour Heart Disease→Cardiomegaly
        assert result[0].delta_category == "new"
        assert result[0].known_chronic is False


# ════════════════════════════════════════════════════════════════════════
# Tests — sérialisation et endpoint (Issue E + F)
# ════════════════════════════════════════════════════════════════════════

class TestComparisonResultFormat:
    """Vérification du format de sortie compatible Agent 3."""

    def test_label_delta_serializable(self):
        """LabelDelta → dict doit être directement JSON-serializable."""
        ld = LabelDelta(
            label="Cardiomegaly",
            delta_category="new",
            current_prob=0.78,
            prior_prob=None,
            reference_exam_date=None,
            known_chronic=False,
        )
        d = ld.model_dump(mode="json")
        assert d["label"] == "Cardiomegaly"
        assert d["delta_category"] == "new"
        assert d["current_prob"] == 0.78
        assert d["prior_prob"] is None

    def test_comparison_result_serializable(self):
        """ComparisonResult → dict doit inclure config_version et config_hash."""
        d = ComparisonResult(
            patient_id="P001",
            current_exam_id=1,
            current_exam_date=T2,
            deltas=[],
            prior_exam_count=1,
            config_version="1.0.0",
            config_hash="a1b2c3d4e5f6",
        ).model_dump(mode="json")
        assert d["config_version"] == "1.0.0"
        assert d["config_hash"] == "a1b2c3d4e5f6"
