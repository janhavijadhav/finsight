from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def generate_answer(query: str, retrieval: dict) -> dict:
    """
    Takes a query and hybrid retrieval results (vector + graph),
    builds a grounded prompt, and generates an answer via Groq.
    Returns answer text plus token usage.
    """
    # Format vector search results
    vector_context = ""
    for i, chunk in enumerate(retrieval.get("vector_results", []), 1):
        vector_context += f"\n[{i}] [{chunk['ticker']}] (relevance: {chunk['relevance_score']})\n{chunk['text']}\n"

    # Format knowledge graph results
    graph_context = ""
    for node in retrieval.get("graph_results", []):
        graph_context += f"\n[{node['ticker']}] {node.get('risk_type', 'Risk')}: {node['text']}\n"

    companies = retrieval.get("detected_companies", [])
    company_str = ", ".join(companies) if companies else "the mentioned company"

    prompt = f"""You are FinSight, an expert financial analyst. Answer the following question using ONLY the SEC filing excerpts provided below. Do not use outside knowledge.

Question: {query}

=== SEC FILING EXCERPTS (Vector Search) ===
{vector_context if vector_context else "No vector results found."}

=== KNOWLEDGE GRAPH RISK NODES ===
{graph_context if graph_context else "No graph results found."}

Instructions:
- Answer directly and specifically using the excerpts above
- Cite the company ticker in brackets when referencing specific information, e.g. [AAPL]
- Use bullet points for multiple risk factors or findings
- If the excerpts don't contain enough information to answer fully, say so
- Be concise but thorough

Answer:"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=1024,
    )

    answer = response.choices[0].message.content

    return {
        "answer": answer,
        "model": response.model,
        "input_tokens": response.usage.prompt_tokens,
        "output_tokens": response.usage.completion_tokens,
    }
