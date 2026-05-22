"""Unit tests for the CSV portfolio parser."""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from portfolio_analyzer.data.portfolio_parser import (
    PortfolioParseError,
    normalize_ticker,
    parse_portfolio_csv,
)


class TestNormalizeTicker:
    def test_plain_ticker(self):
        clean, yf = normalize_ticker("RELIANCE")
        assert clean == "RELIANCE"
        assert yf == "RELIANCE.NS"

    def test_ns_suffix(self):
        clean, yf = normalize_ticker("TCS.NS")
        assert clean == "TCS"
        assert yf == "TCS.NS"

    def test_bo_suffix(self):
        clean, yf = normalize_ticker("INFY.BO")
        assert clean == "INFY"
        assert yf == "INFY.NS"

    def test_lowercase(self):
        clean, yf = normalize_ticker("hdfc")
        assert clean == "HDFC"
        assert yf == "HDFC.NS"

    def test_whitespace(self):
        clean, yf = normalize_ticker("  SBIN  ")
        assert clean == "SBIN"
        assert yf == "SBIN.NS"


class TestParsePortfolioCsv:
    def test_valid_csv(self):
        csv = """ticker,quantity,buy_price,buy_date
RELIANCE,50,2450.00,2024-01-15
TCS,30,3800.00,2024-02-10"""
        portfolio = parse_portfolio_csv(csv)
        assert len(portfolio.holdings) == 2
        assert portfolio.holdings[0].ticker == "RELIANCE"
        assert portfolio.holdings[0].quantity == 50
        assert portfolio.holdings[0].buy_price == 2450.00
        assert portfolio.holdings[0].ticker_ns == "RELIANCE.NS"

    def test_column_aliases(self):
        csv = """symbol,qty,avg_price
INFY,100,1500"""
        portfolio = parse_portfolio_csv(csv)
        assert len(portfolio.holdings) == 1
        assert portfolio.holdings[0].ticker == "INFY"
        assert portfolio.holdings[0].quantity == 100

    def test_with_rupee_symbol(self):
        csv = """ticker,quantity,buy_price
ITC,200,₹440.50"""
        portfolio = parse_portfolio_csv(csv)
        assert portfolio.holdings[0].buy_price == 440.50

    def test_with_commas_in_numbers(self):
        csv = """ticker,quantity,buy_price
MARUTI,10,"10,500.00" """
        portfolio = parse_portfolio_csv(csv)
        assert portfolio.holdings[0].buy_price == 10500.00

    def test_missing_required_columns(self):
        csv = """name,quantity
RELIANCE,50"""
        with pytest.raises(PortfolioParseError, match="Missing required columns"):
            parse_portfolio_csv(csv)

    def test_empty_csv(self):
        with pytest.raises(PortfolioParseError, match="empty"):
            parse_portfolio_csv("")

    def test_no_valid_rows(self):
        csv = """ticker,quantity,buy_price
,50,2450"""
        with pytest.raises(PortfolioParseError, match="No valid holdings"):
            parse_portfolio_csv(csv)

    def test_portfolio_weights(self):
        csv = """ticker,quantity,buy_price
RELIANCE,10,1000
TCS,10,1000"""
        portfolio = parse_portfolio_csv(csv)
        weights = portfolio.weights
        assert abs(weights["RELIANCE"] - 0.5) < 0.01
        assert abs(weights["TCS"] - 0.5) < 0.01

    def test_total_invested(self):
        csv = """ticker,quantity,buy_price
RELIANCE,10,1000
TCS,20,500"""
        portfolio = parse_portfolio_csv(csv)
        assert portfolio.total_invested == 20000.0

    def test_sample_fixture(self):
        fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "sample_portfolio.csv")
        with open(fixture_path) as f:
            csv_content = f.read()
        portfolio = parse_portfolio_csv(csv_content)
        assert len(portfolio.holdings) == 10
        assert portfolio.total_invested > 0
