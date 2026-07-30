"""
Agent 2 - Inference Script.
Loads the base Qwen2-VL model, attaches the trained LoRA adapters, 
and generates a radiology report from an X-ray image.
"""
import torch
from PIL import Image
from transformers import Qwen2VLForConditionalGeneration, Qwen2VLProcessor, BitsAndBytesConfig
from peft import PeftModel
import argparse
import os

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image_path", required=True, help="Path to input X-ray image")
    parser.add_argument("--checkpoint", default="/workspace/agent_2/checkpoints/checkpoint-500", help="Path to LoRA checkpoint")
    parser.add_argument("--report_type", choices=["clinical", "patient"], default="clinical", help="Type of report to generate")
    args = parser.parse_args()

    MODEL_ID = "Qwen/Qwen2-VL-7B-Instruct"

    print("Loading Base Model (4-bit)...")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )

    model = Qwen2VLForConditionalGeneration.from_pretrained(
        MODEL_ID,
        quantization_config=bnb_config,
        device_map="auto"
    )

    print(f"Attaching LoRA adapters from {args.checkpoint}...")
    model = PeftModel.from_pretrained(model, args.checkpoint)
    model.eval()

    processor = Qwen2VLProcessor.from_pretrained(MODEL_ID)

    print(f"Processing image: {args.image_path}")
    image = Image.open(args.image_path).convert("RGB").resize((512, 512))

    # --- The Multi-Agent Prompt ---
    # For now, we just test the vision-to-text. 
    # In the full pipeline, Agent 1 and 1.5 data will be injected here.
    if args.report_type == "clinical":
        prompt_text = "You are an expert radiologist. Analyze this chest X-ray image and generate a detailed radiology report.\nPlease provide:\n1. FINDINGS: Describe visible structures and abnormalities\n2. IMPRESSION: Summarize key findings"
    else:
        prompt_text = "You are a compassionate patient care navigator. Look at this chest X-ray and write a report for the patient in plain, non-scary English (8th-grade reading level).\nPlease provide:\n1. WHAT WE SAW: Explain what the X-ray shows.\n2. NEXT STEPS: Provide a gentle recommendation."

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": prompt_text}
            ]
        }
    ]

    # Prepare inputs
    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = processor(text=[text], images=[image], padding=True, return_tensors="pt").to("cuda")

    print("\nGenerating report (this may take a few seconds)...")
    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=512,
            do_sample=True,
            temperature=0.3,
            top_p=0.9
        )

    # Decode only the newly generated tokens
    generated_ids = [output_ids[len(input_ids):] for input_ids, output_ids in zip(inputs.input_ids, output_ids)]
    output_text = processor.batch_decode(generated_ids, skip_special_tokens=True, clean_up_tokenization_spaces=True)[0]

    print("\n" + "="*50)
    print("GENERATED REPORT:")
    print("="*50)
    print(output_text)

if __name__ == "__main__":
    main()
