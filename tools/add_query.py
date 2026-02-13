# tools/add_query.py
import sys
import os

# --- Start of Fix ---
# This code makes the script runnable from the project root (agentic_framework_v2).
# It adds the project root to the Python path.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# --- End of Fix ---

from src.database.status_manager import status_manager

if __name__ == "__main__":
    if len(sys.argv) > 1:
        query_id = sys.argv[1]
        status_manager.add_query(query_id)
    else:
        print("Usage: python tools/add_query.py <query_id>")