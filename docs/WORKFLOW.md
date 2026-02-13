# Pipeline Workflow

This document explains the step-by-step processing workflow for both **Offline** and **Online** query modes.

---

## Offline Query Mode

The offline mode uses only the local evidence database (ChromaDB) to analyze a query. No internet access is required.

### Step-by-Step Flow

```
User submits query ──► Watcher detects ──► Worker picks up job
         │                                         │
         │                                    ┌────▼─────┐
         │                                    │ Stage 1:  │
         │                                    │ Evidence  │
         │                                    │ Extraction│
         │                                    └────┬─────┘
         │                                         │
         │                                    ┌────▼─────┐
         │                                    │ Stage 2:  │
         │                                    │ Model     │
         │                                    │ Inference │
         │                                    └────┬─────┘
         │                                         │
         │                                    ┌────▼─────┐
         │                                    │ Stage 3:  │
         │                                    │ PDF Report│
         │                                    └────┬─────┘
         │                                         │
         └──── Dashboard shows "completed" ◄───────┘
```

---

### Stage 1: Query Detection & Evidence Extraction

**1.1 — Query Submission**

Users submit queries through one of three methods:

- **Streamlit UI (Offline Query Mode page)**: Upload image + type caption, or upload a `.zip` file
- **File system**: Place a folder containing an image file + `query_cap.txt` into `agentic_workspace/1_queries/{username}/`
- The API creates the query directory and stores the files

**1.2 — Watcher Detection**

The `watcher.py` service (using **Watchdog**) monitors `1_queries/`. Upon detecting a new folder:

1. Extracts the query ID and username from the directory path
2. Registers the query in the SQLite database with status `pending`
3. Creates a `.job` file in `.system/job_queue/` containing `{username}/{query_id}`

**1.3 — Evidence Extraction**

The `main_worker.py` picks up the `.job` file and starts processing:

1. Reads the query image and caption from `1_queries/{username}/{query_id}/`
2. Generates **CLIP embeddings** (ViT-L/14) for both the image and text
3. Queries the **ChromaDB** vector store with both embeddings
4. Retrieves the **top-K most similar** items (images and texts), ranked by cosine similarity
5. Creates a staging directory at `3_processed_for_model/{username}/{query_id}/`
6. Copies:
   - Original query image and caption
   - Best evidence image (renamed to `best_evidence.jpg`)
7. Saves `evidence_metadata.json` containing:
   - Query file paths
   - Full list of ranked evidence items (image/caption paths and similarity scores)

---

### Stage 2: Multimodal AI Inference

The worker calls `run_full_inference()`, which:

**2.1 — Model Initialization (Singleton)**

On first call, loads both models and keeps them in memory:

- **MultimodalClaimVerifier**: Loads Gemma 3 (12B) via vLLM with processor
- **FraudNet**: Loads the PyTorch classifier + domain vectors + CLIP feature extractor

**2.2 — LangGraph Workflow Execution**

The `build_langgraph()` function creates a 3-node directed graph:

```
[stage_1] ──► [stage_2] ──► [fraudnet]
```

**Node: `stage_1` — Independent Agent Analysis**

Runs multiple LLM prompts in a single batched inference call:

| Prompt                         | Images                       | Purpose                                                                             |
| ------------------------------ | ---------------------------- | ----------------------------------------------------------------------------------- |
| `get_qimg_qtxt_unified_prompt` | Query image                  | Analyzes sentiment, entity, and event consistency between the image and its caption |
| `get_img_img_unified_prompt`   | Query image + Evidence image | Compares visual similarity across sentiment, entities, and events                   |
| `get_response_txttxt` × N      | None                         | For each evidence text, determines if it supports or negates the query claim        |

All prompts are batched and processed in parallel by vLLM.

**Node: `stage_2` — Collaborative Reasoning**

1. **Weighted Support Scoring**: Analyzes all Text–Text responses, computing a weighted score for support vs. negation
2. **Rationale Summary**: Extracts rationales from individual Text–Text comparisons and generates a unified summary via LLM
3. **Final Unified Reasoning**: Feeds all prior analysis (Image–Text, Image–Image, claim verification string) into a final prompt that produces a `**Final Classification**: Fake/True` verdict

**Node: `fraudnet` — Neural Network Classification**

1. Extracts CLIP features for query image, caption, and evidence
2. Constructs `fraudnet_input` with:
   - `img_feat` (1, 768) — query image embedding
   - `text_feat` (1, 768) — query text embedding
   - `domain_vec` (1, 768) — domain-specific vector
   - `fake_evidence` (1, 20, 768) — combined evidence embeddings (10 image + 10 text, padded)
3. Runs forward pass → sigmoid → binary prediction with confidence

**2.3 — Results Storage**

The combined output from Stage 2 and FraudNet is saved as `inference_results.json`:

```json
{
  "stage2_outputs": {
    "img_txt_result": "...",
    "qimg_eimg_result": "...",
    "claim_verification_str": "The claim is FAKE with support score 0.23.",
    "final_response": "... **Final Classification**: Fake ...",
    "txt_txt_results": ["...", "..."],
    "txt_txt_rational_summary": ["..."]
  },
  "fraudnet_response": {
    "fraudnet_label": 1,
    "confidence": 0.87
  }
}
```

The worker also extracts the verdict from the LLM's final response using regex and stores it in the SQLite database.

---

### Stage 3: PDF Report Generation

The `pdf_generator.py` module creates a professional multi-page report:

1. **Summary Page**: Verdict banner, query image + caption, evidence image + caption
2. **Image–Text Analysis**: Full LLM reasoning about image-caption consistency
3. **Image–Image Analysis**: Visual comparison reasoning
4. **Text–Text Analysis**: Individual evidence comparisons + claim verification summary
5. **Font rendering**: DejaVu Sans for Unicode support
6. **Conditional highlighting**: "Mismatch" in red, "Aligned" in green

The PDF is saved to `4_results/` and the path is recorded in the database. The query status is updated to `completed`.

---

## Online Query Mode

The online mode extends the offline workflow by first **searching the web for additional evidence** before running the analysis.

### Step-by-Step Flow

```
User submits image + caption ──► API: /investigate_and_analyze
                                         │
                                    ┌────▼─────────────────┐
                                    │ Phase 1:              │
                                    │ Online Evidence       │
                                    │ Extraction            │
                                    │                       │
                                    │ Brave Search API      │
                                    │ → Filter results      │
                                    │ → Download images     │
                                    │ → Index into ChromaDB │
                                    └────┬─────────────────┘
                                         │
                                    ┌────▼─────────────────┐
                                    │ Phase 2:              │
                                    │ Submit as Offline     │
                                    │ Query (same pipeline) │
                                    └────┬─────────────────┘
                                         │
                                    Standard 3-stage
                                    offline pipeline
```

### Phase 1: Online Evidence Extraction

1. The API calls `run_extraction_and_indexing_pipeline(caption)`
2. **Brave Search**: Sends the caption as a search query to the Brave Web Search API
3. **Result Filtering**:
   - Removes results from blocked domains (Reddit, Quora, Facebook, Twitter, Wikipedia, etc.)
   - Removes results that are too similar to the original caption (deduplication via `SequenceMatcher`)
   - Requires valid title, URL, and thumbnail image
4. **Download & Save**: For each valid result:
   - Downloads the thumbnail image → saves as `image.jpg`
   - Saves the article title as `caption.txt`
   - Creates a unique directory in `2_evidence_database/`
5. **ChromaDB Indexing**: Immediately generates CLIP embeddings and adds them to the vector store

### Phase 2: Analysis Submission

After evidence extraction, the API creates a new query in `1_queries/` using the original image and caption. This triggers the standard offline pipeline (watcher → worker → 3 stages).

**Key advantage**: The offline evidence search in Stage 1 now has access to the freshly scraped online evidence, producing more relevant results.

---

## Indian Data Scraper Pipeline

The Indian Data page provides a separate evidence collection workflow targeting Indian fact-checking websites.

### How It Works

1. User selects a scraper (e.g., Factly) and the number of articles to fetch
2. The frontend calls the corresponding API endpoint (e.g., `POST /scrape_factly`)
3. The scraper:
   - Fetches the latest N articles from the source website
   - Parses HTML to extract image, caption, timestamp, and source URL
   - Checks if articles already exist in `6_fakeNewsData/` (deduplication)
   - Downloads and saves new articles with images
   - Indexes new items into ChromaDB
4. Returns a summary showing total found, newly scraped, and already indexed

### Available Sources

| Source        | Focus                         | Languages               |
| ------------- | ----------------------------- | ----------------------- |
| Factly.in     | Data-driven fact-checking     | English, Telugu         |
| BoomLive      | Multimedia fact-checking      | English, Hindi, Bengali |
| FactCrescendo | Independent fact-checking     | English, Hindi          |
| NewsChecker   | Misinformation detection      | English, Hindi          |
| NewsMobile    | News media fact-check section | English                 |
| VishvasNews   | Multi-language fact-checking  | Hindi, English + more   |

---

## Query Lifecycle States

Every query transitions through these states:

```
          ┌──────────┐
          │ pending   │
          └────┬─────┘
               │
          ┌────▼─────┐
          │processing │
          └────┬─────┘
               │
       ┌───────┼───────┐
       │       │       │
  ┌────▼──┐ ┌─▼────┐ ┌▼───────┐
  │failed │ │      │ │completed│
  └───────┘ │      │ └────┬───┘
            │      │      │
            │      │ ┌────▼───┐
            │      │ │trashed │
            │      │ └────┬───┘
            │      │      │
            │      └──────┤
            │             │
            │        ┌────▼────┐
            │        │ restored│──► back to pending
            │        └─────────┘
            │
            └──► can be re-run → back to pending
```

Each query also tracks per-stage status: `evidence_extraction`, `model_inference`, `pdf_generation` — each can be `pending`, `processing`, `completed`, or `failed`.
