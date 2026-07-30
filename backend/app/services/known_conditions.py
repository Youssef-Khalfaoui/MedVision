"""Service — conversion PatientMedicalHistory → liste de labels textuels.

Utilisé par Agent 1.5 (known_conditions pour la comparaison historique)
et Agent 3 (contexte pour la validation).

Cette fonction est le SEUL point de conversion autorisé — ne pas dupliquer
cette logique ailleurs.
"""

_HISTORY_LABELS: dict[str, str] = {
    "prior_pneumonia": "Prior Pneumonia",
    "tuberculosis_history": "Tuberculosis History",
    "copd": "COPD",
    "asthma": "Asthma",
    "heart_disease": "Heart Disease",
    "diabetes": "Diabetes",
    "hypertension": "Hypertension",
}


def to_known_conditions(history: object) -> list[str]:
    """Convertit un objet PatientMedicalHistory en liste de labels.

    Args:
        history: Instance PatientMedicalHistory ou tout objet avec attributs
                 correspondant aux booléens de _HISTORY_LABELS.

    Returns:
        Liste triée des labels pour lesquels le booléen est vrai.
        Retourne [] si history est None.
    """
    if history is None:
        return []

    labels: list[str] = []
    for field, label in _HISTORY_LABELS.items():
        value = getattr(history, field, False)
        if value:
            labels.append(label)

    smoking = getattr(history, "smoking_status", None)
    if smoking:
        smoking_label = {
            "never": "Never Smoker",
            "former": "Former Smoker",
            "current": "Current Smoker",
        }.get(smoking.value if hasattr(smoking, "value") else str(smoking))
        if smoking_label:
            labels.append(smoking_label)

    labels.sort()
    return labels
