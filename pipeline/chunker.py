import json
from pathlib import Path
from typing import List

VALID_TICKERS = {"AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "JPM", "META"}

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """
    Splits text into overlapping word-based chunks.
    
    chunk_size = 500 words per chunk
    overlap = 50 words shared between consecutive chunks
    (so context isn't lost at boundaries)
    """
    words = text.split()
    chunks = []
    
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start += chunk_size - overlap
    
    return chunks

def chunk_all_documents(processed_dir: str = "data/processed"):
    """
    Reads each parsed JSON, chunks the text,
    and saves an enriched JSON with all chunks + metadata.
    Only processes valid ticker files.
    """
    processed_path = Path(processed_dir)
    
    # Only process ticker JSON files, skip all_chunks and knowledge_graph
    json_files = [f for f in processed_path.glob("*.json")
                  if f.stem in VALID_TICKERS]
    
    print(f"Chunking {len(json_files)} document(s)...")
    
    all_chunks = []
    
    for json_file in json_files:
        with open(json_file) as f:
            doc = json.load(f)
        
        chunks = chunk_text(doc["text"])
        print(f"  {doc['ticker']}: {len(chunks)} chunks")
        
        for i, chunk in enumerate(chunks):
            all_chunks.append({
                "id": f"{doc['ticker']}_{json_file.stem}_chunk_{i}",
                "ticker": doc["ticker"],
                "chunk_index": i,
                "text": chunk,
                "source_file": doc["file_path"]
            })
    
    # Save all chunks to one file for the embedder
    out_file = processed_path / "all_chunks.json"
    with open(out_file, "w") as f:
        json.dump(all_chunks, f, indent=2)
    
    print(f"\nTotal chunks: {len(all_chunks)}")
    print(f"Saved to: {out_file}")
    return all_chunks

if __name__ == "__main__":
    chunk_all_documents()