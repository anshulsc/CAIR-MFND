import streamlit as st
import requests
import pandas as pd
import json
import time
import html
from pathlib import Path
from streamlit_autorefresh import st_autorefresh

from src.config import QUERIES_DIR
from src.auth import user_manager

st.set_page_config(
    page_title="Fake News Detection Dashboard",
    page_icon="🛡️",
    layout="wide"
)

# --- Login Logic ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None

def login_page():
    st.title("🔐 Login")
    
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login"):
            if user_manager.authenticate_user(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success("Logged in successfully!")
                st.rerun()
            else:
                st.error("Invalid username or password")

    with tab2:
        new_user = st.text_input("Username", key="reg_user")
        new_pass = st.text_input("Password", type="password", key="reg_pass")
        if st.button("Register"):
            success, msg = user_manager.register_user(new_user, new_pass)
            if success:
                st.success(msg)
            else:
                st.error(msg)

if not st.session_state.logged_in:
    login_page()
    st.stop()

# Add logout button in sidebar
with st.sidebar:
    st.write(f"Logged in as: **{st.session_state.username}**")
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.rerun()

import os
API_URL = os.getenv("API_URL", "http://localhost:8000")

# ============= OPTIMIZED API FUNCTIONS =============
@st.cache_data(ttl=30)  # Cache for 2 seconds to reduce API calls
def get_queries(username):
    """Fetch queries with short-term caching"""
    try:
        response = requests.get(f"{API_URL}/queries", params={"username": username}, timeout=5)
        response.raise_for_status()
        return response.json().get("queries", [])
    except requests.exceptions.RequestException as e:
        st.error(f"Could not connect to the API: {e}")
        return None

def move_to_trash(query_id):
    """Move query to trash and return success status"""
    try:
        response = requests.delete(f"{API_URL}/trash/{query_id}", timeout=5)
        response.raise_for_status()
        st.toast(f"Query '{query_id}' moved to trash.", icon="🗑️")
        return True
    except requests.exceptions.RequestException as e:
        error_msg = e.response.json().get('detail') if e.response else str(e)
        st.error(f"Failed to move to trash: {error_msg}")
        return False

def rerun_query(query_id):
    """Rerun query and return success status"""
    try:
        response = requests.post(f"{API_URL}/rerun/{query_id}", timeout=5)
        response.raise_for_status()
        st.toast(f"✅ Successfully queued '{query_id}' for rerun!", icon="🔄")
        return True
    except requests.exceptions.RequestException as e:
        error_msg = e.response.json().get('detail') if e.response else str(e)
        st.error(f"Failed to rerun query: {error_msg}")
        return False



@st.cache_data(ttl=60)
def read_caption_file(query_id, username):
    """Read caption file with caching"""
    try:
        if username:
            query_dir = QUERIES_DIR / username / query_id
        else:
            query_dir = QUERIES_DIR / query_id
            
        caption_path = next(query_dir.glob("*.txt"))
        return caption_path.read_text().strip()
    except (StopIteration, FileNotFoundError):
        return "[Caption not found]"

def get_image_base64(image_path):
    """Convert local image to base64 for display"""
    try:
        import base64
        path = Path(image_path)
        if path.exists():
            with open(path, "rb") as img_file:
                encoded = base64.b64encode(img_file.read()).decode()
                ext = path.suffix.lower()
                mime_type = {
                    '.jpg': 'jpeg', '.jpeg': 'jpeg',
                    '.png': 'png', '.gif': 'gif',
                    '.webp': 'webp', '.svg': 'svg+xml'
                }.get(ext, 'jpeg')
                return f"data:image/{mime_type};base64,{encoded}"
    except Exception as e:
        print(f"Error loading image: {e}")
    return None

def get_verdict_badge(verdict):
    """Generate glassmorphic verdict badge HTML"""
    verdict_lower = str(verdict).lower()
    
    if verdict_lower in ['true', 'verified', 'real', 'authentic']:
        bg_color = "rgba(34, 197, 94, 0.15)"
        border_color = "rgba(34, 197, 94, 0.4)"
        text_color = "#22c55e"
        icon = "✓"
        label = "VERIFIED"
    elif verdict_lower in ['fake', 'false', 'misleading', 'fabricated']:
        bg_color = "rgba(239, 68, 68, 0.15)"
        border_color = "rgba(239, 68, 68, 0.4)"
        text_color = "#ef4444"
        icon = "✕"
        label = "FAKE"
    else:
        bg_color = "rgba(251, 191, 36, 0.15)"
        border_color = "rgba(251, 191, 36, 0.4)"
        text_color = "#fbbf24"
        icon = "?"
        label = "UNCERTAIN"
    
    return f"""
        <div style="
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: {bg_color};
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1.5px solid {border_color};
            color: {text_color};
            padding: 8px 18px;
            border-radius: 50px;
            font-size: 0.7rem;
            font-weight: 800;
            letter-spacing: 1.2px;
            text-transform: uppercase;
            box-shadow: 0 4px 20px rgba(0,0,0,0.15);
        ">
            <span style="font-size: 1rem; font-weight: 900;">{icon}</span>
            {label}
        </div>
    """

@st.cache_data(ttl=5)
def get_highlight_news():
    """Fetch highlight news with caching"""
    try:
        response = requests.get(f"{API_URL}/highlight_news", timeout=5)
        response.raise_for_status()
        return response.json().get("highlights", [])
    except requests.exceptions.RequestException as e:
        print(f"Could not fetch highlight news: {e}")
        return []

# ============= STYLING =============
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Hide Streamlit's running indicator */
    .stApp [data-testid="stStatusWidget"] {
        display: none;
    }
    
    /* Hide the rerun emoji/icon at top right */
    .stApp header [data-testid="stStatusWidget"] {
        display: none !important;
        visibility: hidden !important;
    }
    
    /* Modern Navigation Buttons */
    div[data-testid="column"] button {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        color: white;
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 50%;
        width: 56px;
        height: 56px;
        font-size: 24px;
        font-weight: 300;
        box-shadow: 0 8px 32px rgba(0,0,0,0.2);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        cursor: pointer;
    }
    
    div[data-testid="column"] button:hover {
        background: rgba(255, 255, 255, 0.25);
        border-color: rgba(255, 255, 255, 0.4);
        box-shadow: 0 12px 48px rgba(0,0,0,0.3);
        transform: scale(1.1);
    }
    
    div[data-testid="column"] button:active {
        transform: scale(0.95);
    }
    
    /* Smooth animations */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px) scale(0.95); }
        to { opacity: 1; transform: translateY(0) scale(1); }
    }
    
    @keyframes slideIn {
        from { opacity: 0; transform: translateX(30px); }
        to { opacity: 1; transform: translateX(0); }
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.8; transform: scale(1.15); }
    }
    
    .carousel-item {
        animation: fadeIn 0.6s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    .carousel-content {
        animation: slideIn 0.8s cubic-bezier(0.4, 0, 0.2, 1) 0.2s both;
    }
    
    .carousel-image {
        width: 100%;
        height: 100%;
        object-fit: cover;
        object-position: center;
        transition: transform 0.6s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    .carousel-item:hover .carousel-image {
        transform: scale(1.03);
    }
    
    .indicator-dot {
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    .indicator-dot:hover {
        transform: scale(1.3);
    }
    
    /* Smooth content transitions */
    .element-container {
        transition: opacity 0.3s ease-in-out;
    }
</style>
""", unsafe_allow_html=True)

# ============= MAIN APP =============
st.title("🛡️ Fake News Detection Dashboard")
st.markdown("Monitor the status of all news queries and view their analysis reports.")

# Initialize session state
if 'previous_queries' not in st.session_state:
    st.session_state.previous_queries = {}
if 'search_term' not in st.session_state:
    st.session_state.search_term = ""
if 'carousel_index' not in st.session_state:
    st.session_state.carousel_index = 0
if 'last_manual_carousel_time' not in st.session_state:
    st.session_state.last_manual_carousel_time = 0
if 'notification_shown' not in st.session_state:
    st.session_state.notification_shown = set()

# ============= CAROUSEL FRAGMENT (runs independently) =============
@st.fragment(run_every=5000)
def carousel_fragment():
    """Carousel that auto-updates without blocking the rest of the app"""
    highlight_items_data = get_highlight_news()
    
    if not highlight_items_data:
        return
    
    st.markdown("### 🌟 Highlighted News")
    st.markdown("")
    
    # Check if user manually navigated recently (30 second cooldown)
    current_time = time.time()
    if (current_time - st.session_state.last_manual_carousel_time) > 30:
        # Auto-advance carousel
        st.session_state.carousel_index = (st.session_state.carousel_index + 1) % len(highlight_items_data)
    
    current_item = highlight_items_data[st.session_state.carousel_index % len(highlight_items_data)]
    
    # Navigation
    nav_left, carousel_col, nav_right = st.columns([0.5, 10, 0.5])
    
    with nav_left:
        st.markdown("<br><br><br><br><br>", unsafe_allow_html=True)
        if st.button("‹", key="carousel_prev", width="stretch"):
            st.session_state.carousel_index = (st.session_state.carousel_index - 1) % len(highlight_items_data)
            st.session_state.last_manual_carousel_time = time.time()
    
    with nav_right:
        st.markdown("<br><br><br><br><br>", unsafe_allow_html=True)
        if st.button("›", key="carousel_next", width="stretch"):
            st.session_state.carousel_index = (st.session_state.carousel_index + 1) % len(highlight_items_data)
            st.session_state.last_manual_carousel_time = time.time()
    
    with carousel_col:
        img_path = current_item['img_path']
        img_data = get_image_base64(img_path)
        verdict = current_item.get('text', '').lower()
        verdict_badge = get_verdict_badge(verdict)
        title_text = str(current_item.get('title', 'Untitled'))
        title_escaped = html.escape(title_text)
        
        carousel_html = f"""
            <div class="carousel-item" style="
                position: relative; height: 500px; border-radius: 24px; overflow: hidden;
                box-shadow: 0 20px 60px rgba(0,0,0,0.2); margin: 10px 0 20px 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            ">
                {f'<img src="{img_data}" class="carousel-image" alt="News image">' if img_data else ''}
                <div style="
                    position: absolute; top: 0; left: 0; right: 0; bottom: 0;
                    background: linear-gradient(180deg, rgba(0,0,0,0) 0%, rgba(0,0,0,0.2) 40%, rgba(0,0,0,0.9) 100%);
                    transition: background 0.6s ease;
                "></div>
                <div class="carousel-content" style="
                    position: absolute; bottom: 0; left: 0; right: 0; padding: 45px; z-index: 2;
                ">
                    <div style="display: flex; align-items: center; gap: 16px; margin-bottom: 24px;">
                        <div style="
                            display: inline-flex; align-items: center; gap: 10px;
                            background: rgba(255,255,255,0.15); backdrop-filter: blur(12px);
                            border: 1px solid rgba(255,255,255,0.25); color: white;
                            padding: 10px 20px; border-radius: 50px; font-size: 0.7rem;
                            font-weight: 700; letter-spacing: 1px; text-transform: uppercase;
                            box-shadow: 0 4px 20px rgba(0,0,0,0.2);
                        ">
                            <span style="
                                width: 10px; height: 10px; background: #22c55e; border-radius: 50%;
                                display: inline-block; animation: pulse 2s ease-in-out infinite;
                                box-shadow: 0 0 12px rgba(34,197,94,0.7);
                            "></span>
                            Trending Now
                        </div>
                    </div>
                    <h1 style="
                        margin: 0 0 16px 0; font-size: 2.5rem; font-weight: 800; color: white;
                        text-shadow: 0 4px 20px rgba(0,0,0,0.5); line-height: 1.2;
                        overflow: hidden; text-overflow: ellipsis; display: -webkit-box;
                        -webkit-line-clamp: 2; -webkit-box-orient: vertical; letter-spacing: -0.8px;
                    ">{title_escaped}</h1>
                    {verdict_badge}
        """
        st.markdown(carousel_html, unsafe_allow_html=True)
    
    # Indicator dots
    indicator_html = '<div style="text-align: center; margin: 20px 0 30px 0; display: flex; justify-content: center; align-items: center; gap: 10px;">'
    for idx in range(len(highlight_items_data)):
        if idx == st.session_state.carousel_index % len(highlight_items_data):
            indicator_html += '<span class="indicator-dot" style="display: inline-block; width: 36px; height: 8px; border-radius: 4px; background: linear-gradient(90deg, #6366f1 0%, #8b5cf6 100%); margin: 0 3px; box-shadow: 0 2px 12px rgba(99,102,241,0.5);"></span>'
        else:
            indicator_html += '<span class="indicator-dot" style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: rgba(209,213,219,0.5); margin: 0 3px; cursor: pointer;"></span>'
    indicator_html += '</div>'
    st.markdown(indicator_html, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.divider()

# ============= QUERY LIST FRAGMENT (runs independently with auto-refresh) =============
@st.fragment(run_every=300)
def query_list_fragment():
    """Query list that auto-updates without freezing the UI"""
    
    queries = get_queries(st.session_state.username)
    
    # Check for newly completed queries and show notifications (only once per query)
    if queries is not None:
        current_queries_dict = {q['query_id']: q for q in queries}
        
        for query_id, query_data in current_queries_dict.items():
            prev_data = st.session_state.previous_queries.get(query_id, {})
            prev_status = prev_data.get('status')
            current_status = query_data['status']
            
            # Full completion notification (only show once)
            notification_key = f"{query_id}_completed"
            if prev_status and prev_status != 'completed' and current_status == 'completed':
                if notification_key not in st.session_state.notification_shown:
                    st.toast(f"✅ Analysis Complete: '{query_id}'", icon="✅")
                    st.session_state.notification_shown.add(notification_key)
            
            # Stage completion notifications (only show once per stage)
            if prev_data.get('stages'):
                prev_stages = json.loads(prev_data.get('stages', '{}'))
                current_stages = json.loads(query_data.get('stages', '{}'))
                
                evidence_key = f"{query_id}_evidence"
                if prev_stages.get('evidence_extraction') != 'completed' and \
                   current_stages.get('evidence_extraction') == 'completed':
                    if evidence_key not in st.session_state.notification_shown:
                        st.toast(f"🔍 Evidence extracted for '{query_id}'", icon="📊")
                        st.session_state.notification_shown.add(evidence_key)
                
                model_key = f"{query_id}_model"
                if prev_stages.get('model_inference') != 'completed' and \
                   current_stages.get('model_inference') == 'completed':
                    if model_key not in st.session_state.notification_shown:
                        st.toast(f"🤖 AI analysis complete for '{query_id}'", icon="🧠")
                        st.session_state.notification_shown.add(model_key)
                
                pdf_key = f"{query_id}_pdf"
                if prev_stages.get('pdf_generation') != 'completed' and \
                   current_stages.get('pdf_generation') == 'completed':
                    if pdf_key not in st.session_state.notification_shown:
                        st.toast(f"📄 Report ready for '{query_id}'", icon="📤")
                        st.session_state.notification_shown.add(pdf_key)
        
        st.session_state.previous_queries = current_queries_dict
    
    if queries is None:
        st.warning("Could not load data from API. Is the API server running?")
        return
    elif not queries:
        st.info("No queries found. Add a new query using the 'Add New Query' page.")
        return
    
    # Filter queries
    filtered_queries = []
    search_lower = st.session_state.search_term.lower()
    
    for q in queries:
        caption_text = read_caption_file(q['query_id'], q.get('username'))
        q['caption_text'] = caption_text
        
        if search_lower in q['query_id'].lower() or search_lower in caption_text.lower():
            filtered_queries.append(q)
    
    st.subheader(f"Displaying {len(filtered_queries)} of {len(queries)} Queries")
    st.divider()
    
    if not filtered_queries:
        st.warning("No queries match your search term.")
        return
    
    # Display queries
    for q in sorted(filtered_queries, key=lambda x: x['created_at'], reverse=True):
        if q['status'] == 'trashed':
            continue
        
        query_id = q['query_id']
        status = q['status']
        stages = json.loads(q['stages'])
        status_icon = {"pending": "🕒", "processing": "⚙️", "completed": "✅", "failed": "❌"}
        verdict = q.get('verdict', 'N/A')
        verdict_icon = {"True": "✅", "Fake": "❌", "Uncertain": "❓", "Error": "🔥"}
        caption_text = q['caption_text']
        
        with st.container(border=True):
            col1, col2, col3, col4 = st.columns([4, 2, 2, 2])
            
            with col1:
                st.markdown(f"**Query ID:** `{query_id}`")
                st.info(f"**Caption:** {caption_text[:100] + ('...' if len(caption_text) > 100 else '')}")
            
            with col2:
                st.markdown(f"**Status:** {status_icon.get(status, '❓')} {status.title()}")
                st.markdown(f"""<small>{status_icon.get(stages['evidence_extraction'])} Evidence<br>{status_icon.get(stages['model_inference'])} Inference<br>{status_icon.get(stages['pdf_generation'])} PDF</small>""", unsafe_allow_html=True)
            
            with col3:
                st.markdown("**Verdict**")
                if status == 'completed':
                    if verdict == "True" or verdict == "Real":
                        verdict = "True"
                        st.success(f" {verdict}", icon=verdict_icon[verdict])
                    elif verdict == "Fake":
                        st.error(f" {verdict}", icon=verdict_icon[verdict])
                    else:
                        st.warning(f"{verdict}", icon=verdict_icon.get(verdict, '❓'))
                else:
                    st.caption("Processing...")
                
                if status == 'failed':
                    with st.expander("Show Error"):
                        st.error(f"{q.get('error_message', 'Unknown error')}")
            
            with col4:
                st.markdown("**Actions**")
                b_col1, b_col2, b_col3, b_col4 = st.columns([1, 1, 1, 1])
                
                with b_col1:
                    if st.button("👁️", key=f"details_{query_id}", help="View analysis details page"):
                        st.session_state.selected_query_id = query_id
                        st.switch_page("pages/2_Query_Details.py")
                
                with b_col2:
                    if status == 'completed' and q.get("result_pdf_path"):
                        st.link_button("📤", f"{API_URL}/results/{query_id}", help="Open final PDF report")
                
                with b_col3:
                    if st.button("🔄", key=f"rerun_{query_id}", help="Rerun analysis for this query"):
                        if rerun_query(query_id):
                            get_queries.clear()
                            st.rerun(scope="fragment")
                
                with b_col4:
                    if st.button("🗑️", key=f"trash_{query_id}", help="Move this query to the trash"):
                        if move_to_trash(query_id):
                            get_queries.clear()
                            st.rerun(scope="fragment")

# ============= RENDER FRAGMENTS =============
# Render carousel
carousel_fragment()

# Search bar (outside fragment to avoid resetting on every rerun)
st.markdown("<br>", unsafe_allow_html=True)

search_term = st.text_input(
    "🔎 Search Queries",
    value=st.session_state.search_term,
    placeholder="Type to search by Query ID or Caption content...",
    help="Your query list will update in real-time as you type.",
    key="search_input"
)
st.session_state.search_term = search_term

if st.button("🔄 Refresh All", key="main_refresh"):
    st.session_state.search_term = ""
    get_queries.clear()
    get_highlight_news.clear()
    st.rerun()

# Render query list
query_list_fragment()