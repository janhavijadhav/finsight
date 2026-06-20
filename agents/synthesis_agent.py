from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def synthesis_agent(
    original_query: str,
    synthesis_goal: str,
    rag_results: list,
    research_results: list
) -> dict:
    """
    Takes outputs from all agents and synthesizes a final report.
    This is the final step in the multi-agent pipeline.
    """
    print(f"  [Synthesis Agent] Writing final report...")

    # Format RAG results
    rag_context = ""
    for r in rag_results:
        if r and r.get("answer"):
            rag_context += f"\n=== SEC FILING ANALYSIS ===\n{r['answer']}\n"

    # Format web research results
    news_context = ""
    for r in research_results:
        if r and r.get("results"):
            news_context += "\n=== RECENT NEWS ===\n"
            for article in r["results"][:3]:
                news_context += f"\nHeadline: {article['title']}\n"
                news_context += f"Summary: {article['snippet']}\n"
                news_context += f"Source: {article['url']}\n"

    prompt = f"""You are FinSight, an expert financial analyst writing a research report.

Original Question: {original_query}
Report Goal: {synthesis_goal}

You have two sources of information:

{rag_context}

{news_context}

Write a comprehensive, well-structured financial research report that:
1. Directly answers the original question
2. Combines insights from SEC filings AND recent news
3. Clearly labels which information comes from filings vs. recent news
4. Uses headers and bullet points for readability
5. Ends with a brief "Key Takeaways" section with 3 bullet points

Be specific, cite sources, and be concise."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=2048,
    )

    report = response.choices[0].message.content

    print(f"  [Synthesis Agent] Report complete ({len(report)} chars)")

    return {
        "report": report,
        "model": response.model,
        "input_tokens": response.usage.prompt_tokens,
        "output_tokens": response.usage.completion_tokens
    }