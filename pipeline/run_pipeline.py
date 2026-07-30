"""
MedVision End-to-End Pipeline Orchestrator.
Runs a single image through Agent 0 -> 1 -> 1.5 -> 2 -> 3.
"""
import os
import sys
import json
import cv2
import base64
import torch
import numpy as np
from PIL import Image
import torchvision.transforms.functional as F_tv

# Add all agent src directories to path
sys.path.extend([
    '/workspace/agent_guard/src',
    '/workspace/agent_1_v2/src',
    '/workspace/agent_1_5_comparator/src',
    '/workspace/agent_2_report/src',
    '/workspace/agent_3_validator/src'
])

# Import Agent 0 & 1
from guard_model import GuardAgent
from convnext_predictor import ConvNeXtPredictor, CATEGORIES
# Import Agent 1.5
from comparator import Agent1_5_Comparator
# Import Agent 3 (Layer 1)
from validator import validate_report, force_correct_report


class GradCAM:
    def __init__(self, model, target_layer):
        self.model = model
        self.target_layer = target_layer
        self.gradients = None
        self.activations = None
        target_layer.register_forward_hook(self.save_activation)
        target_layer.register_full_backward_hook(self.save_gradient)

    def save_activation(self, module, input, output):
        self.activations = output

    def save_gradient(self, module, grad_input, grad_output):
        self.gradients = grad_output[0]

    def __call__(self, x, class_idx):
        self.model.eval()
        out = self.model(x, apply_hierarchy=False)
        cal_logits = out["calibrated_logits"]
        self.model.zero_grad()
        cal_logits[0, class_idx].backward(retain_graph=False)
        gradients = self.gradients.cpu().detach().numpy()[0]
        activations = self.activations.cpu().detach().numpy()[0]
        weights = np.mean(gradients, axis=(1, 2))
        cam = np.zeros(activations.shape[1:], dtype=np.float32)
        for i, w in enumerate(weights):
            cam += w * activations[i, :, :]
        cam = np.maximum(cam, 0)
        cam = cv2.resize(cam, (x.shape[-1], x.shape[-2]))
        cam = cam - np.min(cam)
        cam = cam / np.max(cam)
        return cam

class MedVisionPipeline:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Initializing MedVision Pipeline on {self.device}...")
        
        # 1. Load Agent 0 (Guard)
        print("-> Loading Agent 0 (Guard)...")
        self.agent0 = GuardAgent().to(self.device)
        agent0_ckpt = torch.load("/workspace/agent_guard/checkpoints/best_guard.pt", map_location=self.device)
        self.agent0.load_state_dict(agent0_ckpt)
        self.agent0.eval()
        
        # 2. Load Agent 1 (ConvNeXt + GAT)
        print("-> Loading Agent 1 (ConvNeXtV2)...")
        self.agent1 = ConvNeXtPredictor(pretrained_backbone=False).to(self.device)
        if os.path.exists("/data/label_output/cooccurrence_edges.pt"):
            edge_index = torch.load("/data/label_output/cooccurrence_edges.pt", map_location=self.device)
            self.agent1.set_cooccurrence_edges(edge_index)
        agent1_ckpt = torch.load("/workspace/agent_1_v2/checkpoints/best_model.pt", map_location=self.device)
        self.agent1.load_state_dict(agent1_ckpt)
        self.agent1.eval()
        
        # 3. Load Agent 1.5 (Comparator)
        self.agent1_5 = Agent1_5_Comparator()
        
        # 4. Load Agent 2 & 3 (Qwen2-VL LLM)
        print("-> Loading Agent 2/3 (Qwen2-VL 7B 4-bit)...")
        from transformers import Qwen2VLForConditionalGeneration, Qwen2VLProcessor, BitsAndBytesConfig
        from peft import PeftModel
        
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4", 
            bnb_4bit_compute_dtype=torch.float16, bnb_4bit_use_double_quant=True,
        )
        self.llm = Qwen2VLForConditionalGeneration.from_pretrained(
            "Qwen/Qwen2-VL-7B-Instruct", quantization_config=bnb_config, device_map="auto"
        )
        self.llm = PeftModel.from_pretrained(self.llm, "/workspace/agent_2_report/checkpoints/checkpoint-9000")
        self.llm.eval()
        self.processor = Qwen2VLProcessor.from_pretrained(
            "Qwen/Qwen2-VL-7B-Instruct",
            min_pixels=256 * 28 * 28,
            max_pixels=1024 * 28 * 28,
        )
        print("Pipeline initialization complete!\n" + "="*50 + "\n")

    def _preprocess_agent0(self, image_path):
        """Agent 0 (Guard) expects 1-channel, 224x224, torchxrayvision-style [-1024, 1024] normalization."""
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise ValueError(f"Could not read image at {image_path}")
        img = cv2.resize(img, (224, 224), interpolation=cv2.INTER_AREA)
        img = img.astype(np.float32)
        img = (2 * (img / 255.0) - 1.0) * 1024.0
        tensor = torch.from_numpy(img).float().unsqueeze(0)
        return tensor

    def _preprocess_agent1(self, image_path):
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        img = cv2.resize(img, (512, 512), interpolation=cv2.INTER_AREA)
        img = img.astype(np.float32) / 255.0
        img_3ch = np.stack([img, img, img], axis=0)
        tensor = torch.from_numpy(img_3ch).float()
        mean = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
        std = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)
        return (tensor - mean) / std

    def run(self, image_path, prior_exam=None, chronic_history=None, clinical_context=None):
        print("[Agent 0] Validating image...")
        agent0_input = self._preprocess_agent0(image_path).unsqueeze(0).to(self.device)
        with torch.no_grad():
            guard_logit = self.agent0(agent0_input)
            guard_prob = torch.sigmoid(guard_logit).item()
        del agent0_input
        torch.cuda.empty_cache()

        if guard_prob < 0.5:
            print(f"  -> REJECTED. Guard confidence: {guard_prob:.4f} (not a valid chest X-ray)")
            return {
                "image_path": image_path,
                "error": "invalid_image",
                "message": "Uploaded image is not a valid chest X-ray. Please upload a PA or AP chest radiograph.",
                "guard_confidence": guard_prob,
            }
        print(f"  -> ACCEPTED. Guard confidence: {guard_prob:.4f}")

        print("[Agent 1] Running pathology classification (4-way TTA)...")
        input_tensor = self._preprocess_agent1(image_path).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            out = self.agent1(input_tensor, apply_hierarchy=True)
            probs = out["probabilities"].cpu().numpy()[0]
            
            flips = [torch.flip(input_tensor, dims=[-1]), input_tensor]
            rots = [
                F_tv.affine(input_tensor, angle=10, translate=[0,0], scale=1, shear=[0,0], interpolation=F_tv.InterpolationMode.BILINEAR, fill=[-2.1179, -2.0357, -1.8044]),
                F_tv.affine(input_tensor, angle=-10, translate=[0,0], scale=1, shear=[0,0], interpolation=F_tv.InterpolationMode.BILINEAR, fill=[-2.1179, -2.0357, -1.8044])
            ]
            
            for aug in flips + rots:
                out_aug = self.agent1(aug, apply_hierarchy=True)
                probs = (probs + out_aug["probabilities"].cpu().numpy()[0]) / 2.0
                
        agent1_preds = {CATEGORIES[i]: float(probs[i]) for i in range(14)}
        print(f"  -> Top Finding: {max(agent1_preds, key=agent1_preds.get)} ({max(agent1_preds.values()):.2f}%)")

        # Generate Grad-CAM
        gradcam_base64 = None
        positive_findings = [k for k, v in agent1_preds.items() if v >= 0.5 and k != "No Finding"]
        if not positive_findings:
            positive_findings = ["No Finding"]
        if positive_findings:
            best_label = max(positive_findings, key=agent1_preds.get)
            print(f"[Agent 1] Generating Grad-CAM for: {best_label}")
            target_layer = self.agent1.backbone.backbone.stages[-1]
            grad_cam = GradCAM(self.agent1, target_layer)
            
            input_tensor.requires_grad = True
            best_idx = CATEGORIES.index(best_label)
            cam = grad_cam(input_tensor, best_idx)
            
            heatmap = cv2.applyColorMap(np.uint8(255 * cam), cv2.COLORMAP_JET)
            orig_img = cv2.imread(image_path)
            orig_img = cv2.resize(orig_img, (512, 512))
            overlay = cv2.addWeighted(orig_img, 0.5, heatmap, 0.5, 0)
            _, buffer = cv2.imencode('.png', overlay)
            gradcam_base64 = base64.b64encode(buffer).decode('utf-8')

            input_tensor.requires_grad = False
            del grad_cam
            torch.cuda.empty_cache()

        print("[Agent 1.5] Analyzing patient history & trends...")
        # Use real patient data when provided (from backend DB query)
        # Falls back to empty defaults when no prior data exists
        if prior_exam or chronic_history or clinical_context:
            trend_data = self.agent1_5.analyze(
                agent1_preds,
                prior_exam or {},
                chronic_history or {},
                clinical_context or {},
            )
        else:
            # No prior data available — trend analysis with empty context
            trend_data = self.agent1_5.analyze(
                agent1_preds,
                {},
                {},
                {},
            )
        print(f"  -> Trend Summary: {trend_data['llm_prompt_summary'].splitlines()[0] if trend_data['llm_prompt_summary'] else '(no history)'}")

        print("[Agent 2] Generating Clinical Report...")
        positive_findings = [k for k, v in agent1_preds.items() if v >= 0.5 and k != "No Finding"]
        if not positive_findings:
            positive_findings = ["No Finding"]
        
        # Prepare strings outside of f-string to avoid backslash issues
        findings_str = ", ".join(positive_findings) if positive_findings else "No acute findings"
        history_str = trend_data["llm_prompt_summary"]
        
        prompt_text = (
            "You are an expert radiologist. Write a detailed radiology report for this chest X-ray.\n"
            f"CRITICAL INSTRUCTION: A computer vision model has detected the following acute findings: {findings_str}.\n"
            "You MUST explicitly mention these findings in your report. DO NOT say the lungs are clear. DO NOT say 'No acute findings'.\n"
            f"Patient History:\n{history_str}\n"
            "Please provide the report in the following format:\nFINDINGS: ...\nIMPRESSION: ..."
        )

        image = Image.open(image_path).convert("RGB")
        print(f"  [debug] VLM input image size: {image.size}")
        messages = [{"role": "user", "content": [{"type": "image", "image": image}, {"type": "text", "text": prompt_text}]}]
        text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.processor(text=[text], images=[image], return_tensors="pt").to("cuda")
        
        try:
            with torch.no_grad():
                output_ids = self.llm.generate(**inputs, max_new_tokens=512, do_sample=True, temperature=0.3, top_p=0.9)
            generated_ids = [output_ids[len(i):] for i, output_ids in zip(inputs.input_ids, output_ids)]
        finally:
            del inputs
            torch.cuda.empty_cache()
        clinical_report = self.processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        print("  -> Report Draft Generated.")

        print("[Agent 3] Validating report (Layer 1: Deterministic)...")
        validation_result = validate_report(clinical_report, agent1_preds)
        
        if validation_result["verdict"] == "FAIL":
            print(f"  -> Layer 1 FAILED: {validation_result['errors']}")
            print("[Agent 3] Correcting report (Layer 2: LLM-as-a-Judge)...")
            
            errors_str = "\n".join([f"- {e}" for e in validation_result["errors"]])
            truth_str = ", ".join(positive_findings)
            
            fix_prompt = (
                "You are a clinical AI validator. Your previous radiology report contained errors.\n"
                "Please rewrite the report to fix these errors. You must strictly adhere to the ground truth predictions provided by Agent 1.\n"
                f"[Agent 1 Ground Truth]: {truth_str}\n"
                "[Errors found]:\n"
                f"{errors_str}\n"
                "[Your Previous Report]:\n"
                f"{clinical_report}\n"
                "Please rewrite the entire report (FINDINGS and IMPRESSION) now:"
            )
            
            messages_fix = [{"role": "user", "content": [{"type": "image", "image": image}, {"type": "text", "text": fix_prompt}]}]
            text_fix = self.processor.apply_chat_template(messages_fix, tokenize=False, add_generation_prompt=True)
            inputs_fix = self.processor(text=[text_fix], images=[image], return_tensors="pt").to("cuda")
            
            with torch.no_grad():
                fix_ids = self.llm.generate(**inputs_fix, max_new_tokens=512, do_sample=True, temperature=0.3, top_p=0.9)
            fixed_ids = [fix_ids[len(i):] for i, fix_ids in zip(inputs_fix.input_ids, fix_ids)]
            final_report = self.processor.batch_decode(fixed_ids, skip_special_tokens=True)[0]
            print("  -> Layer 2 Correction Applied.")
            print(f"  [debug] Layer 2 output:\n{final_report}")

            print("[Agent 3] Re-validating report after Layer 2 correction...")
            validation_result = validate_report(final_report, agent1_preds)
            corrected_deterministically = False
            if validation_result["verdict"] == "FAIL":
                print(f"  -> Layer 2 STILL FAILING: {validation_result['errors']}")
                print("[Agent 3] Applying deterministic correction (safety net)...")
                final_report = force_correct_report(final_report, validation_result.get("missing_or_contradicted", []))
                validation_result = validate_report(final_report, agent1_preds)
                corrected_deterministically = True
                if validation_result["verdict"] == "FAIL":
                    print(f"  -> Deterministic correction insufficient: {validation_result['errors']}")
                    needs_review = True
                else:
                    print("  -> Deterministic correction succeeded: report now aligned.")
                    needs_review = False
            else:
                print("  -> Layer 2 correction verified: report now aligned.")
                needs_review = False
        else:
            print("  -> Layer 1 PASSED. Report is mathematically aligned.")
            final_report = clinical_report
            needs_review = False
            corrected_deterministically = False

        patient_report = None
        if not needs_review:
            print("[Agent 4] Generating patient-friendly report...")
            patient_prompt = (
                "You are a radiologist explaining a chest X-ray report to the patient, in plain language.\n"
                "Rewrite the following validated clinical report into a short, clear summary a patient with no medical background can understand.\n"
                "Rules:\n"
                "- Do NOT invent, omit, or soften any finding present in the clinical report.\n"
                "- Avoid medical jargon; explain any technical term you must keep.\n"
                "- Keep a calm, reassuring, non-alarming tone, but stay accurate.\n"
                "- 3-5 short sentences maximum. No headers, no bullet points.\n"
                "[Clinical Report]:\n"
                f"{final_report}\n"
                "Patient-friendly summary:"
            )
            messages_patient = [{"role": "user", "content": [{"type": "image", "image": image}, {"type": "text", "text": patient_prompt}]}]
            text_patient = self.processor.apply_chat_template(messages_patient, tokenize=False, add_generation_prompt=True)
            inputs_patient = self.processor(text=[text_patient], images=[image], return_tensors="pt").to("cuda")
            try:
                with torch.no_grad():
                    patient_out_ids = self.llm.generate(**inputs_patient, max_new_tokens=256, do_sample=True, temperature=0.3, top_p=0.9)
                patient_gen_ids = [patient_out_ids[len(i):] for i, patient_out_ids in zip(inputs_patient.input_ids, patient_out_ids)]
            finally:
                del inputs_patient
                torch.cuda.empty_cache()
            patient_report = self.processor.batch_decode(patient_gen_ids, skip_special_tokens=True)[0]
            print(f"  [debug] Agent 4 raw output:\n{patient_report}")
            print("  -> Patient report generated.")
        else:
            print("[Agent 4] Skipped: report still needs manual review, no patient version generated.")

        # Return structured JSON for the API
        return {
            "image_path": image_path,
            "predictions": {k: v for k, v in sorted(agent1_preds.items(), key=lambda item: item[1], reverse=True) if v > 0.2},
            "trend_summary": trend_data['llm_prompt_summary'],
            "validation_verdict": validation_result['verdict'],
            "needs_review": needs_review,
            "corrected_deterministically": corrected_deterministically,
            "clinical_report": final_report,
            "patient_report": patient_report,
            "gradcam_base64": gradcam_base64
        }

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--image_path", required=True)
    args = parser.parse_args()
    
    pipeline = MedVisionPipeline()
    pipeline.run(args.image_path)
