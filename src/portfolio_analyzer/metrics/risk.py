"""Risk-adjusted performance metrics.

Sharpe ratio, Sortino ratio, volatility, beta, information ratio.
All use annualized values assuming 252 trading days/year.
"""

import os

import numpy as np
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

TRADING_DAYS = 252
RISK_FREE_RATE = float(os.getenv("RISK_FREE_RATE", "0.07"))  # Annualized


def _portfolio_returns(
    returns: pd.DataFrame, weights: dict[str, float]
) -> pd.Series:
    """Compute weighted portfolio daily returns."""
    weight_arr = np.array([weights.get(col, 0) for col in returns.columns])
    if weight_arr.sum() > 0:
        weight_arr = weight_arr / weight_arr.sum()
    return pd.Series(returns.values @ weight_arr, index=returns.index)


def calc_volatility(
    prices: pd.DataFrame,
    weights: dict[str, float],
) -> dict:
    """Calculate annualized volatility for portfolio and individual stocks.

    Args:
        prices: DataFrame of closing prices.
        weights: Dict of ticker → portfolio weight.

    Returns:
        Dict with individual and portfolio volatility.
    """
    if prices.empty:
        return {"error": "No price data available"}

    returns = prices.pct_change().dropna()

    individual_vol = {}
    for col in returns.columns:
        individual_vol[col] = float(returns[col].std() * np.sqrt(TRADING_DAYS))

    portfolio_daily = _portfolio_returns(returns, weights)
    portfolio_vol = float(portfolio_daily.std() * np.sqrt(TRADING_DAYS))

    return {
        "individual_volatility": individual_vol,
        "portfolio_volatility": portfolio_vol,
        "annualized": True,
        "trading_days": TRADING_DAYS,
    }


def calc_sharpe_ratio(
    prices: pd.DataFrame,
    weights: dict[str, float],
    risk_free_rate: float = RISK_FREE_RATE,
) -> dict:
    """Calculate annualized Sharpe ratio.

    Sharpe = (Rp - Rf) / σp (annualized)

    Args:
        prices: DataFrame of closing prices.
        weights: Dict of ticker → portfolio weight.
        risk_free_rate: Annualized risk-free rate (default: India 10Y ~7%).

    Returns:
        Dict with individual and portfolio Sharpe ratios.
    """
    if prices.empty:
        return {"error": "No price data available"}

    returns = prices.pct_change().dropna()
    daily_rf = risk_free_rate / TRADING_DAYS

    individual_sharpe = {}
    for col in returns.columns:
        excess = returns[col] - daily_rf
        if returns[col].std() > 0:
            individual_sharpe[col] = float(
                (excess.mean() / returns[col].std()) * np.sqrt(TRADING_DAYS)
            )
        else:
            individual_sharpe[col] = 0.0

    portfolio_daily = _portfolio_returns(returns, weights)
    excess_portfolio = portfolio_daily - daily_rf
    portfolio_std = portfolio_daily.std()
    portfolio_sharpe = (
        float((excess_portfolio.mean() / portfolio_std) * np.sqrt(TRADING_DAYS))
        if portfolio_std > 0
        else 0.0
    )

    # Interpretation
    if portfolio_sharpe >= 3:
        interpretation = "Excellent risk-adjusted returns"
    elif portfolio_sharpe >= 2:
        interpretation = "Very good risk-adjusted returns"
    elif portfolio_sharpe >= 1:
        interpretation = "Good risk-adjusted returns"
    elif portfolio_sharpe >= 0:
        interpretation = "Positive but below-average risk-adjusted returns"
    else:
        interpretation = "Negative risk-adjusted returns — underperforming risk-free rate"

    return {
        "individual_sharpe": individual_sharpe,
        "portfolio_sharpe": portfolio_sharpe,
        "risk_free_rate": risk_free_rate,
        "interpretation": interpretation,
    }


def calc_sortino_ratio(
    prices: pd.DataFrame,
    weights: dict[str, float],
    risk_free_rate: float = RISK_FREE_RATE,
) -> dict:
    """Calculate annualized Sortino ratio.

    Like Sharpe but only penalizes downside volatility.
    Sortino = (Rp - Rf) / σ_downside

    Args:
        prices: DataFrame of closing prices.
        weights: Dict of ticker → portfolio weight.
        risk_free_rate: Annualized risk-free rate.

    Returns:
        Dict with portfolio Sortino ratio.
    """
    if prices.empty:
        return {"error": "No price data available"}

    returns = prices.pct_change().dropna()
    daily_rf = risk_free_rate / TRADING_DAYS
    portfolio_daily = _portfolio_returns(returns, weights)

    excess = portfolio_daily - daily_rf
    downside = portfolio_daily[portfolio_daily < 0]
    downside_std = downside.std() * np.sqrt(TRADING_DAYS) if len(downside) > 0 else 0.0

    sortino = float(excess.mean() * TRADING_DAYS / downside_std) if downside_std > 0 else 0.0

    return {
        "portfolio_sortino": sortino,
        "downside_volatility": float(downside_std),
        "downside_days_pct": float(len(downside) / len(portfolio_daily) * 100),
        "risk_free_rate": risk_free_rate,
    }


def calc_beta(
    prices: pd.DataFrame,
    benchmark_prices: pd.Series,
    weights: dict[str, float],
) -> dict:
    """Calculate portfolio beta relative to a benchmark.

    Beta = Cov(Rp, Rb) / Var(Rb)

    Args:
        prices: DataFrame of closing prices for holdings.
        benchmark_prices: Series of benchmark closing prices (e.g., Nifty 50).
        weights: Dict of ticker → portfolio weight.

    Returns:
        Dict with individual and portfolio beta values.
    """
    if prices.empty or benchmark_prices.empty:
        return {"error": "No price data available"}

    returns = prices.pct_change().dropna()
    bench_returns = benchmark_prices.pct_change().dropna()

    # Align dates
    common_idx = returns.index.intersection(bench_returns.index)
    if len(common_idx) < 30:
        return {"error": "Insufficient overlapping data for beta calculation"}

    returns = returns.loc[common_idx]
    bench_returns = bench_returns.loc[common_idx]

    bench_var = bench_returns.var()
    if bench_var == 0:
        return {"error": "Benchmark has zero variance"}

    individual_beta = {}
    for col in returns.columns:
        cov = returns[col].cov(bench_returns)
        individual_beta[col] = float(cov / bench_var)

    portfolio_daily = _portfolio_returns(returns, weights)
    portfolio_cov = portfolio_daily.cov(bench_returns)
    portfolio_beta = float(portfolio_cov / bench_var)

    # Interpretation
    if portfolio_beta > 1.2:
        interpretation = "High beta — portfolio amplifies market movements"
    elif portfolio_beta > 0.8:
        interpretation = "Moderate beta — portfolio moves roughly with the market"
    elif portfolio_beta > 0:
        interpretation = "Low beta — portfolio is less volatile than the market"
    else:
        interpretation = "Negative beta — portfolio moves opposite to the market"

    return {
        "individual_beta": individual_beta,
        "portfolio_beta": portfolio_beta,
        "benchmark": "Nifty 50",
        "interpretation": interpretation,
    }


def calc_information_ratio(
    prices: pd.DataFrame,
    benchmark_prices: pd.Series,
    weights: dict[str, float],
) -> dict:
    """Calculate Information Ratio.

    IR = (Rp - Rb) / Tracking Error

    Args:
        prices: DataFrame of closing prices.
        benchmark_prices: Series of benchmark closing prices.
        weights: Dict of ticker → portfolio weight.

    Returns:
        Dict with information ratio.
    """
    if prices.empty or benchmark_prices.empty:
        return {"error": "No price data available"}

    returns = prices.pct_change().dropna()
    bench_returns = benchmark_prices.pct_change().dropna()

    common_idx = returns.index.intersection(bench_returns.index)
    if len(common_idx) < 30:
        return {"error": "Insufficient data"}

    returns = returns.loc[common_idx]
    bench_returns = bench_returns.loc[common_idx]

    portfolio_daily = _portfolio_returns(returns, weights)
    active_returns = portfolio_daily - bench_returns
    tracking_error = active_returns.std() * np.sqrt(TRADING_DAYS)

    ir = (
        float(active_returns.mean() * TRADING_DAYS / tracking_error)
        if tracking_error > 0
        else 0.0
    )

    return {
        "information_ratio": ir,
        "annualized_active_return": float(active_returns.mean() * TRADING_DAYS),
        "tracking_error": float(tracking_error),
    }
