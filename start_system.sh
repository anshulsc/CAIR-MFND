#!/bin/bash

set -e

echo "========================================"
echo " Starting Agentic Framework System"
echo "========================================"

if [ -z "$VIRTUAL_ENV" ]; then
    echo "❌ ERROR: No Python virtual environment is activated."
    echo "Please activate your virtual environment before running this script."
    echo "For example: source .venv/bin/activate"
    exit 1
fi
echo "✅ Virtual environment check passed."


LOG_DIR="agentic_workspace/.system/logs"
mkdir -p $LOG_DIR
echo "✅ Log directory is ready at '$LOG_DIR'."


cleanup() {
    echo "" 
    echo "--- 🛑 Shutting down all services... ---"
    pkill -f "src.workers.watcher" && echo "✅ Watcher stopped." || echo "ℹ️ Watcher was not running."
    pkill -f "src.workers.main_worker" && echo "✅ Worker stopped." || echo "ℹ️ Worker was not running."
    pkill -f "src.api.main" && echo "✅ API Server stopped." || echo "ℹ️ API Server was not running."
    
    echo "--- System is offline. ---"
    exit 0
}

# Set the trap. This tells the script to run the 'cleanup' function on exit.
trap cleanup SIGINT SIGTERM EXIT


echo ""
echo "--- 🚀 Launching background services ---"
echo "Logs for each service will be printed to the terminal and saved to '$LOG_DIR'."


echo ""
echo "--- 🖥️  Launching Main Worker ---"
echo "You can now access the dashboard in your browser."
echo "Press Ctrl+C in this terminal to stop the entire system."
echo "-------------------------------------------"
echo "Starting Watcher..."
python -m src.workers.watcher 2>&1 | tee "$LOG_DIR/watcher.log" &

# Start the Main Worker in the background
echo ""
echo "--- 🖥️  Launching Main Worker ---"
echo "You can now access the dashboard in your browser."
echo "Press Ctrl+C in this terminal to stop the entire system."
echo "-------------------------------------------"
echo "Starting Worker..."
python -m src.workers.main_worker 2>&1 | tee "$LOG_DIR/worker.log" &

# Start the FastAPI server in the background
echo "Starting API Server on http://0.0.0.0:8000..."
python -m src.api.main 2>&1 | tee "$LOG_DIR/api.log" &

# Give the backend services a moment to initialize
sleep 5

# --- Start Frontend Service (Foreground) ---
echo ""
echo "--- 🖥️  Launching Streamlit Frontend ---"
echo "You can now access the dashboard in your browser."
echo "Press Ctrl+C in this terminal to stop the entire system."
echo "-------------------------------------------"


streamlit run Dashboard.py


wait