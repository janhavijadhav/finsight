from ddgs import DDGS
from datetime import datetime

def research_agent(instruction: str, companies: list = None) -> dict:
    """
    Searches the web for recent news related to the instruction.
    Returns structured news results with titles, snippets, and URLs.
    """
    print(f"  [Research Agent] Searching web for: {instruction[:60]}...")

    # Build a focused search query
    if companies:
        company_str = " OR ".join(companies)
        search_query = f"{instruction} {company_str} 2024 2025"
    else:
        search_query = f"{instruction} financial 2025"

    results = []

    try:
        with DDGS() as ddgs:
            search_results = list(ddgs.text(
                search_query,
                max_results=5,
                timelimit="m"  # last month — recent news only
            ))

            for r in search_results:
                results.append({
                    "title": r.get("title", ""),
                    "snippet": r.get("body", "")[:300],
                    "url": r.get("href", ""),
                    "source": "web_search"
                })

        print(f"  [Research Agent] Found {len(results)} news articles")

    except Exception as e:
        print(f"  [Research Agent] Search failed: {e}")
        results = []

    return {
        "instruction": instruction,
        "results": results,
        "searched_at": datetime.now().isoformat(),
        "total_results": len(results)
    }

if __name__ == "__main__":
    print("Testing Research Agent...\n")

    result = research_agent(
        "Apple China supply chain risks tariffs",
        companies=["Apple", "AAPL"]
    )

    print(f"Found {result['total_results']} results:")
    for r in result["results"]:
        print(f"\n  Title: {r['title']}")
        print(f"  Snippet: {r['snippet'][:150]}...")
        print(f"  URL: {r['url']}")