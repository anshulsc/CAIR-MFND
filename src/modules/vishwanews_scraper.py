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

def get_latest_article_links(count=10):
    """Fetch latest fact-check article links from Vishvas News English"""
    main_page_url = 'https://www.vishvasnews.com/english/viral/'
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
        
        # Vishvas News uses article links with 'fact-check' in their URLs
        all_links = soup.find_all('a', href=True)
        
        for link in all_links:
            href = link.get('href')
            if href:
                # Check if it's a fact-check article URL
                if 'fact-check' in href and '/english/' in href:
                    # Make sure it's a full URL
                    if not href.startswith('http'):
                        href = urljoin(main_page_url, href)
                    
                    # Avoid duplicate URLs and category pages
                    if href not in seen_urls and href != main_page_url:
                        seen_urls.add(href)
                        article_links.append(href)
                        
                        if len(article_links) >= count:
                            break
        
        worker_logger.info(f"Found {len(article_links)} article links.")
        return article_links[:count]
    except requests.exceptions.RequestException as e:
        worker_logger.error(f"Error fetching the main Vishvas News page: {e}")
        return []

def scrape_and_save_article(url: str):
    """Scrape a single Vishvas News article and save its content"""
    worker_logger.info(f"  -> Scraping new article: {url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract title - Vishvas News typically uses h1 for article titles
        title_elem = soup.select_one('h1.entry-title') or soup.select_one('h1')
        caption = title_elem.text.strip() if title_elem else "Untitled"

        # Extract date - look for time element or published date
        date_elem = soup.select_one('time.entry-date') or soup.select_one('time')
        if date_elem:
            timestamp = date_elem.text.strip() if date_elem.text else date_elem.get('datetime', 'N/A')
        else:
            # Try to find date in meta tags
            date_meta = soup.find('meta', property='article:published_time')
            timestamp = date_meta['content'] if date_meta else "N/A"

        evidence_id = f"vishvasnews_{uuid.uuid4().hex[:10]}"
        save_dir = EVIDENCE_DB_DIR / evidence_id
        save_dir.mkdir(exist_ok=True)
        
        # Extract images from article content
        img_path = None
        img_url = None
        
        # Method 1: Try og:image meta tag first
        og_image = soup.find('meta', property='og:image')
        if og_image:
            img_url = og_image.get('content')
        
        # Method 2: Look for images within the article content
        if not img_url:
            # Try different selectors for Vishvas News structure
            img_elements = []
            
            # Check for images in common content areas
            for selector in [
                '.entry-content img',
                'article img',
                '.post-content img',
                'figure img',
                '.wp-post-image',
                'img[class*="featured"]'
            ]:
                found = soup.select(selector)
                if found:
                    img_elements.extend(found)
            
            # Try to get the second or first image (skip potential watermarked images)
            for idx in [1, 0]:  # Try second image first, then first
                if len(img_elements) > idx:
                    img_elem = img_elements[idx]
                    img_url = img_elem.get('src')
                    
                    # Handle data-src, srcset for lazy loading
                    if not img_url or img_url.startswith('data:'):
                        img_url = (img_elem.get('data-src') or 
                                  img_elem.get('data-lazy-src') or 
                                  img_elem.get('data-original') or
                                  img_elem.get('data-layzr'))
                        
                        # Try srcset as fallback
                        if not img_url:
                            srcset = img_elem.get('srcset')
                            if srcset:
                                # Get first URL from srcset
                                img_url = srcset.split(',')[0].split()[0]
                    
                    # Skip placeholder or logo images
                    if img_url and not any(skip in img_url.lower() for skip in ['placeholder', 'logo', 'icon']):
                        break
                    else:
                        img_url = None
        
        if img_url:
            # Handle relative URLs
            if not img_url.startswith('http'):
                img_url = urljoin(url, img_url)
            
            # Skip unwanted images
            if not any(skip in img_url.lower() for skip in ['placeholder', 'logo', 'icon']):
                try:
                    img_data = requests.get(img_url, timeout=15, headers=headers).content
                    img_path = save_dir / "image.jpg"
                    with open(img_path, 'wb') as handler:
                        handler.write(img_data)
                    worker_logger.info(f"Downloaded image from: {img_url}")
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


def run_vishvasnews_pipeline(count=10):
    """Main pipeline to scrape and index Vishvas News articles"""
    worker_logger.info("--- Starting Vishvas News Scraper & Indexer Pipeline ---")
    
    latest_links = get_latest_article_links(count=count)
    if not latest_links:
        return {
            "processed_items": [], 
            "newly_scraped_count": 0, 
            "message": "Could not retrieve any article links from Vishvas News."
        }

    # Get existing Vishvas News items from the database
    existing_items_db = collection.get(where={"source": "vishvasnews.com"}, include=["metadatas"])
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
                worker_logger.info(f"Indexing new Vishvas News evidence: {article_data['evidence_id']}")
                
                # Generate embeddings
                img_embedding = get_image_embedding(article_data['image_path'])
                text_embedding = get_text_embedding(article_data['caption'])
                
                metadata = {
                    "source": "vishvasnews.com", 
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
    
    print("Testing Vishvas News Scraper...")
    print("=" * 60)
    
    result = run_vishvasnews_pipeline()
    
    print(f"\n{result['message']}")
    print(f"\nTotal processed: {len(result['processed_items'])}")
    print(f"Newly scraped: {result['newly_scraped_count']}")
    
    if result['processed_items']:
        print("\nSample articles:")
        for i, item in enumerate(result['processed_items'][:3], 1):
            print(f"\n{i}. {item['caption'][:100]}...")
            print(f"   URL: {item['source_url']}")
            print(f"   Date: {item['timestamp']}")