import json
from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def planning_agent(query: str) -> dict:
    """
    Takes a user query and breaks it into subtasks.
    Returns a structured plan that the orchestrator follows.
    """
    print(f"  [Planning Agent] Analyzing query...")

    prompt = f"""You are a financial research planning agent. 
A user has asked: "{query}"

Break this into a structured research plan. Respond ONLY with valid JSON, no other text.

Return this exact format:
{{
    "original_query": "{query}",
    "research_tasks": [
        {{
            "task_id": 1,
            "agent": "rag_agent",
            "instruction": "specific instruction for searching SEC filings"
        }},
        {{
            "task_id": 2,
            "agent": "research_agent", 
            "instruction": "specific instruction for web news search"
        }}
    ],
    "companies_mentioned": ["TICKER1", "TICKER2"],
    "synthesis_goal": "what the final answer should accomplish"
}}

Only include companies from this list: AAPL, MSFT, GOOGL, AMZN, NVDA, TSLA, JPM, META.
If no specific company is mentioned, include the most relevant ones."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=1024,
    )

    raw = response.choices[0].message.content.strip()

    # Clean up response in case model adds markdown
    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        plan = json.loads(raw)
        print(f"  [Planning Agent] Plan created — {len(plan['research_tasks'])} tasks, companies: {plan['companies_mentioned']}")
        return plan
    except json.JSONDecodeError:
        # Fallback plan if JSON parsing fails
        print(f"  [Planning Agent] JSON parse failed, using fallback plan")
        return {
            "original_query": query,
            "research_tasks": [
                {"task_id": 1, "agent": "rag_agent", "instruction": query},
                {"task_id": 2, "agent": "research_agent", "instruction": query}
            ],
            "companies_mentioned": [],
            "synthesis_goal": f"Answer the question: {query}"
        }

if __name__ == "__main__":
    test_queries = [
        "What are Apple's biggest risks related to China?",
        "Compare Microsoft and Nvidia's AI strategies",
    ]

    for query in test_queries:
        print(f"\nQuery: {query}")
        print("-" * 40)
        plan = planning_agent(query)
        print(json.dumps(plan, indent=2))