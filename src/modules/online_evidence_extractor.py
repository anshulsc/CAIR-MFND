import uuid
from pathlib import Path
from difflib import SequenceMatcher
import requests
from PIL import Image
from io import BytesIO
import chromadb 

from src.config import EVIDENCE_DB_DIR, VECTOR_DB_DIR 
from src.logger_config import worker_logger
from src.modules.embedding_utils import get_image_embedding, get_text_embedding 


API_KEY = "BSA1cZFR9cSOtpkalB5rDvwNEbOvZz9"
BAD_DOMAINS = [
    "reddit.com", "quora.com", "facebook.com", "instagram.com", "x.com", 
    "twitter.com", "pinterest.com", "tiktok.com", "linkedin.com", "youtube.com",
    "wikipedia.org", "medium.com", "forbes.com"
]

client = chromadb.PersistentClient(path=str(VECTOR_DB_DIR))
collection = client.get_or_create_collection(name="evidence_collection")

def is_similar(a, b, threshold=0.9):
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio() > threshold

def brave_news_search(query: str, api_key: str = API_KEY, count: int = 12):
    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {"X-Subscription-Token": api_key, "Accept": "application/json"}
    params = {"q": query, "count": count}
    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        worker_logger.error(f"Brave Search API failed for query '{query}'. Reason: {e}")
        return None

def download_and_save_evidence(url: str, save_dir: Path, caption: str):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content)).convert("RGB")
        img_path = save_dir / "image.jpg"
        img.save(img_path, "JPEG")
        cap_path = save_dir / "caption.txt"
        cap_path.write_text(caption.strip(), encoding='utf-8')
        return str(img_path), str(cap_path)
    except Exception as e:
        worker_logger.warning(f"Failed to download or save evidence from {url}. Reason: {e}")
        return None, None

def run_extraction_and_indexing_pipeline(query_caption: str):
    worker_logger.info(f"Starting online evidence extraction for caption: '{query_caption[:50]}...'")
    
    search_results = brave_news_search(query_caption)
    if not search_results or "web" not in search_results:
        return {"new_evidence_count": 0, "message": "Failed to get results from search API."}


    filtered_results = []
    for r in search_results["web"].get("results", []):
        title = r.get("title", "").strip()
        url = r.get("url", "")
        img_url = r.get("thumbnail", {}).get("src", "")
        if not all([title, url, img_url]): continue
        if any(domain in url for domain in BAD_DOMAINS): continue
        if is_similar(query_caption, title): continue
        filtered_results.append({"title": title, "img_url": img_url})

    if not filtered_results:
        return {"new_evidence_count": 0, "message": "No suitable new evidence found after filtering."}
    

    saved_evidence_details = []
    
    newly_indexed_items = 0
    for item in filtered_results:
        evidence_id = f"evidence_{uuid.uuid4().hex[:12]}"
        save_dir = EVIDENCE_DB_DIR / evidence_id
        save_dir.mkdir(exist_ok=True)
        
        img_path, cap_path = download_and_save_evidence(item['img_url'], save_dir, item['title'])
        
        if img_path and cap_path:
            worker_logger.info(f"Indexing new evidence: {evidence_id}")
            
            saved_evidence_details.append({
                "image_path": img_path,
                "caption": item['title']
            })

            img_embedding = get_image_embedding(img_path)
            text_embedding = get_text_embedding(item['title'])
            if img_embedding is not None:
                collection.add(embeddings=[img_embedding], documents=[item['title']], metadatas=[{"type": "image", "path": img_path}], ids=[f"{evidence_id}_img"])
            if text_embedding is not None:
                collection.add(embeddings=[text_embedding], documents=[item['title']], metadatas=[{"type": "text", "path": cap_path}], ids=[f"{evidence_id}_txt"])
            newly_indexed_items += 1
            
    worker_logger.info(f"Extraction complete. Saved and indexed {newly_indexed_items} new items.")
    return {
        "new_evidence_count": newly_indexed_items,
        "message": f"Successfully extracted and indexed {newly_indexed_items} new evidence items.",
        "saved_evidence": saved_evidence_details 
    }