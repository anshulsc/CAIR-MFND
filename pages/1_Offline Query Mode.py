# pages/1_Add_New_Query.py
import streamlit as st
import requests
import io

import os
API_URL = os.getenv("API_URL", "http://localhost:8000")

# Check login status
if not st.session_state.get('logged_in'):
    st.warning("Please login from the main Dashboard to add queries.")
    st.stop()

username = st.session_state.username

st.set_page_config(page_title="Add New Query", page_icon="➕", layout="wide")
st.title("➕ Add a New Query for Analysis")
st.markdown("Choose one of the methods below to submit a new news sample.")

tab1, tab2 = st.tabs(["📁 Upload Image & Caption", "Upload Zipped Folder"])

# --- Tab 1: Manual Upload ---
with tab1:
    st.header("Method 1: Upload Image and Type Caption")
    with st.form("manual_query_form"):
        image_file = st.file_uploader(
            "Upload News Image", 
            type=['png', 'jpg', 'jpeg', 'webp']
        )
        caption_text = st.text_area(
            "Enter the News Caption / Text",
            height=150,
            placeholder="e.g., 'Delhi records season's coldest morning...'"
        )
        submitted = st.form_submit_button("Submit for Analysis")

        if submitted:
            if image_file is None or not caption_text.strip():
                st.error("Please upload an image and provide a caption.")
            else:
                files = {'image': (image_file.name, image_file.getvalue(), image_file.type)}
                data = {'caption': caption_text, 'username': username}
                try:
                    with st.spinner("Uploading and queueing query..."):
                        response = requests.post(f"{API_URL}/add_query_manual", files=files, data=data)
                        response.raise_for_status()
                    st.success(f"Successfully added query! New Query ID: `{response.json()['query_id']}`")
                except requests.exceptions.RequestException as e:
                    st.error(f"Upload failed: {e}")

# --- Tab 2: Folder Upload ---
with tab2:
    st.header("Method 2: Upload a Zipped Folder")
    st.info("""
        Please ensure your `.zip` file contains exactly two files:
        - An image file (e.g., `query_img.jpg`)
        - A text file named `query_cap.txt`
    """)
    
    zip_file = st.file_uploader("Upload a .zip file", type="zip")
    
    if st.button("Submit Zipped Folder"):
        if zip_file is None:
            st.error("Please upload a .zip file.")
        else:
            files = {'file': (zip_file.name, zip_file.getvalue(), 'application/zip')}
            data = {'username': username}
            try:
                with st.spinner("Uploading and extracting folder..."):
                    response = requests.post(f"{API_URL}/add_query_folder", files=files, data=data)
                    response.raise_for_status()
                st.success(f"Successfully uploaded folder! New Query ID: `{response.json()['query_id']}`")
            except requests.exceptions.RequestException as e:
                st.error(f"Upload failed: {e}")