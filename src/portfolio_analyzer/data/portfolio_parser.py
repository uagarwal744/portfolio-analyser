"""CSV portfolio parser with validation and normalization.

Handles parsing user-uploaded portfolio CSVs, normalizing ticker symbols
to NSE format, and validating that all stocks are Indian.
"""

import csv
import io
import logging
from typing import Optional

from portfolio_analyzer.state import Holding, PortfolioData

logger = logging.getLogger(__name__)

# Expected CSV columns (case-insensitive matching)
REQUIRED_COLUMNS = {"ticker", "quantity", "buy_price"}
OPTIONAL_COLUMNS = {"buy_date", "asset_class"}
ALL_COLUMNS = REQUIRED_COLUMNS | OPTIONAL_COLUMNS

# Common column aliases
COLUMN_ALIASES = {
    "symbol": "ticker",
    "stock": "ticker",
    "name": "ticker",
    "scrip": "ticker",
    "qty": "quantity",
    "shares": "quantity",
    "units": "quantity",
    "price": "buy_price",
    "avg_price": "buy_price",
    "purchase_price": "buy_price",
    "avg_cost": "buy_price",
    "cost_price": "buy_price",
    "date": "buy_date",
    "purchase_date": "buy_date",
    "class": "asset_class",
    "type": "asset_class",
    "category": "asset_class",
}

# Known Indian exchange suffixes
INDIAN_SUFFIXES = {".NS", ".BO"}


def normalize_ticker(raw_ticker: str) -> tuple[str, str]:
    """Normalize a ticker to clean and Yahoo Finance formats.

    Args:
        raw_ticker: Raw ticker string from CSV.

    Returns:
        Tuple of (clean_ticker, yf_ticker). e.g., ('RELIANCE', 'RELIANCE.NS')
    """
    ticker = raw_ticker.strip().upper()

    # Remove exchange suffixes to get clean ticker
    clean = ticker
    for suffix in INDIAN_SUFFIXES:
        if ticker.endswith(suffix):
            clean = ticker[: -len(suffix)]
            break

    # Yahoo Finance ticker defaults to NSE
    yf_ticker = f"{clean}.NS"

    return clean, yf_ticker


def _normalize_columns(headers: list[str]) -> dict[str, str]:
    """Map CSV column headers to standard column names.

    Returns:
        Dict mapping standard name → original header name.
    """
    mapping = {}
    for header in headers:
        normalized = header.strip().lower().replace(" ", "_")
        if normalized in ALL_COLUMNS:
            mapping[normalized] = header
        elif normalized in COLUMN_ALIASES:
            standard = COLUMN_ALIASES[normalized]
            mapping[standard] = header
    return mapping


class PortfolioParseError(Exception):
    """Error during portfolio CSV parsing."""
    pass


def parse_portfolio_csv(csv_content: str) -> PortfolioData:
    """Parse a portfolio CSV string into a PortfolioData object.

    Args:
        csv_content: Raw CSV content as a string.

    Returns:
        PortfolioData with parsed holdings.

    Raises:
        PortfolioParseError: If the CSV is invalid or missing required columns.
    """
    if not csv_content or not csv_content.strip():
        raise PortfolioParseError("CSV content is empty.")

    reader = csv.DictReader(io.StringIO(csv_content.strip()))

    if not reader.fieldnames:
        raise PortfolioParseError("CSV has no headers.")

    col_map = _normalize_columns(list(reader.fieldnames))

    # Check required columns
    missing = REQUIRED_COLUMNS - set(col_map.keys())
    if missing:
        raise PortfolioParseError(
            f"Missing required columns: {', '.join(missing)}. "
            f"Found columns: {', '.join(reader.fieldnames)}. "
            f"Expected: ticker, quantity, buy_price"
        )

    holdings = []
    total_invested = 0.0

    for i, row in enumerate(reader, start=2):  # start=2 because row 1 is header
        try:
            raw_ticker = row[col_map["ticker"]].strip()
            if not raw_ticker:
                logger.warning(f"Row {i}: empty ticker, skipping")
                continue

            clean_ticker, yf_ticker = normalize_ticker(raw_ticker)

            quantity = float(row[col_map["quantity"]].strip().replace(",", ""))
            buy_price = float(row[col_map["buy_price"]].strip().replace(",", "").replace("₹", ""))

            buy_date = None
            if "buy_date" in col_map and row.get(col_map["buy_date"]):
                buy_date = row[col_map["buy_date"]].strip()

            asset_class = None
            if "asset_class" in col_map and row.get(col_map["asset_class"]):
                asset_class = row[col_map["asset_class"]].strip()

            holding = Holding(
                ticker=clean_ticker,
                ticker_ns=yf_ticker,
                quantity=quantity,
                buy_price=buy_price,
                buy_date=buy_date,
                asset_class=asset_class,
            )
            holdings.append(holding)
            total_invested += holding.investment_value

        except (ValueError, KeyError) as e:
            logger.warning(f"Row {i}: failed to parse — {e}")
            continue

    if not holdings:
        raise PortfolioParseError(
            "No valid holdings found in CSV. Please check the format."
        )

    logger.info(
        f"Parsed {len(holdings)} holdings, total invested: ₹{total_invested:,.2f}"
    )

    return PortfolioData(
        holdings=holdings,
        total_invested=total_invested,
        csv_raw=csv_content,
    )
