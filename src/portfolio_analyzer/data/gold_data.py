"""Gold price data reader for benchmark comparison.

Reads historical GOLDM spot prices from the bundled NSE CSV file
and returns a pandas Series suitable for benchmark comparisons.
"""

import logging
import os
from datetime import datetime

import pandas as pd

logger = logging.getLogger(__name__)

_GOLD_CSV_PATH = os.path.join(os.path.dirname(__file__), "gold_historical.csv")

# In-memory cache
_gold_cache: pd.Series | None = None


def get_gold_price_history() -> pd.Series:
    """Load gold spot prices from the bundled CSV.

    Returns:
        pd.Series indexed by datetime with daily gold prices (₹ per 10g).
        Uses the average of Session 1 and Session 2 spot prices.
    """
    global _gold_cache
    if _gold_cache is not None:
        return _gold_cache.copy()

    if not os.path.exists(_GOLD_CSV_PATH):
        logger.error(f"Gold CSV not found at {_GOLD_CSV_PATH}")
        return pd.Series(dtype=float)

    try:
        # The CSV has unusual headers with newlines and whitespace
        df = pd.read_csv(_GOLD_CSV_PATH, skipinitialspace=True)

        # Normalize column names
        df.columns = [c.strip().strip('"').strip() for c in df.columns]

        # Identify the date and price columns by position (robust to header weirdness)
        # Columns: SYMBOL, QUOTATION VALUE, UPDATED DATE, SESSION 1 PRICE, SESSION 2 PRICE, POLLED INFO
        if len(df.columns) < 5:
            logger.error(f"Gold CSV has unexpected columns: {list(df.columns)}")
            return pd.Series(dtype=float)

        date_col = df.columns[2]
        session1_col = df.columns[3]
        session2_col = df.columns[4]

        # Parse dates (DD-MMM-YYYY format, e.g., "22-MAY-2026")
        df["date"] = pd.to_datetime(df[date_col].str.strip().str.strip('"'), format="%d-%b-%Y")

        # Parse prices: remove quotes, commas, and convert to float
        def _parse_price(val):
            if pd.isna(val):
                return None
            cleaned = str(val).strip().strip('"').replace(",", "")
            try:
                return float(cleaned)
            except ValueError:
                return None

        df["price1"] = df[session1_col].apply(_parse_price)
        df["price2"] = df[session2_col].apply(_parse_price)

        # Average of both sessions
        df["price"] = df[["price1", "price2"]].mean(axis=1)

        # Drop rows with no valid price
        df = df.dropna(subset=["price"])

        # Sort chronologically and create the series
        df = df.sort_values("date")
        series = pd.Series(df["price"].values, index=df["date"].values, name="Gold")
        series.index = pd.to_datetime(series.index)
        series.index.name = "Date"

        _gold_cache = series
        logger.info(f"Loaded {len(series)} gold price records ({series.index[0].date()} to {series.index[-1].date()})")
        return series.copy()

    except Exception as e:
        logger.error(f"Failed to parse gold CSV: {e}")
        return pd.Series(dtype=float)


def clear_gold_cache() -> None:
    """Clear the gold price cache."""
    global _gold_cache
    _gold_cache = None
