#!/bin/bash

unset NGROK_AUTHTOKEN
export NGROK_AUTHTOKEN=""
export PYTHONPATH=$PYTHONPATH:.

VENV_PYTHON="/data/asca/FND/.venv/bin/python"

echo "--- 🚀 Starting Backend in OFFLINE Mode ---"


echo "---1  Starting Watcher ---"
$VENV_PYTHON src/workers/watcher.py > logs/watcher.log 2>&1 &
WATCHER_PID=$!
echo "Watcher started (PID: $WATCHER_PID)"


echo "--- Starting Main Worker ---"
$VENV_PYTHON src/workers/main_worker.py > logs/worker.log 2>&1 &
WORKER_PID=$!
echo "Main Worker started (PID: $WORKER_PID)"

echo "--- Starting API Server (Localhost Only) ---"
$VENV_PYTHON src/api/main.py > logs/api.log 2>&1 &
API_PID=$!
echo "API Server started (PID: $API_PID)"
echo "API is available at: http://localhost:8000"

echo "--- All Backend Services Running ---"
echo "Press [CTRL+C] to stop all services."

trap "echo 'Stopping services...'; kill $WATCHER_PID $WORKER_PID $API_PID; exit" SIGINT

echo "--- Tailing logs (Press Ctrl+C to stop) ---"
tail -f logs/api.log logs/watcher.log logs/worker.log
