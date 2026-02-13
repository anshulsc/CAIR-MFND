# pages/3_Settings.py
import streamlit as st
import subprocess
import time
from src.config import LOGS_DIR

st.set_page_config(page_title="Settings", page_icon="⚙️", layout="wide")
st.title("⚙️ System Settings & Administration")


st.header("Database Management")
st.warning("⚠️ Indexing can be resource-intensive. Please run it when the system is not under heavy load.")

if st.button("Re-Index Evidence Database", type="primary", width="stretch"):
    st.info("Starting the indexing process... Live output will appear below. Please do not navigate away from this page.", icon="⏳")
    
    # Create a placeholder for the live output
    output_container = st.empty()
    log_content = ""
    
    try:
        process = subprocess.Popen(
            ["python", "-m", "tools.build_index"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            bufsize=1 # Line buffered
        )

        # Read the output line by line as it is generated
        for line in iter(process.stdout.readline, ''):
            log_content += line
            output_container.code(log_content, language="log")
            # A small sleep can help make the streaming smoother in some environments
            time.sleep(0.01)

        process.stdout.close()
        return_code = process.wait()

        if return_code == 0:
            st.success("✅ Database indexing completed successfully!", icon="🎉")
        else:
            st.error(f"❌ Indexing failed with return code: {return_code}", icon="🔥")

    except FileNotFoundError:
        st.error("❌ Critical Error: Could not find the 'tools/build_index.py' script.")
    except Exception as e:
        st.error(f"❌ An unexpected error occurred: {e}")


st.divider()
st.header("System Logs")
st.info("View the latest logs to debug the system's automated components. Logs are automatically rotated.")

# --- NEW: Dynamically find log files ---
try:
    log_files = [f for f in LOGS_DIR.iterdir() if f.is_file() and f.suffix == '.log']
    log_file_names = [f.name for f in log_files]
    
    if not log_file_names:
        st.warning("No log files found yet. Please run the backend services to generate logs.")
    else:
        selected_log_name = st.selectbox("Select a log file to view:", options=log_file_names)
        
        log_path = LOGS_DIR / selected_log_name
        if log_path.exists():
            try:
                with open(log_path, 'r', encoding='utf-8') as f:
                    # Read the whole file as it's rotated, so it shouldn't be too large
                    log_content = f.read()
                st.code(log_content, language="log", line_numbers=True)
            except Exception as e:
                st.error(f"Could not read log file: {e}")
        else:
             st.error("Selected log file does not exist.")

except FileNotFoundError:
    st.error(f"Log directory not found at: {LOGS_DIR}")