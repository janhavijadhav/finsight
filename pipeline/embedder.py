import json
from pathlib import Path
import chromadb
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

def build_vector_store(
    chunks_file: str = "data/processed/all_chunks.json",
    db_path: str = "data/chroma_db"
):
    """
    Embeds all text chunks and stores them in ChromaDB.
    Uses a free local embedding model — no API key needed.
    """
    
    # Load chunks
    with open(chunks_file) as f:
        chunks = json.load(f)
    
    print(f"Embedding {len(chunks)} chunks...")
    
    # Free local embedding model — runs on your machine
    # 'all-MiniLM-L6-v2' is small, fast, and good enough
    print("Loading embedding model (downloads once, ~80MB)...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # Set up ChromaDB — stores data locally in data/chroma_db/
    client = chromadb.PersistentClient(path=db_path)
    
    # Delete existing collection if re-running (clean slate)
    try:
        client.delete_collection("filings")
    except:
        pass
    
    collection = client.create_collection(
        name="filings",
        metadata={"hnsw:space": "cosine"}  # cosine similarity for text
    )
    
    # Embed and store in batches of 100
    batch_size = 100
    for i in tqdm(range(0, len(chunks), batch_size), desc="Embedding"):
        batch = chunks[i:i + batch_size]
        
        texts = [c["text"] for c in batch]
        ids = [c["id"] for c in batch]
        metadatas = [{"ticker": c["ticker"], "source": c["source_file"]} for c in batch]
        
        # Generate embeddings
        embeddings = model.encode(texts).tolist()
        
        # Store in ChromaDB
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas
        )
    
    print(f"\nVector store built at: {db_path}")
    print(f"Total vectors stored: {collection.count()}")
    
    # Quick test — search for something
    print("\nTest search: 'supply chain risk China'")
    test_embedding = model.encode(["supply chain risk China"]).tolist()
    results = collection.query(query_embeddings=test_embedding, n_results=3)
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        print(f"  [{meta['ticker']}] {doc[:120]}...")

if __name__ == "__main__":
    build_vector_store()