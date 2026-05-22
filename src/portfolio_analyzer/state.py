"""Graph state schema for the portfolio analyzer."""

from dataclasses import dataclass, field
from typing import Annotated, Any, Optional

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field
from typing_extensions import TypedDict


class Holding(BaseModel):
    """A single stock holding in the portfolio."""

    ticker: str = Field(description="NSE/BSE ticker symbol (e.g., 'RELIANCE').")
    ticker_ns: str = Field(description="Yahoo Finance ticker (e.g., 'RELIANCE.NS').")
    quantity: float = Field(description="Number of shares held.")
    buy_price: float = Field(description="Average purchase price per share (₹).")
    buy_date: Optional[str] = Field(default=None, description="Purchase date (YYYY-MM-DD).")
    asset_class: Optional[str] = Field(default=None, description="Asset class (equity, debt, etc.).")
    # Enriched fields (filled after Tapetide lookup)
    sector: Optional[str] = Field(default=None, description="Sector from Tapetide.")
    industry: Optional[str] = Field(default=None, description="Industry from Tapetide.")
    current_price: Optional[float] = Field(default=None, description="Latest market price (₹).")
    market_cap: Optional[float] = Field(default=None, description="Market capitalization.")

    @property
    def investment_value(self) -> float:
        """Total invested amount."""
        return self.quantity * self.buy_price

    @property
    def current_value(self) -> Optional[float]:
        """Current market value, if current_price is available."""
        if self.current_price is not None:
            return self.quantity * self.current_price
        return None


class PortfolioData(BaseModel):
    """Parsed and validated portfolio data."""

    holdings: list[Holding] = Field(default_factory=list)
    total_invested: float = Field(default=0.0)
    csv_raw: Optional[str] = Field(default=None, description="Raw CSV content for reference.")

    @property
    def tickers(self) -> list[str]:
        """List of clean ticker symbols."""
        return [h.ticker for h in self.holdings]

    @property
    def tickers_ns(self) -> list[str]:
        """List of Yahoo Finance ticker symbols."""
        return [h.ticker_ns for h in self.holdings]

    @property
    def weights(self) -> dict[str, float]:
        """Portfolio weights by investment value."""
        total = sum(h.investment_value for h in self.holdings)
        if total == 0:
            return {h.ticker: 0.0 for h in self.holdings}
        return {h.ticker: h.investment_value / total for h in self.holdings}

    @property
    def sector_weights(self) -> dict[str, float]:
        """Portfolio weights by sector."""
        sector_totals: dict[str, float] = {}
        total = sum(h.investment_value for h in self.holdings)
        if total == 0:
            return {}
        for h in self.holdings:
            sector = h.sector or "Unknown"
            sector_totals[sector] = sector_totals.get(sector, 0) + h.investment_value
        return {s: v / total for s, v in sector_totals.items()}


class PortfolioState(TypedDict):
    """LangGraph state for the portfolio analyzer conversation."""

    # ── Conversation history ──
    messages: Annotated[list[AnyMessage], add_messages]

    # ── Portfolio data (persists across turns) ──
    portfolio: Optional[PortfolioData]

    # ── Per-turn working data (reset each cycle) ──
    intent: Optional[dict]  # IntentClassification as dict
    market_data: Optional[dict[str, Any]]  # ticker → price DataFrame (serialized)
    analysis_results: Optional[dict[str, Any]]  # metric_name → results
    dashboard_signals: Optional[list[dict]]  # list of DashboardSignal dicts
    suggested_questions: Optional[list[str]]  # follow-up suggestions

    # ── Control flow ──
    error: Optional[str]  # Error message (e.g., non-Indian stock)
