#!/usr/bin/env python3
"""
Backfill script to populate verdict column for existing queries.
This reads the inference_results.json for completed queries and extracts the verdict.
"""
import sys
import json
import re
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.config import PROCESSED_DIR
from src.database.status_manager import status_manager

def extract_verdict_from_results(results_path):
    """Extract verdict from inference_results.json"""
    try:
        with open(results_path) as f:
            data = json.load(f)
        
        final_response = data.get('stage2_outputs', {}).get('final_response', '')
        verdict_match = re.search(r"\*\*Final Classification\*\*:\s*(\w+)", final_response, re.IGNORECASE)
        
        if verdict_match:
            return verdict_match.group(1).title()
        return "Uncertain"
    except Exception as e:
        print(f"Error extracting verdict from {results_path}: {e}")
        return None

def backfill_verdicts():
    """Backfill verdicts for all completed queries"""
    queries = status_manager.get_all_queries()
    updated_count = 0
    skipped_count = 0
    
    for query in queries:
        query_id = query['query_id']
        username = query.get('username')
        current_verdict = query.get('verdict')
        
        # Skip if verdict already exists
        if current_verdict:
            skipped_count += 1
            continue
        
        # Only process completed queries
        if query['status'] != 'completed':
            skipped_count += 1
            continue
        
        # Construct path to inference results
        if username:
            results_path = PROCESSED_DIR / username / query_id / "inference_results.json"
        else:
            results_path = PROCESSED_DIR / query_id / "inference_results.json"
        
        if not results_path.exists():
            print(f"⚠️  No results found for {query_id}")
            skipped_count += 1
            continue
        
        # Extract and save verdict
        verdict = extract_verdict_from_results(results_path)
        if verdict:
            status_manager.set_verdict(query_id, verdict)
            print(f"✅ Updated {query_id}: {verdict}")
            updated_count += 1
        else:
            print(f"❌ Failed to extract verdict for {query_id}")
            skipped_count += 1
    
    print(f"\n📊 Summary:")
    print(f"   Updated: {updated_count}")
    print(f"   Skipped: {skipped_count}")
    print(f"   Total:   {len(queries)}")

if __name__ == "__main__":
    print("🔄 Starting verdict backfill...")
    backfill_verdicts()
    print("✅ Backfill complete!")
