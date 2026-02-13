#!/bin/bash

# ==============================================================================
#           Agentic Framework Backend Deployment Script
# ==============================================================================
# This script starts the backend services (Watcher, Worker, API) and
# exposes the API publicly using an Ngrok tunnel.
# ==============================================================================

set -e

# --- Configuration ---
NGROK_AUTHTOKEN="348sF0eAlt020Eh3jSH4FHeUckj_3UAbKeFyGTrCfoad4wDGv"
LOG_DIR="agentic_workspace/.system/logs"
STARTUP_WAIT=5  # seconds to wait for worker/watcher to initialize

# --- Preamble and Checks ---
echo "==============================================="
echo " Starting Backend for Streamlit Cloud Deployment"
echo "==============================================="

# Validate ngrok token
if [ -z "$NGROK_AUTHTOKEN" ] || [ "$NGROK_AUTHTOKEN" == "YOUR_AUTHTOKEN_HERE" ]; then
    echo "❌ ERROR: NGROK_AUTHTOKEN is not set properly in the script."
    exit 1
fi
echo "✅ Ngrok authtoken is set."
export NGROK_AUTHTOKEN

# Activate virtual environment
if [ -f "../FND/.venv/bin/activate" ]; then
    source ../FND/.venv/bin/activate
    echo "✅ Virtual environment activated."
else
    echo "❌ ERROR: Could not find '.venv/bin/activate'."
    exit 1
fi

# Create log directory
mkdir -p "$LOG_DIR"
echo "✅ Log directory created: $LOG_DIR"

# --- Cleanup Function ---
cleanup() {
    echo ""
    echo "--- 🛑 Shutting down backend services... ---"
    
    # Kill API and ngrok first
    if pkill -f "src.api.main"; then
        echo "✅ API Server & Ngrok Tunnel stopped."
    else
        echo "ℹ️ API Server was not running."
    fi
    
    # Kill worker
    if pkill -f "src.workers.main_worker"; then
        echo "✅ Worker stopped."
    else
        echo "ℹ️ Worker was not running."
    fi
    
    # Kill watcher
    if pkill -f "src.workers.watcher"; then
        echo "✅ Watcher stopped."
    else
        echo "ℹ️ Watcher was not running."
    fi
    
    echo "--- Backend is offline. ---"
    exit 0
}

# Set up signal handling
trap cleanup SIGINT SIGTERM EXIT

# --- Start Background Services in Order ---
echo ""
echo "--- 🚀 Step 1: Launching Watcher ---"
python -m src.workers.watcher > "$LOG_DIR/watcher.log" 2>&1 &
WATCHER_PID=$!
echo "✅ Watcher started (PID: $WATCHER_PID)"

echo ""
echo "--- 🚀 Step 2: Launching Worker ---"
python -m src.workers.main_worker > "$LOG_DIR/worker.log" 2>&1 &
WORKER_PID=$!
echo "✅ Worker started (PID: $WORKER_PID)"

# Wait for services to initialize
echo ""
echo "⏳ Waiting ${STARTUP_WAIT} seconds for Worker and Watcher to initialize..."
sleep $STARTUP_WAIT

# Check if processes are still running
if ! kill -0 $WATCHER_PID 2>/dev/null; then
    echo "❌ ERROR: Watcher process died. Check logs at $LOG_DIR/watcher.log"
    exit 1
fi

if ! kill -0 $WORKER_PID 2>/dev/null; then
    echo "❌ ERROR: Worker process died. Check logs at $LOG_DIR/worker.log"
    exit 1
fi

echo "✅ Worker and Watcher are running successfully"

# --- Start API Server with Ngrok ---
echo ""
echo "--- 🌍 Step 3: Launching API Server with Ngrok Tunnel ---"
echo "----------------------------------------------------"
echo "Press Ctrl+C in this terminal to stop all services."
echo "----------------------------------------------------"
echo ""

# Run API in foreground to see logs and ngrok URL
python -m src.api.main

# Note: The script will stay here until the API is terminated
# The trap will handle cleanup when Ctrl+C is pressed