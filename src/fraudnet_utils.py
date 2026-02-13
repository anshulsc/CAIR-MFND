from lavis.models import load_model_and_preprocess
clip_device = "cuda"
import torch
import json, os
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import random
import numpy as np
from torch.nn.functional import cosine_similarity

lavis_clip_model, vis_processors, txt_processors = load_model_and_preprocess(name="clip_feature_extractor", 
                                                                        model_type="ViT-L-14", 
                                                                        is_eval=True, 
                                                                        device=clip_device)   
lavis_clip_model.to(clip_device)
lavis_clip_model.eval()
import torchvision.transforms as transforms
transform = transforms.Compose([transforms.PILToTensor()])


def get_clip_feature_queries(img_path, caption):
    with torch.no_grad():
        image = Image.open(img_path)
        image = image.convert('RGB')
        max_size = 400
        width, height = image.size
        if width > height:
            new_width = max_size
            new_height = int(height * (max_size / width))
        else:
            new_height = max_size
            new_width = int(width * (max_size / height))
        image = image.resize((new_width, new_height))
        img = vis_processors["eval"](image).unsqueeze(0)        
        txt = txt_processors["eval"](caption)
        
        sample = {
                        "image": img.to(clip_device),
                        "text_input": txt
        }

        clip_features = lavis_clip_model.extract_features(sample)                

        image_features = clip_features.image_embeds_proj
        text_features = clip_features.text_embeds_proj 
        text_features = text_features.reshape(-1)
        text_features = text_features.detach()
        image_features = image_features.reshape(-1).detach()#.numpy()
    return image_features, text_features


def get_clip_features(q_img_path, q_caption, evidence_image=None, evidence_caption=None):
    use_evidence = 10
    device = 'cuda'

    q_img, q_caption = get_clip_feature_queries(q_img_path, q_caption)
    X_img = []
    if isinstance(evidence_image, str) and evidence_image.strip() and os.path.isfile(evidence_image):
        img_feature = get_clip_img_feature(evidence_image)
        if img_feature is not None:
            X_img.append(img_feature)

    if len(X_img) > 0:
        X_img = torch.stack(X_img).to(device)
        cos_sim_img = cosine_similarity(q_img.cpu().reshape(1, -1), X_img.cpu())
        image_evidences_ranks = torch.argsort(-cos_sim_img).tolist()
        X_img = X_img[image_evidences_ranks]
    else:
        X_img = torch.zeros((0, 768), device=device)
    X_txt = []
    if isinstance(evidence_caption, str) and evidence_caption.strip():
        txt_feature = get_clip_text_feature(evidence_caption)
        if txt_feature is not None:
            X_txt.append(txt_feature)

    if len(X_txt) > 0:
        X_txt = torch.stack(X_txt).to(device)
        cos_sim_txt = cosine_similarity(q_caption.cpu().reshape(1, -1), X_txt.cpu())
        text_evidences_ranks = torch.argsort(-cos_sim_txt).tolist()
        X_txt = X_txt[text_evidences_ranks]
    else:
        X_txt = torch.zeros((0, 768), device=device)

    # Pad or truncate
    if X_img.shape[0] < use_evidence:
        pad_zeros = torch.zeros((use_evidence - X_img.shape[0], 768), device=device)
        X_img = torch.vstack([X_img, pad_zeros])
    else:
        X_img = X_img[:use_evidence]

    if X_txt.shape[0] < use_evidence:
        pad_zeros = torch.zeros((use_evidence - X_txt.shape[0], 768), device=device)
        X_txt = torch.vstack([X_txt, pad_zeros])
    else:
        X_txt = X_txt[:use_evidence]

    # Combine features
    X_all = torch.cat([X_img, X_txt], dim=0)  # (20, 768)
    X_all = X_all.to(torch.float32)    # (1, 20, 768)

    images = q_img.unsqueeze(0).to(device, non_blocking=True)   # (1, 768)
    texts = q_caption.unsqueeze(0).to(device, non_blocking=True)  # (1, 768)

    return images, texts, X_all




def get_clip_img_feature(img_path):
    """ Use this version when path of image is available
    """
    with torch.no_grad():
        image = Image.open(img_path)
        image = image.convert('RGB')
        max_size = 400
        width, height = image.size
        if width > height:
            new_width = max_size
            new_height = int(height * (max_size / width))
        else:
            new_height = max_size
            new_width = int(width * (max_size / height))
        image = image.resize((new_width, new_height))
        img = vis_processors["eval"](image).unsqueeze(0)        
        sample = {
                        "image": img.to(clip_device)
        }
        image_features = lavis_clip_model.extract_features(sample)                
        image_features = image_features.reshape(-1).detach()#.numpy()
    return image_features

def get_clip_text_feature(caption):
    """caption is a single string
    """
    with torch.no_grad():
        txt = txt_processors["eval"](caption)
        sample = {
                        "text_input": txt
        }
        clip_features = lavis_clip_model.extract_features(sample)
        text_features = clip_features
        text_features = text_features.reshape(-1)
        text_features = text_features.detach()#.numpy()
    return text_features

def get_clip_img_feature_imgobject(image):
    """ Use this version when PIL Image object is available. Don't convert it into RGB.
    """
    with torch.no_grad():
        # image = Image.open(img_path)
        image = image.convert('RGB')
        max_size = 400
        width, height = image.size
        if width > height:
            new_width = max_size
            new_height = int(height * (max_size / width))
        else:
            new_height = max_size
            new_width = int(width * (max_size / height))
        image = image.resize((new_width, new_height))
        img = vis_processors["eval"](image).unsqueeze(0)        
        sample = {
                        "image": img.to(clip_device)
        }
        image_features = lavis_clip_model.extract_features(sample)                
        image_features = image_features.reshape(-1).detach()#.numpy()
    return image_features

