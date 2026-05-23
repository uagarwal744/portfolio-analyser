"""Intent classification and analysis type models."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class AnalysisIntent(str, Enum):
    """Categories of portfolio analysis the system can perform."""

    RISK_ANALYSIS = "risk_analysis"
    TAIL_RISK = "tail_risk"
    CORRELATION = "correlation"
    BENCHMARK_COMPARISON = "benchmark"
    RETURNS_ANALYSIS = "returns"
    SECTOR_EXPOSURE = "sector_exposure"
    PORTFOLIO_OVERVIEW = "overview"
    GENERAL_QUESTION = "general"
    UNSUPPORTED = "unsupported"
    END_SESSION = "end_session"


# Mapping from intent to the set of metric modules to invoke
INTENT_METRIC_MAP: dict[AnalysisIntent, list[str]] = {
    AnalysisIntent.RISK_ANALYSIS: ["risk", "drawdown"],
    AnalysisIntent.TAIL_RISK: ["var", "drawdown"],
    AnalysisIntent.CORRELATION: ["correlation"],
    AnalysisIntent.BENCHMARK_COMPARISON: ["benchmark", "returns"],
    AnalysisIntent.RETURNS_ANALYSIS: ["returns"],
    AnalysisIntent.SECTOR_EXPOSURE: ["sector", "correlation"],
    AnalysisIntent.PORTFOLIO_OVERVIEW: [
        "returns",
        "risk",
        "drawdown",
        "var",
        "correlation",
        "benchmark",
        "sector",
    ],
    AnalysisIntent.GENERAL_QUESTION: [],
    AnalysisIntent.UNSUPPORTED: [],
    AnalysisIntent.END_SESSION: [],
}


class IntentClassification(BaseModel):
    """Structured output from the intent classification LLM call."""

    primary_intent: AnalysisIntent = Field(
        description="The main type of analysis the user is requesting."
    )
    secondary_intents: list[AnalysisIntent] = Field(
        default_factory=list,
        description="Additional analysis types implied by the query.",
    )
    specific_tickers: list[str] = Field(
        default_factory=list,
        description="Specific stock tickers mentioned in the query (e.g., 'RELIANCE', 'TCS').",
    )
    time_period: Optional[str] = Field(
        default=None,
        description="Time period mentioned (e.g., 'last 1 year', 'since purchase', '6 months').",
    )
    benchmark_requested: Optional[str] = Field(
        default=None,
        description="Benchmark index requested (e.g., 'nifty50', 'banknifty'). Defaults to Nifty 50.",
    )

    @property
    def all_intents(self) -> list[AnalysisIntent]:
        """Return primary + secondary intents, deduplicated."""
        seen = {self.primary_intent}
        result = [self.primary_intent]
        for intent in self.secondary_intents:
            if intent not in seen:
                seen.add(intent)
                result.append(intent)
        return result

    @property
    def required_metrics(self) -> list[str]:
        """Return deduplicated list of metric modules needed for all intents."""
        seen: set[str] = set()
        result: list[str] = []
        for intent in self.all_intents:
            for metric in INTENT_METRIC_MAP.get(intent, []):
                if metric not in seen:
                    seen.add(metric)
                    result.append(metric)
        return result
