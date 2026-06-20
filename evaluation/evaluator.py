import re
import sys
from pathlib import Path
from groq import Groq
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def score_relevance(query: str, answer: str) -> dict:
    """
    Scores how relevant the answer is to the query.
    Uses LLM as a judge — standard production technique.
    """
    prompt = f"""You are an evaluation agent. Score the relevance of this answer to the query.

Query: {query}
Answer: {answer[:500]}

Rate relevance from 1-10 where:
10 = perfectly answers the query
5  = partially answers the query  
1  = completely irrelevant

Respond ONLY with JSON: {{"score": <number>, "reason": "<one sentence>"}}"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=100,
    )

    raw = response.choices[0].message.content.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        return {"metric": "relevance", **eval(raw)}
    except:
        return {"metric": "relevance", "score": 5, "reason": "Could not parse score"}

def score_consistency(answer: str, sources: list) -> dict:
    """
    Checks if the answer is consistent with the source documents.
    Detects hallucinations by checking key claims against sources.
    """
    if not sources:
        return {"metric": "consistency", "score": 5, "reason": "No sources to check against"}

    source_text = " ".join(
        s.get("text", "") for s in sources if isinstance(s, dict)
    )[:2000]

    prompt = f"""You are a fact-checking agent. Check if this answer is consistent with the source documents.

Answer: {answer[:500]}

Source documents: {source_text}

Rate consistency from 1-10 where:
10 = all claims are supported by sources
5  = some claims are supported
1  = answer contradicts or ignores sources

Respond ONLY with JSON: {{"score": <number>, "reason": "<one sentence>"}}"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=100,
    )

    raw = response.choices[0].message.content.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        return {"metric": "consistency", **eval(raw)}
    except:
        return {"metric": "consistency", "score": 5, "reason": "Could not parse score"}

def score_accuracy(answer: str) -> dict:
    """
    Checks structural accuracy — does the answer have citations,
    proper structure, and avoid vague claims?
    """
    score = 10
    reasons = []

    # Check for citations
    if "10-K" in answer or "Source" in answer or "AAPL" in answer or "MSFT" in answer:
        reasons.append("has citations")
    else:
        score -= 3
        reasons.append("missing citations")

    # Check for specific data points
    has_numbers = bool(re.search(r'\d+%|\$[\d,]+|decreased|increased', answer))
    if has_numbers:
        reasons.append("contains specific data")
    else:
        score -= 2
        reasons.append("lacks specific data points")

    # Check minimum length
    if len(answer) < 100:
        score -= 3
        reasons.append("answer too brief")
    else:
        reasons.append("adequate length")

    return {
        "metric": "accuracy",
        "score": max(1, score),
        "reason": ", ".join(reasons)
    }

def evaluate_response(query: str, answer: str, sources: list = None) -> dict:
    """
    Runs all three evaluation metrics and returns a combined score.
    This is what gets called after every RAG or agent response.
    """
    print("  [Evaluator] Scoring response...")

    relevance = score_relevance(query, answer)
    consistency = score_consistency(answer, sources or [])
    accuracy = score_accuracy(answer)

    overall = round(
        (relevance["score"] + consistency["score"] + accuracy["score"]) / 3, 1
    )

    result = {
        "timestamp": datetime.now().isoformat(),
        "query": query,
        "scores": {
            "relevance": relevance,
            "consistency": consistency,
            "accuracy": accuracy,
            "overall": overall
        },
        "passed": overall >= 6.0  # threshold for acceptable response
    }

    status = "PASS" if result["passed"] else "FAIL"
    print(f"  [Evaluator] {status} — Overall: {overall}/10 "
          f"(R:{relevance['score']} C:{consistency['score']} A:{accuracy['score']})")

    return result

if __name__ == "__main__":
    print("Testing Evaluator...\n")

    test_answer = """**Apple's Biggest Risks Related to China**
    According to Apple's (AAPL) 2025 Form 10-K, the company faces:
    1. Supply chain risks — manufacturing concentrated in China
    2. Revenue exposure — Greater China sales decreased 4% in 2025
    3. Regulatory risks — subject to Chinese export/import regulations
    """

    result = evaluate_response(
        query="What are Apple's biggest risks related to China?",
        answer=test_answer,
        sources=[{"text": "Apple manufacturing in China supply chain risk decreased 4%"}]
    )

    print("\nFull evaluation result:")
    import json
    print(json.dumps(result, indent=2))