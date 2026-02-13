# pages/5_Investigate_and_Analyze.py (Rename the file for clarity)
# IMPORTANT: Rename this file from 5_Evidence_Extractor.py to 5_Investigate_and_Analyze.py
# The number prefix in the filename determines its order in the sidebar.

import streamlit as st
import requests
import time

import os
API_URL = os.getenv("API_URL", "http://localhost:8000")

# Check login status
if not st.session_state.get('logged_in'):
    st.warning("Please login from the main Dashboard to use this feature.")
    st.stop()

username = st.session_state.username

st.set_page_config(page_title="Evidence Extractor & Analyze", page_icon="🕵️‍♂️", layout="wide")

# --- Initialize session state ---
if 'investigation_result' not in st.session_state:
    st.session_state.investigation_result = None

st.title("🕵️‍♂️ Investigate & Analyze Pipeline")
st.markdown("""
This powerful agent combines two workflows into one:
1.  **Extract:** It performs an online search for new evidence based on your query caption and adds it to the database.
2.  **Analyze:** It then submits your original query (image + caption) to the main fake news detection pipeline.
""")
st.info("The analysis will leverage the evidence that was just discovered in the investigation step.", icon="💡")


with st.form("investigation_form"):
    image_file = st.file_uploader(
        "Upload the Query Image to Extract Evidences",
        type=['png', 'jpg', 'jpeg', 'webp']
    )
    
    caption_text = st.text_area(
        "Enter the News Caption / Claim to Investigate",
        height=150,
        placeholder="e.g., 'Major political figure seen at controversial event...'"
    )
    
    submitted = st.form_submit_button("Begin Investigation & Analysis", width="stretch", type="primary")

    if submitted:
        st.session_state.investigation_result = None # Clear previous results
        if not image_file or not caption_text.strip():
            st.error("Please upload an image AND provide a caption.")
        else:
            files = {'image': (image_file.name, image_file.getvalue(), image_file.type)}
            data = {'caption': caption_text, 'username': username}
            
            try:
                with st.spinner("Agent at work... This may take a minute..."):
                    # Step 1: Investigating online evidence
                    st.status("**Step 1/2:** Investigating online for new evidence...", state="running")
                    time.sleep(2) # Short pause for UX
                    
                    # Step 2: Submitting for analysis
                    response = requests.post(f"{API_URL}/investigate_and_analyze", files=files, data=data, timeout=120)
                    response.raise_for_status()
                    st.status("**Step 2/2:** Submitting your query for full analysis...", state="running")
                    time.sleep(2) # Short pause for UX
                    
                    st.session_state.investigation_result = response.json()
                    st.status("Investigation complete!", state="complete")

            except requests.exceptions.Timeout:
                st.error("The request timed out. The server may still be processing.")
            except requests.exceptions.RequestException as e:
                st.error(f"An API error occurred: {e}")
                st.session_state.investigation_result = None

# --- Display results outside the form ---
if st.session_state.investigation_result:
    result = st.session_state.investigation_result
    st.divider()
    
    st.success(result.get("message", "Processing complete!"), icon="✅")
    
    extraction_details = result.get("extraction_details", {})
    new_evidence_count = extraction_details.get("new_evidence_count", 0)
    
    if new_evidence_count > 0:
        with st.expander(f"View the {new_evidence_count} new evidence items found online", expanded=True):
            saved_evidence = extraction_details.get("saved_evidence", [])
            cols = st.columns(3)
            for i, evidence in enumerate(saved_evidence):
                col = cols[i % 3]
                with col:
                    with st.container(border=True):
                        st.image(evidence["image_path"], width='content')
                        st.caption(evidence["caption"])
    else:
        st.warning("No new evidence was added during the investigation step. The analysis will proceed with existing knowledge.")
    
    new_query_id = result.get("new_query_id")
    st.info(f"Your query is now being processed with ID: `{new_query_id}`. You can monitor its progress on the Dashboard.", icon="➡️")
    
    if st.button("Go to Dashboard"):
        st.switch_page("Dashboard.py")


    
