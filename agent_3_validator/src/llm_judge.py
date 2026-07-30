"""
Agent 3 - Layer 2: LLM-as-a-Judge.
If Layer 1 finds a mismatch, this module uses Qwen2-VL to rewrite the report 
to fix the hallucination/omission based on Agent 1's ground truth.
"""
import torch
from transformers import Qwen2VLForConditionalGeneration, Qwen2VLProcessor, BitsAndBytesConfig
from peft import PeftModel

class LLMJudge:
    def __init__(self, model_id="Qwen/Qwen2-VL-7B-Instruct", checkpoint_path="/workspace/agent_2/checkpoints/checkpoint-1000"):
        print("Loading LLM Judge (Qwen2-VL)...")
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )
        self.model = Qwen2VLForConditionalGeneration.from_pretrained(
            model_id, quantization_config=bnb_config, device_map="auto"
        )
        self.model = PeftModel.from_pretrained(self.model, checkpoint_path)
        self.model.eval()
        self.processor = Qwen2VLProcessor.from_pretrained(model_id)

    def fix_report(self, original_report, agent1_predictions, errors):
        """
        Asks the LLM to rewrite the report fixing the specific errors found by Layer 1.
        """
        # Format Agent 1's positive findings for the prompt
        positive_findings = [label for label, prob in agent1_predictions.items() if prob >= 0.5]
        findings_str = ", ".join(positive_findings) if positive_findings else "None"
        errors_str = "\n".join([f"- {e}" for e in errors])

        prompt_text = f"""You are a clinical AI validator. Your previous radiology report contained errors.
Please rewrite the report to fix these errors. You must strictly adhere to the ground truth predictions provided by Agent 1.

[Agent 1 Ground Truth Predictions]: {findings_str}
[Errors found in your previous report]:
{errors_str}

[Your Previous Report]:
{original_report}

Please rewrite the entire report (FINDINGS and IMPRESSION) now, ensuring it perfectly matches the Agent 1 Ground Truth:"""

        messages = [{"role": "user", "content": [{"type": "text", "text": prompt_text}]}]
        text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.processor(text=[text], return_tensors="pt").to("cuda")

        with torch.no_grad():
            output_ids = self.model.generate(
                **inputs, max_new_tokens=512, do_sample=True, temperature=0.3, top_p=0.9
            )

        generated_ids = [output_ids[len(input_ids):] for input_ids, output_ids in zip(inputs.input_ids, output_ids)]
        corrected_report = self.processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        
        return corrected_report
