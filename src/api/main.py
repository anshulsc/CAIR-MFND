# src/api/main.py
import shutil
import uuid
import zipfile
from pathlib import Path
from typing import List
import json
import regex as re
import time


from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware


from src.config import QUERIES_DIR, JOB_QUEUE_DIR, RESULTS_DIR, PROCESSED_DIR, TRASH_DIR, FAKE_NEWS_DATA_DIR, HIGHLIGHT_NEWS_DIR
from src.database.status_manager import status_manager
from src.logger_config import api_logger
from src.modules.factly_scraper import run_factly_pipeline
from src.modules.boomlive_scraper import run_boomlive_pipeline
from src.modules.factcrescendo_scraper import run_factcrescendo_pipeline
from src.modules.newschecker_sracper import run_newschecker_pipeline
from src.modules.newsmobile_scraper import run_newsmobile_pipeline
from src.modules.vishwanews_scraper import run_vishvasnews_pipeline

from pyngrok import ngrok, conf


app = FastAPI(title="Agentic Framework API")

# Allow CORS for Streamlit communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def _extract_verdict_from_results(query_id: str) -> str:
    try:
        results_path = PROCESSED_DIR / query_id / "inference_results.json"
        if not results_path.exists():
            return "N/A"

        with open(results_path, 'r', encoding='utf-8') as f:
            results = json.load(f)
        
        final_response = results.get('stage2_outputs', {}).get('final_response', "")
        
        verdict_match = re.search(r"\*\*Final Classification\*\*:\s*(\w+)", final_response, re.IGNORECASE)
        if verdict_match:
            verdict = verdict_match.group(1).upper()
            if "FAKE" in verdict:
                return "Fake"
            elif "TRUE" in verdict or "REAL" in verdict:
                return "True"
        return "Uncertain"
    except Exception:
        return "Error"
    
def _extract_fraudnet_result(query_id: str, username: str = None) -> dict:

    default_result = {"label": "N/A", "confidence": 0.0}
    try:
        if username:
            results_path = PROCESSED_DIR / username / query_id / "inference_results.json"
        else:
            results_path = PROCESSED_DIR / query_id / "inference_results.json"
            
        if not results_path.exists():
            return default_result

        with open(results_path, 'r', encoding='utf-8') as f:
            results = json.load(f)
        
        fraudnet_response = results.get('fraudnet_response', {})
        if not fraudnet_response:
            return default_result
            
        label_int = fraudnet_response.get("fraudnet_label")
        label_str = "True News" if label_int == 0 else "Fake News"
        
        return {
            "label": label_str,
            "confidence": fraudnet_response.get("confidence", 0.0)
        }
    except Exception:
        return default_result

def robust_read_text(file_path: Path) -> str:
    if not file_path.exists():
        return ""
    try:
        return file_path.read_text(encoding='utf-8').strip()
    except UnicodeDecodeError:
        try:
            return file_path.read_text(encoding='latin-1').strip()
        except Exception as e:
            api_logger.error(f"Could not read file {file_path} with any encoding: {e}")
            return "[Read Error]"
    except Exception as e:
        api_logger.error(f"An unexpected error occurred reading {file_path}: {e}")
        return "[Read Error]"


@app.get("/queries", summary="Get status of all queries")
def get_all_queries(username: str = None):
    api_logger.info(f"Request received for /queries endpoint. User: {username}")
    queries = status_manager.get_all_queries(username=username)
    
    enriched_queries = []
    for query in queries:
        query_dict = dict(query)
        if query_dict['status'] == 'completed':
            if not query_dict.get('verdict'):
                query_dict['verdict'] = _extract_verdict_from_results(query_dict['query_id']) or "N/A"
            query_dict['fraudnet_result'] = _extract_fraudnet_result(
                query_dict['query_id'], 
                query_dict.get('username')
            )
        else:
            query_dict['verdict'] = query_dict.get('verdict') or "Pending"
            query_dict['fraudnet_result'] = {"label": "Pending", "confidence": 0.0}
        enriched_queries.append(query_dict)
            
    return JSONResponse(content={"queries": enriched_queries})

@app.get("/results/{query_id}", summary="Get a PDF report")
def get_result_pdf(query_id: str):
    query_info = status_manager.get_query_status(query_id)
    if not query_info or not query_info.get("result_pdf_path"):
        api_logger.warning("Result PDF not found or not yet generated", extra={"query_id": query_id})
        raise HTTPException(status_code=404, detail="Result PDF not found or not yet generated.")
    
    pdf_path = Path(query_info["result_pdf_path"])
    if not pdf_path.exists():
        api_logger.error("PDF file missing from filesystem", extra={"query_id": query_id, "path": str(pdf_path)})
        raise HTTPException(status_code=404, detail="PDF file is missing from the filesystem.")

    api_logger.info("Serving result PDF", extra={"query_id": query_id, "path": str(pdf_path)})
    return FileResponse(pdf_path, media_type="application/pdf", filename=f"{query_id}_report.pdf")

@app.post("/rerun/{query_id}", summary="Rerun a query")
def rerun_query(query_id: str):
    query_info = status_manager.get_query_status(query_id)
    if not query_info:
         raise HTTPException(status_code=404, detail=f"Query ID '{query_id}' not found.")
    
    username = query_info.get('username')
    if username:
        query_path = QUERIES_DIR / username / query_id
    else:
        query_path = QUERIES_DIR / query_id

    if not query_path.exists():
        api_logger.warning("Query ID not found in queries directory", extra={"query_id": query_id})
        raise HTTPException(status_code=404, detail=f"Query ID '{query_id}' not found in queries directory.")

    status_manager.reset_query(query_id)
    if username:
        job_filename = f"{username}__{query_id}.job"
        job_content = f"{username}/{query_id}"
    else:
        job_filename = f"{query_id}.job"
        job_content = query_id
        
    job_file_path = JOB_QUEUE_DIR / job_filename
    with open(job_file_path, 'w') as f:
        f.write(job_content)
    
    api_logger.info("Query queued for rerun", extra={"query_id": query_id, "job_file": str(job_file_path)})
    return JSONResponse(content={"message": f"Query '{query_id}' has been queued for rerun."})

@app.post("/add_query_manual", summary="Add query via image and text")
async def add_query_manual(caption: str = Form(...), image: UploadFile = File(...), username: str = Form(...)):
    query_id = f"query_{uuid.uuid4().hex[:8]}"
    
    user_query_dir = QUERIES_DIR / username
    user_query_dir.mkdir(parents=True, exist_ok=True)
    
    query_dir = user_query_dir / query_id
    query_dir.mkdir()

    # Save image
    image_ext = Path(image.filename).suffix or ".jpg"
    image_path = query_dir / f"query_img{image_ext}"
    with open(image_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    # Save caption
    caption_path = query_dir / "query_cap.txt"
    with open(caption_path, "w") as f:
        f.write(caption)

    # The watcher will automatically pick this up. The API's job is done.
    api_logger.info("Manual query added", extra={"query_id": query_id, "image_path": str(image_path), "caption_path": str(caption_path), "username": username})
    return JSONResponse(content={"message": "Query added successfully.", "query_id": query_id})

@app.post("/add_query_folder", summary="Add query via zipped folder")
async def add_query_folder(file: UploadFile = File(...), username: str = Form(...)):
    """Creates a new query from an uploaded zip file containing query_img and query_cap."""
    if not file.filename.endswith('.zip'):
        api_logger.warning("Invalid file type for add_query_folder", extra={"filename": file.filename})
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a .zip file.")

    query_id = f"query_{uuid.uuid4().hex[:8]}"
    
    # Create user-specific directory
    user_query_dir = QUERIES_DIR / username
    user_query_dir.mkdir(parents=True, exist_ok=True)
    
    query_dir = user_query_dir / query_id
    temp_zip_path = query_dir.with_suffix('.zip')

    # Save and extract zip file
    with open(temp_zip_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
        zip_ref.extractall(query_dir)
    
    # Clean up temp file
    temp_zip_path.unlink()
    
    # The watcher will automatically pick this up.
    api_logger.info("Folder query uploaded and extracted", extra={"query_id": query_id, "extract_dir": str(query_dir), "username": username})
    return JSONResponse(content={"message": "Query folder uploaded and extracted successfully.", "query_id": query_id})

@app.get("/details/{query_id}", summary="Get full JSON details for a query")
def get_query_details(query_id: str):
    
    query_info = status_manager.get_query_status(query_id)
    if not query_info:
        raise HTTPException(status_code=404, detail=f"Query ID '{query_id}' not found.")
        
    username = query_info.get('username')
    if username:
        query_dir = PROCESSED_DIR / username / query_id
    else:
        query_dir = PROCESSED_DIR / query_id

    results_path = query_dir / "inference_results.json"
    api_logger.debug("Fetching query details", extra={"query_id": query_id, "results_path": str(results_path)})
    
    if not results_path.exists():
        api_logger.warning("Inference results JSON not found", extra={"query_id": query_id, "results_path": str(results_path)})
        raise HTTPException(status_code=404, detail="Inference results JSON file not found.")
        
    metadata_path = query_dir / "evidence_metadata.json"
    
    metadata = json.loads(metadata_path.read_text()) if metadata_path.exists() else {}
    
    if metadata:
        if "query_image_path" in metadata and not Path(metadata["query_image_path"]).is_absolute():
            metadata["query_image_path"] = str((query_dir / metadata["query_image_path"]).resolve())
        if "query_caption_path" in metadata and not Path(metadata["query_caption_path"]).is_absolute():
            metadata["query_caption_path"] = str((query_dir / metadata["query_caption_path"]).resolve())

    details = {
        "status": query_info,
        "results": json.loads(results_path.read_text()),
        "metadata": metadata
    }

    api_logger.info("Returning query details", extra={"query_id": query_id, "has_metadata": metadata_path.exists()})
    return JSONResponse(content=details)

@app.delete("/trash/{query_id}", summary="Move a query and its results to trash")
def move_query_to_trash(query_id: str):
    api_logger.info(f"Received request to move query '{query_id}' to trash.")
    
    processed_path = PROCESSED_DIR / query_id
    results_path = RESULTS_DIR / query_id
    
    # Define destination paths
    trash_processed_path = TRASH_DIR / "processed" / query_id
    trash_results_path = TRASH_DIR / "results" / query_id
    
    try:
        if processed_path.exists():
            shutil.move(str(processed_path), str(trash_processed_path))
        if results_path.exists():
            shutil.move(str(results_path), str(trash_results_path))
            
        # Update the status in the database
        status_manager.move_to_trash(query_id)
        
        return JSONResponse(content={"message": f"Query '{query_id}' moved to trash."})
    except Exception as e:
        api_logger.error(f"Failed to move '{query_id}' to trash: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to move to trash: {e}")

@app.post("/restore/{query_id}", summary="Restore a query from trash")
def restore_query_from_trash(query_id: str):
    """Moves a query's files back from the trash and resets its status to pending."""
    api_logger.info(f"Received request to restore query '{query_id}' from trash.")

    # Define source paths in trash
    trash_processed_path = TRASH_DIR / "processed" / query_id
    trash_results_path = TRASH_DIR / "results" / query_id

    # Define original destination paths
    processed_path = PROCESSED_DIR / query_id
    results_path = RESULTS_DIR / query_id
    
    try:
        if trash_processed_path.exists():
            shutil.move(str(trash_processed_path), str(processed_path))
        if trash_results_path.exists():
            shutil.move(str(trash_results_path), str(results_path))
        
        # Reset the status in the database (restoring puts it back in a neutral state)
        status_manager.reset_query(query_id)
        # We create a job file so the user can choose to rerun it from the dashboard.
        (JOB_QUEUE_DIR / f"{query_id}.job").touch()
        
        return JSONResponse(content={"message": f"Query '{query_id}' restored and queued for processing."})
    except Exception as e:
        api_logger.error(f"Failed to restore '{query_id}': {e}")
        raise HTTPException(status_code=500, detail=f"Failed to restore from trash: {e}")

@app.delete("/delete_permanent/{query_id}", summary="Permanently delete a query")
def delete_query_permanently(query_id: str):
    """Permanently deletes a query's files from trash and its record from the database."""
    api_logger.warning(f"Received request to PERMANENTLY DELETE query '{query_id}'.")


    trash_processed_path = TRASH_DIR / "processed" / query_id
    trash_results_path = TRASH_DIR / "results" / query_id
    
    try:
        if trash_processed_path.exists():
            shutil.rmtree(trash_processed_path)
        if trash_results_path.exists():
            shutil.rmtree(trash_results_path)
            
        # Remove from the database
        status_manager.delete_permanently(query_id)
        
        return JSONResponse(content={"message": f"Query '{query_id}' has been permanently deleted."})
    except Exception as e:
        api_logger.error(f"Failed to permanently delete '{query_id}': {e}")
        raise HTTPException(status_code=500, detail=f"Failed to permanently delete: {e}")
    
from src.modules.online_evidence_extractor import run_extraction_and_indexing_pipeline

@app.post("/extract_evidence", summary="Run the online evidence extraction and indexing agent")
async def extract_evidence_online(caption: str = Form(...)):

    api_logger.info("Received request for online evidence extraction and indexing.") 
    extraction_result = run_extraction_and_indexing_pipeline(caption)
    return JSONResponse(content=extraction_result)



@app.post("/investigate_and_analyze", summary="A full pipeline to extract evidence and queue for analysis")
@app.post("/investigate_and_analyze", summary="A full pipeline to extract evidence and queue for analysis")
async def investigate_and_analyze(caption: str = Form(...), username: str = Form(...), image: UploadFile = File(...)):

    api_logger.info("Received request for full 'Investigate & Analyze' pipeline.")
    
    try:
        extraction_result = run_extraction_and_indexing_pipeline(caption)
        new_evidence_count = extraction_result.get("new_evidence_count", 0)
        api_logger.info(f"Evidence extraction found {new_evidence_count} new items.")
    except Exception as e:
        api_logger.error(f"Online evidence extraction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Evidence extraction failed: {e}")
    
    time.sleep(10)

    try:
        query_id = f"query_{uuid.uuid4().hex[:8]}"
        query_dir = QUERIES_DIR / username / query_id
        query_dir.mkdir(parents=True, exist_ok=True)

        image_ext = Path(image.filename).suffix if Path(image.filename).suffix else ".jpg"
        image_path = query_dir / f"query_img{image_ext}"
        
        # We need to reset the file pointer before reading it again
        image.file.seek(0)
        with open(image_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)

        # Save the caption
        caption_path = query_dir / "query_cap.txt"
        caption_path.write_text(caption.strip(), encoding='utf-8')
        
        api_logger.info(f"Successfully saved new query with ID '{query_id}' for the watcher to process.")
    except Exception as e:
        api_logger.error(f"Failed to save the original query files: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save original query: {e}")

    # --- Step 3: Return a consolidated result to the frontend ---
    final_response = {
        "message": f"Successfully found {new_evidence_count} new evidence items. The original query has been submitted for full analysis.",
        "new_query_id": query_id,
        "extraction_details": extraction_result
    }
    
    return JSONResponse(content=final_response)



@app.post("/scrape_factly", summary="Scrape and index latest articles from Factly.in")
async def scrape_factly_latest(request: Request):
    body = await request.json() if request.headers.get('content-type') == 'application/json' else {}
    count = body.get('count', 10)
    api_logger.info(f"Received request to run Factly scraper agent with count={count}.")
    try:
        result = run_factly_pipeline(count=count)
        return JSONResponse(content=result)
    except Exception as e:
        api_logger.error(f"Factly scraper pipeline failed: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

@app.post("/scrape_boomlive", summary="Scrape and index latest articles from BoomLive")
async def scrape_boomlive_latest(request: Request):
    body = await request.json() if request.headers.get('content-type') == 'application/json' else {}
    count = body.get('count', 10)
    api_logger.info(f"Received request to run BoomLive scraper agent with count={count}.")
    try:
        result = run_boomlive_pipeline(count=count)
        return JSONResponse(content=result)
    except Exception as e:
        api_logger.error(f"BoomLive scraper pipeline failed: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

@app.post("/scrape_factcrescendo", summary="Scrape and index latest articles from FactCrescendo")
async def scrape_factcrescendo_latest(request: Request):
    body = await request.json() if request.headers.get('content-type') == 'application/json' else {}
    count = body.get('count', 10)
    api_logger.info(f"Received request to run FactCrescendo scraper agent with count={count}.")
    try:
        result = run_factcrescendo_pipeline(count=count)
        return JSONResponse(content=result)
    except Exception as e:
        api_logger.error(f"FactCrescendo scraper pipeline failed: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

@app.post("/scrape_newschecker", summary="Scrape and index latest articles from NewsChecker")
async def scrape_newschecker_latest(request: Request):
    body = await request.json() if request.headers.get('content-type') == 'application/json' else {}
    count = body.get('count', 10)
    api_logger.info(f"Received request to run NewsChecker scraper agent with count={count}.")
    try:
        result = run_newschecker_pipeline(count=count)
        return JSONResponse(content=result)
    except Exception as e:
        api_logger.error(f"NewsChecker scraper pipeline failed: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

@app.post("/scrape_newsmobile", summary="Scrape and index latest articles from NewsMobile")
async def scrape_newsmobile_latest(request: Request):
    body = await request.json() if request.headers.get('content-type') == 'application/json' else {}
    count = body.get('count', 10)
    api_logger.info(f"Received request to run NewsMobile scraper agent with count={count}.")
    try:
        result = run_newsmobile_pipeline(count=count)
        return JSONResponse(content=result)
    except Exception as e:
        api_logger.error(f"NewsMobile scraper pipeline failed: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

@app.post("/scrape_vishvasnews", summary="Scrape and index latest articles from Vishvas News")
async def scrape_vishvasnews_latest(request: Request):
    body = await request.json() if request.headers.get('content-type') == 'application/json' else {}
    count = body.get('count', 10)
    api_logger.info(f"Received request to run Vishvas News scraper agent with count={count}.")
    try:
        result = run_vishvasnews_pipeline(count=count)
        return JSONResponse(content=result)
    except Exception as e:
        api_logger.error(f"Vishvas News scraper pipeline failed: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")
    
@app.get("/data_explorer_samples", summary="Get all collected fake news data samples")
def get_data_explorer_samples():
    api_logger.info("Request received for /data_explorer_samples endpoint.")
    
    try:
        sample_paths = sorted(
            [p for p in FAKE_NEWS_DATA_DIR.iterdir() if p.is_dir()],
            key=lambda p: str(p.name),
            reverse=True
        )
        all_sample_details = []

        for sample_path in sample_paths:
            details = {"id": sample_path.name}
            
            q_cap_path = sample_path / "Qcaption.txt"
            q_img_path = next(sample_path.glob("Qimage.*"), None)

            if not (q_cap_path.exists() and q_img_path and q_img_path.exists()):
                continue # Skip incomplete samples

            details["query_caption"] = q_cap_path.read_text(encoding='utf-8').strip()
            details["query_image"] = str(q_img_path)

            evidence_dir = sample_path / f"evidence_{sample_path.name}"
            details["evidence_items"] = []
            if evidence_dir.exists():
                evidence_paths = sorted([p for p in evidence_dir.iterdir() if p.is_dir()], key=lambda p: int(p.name))
                for item_dir in evidence_paths:
                    img_path = next(item_dir.glob("image.*"), None)
                    title_path = item_dir / "title.txt"
                    if img_path and img_path.exists() and title_path.exists():
                        details["evidence_items"].append({
                            "image": str(img_path),
                            "title": title_path.read_text(encoding='utf-8').strip()
                        })
            
            json_path = evidence_dir / "brave_raw_results.json"
            details["brave_json"] = json.load(open(json_path, 'r', encoding='utf-8')) if json_path.exists() else None
            
            all_sample_details.append(details)
        
        return JSONResponse(content={"samples": all_sample_details})

    except Exception as e:
        api_logger.error(f"Error loading data explorer samples: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load samples: {e}")
    
    
@app.get("/highlight_news", summary="Get all highlight news samples")
def get_highlight_news():
    api_logger.info("Request received for /highlight_news endpoint.")
    
    try:
        if not HIGHLIGHT_NEWS_DIR.exists():
            return JSONResponse(content={"highlights": []})

        sample_paths = sorted([p for p in HIGHLIGHT_NEWS_DIR.iterdir() if p.is_dir()])[10:25]
        all_highlights = []

        for sample_dir in sample_paths:
            q_img_path = next(sample_dir.glob("query_image.*"), None)
            q_cap_path = sample_dir / "query_caption.txt"
            g_truth_path = sample_dir / "ground_truth.txt"

            if q_img_path and q_img_path.exists() and q_cap_path.exists():
                caption = robust_read_text(q_cap_path)
                ground_truth = robust_read_text(g_truth_path)

                all_highlights.append({
                    "title": caption,
                    "text": ground_truth if ground_truth else "This is a highlighted case for analysis.",
                    "img_path": str(q_img_path)
                })
        
        return JSONResponse(content={"highlights": all_highlights})

    except Exception as e:
        api_logger.error(f"Error loading highlight news: {e}")
        import traceback
        api_logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to load highlight samples: {e}")
    
    
    
    
    
    
@app.get("/serve_file", summary="Serve a file from the workspace")
def serve_file(path: str):

    file_path = Path(path)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    media_type = "application/octet-stream"
    if file_path.suffix.lower() in ['.jpg', '.jpeg']:
        media_type = "image/jpeg"
    elif file_path.suffix.lower() == '.png':
        media_type = "image/png"
    elif file_path.suffix.lower() == '.pdf':
        media_type = "application/pdf"
    elif file_path.suffix.lower() == '.txt':
        media_type = "text/plain"
        
    return FileResponse(file_path, media_type=media_type)

if __name__ == "__main__":
    import uvicorn
    import os
    from src.config import API_HOST, API_PORT
    
    
    NGROK_AUTHTOKEN = os.environ.get("NGROK_AUTHTOKEN")
    if not NGROK_AUTHTOKEN:
        print("CRITICAL: NGROK_AUTHTOKEN environment variable not set. Tunneling will not work.")
        uvicorn.run(app, host=API_HOST, port=API_PORT)
    else:
        print("INFO: Starting Ngrok tunnel...")
        conf.get_default().auth_token = NGROK_AUTHTOKEN
        public_url = ngrok.connect(API_PORT, "http").public_url
        print(f"✅ Public API URL: {public_url}")
        print("IMPORTANT: Copy this URL and set it as the API_URL in your Streamlit secrets.")

        uvicorn.run(app, host=API_HOST, port=API_PORT)