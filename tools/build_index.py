# tools/build_index.py
import os
import chromadb
from tqdm import tqdm
import sys
from src.config import EVIDENCE_DB_DIR, VECTOR_DB_DIR
from src.modules.embedding_utils import get_image_embedding, get_text_embedding

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# --- ChromaDB Client Setup ---
# This sets up a persistent client that saves data to disk.
client = chromadb.PersistentClient(path=str(VECTOR_DB_DIR))

# --- Collection Setup ---
# We use a collection to store our embeddings.
# The 'get_or_create' is convenient: it creates the collection if it doesn't exist.
collection_name = "evidence_collection"
collection = client.get_or_create_collection(name=collection_name)

def index_database():
    """
    Scans the evidence database, computes embeddings, and stores them in ChromaDB.
    This function is idempotent: running it again will only add new items.
    """
    print("--- Starting Evidence Database Indexing ---")
    
    # Get a list of all item IDs already in the database to avoid re-processing.
    existing_ids = set(collection.get(include=[])['ids'])
    print(f"Found {len(existing_ids)} items already indexed.")

    items_to_add = []
    
    # Walk through the evidence directory
    for root, _, files in os.walk(EVIDENCE_DB_DIR):
        # We assume one image and one caption file per directory
        img_file = next((f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))), None)
        cap_file = next((f for f in files if f.lower().endswith('.txt')), None)

        if img_file and cap_file:
            item_id = os.path.basename(root)
            
            # Skip if we've already processed this item
            if item_id in existing_ids:
                continue

            img_path = os.path.join(root, img_file)
            cap_path = os.path.join(root, cap_file)
            
            with open(cap_path, 'r', encoding='utf-8') as f:
                caption = f.read().strip()
            
            items_to_add.append({
                "id": item_id,
                "img_path": img_path,
                "cap_path": cap_path,
                "caption": caption
            })

    if not items_to_add:
        print("Database is already up-to-date. No new items to index.")
        return

    print(f"Found {len(items_to_add)} new items to index...")
    
    # Process items in batches for efficiency
    batch_size = 32
    for i in tqdm(range(0, len(items_to_add), batch_size), desc="Indexing Batches"):
        batch = items_to_add[i:i + batch_size]
        
        # Prepare data for ChromaDB
        ids = [item['id'] for item in batch]
        img_embeddings = [get_image_embedding(item['img_path']) for item in batch]
        text_embeddings = [get_text_embedding(item['caption']) for item in batch]
        
        # We'll store both image and text embeddings for multimodal search
        # Note: ChromaDB doesn't directly support multiple vectors per item,
        # so we create separate entries for image and text with a common ID.
        # A more advanced setup could concatenate them or use different collections.
        # For simplicity, we will index them separately with a suffix.
        
        image_ids = [f"{id}_img" for id in ids]
        text_ids = [f"{id}_txt" for id in ids]

        # Filter out any failed embeddings
        valid_img_indices = [idx for idx, emb in enumerate(img_embeddings) if emb is not None]
        valid_text_indices = [idx for idx, emb in enumerate(text_embeddings) if emb is not None]

        # Add to collection if there's anything valid to add
        if valid_img_indices:
            collection.add(
                embeddings=[img_embeddings[i] for i in valid_img_indices],
                documents=[batch[i]['caption'] for i in valid_img_indices], # Store caption as document for context
                metadatas=[{"type": "image", "path": batch[i]['img_path']} for i in valid_img_indices],
                ids=[image_ids[i] for i in valid_img_indices]
            )
        
        if valid_text_indices:
             collection.add(
                embeddings=[text_embeddings[i] for i in valid_text_indices],
                documents=[batch[i]['caption'] for i in valid_text_indices],
                metadatas=[{"type": "text", "path": batch[i]['cap_path']} for i in valid_text_indices],
                ids=[text_ids[i] for i in valid_text_indices]
            )

    print(f"--- Indexing Complete. Total items in collection: {collection.count()} ---")


if __name__ == "__main__":
    index_database()