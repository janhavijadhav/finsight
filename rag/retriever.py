import json
import chromadb
import networkx as nx
from pathlib import Path
from sentence_transformers import SentenceTransformer

# Load once at module level so we don't reload on every query
_model = None
_collection = None
_graph = None

def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    return _model

def get_collection():
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path="data/chroma_db")
        _collection = client.get_collection("filings")
    return _collection

def get_graph():
    global _graph
    if _graph is None:
        graph_path = Path("data/processed/knowledge_graph.json")
        with open(graph_path) as f:
            data = json.load(f)
        _graph = nx.node_link_graph(data)
    return _graph

def vector_search(query: str, n_results: int = 5, ticker_filter: str = None) -> list:
    """
    Searches ChromaDB for chunks semantically similar to the query.
    Optionally filters by company ticker.
    """
    model = get_model()
    collection = get_collection()

    query_embedding = model.encode([query]).tolist()

    # Build filter if ticker specified
    where = {"ticker": ticker_filter} if ticker_filter else None

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=n_results,
        where=where
    )

    chunks = []
    for doc, meta, distance in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0]
    ):
        chunks.append({
            "text": doc,
            "ticker": meta["ticker"],
            "source": meta["source"],
            "relevance_score": round(1 - distance, 3)  # convert distance to similarity
        })

    return chunks

def graph_search(query: str, tickers: list = None) -> list:
    """
    Searches the knowledge graph for risks related to keywords in the query.
    Returns matching risk nodes with their company.
    """
    G = get_graph()
    query_lower = query.lower()

    # Extract keywords from query (words longer than 4 chars)
    keywords = [w.lower() for w in query.split() if len(w) > 4]

    results = []
    for node, data in G.nodes(data=True):
        if data.get("type") != "Risk":
            continue

        risk_text = data.get("text", "").lower()
        risk_type = data.get("risk_type", "").lower()

        # Check if any keyword matches the risk
        if any(kw in risk_text or kw in risk_type for kw in keywords):
            # Find which company owns this risk
            predecessors = list(G.predecessors(node))
            for company in predecessors:
                company_data = G.nodes[company]
                if company_data.get("type") == "Company":
                    # Filter by ticker if specified
                    if tickers and company not in tickers:
                        continue
                    results.append({
                        "ticker": company,
                        "risk_type": data.get("risk_type"),
                        "text": data.get("text"),
                        "source": "knowledge_graph"
                    })

    return results[:10]  # top 10 graph results

def hybrid_search(query: str, n_vector: int = 5, tickers: list = None) -> dict:
    """
    Combines vector search + graph search into one result set.
    This is what gets passed to the LLM for answer generation.
    """
    # Detect if query mentions specific companies
    ticker_map = {
        "apple": "AAPL", "aapl": "AAPL",
        "microsoft": "MSFT", "msft": "MSFT",
        "google": "GOOGL", "googl": "GOOGL", "alphabet": "GOOGL",
        "amazon": "AMZN", "amzn": "AMZN",
        "nvidia": "NVDA", "nvda": "NVDA",
        "tesla": "TSLA", "tsla": "TSLA",
        "jpmorgan": "JPM", "jpm": "JPM", "jp morgan": "JPM",
        "meta": "META", "facebook": "META",
    }

    query_lower = query.lower()
    detected_tickers = list(set(
        ticker for keyword, ticker in ticker_map.items()
        if keyword in query_lower
    ))

    # Use detected tickers or passed tickers
    active_tickers = tickers or detected_tickers or None

    # Run both searches
    vector_results = vector_search(
        query,
        n_results=n_vector,
        ticker_filter=active_tickers[0] if active_tickers and len(active_tickers) == 1 else None
    )

    graph_results = graph_search(query, tickers=active_tickers)

    return {
        "query": query,
        "detected_companies": detected_tickers,
        "vector_results": vector_results,
        "graph_results": graph_results,
        "total_sources": len(vector_results) + len(graph_results)
    }

if __name__ == "__main__":
    # Quick test
    print("Testing hybrid search...")
    results = hybrid_search("What are Apple's biggest risks related to China?")
    print(f"\nDetected companies: {results['detected_companies']}")
    print(f"Vector results: {len(results['vector_results'])}")
    print(f"Graph results: {len(results['graph_results'])}")
    print("\nTop vector result:")
    if results['vector_results']:
        r = results['vector_results'][0]
        print(f"  [{r['ticker']}] score={r['relevance_score']} — {r['text'][:150]}...")
    print("\nTop graph result:")
    if results['graph_results']:
        r = results['graph_results'][0]
        print(f"  [{r['ticker']}] type={r['risk_type']} — {r['text'][:150]}...")