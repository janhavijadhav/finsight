import json
import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = "data/audit_log.db"

def init_db():
    """Creates the audit log database and table if they don't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            query TEXT NOT NULL,
            status TEXT NOT NULL,
            agents_used TEXT,
            tools_called TEXT,
            rag_sources INTEGER,
            news_articles INTEGER,
            eval_overall REAL,
            eval_relevance REAL,
            eval_consistency REAL,
            eval_accuracy REAL,
            eval_passed INTEGER,
            answer_length INTEGER,
            total_tokens INTEGER,
            time_seconds REAL,
            warnings TEXT,
            final_report TEXT
        )
    """)

    conn.commit()
    conn.close()

def log_request(
    query: str,
    status: str,
    orchestrator_result: dict = None,
    eval_result: dict = None,
    warnings: list = None
):
    """
    Logs every request to the audit database.
    Records what tools were used, what data was accessed,
    what decisions were made, and evaluation scores.
    """
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Extract metadata safely
    metadata = orchestrator_result.get("metadata", {}) if orchestrator_result else {}
    scores = eval_result.get("scores", {}) if eval_result else {}
    report = orchestrator_result.get("final_report", "") if orchestrator_result else ""

    cursor.execute("""
        INSERT INTO audit_logs (
            timestamp, query, status, agents_used, tools_called,
            rag_sources, news_articles, eval_overall, eval_relevance,
            eval_consistency, eval_accuracy, eval_passed,
            answer_length, total_tokens, time_seconds, warnings, final_report
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().isoformat(),
        query,
        status,
        json.dumps(metadata.get("agents_used", [])),
        json.dumps(["vector_search", "graph_search", "web_search", "llm_generate"]),
        metadata.get("rag_sources", 0),
        metadata.get("news_articles", 0),
        scores.get("overall", 0),
        scores.get("relevance", {}).get("score", 0),
        scores.get("consistency", {}).get("score", 0),
        scores.get("accuracy", {}).get("score", 0),
        1 if eval_result and eval_result.get("passed") else 0,
        len(report),
        metadata.get("total_tokens", 0),
        metadata.get("total_time_seconds", 0),
        json.dumps(warnings or []),
        report[:2000]  # store first 2000 chars
    ))

    conn.commit()
    conn.close()
    print(f"  [Audit Logger] Request logged to {DB_PATH}")

def get_recent_logs(limit: int = 10) -> list:
    """Returns the most recent audit log entries."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, timestamp, query, status, agents_used,
               rag_sources, news_articles, eval_overall, eval_passed,
               time_seconds, answer_length
        FROM audit_logs
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))

    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def get_stats() -> dict:
    """Returns aggregate stats from the audit log."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            COUNT(*) as total_requests,
            AVG(eval_overall) as avg_score,
            AVG(time_seconds) as avg_time,
            SUM(eval_passed) as passed_count,
            AVG(rag_sources) as avg_rag_sources,
            AVG(news_articles) as avg_news_articles
        FROM audit_logs
    """)

    row = cursor.fetchone()
    conn.close()

    return {
        "total_requests": row[0],
        "avg_eval_score": round(row[1] or 0, 2),
        "avg_time_seconds": round(row[2] or 0, 2),
        "pass_rate": f"{int(row[3] or 0)}/{int(row[0] or 0)}",
        "avg_rag_sources": round(row[4] or 0, 1),
        "avg_news_articles": round(row[5] or 0, 1)
    }

if __name__ == "__main__":
    print("Testing Audit Logger...\n")

    # Log a fake request
    log_request(
        query="Test query",
        status="success",
        orchestrator_result={
            "final_report": "Test report content",
            "metadata": {
                "agents_used": ["rag_agent", "research_agent"],
                "rag_sources": 15,
                "news_articles": 5,
                "total_tokens": 1500,
                "total_time_seconds": 10.2
            }
        },
        eval_result={
            "passed": True,
            "scores": {
                "overall": 8.5,
                "relevance": {"score": 9},
                "consistency": {"score": 8},
                "accuracy": {"score": 8}
            }
        }
    )

    print("\nRecent logs:")
    logs = get_recent_logs(5)
    for log in logs:
        print(f"  [{log['id']}] {log['timestamp'][:19]} | {log['query'][:40]} | score={log['eval_overall']}")

    print("\nStats:")
    stats = get_stats()
    for k, v in stats.items():
        print(f"  {k}: {v}")