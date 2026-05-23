"""Historical returns calculations.

All functions operate on pandas DataFrames/Series of prices or returns.
No LLM calls — pure deterministic computation.
"""

import numpy as np
import pandas as pd


def calc_historical_returns(
    prices: pd.DataFrame,
    weights: dict[str, float],
) -> dict:
    """Calculate historical returns for portfolio and individual holdings.

    Args:
        prices: DataFrame of closing prices (tickers as columns).
        weights: Dict of ticker → portfolio weight.

    Returns:
        Dict with per-stock and portfolio returns.
    """
    if prices.empty:
        return {"error": "No price data available"}

    returns = prices.pct_change().dropna()
    total_return = {}
    for col in returns.columns:
        total_return[col] = float((1 + returns[col]).prod() - 1)

    # Portfolio return (weighted)
    weight_arr = np.array([weights.get(col, 0) for col in returns.columns])
    if weight_arr.sum() > 0:
        weight_arr = weight_arr / weight_arr.sum()
    portfolio_daily = returns.values @ weight_arr
    portfolio_total = float(np.prod(1 + portfolio_daily) - 1)

    return {
        "individual_returns": total_return,
        "portfolio_total_return": portfolio_total,
        "period_days": len(returns),
        "start_date": str(prices.index[0].date()),
        "end_date": str(prices.index[-1].date()),
    }


def calc_cagr(
    prices: pd.DataFrame,
    weights: dict[str, float],
) -> dict:
    """Calculate Compound Annual Growth Rate.

    Args:
        prices: DataFrame of closing prices.
        weights: Dict of ticker → portfolio weight.

    Returns:
        Dict with per-stock and portfolio CAGR.
    """
    if prices.empty or len(prices) < 2:
        return {"error": "Insufficient price data for CAGR"}

    n_days = (prices.index[-1] - prices.index[0]).days
    if n_days <= 0:
        return {"error": "Price data spans less than one day"}

    years = n_days / 365.25

    individual_cagr = {}
    for col in prices.columns:
        start_price = prices[col].iloc[0]
        end_price = prices[col].iloc[-1]
        if start_price > 0:
            individual_cagr[col] = float((end_price / start_price) ** (1 / years) - 1)

    # Portfolio CAGR
    returns = prices.pct_change().dropna()
    weight_arr = np.array([weights.get(col, 0) for col in returns.columns])
    if weight_arr.sum() > 0:
        weight_arr = weight_arr / weight_arr.sum()
    portfolio_daily = returns.values @ weight_arr
    cumulative = np.prod(1 + portfolio_daily)
    portfolio_cagr = float(cumulative ** (1 / years) - 1) if years > 0 else 0.0

    return {
        "individual_cagr": individual_cagr,
        "portfolio_cagr": portfolio_cagr,
        "period_years": round(years, 2),
    }


def calc_cumulative_returns(
    prices: pd.DataFrame,
    weights: dict[str, float],
    bench: pd.Series | None = None,
    benchmark_name: str = "Nifty 50",
) -> dict:
    """Calculate cumulative returns from the first point in timeseries.

    Args:
        prices: DataFrame of closing prices.
        weights: Dict of ticker → portfolio weight.
        bench: Optional Series of benchmark closing prices.
        benchmark_name: Label for the benchmark series (e.g., "Nifty 50", "Gold").

    Returns:
        Dict with cumulative return statistics and timeseries for plotting.
    """
    if prices.empty:
        return {"error": "Need price data for cumulative returns"}

    returns = prices.pct_change().dropna()
    weight_arr = np.array([weights.get(col, 0) for col in returns.columns])
    if weight_arr.sum() > 0:
        weight_arr = weight_arr / weight_arr.sum()
    portfolio_daily = pd.Series(returns.values @ weight_arr, index=returns.index)

    cum_port = (1 + portfolio_daily).cumprod() - 1

    if cum_port.empty:
        return {"error": "Insufficient data for cumulative calculation"}

    result = {
        "current_return": float(cum_port.iloc[-1]),
        "best_return": float(cum_port.max()),
        "worst_return": float(cum_port.min()),
        "best_period_end": str(cum_port.idxmax().date()),
        "worst_period_end": str(cum_port.idxmin().date()),
    }

    # Add timeseries data for plotting (sample to avoid huge payloads)
    step = max(1, len(cum_port) // 250)
    sampled_port = cum_port.iloc[::step]
    
    result["dates"] = [str(d.date()) for d in sampled_port.index]
    result["portfolio_cumulative"] = [float(v) for v in sampled_port.values]

    if bench is not None and not bench.empty:
        bench_ret = bench.pct_change().dropna()
        common = returns.index.intersection(bench_ret.index)
        if len(common) > 0:
            bench_ret_common = bench_ret.loc[common]
            cum_bench = (1 + bench_ret_common).cumprod() - 1
            
            # Sample using the same dates as portfolio where possible
            cum_bench_sampled = cum_bench.reindex(sampled_port.index, method='ffill')
            result["benchmark_cumulative"] = [float(v) if pd.notna(v) else None for v in cum_bench_sampled.values]
            result["benchmark_name"] = benchmark_name

    return result


def calc_period_returns(
    prices: pd.DataFrame,
    weights: dict[str, float],
) -> dict:
    """Calculate returns over standard periods (1M, 3M, 6M, 1Y, 3Y, 5Y).

    Args:
        prices: DataFrame of closing prices (should have max available history).
        weights: Dict of ticker → portfolio weight.

    Returns:
        Dict with returns for each standard period.
    """
    if prices.empty:
        return {"error": "No price data available"}

    returns = prices.pct_change().dropna()
    weight_arr = np.array([weights.get(col, 0) for col in returns.columns])
    if weight_arr.sum() > 0:
        weight_arr = weight_arr / weight_arr.sum()
    portfolio_daily = pd.Series(returns.values @ weight_arr, index=returns.index)

    periods = {
        "1M": 21,
        "3M": 63,
        "6M": 126,
        "1Y": 252,
        "3Y": 756,
        "5Y": 1260,
    }

    period_returns = {}
    for label, days in periods.items():
        if len(portfolio_daily) >= days:
            recent = portfolio_daily.iloc[-days:]
            period_returns[label] = float(np.prod(1 + recent) - 1)
        else:
            period_returns[label] = None

    return {"period_returns": period_returns}
