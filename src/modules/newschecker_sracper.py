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
    """Fetch latest fact-check article links from NewChecker"""
    main_page_url = 'https://newschecker.in/fact-check/1'
    worker_logger.info(f"Fetching article links from: {main_page_url}")
    try:
        response = requests.get(main_page_url, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # NewChecker uses article cards with links in specific structure
        # Looking for article links in the main content area
        article_links = []
        
        # Find all article containers
        articles = soup.select('a[href*="/fact-check/"]')
        seen_urls = set()
        
        for link in articles:
            href = link.get('href')
            if href and href not in seen_urls:
                # Make sure it's a full URL
                if href.startswith('/'):
                    href = urljoin(main_page_url, href)
                # Only include actual article pages, not category pages
                if '/fact-check/' in href and not href.endswith('/1') and not href.endswith('/fact-check/'):
                    seen_urls.add(href)
                    article_links.append(href)
                    if len(article_links) >= count:
                        break
        
        worker_logger.info(f"Found {len(article_links)} article links.")
        return article_links[:count]
    except requests.exceptions.RequestException as e:
        worker_logger.error(f"Error fetching the main NewChecker page: {e}")
        return []

def scrape_and_save_article(url: str):
    """Scrape a single NewChecker article and save its content"""
    worker_logger.info(f"  -> Scraping new article: {url}")
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract title - NewChecker uses h1 for article titles
        title_elem = soup.select_one('h1')
        caption = title_elem.text.strip() if title_elem else "Untitled"

        # Extract date - NewChecker shows date in article metadata
        date_elem = soup.select_one('time') or soup.find(string=lambda text: text and any(month in str(text) for month in ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']))
        timestamp = date_elem if isinstance(date_elem, str) else (date_elem.text.strip() if date_elem else "N/A")

        evidence_id = f"newschecker_{uuid.uuid4().hex[:10]}"
        save_dir = EVIDENCE_DB_DIR / evidence_id
        save_dir.mkdir(exist_ok=True)
        
        # Extract the main featured image (banner_image)
        img_elem = soup.select_one('img[alt="banner_image"]') or soup.select_one('article img') or soup.select_one('img')
        img_path = None
        if img_elem and 'src' in img_elem.attrs:
            img_url = img_elem['src']
            # Handle relative URLs
            if not img_url.startswith('http'):
                img_url = urljoin(url, img_url)
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


def run_newschecker_pipeline(count=10):
    """Main pipeline to scrape and index NewChecker articles"""
    worker_logger.info("--- Starting NewChecker Scraper & Indexer Pipeline ---")
    
    latest_links = get_latest_article_links(count=count)
    if not latest_links:
        return {
            "processed_items": [], 
            "newly_scraped_count": 0, 
            "message": "Could not retrieve any article links from NewChecker."
        }

    # Get existing NewChecker items from the database
    existing_items_db = collection.get(where={"source": "newschecker.in"}, include=["metadatas"])
    url_to_data_map = {}
    if existing_items_db and existing_items_db['ids']:
        for i, meta in enumerate(existing_items_db['metadatas']):
            if 'source_url' in meta:
                article_dir = Path(meta['path']).parent
                url_to_data_map[meta['source_url']] = {
                    "caption": (article_dir / "caption.txt").read_text(encoding='utf-8').strip(),
                    "image_path": str(article_dir / "image.jpg"),
                    "source_url": meta['source_url'],
                    "timestamp": meta.get('timestamp', 'Previously Scraped')
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
                worker_logger.info(f"Indexing new NewChecker evidence: {article_data['evidence_id']}")
                
                # Generate embeddings
                img_embedding = get_image_embedding(article_data['image_path'])
                text_embedding = get_text_embedding(article_data['caption'])
                
                metadata = {
                    "source": "newschecker.in", 
                    "source_url": article_data['source_url'], 
                    "timestamp": article_data['timestamp']
                }
                
                # Add to vector database
                if img_embedding:
                    collection.add(
                        embeddings=[img_embedding], 
                        documents=[article_data['caption']], 
                        metadatas=[{"type": "image", "path": article_data['image_path'], **metadata}], 
                        ids=[f"{article_data['evidence_id']}_img"]
                    )
                if text_embedding:
                    collection.add(
                        embeddings=[text_embedding], 
                        documents=[article_data['caption']], 
                        metadatas=[{"type": "text", "path": article_data['caption_path'], **metadata}], 
                        ids=[f"{article_data['evidence_id']}_txt"]
                    )
                processed_items.append(article_data)

    message = f"Processed {len(processed_items)} latest articles. Scraped and indexed {newly_scraped_count} new items."
    if newly_scraped_count == 0 and processed_items:
        message = "Already up-to-date. Displaying the 10 most recent articles from the database."

    return {
        "processed_items": processed_items,
        "newly_scraped_count": newly_scraped_count,
        "message": message
    }


# Standalone execution for testing
if __name__ == "__main__":
    import sys
    import os
    
    # Add the parent directory to the path so we can import from src
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    
    print("Testing NewChecker Scraper...")
    print("=" * 60)
    
    result = run_newschecker_pipeline()
    
    print(f"\n{result['message']}")
    print(f"\nTotal processed: {len(result['processed_items'])}")
    print(f"Newly scraped: {result['newly_scraped_count']}")
    
    if result['processed_items']:
        print("\nSample articles:")
        for i, item in enumerate(result['processed_items'][:3], 1):
            print(f"\n{i}. {item['caption'][:100]}...")
            print(f"   URL: {item['source_url']}")
            print(f"   Date: {item['timestamp']}")