"""
Agent 1.5 - Clinical Trend & History Comparator
Analyzes current Agent 1 predictions against prior exams, chronic medical history,
and current clinical context to produce a structured trend analysis.
This output is fed into Agent 2 (LLM) to ground the report generation in factual patient history.
"""
import json
from datetime import datetime

# The 14 CheXpert labels
CATEGORIES = [
    "No Finding", "Enlarged Cardiomediastinum", "Cardiomegaly", "Lung Opacity",
    "Lung Lesion", "Edema", "Consolidation", "Pneumonia", "Atelectasis",
    "Pneumothorax", "Pleural Effusion", "Pleural Other", "Fracture",
    "Support Devices",
]

# Mapping chronic history booleans to relevant CheXpert labels
HISTORY_MAPPING = {
    "prior_pneumonia": ["Pneumonia", "Consolidation", "Lung Opacity"],
    "copd": ["Lung Opacity", "Pneumothorax", "Atelectasis"],
    "asthma": ["Atelectasis", "Lung Opacity"],
    "heart_disease": ["Cardiomegaly", "Enlarged Cardiomediastinum"],
    "heart_failure": ["Edema", "Pleural Effusion", "Cardiomegaly"],
}

# Mapping acute clinical context to relevant CheXpert labels
CONTEXT_MAPPING = {
    "fever": ["Pneumonia", "Consolidation"],
    "cough": ["Pneumonia", "Lung Opacity", "Atelectasis"],
    "shortness_of_breath": ["Edema", "Pleural Effusion", "Pneumothorax", "Cardiomegaly"],
    "chest_pain": ["Pneumothorax", "Fracture", "Consolidation"],
}

class Agent1_5_Comparator:
    def __init__(self, threshold=0.5, delta_threshold=0.15):
        self.threshold = threshold
        self.delta_threshold = delta_threshold

    def _calculate_trend(self, current_prob, prior_prob):
        """Calculates the trend of a specific label."""
        current_pos = current_prob >= self.threshold
        prior_pos = prior_prob >= self.threshold

        if not prior_pos and current_pos:
            return "New Finding"
        elif prior_pos and not current_pos:
            return "Resolving"
        elif prior_pos and current_pos:
            delta = current_prob - prior_prob
            if delta > self.delta_threshold:
                return "Worsening"
            elif delta < -self.delta_threshold:
                return "Improving"
            else:
                return "Stable"
        else:
            return "Absent"

    def analyze(self, current_findings, prior_exam=None, medical_history=None, clinical_context=None):
        """
        Main analysis function.
        
        :param current_findings: dict of 14 probabilities from Agent 1
        :param prior_exam: dict containing 'findings' (14 probs) and 'exam_date'
        :param medical_history: dict from PatientMedicalHistory table
        :param clinical_context: dict from ExamClinicalContext table
        :return: dict structured for the `comparison_result` JSON field and Agent 2 prompt
        """
        if medical_history is None: medical_history = {}
        if clinical_context is None: clinical_context = {}

        trend_analysis = []
        active_chronic_conditions = []
        acute_correlations = []

        # 1. Compare Current vs Prior Exam
        has_prior = prior_exam is not None and "findings" in prior_exam
        prior_date_str = prior_exam["exam_date"].strftime('%Y-%m-%d') if has_prior else None

        for label in CATEGORIES:
            current_prob = current_findings.get(label, 0.0)
            prior_prob = prior_exam["findings"].get(label, 0.0) if has_prior else 0.0
            
            trend = self._calculate_trend(current_prob, prior_prob)
            
            # Only report on positive findings or significant trends
            if current_prob >= self.threshold or trend in ["Resolving", "Improving", "Worsening"]:
                entry = {
                    "label": label,
                    "current_probability": round(current_prob, 4),
                    "trend": trend,
                    "prior_probability": round(prior_prob, 4) if has_prior else None
                }
                if has_prior:
                    entry["prior_date"] = prior_date_str
                
                # Check if this is a chronic condition
                is_chronic = False
                for hist_key, related_labels in HISTORY_MAPPING.items():
                    if medical_history.get(hist_key, False) and label in related_labels:
                        entry["is_chronic"] = True
                        is_chronic = True
                        if trend == "Stable" or trend == "New Finding":
                            active_chronic_conditions.append(f"Chronic {label} ({hist_key.replace('_', ' ')})")
                        break
                if not is_chronic:
                    entry["is_chronic"] = False

                trend_analysis.append(entry)

        # 2. Analyze Acute Clinical Context
        for ctx_key, related_labels in CONTEXT_MAPPING.items():
            if clinical_context.get(ctx_key, False):
                # Find if any related label is positive in current findings
                triggered_labels = [l for l in related_labels if current_findings.get(l, 0.0) >= self.threshold]
                if triggered_labels:
                    acute_correlations.append({
                        "symptom": ctx_key.replace('_', ' '),
                        "correlated_findings": triggered_labels
                    })

        # 3. Construct Final Structured Output
        output = {
            "summary": {
                "has_prior_exam": has_prior,
                "prior_exam_date": prior_date_str,
                "chronic_conditions_active": list(set(active_chronic_conditions)),
                "acute_symptoms_correlated": acute_correlations
            },
            "findings_breakdown": trend_analysis
        }

        # Generate a text summary specifically for the LLM prompt
        output["llm_prompt_summary"] = self._generate_llm_summary(output)
        return output

    def _generate_llm_summary(self, analysis):
        """Converts the structured JSON into a concise text string for the Agent 2 LLM prompt."""
        summary_parts = []
        
        if analysis["summary"]["has_prior_exam"]:
            summary_parts.append(f"Comparison to prior exam from {analysis['summary']['prior_exam_date']}:")
        else:
            summary_parts.append("No prior exams available for comparison. All findings are new.")

        for finding in analysis["findings_breakdown"]:
            trend = finding["trend"]
            label = finding["label"]
            
            if trend == "New Finding":
                txt = f"- {label}: New finding detected."
            elif trend == "Resolving":
                txt = f"- {label}: Resolving (was present in prior exam)."
            elif trend == "Worsening":
                txt = f"- {label}: Worsening compared to prior exam."
            elif trend == "Improving":
                txt = f"- {label}: Improving compared to prior exam."
            elif trend == "Stable":
                txt = f"- {label}: Stable chronic finding."
            else:
                continue
                
            if finding["is_chronic"]:
                txt += " (Correlates with patient's chronic medical history)."
            summary_parts.append(txt)

        if analysis["summary"]["acute_symptoms_correlated"]:
            summary_parts.append("\nClinical Context Correlations:")
            for corr in analysis["summary"]["acute_symptoms_correlated"]:
                summary_parts.append(f"- Patient presents with {corr['symptom']}, which correlates with detected {', '.join(corr['correlated_findings'])}.")

        return "\n".join(summary_parts)

# --- Example Usage / Smoke Test ---
if __name__ == "__main__":
    comparator = Agent1_5_Comparator()

    # Mock data matching the database schema
    current_findings = {
        "No Finding": 0.1, "Cardiomegaly": 0.85, "Pleural Effusion": 0.72, 
        "Edema": 0.45, "Pneumonia": 0.15, "Fracture": 0.0
    }
    
    prior_exam = {
        "exam_date": datetime(2023, 5, 12),
        "findings": {"Cardiomegaly": 0.82, "Pleural Effusion": 0.65, "Edema": 0.20}
    }
    
    medical_history = {
        "heart_failure": True, "copd": False, "prior_pneumonia": False
    }
    
    clinical_context = {
        "shortness_of_breath": True, "fever": False
    }

    result = comparator.analyze(current_findings, prior_exam, medical_history, clinical_context)
    
    print("=== JSON for DB (comparison_result) ===")
    print(json.dumps(result, indent=2))
    
    print("\n=== Text for Agent 2 LLM Prompt ===")
    print(result["llm_prompt_summary"])
