import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from parser import parse_all_filings
from chunker import chunk_all_documents
from embedder import build_vector_store
from graph_builder import build_graph

def run_full_pipeline():
    print("=" * 50)
    print("FINSIGHT — Phase 1 Data Pipeline")
    print("=" * 50)

    # Step 1 — skipped: files already downloaded manually
    print("\nStep 1/5: Downloading SEC filings...")
    print("  Skipped — filings already present in data/raw/")

    print("\nStep 2/5: Parsing HTML filings...")
    parse_all_filings(
        raw_dir="../data/raw" if Path("../data/raw").exists() else "data/raw",
        output_dir="../data/processed" if Path("../data/processed").exists() else "data/processed"
    )

    print("\nStep 3/5: Chunking documents...")
    chunk_all_documents(
        processed_dir="../data/processed" if Path("../data/processed").exists() else "data/processed"
    )

    print("\nStep 4/5: Building vector store...")
    build_vector_store(
        chunks_file="../data/processed/all_chunks.json" if Path("../data/processed").exists() else "data/processed/all_chunks.json",
        db_path="../data/chroma_db" if Path("../data/chroma_db").exists() else "data/chroma_db"
    )

    print("\nStep 5/5: Building knowledge graph...")
    build_graph(
        processed_dir="../data/processed" if Path("../data/processed").exists() else "data/processed"
    )

    print("\n" + "=" * 50)
    print("Phase 1 Complete!")
    print("  Raw filings:     data/raw/")
    print("  Processed docs:  data/processed/")
    print("  Vector store:    data/chroma_db/")
    print("  Knowledge graph: data/processed/knowledge_graph.json")
    print("=" * 50)

if __name__ == "__main__":
    run_full_pipeline()