"""LangGraph StateGraph definition and compilation.

The graph handles the analysis pipeline only. Portfolio parsing is done
outside the graph (in the API layer). The graph always starts from
classify_intent with a pre-loaded portfolio.

Termination conditions:
  - UNSUPPORTED intent  → reject_node  → END
  - END_SESSION intent  → farewell_node → END
  - GENERAL_QUESTION    → generate_response → END  (short-circuit, no metrics)
  - Analysis intents    → fetch → analyze → respond → dashboard → followups → END
  - recursion_limit     → hard stop after MAX_GRAPH_STEPS to prevent infinite loops
"""

import logging
from typing import Any

from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from portfolio_analyzer.models.intent import AnalysisIntent
from portfolio_analyzer.nodes.classify_intent import classify_intent_node
from portfolio_analyzer.nodes.emit_dashboard import emit_dashboard_node
from portfolio_analyzer.nodes.execute_analysis import execute_analysis_node
from portfolio_analyzer.nodes.fetch_data import fetch_data_node
from portfolio_analyzer.nodes.generate_response import generate_response_node
from portfolio_analyzer.nodes.suggest_followups import suggest_followups_node
from portfolio_analyzer.state import PortfolioState

logger = logging.getLogger(__name__)

# Hard limit on graph steps to prevent infinite loops (safety net)
MAX_GRAPH_STEPS = 25


# ── Lightweight termination nodes ──


def reject_node(state: PortfolioState) -> dict[str, Any]:
    """Respond to unsupported / off-topic queries and terminate."""
    msg = (
        "🚫 Sorry, I can only help with **Indian stock market portfolio analysis** — "
        "things like risk, returns, benchmarks, and sector exposure.\n\n"
        "Please try a finance-related question, for example:\n"
        "  • *\"What's my overall risk profile?\"*\n"
        "  • *\"Compare my portfolio to Nifty 50\"*"
    )
    return {"messages": [AIMessage(content=msg)]}


def farewell_node(state: PortfolioState) -> dict[str, Any]:
    """Send a friendly goodbye message and terminate."""
    msg = (
        "👋 Thanks for using Portfolio Analyzer! "
        "Your session data is still saved — come back anytime to continue where you left off. "
        "Happy investing! 📈"
    )
    return {"messages": [AIMessage(content=msg)]}


# ── Routing functions ──


def route_by_intent(state: PortfolioState) -> str:
    """Route based on classified intent."""
    intent_dict = state.get("intent", {})
    primary = intent_dict.get("primary_intent", "general")

    if primary == AnalysisIntent.UNSUPPORTED.value:
        return "reject"

    if primary == AnalysisIntent.END_SESSION.value:
        return "farewell"

    if primary == AnalysisIntent.GENERAL_QUESTION.value:
        return "generate_response"

    return "fetch_data"


# ── Graph builder ──


def build_portfolio_graph(checkpointer=None):
    """Build and compile the portfolio analyzer StateGraph.

    Args:
        checkpointer: LangGraph checkpointer for state persistence.
                       Defaults to MemorySaver (in-memory).

    Returns:
        Compiled StateGraph ready to invoke.
    """
    if checkpointer is None:
        checkpointer = MemorySaver()

    graph = StateGraph(PortfolioState)

    # ── Register nodes ──
    graph.add_node("classify_intent", classify_intent_node)
    graph.add_node("reject", reject_node)
    graph.add_node("farewell", farewell_node)
    graph.add_node("fetch_data", fetch_data_node)
    graph.add_node("execute_analysis", execute_analysis_node)
    graph.add_node("generate_response", generate_response_node)
    graph.add_node("emit_dashboard", emit_dashboard_node)
    graph.add_node("suggest_followups", suggest_followups_node)

    # ── Define edges ──

    # Entry: always classify intent first
    graph.add_edge(START, "classify_intent")

    # After intent classification: route by intent type
    graph.add_conditional_edges(
        "classify_intent",
        route_by_intent,
        {
            "reject": "reject",
            "farewell": "farewell",
            "generate_response": "generate_response",
            "fetch_data": "fetch_data",
        },
    )

    # Termination paths (short-circuit → END)
    graph.add_edge("reject", END)
    graph.add_edge("farewell", END)

    # General question path (short-circuit → END, no dashboard/followups needed)
    graph.add_edge("generate_response", END)

    # Analysis flow: fetch → analyze → respond → dashboard → followups → END
    graph.add_edge("fetch_data", "execute_analysis")
    graph.add_edge("execute_analysis", "generate_response_full")

    # We need a separate node name for the full-flow response, since
    # generate_response in the general path goes to END but in the
    # analysis path it goes to emit_dashboard. LangGraph doesn't allow
    # the same node to have conditional out-edges AND a fixed out-edge.
    # Solution: reuse the same function under a different node name.
    graph.add_node("generate_response_full", generate_response_node)
    graph.add_edge("generate_response_full", "emit_dashboard")
    graph.add_edge("emit_dashboard", "suggest_followups")
    graph.add_edge("suggest_followups", END)

    # Compile with checkpointer
    compiled = graph.compile(checkpointer=checkpointer)
    logger.info("Portfolio analyzer graph compiled successfully")

    return compiled


# ── Convenience function for quick usage ──

_default_graph = None


def get_graph():
    """Get or create the default portfolio analyzer graph.

    Lazily initializes a singleton graph instance.
    """
    global _default_graph
    if _default_graph is None:
        _default_graph = build_portfolio_graph()
    return _default_graph
