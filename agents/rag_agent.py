import sys
from pathlib import Path

# Add rag/ to path
sys.path.append(str(Path(__file__).parent.parent / "rag"))

from retriever import hybrid_search
from generator import generate_answer

def rag_agent(instruction: str, companies: list = None) -> dict:
    """
    Queries the SEC filing vector store and knowledge graph.
    Wraps Phase 2 RAG pipeline as an agent.
    """
    print(f"  [RAG Agent] Searching filings for: {instruction[:60]}...")

    # Run hybrid search
    retrieval = hybrid_search(instruction)

    if retrieval["total_sources"] == 0:
        print(f"  [RAG Agent] No relevant chunks found")
        return {
            "instruction": instruction,
            "answer": "No relevant information found in SEC filings.",
            "sources": [],
            "total_sources": 0
        }

    # Generate answer from retrieved chunks
    generation = generate_answer(instruction, retrieval)

    print(f"  [RAG Agent] Found {retrieval['total_sources']} sources, generated answer")

    return {
        "instruction": instruction,
        "answer": generation["answer"],
        "vector_results": retrieval["vector_results"],
        "graph_results": retrieval["graph_results"],
        "total_sources": retrieval["total_sources"],
        "companies_found": retrieval["detected_companies"]
    }

if __name__ == "__main__":
    print("Testing RAG Agent...\n")

    result = rag_agent(
        "What are Apple's risks related to China and supply chain?",
        companies=["AAPL"]
    )

    print(f"Total sources: {result['total_sources']}")
    print(f"Companies found: {result['companies_found']}")
    print(f"\nAnswer preview:\n{result['answer'][:300]}...")