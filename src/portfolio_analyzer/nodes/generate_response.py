"""Generate natural language response from analysis results using LLM."""

import json
import logging
import os
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

from portfolio_analyzer.prompts.templates import RESPONSE_SYNTHESIS_PROMPT, SYSTEM_PROMPT
from portfolio_analyzer.state import PortfolioState

load_dotenv()
logger = logging.getLogger(__name__)


def _build_portfolio_summary(state: PortfolioState) -> str:
    """Build a concise portfolio summary string for the LLM."""
    portfolio = state.get("portfolio")
    if not portfolio:
        return "No portfolio loaded"

    lines = []
    for h in portfolio.holdings:
        current = f"₹{h.current_price:,.2f}" if h.current_price else "N/A"
        lines.append(
            f"{h.ticker} ({h.sector or '?'}): {h.quantity} shares @ ₹{h.buy_price:,.2f}, "
            f"Current: {current}, Weight: {portfolio.weights.get(h.ticker, 0)*100:.1f}%"
        )
    return "\n".join(lines)


def _format_results(results: dict) -> str:
    """Format analysis results as a readable string for the LLM.

    Removes chart data (large arrays) to keep prompt size manageable.
    """
    def _clean(obj: Any, depth: int = 0) -> Any:
        if depth > 4:
            return "..."
        if isinstance(obj, dict):
            cleaned = {}
            for k, v in obj.items():
                # Skip large chart data arrays
                if k in ("dates", "drawdown_values", "rolling_excess_return") and isinstance(v, list) and len(v) > 20:
                    cleaned[k] = f"[{len(v)} data points]"
                else:
                    cleaned[k] = _clean(v, depth + 1)
            return cleaned
        if isinstance(obj, list) and len(obj) > 20:
            return f"[{len(obj)} items]"
        return obj

    cleaned = _clean(results)
    return json.dumps(cleaned, indent=2, default=str)


def generate_response_node(state: PortfolioState) -> dict[str, Any]:
    """Synthesize analysis results into a natural language response.

    Takes the raw metric outputs and uses the LLM to create a clear,
    insightful response for the user.
    """
    analysis_results = state.get("analysis_results")
    intent_dict = state.get("intent", {})

    # If this is a general question with no analysis, just answer directly
    if intent_dict.get("primary_intent") == "general":
        llm = ChatGoogleGenerativeAI(model=os.getenv("GEMINI_MODEL", "gemini-1.5-pro"), temperature=0.3)
        response = llm.invoke([
            SystemMessage(content=SYSTEM_PROMPT),
            *state["messages"],
        ])
        return {"messages": [response]}

    if not analysis_results:
        return {
            "messages": [AIMessage(content="I wasn't able to run the analysis. Please make sure your portfolio is loaded and try again.")]
        }

    # Build the synthesis prompt
    portfolio_summary = _build_portfolio_summary(state)
    formatted_results = _format_results(analysis_results)

    synthesis_prompt = RESPONSE_SYNTHESIS_PROMPT.format(
        portfolio_summary=portfolio_summary,
        analysis_results=formatted_results,
    )

    llm = ChatGoogleGenerativeAI(
        model=os.getenv("GEMINI_MODEL", "gemini-1.5-pro"),
        temperature=0.3,
    )

    try:
        response = llm.invoke([
            SystemMessage(content=SYSTEM_PROMPT),
            SystemMessage(content=synthesis_prompt),
            HumanMessage(content=state["messages"][-1].content if state["messages"] else "Analyze my portfolio"),
        ])

        return {"messages": [response]}

    except Exception as e:
        logger.error(f"Response generation failed: {e}")
        # Fallback: return raw results summary
        fallback = "Here are the raw analysis results:\n\n"
        for key, value in analysis_results.items():
            fallback += f"**{key}**:\n```json\n{json.dumps(value, indent=2, default=str)[:500]}\n```\n\n"
        return {"messages": [AIMessage(content=fallback)]}
