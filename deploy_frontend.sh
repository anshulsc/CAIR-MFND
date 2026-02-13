#!/bin/bash

# ==============================================================================
#           Agentic Framework UI Sharer Script (Fixed for Ngrok v3+)
# ==============================================================================
# This script starts the Streamlit frontend and exposes it publicly via an
# Ngrok tunnel using the updated API syntax.
# ==============================================================================

set -e

# --- Preamble and Checks ---
echo "======================================="
echo " Sharing Streamlit UI via Ngrok"
echo "======================================="

export NGROK_AUTHTOKEN="35gggfM2YE616aPZr8vzRDVdiWX_47dfae4VJFXC4bWtj4QNp"

if [ -z "$NGROK_AUTHTOKEN" ] || [ "$NGROK_AUTHTOKEN" == "YOUR_AUTHTOKEN_HERE" ]; then
    echo "❌ ERROR: NGROK_AUTHTOKEN is not set in the script. Please edit deploy_frontend.sh."
    exit 1
fi
echo "✅ Ngrok authtoken is set."

if [ -f "../FND/.venv/bin/activate" ]; then
    source ../FND/.venv/bin/activate
    echo "✅ Virtual environment activated."
else
    echo "❌ ERROR: Could not find '.venv/bin/activate'."
    exit 1
fi

# --- Cleanup Function ---
cleanup() {
    echo ""
    echo "--- 🛑 Shutting down UI services... ---"
    pkill -f "streamlit run Dashboard.py" && echo "✅ Streamlit app stopped." || echo "ℹ️ Streamlit app was not running."
    pkill -f "ui_tunnel_manager.py" && echo "✅ UI Ngrok tunnel stopped." || echo "ℹ️ UI tunnel was not running."
    rm -f ui_tunnel_manager.py # Clean up the temp script
    echo "--- UI is offline. ---"
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

# --- Create a Helper Script for Tunnel Management ---
cat << 'EOF' > ui_tunnel_manager.py
import os
import sys
from pyngrok import ngrok, conf
import time

print("--- UI Tunnel Manager Started ---")

NGROK_AUTHTOKEN = os.environ.get("NGROK_AUTHTOKEN")
if not NGROK_AUTHTOKEN:
    print("❌ ERROR: NGROK_AUTHTOKEN not found.")
    sys.exit(1)

conf.get_default().auth_token = NGROK_AUTHTOKEN
conf.get_default().region = "eu"  # Set region in config instead
streamlit_port = 8501

try:
    # Disconnect any old tunnels to be safe
    for tunnel in ngrok.get_tunnels():
        ngrok.disconnect(tunnel.public_url)

    # Use the updated syntax - pass options as dict
    public_url = ngrok.connect(
        streamlit_port,
        bind_tls=True  # This creates an HTTPS tunnel
    ).public_url
    
    print("===============================================================")
    print(f"✅ Streamlit UI is now public at: {public_url}")
    print("===============================================================")
    
    ngrok.get_ngrok_process().proc.wait()

except Exception as e:
    print(f"❌ An error occurred with ngrok: {e}")
    ngrok.kill()
    sys.exit(1)
EOF

# --- Start Services ---
echo ""
echo "--- 🚀 Launching Streamlit App and Tunnel ---"
echo "Starting Ngrok tunnel for UI..."
python ui_tunnel_manager.py &

sleep 5

echo "Starting Streamlit App..."
echo "Press Ctrl+C in this terminal to stop the UI and the tunnel."
echo "---------------------------------------------------------"
streamlit run Dashboard.py