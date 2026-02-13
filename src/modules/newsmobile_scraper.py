import requests
import uuid
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import chromadb
import time

from src.config import EVIDENCE_DB_DIR, VECTOR_DB_DIR
from src.logger_config import worker_logger
from src.modules.embedding_utils import get_image_embedding, get_text_embedding


client = chromadb.PersistentClient(path=str(VECTOR_DB_DIR))
collection = client.get_or_create_collection(name="evidence_collection")

def get_latest_article_links(count=20):
    """Fetch latest fact-check article links from NewsMobile NM Verified"""
    main_page_url = 'https://www.newsmobile.in/news/nm-fact-checker/'
    worker_logger.info(f"Fetching article links from: {main_page_url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(main_page_url, headers=headers, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        article_links = []
        seen_urls = set()
        
        # NewsMobile uses article links that contain '/nm-fact-checker/'
        all_links = soup.find_all('a', href=True)
        
        for link in all_links:
            href = link.get('href')
            if href:
                # Check if it's an article URL (contains /nm-fact-checker/ in path)
                if '/nm-fact-checker/' in href and href != main_page_url:
                    # Make sure it's a full URL
                    if not href.startswith('http'):
                        href = urljoin(main_page_url, href)
                    
                    # Avoid duplicate URLs and pagination pages
                    if href not in seen_urls and '/page/' not in href:
                        seen_urls.add(href)
                        article_links.append(href)
                        
                        if len(article_links) >= count:
                            break
        
        worker_logger.info(f"Found {len(article_links)} article links.")
        return article_links[:count]
    except requests.exceptions.RequestException as e:
        worker_logger.error(f"Error fetching the main NewsMobile page: {e}")
        return []

def scrape_and_save_article(url: str):
    """Scrape a single NewsMobile article and save its content"""
    worker_logger.info(f"  -> Scraping new article: {url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract title - NewsMobile uses h1 for article titles
        title_elem = soup.select_one('h1')
        caption = title_elem.text.strip() if title_elem else "Untitled"

        # Extract date - look for time element or date display
        date_elem = soup.select_one('time')
        if date_elem:
            timestamp = date_elem.text.strip()
        else:
            # Try to find date in meta tags
            date_meta = soup.find('meta', property='article:published_time')
            timestamp = date_meta['content'] if date_meta else "N/A"

        evidence_id = f"newsmobile_{uuid.uuid4().hex[:10]}"
        save_dir = EVIDENCE_DB_DIR / evidence_id
        save_dir.mkdir(exist_ok=True)
        
        # Extract the second image from article content (skip the watermarked featured image)
        # NewsMobile's first image typically has their "VERIFIED" watermark
        img_elements = soup.select('article img, .post-content img')
        
        img_path = None
        img_url = None
        
        # Try to get the second image (index 1) to avoid watermarked image
        if len(img_elements) >= 2:
            img_elem = img_elements[1]
            img_url = img_elem.get('src')
            
            # Handle data-src for lazy loading
            if not img_url or img_url.startswith('data:'):
                img_url = img_elem.get('data-src') or img_elem.get('data-lazy-src')
        # Fallback to first image if only one exists
        elif len(img_elements) == 1:
            img_elem = img_elements[0]
            img_url = img_elem.get('src')
            
            if not img_url or img_url.startswith('data:'):
                img_url = img_elem.get('data-src') or img_elem.get('data-lazy-src')
        
        
        if img_url:
            # Handle relative URLs
            if not img_url.startswith('http'):
                img_url = urljoin(url, img_url)
            
            try:
                img_data = requests.get(img_url, timeout=15, headers=headers).content
                img_path = save_dir / "image.jpg"
                with open(img_path, 'wb') as handler:
                    handler.write(img_data)
            except requests.exceptions.RequestException as e:
                worker_logger.warning(f"Could not download image {img_url}: {e}")
        
        if not img_path:
            worker_logger.warning(f"No image found for article: {url}")
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
    except Exception as e:
        worker_logger.error(f"Unexpected error while scraping {url}: {e}")
        return None


def run_newsmobile_pipeline(count=20):
    """Main pipeline to scrape and index NewsMobile articles"""
    worker_logger.info("--- Starting NewsMobile Scraper & Indexer Pipeline ---")
    
    latest_links = get_latest_article_links(count=count)
    if not latest_links:
        return {
            "processed_items": [], 
            "newly_scraped_count": 0, 
            "message": "Could not retrieve any article links from NewsMobile."
        }

    # Get existing NewsMobile items from the database
    existing_items_db = collection.get(where={"source": "newsmobile.in"}, include=["metadatas"])
    url_to_data_map = {}
    if existing_items_db and existing_items_db['ids']:
        for i, meta in enumerate(existing_items_db['metadatas']):
            if 'source_url' in meta:
                article_dir = Path(meta['path']).parent
                caption_file = article_dir / "caption.txt"
                image_file = article_dir / "image.jpg"
                
                if caption_file.exists() and image_file.exists():
                    url_to_data_map[meta['source_url']] = {
                        "caption": caption_file.read_text(encoding='utf-8').strip(),
                        "image_path": str(image_file),
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
                worker_logger.info(f"Indexing new NewsMobile evidence: {article_data['evidence_id']}")
                
                # Generate embeddings
                img_embedding = get_image_embedding(article_data['image_path'])
                text_embedding = get_text_embedding(article_data['caption'])
                
                metadata = {
                    "source": "newsmobile.in", 
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
            
            # Add a small delay to be respectful to the server
            time.sleep(1)

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
    
    print("Testing NewsMobile Scraper...")
    print("=" * 60)
    
    result = run_newsmobile_pipeline()
    
    print(f"\n{result['message']}")
    print(f"\nTotal processed: {len(result['processed_items'])}")
    print(f"Newly scraped: {result['newly_scraped_count']}")
    
    if result['processed_items']:
        print("\nSample articles:")
        for i, item in enumerate(result['processed_items'][:3], 1):
            print(f"\n{i}. {item['caption'][:100]}...")
            print(f"   URL: {item['source_url']}")
            print(f"   Date: {item['timestamp']}")