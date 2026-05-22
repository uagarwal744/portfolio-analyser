"""Request/response Pydantic models for the API."""

from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Request models ──


class ChatRequest(BaseModel):
    """Request body for the chat endpoint."""

    session_id: str = Field(description="Unique session identifier for conversation continuity.")
    message: str = Field(description="User's natural language message.")


class PortfolioUploadTextRequest(BaseModel):
    """Request body for uploading portfolio as text."""

    session_id: str = Field(description="Unique session identifier.")
    content: str = Field(
        description=(
            "Portfolio as CSV text. Expected columns: ticker, quantity, buy_price. "
            "Optional: buy_date, asset_class."
        )
    )


# ── Response models ──


class HoldingResponse(BaseModel):
    """A single holding in the portfolio."""

    ticker: str
    quantity: float
    buy_price: float
    buy_date: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    current_price: Optional[float] = None
    investment_value: float
    current_value: Optional[float] = None
    weight: float = 0.0


class PortfolioResponse(BaseModel):
    """Parsed portfolio summary."""

    holdings: list[HoldingResponse]
    total_invested: float
    total_current: Optional[float] = None
    num_holdings: int
    sectors: list[str]


class DashboardSignalResponse(BaseModel):
    """A dashboard signal for the frontend to render."""

    signal_type: str
    title: str
    data: dict[str, Any]
    priority: int = 5
    alert_level: Optional[str] = None
    description: Optional[str] = None


class ChatResponse(BaseModel):
    """Response from the chat endpoint."""

    session_id: str
    message: str = Field(description="AI-generated response text.")
    dashboard_signals: list[DashboardSignalResponse] = Field(default_factory=list)
    suggested_questions: list[str] = Field(default_factory=list)
    portfolio_loaded: bool = False
    error: Optional[str] = None


class PortfolioUploadResponse(BaseModel):
    """Response from portfolio upload endpoint."""

    session_id: str
    success: bool
    message: str
    portfolio: Optional[PortfolioResponse] = None
    suggested_questions: list[str] = Field(default_factory=list)
    error: Optional[str] = None


class SessionResponse(BaseModel):
    """Response from session state endpoint."""

    session_id: str
    has_portfolio: bool
    portfolio: Optional[PortfolioResponse] = None
    message_count: int = 0
