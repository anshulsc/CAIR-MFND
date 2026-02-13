import sys
import os
import shutil
from pathlib import Path
import json
import time

# Add src to path
sys.path.append(str(Path.cwd()))

from unittest.mock import MagicMock
# Mock heavy dependencies before importing worker
sys.modules['vllm'] = MagicMock()
sys.modules['src.modules.inference_pipeline'] = MagicMock()
sys.modules['src.modules.pdf_generator'] = MagicMock()
sys.modules['src.fraudnet_utils'] = MagicMock()

from src.auth import user_manager
from src.config import QUERIES_DIR, JOB_QUEUE_DIR, PROCESSED_DIR
from src.workers.watcher import QueryHandler
# Now import main_worker, it should use mocked modules
from src.workers.main_worker import process_job
from src.database.status_manager import status_manager

def test_user_registration():
    print("Testing User Registration...")
    username = "testuser"
    password = "password123"
    
    # Clean up if exists
    users = user_manager._load_users()
    if username in users:
        del users[username]
        user_manager._save_users(users)

    success, msg = user_manager.register_user(username, password)
    assert success, f"Registration failed: {msg}"
    print("Registration successful.")
    
    assert user_manager.authenticate_user(username, password), "Authentication failed"
    print("Authentication successful.")
    return username

def test_query_creation_and_processing(username):
    print("\nTesting Query Creation and Processing...")
    query_id = "test_query_123"
    
    # 1. Create Query Directory
    query_dir = QUERIES_DIR / username / query_id
    if query_dir.exists():
        shutil.rmtree(query_dir)
    query_dir.mkdir(parents=True)
    
    # Create dummy files
    (query_dir / "image.jpg").touch()
    (query_dir / "caption.txt").write_text("Test caption")
    
    print(f"Created query directory: {query_dir}")
    
    # 2. Simulate Watcher
    handler = QueryHandler()
    class MockEvent:
        is_directory = True
        src_path = str(query_dir)
        
    handler.on_created(MockEvent())
    
    # Check Job File
    job_file = JOB_QUEUE_DIR / f"{username}__{query_id}.job"
    assert job_file.exists(), "Job file not created"
    content = job_file.read_text().strip()
    assert content == f"{username}/{query_id}", f"Incorrect job content: {content}"
    print(f"Job file created correctly: {content}")
    
    # 3. Simulate Worker
    print("Simulating Worker...")
    
    # Mock heavy functions
    import src.workers.main_worker as mw
    mw.find_top_evidence = lambda img, cap: [{"image_path": "dummy_evidence.jpg", "caption_path": "dummy_cap.txt"}]
    def mock_inference(meta):
        res_path = Path("dummy_inference.json")
        with open(res_path, 'w') as f:
            json.dump({"stage2_outputs": {"final_response": "**Final Classification**: Fake"}}, f)
        return res_path
    mw.run_full_inference = mock_inference
    mw.create_report_pdf = lambda meta, inf: Path("dummy_report.pdf")
    
    # Create dummy evidence file so copy works
    Path("dummy_evidence.jpg").touch()
    
    success = process_job(job_file)
    assert success, "Job processing failed"
    
    # Check Processed Directory
    processed_dir = PROCESSED_DIR / username / query_id
    assert processed_dir.exists(), f"Processed directory not created: {processed_dir}"
    assert (processed_dir / "evidence_metadata.json").exists(), "Metadata not created"
    
    # Check Metadata content for relative paths
    metadata_path = processed_dir / "evidence_metadata.json"
    metadata = json.loads(metadata_path.read_text())
    assert metadata["query_image_path"] == "image.jpg", f"Image path is not relative: {metadata['query_image_path']}"
    assert metadata["query_caption_path"] == "caption.txt", f"Caption path is not relative: {metadata['query_caption_path']}"
    
    # Check evidence paths are relative
    if metadata.get('evidences'):
        for evidence in metadata['evidences']:
            assert not evidence['image_path'].startswith('/'), f"Evidence image path is absolute: {evidence['image_path']}"
            assert not evidence['caption_path'].startswith('/'), f"Evidence caption path is absolute: {evidence['caption_path']}"
            assert evidence['image_path'].startswith('agentic_workspace/2_evidence_database/'), \
                f"Evidence image path doesn't start with expected prefix: {evidence['image_path']}"
    
    print("Verified metadata contains relative paths.")
    
    # Check Verdict in DB
    query_info = status_manager.get_query_status(query_id)
    assert query_info['verdict'] == "Fake", f"Verdict not updated in DB. Got: {query_info.get('verdict')}"
    print(f"Verified verdict in DB: {query_info['verdict']}")
    
    print("Job processed successfully and output files created.")
    
    # Clean up
    if query_dir.exists(): shutil.rmtree(query_dir)
    if processed_dir.exists(): shutil.rmtree(processed_dir)
    if job_file.exists(): job_file.unlink()
    if Path("dummy_evidence.jpg").exists(): Path("dummy_evidence.jpg").unlink()
    if Path("dummy_report.pdf").exists(): Path("dummy_report.pdf").unlink()

if __name__ == "__main__":
    try:
        user = test_user_registration()
        test_query_creation_and_processing(user)
        print("\nALL TESTS PASSED!")
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
