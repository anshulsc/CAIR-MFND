# pages/6_FraudNet_Details.py
import streamlit as st
import requests
from pathlib import Path
from src.config import PROCESSED_DIR

# --- Page Configuration ---
st.set_page_config(
    page_title="FraudNet Details",
    page_icon="🔎",
    layout="wide"
)

import os
API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="FraudNet Details", layout="wide")

if "selected_query_id" not in st.session_state:
    st.error("No Query ID specified. Please select a query from the FraudNet Results page.")
    if st.button("Back to FraudNet List", icon="🤖"):
        st.switch_page("pages/4_FraudNet.py")
else:
    query_id = st.session_state.selected_query_id
    try:
        response = requests.get(f"{API_URL}/details/{query_id}")
        response.raise_for_status()
        data = response.json()
        
        fraudnet_result = data.get('results', {}).get('fraudnet_response', {})
        metadata = data.get('metadata', {})

        label_int = fraudnet_result.get("fraudnet_label")
        label_str = "True News" if label_int == 0 else "Fake News"
        confidence = fraudnet_result.get("confidence", 0)

        st.title(f"🤖 FraudNet Details for Query: `{query_id}`")
        if st.button("Back to FraudNet List", icon="⬅️"):
            st.switch_page("pages/6_Fraudnet_Results.py")
        st.divider()

        # --- Display the media side-by-side for comparison ---
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Analyzed Query Sample")
            q_img_path = metadata.get('query_image_path')
            q_cap_path = metadata.get('query_caption_path')
            
            if q_img_path and Path(q_img_path).exists():
                st.image(q_img_path, width="stretch")
            if q_cap_path and Path(q_cap_path).exists():
                st.info(f"**Caption:** \"{Path(q_cap_path).read_text().strip()}\"")

        with col2:
            st.subheader("Top Visual Evidence Used")
            # Get username from metadata for correct path
            username = metadata.get('username')
            if username:
                best_evidence_path = PROCESSED_DIR / username / query_id / "best_evidence.jpg"
            else:
                best_evidence_path = PROCESSED_DIR / query_id / "best_evidence.jpg"
            
            if best_evidence_path.exists():
                st.image(str(best_evidence_path), width="stretch")
                # Safely get the caption for the top evidence
                evidence_caption = "Caption not available."
                if metadata.get('evidences') and len(metadata['evidences']) > 0:
                    from src.config import BASE_DIR
                    evidence_cap_rel = metadata['evidences'][0]['caption_path']
                    top_evidence_cap_path = BASE_DIR / evidence_cap_rel
                    if top_evidence_cap_path.exists():
                        evidence_caption = top_evidence_cap_path.read_text(encoding='utf-8').strip()
                st.warning(f"**Caption:** \"{evidence_caption}\"")
            else:
                st.info("No distinct visual evidence was found or used in the analysis.")
        
        st.divider()

        # --- Display the FraudNet prediction details ---
        st.subheader("FraudNet Model Prediction")
        pred_col1, pred_col2 = st.columns(2)
        with pred_col1:
            st.metric(label="Prediction", value=label_str)
            if label_str == "Fake News":
                st.error("The model predicts this news is FAKE.")
            else:
                st.success("The model predicts this news is TRUE.")

        with pred_col2:
            st.metric(label="Confidence Score", value=f"{confidence*100:.2f}%")
            st.progress(confidence)
            st.caption("This score represents the model's certainty in its prediction.")

    except requests.exceptions.RequestException as e:
        st.error(f"Failed to fetch details for Query ID '{query_id}': {e}")