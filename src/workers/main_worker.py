import os
import time
import shutil
import json
from pathlib import Path
import multiprocessing as mp

from src.config import (
    JOB_QUEUE_DIR, JOB_COMPLETED_DIR, JOB_FAILED_DIR, WORKER_SLEEP_INTERVAL,
    QUERIES_DIR, PROCESSED_DIR
)
from src.database.status_manager import status_manager
from src.modules.evidence_searcher import find_top_evidence
from src.modules.inference_pipeline import run_full_inference
from src.modules.pdf_generator import create_report_pdf
from src.logger_config import worker_logger

def find_query_files(query_path: Path):
    if not query_path.is_dir():
        raise FileNotFoundError(f"Query directory not found: {query_path}")


    image_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp']
    img_file = None
    for ext in image_extensions:
        found_files = list(query_path.glob(f"*{ext}"))
        if found_files:
            img_file = found_files[0] 
            break 

    if img_file is None:
        raise FileNotFoundError(f"No valid image file (.jpg, .png, etc.) found in '{query_path}'")

    # Search for the caption file
    try:
        cap_file = next(query_path.glob('*.txt'))
    except StopIteration:
        raise FileNotFoundError(f"No caption file (.txt) found in '{query_path}'")
    
    return img_file, cap_file

def process_job(job_path):
    try:
        with open(job_path, 'r') as f:
            content = f.read().strip()
    except Exception as e:
        worker_logger.error(f"Failed to read job file {job_path}: {e}")
        return False

    if '/' in content:
        username, query_id = content.split('/', 1)
        rel_path = Path(content)
    else:
        query_id = content
        username = None
        rel_path = Path(query_id)

    worker_logger.info(f"\n--- [WORKER] Processing job for query: {query_id} (User: {username}) ---")
    
    current_stage = "initialization" 

    try:
        status_manager.update_stage_status(query_id, "evidence_extraction", "processing")
        worker_logger.info(f"INFO: [Stage 1/3] Starting Evidence Extraction for '{query_id}'...")
        query_path = QUERIES_DIR / rel_path
        
        q_img_path, q_cap_path = find_query_files(query_path)
        with open(q_cap_path) as f:
            q_caption = f.read().strip()

        # 2. Run the search
        evidence_results = find_top_evidence(str(q_img_path), q_caption)

        # 3. Prepare the processed directory
        # Use the same relative path structure for processed dir
        processed_query_dir = PROCESSED_DIR / rel_path
        processed_query_dir.mkdir(parents=True, exist_ok=True)
        
        # 4. Copy original query files
        shutil.copy(q_img_path, processed_query_dir / q_img_path.name)
        shutil.copy(q_cap_path, processed_query_dir / q_cap_path.name)
        
        # 5. Copy best evidence image
        if evidence_results:
            best_evidence_path = Path(evidence_results[0]['image_path'])
            shutil.copy(best_evidence_path, processed_query_dir / "best_evidence.jpg")
        
        # 6. Save the metadata file
        metadata = {
            "query_id": query_id,
            "username": username,
            "query_image_path": q_img_path.name,
            "query_caption_path": q_cap_path.name,
            "evidences": evidence_results
        }
        metadata_path = processed_query_dir / "evidence_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=4)
        
        worker_logger.info(f"INFO: Evidence extraction complete. Metadata saved to {metadata_path}")
        status_manager.update_stage_status(query_id, "evidence_extraction", "completed")
        
        # STAGE 2: Model Inference (Placeholder)
        status_manager.update_stage_status(query_id, "model_inference", "processing")
        current_stage = "model_inference"
        status_manager.update_stage_status(query_id, "model_inference", "processing")
        worker_logger.info(f"INFO: [Stage 2/3] Starting Model Inference for '{query_id}'...")
        
        inference_result_path = run_full_inference(metadata_path)
        
        # Extract and save verdict
        try:
            with open(inference_result_path) as f:
                res_data = json.load(f)
            final_response = res_data.get('stage2_outputs', {}).get('final_response', '')
            
            import re
            verdict_match = re.search(r"\*\*Final Classification\*\*:\s*(\w+)", final_response, re.IGNORECASE)
            verdict = verdict_match.group(1).title() if verdict_match else "Uncertain"
            
            status_manager.set_verdict(query_id, verdict)
            worker_logger.info(f"INFO: Verdict '{verdict}' saved for query '{query_id}'")
        except Exception as e:
            worker_logger.error(f"ERROR: Failed to extract/save verdict: {e}")

        status_manager.update_stage_status(query_id, "model_inference", "completed")

        current_stage = "pdf_generation"
        status_manager.update_stage_status(query_id, "pdf_generation", "processing")
        worker_logger.info(f"INFO: [Stage 3/3] Starting PDF Generation for '{query_id}'...")
        
        pdf_path = create_report_pdf(metadata_path, inference_result_path)
        status_manager.set_result_path(query_id, str(pdf_path.resolve()))

        status_manager.update_stage_status(query_id, "pdf_generation", "completed")

        worker_logger.info(f"SUCCESS: Job for '{query_id}' completed successfully.")
        return True


    except Exception as e:
        import traceback
        error_msg = f"ERROR: Job for '{query_id}' failed at stage '{current_stage}'. Reason: {e}"
        worker_logger.info(error_msg)
        worker_logger.info(traceback.format_exc())
        status_manager.update_stage_status(query_id, current_stage, "failed", error_message=str(e))
        return False

def start_worker():
    worker_logger.info("--- Starting Main Worker ---")
    worker_logger.info(f"Watching for jobs in: {JOB_QUEUE_DIR}")

    while True:
        job_files = list(JOB_QUEUE_DIR.glob("*.job"))
        if not job_files:
            time.sleep(WORKER_SLEEP_INTERVAL)
            continue

        job_path = job_files[0]
        is_successful = process_job(job_path)

        if is_successful:
            destination = JOB_COMPLETED_DIR / job_path.name
        else:
            destination = JOB_FAILED_DIR / job_path.name
            
        shutil.move(str(job_path), str(destination))
        worker_logger.info(f"INFO: Moved job file to {destination}")

if __name__ == "__main__":
    
    try:
        mp.set_start_method('spawn', force=True)
        worker_logger.info("Multiprocessing start method set to 'spawn' for CUDA safety.")
    except RuntimeError:
        worker_logger.info("Multiprocessing context already set.")

    try:
        start_worker()
    except KeyboardInterrupt:
        worker_logger.info("\n--- Worker stopped by user ---")
        
    try:
        start_worker()
    except KeyboardInterrupt:
        worker_logger.info("\n--- Worker stopped ---")