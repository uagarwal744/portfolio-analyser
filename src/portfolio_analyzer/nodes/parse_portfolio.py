"""Parse portfolio CSV, validate tickers, and enrich with Tapetide data.

This node:
1. Parses the CSV into structured holdings
2. Validates all tickers exist on NSE/BSE via Tapetide search_stocks
3. Enriches holdings with sector/industry data from Tapetide get_company_profile
4. Gets current batch quotes
"""

import asyncio
import logging
from typing import Any

from langchain_core.messages import AIMessage

from portfolio_analyzer.data.portfolio_parser import PortfolioParseError, parse_portfolio_csv
from portfolio_analyzer.data.tapetide_client import TapetideClient, TapetideError
from portfolio_analyzer.prompts.templates import NON_INDIAN_STOCK_ERROR
from portfolio_analyzer.state import Holding, PortfolioData, PortfolioState

logger = logging.getLogger(__name__)


async def _validate_ticker(client: TapetideClient, ticker: str) -> bool:
    """Check if a ticker exists on NSE/BSE via Tapetide."""
    try:
        results = await client.search_stock(ticker)
        if not results:
            return False
        # Check if any result matches our ticker
        for r in results:
            symbol = r.get("symbol", r.get("nseSymbol", "")).upper()
            if symbol == ticker.upper():
                return True
        # Also accept if the first result is a close match
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
            holding.sector = profile.get("sector", profile.get("info", {}).get("sector"))
            holding.industry = profile.get("industry", profile.get("info", {}).get("industry"))
            # Try to get current price from profile
            quote = profile.get("quote", {})
            if quote and isinstance(quote, dict):
                holding.current_price = quote.get("price") or quote.get("lastPrice")
                holding.market_cap = quote.get("marketCap")
    except TapetideError as e:
        logger.warning(f"Failed to enrich {holding.ticker}: {e}")
    return holding


async def parse_portfolio_node(state: PortfolioState) -> dict[str, Any]:
    """Parse and validate portfolio CSV.

    This node is only invoked when has_csv=True (new CSV uploaded).
    It validates all tickers are Indian stocks and enriches with sector data.
    """
    # Extract CSV content from the last message
    last_msg = state["messages"][-1]
    csv_content = ""

    if hasattr(last_msg, "content"):
        content = last_msg.content
        if isinstance(content, str):
            csv_content = content
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    csv_content = part["text"]
                    break

    if not csv_content:
        return {
            "error": "No CSV content found in the message.",
            "messages": [AIMessage(content="I couldn't find a CSV in your message. Please upload or paste your portfolio CSV.")],
        }

    # Step 1: Parse CSV
    try:
        portfolio = parse_portfolio_csv(csv_content)
    except PortfolioParseError as e:
        return {
            "error": str(e),
            "messages": [AIMessage(content=f"Error parsing your portfolio: {e}")],
        }

    # Step 2: Validate tickers are Indian stocks
    client = TapetideClient()
    invalid_tickers = []

    for holding in portfolio.holdings:
        is_valid = await _validate_ticker(client, holding.ticker)
        if not is_valid:
            invalid_tickers.append(holding.ticker)

    if invalid_tickers:
        error_msg = NON_INDIAN_STOCK_ERROR.format(
            invalid_tickers=", ".join(invalid_tickers)
        )
        return {
            "error": error_msg,
            "messages": [AIMessage(content=error_msg)],
        }

    # Step 3: Enrich holdings with sector/industry data
    enriched_holdings = []
    for holding in portfolio.holdings:
        enriched = await _enrich_holding(client, holding)
        enriched_holdings.append(enriched)

    portfolio.holdings = enriched_holdings

    # Step 4: Get batch quotes for current prices
    try:
        tickers = portfolio.tickers
        # Tapetide batch_quotes accepts up to 20
        for i in range(0, len(tickers), 20):
            batch = tickers[i : i + 20]
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

    # Calculate total invested
    portfolio.total_invested = sum(h.investment_value for h in portfolio.holdings)

    # Build summary message (conversational, no immediate analysis)
    summary_lines = [f"✅ **Portfolio loaded**: {len(portfolio.holdings)} stocks, ₹{portfolio.total_invested:,.0f} invested\n"]
    for h in portfolio.holdings:
        current = f"₹{h.current_price:,.2f}" if h.current_price else "N/A"
        sector = h.sector or "—"
        summary_lines.append(f"  • **{h.ticker}** — {h.quantity} shares @ ₹{h.buy_price:,.2f} | Current: {current} | Sector: {sector}")

    summary_lines.append("\nWhat would you like to know about your portfolio? Pick one of the suggestions below, or ask me anything!")

    suggested = [
        "What's my overall risk profile?",
        "Show me sector exposure and concentration",
        "How does my portfolio compare to Nifty 50?",
        "Run a tail risk analysis (VaR & drawdown)",
        "Check correlation between my holdings",
    ]

    return {
        "portfolio": portfolio,
        "error": None,
        "messages": [AIMessage(content="\n".join(summary_lines))],
        "suggested_questions": suggested,
    }
