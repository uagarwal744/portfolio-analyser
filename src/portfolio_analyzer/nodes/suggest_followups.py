"""Suggest contextual follow-up questions based on the analysis performed."""

import json
import logging
import os
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

from portfolio_analyzer.models.intent import IntentClassification
from portfolio_analyzer.prompts.templates import FOLLOWUP_SUGGESTIONS_PROMPT, SYSTEM_PROMPT
from portfolio_analyzer.state import PortfolioState

load_dotenv()
logger = logging.getLogger(__name__)


def _extract_key_findings(analysis_results: dict) -> str:
    """Extract the most important findings for follow-up context."""
    findings = []

    # Check for concentration warnings
    sector = analysis_results.get("sector", {})
    hidden = sector.get("hidden_concentration", {})
    if hidden and hidden.get("hidden_concentration_detected"):
        for w in hidden.get("warnings", [])[:2]:
            findings.append(w.get("message", ""))

    # Check Sharpe ratio
    risk_data = analysis_results.get("risk", {})
    sharpe = risk_data.get("sharpe_ratio", {})
    if sharpe and "portfolio_sharpe" in sharpe:
        findings.append(f"Portfolio Sharpe ratio: {sharpe['portfolio_sharpe']:.2f}")

    # Check max drawdown
    dd = analysis_results.get("drawdown", {})
    mdd = dd.get("max_drawdown", {})
    if mdd and "portfolio_max_drawdown" in mdd:
        findings.append(f"Max drawdown: {mdd['portfolio_max_drawdown']*100:.1f}%")

    # Check benchmark performance
    bench = analysis_results.get("benchmark", {})
    comp = bench.get("benchmark_comparison", {})
    if comp and "status" in comp:
        findings.append(f"Portfolio is {comp['status']} Nifty 50 by {comp.get('outperformance', 0)*100:.1f}%")

    return "; ".join(findings) if findings else "General portfolio analysis completed"


def suggest_followups_node(state: PortfolioState) -> dict[str, Any]:
    """Generate contextual follow-up question suggestions.

    Uses the LLM to suggest 3-4 questions that naturally follow
    from the analysis just performed.
    """
    portfolio = state.get("portfolio")
    intent_dict = state.get("intent", {})
    analysis_results = state.get("analysis_results", {})

    if not portfolio:
        return {"suggested_questions": [
            "Please upload your portfolio CSV to get started.",
            "What format should my portfolio CSV be in?",
        ]}

    intent = IntentClassification(**intent_dict) if intent_dict else None
    analysis_type = intent.primary_intent.value if intent else "general"
    tickers = ", ".join(portfolio.tickers)
    key_findings = _extract_key_findings(analysis_results)

    prompt = FOLLOWUP_SUGGESTIONS_PROMPT.format(
        tickers=tickers,
        analysis_type=analysis_type,
        key_findings=key_findings,
    )

    llm = ChatGoogleGenerativeAI(
        model=os.getenv("GEMINI_MODEL", "gemini-1.5-pro"),
        temperature=0.7,  # Slightly creative for diverse suggestions
    )

    try:
        response = llm.invoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ])

        # Parse JSON array from response
        content = response.content
        if isinstance(content, list):
            # Handle list of text blocks from Gemini/LangChain
            content = "".join([c.get("text", "") if isinstance(c, dict) else str(c) for c in content])
        content = content.strip()
        # Handle markdown code blocks
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        suggestions = json.loads(content)
        if isinstance(suggestions, list):
            return {"suggested_questions": suggestions[:4]}

    except Exception as e:
        logger.error(f"Follow-up generation failed: {e}")

    # Fallback suggestions based on analysis type
    fallback_map = {
        "risk_analysis": [
            "How does my portfolio compare to Nifty 50?",
            "Show me the maximum drawdown and recovery times",
            "Am I over-exposed to any single sector?",
        ],
        "sector_exposure": [
            "What's the correlation between my holdings?",
            "Run a tail risk analysis on my portfolio",
            "How would a sector correction impact my returns?",
        ],
        "returns": [
            "What's my risk-adjusted performance (Sharpe ratio)?",
            "Compare my returns against Nifty 50",
            "Show me the drawdown history",
        ],
    }
    return {"suggested_questions": fallback_map.get(analysis_type, [
        "What's my overall risk profile?",
        "Show me sector exposure and concentration",
        "How do my holdings correlate with each other?",
    ])}
