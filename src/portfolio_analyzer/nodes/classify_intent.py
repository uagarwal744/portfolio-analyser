"""Classify user intent using LLM structured output."""

import json
import logging
import os
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

from portfolio_analyzer.models.intent import AnalysisIntent, IntentClassification
from portfolio_analyzer.prompts.templates import INTENT_CLASSIFICATION_PROMPT, SYSTEM_PROMPT
from portfolio_analyzer.state import PortfolioState

load_dotenv()
logger = logging.getLogger(__name__)


def classify_intent_node(state: PortfolioState) -> dict[str, Any]:
    """Classify the user's intent for portfolio analysis.

    Uses LLM with structured output to determine what kind of analysis
    the user is requesting.
    """
    portfolio = state.get("portfolio")
    tickers = portfolio.tickers if portfolio else []

    # Get the latest user message
    user_messages = [m for m in state["messages"] if isinstance(m, HumanMessage)]
    if not user_messages:
        return {
            "intent": IntentClassification(
                primary_intent=AnalysisIntent.GENERAL_QUESTION
            ).model_dump()
        }

    latest_msg = user_messages[-1].content

    # Build the classification prompt
    classification_prompt = INTENT_CLASSIFICATION_PROMPT.format(
        tickers=", ".join(tickers) if tickers else "Not yet uploaded"
    )

    llm = ChatGoogleGenerativeAI(
        model=os.getenv("GEMINI_MODEL", "gemini-1.5-pro"),
        temperature=0,
    )

    # Use structured output for guaranteed schema
    structured_llm = llm.with_structured_output(IntentClassification)

    try:
        result = structured_llm.invoke([
            SystemMessage(content=SYSTEM_PROMPT + "\n\n" + classification_prompt),
            HumanMessage(content=latest_msg),
        ])

        logger.info(
            f"Intent classified: {result.primary_intent.value} "
            f"(secondary: {[s.value for s in result.secondary_intents]})"
        )

        return {"intent": result.model_dump()}

    except Exception as e:
        logger.error(f"Intent classification failed: {e}")
        # Fallback to overview if classification fails
        fallback = IntentClassification(
            primary_intent=AnalysisIntent.PORTFOLIO_OVERVIEW
        )
        return {"intent": fallback.model_dump()}
