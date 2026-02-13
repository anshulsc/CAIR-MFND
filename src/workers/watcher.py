# src/workers/watcher.py
import time
import os
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from src.config import QUERIES_DIR, JOB_QUEUE_DIR
from src.database.status_manager import status_manager
from src.logger_config import watcher_logger

class QueryHandler(FileSystemEventHandler):


    def on_created(self, event):
        if event.is_directory:
            path = Path(event.src_path)
            
            try:
                rel_path = path.relative_to(QUERIES_DIR)
                parts = rel_path.parts

                if len(parts) == 2:
                    username = parts[0]
                    query_id = parts[1]
                    
                    watcher_logger.info(f"INFO: Detected new query directory: {query_id} for user {username}")
                    
                    status_manager.add_query(query_id, username)
                    
                    job_filename = f"{username}__{query_id}.job"
                    job_file_path = JOB_QUEUE_DIR / job_filename
                    
                    with open(job_file_path, 'w') as f:
                        f.write(f"{username}/{query_id}")
                    
                    watcher_logger.info(f"INFO: Created job file for '{query_id}' at {job_file_path}")
            except ValueError:
                pass

def start_watcher():
    watcher_logger.info("--- Starting Query Watcher ---")
    watcher_logger.info(f"Monitoring directory: {QUERIES_DIR}")
    
    event_handler = QueryHandler()
    observer = Observer()
    observer.schedule(event_handler, str(QUERIES_DIR), recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        watcher_logger.info("\n--- Watcher stopped ---")
    observer.join()

if __name__ == "__main__":
    start_watcher()