# pages/2_Query_Details.py (Corrected and Robust)
import streamlit as st
import requests
import json
import re
from pathlib import Path
from src.config import PROCESSED_DIR # Import for finding local files

import os
API_URL = os.getenv("API_URL", "http://localhost:8000")

# --- Page Configuration ---
st.set_page_config(page_title="Query Details", layout="wide")

# --- Helper function for styling (no changes) ---
def render_styled_markdown(text):
    text = text.replace("`Sentiment Aligned`", '<span style="color:green; font-weight:bold;">Sentiment Aligned</span>')
    text = text.replace("`Entities Aligned`", '<span style="color:green; font-weight:bold;">Entities Aligned</span>')
    text = text.replace("`Event/Action Aligned`", '<span style="color:green; font-weight:bold;">Event/Action Aligned</span>')
    text = text.replace("`Sentiment Mismatch`", '<span style="color:red; font-weight:bold;">Sentiment Mismatch</span>')
    text = text.replace("`Entities Mismatch`", '<span style="color:red; font-weight:bold;">Entities Mismatch</span>')
    text = text.replace("`Event/Action Mismatch`", '<span style="color:red; font-weight:bold;">Event/Action Mismatch</span>')
    text = re.sub(r"### (.*?)\n", r'<h4>\1</h4>', text)
    text = text.replace("---", "<hr>")
    st.markdown(text, unsafe_allow_html=True)

# Check login status
if not st.session_state.get('logged_in'):
    st.warning("Please login from the main Dashboard to view details.")
    st.stop()

username = st.session_state.username

# --- Main Page Logic ---
# Correctly read query_id from st.query_params
if "selected_query_id" not in st.session_state:
    st.error("No Query ID specified. Please select a query from the Dashboard.")
    if st.button("Back to Dashboard", icon="🏠"):
        st.switch_page("Dashboard.py")
else:
    query_id = st.session_state.selected_query_id
    # The rest of the page code remains EXACTLY THE SAME.
    # It will now correctly use the query_id from the session state.
    try:
        response = requests.get(f"{API_URL}/details/{query_id}")
        response.raise_for_status()
        data = response.json()
        
        results = data.get('results', {}).get('stage2_outputs', {})
        metadata = data.get('metadata', {})
        status = data.get('status', {})

        if not results or not metadata:
            st.error("Incomplete data received from API. The analysis may still be in progress or failed.")
            if st.button("Back to Dashboard"):
                st.switch_page("Dashboard.py")
            st.stop()

        # --- Verdict Banner ---
        final_response = results.get('final_response', "")
        verdict_match = re.search(r"\*\*Final Classification\*\*:\s*(\w+)", final_response, re.IGNORECASE)
        verdict = verdict_match.group(1).upper() if verdict_match else "UNCERTAIN"

        if "FAKE" in verdict:
            st.error(f"##  Verdict: FAKE NEWS", icon="❌")
        else:
            st.success(f"## Verdict: TRUE NEWS", icon="✅")

        st.title(f"Analysis Details for Query: `{query_id}`")
        if st.button("Back to Dashboard", icon="🏠"):
            st.switch_page("Dashboard.py")
        st.divider()

        # --- Media Display ---
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Query Sample")
            q_img_path = metadata.get('query_image_path')
            q_cap_path = metadata.get('query_caption_path')
            if q_img_path and Path(q_img_path).exists():
                st.image(q_img_path, width='content')
            if q_cap_path and Path(q_cap_path).exists():
                st.caption(f"\"{Path(q_cap_path).read_text().strip()}\"")

        with col2:
            st.subheader("Top Visual Evidence")
            # Update path to include username
            if username:
                best_evidence_path = PROCESSED_DIR / username / query_id / "best_evidence.jpg"
            else:
                best_evidence_path = PROCESSED_DIR / query_id / "best_evidence.jpg"
                
            if best_evidence_path.exists():
                st.image(str(best_evidence_path), width='stretch')
                if metadata.get('evidences'):
                    from src.config import BASE_DIR
                    evidence_caption_rel = metadata['evidences'][0]['caption_path']
                    evidence_caption_path = BASE_DIR / evidence_caption_rel
                    if evidence_caption_path.exists():
                        evidence_caption = evidence_caption_path.read_text(encoding='utf-8').strip()
                        st.caption(f"\"{evidence_caption}\"")
            else:
                st.info("No distinct visual evidence was found or used.")
        st.divider()

        # --- Detailed Analysis Tabs ---
        tab1, tab2, tab3, tab4 = st.tabs(["🧠 Final Reasoning", "🖼️ Image vs. Text", "🔍 Image vs. Image", "📝 Text vs. Text"])
        
        # ... (The content of the tabs remains exactly the same) ...
        with tab1:
            st.subheader("Final Unified Reasoning")
            render_styled_markdown(results.get('final_response', "Not available."))
        with tab2:
            st.subheader("Image vs. Text Consistency Analysis")
            render_styled_markdown(results.get('img_txt_result', "Not available."))
        with tab3:
            st.subheader("Query Image vs. Evidence Image Analysis")
            render_styled_markdown(results.get('qimg_eimg_result', "Not available."))
        with tab4:
            st.subheader("Text vs. Text Factual Consistency")
            st.info(f"**Claim Verification Summary:** {results.get('claim_verification_str', 'Not available.')}")
            st.markdown("**Rationale Summary from Evidences:**")
            st.warning(results.get('txt_txt_rational_summary', ["Not available."])[0])
            with st.expander("Show Individual Text-to-Text Comparisons"):
                for i, res_str in enumerate(results.get('txt_txt_results', [])):
                    try:
                        res_json = json.loads(re.sub(r"```json|```", "", res_str).strip())
                        st.json(res_json, expanded=False)
                    except json.JSONDecodeError:
                        st.text(res_str)


    except requests.exceptions.RequestException as e:
        st.error(f"Failed to fetch details for Query ID '{query_id}': {e}")