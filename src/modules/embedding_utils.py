import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel


DEVICE = "cpu"  
MODEL_NAME = "openai/clip-vit-base-patch32"

_model = None
_processor = None

def _get_clip_model():
    global _model, _processor
    if _model is None:
        print("INFO: Loading CLIP model for the first time...")
        _model = CLIPModel.from_pretrained(MODEL_NAME).to(DEVICE)
        _processor = CLIPProcessor.from_pretrained(MODEL_NAME)
        print("INFO: CLIP model loaded successfully.")
    return _model, _processor


def get_image_embedding(image_path: str) -> list[float]:
    model, processor = _get_clip_model()
    try:
        image = Image.open(image_path).convert("RGB")
        with torch.no_grad():
            inputs = processor(images=image, return_tensors="pt", padding=True).to(DEVICE)
            image_features = model.get_image_features(**inputs)
            image_features = image_features / image_features.norm(p=2, dim=-1, keepdim=True) 
        
        return image_features.cpu().numpy().flatten().tolist()
    except Exception as e:
        print(f"ERROR: Could not process image {image_path}. Reason: {e}")
        return None

def get_text_embedding(text: str) -> list[float]:
    model, processor = _get_clip_model()
    try:
        with torch.no_grad():
            inputs = processor(text=text, return_tensors="pt", padding=True).to(DEVICE)
            text_features = model.get_text_features(**inputs)
            text_features = text_features / text_features.norm(p=2, dim=-1, keepdim=True)

        return text_features.cpu().numpy().flatten().tolist()
    except Exception as e:
        print(f"ERROR: Could not process text. Reason: {e}")
        return None