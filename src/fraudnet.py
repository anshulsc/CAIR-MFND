import torch
from src import fraudnet_backbone as backbone_function_main

from src.fraudnet_utils import get_clip_features

import json
from pydantic import BaseModel, field_validator, model_validator, ConfigDict
from typing import Any

def load_model(model_path, pdrop=0.0157, device='cuda:0'):
    model = backbone_function_main.Classifier(pdrop)
    checkpoint = torch.load(model_path, map_location=device)
    model.load_state_dict(checkpoint['state_dict'], strict=False)
    model.to(device)
    model.eval()
    return model

def extract_clip_features(img_path, caption,evidence_images,evi_text):
    if isinstance(evi_text, list) and all(isinstance(t, tuple) and len(t) == 2 for t in evi_text):
        evi_text = " ".join([title for title, _ in evi_text])
    q_img, q_cap, X_all = get_clip_features(img_path, caption.strip(), evidence_images, evi_text.strip())
    q_img = q_img.squeeze(0)
    q_cap = q_cap.squeeze(0)
    return q_img, q_cap,X_all

def load_domain_vector(domain_vector_path, device='cuda:0', selected_domain='global'):
    with open(domain_vector_path, 'r') as f:
        domain_vector = json.load(f)
    vec = torch.tensor(domain_vector[selected_domain], dtype=torch.float32).to(device)
    return vec

class fraudnet_input(BaseModel):
    img_feat: torch.Tensor
    text_feat: torch.Tensor
    domain_vec: torch.Tensor
    fake_evidence: torch.Tensor

    model_config = ConfigDict(arbitrary_types_allowed=True)
    @model_validator(mode="before")
    @classmethod
    def validate_all(cls, values):
        expected_shape = (1, 768)
        device = values['img_feat'].device

        for name in ['img_feat', 'text_feat', 'domain_vec']:
            tensor = values[name]
            if not isinstance(tensor, torch.Tensor):
                raise TypeError(f"{name} must be a torch.Tensor")
            if tensor.shape != expected_shape:
                raise ValueError(f"{name} must have shape {expected_shape}, got {tensor.shape}")
            if tensor.device != device:
                raise ValueError(f"{name} must be on device {device}, but got {tensor.device}")

        # Validate fake_evidence shape and device
        fe = values['fake_evidence']
        if not isinstance(fe, torch.Tensor):
            raise TypeError("fake_evidence must be a torch.Tensor")
        if fe.shape != (1, 20, 768):
            raise ValueError(f"fake_evidence must have shape (1, 20, 768), got {fe.shape}")
        if fe.device != device:
            raise ValueError(f"fake_evidence must be on device {device}, but got {fe.device}")

        return values

def run_fraudnet_inference(model, inputs):

    # Now safely extract the validated and formatted values
    img_feat = inputs.img_feat
    text_feat = inputs.text_feat
    domain_vec = inputs.domain_vec
    fake_evidence = inputs.fake_evidence
    device = img_feat.device

    with torch.no_grad():
        output = model(img_feat, text_feat, fake_evidence, domain_vec)
        prob = torch.sigmoid(output).item()
        pred = int(prob >= 0.5)

    return {
        "fraudnet_label": pred,
        "confidence": prob
    }

