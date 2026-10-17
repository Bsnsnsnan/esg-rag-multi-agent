"""
Week 2, Steps 13-14: Embed all chunks with Qwen's text-embedding-v3,
then store them (with metadata) in a persistent ChromaDB collection.

Reads:  chunks.json   (produced by chunk_pdfs.py)
Writes: ./chroma_db/  (persistent ChromaDB directory)

Run with: python embed_and_store.py
"""
import os
import json
import time
from dotenv import load_dotenv
from openai import OpenAI
import chromadb

load_dotenv()

INPUT_FILE = "chunks.json"
CHROMA_PATH = "./chroma_db"
COLLECTION_NAME = "esg_reports"
BATCH_SIZE = 10          # DashScope's embedding endpoint caps texts per request
EMBED_MODEL = "text-embedding-v3"

api_key = os.getenv("DASHSCOPE_API_KEY")
if not api_key:
    raise SystemExit("DASHSCOPE_API_KEY not found. Check your .env file.")

client = OpenAI(
    api_key=api_key,
    base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
)


def embed_batch(texts, retries=3):
    """Embed a list of strings, with basic retry on transient errors."""
    for attempt in range(retries):
        try:
            response = client.embeddings.create(model=EMBED_MODEL, input=texts)
            return [item.embedding for item in response.data]
        except Exception as e:
            if attempt == retries - 1:
                raise
            print(f"  Embedding batch failed ({e}), retrying in 3s...")
            time.sleep(3)


def main():
    if not os.path.exists(INPUT_FILE):
        raise SystemExit(f"'{INPUT_FILE}' not found. Run chunk_pdfs.py first.")

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        chunk_records = json.load(f)

    print(f"Loaded {len(chunk_records)} chunks from '{INPUT_FILE}'.")

    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = chroma_client.get_or_create_collection(COLLECTION_NAME)

    total = len(chunk_records)
    for start in range(0, total, BATCH_SIZE):
        batch = chunk_records[start:start + BATCH_SIZE]
        texts = [r["text"] for r in batch]
        ids = [r["id"] for r in batch]
        metadatas = [r["metadata"] for r in batch]

        embeddings = embed_batch(texts)

        collection.add(
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids,
        )

        done = min(start + BATCH_SIZE, total)
        print(f"  Embedded and stored {done}/{total} chunks...")

    print(f"\nDone. Collection '{COLLECTION_NAME}' now has {collection.count()} chunks stored in '{CHROMA_PATH}'.")


if __name__ == "__main__":
    main()