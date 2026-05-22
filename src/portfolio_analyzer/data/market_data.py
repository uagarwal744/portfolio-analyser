"""yfinance wrapper for historical price data with caching.

Used as the primary source for OHLCV price data needed by metric calculations,
and for Nifty 50 index data (^NSEI) for benchmark comparisons.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

# In-memory cache: (ticker, period_days) → (timestamp, DataFrame)
_price_cache: dict[tuple[str, int], tuple[datetime, pd.DataFrame]] = {}
CACHE_TTL_SECONDS = 300  # 5 minutes


def _cache_key(ticker: str, days: int) -> tuple[str, int]:
    return (ticker.upper(), days)


def _is_cache_valid(key: tuple[str, int]) -> bool:
    if key not in _price_cache:
        return False
    ts, _ = _price_cache[key]
    return (datetime.now() - ts).total_seconds() < CACHE_TTL_SECONDS


def get_price_history(
    ticker: str,
    days: int = 365,
    use_cache: bool = True,
) -> pd.DataFrame:
    """Fetch historical OHLCV data for a ticker.

    Args:
        ticker: Yahoo Finance ticker (e.g., 'RELIANCE.NS' or '^NSEI').
        days: Number of calendar days of history.
        use_cache: Whether to use in-memory cache.

    Returns:
        DataFrame with columns: Open, High, Low, Close, Volume
        indexed by date.
    """
    key = _cache_key(ticker, days)
    if use_cache and _is_cache_valid(key):
        logger.debug(f"Cache hit for {ticker} ({days}d)")
        return _price_cache[key][1].copy()

    logger.info(f"Fetching price history for {ticker} ({days} days)")
    end = datetime.now()
    start = end - timedelta(days=days)

    try:
        data = yf.download(
            ticker,
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            progress=False,
            auto_adjust=True,
        )
        if data.empty:
            logger.warning(f"No price data returned for {ticker}")
            return pd.DataFrame()

        # Flatten multi-level columns if present (yfinance sometimes returns these)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        # Ensure standard column names
        data = data[["Open", "High", "Low", "Close", "Volume"]].copy()
        data.index = pd.to_datetime(data.index)
        data.index.name = "Date"

        if use_cache:
            _price_cache[key] = (datetime.now(), data.copy())

        return data

    except Exception as e:
        logger.error(f"Failed to fetch price data for {ticker}: {e}")
        return pd.DataFrame()


def get_multiple_price_histories(
    tickers: list[str],
    days: int = 365,
) -> dict[str, pd.DataFrame]:
    """Fetch price history for multiple tickers.

    Args:
        tickers: List of Yahoo Finance tickers.
        days: Number of calendar days of history.

    Returns:
        Dict mapping ticker → OHLCV DataFrame.
    """
    result = {}
    for ticker in tickers:
        df = get_price_history(ticker, days)
        if not df.empty:
            result[ticker] = df
        else:
            logger.warning(f"Skipping {ticker} — no data available")
    return result


def get_close_prices(
    tickers: list[str],
    days: int = 365,
) -> pd.DataFrame:
    """Get a DataFrame of closing prices for multiple tickers.

    Args:
        tickers: List of Yahoo Finance tickers.
        days: Number of calendar days of history.

    Returns:
        DataFrame with tickers as columns and dates as index.
    """
    histories = get_multiple_price_histories(tickers, days)
    if not histories:
        return pd.DataFrame()

    close_frames = {}
    for ticker, df in histories.items():
        if "Close" in df.columns:
            close_frames[ticker] = df["Close"]

    if not close_frames:
        return pd.DataFrame()

    combined = pd.DataFrame(close_frames)
    combined = combined.sort_index()
    # Forward-fill missing values (holidays differ across exchanges)
    combined = combined.ffill()
    return combined


def get_nifty50_history(days: int = 365) -> pd.DataFrame:
    """Get Nifty 50 index price history.

    Convenience wrapper for benchmark comparisons.
    """
    return get_price_history("^NSEI", days)


def get_daily_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Calculate daily percentage returns from a price DataFrame.

    Args:
        prices: DataFrame of closing prices (tickers as columns).

    Returns:
        DataFrame of daily returns.
    """
    returns = prices.pct_change().dropna()
    return returns


def clear_cache() -> None:
    """Clear the in-memory price cache."""
    _price_cache.clear()
    logger.info("Price cache cleared")
