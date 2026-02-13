# System Architecture

This document provides a detailed breakdown of the FND Mini system architecture, covering every layer from the user-facing frontend to the deep learning models.

---

## High-Level Overview

FND Mini follows a **service-oriented, file-driven architecture**. Instead of relying on heavy infrastructure like Redis or RabbitMQ, it uses a lightweight file-based job queue monitored by a background worker. This design keeps the system transparent, easy to debug, and simple to deploy.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              USER LAYER                                 │
│                                                                         │
│   Browser ──► Streamlit Dashboard (8 pages) ──► FastAPI REST API        │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │
┌──────────────────────────────────▼──────────────────────────────────────┐
│                          ORCHESTRATION LAYER                            │
│                                                                         │
│   File Watcher (Watchdog)        Status Manager (SQLite)                │
│   Main Worker (Job Processor)    User Auth Manager (JSON)               │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │
┌──────────────────────────────────▼──────────────────────────────────────┐
│                           INTELLIGENCE LAYER                            │
│                                                                         │
│   Evidence Searcher (ChromaDB)   Online Evidence Extractor (Brave API)  │
│   MultimodalClaimVerifier (vLLM) FraudNet Classifier (PyTorch)          │
│   LangGraph Workflow Engine      6 Indian Fact-Check Scrapers           │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │
┌──────────────────────────────────▼──────────────────────────────────────┐
│                            OUTPUT LAYER                                 │
│                                                                         │
│   PDF Report Generator (FPDF2)   Inference Results (JSON)               │
│   Verdict Storage (SQLite)       Evidence Metadata (JSON)               │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Component Breakdown

### 1. Frontend Layer — Streamlit Dashboard

The frontend is a **multi-page Streamlit application** with user authentication. Each page communicates with the backend via REST API calls.

| Page                   | File                            | Purpose                                                                         |
| ---------------------- | ------------------------------- | ------------------------------------------------------------------------------- |
| **Dashboard**          | `Dashboard.py`                  | Main overview — query list, status monitoring, highlight news carousel, search  |
| **Offline Query Mode** | `pages/1_Offline Query Mode.py` | Submit new queries (image + caption, or zipped folder)                          |
| **Query Details**      | `pages/2_Query_Details.py`      | Full analysis breakdown — verdict banner, media display, tabbed reasoning views |
| **Online Query Mode**  | `pages/3_Online Query Mode.py`  | Investigate & Analyze — web search for evidence, then auto-submit for analysis  |
| **FraudNet Dashboard** | `pages/4_FraudNet.py`           | List all FraudNet predictions with confidence bars                              |
| **FraudNet Details**   | `pages/5_FraudNetDetails.py`    | Per-query FraudNet detail view with media comparison                            |
| **Trash**              | `pages/6_Trash.py`              | Manage deleted queries — restore or permanently delete                          |
| **Settings**           | `pages/7_Settings.py`           | Re-index evidence database, view system logs                                    |
| **Indian Data**        | `pages/8_Indian Data.py`        | Browse scraped fake news data, trigger live scrapers                            |

**Authentication**: The `Dashboard.py` includes a login/registration gate. All pages check `st.session_state.logged_in` before rendering content. Users are stored in `.system/users.json` via `src/auth.py`.

---

### 2. Backend API — FastAPI

The API server (`src/api/main.py`) is the central communication layer between the frontend and the backend processing modules.

**Key endpoint groups:**

| Group                   | Endpoints                                                                                                                                                       | Description                               |
| ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------- |
| **Query Management**    | `GET /queries`, `GET /details/{id}`, `POST /add_query_manual`, `POST /add_query_folder`, `POST /rerun/{id}`                                                     | CRUD operations for queries               |
| **Trash Management**    | `POST /trash/{id}`, `POST /restore/{id}`, `DELETE /delete_permanent/{id}`                                                                                       | Soft-delete, restore, permanent delete    |
| **Evidence Extraction** | `POST /extract_evidence_online`, `POST /investigate_and_analyze`                                                                                                | Online evidence search + query submission |
| **Scrapers**            | `POST /scrape_factly`, `POST /scrape_boomlive`, `POST /scrape_factcrescendo`, `POST /scrape_newschecker`, `POST /scrape_newsmobile`, `POST /scrape_vishvasnews` | Live fact-check website scrapers          |
| **Data Explorer**       | `GET /data_explorer_samples`, `GET /highlight_news`                                                                                                             | Browse collected fake news datasets       |
| **File Serving**        | `GET /serve_file`                                                                                                                                               | Serve images/files to the frontend        |

The API uses **CORS middleware** to allow cross-origin requests from the Streamlit frontend, which is critical for the split backend/frontend deployment mode.

---

### 3. Orchestration Layer

#### File System Watcher (`src/workers/watcher.py`)

- Monitors `agentic_workspace/1_queries/` using the **Watchdog** library
- When a new directory is detected, it:
  1. Creates a `.job` file in `.system/job_queue/`
  2. Registers the query in the SQLite database via `StatusManager`

#### Main Worker (`src/workers/main_worker.py`)

The worker is a **long-running process** that continuously polls `.system/job_queue/` for `.job` files. When a job is found, it executes a 3-stage pipeline:

1. **Evidence Extraction** → `evidence_searcher.find_top_evidence()`
2. **Model Inference** → `inference_pipeline.run_full_inference()`
3. **PDF Generation** → `pdf_generator.create_report_pdf()`

On completion, the `.job` file is moved to `job_completed/` or `job_failed/`.

#### Status Manager (`src/database/status_manager.py`)

An SQLite-based state tracker. Every query has:

- `status`: pending → processing → completed / failed / trashed
- `stage_statuses`: JSON tracking individual stage progress
- `verdict`: extracted classification (Fake / True / Uncertain)
- `result_path`: path to the generated PDF
- `username`: owner of the query

#### User Authentication (`src/auth.py`)

A lightweight `UserManager` class using a JSON file (`users.json`) for credential storage. Passwords are hashed with SHA-256. Provides:

- `register_user()` — create new accounts
- `authenticate_user()` — validate credentials
- `get_user_query_dir()` — per-user query directories

---

### 4. Intelligence Layer

#### Evidence Searcher (`src/modules/evidence_searcher.py`)

- Uses **ChromaDB** as a persistent vector store
- Generates CLIP embeddings for query image and caption
- Performs hybrid search: queries with both image and text embeddings
- Returns top-K results ranked by cosine similarity
- Runs in an **isolated subprocess** to prevent CUDA context conflicts

#### Online Evidence Extractor (`src/modules/online_evidence_extractor.py`)

- Calls the **Brave Search API** with the query caption
- Filters out social media and low-quality domains
- Deduplicates results using `SequenceMatcher`
- Downloads images and captions into `2_evidence_database/`
- Indexes new evidence into ChromaDB immediately

#### MultimodalClaimVerifier (`src/agents/agent_class.py`)

The core LLM-powered analysis engine, running **Gemma 3 (12B)** via vLLM.

**Stage 1 — Independent Analysis:**
| Agent | Input | Output |
|---|---|---|
| Image–Text Unified | Query image + caption | Sentiment, entity, event consistency analysis |
| Image–Image Unified | Query image + evidence image | Visual similarity analysis across multiple dimensions |
| Text–Text (N prompts) | Evidence caption vs. query claim | Support/negate verdict per evidence item |

**Stage 2 — Collaborative Reasoning:**

- Computes weighted support scores from Text–Text results
- Extracts rationales and generates a rationale summary
- Runs a final unified prompt that synthesizes all analyses into a single verdict

#### FraudNet (`src/fraudnet.py`, `src/fraudnet_backbone.py`, `src/fraudnet_utils.py`)

An independent neural network classifier:

- **Feature extraction**: Uses CLIP ViT-L/14 (via LAVIS) to extract 768-dim embeddings for query image, caption, and evidence
- **Architecture**: Custom `Classifier` network that processes image features, text features, domain vectors, and evidence features
- **Inference**: Outputs a binary prediction (Fake/True) with a confidence score via sigmoid

#### LangGraph Workflow (`src/workflow.py`)

Orchestrates the analysis pipeline as a **directed graph**:

```
[stage_1] → [stage_2] → [fraudnet]
```

- `stage_1`: Runs all independent LLM agents (Image–Text, Image–Image, Text–Text)
- `stage_2`: Runs collaborative scoring and final reasoning
- `fraudnet`: Runs the FraudNet neural network inference

The graph is compiled once and invoked per query with a state dictionary containing all inputs and model references.

#### Indian Fact-Check Scrapers

Six specialized web scrapers target Indian fact-checking websites:

| Scraper       | Source            | File                       |
| ------------- | ----------------- | -------------------------- |
| Factly        | factly.in         | `factly_scraper.py`        |
| BoomLive      | boomlive.in       | `boomlive_scraper.py`      |
| FactCrescendo | factcrescendo.com | `factcrescendo_scraper.py` |
| NewsChecker   | newschecker.in    | `newschecker_sracper.py`   |
| NewsMobile    | newsmobile.in     | `newsmobile_scraper.py`    |
| VishvasNews   | vishvasnews.com   | `vishwanews_scraper.py`    |

Each scraper:

1. Fetches the latest N articles from the source
2. Extracts image, caption, timestamp, and source URL
3. Saves new articles to `6_fakeNewsData/`
4. Indexes them into ChromaDB

---

### 5. Output Layer

#### PDF Report Generator (`src/modules/pdf_generator.py`)

A sophisticated document renderer built on **FPDF2**:

- Custom header/footer with query ID and page numbers
- Summary page with verdict, query media, and evidence media
- Dedicated pages for each analysis dimension (Image–Text, Image–Image, Text–Text)
- Markdown parsing with conditional styling (e.g., "Mismatch" in red, "Aligned" in green)
- DejaVu Sans fonts for proper Unicode rendering

Reports are saved to `agentic_workspace/4_results/`.

---

## Data Flow Diagram

```
                    ┌──────────────┐
                    │  User Input  │
                    │ (Image+Text) │
                    └──────┬───────┘
                           │
              ┌────────────▼────────────┐
              │    1_queries/{user}/    │
              │    {query_id}/          │
              │    ├── image.jpg        │
              │    └── query_cap.txt    │
              └────────────┬────────────┘
                           │
                    Watcher detects
                           │
              ┌────────────▼────────────┐
              │   .system/job_queue/    │
              │   {query_id}.job        │
              └────────────┬────────────┘
                           │
                    Worker picks up
                           │
         ┌─────────────────▼──────────────────┐
         │        Evidence Extraction          │
         │  ChromaDB → Top-K similar items     │
         └─────────────────┬──────────────────┘
                           │
         ┌─────────────────▼──────────────────┐
         │   3_processed_for_model/{user}/    │
         │   {query_id}/                      │
         │   ├── image.jpg                    │
         │   ├── query_cap.txt                │
         │   ├── best_evidence.jpg            │
         │   └── evidence_metadata.json       │
         └─────────────────┬──────────────────┘
                           │
         ┌─────────────────▼──────────────────┐
         │        LangGraph Inference          │
         │  Stage 1 → Stage 2 → FraudNet      │
         │        ↓                            │
         │  inference_results.json             │
         └─────────────────┬──────────────────┘
                           │
         ┌─────────────────▼──────────────────┐
         │        PDF Report Generation        │
         │  4_results/{query_id}/              │
         │  └── analysis_report.pdf            │
         └─────────────────────────────────────┘
```

---

## Configuration

All paths, model locations, and settings are centralized in `src/config.py`:

| Setting                     | Description                                     |
| --------------------------- | ----------------------------------------------- |
| `WORKSPACE_DIR`             | Root of the data workspace                      |
| `VLLM_MODEL_PATH`           | Path to the Gemma 3 model snapshot              |
| `FRAUDNET_MODEL_PATH`       | Path to the FraudNet checkpoint                 |
| `DOMAIN_VECTOR_PATH`        | Path to the FraudNet domain vectors             |
| `API_HOST` / `API_PORT`     | API server binding (default: `0.0.0.0:8000`)    |
| `WORKER_SLEEP_INTERVAL`     | Seconds between job queue polls (default: 5)    |
| `BRAVE_API_KEY`             | API key for Brave Search                        |
| `AGENT_SEARCH_RESULT_COUNT` | Number of search results to fetch (default: 15) |

All workspace directories are **auto-created** on startup if they don't exist.
