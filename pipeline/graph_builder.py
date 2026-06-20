import json
from pathlib import Path
import spacy
import re
import networkx as nx

nlp = spacy.load("en_core_web_sm")

RISK_KEYWORDS = [
    "risk", "uncertainty", "challenge", "threat", "competition",
    "regulatory", "litigation", "cybersecurity", "inflation", "recession",
    "supply chain", "geopolit", "climate", "interest rate"
]

VALID_TICKERS = {"AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "JPM", "META"}

def extract_risks(text: str) -> list:
    sentences = text.split(". ")
    risks = []
    for sentence in sentences:
        sentence_lower = sentence.lower()
        for keyword in RISK_KEYWORDS:
            if keyword in sentence_lower and len(sentence) > 40:
                risks.append({
                    "text": sentence.strip()[:300],
                    "type": keyword
                })
                break
    return risks[:50]

def extract_companies_mentioned(text: str) -> list:
    doc = nlp(text[:50000])
    companies = set()
    for ent in doc.ents:
        if ent.label_ == "ORG" and len(ent.text) > 2:
            companies.add(ent.text.strip())
    return list(companies)[:30]

def build_graph(processed_dir: str = "data/processed"):
    processed_path = Path(processed_dir)

    # Only process ticker files, not all_chunks or knowledge_graph
    json_files = [f for f in processed_path.glob("*.json")
                  if f.stem in VALID_TICKERS]

    print(f"Building knowledge graph for {len(json_files)} companies...")

    # Create a directed graph
    G = nx.DiGraph()

    for json_file in json_files:
        with open(json_file) as f:
            doc = json.load(f)

        ticker = doc["ticker"]
        text = doc["text"]
        print(f"\nProcessing {ticker}...")

        # Add company node
        G.add_node(ticker, type="Company")

        # Add risk nodes and edges
        risks = extract_risks(text)
        print(f"  Found {len(risks)} risk statements")
        for i, risk in enumerate(risks):
            risk_id = f"{ticker}_risk_{i}"
            G.add_node(risk_id, type="Risk",
                      text=risk["text"],
                      risk_type=risk["type"])
            G.add_edge(ticker, risk_id, relation="HAS_RISK")

        # Add mentioned organizations and edges
        mentioned = extract_companies_mentioned(text)
        print(f"  Mentions {len(mentioned)} organizations")
        for org in mentioned:
            org_id = f"ORG_{org}"
            G.add_node(org_id, type="Organization", name=org)
            G.add_edge(ticker, org_id, relation="MENTIONS")

    # Save graph to file
    graph_path = processed_path / "knowledge_graph.json"
    graph_data = nx.node_link_data(G)
    with open(graph_path, "w") as f:
        json.dump(graph_data, f, indent=2)

    # Print summary
    companies = [n for n, d in G.nodes(data=True) if d.get("type") == "Company"]
    risks = [n for n, d in G.nodes(data=True) if d.get("type") == "Risk"]
    orgs = [n for n, d in G.nodes(data=True) if d.get("type") == "Organization"]

    print(f"\nKnowledge graph built successfully!")
    print(f"  Companies:     {len(companies)}")
    print(f"  Risk nodes:    {len(risks)}")
    print(f"  Org nodes:     {len(orgs)}")
    print(f"  Total edges:   {G.number_of_edges()}")
    print(f"  Saved to:      {graph_path}")

    # Show sample risks per company
    print("\nSample risks found:")
    for ticker in companies:
        risk_neighbors = [
            G.nodes[v] for v in G.successors(ticker)
            if G.nodes[v].get("type") == "Risk"
        ]
        if risk_neighbors:
            sample = risk_neighbors[0]
            print(f"  [{ticker}] {sample.get('risk_type','').upper()}: {sample.get('text','')[:100]}...")

if __name__ == "__main__":
    build_graph()