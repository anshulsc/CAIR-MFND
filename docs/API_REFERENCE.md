# API Reference

Complete reference for the FND Mini FastAPI backend. The API server runs on `http://0.0.0.0:8000` by default.

---

## Query Management

### `GET /queries`

Fetch all queries for a given user.

| Parameter  | Type   | Location | Description                |
| ---------- | ------ | -------- | -------------------------- |
| `username` | string | query    | Filter queries by username |

**Response:**

```json
{
  "queries": [
    {
      "query_id": "sample_001",
      "status": "completed",
      "username": "admin",
      "created_at": "2025-12-01T10:00:00",
      "updated_at": "2025-12-01T10:05:00",
      "verdict": "Fake",
      "fraudnet_result": {
        "label": "Fake News",
        "confidence": 0.87
      },
      "stage_statuses": {
        "evidence_extraction": "completed",
        "model_inference": "completed",
        "pdf_generation": "completed"
      }
    }
  ]
}
```

---

### `GET /details/{query_id}`

Get detailed results for a specific query, including full inference results and evidence metadata.

| Parameter  | Type   | Location | Description          |
| ---------- | ------ | -------- | -------------------- |
| `query_id` | string | path     | The query identifier |

**Response:**

```json
{
    "status": { "...status fields..." },
    "results": {
        "stage2_outputs": {
            "img_txt_result": "...",
            "qimg_eimg_result": "...",
            "claim_verification_str": "...",
            "final_response": "...",
            "txt_txt_results": ["..."],
            "txt_txt_rational_summary": ["..."]
        },
        "fraudnet_response": {
            "fraudnet_label": 1,
            "confidence": 0.87
        }
    },
    "metadata": {
        "query_id": "sample_001",
        "username": "admin",
        "query_image_path": "...",
        "query_caption_path": "...",
        "evidences": [
            {
                "image_path": "...",
                "caption_path": "...",
                "similarity_score": 0.85
            }
        ]
    }
}
```

---

### `POST /add_query_manual`

Submit a new query with an uploaded image and typed caption.

| Parameter  | Type   | Location | Description                      |
| ---------- | ------ | -------- | -------------------------------- |
| `caption`  | string | form     | The news caption/claim to verify |
| `image`    | file   | form     | The news image (jpg, png, webp)  |
| `username` | string | form     | The user submitting the query    |

**Response:**

```json
{
  "message": "Query added successfully.",
  "query_id": "generated_query_id"
}
```

---

### `POST /add_query_folder`

Submit a query by uploading a `.zip` file containing an image and `query_cap.txt`.

| Parameter  | Type   | Location | Description                               |
| ---------- | ------ | -------- | ----------------------------------------- |
| `file`     | file   | form     | ZIP file containing image + query_cap.txt |
| `username` | string | form     | The user submitting the query             |

**Response:**

```json
{
  "message": "Query folder uploaded successfully.",
  "query_id": "extracted_folder_name"
}
```

---

### `POST /rerun/{query_id}`

Re-run a failed or completed query. Resets the status to `pending` and re-queues it.

| Parameter  | Type   | Location | Description         |
| ---------- | ------ | -------- | ------------------- |
| `query_id` | string | path     | The query to re-run |

**Response:**

```json
{
  "message": "Query re-queued successfully."
}
```

---

### `GET /result_pdf/{query_id}`

Download the generated PDF report for a completed query.

| Parameter  | Type   | Location | Description          |
| ---------- | ------ | -------- | -------------------- |
| `query_id` | string | path     | The query identifier |

**Response:** PDF file (binary, `application/pdf`)

---

## Trash Management

### `POST /trash/{query_id}`

Move a query to the trash. Files are moved to `5_trash/`.

**Response:**

```json
{
  "message": "Query moved to trash."
}
```

### `POST /restore/{query_id}`

Restore a trashed query. Files are moved back and status is reset to `pending`.

**Response:**

```json
{
  "message": "Query restored and re-queued."
}
```

### `DELETE /delete_permanent/{query_id}`

Permanently delete a trashed query. Removes all files and the database record.

**Response:**

```json
{
  "message": "Query permanently deleted."
}
```

---

## Evidence & Investigation

### `POST /extract_evidence_online`

Search the web for evidence related to a caption and index the results.

| Parameter | Type   | Location | Description                    |
| --------- | ------ | -------- | ------------------------------ |
| `caption` | string | form     | The news caption to search for |

**Response:**

```json
{
  "new_evidence_count": 5,
  "message": "Successfully extracted and indexed 5 new evidence items."
}
```

---

### `POST /investigate_and_analyze`

Combined pipeline: extract online evidence, then submit the query for full analysis.

| Parameter  | Type   | Location | Description                     |
| ---------- | ------ | -------- | ------------------------------- |
| `caption`  | string | form     | The news caption to investigate |
| `image`    | file   | form     | The news image                  |
| `username` | string | form     | The user submitting the query   |

**Response:**

```json
{
  "message": "Investigation and analysis started.",
  "extraction_details": {
    "new_evidence_count": 3,
    "saved_evidence": [{ "image_path": "...", "caption": "..." }]
  },
  "new_query_id": "generated_query_id"
}
```

---

## Scrapers

All scraper endpoints accept a JSON body with an optional `count` parameter (default: 10).

### `POST /scrape_factly`

### `POST /scrape_boomlive`

### `POST /scrape_factcrescendo`

### `POST /scrape_newschecker`

### `POST /scrape_newsmobile`

### `POST /scrape_vishvasnews`

| Parameter | Type    | Location  | Description                                       |
| --------- | ------- | --------- | ------------------------------------------------- |
| `count`   | integer | json body | Number of latest articles to scrape (default: 10) |

**Response:**

```json
{
  "message": "Successfully processed 10 articles. 3 newly scraped.",
  "newly_scraped_count": 3,
  "processed_items": [
    {
      "image_path": "/path/to/image.jpg",
      "caption": "Article title...",
      "timestamp": "2025-01-15",
      "source_url": "https://..."
    }
  ]
}
```

---

## Data Explorer

### `GET /data_explorer_samples`

Fetch all fake news samples from `6_fakeNewsData/` for browsing.

**Response:**

```json
{
    "samples": [
        {
            "id": "sample_folder_name",
            "query_image": "/path/to/image.jpg",
            "query_caption": "...",
            "evidence_items": [
                { "image": "...", "title": "..." }
            ],
            "brave_json": { "...raw brave search results..." }
        }
    ]
}
```

---

### `GET /highlight_news`

Fetch curated highlight news items for the dashboard carousel.

**Response:**

```json
{
  "items": [
    {
      "image_path": "/path/to/image.jpg",
      "caption": "...",
      "verdict": "Fake"
    }
  ]
}
```

---

## File Serving

### `GET /serve_file`

Serve a local file to the frontend (used for displaying images across different hosts).

| Parameter | Type   | Location | Description                        |
| --------- | ------ | -------- | ---------------------------------- |
| `path`    | string | query    | Absolute path to the file to serve |

**Response:** Binary file content with appropriate MIME type.

---

## Error Handling

All endpoints return standard HTTP error codes:

| Code  | Meaning                               |
| ----- | ------------------------------------- |
| `200` | Success                               |
| `404` | Query not found / File not found      |
| `422` | Validation error (missing parameters) |
| `500` | Internal server error                 |

Error responses include a `detail` field:

```json
{
  "detail": "Query 'sample_001' not found."
}
```
