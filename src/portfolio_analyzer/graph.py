"""LangGraph StateGraph definition and compilation.

The graph handles the analysis pipeline only. Portfolio parsing is done
outside the graph (in the API layer). The graph always starts from
classify_intent with a pre-loaded portfolio.
"""

import logging
from typing import Any, Literal

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


# ── Routing functions ──


def route_by_intent(state: PortfolioState) -> str:
    """Route based on classified intent: analysis or direct response."""
    intent_dict = state.get("intent", {})
    primary = intent_dict.get("primary_intent", "general")

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
    graph.add_node("fetch_data", fetch_data_node)
    graph.add_node("execute_analysis", execute_analysis_node)
    graph.add_node("generate_response", generate_response_node)
    graph.add_node("emit_dashboard", emit_dashboard_node)
    graph.add_node("suggest_followups", suggest_followups_node)

    # ── Define edges ──

    # Entry: always classify intent first
    graph.add_edge(START, "classify_intent")

    # After intent classification: route to analysis or direct response
    graph.add_conditional_edges(
        "classify_intent",
        route_by_intent,
        {
            "fetch_data": "fetch_data",
            "generate_response": "generate_response",
        },
    )

    # Linear flow: fetch → analyze → respond → dashboard → followups
    graph.add_edge("fetch_data", "execute_analysis")
    graph.add_edge("execute_analysis", "generate_response")
    graph.add_edge("generate_response", "emit_dashboard")
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
