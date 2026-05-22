"""Benchmark comparison metrics — alpha, tracking error, excess returns vs Nifty 50."""

import numpy as np
import pandas as pd


def _portfolio_returns(returns: pd.DataFrame, weights: dict[str, float]) -> pd.Series:
    weight_arr = np.array([weights.get(col, 0) for col in returns.columns])
    if weight_arr.sum() > 0:
        weight_arr = weight_arr / weight_arr.sum()
    return pd.Series(returns.values @ weight_arr, index=returns.index)


def calc_benchmark_comparison(
    prices: pd.DataFrame, benchmark_prices: pd.Series, weights: dict[str, float]
) -> dict:
    """Compare portfolio performance vs benchmark."""
    if prices.empty or benchmark_prices.empty:
        return {"error": "No data available"}

    returns = prices.pct_change().dropna()
    bench_ret = benchmark_prices.pct_change().dropna()
    common = returns.index.intersection(bench_ret.index)
    if len(common) < 30:
        return {"error": "Insufficient overlapping data"}

    returns = returns.loc[common]
    bench_ret = bench_ret.loc[common]
    port_ret = _portfolio_returns(returns, weights)

    port_total = float(np.prod(1 + port_ret) - 1)
    bench_total = float(np.prod(1 + bench_ret) - 1)
    years = len(common) / 252

    port_cagr = float((1 + port_total) ** (1 / years) - 1) if years > 0 else 0
    bench_cagr = float((1 + bench_total) ** (1 / years) - 1) if years > 0 else 0

    outperformance = port_total - bench_total
    status = "outperforming" if outperformance > 0 else "underperforming"

    return {
        "portfolio_total_return": port_total,
        "benchmark_total_return": bench_total,
        "portfolio_cagr": port_cagr,
        "benchmark_cagr": bench_cagr,
        "outperformance": outperformance,
        "status": status,
        "benchmark_name": "Nifty 50",
        "period_years": round(years, 2),
    }


def calc_alpha(
    prices: pd.DataFrame, benchmark_prices: pd.Series, weights: dict[str, float],
    risk_free_rate: float = 0.07,
) -> dict:
    """Calculate Jensen's Alpha — risk-adjusted outperformance."""
    if prices.empty or benchmark_prices.empty:
        return {"error": "No data available"}

    returns = prices.pct_change().dropna()
    bench_ret = benchmark_prices.pct_change().dropna()
    common = returns.index.intersection(bench_ret.index)
    if len(common) < 30:
        return {"error": "Insufficient data"}

    returns = returns.loc[common]
    bench_ret = bench_ret.loc[common]
    port_ret = _portfolio_returns(returns, weights)

    daily_rf = risk_free_rate / 252
    bench_var = bench_ret.var()
    beta = float(port_ret.cov(bench_ret) / bench_var) if bench_var > 0 else 1.0

    port_ann = port_ret.mean() * 252
    bench_ann = bench_ret.mean() * 252
    alpha = float(port_ann - (daily_rf * 252 + beta * (bench_ann - daily_rf * 252)))

    return {
        "jensens_alpha": alpha,
        "beta": beta,
        "interpretation": f"Portfolio generates {alpha*100:.2f}% annual excess return after adjusting for market risk",
    }


def calc_tracking_error(
    prices: pd.DataFrame, benchmark_prices: pd.Series, weights: dict[str, float]
) -> dict:
    """Calculate tracking error — how closely portfolio follows benchmark."""
    if prices.empty or benchmark_prices.empty:
        return {"error": "No data available"}

    returns = prices.pct_change().dropna()
    bench_ret = benchmark_prices.pct_change().dropna()
    common = returns.index.intersection(bench_ret.index)
    if len(common) < 30:
        return {"error": "Insufficient data"}

    returns = returns.loc[common]
    bench_ret = bench_ret.loc[common]
    port_ret = _portfolio_returns(returns, weights)

    active = port_ret - bench_ret
    te = float(active.std() * np.sqrt(252))

    return {
        "tracking_error": te,
        "interpretation": "Low tracking error — closely follows benchmark" if te < 0.05 else "Moderate" if te < 0.10 else "High — significantly different from benchmark",
    }


def calc_excess_returns(
    prices: pd.DataFrame, benchmark_prices: pd.Series, weights: dict[str, float]
) -> dict:
    """Calculate rolling excess returns vs benchmark."""
    if prices.empty or benchmark_prices.empty:
        return {"error": "No data available"}

    returns = prices.pct_change().dropna()
    bench_ret = benchmark_prices.pct_change().dropna()
    common = returns.index.intersection(bench_ret.index)
    if len(common) < 60:
        return {"error": "Insufficient data"}

    returns = returns.loc[common]
    bench_ret = bench_ret.loc[common]
    port_ret = _portfolio_returns(returns, weights)

    active = port_ret - bench_ret
    rolling_30d = active.rolling(21).mean() * 252
    rolling_30d = rolling_30d.dropna()

    step = max(1, len(rolling_30d) // 200)
    sampled = rolling_30d.iloc[::step]

    pct_outperform = float((active > 0).mean() * 100)

    return {
        "dates": [str(d.date()) for d in sampled.index],
        "rolling_excess_return": [float(v) for v in sampled.values],
        "pct_days_outperforming": pct_outperform,
        "avg_daily_excess": float(active.mean() * 252),
    }
