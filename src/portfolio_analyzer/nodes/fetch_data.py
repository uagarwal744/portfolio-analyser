"""Fetch market data from yfinance and Tapetide before analysis."""

import logging
from typing import Any

from portfolio_analyzer.data.market_data import get_close_prices, get_nifty50_history
from portfolio_analyzer.models.intent import IntentClassification
from portfolio_analyzer.state import PortfolioState

logger = logging.getLogger(__name__)

# How many calendar days of data per time period mention
TIME_PERIOD_MAP = {
    "1 month": 45,
    "1m": 45,
    "3 months": 120,
    "3m": 120,
    "6 months": 220,
    "6m": 220,
    "1 year": 400,
    "1y": 400,
    "2 years": 780,
    "2y": 780,
    "3 years": 1150,
    "3y": 1150,
    "5 years": 1900,
    "5y": 1900,
}


def _resolve_days(time_period: str | None) -> int:
    """Convert a time period string to calendar days."""
    if not time_period:
        return 400  # Default ~1 year
    tp = time_period.lower().strip()
    for key, days in TIME_PERIOD_MAP.items():
        if key in tp:
            return days
    return 400


def fetch_data_node(state: PortfolioState) -> dict[str, Any]:
    """Fetch price data from yfinance for the portfolio holdings.

    This node runs BEFORE execute_analysis to ensure all price data
    is available for metric calculations.
    """
    portfolio = state.get("portfolio")
    intent_dict = state.get("intent", {})

    if not portfolio or not portfolio.holdings:
        return {"market_data": None, "error": "No portfolio loaded"}

    intent = IntentClassification(**intent_dict) if intent_dict else None
    time_period = intent.time_period if intent else None
    days = _resolve_days(time_period)

    logger.info(f"Fetching {days} days of data for {len(portfolio.tickers_ns)} tickers")

    # Fetch close prices for all holdings
    tickers_ns = portfolio.tickers_ns
    close_prices = get_close_prices(tickers_ns, days=days)

    if close_prices.empty:
        return {"market_data": None, "error": "Could not fetch price data from yfinance"}

    # Fetch Nifty 50 benchmark data
    nifty = get_nifty50_history(days=days)
    nifty_close = None
    if not nifty.empty and "Close" in nifty.columns:
        nifty_close = nifty["Close"]

    # Serialize to dict for state storage
    market_data = {
        "close_prices": close_prices.to_json(),
        "columns": list(close_prices.columns),
        "nifty50": nifty_close.to_json() if nifty_close is not None else None,
        "days_fetched": days,
        "date_range": {
            "start": str(close_prices.index[0].date()),
            "end": str(close_prices.index[-1].date()),
        },
    }

    logger.info(
        f"Fetched data: {len(close_prices)} rows, "
        f"{len(close_prices.columns)} tickers, "
        f"range: {market_data['date_range']['start']} to {market_data['date_range']['end']}"
    )

    return {"market_data": market_data}
