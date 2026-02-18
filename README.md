# 🛡️ FND— Agentic Fake News Detection Framework


**Author**: [Anshul Singh](https://anshulsc.github.io)

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Technology Stack](#technology-stack)
- [Getting Started](#getting-started)
- [Deployment Modes](#deployment-modes)
- [Documentation](#documentation)
- [Directory Structure](#directory-structure)

---

## Overview

FND Mini is a sophisticated, multi-modal agentic framework for automated fake news detection. It combines:

- **Gemma 3 (12B)** via vLLM for multi-stage agentic reasoning
- **FraudNet** — a custom deep learning classifier for binary fake/true prediction
- **ChromaDB** vector search for evidence retrieval
- **LangGraph** to orchestrate agents in a stateful, debuggable graph
- **6 Indian fact-check scrapers** for live evidence collection
- **Brave Search API** for online evidence discovery

The entire pipeline is fully automated: submit a query (image + caption), and the system gathers evidence, runs multi-modal AI analysis, and generates a professional PDF report — all monitored through an interactive Streamlit dashboard with user authentication.

---

## Key Features

| Feature                      | Description                                                                                                                       |
| ---------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| **Offline Query Mode**       | Submit image + caption queries; evidence is retrieved from a local ChromaDB vector database                                       |
| **Online Query Mode**        | The system searches the web via Brave Search API, downloads new evidence, indexes it, then runs the analysis                      |
| **Multi-Agent LLM Analysis** | Image–Text consistency, Image–Image similarity, Text–Text factual alignment — all fused in a final reasoning stage                |
| **FraudNet Neural Network**  | A CLIP-based deep learning model that provides an independent fake/true classification with confidence scores                     |
| **Indian News Scrapers**     | 6 live scrapers (Factly, BoomLive, FactCrescendo, NewsChecker, NewsMobile, VishvasNews) to build and expand the evidence database |
| **PDF Report Generation**    | Professional, multi-page PDF reports with evidence, reasoning chains, and verdicts                                                |
| **User Authentication**      | Multi-user support with login/registration                                                                                        |
| **Highlight News Carousel**  | Dashboard carousel showcasing recently analyzed news stories                                                                      |
| **Trash & Restore**          | Soft-delete queries with the ability to restore or permanently delete                                                             |
| **Flexible Deployment**      | Local (offline), or publicly shared via Ngrok tunnels (online)                                                                    |

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    STREAMLIT FRONTEND (Dashboard)                │
│                                                                 │
│  Dashboard ─ Offline Query ─ Online Query ─ FraudNet ─ Indian  │
│  Query Details ─ FraudNet Details ─ Trash ─ Settings            │
└───────────────────────────┬─────────────────────────────────────┘
                            │  REST API calls
┌───────────────────────────▼─────────────────────────────────────┐
│                    FASTAPI BACKEND (API Server)                  │
│                                                                 │
│  Query CRUD ─ Evidence Extraction ─ Scraper Endpoints ─ File    │
│  Serving ─ Investigate & Analyze ─ Data Explorer                │
└──────┬──────────────┬───────────────────────┬───────────────────┘
       │              │                       │
       ▼              ▼                       ▼
┌────────────┐ ┌─────────────┐ ┌──────────────────────────────────┐
│  Watcher   │ │ Main Worker │ │         Status Manager            │
│ (Watchdog) │ │ (Job Queue) │ │         (SQLite DB)               │
└──────┬─────┘ └──────┬──────┘ └──────────────────────────────────┘
       │              │
       │              ├── Evidence Extraction (ChromaDB + CLIP)
       │              ├── Model Inference (vLLM + LangGraph + FraudNet)
       │              └── PDF Generation (FPDF2)
       │
       └── Monitors 1_queries/ for new submissions
```

For a detailed architecture breakdown, see **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**.

---

## Technology Stack

| Layer                        | Technology                     |
| ---------------------------- | ------------------------------ |
| **Frontend**                 | Streamlit (multi-page app)     |
| **Backend API**              | FastAPI + Uvicorn              |
| **LLM Inference**            | vLLM with Gemma 3 (12B)        |
| **Agent Orchestration**      | LangGraph (StateGraph)         |
| **Neural Network**           | PyTorch (FraudNet classifier)  |
| **Feature Extraction**       | CLIP (ViT-L/14 via LAVIS)      |
| **Vector Database**          | ChromaDB                       |
| **Evidence Search (Online)** | Brave Search API               |
| **Web Scraping**             | BeautifulSoup4 / Requests      |
| **PDF Generation**           | FPDF2 + Markdown2              |
| **File Monitoring**          | Watchdog                       |
| **Authentication**           | Custom JSON-based user manager |
| **Tunnel/Sharing**           | Ngrok (pyngrok)                |

---

## Getting Started

### Prerequisites

- Python 3.10+
- NVIDIA GPU with CUDA (required for vLLM and FraudNet)
- A valid Brave Search API key (for online mode)
- `wget` (for downloading fonts)

### Quick Start

```bash
# 1. Clone and enter the project
git clone <your-repo-url>
cd FND_mini

# 2. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install salesforce-lavis==1.0.2
pip install -r requirements.txt

# 4. Download fonts for PDF generation
mkdir -p assets/fonts
wget -P assets/fonts/ https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans.ttf
wget -P assets/fonts/ https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans-Bold.ttf

# 5. Populate the evidence database
# Place news article folders (each with image + caption.txt) into:
#   agentic_workspace/2_evidence_database/

# 6. Build the initial search index
python -m tools.build_index

# 7. Start the system
./start_system.sh
```

For detailed setup, deployment, and configuration instructions, see **[docs/SETUP.md](docs/SETUP.md)**.

---

## Deployment Modes

FND Mini supports **4 deployment configurations**:

| Script                       | Mode                   | Description                                                  |
| ---------------------------- | ---------------------- | ------------------------------------------------------------ |
| `start_system.sh`            | Local (all-in-one)     | Starts watcher, worker, API, and Streamlit frontend together |
| `deploy_backend_offline.sh`  | Backend only (local)   | Runs backend services on localhost without tunnels           |
| `deploy_backend.sh`          | Backend only (public)  | Runs backend + exposes API via Ngrok tunnel                  |
| `deploy_frontend_offline.sh` | Frontend only (local)  | Runs Streamlit connecting to localhost API                   |
| `deploy_frontend.sh`         | Frontend only (public) | Runs Streamlit + exposes UI via Ngrok tunnel                 |

**Typical remote deployment**: Run `deploy_backend.sh` on the GPU server, copy the Ngrok URL, then run `deploy_frontend.sh` on a separate machine with `API_URL` set to the backend's public URL.

For details, see **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)**.

---

## Documentation

| Document                                  | Description                                                      |
| ----------------------------------------- | ---------------------------------------------------------------- |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md)   | Detailed system architecture, component breakdown, and data flow |
| [WORKFLOW.md](docs/WORKFLOW.md)           | Step-by-step pipeline walkthrough (offline & online modes)       |
| [API_REFERENCE.md](docs/API_REFERENCE.md) | Complete REST API endpoint reference                             |
| [SETUP.md](docs/SETUP.md)                 | Installation, configuration, and deployment guide                |

---

## Directory Structure

```
FND_mini/
├── Dashboard.py                # Main Streamlit dashboard (entry point)
├── pages/                      # Streamlit multi-page app
│   ├── 1_Offline Query Mode.py #   Submit query for offline analysis
│   ├── 2_Query_Details.py      #   Detailed analysis results viewer
│   ├── 3_Online Query Mode.py  #   Investigate & analyze with web search
│   ├── 4_FraudNet.py           #   FraudNet prediction dashboard
│   ├── 5_FraudNetDetails.py    #   Per-query FraudNet detail view
│   ├── 6_Trash.py              #   Trash management (restore / delete)
│   ├── 7_Settings.py           #   System settings & log viewer
│   └── 8_Indian Data.py        #   Indian news database + live scrapers
│
├── src/                        # Core Python source code
│   ├── config.py               #   Central configuration (paths, model paths, API settings)
│   ├── auth.py                 #   User authentication manager
│   ├── workflow.py             #   LangGraph workflow definition
│   ├── fraudnet.py             #   FraudNet model loading & inference
│   ├── fraudnet_backbone.py    #   FraudNet neural network architecture
│   ├── fraudnet_utils.py       #   CLIP feature extraction utilities
│   ├── logger_config.py        #   Logging configuration
│   ├── agents/                 #   AI agent module
│   │   ├── agent_class.py      #     MultimodalClaimVerifier (2-stage LLM pipeline)
│   │   ├── prompts.py          #     All LLM prompt templates
│   │   └── utils.py            #     Model loading, batch inference, scoring utilities
│   ├── api/
│   │   └── main.py             #     FastAPI server with all REST endpoints
│   ├── database/
│   │   └── status_manager.py   #     SQLite-based query state tracking
│   ├── modules/
│   │   ├── evidence_searcher.py       # ChromaDB vector search (offline evidence)
│   │   ├── embedding_utils.py         # CLIP embedding generation
│   │   ├── online_evidence_extractor.py # Brave Search + download + index pipeline
│   │   ├── inference_pipeline.py      # Model initialization + LangGraph execution
│   │   ├── pdf_generator.py           # Professional PDF report renderer
│   │   ├── boomlive_scraper.py        # BoomLive fact-check scraper
│   │   ├── factly_scraper.py          # Factly.in scraper
│   │   ├── factcrescendo_scraper.py   # FactCrescendo scraper
│   │   ├── newschecker_sracper.py     # NewsChecker scraper
│   │   ├── newsmobile_scraper.py      # NewsMobile scraper
│   │   └── vishwanews_scraper.py      # VishvasNews scraper
│   └── workers/
│       ├── watcher.py          #     Monitors 1_queries/ for new submissions
│       └── main_worker.py      #     Job queue processor (evidence → inference → PDF)
│
├── tools/                      # Utility scripts
│   ├── build_index.py          #   Build/rebuild ChromaDB vector index
│   └── add_query.py            #   CLI tool to add queries
│
├── scripts/
│   └── backfill_verdicts.py    #   Backfill verdict column for existing queries
│
├── agentic_workspace/          # All runtime data
│   ├── .system/                #   System internals (DB, logs, job queue, vector DB)
│   ├── 1_queries/              #   Input: query folders (per-user subdirectories)
│   ├── 2_evidence_database/    #   Input: evidence articles (image + caption.txt)
│   ├── 3_processed_for_model/  #   Staging: prepared data for model inference
│   ├── 4_results/              #   Output: generated PDF reports
│   ├── 5_trash/                #   Soft-deleted queries
│   ├── 6_fakeNewsData/         #   Scraped Indian fake news data
│   └── 7_highlight_news/       #   Curated highlight news for dashboard carousel
│
├── assets/fonts/               # DejaVu fonts for PDF generation
├── logs/                       # Runtime logs (watcher, worker, API)
├── docs/                       # Project documentation
│
├── start_system.sh             # All-in-one local launcher
├── deploy_backend.sh           # Backend + Ngrok tunnel
├── deploy_backend_offline.sh   # Backend (localhost only)
├── deploy_frontend.sh          # Frontend + Ngrok tunnel
├── deploy_frontend_offline.sh  # Frontend (localhost only)
├── requirements.txt            # Python dependencies
└── tests/                      # Test suite
```
