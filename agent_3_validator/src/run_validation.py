"""
Agent 3 - Orchestrator.
Runs the Dual-Layer Validation process.
"""
import json
from validator import validate_report

# We only import the LLM Judge if we need to actually fix something
# (This prevents loading the 15GB model if the report is already perfect)
def run_agent3(generated_text, agent1_predictions, llm_judge=None):
    print("--- Running Agent 3 Layer 1: Deterministic Check ---")
    validation_result = validate_report(generated_text, agent1_predictions)
    
    if validation_result["verdict"] == "PASS":
        print("✅ Layer 1 PASSED. Report is clinically accurate.")
        return generated_text, validation_result
    
    print("❌ Layer 1 FAILED. Errors detected:")
    for err in validation_result["errors"]:
        print(f"  -> {err}")
        
    if llm_judge is None:
        print("\n[WARNING] LLM Judge not initialized. Cannot auto-correct. Returning original text.")
        return generated_text, validation_result

    print("\n--- Running Agent 3 Layer 2: LLM-as-a-Judge Correction ---")
    corrected_text = llm_judge.fix_report(generated_text, agent1_predictions, validation_result["errors"])
    
    # Run Layer 1 again on the corrected text to ensure the LLM actually fixed it
    print("\n--- Re-validating Corrected Report ---")
    re_validation = validate_report(corrected_text, agent1_predictions)
    
    if re_validation["verdict"] == "PASS":
        print("✅ Layer 2 Correction SUCCESSFUL. Report is now clinically accurate.")
    else:
        print("⚠️ Layer 2 Correction still has minor discrepancies, but returning best effort.")
        
    return corrected_text, re_validation

# --- Example Usage ---
if __name__ == "__main__":
    # Mock data
    mock_agent1_preds = {
        "Cardiomegaly": 0.85,
        "Pleural Effusion": 0.72,
        "Edema": 0.12,
        "Pneumonia": 0.08
    }
    
    # A bad report that hallucinates and omits findings
    bad_report = "FINDINGS: The lungs are clear. There is no pneumonia. IMPRESSION: No acute cardiopulmonary findings."
    
    # To test this fully, you would initialize the LLM Judge like this:
    # from llm_judge import LLMJudge
    # judge = LLMJudge(checkpoint_path="/workspace/agent_2/checkpoints/checkpoint-1000")
    # final_text, final_verdict = run_agent3(bad_report, mock_agent1_preds, llm_judge=judge)
    
    # For now, we test Layer 1 without the GPU:
    print("Testing Layer 1 Orchestrator (CPU only)...")
    final_text, final_verdict = run_agent3(bad_report, mock_agent1_preds, llm_judge=None)
    
    print("\n=== FINAL VERDICT ===")
    print(json.dumps(final_verdict, indent=2))
