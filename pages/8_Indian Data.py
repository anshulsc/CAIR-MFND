import streamlit as st
import json
import requests
from pathlib import Path
import time

from src.config import FAKE_NEWS_DATA_DIR

st.set_page_config(page_title="Data Explorer", page_icon="📚", layout="wide")

if 'scraper_result' not in st.session_state:
    st.session_state.scraper_result = None
if 'selected_scraper' not in st.session_state:
    st.session_state.selected_scraper = None

st.title("🇮🇳 Indian News Database")
st.markdown("Browse and inspect the manually collected fake news samples and their extracted evidence. You can also update the database with the latest articles from live sources.")

import os
API_URL = os.getenv("API_URL", "http://localhost:8000")

# Define scraper configurations
SCRAPERS = {
    "factly": {
        "name": "Factly.in",
        "emoji": "📰",
        "color": "#FF6B6B",
        "endpoint": "/scrape_factly",
        "description": "Fact-checking platform focused on Indian news"
    },
    "boomlive": {
        "name": "BoomLive",
        "emoji": "💥",
        "color": "#4ECDC4",
        "endpoint": "/scrape_boomlive",
        "description": "Multimedia fact-checking organization"
    },
    "factcrescendo": {
        "name": "FactCrescendo",
        "emoji": "🎯",
        "color": "#95E1D3",
        "endpoint": "/scrape_factcrescendo",
        "description": "Independent fact-checking platform"
    },
    "newschecker": {
        "name": "NewsChecker",
        "emoji": "✓",
        "color": "#F38181",
        "endpoint": "/scrape_newschecker",
        "description": "Fact-checking news and misinformation"
    },
    "newsmobile": {
        "name": "NewsMobile",
        "emoji": "📱",
        "color": "#AA96DA",
        "endpoint": "/scrape_newsmobile",
        "description": "News media with fact-checking section"
    },
    "vishvasnews": {
        "name": "Vishvas News",
        "emoji": "🔍",
        "color": "#FCBAD3",
        "endpoint": "/scrape_vishvasnews",
        "description": "Fact-checking in multiple Indian languages"
    }
}

# Custom CSS for better styling
st.markdown("""
<style>
    .scraper-card {
        padding: 1.5rem;
        border-radius: 12px;
        border: 2px solid #e0e0e0;
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        margin-bottom: 1rem;
        transition: all 0.3s ease;
        cursor: pointer;
    }
    .scraper-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        border-color: #4CAF50;
    }
    .scraper-title {
        font-size: 1.3rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    .scraper-desc {
        font-size: 0.9rem;
        color: #666;
        margin-bottom: 0;
    }
    .article-card {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 1rem;
        background: white;
        height: 100%;
        transition: all 0.2s ease;
    }
    .article-card:hover {
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        transform: translateY(-1px);
    }
    .stats-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
        margin-bottom: 1rem;
    }
    .stats-number {
        font-size: 2rem;
        font-weight: bold;
    }
    .stats-label {
        font-size: 0.9rem;
        opacity: 0.9;
    }
</style>
""", unsafe_allow_html=True)

with st.expander("📡 Live Scraper Agent", expanded=True):
    st.info("Select a fact-checking source below to scrape the latest articles. The agent will show all articles and will scrape/index any that are new.")
    
    # Add post count selector
    col_left, col_right = st.columns([1, 3])
    with col_left:
        post_count = st.number_input(
            "Number of articles to scrape",
            min_value=5,
            max_value=30,
            value=10,
            step=1,
            help="Choose how many of the latest articles to scrape"
        )
    with col_right:
        st.markdown(f"**Configured to scrape the latest {post_count} articles**")
    
    st.divider()
    
    # Display scrapers in a grid
    cols = st.columns(3)
    for idx, (scraper_key, scraper_info) in enumerate(SCRAPERS.items()):
        col = cols[idx % 3]
        with col:
            button_label = f"{scraper_info['emoji']} {scraper_info['name']}"
            if st.button(button_label, key=f"btn_{scraper_key}", width="stretch", type="primary"):
                st.session_state.selected_scraper = scraper_key
                st.session_state.scraper_result = None
                st.rerun()
    
    # If a scraper is selected, run it
    if st.session_state.selected_scraper:
        scraper_key = st.session_state.selected_scraper
        scraper_info = SCRAPERS[scraper_key]
        
        st.markdown(f"### {scraper_info['emoji']} Running {scraper_info['name']} Scraper")
        st.caption(scraper_info['description'])
        
        with st.spinner(f"Agent is running... Checking {scraper_info['name']} for new articles, scraping, and indexing..."):
            try:
                response = requests.post(
                    f"{API_URL}{scraper_info['endpoint']}", 
                    json={"count": post_count},
                    timeout=180
                )
                response.raise_for_status()
                st.session_state.scraper_result = response.json()
                st.session_state.scraper_result['scraper_name'] = scraper_info['name']
                st.session_state.scraper_result['scraper_emoji'] = scraper_info['emoji']
                st.toast(f"✅ Scraping complete from {scraper_info['name']}! Refreshing data list...", icon="✅")
                time.sleep(1)
                st.session_state.selected_scraper = None
                st.rerun()
            except requests.exceptions.Timeout:
                st.error(f"⏱️ The request timed out while scraping {scraper_info['name']}.")
                st.session_state.selected_scraper = None
            except requests.exceptions.RequestException as e:
                st.error(f"❌ An API error occurred while scraping {scraper_info['name']}: {e}")
                st.session_state.selected_scraper = None
                st.session_state.scraper_result = None

    # Display results
    if st.session_state.scraper_result:
        result = st.session_state.scraper_result
        scraper_name = result.get('scraper_name', 'Source')
        scraper_emoji = result.get('scraper_emoji', '📰')
        
        # Stats
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"""
            <div class="stats-box" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
                <div class="stats-number">{len(result.get('processed_items', []))}</div>
                <div class="stats-label">Articles Found</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="stats-box" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
                <div class="stats-number">{result.get('newly_scraped_count', 0)}</div>
                <div class="stats-label">Newly Scraped</div>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
            <div class="stats-box" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
                <div class="stats-number">{len(result.get('processed_items', [])) - result.get('newly_scraped_count', 0)}</div>
                <div class="stats-label">Already Indexed</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.success(result.get("message", "Processing finished."))
        
        processed_items = result.get("processed_items", [])
        if processed_items:
            st.subheader(f"{scraper_emoji} Latest Articles from {scraper_name}:")
            cols = st.columns(3)
            for i, item in enumerate(processed_items):
                col = cols[i % 3]
                with col:
                    with st.container(border=True):
                        # Display the image
                        from PIL import Image
                        import io

                        image_path = item.get("image_path")
                        if image_path and Path(image_path).exists():
                            try:
                                with open(image_path, "rb") as f:
                                    img_bytes = f.read()
                                img = Image.open(io.BytesIO(img_bytes))
                                st.image(img, width="stretch")
                            except Exception as e:
                                st.error(f"Could not display image: {e}")
                        else:
                            st.warning("No image available for this article.")
                        
                        st.markdown(f"**{item.get('caption', 'No caption')}**")
                        st.caption(f"📅 Published: {item.get('timestamp', 'N/A')}")
                        
                        if 'source_url' in item:
                            st.link_button("Read Full Article ↗️", item["source_url"], width="stretch")
        
        # Clear button
        if st.button("Clear Results", type="secondary"):
            st.session_state.scraper_result = None
            st.rerun()

st.divider()

@st.cache_data
def load_all_samples_from_api():
    try:
        response = requests.get(f"{API_URL}/data_explorer_samples")
        response.raise_for_status()
        return response.json().get("samples", [])
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to load data from API: {e}")
        return None

all_samples = load_all_samples_from_api()

if all_samples is None:
    st.warning("Could not load data. Is the API server running?")
    st.stop()
elif not all_samples:
    st.info("No valid samples found in the data directory.")
    st.stop()
    
if 'data_search_term' not in st.session_state: st.session_state.data_search_term = ""
search_term = st.text_input("🔎 Search Samples", value=st.session_state.data_search_term, placeholder="Type to search by Sample ID or Caption...")
st.session_state.data_search_term = search_term

filtered_samples = []
if search_term:
    search_lower = search_term.lower()
    for sample in all_samples:
        if search_lower in sample['id'].lower() or search_lower in sample['query_caption'].lower():
            filtered_samples.append(sample)
else:
    filtered_samples = all_samples

st.subheader(f"📊 Displaying {len(filtered_samples)} of {len(all_samples)} Samples")
st.divider()

for sample in filtered_samples:
    with st.expander(f"**Sample `{sample['id']}`**: {sample['query_caption'][:120]}"):
        st.subheader("Original Query")
        col1, col2 = st.columns([1, 2])
        with col1:
            query_image_path = sample.get("query_image")
            if query_image_path and Path(query_image_path).exists():
                try:
                    st.image(query_image_path, width="stretch")
                except Exception as e:
                    st.error(f"Corrupted Image: {Path(query_image_path).name}")
            else:
                st.error("[Query Image file not found]")
        with col2:
            st.info(f"**Caption:** {sample['query_caption']}")

        st.subheader("Collected Evidence")
        if sample.get("evidence_items"):
            cols = st.columns(4)
            for i, item in enumerate(sample["evidence_items"]):
                col = cols[i % 4]
                with col:
                    evidence_image_path = item.get("image")
                    if evidence_image_path and Path(evidence_image_path).exists():
                        try:
                            st.image(evidence_image_path, width="stretch")
                        except Exception as e:
                            st.error(f"Corrupted: {Path(evidence_image_path).name}")
                    else:
                        st.caption("[Image missing]")
                    st.caption(item["title"])
        else:
            st.info("No valid evidence items found for this sample.")

        st.subheader("Brave Search Raw Results")
        if sample.get("brave_json"):
            brave_data = sample["brave_json"]
            if "web" in brave_data and "results" in brave_data["web"]:
                for i, result in enumerate(brave_data["web"]["results"]):
                    with st.container(border=True):
                        st.markdown(f"**{i+1}. {result.get('title', 'No Title')}**")
                        if 'url' in result: st.link_button("Visit Source ↗️", result['url'])
                        st.caption(f"Source: {result.get('meta_url', {}).get('hostname', 'N/A')}")
                        description = result.get('description', 'No description.')
                        st.markdown(description, unsafe_allow_html=True)
            with st.expander("Show Full Raw JSON Data"):
                st.json(brave_data)
        else:
            st.warning("'brave_raw_results.json' not found for this sample.")