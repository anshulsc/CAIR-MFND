# src/modules/inference_pipeline.py
import json
import torch
from pathlib import Path


from src.config import VLLM_MODEL_PATH, FRAUDNET_MODEL_PATH, DOMAIN_VECTOR_PATH
from src.agents.agent_class import MultimodalClaimVerifier
from src.fraudnet import load_model, extract_clip_features, load_domain_vector, fraudnet_input
from src.workflow import build_langgraph

_verifier = None
_fraudnet_model = None
_domain_vec = None


FRAUDNET_DEVICE = 'cpu'  
VLLM_DEVICE = 'cuda:0' if torch.cuda.is_available() else 'cpu'

def _initialize_models():
    global _verifier, _fraudnet_model, _domain_vec
    
    if _verifier is None:
        print("INFO: Initializing MultimodalClaimVerifier (vLLM)...")
        _verifier = MultimodalClaimVerifier(VLLM_MODEL_PATH)
        print("INFO: Verifier initialized.")

    if _fraudnet_model is None:
        print(f"INFO: Initializing FraudNet model on {FRAUDNET_DEVICE}...")
        _fraudnet_model = load_model(FRAUDNET_MODEL_PATH, device=FRAUDNET_DEVICE)
        _domain_vec = load_domain_vector(DOMAIN_VECTOR_PATH, device=FRAUDNET_DEVICE)
        print(f"INFO: FraudNet model initialized on {FRAUDNET_DEVICE}.")

def run_full_inference(metadata_path: Path):
    _initialize_models()


    with open(metadata_path, 'r') as f:
        metadata = json.load(f)

    base_dir = metadata_path.parent
    query_image_path = base_dir / metadata['query_image_path']
    
    from src.config import BASE_DIR
    if metadata['evidences']:
        evidence_rel_path = metadata['evidences'][0]['image_path']
        evidence_image_path = BASE_DIR / evidence_rel_path
    else:
        evidence_image_path = query_image_path
    
    query_caption_path = base_dir / metadata['query_caption_path']
    with open(query_caption_path, 'r') as f:
        query_caption = f.read().strip()

    search_results = "\n".join([
        (BASE_DIR / e['caption_path']).read_text(encoding='utf-8').strip() 
        for e in metadata['evidences']
    ])

    claims = "\n".join([query_caption for _ in metadata['evidences']])
    
    txt_txt_inputs = [
        (sr, cl) for sr, cl in zip(search_results.split("\n"), claims.split("\n")) if sr and cl
    ]

    img_feat, text_feat, X_all = extract_clip_features(query_image_path, query_caption, evidence_image_path, search_results)
    img_feat = img_feat.to(FRAUDNET_DEVICE)
    text_feat = text_feat.to(FRAUDNET_DEVICE)
    X_all = X_all.to(FRAUDNET_DEVICE)
    
    fraudnet_inputs = fraudnet_input(
        img_feat=img_feat.unsqueeze(0),
        text_feat=text_feat.unsqueeze(0),
        domain_vec=_domain_vec.unsqueeze(0),
        fake_evidence=X_all.unsqueeze(0)
    )

    state = {
        'query_image_path': query_image_path,
        'evidence_image_path': evidence_image_path,
        'query_caption': query_caption,
        'txt_txt_inputs': txt_txt_inputs,
        'verifier': _verifier,
        'fraudnet_model': _fraudnet_model,
        'fraudnet_input': fraudnet_inputs
    }
    
    graph = build_langgraph()
    final_state = graph.invoke(state)

    final_output = {
        key: final_state[key] for key in ["stage2_outputs", "fraudnet_response"] if key in final_state
    }

    result_path = metadata_path.parent / "inference_results.json"
    with open(result_path, 'w') as f:
        json.dump(final_output, f, indent=4)
        
    print(f"INFO: Inference complete. Results saved to {result_path}")
    return result_path