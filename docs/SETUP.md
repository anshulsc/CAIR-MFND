# Setup & Deployment Guide

Complete guide for installing, configuring, and deploying the FND Mini system.

---

## Prerequisites

| Requirement       | Details                                                                                                        |
| ----------------- | -------------------------------------------------------------------------------------------------------------- |
| **Python**        | 3.10 or higher                                                                                                 |
| **NVIDIA GPU**    | CUDA-capable GPU required for vLLM (Gemma 3) and FraudNet                                                      |
| **CUDA**          | CUDA toolkit installed and configured                                                                          |
| **Disk Space**    | ~30GB minimum (model weights + evidence database)                                                              |
| **RAM**           | 32GB+ recommended                                                                                              |
| **Brave API Key** | Required for Online Query Mode (free tier available at [brave.com/search/api/](https://brave.com/search/api/)) |

---

## Installation

### Step 1: Clone the Repository

```bash
git clone <your-repo-url>
cd FND_mini
```

### Step 2: Create Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3: Install Python Dependencies

The project requires the following major packages (install via pip):

```bash
pip install fastapi uvicorn streamlit chromadb langgraph
pip install vllm torch torchvision
pip install fpdf2 markdown2 pillow
pip install watchdog pyngrok requests
pip install pydantic regex beautifulsoup4
pip install streamlit-autorefresh
pip install salesforce-lavis
```

> **Note**: The `requirements.txt` in the repo contains only frontend dependencies (`streamlit`, `pandas`, `requests`). For the full system, install the packages listed above.

### Step 4: Download Fonts

The PDF generator requires DejaVu Sans fonts for proper Unicode rendering:

```bash
mkdir -p assets/fonts
wget -P assets/fonts/ https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans.ttf
wget -P assets/fonts/ https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans-Bold.ttf
```

### Step 5: Model Setup

You need to have the following models accessible on disk:

| Model                   | Purpose                                                    | Config Key                               |
| ----------------------- | ---------------------------------------------------------- | ---------------------------------------- |
| **Gemma 3 (12B)**       | LLM inference via vLLM                                     | `VLLM_MODEL_PATH` in `src/config.py`     |
| **FraudNet Checkpoint** | Neural network classifier                                  | `FRAUDNET_MODEL_PATH` in `src/config.py` |
| **Domain Vector JSON**  | FraudNet domain embeddings                                 | `DOMAIN_VECTOR_PATH` in `src/config.py`  |
| **CLIP ViT-L/14**       | Feature extraction (auto-downloaded by LAVIS on first run) | N/A                                      |

Update the paths in `src/config.py`:

```python
VLLM_MODEL_PATH = "/path/to/gemma-3-12b-it/snapshot"
FRAUDNET_MODEL_PATH = "/path/to/fraudnet_checkpoint.pth.tar"
DOMAIN_VECTOR_PATH = "/path/to/domain_vector_VITL14.json"
```

### Step 6: Configure API Keys

Edit `src/config.py` to set your Brave Search API key:

```python
BRAVE_API_KEY = "your-brave-api-key-here"
```

### Step 7: Populate the Evidence Database

Place fact-checked news article folders into `agentic_workspace/2_evidence_database/`. Each folder should contain:

- An image file (any common format)
- A `caption.txt` file with the article headline/caption

### Step 8: Build the Search Index

```bash
python -m tools.build_index
```

This processes all evidence items, generates CLIP embeddings, and stores them in ChromaDB. Run this once at setup, and again (from the Settings page) whenever you add new evidence.

---

## Environment Variables

| Variable          | Default                 | Description                                   |
| ----------------- | ----------------------- | --------------------------------------------- |
| `API_URL`         | `http://localhost:8000` | Backend API URL (used by Streamlit frontend)  |
| `NGROK_AUTHTOKEN` | (set in deploy scripts) | Ngrok authentication token for public tunnels |

---

## Deployment Options

### Option 1: Local Development (All-in-One)

The simplest way to run the entire system on a single machine:

```bash
# Activate your virtual environment
source .venv/bin/activate

# Start everything
chmod +x start_system.sh
./start_system.sh
```

This script:

1. Validates that a virtual environment is active
2. Starts the **Watcher** in background (monitors for new queries)
3. Starts the **Worker** in background (processes queries)
4. Starts the **API Server** in background (FastAPI on port 8000)
5. Launches **Streamlit** in foreground (port 8501)
6. Sets up signal handlers for clean shutdown on `Ctrl+C`

**Access**: Open `http://localhost:8501` in your browser.

---

### Option 2: Split Deployment (Backend + Frontend on Same Machine)

Useful for running backend and frontend as independent processes:

**Terminal 1 — Backend:**

```bash
chmod +x deploy_backend_offline.sh
./deploy_backend_offline.sh
```

**Terminal 2 — Frontend:**

```bash
chmod +x deploy_frontend_offline.sh
./deploy_frontend_offline.sh
```

---

### Option 3: Remote Deployment via Ngrok

Run the backend on a GPU server and the frontend anywhere. Both are exposed publicly via Ngrok tunnels.

**On the GPU Server — Backend:**

```bash
# Edit deploy_backend.sh to set your NGROK_AUTHTOKEN
chmod +x deploy_backend.sh
./deploy_backend.sh
```

The script will:

1. Start watcher, worker, and API server
2. Run Ngrok tunnel for the API (port 8000)
3. Print the public URL (e.g., `https://xxxx.ngrok.io`)

**On Any Machine — Frontend:**

```bash
# Set the API URL to the backend's public URL
export API_URL="https://xxxx.ngrok.io"

# Edit deploy_frontend.sh to set your NGROK_AUTHTOKEN
chmod +x deploy_frontend.sh
./deploy_frontend.sh
```

> **Important**: The backend and frontend use **different** Ngrok authtokens to create separate tunnels. You may need a paid Ngrok plan for multiple simultaneous tunnels.

---

### Option 4: Remote Backend, Local Frontend

Run the GPU-heavy backend remotely, but access the frontend locally:

**On the GPU Server:**

```bash
./deploy_backend.sh
# Note the Ngrok URL
```

**On Your Local Machine:**

```bash
export API_URL="https://xxxx.ngrok.io"
./deploy_frontend_offline.sh
```

---

## User Management

### Creating Accounts

New users can register through the login page on the Streamlit Dashboard. Accounts are stored in `agentic_workspace/.system/users.json`.

### Per-User Isolation

Each user's queries are stored in separate directories:

- `1_queries/{username}/{query_id}/`
- `3_processed_for_model/{username}/{query_id}/`

The dashboard only shows queries belonging to the logged-in user.

---

## Maintenance

### Re-Indexing the Evidence Database

When you add new evidence articles to `2_evidence_database/`, rebuild the search index:

**Via Streamlit**: Go to **Settings** page → click **Re-Index Evidence Database**

**Via CLI**:

```bash
python -m tools.build_index
```

### Backfilling Verdicts

If you have existing completed queries that are missing verdict data in the database:

```bash
python scripts/backfill_verdicts.py
```

This reads `inference_results.json` for each completed query and extracts the verdict.

### Viewing Logs

- **Streamlit**: Settings page → select a log file to view
- **CLI**: Logs are stored in `agentic_workspace/.system/logs/` (or `logs/` for offline deploy scripts)
  - `watcher.log` — file system monitoring events
  - `worker.log` — job processing logs
  - `api.log` — API server access and error logs

### Stopping the System

- Press `Ctrl+C` in the terminal — the trap handler will clean up all background processes
- Or use `pkill -f "src.workers"` and `pkill -f "src.api"` to stop individual services

---

## Troubleshooting

| Issue                             | Cause                    | Solution                                                                                            |
| --------------------------------- | ------------------------ | --------------------------------------------------------------------------------------------------- |
| `database is locked`              | Concurrent SQLite writes | Set `timeout` in SQLite connections, enable WAL mode                                                |
| CUDA out of memory                | Model too large for GPU  | Reduce vLLM `max_num_seqs`, use tensor parallelism, or offload FraudNet to CPU (already configured) |
| Watcher not detecting files       | Filesystem event limits  | Increase `fs.inotify.max_user_watches` via `sysctl`                                                 |
| Evidence search returns nothing   | Empty vector database    | Run `python -m tools.build_index` to populate ChromaDB                                              |
| PDF missing fonts                 | Fonts not downloaded     | Run the `wget` commands from the setup instructions                                                 |
| Streamlit "Cannot connect to API" | API not running          | Start the backend before the frontend; check `API_URL` env variable                                 |
| Ngrok tunnel disconnects          | Free tier limits         | Upgrade Ngrok plan or use offline deployment mode                                                   |
