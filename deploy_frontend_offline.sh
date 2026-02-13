#!/bin/bash

# deploy_frontend_offline.sh
# Starts the Streamlit Frontend in OFFLINE mode, connecting to localhost API.

# 1. Set the API URL to localhost
export API_URL="http://localhost:8000"

echo "--- 🚀 Starting Frontend in OFFLINE Mode ---"
echo "👉 Connecting to API at: $API_URL"

# 2. Check if port 8501 is in use and kill it
if fuser 8501/tcp >/dev/null 2>&1; then
    echo "⚠️  Port 8501 is in use. Killing conflicting process..."
    fuser -k 8501/tcp >/dev/null 2>&1
    echo "✅ Port 8501 freed."
    sleep 1
fi

# 3. Run Streamlit
VENV_STREAMLIT="/data/asca/FND/.venv/bin/streamlit"
$VENV_STREAMLIT run Dashboard.py --server.port 8501 --server.address localhost
