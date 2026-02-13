# pages/4_Trash.py
import streamlit as st
import requests
import pandas as pd

import os
API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Trash", page_icon="🗑️", layout="wide")
st.title("🗑️ Trashed Queries")
st.info("Queries moved to trash can be restored or permanently deleted.")


# Check login status
if not st.session_state.get('logged_in'):
    st.warning("Please login from the main Dashboard to view trash.")
    st.stop()

username = st.session_state.username

def get_queries():
    try:
        response = requests.get(f"{API_URL}/queries", params={"username": username})
        response.raise_for_status()
        # Filter for only trashed items
        all_queries = response.json().get("queries", [])
        return [q for q in all_queries if q['status'] == 'trashed']
    except requests.exceptions.RequestException as e:
        st.error(f"Could not connect to the API: {e}")
        return None

def restore_query(query_id):
    try:
        response = requests.post(f"{API_URL}/restore/{query_id}")
        response.raise_for_status()
        st.toast(f"✅ Query '{query_id}' restored and re-queued.", icon="♻️")
        return True
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to restore: {e.response.json().get('detail')}")
        return False

def delete_permanently(query_id):
    try:
        response = requests.delete(f"{API_URL}/delete_permanent/{query_id}")
        response.raise_for_status()
        st.toast(f"🔥 Query '{query_id}' permanently deleted.", icon="🗑️")
        return True
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to delete: {e.response.json().get('detail')}")
        return False

# --- Main Page UI ---
if st.button("Refresh"):
    st.rerun()

trashed_queries = get_queries()

if trashed_queries is None:
    st.warning("Could not load data from API.")
elif not trashed_queries:
    st.success("The trash is empty!")
else:
    for q in trashed_queries:
        query_id = q['query_id']
        with st.container(border=True):
            col1, col2, col3 = st.columns([4, 2, 2])
            with col1:
                st.markdown(f"**Query ID:** `{query_id}`")
                st.caption(f"Moved to trash on: {pd.to_datetime(q['updated_at']).strftime('%Y-%m-%d %H:%M')}")
            
            with col2:
                if st.button("Restore", key=f"restore_{query_id}", width="stretch"):
                    if restore_query(query_id):
                        st.rerun()
            
            with col3:
                # Add a confirmation for a destructive action
                if f"confirm_delete_{query_id}" not in st.session_state:
                    st.session_state[f"confirm_delete_{query_id}"] = False

                if st.session_state[f"confirm_delete_{query_id}"]:
                    st.warning("Are you sure? This cannot be undone.")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("YES, DELETE", key=f"yes_{query_id}", type="primary", width="stretch"):
                            if delete_permanently(query_id):
                                del st.session_state[f"confirm_delete_{query_id}"]
                                st.rerun()
                    with c2:
                         if st.button("NO, CANCEL", key=f"no_{query_id}", width="stretch"):
                             st.session_state[f"confirm_delete_{query_id}"] = False
                             st.rerun()
                else:
                    if st.button("Delete Permanently", key=f"delete_{query_id}", type="secondary", width="stretch"):
                        st.session_state[f"confirm_delete_{query_id}"] = True
                        st.rerun()