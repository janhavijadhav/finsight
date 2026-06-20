import streamlit as st
import sys
from pathlib import Path
import json
import plotly.graph_objects as go

sys.path.append(str(Path(__file__).parent / "agents"))
sys.path.append(str(Path(__file__).parent / "rag"))
sys.path.append(str(Path(__file__).parent / "evaluation"))

from orchestrator import orchestrator
from audit_logger import get_recent_logs, get_stats

# Page config
st.set_page_config(
    page_title="FinSight",
    page_icon="📊",
    layout="wide"
)

# Sidebar
with st.sidebar:
    st.title("📊 FinSight")
    st.caption("Multi-Agent Financial Research System")
    st.divider()

    st.subheader("Supported Companies")
    companies = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "JPM", "META"]
    for c in companies:
        st.markdown(f"• {c}")

    st.divider()
    st.subheader("System Info")
    st.markdown("**LLM:** LLaMA 3.3 70B via Groq")
    st.markdown("**Vector DB:** ChromaDB")
    st.markdown("**Graph DB:** NetworkX")
    st.markdown("**Data:** SEC 10-K Filings 2025")

# Main tabs
tab1, tab2, tab3 = st.tabs(["🔍 Research", "📋 Audit Log", "📈 Analytics"])

# Tab 1: Research
with tab1:
    st.title("Financial Research Assistant")
    st.caption("Powered by SEC 10-K filings + live news + multi-agent AI")

    st.subheader("Try an example query:")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Apple China risks"):
            st.session_state.query = "What are Apple's biggest risks related to China?"
    with col2:
        if st.button("MSFT vs NVDA AI"):
            st.session_state.query = "Compare Microsoft and Nvidia's AI strategies and risks"
    with col3:
        if st.button("Tesla outlook"):
            st.session_state.query = "What does Tesla say about its growth strategy and risks?"

    query = st.text_area(
        "Or type your own research question:",
        value=st.session_state.get("query", ""),
        height=80,
        placeholder="e.g. What are JPMorgan's biggest regulatory risks?"
    )

    if st.button("🔍 Research", type="primary", use_container_width=True):
        if not query.strip():
            st.warning("Please enter a research question.")
        else:
            with st.spinner("Running multi-agent research pipeline..."):
                progress = st.empty()
                progress.info("🧠 Planning Agent: Breaking down your query...")
                result = orchestrator(query)
                progress.empty()

            if result["status"] == "success":
                eval_scores = result["evaluation"]["scores"]
                m1, m2, m3, m4, m5 = st.columns(5)
                m1.metric("Overall Score", str(eval_scores["overall"]) + "/10")
                m2.metric("Relevance", str(eval_scores["relevance"]["score"]) + "/10")
                m3.metric("Consistency", str(eval_scores["consistency"]["score"]) + "/10")
                m4.metric("Accuracy", str(eval_scores["accuracy"]["score"]) + "/10")
                m5.metric("Time", str(round(result["metadata"]["total_time_seconds"], 1)) + "s")

                st.divider()

                st.subheader("📄 Research Report")
                st.markdown(result["final_report"])

                st.divider()

                col_a, col_b = st.columns(2)

                with col_a:
                    st.subheader("🔗 Sources Used")
                    st.markdown("**SEC Filing chunks:** " + str(result["metadata"]["rag_sources"]))
                    st.markdown("**News articles:** " + str(result["metadata"]["news_articles"]))
                    st.markdown("**Companies:** " + ", ".join(result["metadata"]["companies_researched"]))

                with col_b:
                    st.subheader("🤖 Agent Trace")
                    plan = result.get("plan", {})
                    for task in plan.get("research_tasks", []):
                        agent = task["agent"].replace("_", " ").title()
                        st.markdown("**" + agent + ":** " + task["instruction"][:100] + "...")

                with st.expander("📊 Evaluation Details"):
                    for metric, data in eval_scores.items():
                        if isinstance(data, dict):
                            st.markdown("**" + metric.capitalize() + "** (" + str(data["score"]) + "/10): " + data["reason"])

            else:
                st.error("Request failed: " + str(result.get("error", "Unknown error")))

# Tab 2: Audit Log
with tab2:
    st.title("Audit Log")
    st.caption("Every request logged with full reasoning trace")

    if st.button("🔄 Refresh"):
        st.rerun()

    logs = get_recent_logs(20)

    if not logs:
        st.info("No requests logged yet. Run a research query first.")
    else:
        for log in logs:
            passed = "✅" if log["eval_passed"] else "❌"
            score = log["eval_overall"] or 0
            with st.expander(
                passed + " [" + str(log["id"]) + "] " + log["timestamp"][:19] + " — " + log["query"][:60] + " — Score: " + str(score) + "/10"
            ):
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Eval Score", str(score) + "/10")
                col2.metric("RAG Sources", log["rag_sources"])
                col3.metric("News Articles", log["news_articles"])
                col4.metric("Time", str(round(log["time_seconds"], 1)) + "s")

                agents = json.loads(log["agents_used"]) if log["agents_used"] else []
                st.markdown("**Agents used:** " + ", ".join(agents))
                st.markdown("**Status:** " + log["status"])

# Tab 3: Analytics
with tab3:
    st.title("Analytics Dashboard")
    st.caption("Aggregate performance metrics across all requests")

    stats = get_stats()

    if stats["total_requests"] == 0:
        st.info("No data yet. Run some research queries first.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Requests", stats["total_requests"])
        c2.metric("Avg Eval Score", str(stats["avg_eval_score"]) + "/10")
        c3.metric("Pass Rate", stats["pass_rate"])
        c4.metric("Avg Time", str(stats["avg_time_seconds"]) + "s")

        st.divider()

        logs = get_recent_logs(50)
        if logs:
            timestamps = [l["timestamp"][:19] for l in reversed(logs)]
            scores = [l["eval_overall"] or 0 for l in reversed(logs)]

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=timestamps,
                y=scores,
                mode="lines+markers",
                name="Eval Score",
                line=dict(color="#00cc88", width=2),
                marker=dict(size=8)
            ))
            fig.add_hline(
                y=6.0,
                line_dash="dash",
                line_color="red",
                annotation_text="Pass threshold (6.0)"
            )
            fig.update_layout(
                title="Evaluation Scores Over Time",
                xaxis_title="Request Time",
                yaxis_title="Score (out of 10)",
                yaxis_range=[0, 10],
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig, use_container_width=True)

            avg_rag = stats["avg_rag_sources"]
            avg_news = stats["avg_news_articles"]

            fig2 = go.Figure(go.Bar(
                x=["SEC Filing Chunks", "News Articles"],
                y=[avg_rag, avg_news],
                marker_color=["#4B8BBE", "#FFD43B"]
            ))
            fig2.update_layout(
                title="Average Sources Per Query",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig2, use_container_width=True)