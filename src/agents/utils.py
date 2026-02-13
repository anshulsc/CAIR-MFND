import os
from typing import List, Dict, Any, Union
from PIL import Image
from transformers import AutoProcessor
from vllm import LLM, SamplingParams
from dataclasses import asdict
import json

# from prompts import get_qimg_qtxt_sentiment_prompt, get_qimg_qtxt_entities_prompt, get_qimg_qtxt_event_prompt, get_qimg_qtxt_colab_prompt

# def load_model_and_processor(model_name: str, num_prompts: int, max_images_per_prompt: int) -> tuple[LLM, AutoProcessor]:
#     """
#     Loads the vLLM model and HuggingFace processor.

#     Args:
#         model_name: Name or path to the model.
#         num_prompts: Number of prompts to process in a batch.
#         max_images_per_prompt: Max number of images expected per prompt.

#     Returns:
#         A tuple of (LLM instance, processor instance)
#     """
#     processor = AutoProcessor.from_pretrained(model_name, local_files_only=True )
#     llm = LLM(
#         model=model_name,
#         max_model_len=4096,
#         max_num_seqs=num_prompts,
#         limit_mm_per_prompt={"image": max_images_per_prompt},
#         dtype="bfloat16",
#         device="auto",
#     )
#     return llm, processor

def load_model_and_processor(model_path: str, num_prompts: int, max_images_per_prompt: int) -> tuple[LLM, AutoProcessor]:
    """
    Loads the vLLM model and HuggingFace processor.

    Args:
        model_path: Local path to the model folder that contains config files.
        num_prompts: Number of prompts to process in a batch.
        max_images_per_prompt: Max number of images expected per prompt.

    Returns:
        A tuple of (LLM instance, processor instance)
    """
    processor = AutoProcessor.from_pretrained(
        model_path,
        cache_dir="/data/shwetabh_agentic_FND/agentic_framework_4/agents/google/gemma-3-12b-it",
        local_files_only=True   #  Ensures no call to Hugging Face Hub
    )

    llm = LLM(
        model=model_path,                 #  Same local path
        # quantization="compressed-tesnor",
        download_dir="/data/shwetabh_agentic_FND/agentic_framework_4/agents/google/gemma-3-12b-it",          #  Also pointing to local
        max_model_len=4096,
        max_num_seqs=num_prompts,
        limit_mm_per_prompt={"image": max_images_per_prompt},
        dtype="bfloat16",
    )
    return llm, processor



def prepare_batch_inputs_from_messages(
    messages_list: List[List[Dict[str, Any]]],
    image_paths: List[Union[str, List[str]]],
    processor: AutoProcessor
) -> List[Dict[str, Any]]:
    """
    Prepares batched inputs using user-provided messages and corresponding image path(s).

    Args:
        messages_list: List of message dicts per input (formatted for chat template).
        image_paths: List of str or list of str (paths to images).
        processor: Hugging Face AutoProcessor.

    Returns:
        A list of dicts ready for vLLM.generate().
    """
    assert len(messages_list) == len(image_paths), "messages and images must be the same length"

    batch_inputs = []
    for messages, image_input in zip(messages_list, image_paths):
        if image_input is not None:
            # Normalize to list of image paths
            from pathlib import Path
            image_path_list = [image_input] if isinstance(image_input, (str, Path)) else image_input
            images = [Image.open(path).convert("RGB") for path in image_path_list]

            # Clean image placeholders
            for msg in messages:
                for item in msg["content"]:
                    if isinstance(item, dict) and item.get("type") == "image":
                        item.pop("image", None)  # Let processor insert image tokens

            # Apply template
            prompt_text = processor.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )

            batch_inputs.append({
                "prompt": prompt_text,
                "multi_modal_data": {"image": images},
            })
            
        else:
            # If no images, just use the text messages
            prompt_text = processor.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
            batch_inputs.append({
                "prompt": prompt_text
                # "multi_modal_data": {"image": []},  # No images provided
            })
    return batch_inputs

def run_inference(
    llm: LLM,
    batch_inputs: List[Dict[str, Any]],
    max_tokens: int = 1024
):
    """
    Runs inference with vLLM on the provided batch inputs,
    using generation settings aligned with HuggingFace Gemma 3 12B.

    Args:
        llm: Loaded vLLM model.
        batch_inputs: Prepared list of prompts and images.
        max_tokens: Max tokens to generate per prompt.

    Returns:
        List of generated texts.
    """
    all_generated_texts = []

    # Parameters aligned with Hugging Face Gemma 3 12B defaults
    sampling_params = SamplingParams(
        temperature=0.0,             # Default for Gemma
        top_k=64,                    # Default for Gemma
        top_p=0.95,                  # Default for Gemma
        seed=42,
        max_tokens=max_tokens,       # Controlled externally
        stop_token_ids=[1, 106],     # eos_token_id from Gemma
        skip_special_tokens=True,
        presence_penalty=0.0,
        frequency_penalty=0.0,
        repetition_penalty=1.0
    )

    # Generate outputs
    outputs = llm.generate(batch_inputs, sampling_params=sampling_params)

    # Process and print results
    for i, output in enumerate(outputs):
        generated_text = output.outputs[0].text
        all_generated_texts.append(generated_text)
        print(f"Prompt {i + 1} Response:\n{generated_text}\n{'-' * 50}")
    return all_generated_texts

import re
import re

def extract_prediction_info(text):
    # Extract FAKE or TRUE (first instance)
    label_match = re.search(r'\b(FAKE|TRUE)\b', text, re.IGNORECASE)
    label = label_match.group(1).upper() if label_match else None

    # Extract confidence (supports float/int with or without %, **, etc.)
    conf_match = re.search(
        r'(?:\*\*)?\s*Confidence\s*(Score)?\s*[:\-]?\s*(?:\*\*)?\s*([0-9]*\.?[0-9]+)', 
        text, re.IGNORECASE
    )
    confidence = float(conf_match.group(2)) if conf_match else None

    # Extract reasoning (supports **Reasoning:** and variants)
    reasoning_match = re.search(
        r'(?:\*\*)?\s*Reasoning\s*[:\-]?\s*(?:\*\*)?\s*\n?(.*)', 
        text, re.IGNORECASE | re.DOTALL
    )
    reasoning = reasoning_match.group(1).strip() if reasoning_match else None

    return {
        "label": label,
        "confidence": confidence,
        "reasoning": reasoning
    }

def extract_support_and_confidence(text):
    """
    Extracts 'support_or_negate_or_baseless' and 'confidence' from a JSON-like string.
    """
    support_match = re.search(r'"support_or_negate_or_baseless"\s*:\s*"(\w+)"', text)
    confidence_match = re.search(r'"confidence"\s*:\s*"(\w+)"', text)

    support = support_match.group(1).lower() if support_match else None
    confidence = confidence_match.group(1).lower() if confidence_match else None

    return support, confidence

def extract_alignment_info(raw_output: str):
    """
    Extracts alignment score and flags from LLM output containing a JSON object.
    Returns a dictionary with keys: score, factcheck_flag, trusted_flag.
    """
    try:
        cleaned = re.sub(r"```json|```", "", raw_output.strip())
        json_match = re.search(r"{.*}", cleaned, re.DOTALL)
        if not json_match:
            raise ValueError("No JSON object found in output.")
        
        json_str = json_match.group(0)
        data = json.loads(json_str)

        score = float(data.get("FactualAlignmentScore", 0.0))
        factcheck_flag = bool(data.get("FactCheckVerdictUsed", False))
        trusted_flag = bool(data.get("TrustedNewsSourceVerified", False))

        return {
            "score": score,
            "factcheck_flag": factcheck_flag,
            "trusted_flag": trusted_flag
        }
    except Exception as e:
        raise ValueError(f"Failed to extract alignment info: {e}")
    
def extract_rationales(txt_txt_results):
    rationales = []
    for entry in txt_txt_results:
        try:
            # Clean backticks and whitespace
            entry_clean = re.sub(r"```json|```", "", entry).strip()
            parsed = json.loads(entry_clean)
            if "rationale" in parsed:
                rationales.append(parsed["rationale"])
        except Exception as e:
            print(f"⚠️ Failed to parse entry: {entry}\nError: {e}")
    return rationales


def compute_weighted_support_score(text_list, custom_weights=None):
    """
    Computes weighted total score based on factual alignment outputs and classifies the claim.

    Output:
        {
            "score": float,
            "verdict": "FAKE" | "TRUE" | "LIKELY FAKE" | "LIKELY TRUE" | "UNCERTAIN/REVIEW"
        }
    """
    if custom_weights is None:
        custom_weights = {
            "factcheck": 5.0,
            "trusted": 2.0,
            "default": 1.0
        }
    weighted_sum = 0.0
    total_weight = 0.0
    has_trusted_positive = False
    for text in text_list:
        info = extract_alignment_info(text)
        score = info["score"]
        if info.get("factcheck_flag") and score == -1.0:
            return {"score": -20.0, "verdict": "FAKE"}
        if info.get("trusted_flag") and score == 1.0:
            has_trusted_positive = True
        if info["factcheck_flag"]:
            weight = custom_weights["factcheck"]
        elif info["trusted_flag"]:
            weight = custom_weights["trusted"]
        else:
            weight = custom_weights["default"]
        weighted_sum += score * weight
        total_weight += weight
    if has_trusted_positive:
        return {"score": 20.0, "verdict": "TRUE"}

    # Fallback scoring
    final_score = weighted_sum / total_weight if total_weight > 0 else 0.0

    # 🧠 Classification logic based on final score
    if final_score >= 0.75:
        verdict = "LIKELY TRUE"
    elif final_score <= 0.3:
        verdict = "LIKELY FAKE"
    else:
        verdict = "UNCERTAIN/REVIEW"

    return {"score": final_score, "verdict": verdict}

# text1 = """Prompt 1 Response:
# FAKE

# Confidence Score: 0.99

# **Reasoning:**

# All three analyses (sentiment, entities, and event/action) point to a significant mismatch...
# """

# text2 = """Prompt 2 Response:
# **TRUE**

# **Confidence Score: 0.95**

# **Reasoning:**

# All three analyses (Sentiment, Entities, and Event/Action) consistently indicate alignment...
# """

# print(extract_prediction_info(text1))
# print(extract_prediction_info(text2))

if __name__ == "__main__":
    # Example usage of compute_weighted_support_score
    # # This is just a placeholder; replace with actual text inputs as needed.
    # example_texts = [
    #     '```json\n{"support_or_negate_or_baseless": "support", "confidence": "high", "rationale": "Strong evidence"}\n```',
    #     '```json\n{"support_or_negate_or_baseless": "negate", "confidence": "medium", "rationale": "Unrelated evidence"}\n```',
    #     '```json\n{"support_or_negate_or_baseless": "support", "confidence": "low", "rationale": "Vague statement"}\n```',
    #     '```json\n{"support_or_negate_or_baseless": "negate", "confidence": "high", "rationale": "Contradiction"}\n```'
    # ]

    # result = compute_weighted_support_score(example_texts)
    # print(result)

    llm, processor = load_model_and_processor(model_path="google/gemma-3-12b-it",num_prompts=18,max_images_per_prompt=2)