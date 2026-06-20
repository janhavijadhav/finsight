import sys
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent))
sys.path.append(str(Path(__file__).parent.parent / "evaluation"))

from planning_agent import planning_agent
from research_agent import research_agent
from rag_agent import rag_agent
from synthesis_agent import synthesis_agent
from evaluator import evaluate_response
from audit_logger import log_request

def orchestrator(query: str) -> dict:
    print(f"\n{'='*60}")
    print(f"FINSIGHT ORCHESTRATOR")
    print(f"Query: {query}")
    print(f"{'='*60}")

    start_time = datetime.now()
    result = {
        "query": query,
        "status": "success",
        "plan": None,
        "agent_outputs": {},
        "final_report": None,
        "evaluation": None,
        "error": None,
        "metadata": {}
    }

    # Step 1 — Planning
    print("\n[Step 1] Planning...")
    plan = planning_agent(query)
    result["plan"] = plan

    companies = plan.get("companies_mentioned", [])
    tasks = plan.get("research_tasks", [])
    synthesis_goal = plan.get("synthesis_goal", query)

    # Step 2 — Execute tasks
    print("\n[Step 2] Executing agent tasks...")
    rag_outputs = []
    research_outputs = []
    all_sources = []

    for task in tasks:
        agent_name = task.get("agent")
        instruction = task.get("instruction")

        if agent_name == "rag_agent":
            output = rag_agent(instruction, companies)
            rag_outputs.append(output)
            all_sources.extend(output.get("vector_results", []))
            result["agent_outputs"][f"rag_{task['task_id']}"] = {
                "instruction": instruction,
                "total_sources": output.get("total_sources", 0)
            }

        elif agent_name == "research_agent":
            output = research_agent(instruction, companies)
            research_outputs.append(output)
            result["agent_outputs"][f"research_{task['task_id']}"] = {
                "instruction": instruction,
                "total_results": output.get("total_results", 0)
            }

    # Step 3 — Synthesis
    print("\n[Step 3] Synthesizing final report...")
    synthesis = synthesis_agent(
        original_query=query,
        synthesis_goal=synthesis_goal,
        rag_results=rag_outputs,
        research_results=research_outputs
    )
    result["final_report"] = synthesis["report"]

    # Step 4 — Evaluate
    print("\n[Step 4] Evaluating response...")
    evaluation = evaluate_response(
        query=query,
        answer=synthesis["report"],
        sources=all_sources
    )
    result["evaluation"] = evaluation

    # Step 5 — Audit log
    print("\n[Step 5] Logging to audit trail...")
    result["metadata"] = {
        "total_time_seconds": (datetime.now() - start_time).total_seconds(),
        "agents_used": list(set(t["agent"] for t in tasks)),
        "companies_researched": companies,
        "rag_sources": sum(o.get("total_sources", 0) for o in rag_outputs),
        "news_articles": sum(o.get("total_results", 0) for o in research_outputs),
        "total_tokens": synthesis["input_tokens"] + synthesis["output_tokens"]
    }

    log_request(
        query=query,
        status=result["status"],
        orchestrator_result=result,
        eval_result=evaluation,
        warnings=[]
    )

    print(f"\n{'='*60}")
    print(f"DONE in {result['metadata']['total_time_seconds']:.1f}s")
    print(f"  RAG sources:   {result['metadata']['rag_sources']}")
    print(f"  News articles: {result['metadata']['news_articles']}")
    print(f"  Eval score:    {evaluation['scores']['overall']}/10")
    print(f"  Eval passed:   {'✅' if evaluation['passed'] else '❌'}")
    print(f"{'='*60}")

    return result

if __name__ == "__main__":
    result = orchestrator(
        "What are Microsoft's biggest AI risks and recent developments?"
    )
    print(f"\nFINAL REPORT:\n{result['final_report']}")
    print(f"\nEVALUATION: {result['evaluation']['scores']}")