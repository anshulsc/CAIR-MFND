# src/database/status_manager.py
import sqlite3
import json
from datetime import datetime
from contextlib import contextmanager
from src.config import DB_PATH

class StatusManager:
    def __init__(self):
        self.db_path = DB_PATH
        self.init_db()

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections with proper timeout and WAL mode."""
        conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # Enable WAL mode for better concurrency
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")  # 30 seconds timeout
        try:
            yield conn
        finally:
            conn.close()

    def init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='queries'")
            table_exists = cursor.fetchone()
            
            if not table_exists:
                cursor.execute("""
                    CREATE TABLE queries (
                        query_id TEXT PRIMARY KEY,
                        username TEXT,
                        status TEXT NOT NULL,
                        stages TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        result_pdf_path TEXT,
                        error_message TEXT,
                        verdict TEXT
                    )
                """)
            else:
                # Check if username column exists, if not add it
                cursor.execute("PRAGMA table_info(queries)")
                columns = [info[1] for info in cursor.fetchall()]
                if 'username' not in columns:
                    print("INFO: Migrating database to include 'username' column.")
                    cursor.execute("ALTER TABLE queries ADD COLUMN username TEXT")
                if 'verdict' not in columns:
                    print("INFO: Migrating database to include 'verdict' column.")
                    cursor.execute("ALTER TABLE queries ADD COLUMN verdict TEXT")
                    
            conn.commit()

    def add_query(self, query_id: str, username: str = None):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.utcnow().isoformat()
            initial_stages = {
                "evidence_extraction": "pending",
                "model_inference": "pending",
                "pdf_generation": "pending"
            }
            
            try:
                cursor.execute(
                    "INSERT INTO queries (query_id, username, status, stages, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (query_id, username, "pending", json.dumps(initial_stages), now, now)
                )
                conn.commit()
                print(f"INFO: Query '{query_id}' added to status tracker for user '{username}'.")
            except sqlite3.IntegrityError:
                print(f"WARN: Query '{query_id}' already exists in the database.")

    def update_stage_status(self, query_id: str, stage: str, status: str, error_message: str = None):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT stages FROM queries WHERE query_id = ?", (query_id,))
            row = cursor.fetchone()
            if not row:
                print(f"ERROR: Query ID '{query_id}' not found.")
                return

            stages = json.loads(row['stages'])
            stages[stage] = status
            
            # Determine overall status
            overall_status = "processing"
            if status == "failed":
                overall_status = "failed"
            elif all(s == "completed" for s in stages.values()):
                overall_status = "completed"

            cursor.execute(
                """
                UPDATE queries 
                SET status = ?, stages = ?, updated_at = ?, error_message = ?
                WHERE query_id = ?
                """,
                (overall_status, json.dumps(stages), datetime.utcnow().isoformat(), error_message, query_id)
            )
            conn.commit()
            print(f"INFO: Status updated for '{query_id}': Stage '{stage}' -> '{status}'")

    def set_result_path(self, query_id: str, pdf_path: str):
        """Sets the final PDF result path for a query."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE queries SET result_pdf_path = ?, updated_at = ? WHERE query_id = ?",
                (pdf_path, datetime.utcnow().isoformat(), query_id)
            )
            conn.commit()

    def set_verdict(self, query_id, verdict):
        """Updates the verdict for a query."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE queries
                SET verdict = ?, updated_at = ?
                WHERE query_id = ?
            """, (verdict, datetime.utcnow().isoformat(), query_id))
            conn.commit()
        
    def get_all_queries(self, username: str = None):
        """Retrieves all queries from the database, optionally filtered by username."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            if username:
                cursor.execute("SELECT * FROM queries WHERE username = ? ORDER BY created_at DESC", (username,))
            else:
                cursor.execute("SELECT * FROM queries ORDER BY created_at DESC")
                
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        
    def get_query_status(self, query_id: str):
        """Retrieves the status of a single query."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM queries WHERE query_id = ?", (query_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def reset_query(self, query_id: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.utcnow().isoformat()
            initial_stages = {
                "evidence_extraction": "pending",
                "model_inference": "pending",
                "pdf_generation": "pending"
            }
            
            cursor.execute(
                """
                UPDATE queries
                SET status = ?, stages = ?, updated_at = ?, result_pdf_path = NULL, error_message = NULL
                WHERE query_id = ?
                """,
                ("pending", json.dumps(initial_stages), now, query_id)
            )
            conn.commit()
            print(f"INFO: Query '{query_id}' has been reset for reprocessing.")
        
    
    def move_to_trash(self, query_id: str):
        """Marks a query's status as 'trashed' in the database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.utcnow().isoformat()
            cursor.execute(
                "UPDATE queries SET status = ?, updated_at = ? WHERE query_id = ?",
                ("trashed", now, query_id)
            )
            conn.commit()
        
    def delete_permanently(self, query_id: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM queries WHERE query_id = ?", (query_id,))
            conn.commit()


status_manager = StatusManager()