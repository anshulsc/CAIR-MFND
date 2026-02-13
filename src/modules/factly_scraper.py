import requests
import uuid
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import chromadb

from src.config import EVIDENCE_DB_DIR, VECTOR_DB_DIR
from src.logger_config import worker_logger
from src.modules.embedding_utils import get_image_embedding, get_text_embedding


client = chromadb.PersistentClient(path=str(VECTOR_DB_DIR))
collection = client.get_or_create_collection(name="evidence_collection")

def get_latest_article_links(count=10):
    main_page_url = 'https://factly.in/category/english/fake-news/'
    worker_logger.info(f"Fetching article links from: {main_page_url}")
    try:
        response = requests.get(main_page_url, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        link_elements = soup.select('h2.post-title a')
        article_urls = [link['href'] for link in link_elements[:count]]
        worker_logger.info(f"Found {len(article_urls)} article links.")
        return article_urls
    except requests.exceptions.RequestException as e:
        worker_logger.error(f"Error fetching the main Factly page: {e}")
        return []

def scrape_and_save_article(url: str):
    worker_logger.info(f"  -> Scraping new article: {url}")
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        caption_elem = soup.select_one('h1.post-title.item.fn')
        caption = caption_elem.text.strip() if caption_elem else "Untitled"

        date_elem = soup.select_one('span.dtreviewed')
        timestamp = date_elem.text.strip() if date_elem else "N/A"

        evidence_id = f"factly_{uuid.uuid4().hex[:10]}"
        save_dir = EVIDENCE_DB_DIR / evidence_id
        save_dir.mkdir(exist_ok=True)
        
        img_elem = soup.select_one('div.post-content.description img')
        img_path = None
        if img_elem and 'src' in img_elem.attrs:
            img_url = urljoin(url, img_elem['src'])
            try:
                img_data = requests.get(img_url, timeout=15).content
                img_path = save_dir / "image.jpg"
                with open(img_path, 'wb') as handler:
                    handler.write(img_data)
            except requests.exceptions.RequestException as e:
                worker_logger.warning(f"Could not download image {img_url}: {e}")
        
        if not img_path:
            return None

        cap_path = save_dir / "caption.txt"
        cap_path.write_text(caption, encoding='utf-8')
        
        return {
            "evidence_id": evidence_id,
            "caption": caption,
            "image_path": str(img_path),
            "caption_path": str(cap_path),
            "source_url": url,
            "timestamp": timestamp 
        }
    except requests.exceptions.RequestException as e:
        worker_logger.error(f"Failed to scrape {url}: {e}")
        return None


def run_factly_pipeline(count=10):
    worker_logger.info("--- Starting Factly Scraper & Indexer Pipeline ---")
    
    latest_links = get_latest_article_links(count=count)
    if not latest_links:
        return {"processed_items": [], "newly_scraped_count": 0, "message": "Could not retrieve any article links from Factly."}

    existing_items_db = collection.get(where={"source": "factly.in"}, include=["metadatas"])
    url_to_data_map = {}
    if existing_items_db and existing_items_db['ids']:
        for i, meta in enumerate(existing_items_db['metadatas']):
            if 'source_url' in meta:
                article_dir = Path(meta['path']).parent
                url_to_data_map[meta['source_url']] = {
                    "caption": (article_dir / "caption.txt").read_text(encoding='utf-8').strip(),
                    "image_path": str(article_dir / "image.jpg"),
                    "source_url": meta['source_url'],
                    "timestamp": meta.get('timestamp', 'Previously Scraped') # Get timestamp if it exists
                }

    processed_items = []
    newly_scraped_count = 0
    for link in latest_links:
        if link in url_to_data_map:
            worker_logger.info(f"  -> Retrieving existing article: {link}")
            processed_items.append(url_to_data_map[link])
        else:
            article_data = scrape_and_save_article(link)
            if article_data:
                newly_scraped_count += 1
                worker_logger.info(f"Indexing new Factly evidence: {article_data['evidence_id']}")
                img_embedding = get_image_embedding(article_data['image_path'])
                text_embedding = get_text_embedding(article_data['caption'])
                metadata = {"source": "factly.in", "source_url": article_data['source_url'], "timestamp": article_data['timestamp']}
                if img_embedding:
                    collection.add(embeddings=[img_embedding], documents=[article_data['caption']], metadatas=[{"type": "image", "path": article_data['image_path'], **metadata}], ids=[f"{article_data['evidence_id']}_img"])
                if text_embedding:
                    collection.add(embeddings=[text_embedding], documents=[article_data['caption']], metadatas=[{"type": "text", "path": article_data['caption_path'], **metadata}], ids=[f"{article_data['evidence_id']}_txt"])
                processed_items.append(article_data)

    message = f"Processed {len(processed_items)} latest articles. Scraped and indexed {newly_scraped_count} new items."
    if newly_scraped_count == 0 and processed_items:
        message = "Already up-to-date. Displaying the 10 most recent articles from the database."

    return {
        "processed_items": processed_items,
        "newly_scraped_count": newly_scraped_count,
        "message": message
    }