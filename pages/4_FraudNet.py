# pages/5_FraudNet_Results.py
import streamlit as st
import requests
import pandas as pd
import json
from pathlib import Path

from src.config import QUERIES_DIR

# --- Page Configuration ---
st.set_page_config(
    page_title="FraudNet Results",
    page_icon="🔎",
    layout="wide"
)

import os
API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="FraudNet Results", page_icon="🤖", layout="wide")

# Check login status
if not st.session_state.get('logged_in'):
    st.warning("Please log in from the Dashboard to access this page.")
    st.stop()

st.title("🤖 FraudNet Prediction Dashboard")
st.markdown("A centralized view of all FraudNet model predictions for completed queries.")

def get_completed_queries(username):
    try:
        response = requests.get(f"{API_URL}/queries", params={"username": username})
        response.raise_for_status()
        all_queries = response.json().get("queries", [])
        # Filter for only completed queries, as only they have results
        return [q for q in all_queries if q['status'] == 'completed']
    except requests.exceptions.RequestException as e:
        st.error(f"Could not connect to the API: {e}")
        return None

if st.button("Refresh Results"):
    st.rerun()

completed_queries = get_completed_queries(st.session_state.username)

if completed_queries is None:
    st.warning("Could not load data from API.")
elif not completed_queries:
    st.info("No queries have been successfully analyzed yet.")
else:
    st.subheader(f"Displaying FraudNet Results for {len(completed_queries)} Queries")
    
    for q in sorted(completed_queries, key=lambda x: x['updated_at'], reverse=True):
        query_id = q['query_id']
        fraudnet_result = q.get('fraudnet_result', {})
        label = fraudnet_result.get('label', 'N/A')
        confidence = fraudnet_result.get('confidence', 0) * 100 # Convert to percentage

        caption_text = "[Caption not found]"
        try:
            username = q.get('username')
            if username:
                caption_path = next((QUERIES_DIR / username / query_id).glob("*.txt"))
            else:
                caption_path = next((QUERIES_DIR / query_id).glob("*.txt"))
            caption_text = caption_path.read_text().strip()
        except (StopIteration, FileNotFoundError):
            pass
            
        with st.container(border=True):
            col1, col2, col3 = st.columns([5, 2, 2])
            with col1:
                st.markdown(f"**Query ID:** `{query_id}`")
                st.caption(f"{caption_text[:120] + '...' if len(caption_text) > 120 else caption_text}")
            
            with col2:
                st.markdown("**Prediction**")
                if label == "True News":
                    st.success(f"✅ {label}")
                elif label == "Fake News":
                    st.error(f"❌ {label}")
                else:
                    st.warning(f"❓ {label}")
                st.progress(int(confidence))
                st.caption(f"{confidence:.2f}% Confidence")
                
            with col3:
                st.markdown("**Actions**")
                if st.button("View FraudNet Details", key=f"details_{query_id}", width="stretch"):
                    st.session_state.selected_query_id = query_id
                    st.switch_page("pages/5_FraudNetDetails.py")