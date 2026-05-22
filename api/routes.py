"""FastAPI routes for the portfolio analyzer.

Portfolio upload is handled directly (no LangGraph).
Chat messages are routed through the LangGraph pipeline.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from langchain_core.messages import HumanMessage

from api.schemas import (
    ChatRequest,
    ChatResponse,
    HoldingResponse,
    PortfolioResponse,
    PortfolioUploadResponse,
    PortfolioUploadTextRequest,
    SessionResponse,
)
from portfolio_analyzer.data.portfolio_parser import PortfolioParseError, parse_portfolio_csv
from portfolio_analyzer.data.tapetide_client import TapetideClient, TapetideError
from portfolio_analyzer.graph import get_graph
from portfolio_analyzer.state import Holding, PortfolioData

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["portfolio"])

# ── In-memory session store for parsed portfolios ──
# Keyed by session_id → PortfolioData
_portfolio_store: dict[str, PortfolioData] = {}

DEFAULT_SUGGESTIONS = [
    "What's my overall risk profile?",
    "Show me sector exposure and concentration",
    "How does my portfolio compare to Nifty 50?",
    "Run a tail risk analysis (VaR & drawdown)",
    "Check correlation between my holdings",
]


def _portfolio_to_response(portfolio: PortfolioData) -> PortfolioResponse:
    """Convert a PortfolioData to a PortfolioResponse for the frontend."""
    weights = portfolio.weights
    holdings = []
    sectors = set()
    total_current = 0.0

    for h in portfolio.holdings:
        if h.sector:
            sectors.add(h.sector)
        if h.current_value:
            total_current += h.current_value

        holdings.append(
            HoldingResponse(
                ticker=h.ticker,
                quantity=h.quantity,
                buy_price=h.buy_price,
                buy_date=h.buy_date,
                sector=h.sector,
                industry=h.industry,
                current_price=h.current_price,
                investment_value=h.investment_value,
                current_value=h.current_value,
                weight=weights.get(h.ticker, 0.0),
            )
        )

    return PortfolioResponse(
        holdings=holdings,
        total_invested=portfolio.total_invested,
        total_current=total_current if total_current > 0 else None,
        num_holdings=len(holdings),
        sectors=list(sectors),
    )


def _build_summary_message(portfolio: PortfolioData) -> str:
    """Build a human-friendly portfolio summary message."""
    lines = [f"✅ **Portfolio loaded**: {len(portfolio.holdings)} stocks, ₹{portfolio.total_invested:,.0f} invested\n"]
    for h in portfolio.holdings:
        current = f"₹{h.current_price:,.2f}" if h.current_price else "N/A"
        sector = h.sector or "—"
        lines.append(f"  • **{h.ticker}** — {h.quantity} shares @ ₹{h.buy_price:,.2f} | Current: {current} | Sector: {sector}")

    lines.append("\nWhat would you like to know about your portfolio? Pick one of the suggestions below, or ask me anything!")
    return "\n".join(lines)


# ── Portfolio upload (no LangGraph) ──


async def _validate_ticker(client: TapetideClient, ticker: str) -> bool:
    """Check if a ticker exists on NSE/BSE via Tapetide."""
    try:
        results = await client.search_stock(ticker)
        if not results:
            return False
        for r in results:
            symbol = r.get("symbol", r.get("nseSymbol", r.get("nse_symbol", ""))).upper()
            if symbol == ticker.upper():
                return True
        # Accept if first result is a close match
        if results and isinstance(results[0], dict):
            return True
        return False
    except TapetideError:
        logger.warning(f"Tapetide search failed for {ticker}, assuming valid")
        return True


async def _enrich_holding(client: TapetideClient, holding: Holding) -> Holding:
    """Enrich a holding with sector/industry data from Tapetide."""
    try:
        profile = await client.get_company_profile(holding.ticker)
        if isinstance(profile, dict):
            data = profile.get("data", profile)
            holding.sector = data.get("sector", data.get("info", {}).get("sector"))
            holding.industry = data.get("industry", data.get("info", {}).get("industry"))
            quote = data.get("quote", {})
            if quote and isinstance(quote, dict):
                holding.current_price = quote.get("price") or quote.get("lastPrice")
                holding.market_cap = quote.get("marketCap")
    except TapetideError as e:
        logger.warning(f"Failed to enrich {holding.ticker}: {e}")
    return holding


async def _process_upload(session_id: str, csv_content: str) -> PortfolioUploadResponse:
    """Parse, validate, and enrich portfolio CSV — entirely outside LangGraph."""
    try:
        # Step 1: Parse CSV
        portfolio = parse_portfolio_csv(csv_content)
    except PortfolioParseError as e:
        return PortfolioUploadResponse(
            session_id=session_id, success=False,
            message=f"Error parsing your portfolio: {e}", error=str(e),
        )

    # Step 2: Validate tickers are Indian stocks
    client = TapetideClient()
    invalid_tickers = []
    for holding in portfolio.holdings:
        is_valid = await _validate_ticker(client, holding.ticker)
        if not is_valid:
            invalid_tickers.append(holding.ticker)

    if invalid_tickers:
        error_msg = (
            f"The following tickers are not valid Indian stocks: {', '.join(invalid_tickers)}. "
            "Only NSE/BSE listed stocks are supported."
        )
        return PortfolioUploadResponse(
            session_id=session_id, success=False,
            message=error_msg, error=error_msg,
        )

    # Step 3: Enrich holdings with sector/industry data
    for i, holding in enumerate(portfolio.holdings):
        portfolio.holdings[i] = await _enrich_holding(client, holding)

    # Step 4: Get batch quotes for current prices
    try:
        tickers = portfolio.tickers
        for batch_start in range(0, len(tickers), 20):
            batch = tickers[batch_start: batch_start + 20]
            quotes = await client.get_batch_quotes(batch)
            if isinstance(quotes, list):
                for q in quotes:
                    symbol = q.get("symbol", "").upper()
                    for h in portfolio.holdings:
                        if h.ticker == symbol and h.current_price is None:
                            h.current_price = q.get("price") or q.get("lastPrice")
                            h.market_cap = q.get("marketCap")
    except TapetideError as e:
        logger.warning(f"Batch quotes failed: {e}")

    portfolio.total_invested = sum(h.investment_value for h in portfolio.holdings)

    # Step 5: Store in session and return
    _portfolio_store[session_id] = portfolio
    logger.info(f"Portfolio stored for session {session_id}: {len(portfolio.holdings)} holdings")

    return PortfolioUploadResponse(
        session_id=session_id,
        success=True,
        message=_build_summary_message(portfolio),
        portfolio=_portfolio_to_response(portfolio),
        suggested_questions=DEFAULT_SUGGESTIONS,
    )


@router.post("/portfolio/upload/file", response_model=PortfolioUploadResponse)
async def upload_portfolio_file(
    session_id: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
):
    """Upload a portfolio CSV file."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    content = await file.read()
    text_content = content.decode("utf-8")
    return await _process_upload(session_id, text_content)


@router.post("/portfolio/upload/text", response_model=PortfolioUploadResponse)
async def upload_portfolio_text(request: PortfolioUploadTextRequest):
    """Upload a portfolio as raw CSV text."""
    return await _process_upload(request.session_id, request.content)


# ── Chat (LangGraph) ──


def _coerce_message(raw) -> str:
    """Safely extract a string from LangChain message content."""
    if isinstance(raw, list):
        return "".join([c.get("text", "") if isinstance(c, dict) else str(c) for c in raw])
    return str(raw)


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Process a user query against their portfolio via LangGraph."""
    graph = get_graph()
    config = {"configurable": {"thread_id": request.session_id}}

    # Retrieve portfolio from session store
    portfolio = _portfolio_store.get(request.session_id)
    if not portfolio:
        return ChatResponse(
            session_id=request.session_id,
            message="Please upload your portfolio first before asking questions.",
            portfolio_loaded=False,
        )

    try:
        result = await graph.ainvoke(
            {
                "messages": [HumanMessage(content=request.message)],
                "portfolio": portfolio,
            },
            config=config,
        )

        error = result.get("error")
        messages = result.get("messages", [])
        ai_response = _coerce_message(messages[-1].content) if messages else "No response generated."

        return ChatResponse(
            session_id=request.session_id,
            message=ai_response,
            dashboard_signals=result.get("dashboard_signals", []),
            suggested_questions=result.get("suggested_questions", []),
            portfolio_loaded=True,
            error=error,
        )

    except Exception as e:
        logger.error(f"Chat failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ── Session info ──


@router.get("/session/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """Get the current state of a session."""
    portfolio = _portfolio_store.get(session_id)
    if not portfolio:
        return SessionResponse(session_id=session_id, has_portfolio=False)

    return SessionResponse(
        session_id=session_id,
        has_portfolio=True,
        portfolio=_portfolio_to_response(portfolio),
        message_count=0,
    )
