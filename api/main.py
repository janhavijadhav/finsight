from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys
from pathlib import Path

# Add rag/ to path so we can import from it
sys.path.append(str(Path(__file__).parent.parent / "rag"))

from rag_pipeline import run_rag_pipeline

app = FastAPI(
    title="FinSight API",
    description="Multi-agent financial research system powered by SEC 10-K filings",
    version="1.0.0"
)

# Allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    status: str
    query: str
    answer: str | None
    warnings: list
    sources: dict | None
    error: str | None

@app.get("/")
def root():
    return {
        "name": "FinSight API",
        "status": "running",
        "companies": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "JPM", "META"],
        "endpoints": {
            "POST /query": "Ask a financial research question",
            "GET /health": "Health check"
        }
    }

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    print(f"\nIncoming query: {request.query}")
    result = run_rag_pipeline(request.query)

    return QueryResponse(
        status=result["status"],
        query=result["query"],
        answer=result.get("answer"),
        warnings=result.get("warnings", []),
        sources=result.get("sources"),
        error=result.get("error")
    )

@app.post("/research")
def research(request: QueryRequest):
    """Full multi-agent research report endpoint."""
    sys.path.append(str(Path(__file__).parent.parent / "agents"))
    from orchestrator import orchestrator
    
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    result = orchestrator(request.query)
    return {
        "status": result["status"],
        "query": result["query"],
        "report": result["final_report"],
        "metadata": result["metadata"]
    }