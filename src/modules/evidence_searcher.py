# src/modules/evidence_searcher.py
import chromadb
from pathlib import Path
import time
from multiprocessing import Process, Queue 

from src.config import VECTOR_DB_DIR, QUERIES_DIR, EVIDENCE_DB_DIR
from src.modules.embedding_utils import get_image_embedding, get_text_embedding
from src.logger_config import worker_logger


def _perform_search_in_isolated_process(query_image_path, query_caption, top_k, result_queue):
    try:
        client = chromadb.PersistentClient(path=str(VECTOR_DB_DIR))
        collection = client.get_collection(name="evidence_collection")
        
        query_img_emb = get_image_embedding(query_image_path)
        query_text_emb = get_text_embedding(query_caption)

        if query_img_emb is None or query_text_emb is None:
            raise ValueError("Failed to generate embeddings for the query.")

        image_results = collection.query(query_embeddings=[query_img_emb], n_results=top_k, where={"type": "image"})
        text_results = collection.query(query_embeddings=[query_text_emb], n_results=top_k, where={"type": "text"})
        
        combined_results = {}
        if image_results and image_results['ids'][0]:
            for i, item_id in enumerate(image_results['ids'][0]):
                base_id = item_id.replace('_img', '')
                distance = image_results['distances'][0][i]
                similarity = max(0, 1 - distance)
                if base_id not in combined_results or similarity > combined_results[base_id]['similarity_score']:
                     combined_results[base_id] = {'similarity_score': similarity, 'path': image_results['metadatas'][0][i]['path']}

        if text_results and text_results['ids'][0]:
            for i, item_id in enumerate(text_results['ids'][0]):
                base_id = item_id.replace('_txt', '')
                distance = text_results['distances'][0][i]
                similarity = max(0, 1 - distance)
                if base_id not in combined_results or similarity > combined_results[base_id]['similarity_score']:
                    combined_results[base_id] = {'similarity_score': similarity, 'path': text_results['metadatas'][0][i]['path']}
        
        sorted_evidence = sorted(combined_results.items(), key=lambda item: item[1]['similarity_score'], reverse=True)

        final_results = []
        for rank, (item_id, data) in enumerate(sorted_evidence[:top_k], 1):
            evidence_dir = EVIDENCE_DB_DIR / item_id
            img_path = next(evidence_dir.glob('*.[jp][pn]g'), None) or next(evidence_dir.glob('*.webp'), None)
            cap_path = next(evidence_dir.glob('*.txt'), None)
            if img_path and cap_path and img_path.exists() and cap_path.exists():
                # Store paths relative to BASE_DIR (project root)
                from src.config import BASE_DIR
                img_rel = img_path.relative_to(BASE_DIR)
                cap_rel = cap_path.relative_to(BASE_DIR)
                final_results.append({
                    "rank": rank, "similarity_score": round(data['similarity_score'], 4),
                    "image_path": str(img_rel), "caption_path": str(cap_rel)
                })
        
        result_queue.put(final_results)
    except Exception as e:
        result_queue.put(e)

def find_top_evidence(query_image_path: str, query_caption: str, top_k: int = 10, retries: int = 2, delay: int = 5):
    worker_logger.info(f"Initiating isolated search for query: {Path(query_image_path).parent.name}")

    for attempt in range(retries):
        result_queue = Queue()
        search_process = Process(
            target=_perform_search_in_isolated_process,
            args=(query_image_path, query_caption, top_k, result_queue)
        )
        try:
            search_process.start()
            result = result_queue.get(timeout=60)
            search_process.join()

            if isinstance(result, Exception):
                raise result
            
            # Success!
            worker_logger.info(f"Isolated search successful on attempt {attempt + 1}. Found {len(result)} items.")
            return result

        except Exception as e:
            worker_logger.warning(f"Attempt {attempt + 1}/{retries} of isolated search failed. Error: {e}")
            if search_process.is_alive():
                search_process.terminate() 
            
            if attempt + 1 == retries:
                worker_logger.error("All retry attempts failed for isolated search. Propagating error.")
                raise e
            
            worker_logger.info(f"Waiting for {delay} seconds before retrying...")
            time.sleep(delay)


# def find_top_evidence(query_image_path: str, query_caption: str, top_k: int = 10, retries: int = 3, delay: int = 5):

#     worker_logger.info(f"Searching for evidence for query: {Path(query_image_path).parent.name}")

#     for attempt in range(retries):
#         try:
#             client = chromadb.PersistentClient(path=str(VECTOR_DB_DIR))
#             collection = client.get_collection(name="evidence_collection")
            
#             query_img_emb = get_image_embedding(query_image_path)
#             query_text_emb = get_text_embedding(query_caption)

#             if query_img_emb is None or query_text_emb is None:
#                 worker_logger.error("Failed to generate embeddings for the query. Aborting search.")
#                 return []

#             image_results = collection.query(
#                 query_embeddings=[query_img_emb],
#                 n_results=top_k,
#                 where={"type": "image"}
#             )
#             text_results = collection.query(
#                 query_embeddings=[query_text_emb],
#                 n_results=top_k,
#                 where={"type": "text"}
#             )

#             combined_results = {}
#             if image_results and image_results['ids'][0]:
#                 for i, item_id in enumerate(image_results['ids'][0]):
#                     base_id = item_id.replace('_img', '')
#                     distance = image_results['distances'][0][i]
#                     similarity = max(0, 1 - distance)
#                     if base_id not in combined_results or similarity > combined_results[base_id]['similarity_score']:
#                          combined_results[base_id] = {'similarity_score': similarity, 'path': image_results['metadatas'][0][i]['path']}

#             if text_results and text_results['ids'][0]:
#                 for i, item_id in enumerate(text_results['ids'][0]):
#                     base_id = item_id.replace('_txt', '')
#                     distance = text_results['distances'][0][i]
#                     similarity = max(0, 1 - distance)
#                     if base_id not in combined_results or similarity > combined_results[base_id]['similarity_score']:
#                         combined_results[base_id] = {'similarity_score': similarity, 'path': text_results['metadatas'][0][i]['path']}
            
#             sorted_evidence = sorted(combined_results.items(), key=lambda item: item[1]['similarity_score'], reverse=True)

#             final_results = []
#             for rank, (item_id, data) in enumerate(sorted_evidence[:top_k], 1):
#                 evidence_dir = EVIDENCE_DB_DIR / item_id
#                 img_path = next(evidence_dir.glob('*.[jp][pn]g'), None) or next(evidence_dir.glob('*.webp'), None)
#                 cap_path = next(evidence_dir.glob('*.txt'), None)
#                 if img_path and cap_path and img_path.exists() and cap_path.exists():
#                     final_results.append({
#                         "rank": rank, "similarity_score": round(data['similarity_score'], 4),
#                         "image_path": str(img_path.resolve()), "caption_path": str(cap_path.resolve())
#                     })

#             worker_logger.info(f"Successfully found {len(final_results)} relevant evidence items on attempt {attempt + 1}.")
#             return final_results

#         except Exception as e:
#             worker_logger.warning(f"Attempt {attempt + 1}/{retries} to search evidence failed. Error: {e}")
#             if attempt + 1 == retries:
#                 worker_logger.error("All retry attempts failed for evidence search. Propagating error.")
#                 raise e
#             worker_logger.info(f"Waiting for {delay} seconds before retrying...")
#             time.sleep(delay)

if __name__ == "__main__":
    print("--- Running Standalone Evidence Searcher Test ---")
    test_query_dir = QUERIES_DIR / "0"
    try:
        test_image_path = next(test_query_dir.glob('*.jpg')) 
        test_caption_path = next(test_query_dir.glob('*.txt'))
        
        with open(test_caption_path, 'r') as f:
            test_caption = f.read().strip()
            
        print(f"Test Query Image: {test_image_path}")
        print(f"Test Query Caption: '{test_caption}'")
        
        top_evidence = find_top_evidence(str(test_image_path), test_caption, top_k=5)
        if top_evidence:
            print("\n--- Top 5 Evidence Found ---")
            for item in top_evidence:
                print(
                    f"Rank: {item['rank']}, "
                    f"Score: {item['similarity_score']}, "
                    f"Image: ...{Path(item['image_path']).name}, "
                    f"Caption: ...{Path(item['caption_path']).parent.name}/{Path(item['caption_path']).name}"
                )
        else:
            print("No evidence found.")
            
    except (StopIteration, FileNotFoundError):
        print("\nERROR: Test query not found!")
        print(f"Please make sure the directory '{test_query_dir}' exists and contains an image and a .txt file.")