"""Unit tests for financial metric functions."""

import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from portfolio_analyzer.metrics import returns, risk, drawdown, var, correlation, benchmark, sector


# ── Test fixtures ──

@pytest.fixture
def sample_prices():
    """Create synthetic price data for testing."""
    np.random.seed(42)
    dates = pd.bdate_range("2023-01-01", periods=252)
    # Two stocks with known characteristics
    price_a = 100 * np.cumprod(1 + np.random.normal(0.0004, 0.02, 252))
    price_b = 100 * np.cumprod(1 + np.random.normal(0.0002, 0.015, 252))
    return pd.DataFrame({"STOCK_A": price_a, "STOCK_B": price_b}, index=dates)


@pytest.fixture
def equal_weights():
    return {"STOCK_A": 0.5, "STOCK_B": 0.5}


@pytest.fixture
def benchmark_prices(sample_prices):
    """Synthetic benchmark (index) data."""
    np.random.seed(99)
    dates = sample_prices.index
    prices = 100 * np.cumprod(1 + np.random.normal(0.0003, 0.012, len(dates)))
    return pd.Series(prices, index=dates, name="NIFTY50")


# ── Returns tests ──

class TestReturns:
    def test_historical_returns(self, sample_prices, equal_weights):
        result = returns.calc_historical_returns(sample_prices, equal_weights)
        assert "individual_returns" in result
        assert "portfolio_total_return" in result
        assert len(result["individual_returns"]) == 2
        assert isinstance(result["portfolio_total_return"], float)

    def test_cagr(self, sample_prices, equal_weights):
        result = returns.calc_cagr(sample_prices, equal_weights)
        assert "portfolio_cagr" in result
        assert "period_years" in result
        assert result["period_years"] > 0

    def test_rolling_returns(self, sample_prices, equal_weights):
        result = returns.calc_rolling_returns(sample_prices, equal_weights, window=21)
        assert "avg_rolling_return" in result
        assert result["window_days"] == 21

    def test_period_returns(self, sample_prices, equal_weights):
        result = returns.calc_period_returns(sample_prices, equal_weights)
        assert "period_returns" in result

    def test_empty_prices(self, equal_weights):
        result = returns.calc_historical_returns(pd.DataFrame(), equal_weights)
        assert "error" in result


# ── Risk tests ──

class TestRisk:
    def test_volatility(self, sample_prices, equal_weights):
        result = risk.calc_volatility(sample_prices, equal_weights)
        assert "portfolio_volatility" in result
        assert result["portfolio_volatility"] > 0
        assert result["annualized"] is True

    def test_sharpe_ratio(self, sample_prices, equal_weights):
        result = risk.calc_sharpe_ratio(sample_prices, equal_weights)
        assert "portfolio_sharpe" in result
        assert "interpretation" in result
        assert isinstance(result["portfolio_sharpe"], float)

    def test_sortino_ratio(self, sample_prices, equal_weights):
        result = risk.calc_sortino_ratio(sample_prices, equal_weights)
        assert "portfolio_sortino" in result
        assert "downside_volatility" in result

    def test_beta(self, sample_prices, benchmark_prices, equal_weights):
        result = risk.calc_beta(sample_prices, benchmark_prices, equal_weights)
        assert "portfolio_beta" in result
        assert "interpretation" in result

    def test_information_ratio(self, sample_prices, benchmark_prices, equal_weights):
        result = risk.calc_information_ratio(sample_prices, benchmark_prices, equal_weights)
        assert "information_ratio" in result


# ── Drawdown tests ──

class TestDrawdown:
    def test_max_drawdown(self, sample_prices, equal_weights):
        result = drawdown.calc_max_drawdown(sample_prices, equal_weights)
        assert "portfolio_max_drawdown" in result
        assert result["portfolio_max_drawdown"] <= 0  # Drawdown is always negative

    def test_drawdown_series(self, sample_prices, equal_weights):
        result = drawdown.calc_drawdown_series(sample_prices, equal_weights)
        assert "dates" in result
        assert "drawdown_values" in result
        assert len(result["dates"]) == len(result["drawdown_values"])

    def test_drawdown_duration(self, sample_prices, equal_weights):
        result = drawdown.calc_drawdown_duration(sample_prices, equal_weights)
        assert "total_drawdown_periods" in result


# ── VaR tests ──

class TestVaR:
    def test_var_historical(self, sample_prices, equal_weights):
        result = var.calc_var_historical(sample_prices, equal_weights)
        assert "var_95_daily" in result
        assert result["var_95_daily"] < 0  # VaR is a loss

    def test_var_parametric(self, sample_prices, equal_weights):
        result = var.calc_var_parametric(sample_prices, equal_weights)
        assert "var_95_daily" in result

    def test_cvar(self, sample_prices, equal_weights):
        result = var.calc_cvar(sample_prices, equal_weights)
        assert "cvar_95_daily" in result
        # CVaR should be worse (more negative) than VaR
        assert result["cvar_95_daily"] <= result["var_95_daily"]

    def test_tail_risk(self, sample_prices, equal_weights):
        result = var.calc_tail_risk_metrics(sample_prices, equal_weights)
        assert "skewness" in result
        assert "excess_kurtosis" in result
        assert "worst_5_days" in result
        assert len(result["worst_5_days"]) == 5


# ── Correlation tests ──

class TestCorrelation:
    def test_correlation_matrix(self, sample_prices):
        result = correlation.calc_correlation_matrix(sample_prices)
        assert "correlation_matrix" in result
        assert "avg_correlation" in result

    def test_portfolio_concentration(self, equal_weights):
        result = correlation.calc_portfolio_concentration(equal_weights)
        assert "herfindahl_index" in result
        assert result["herfindahl_index"] == 0.5  # Equal weights: 0.5^2 + 0.5^2

    def test_concentrated_portfolio(self):
        weights = {"A": 0.9, "B": 0.1}
        result = correlation.calc_portfolio_concentration(weights)
        assert result["herfindahl_index"] > 0.5
        assert "concentrated" in result["interpretation"].lower()

    def test_single_stock_correlation(self):
        prices = pd.DataFrame({"A": [1, 2, 3]}, index=pd.date_range("2024-01-01", periods=3))
        result = correlation.calc_correlation_matrix(prices)
        assert "error" in result


# ── Benchmark tests ──

class TestBenchmark:
    def test_benchmark_comparison(self, sample_prices, benchmark_prices, equal_weights):
        result = benchmark.calc_benchmark_comparison(sample_prices, benchmark_prices, equal_weights)
        assert "portfolio_total_return" in result
        assert "benchmark_total_return" in result
        assert result["status"] in ("outperforming", "underperforming")

    def test_alpha(self, sample_prices, benchmark_prices, equal_weights):
        result = benchmark.calc_alpha(sample_prices, benchmark_prices, equal_weights)
        assert "jensens_alpha" in result

    def test_tracking_error(self, sample_prices, benchmark_prices, equal_weights):
        result = benchmark.calc_tracking_error(sample_prices, benchmark_prices, equal_weights)
        assert "tracking_error" in result
        assert result["tracking_error"] >= 0


# ── Sector tests ──

class TestSector:
    def test_sector_breakdown(self):
        holdings = [
            {"ticker": "TCS", "sector": "IT", "investment_value": 100000},
            {"ticker": "INFY", "sector": "IT", "investment_value": 80000},
            {"ticker": "HDFC", "sector": "Banking", "investment_value": 120000},
        ]
        result = sector.calc_sector_breakdown(holdings)
        assert "sector_breakdown" in result
        assert result["total_sectors"] == 2

    def test_hidden_concentration(self):
        holdings = [
            {"ticker": "TCS", "sector": "IT", "investment_value": 100000},
            {"ticker": "INFY", "sector": "IT", "investment_value": 100000},
            {"ticker": "WIPRO", "sector": "IT", "investment_value": 100000},
            {"ticker": "HCLTECH", "sector": "IT", "investment_value": 100000},
            {"ticker": "HDFC", "sector": "Banking", "investment_value": 50000},
        ]
        result = sector.identify_hidden_concentration(holdings)
        assert result["hidden_concentration_detected"] is True
        assert result["risk_level"] in ("medium", "high")

    def test_no_concentration(self):
        holdings = [
            {"ticker": "TCS", "sector": "IT", "investment_value": 100},
            {"ticker": "HDFC", "sector": "Banking", "investment_value": 100},
            {"ticker": "RELIANCE", "sector": "Oil", "investment_value": 100},
            {"ticker": "ITC", "sector": "FMCG", "investment_value": 100},
        ]
        result = sector.identify_hidden_concentration(holdings)
        assert result["hidden_concentration_detected"] is False
