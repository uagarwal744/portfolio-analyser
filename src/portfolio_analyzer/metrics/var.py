"""Value at Risk (VaR) and tail risk metrics."""

import numpy as np
import pandas as pd
from scipy import stats


def _portfolio_returns(returns: pd.DataFrame, weights: dict[str, float]) -> pd.Series:
    weight_arr = np.array([weights.get(col, 0) for col in returns.columns])
    if weight_arr.sum() > 0:
        weight_arr = weight_arr / weight_arr.sum()
    return pd.Series(returns.values @ weight_arr, index=returns.index)


def calc_var_historical(prices: pd.DataFrame, weights: dict[str, float], confidence: float = 0.95) -> dict:
    """Historical Value at Risk — uses actual return distribution."""
    if prices.empty:
        return {"error": "No price data available"}

    returns = prices.pct_change().dropna()
    port_ret = _portfolio_returns(returns, weights)

    var_95 = float(np.percentile(port_ret, (1 - confidence) * 100))
    var_99 = float(np.percentile(port_ret, 1))

    return {
        "var_95_daily": var_95,
        "var_99_daily": var_99,
        "var_95_monthly": var_95 * np.sqrt(21),
        "var_99_monthly": var_99 * np.sqrt(21),
        "method": "historical",
        "confidence": confidence,
        "interpretation": f"With 95% confidence, the portfolio won't lose more than {abs(var_95)*100:.2f}% in a single day",
    }


def calc_var_parametric(prices: pd.DataFrame, weights: dict[str, float], confidence: float = 0.95) -> dict:
    """Parametric VaR — assumes normal distribution."""
    if prices.empty:
        return {"error": "No price data available"}

    returns = prices.pct_change().dropna()
    port_ret = _portfolio_returns(returns, weights)

    mean = port_ret.mean()
    std = port_ret.std()
    z_95 = stats.norm.ppf(1 - confidence)
    z_99 = stats.norm.ppf(0.01)

    var_95 = float(mean + z_95 * std)
    var_99 = float(mean + z_99 * std)

    return {
        "var_95_daily": var_95,
        "var_99_daily": var_99,
        "method": "parametric",
        "mean_daily_return": float(mean),
        "daily_std": float(std),
    }


def calc_cvar(prices: pd.DataFrame, weights: dict[str, float], confidence: float = 0.95) -> dict:
    """Conditional VaR (Expected Shortfall) — average loss beyond VaR."""
    if prices.empty:
        return {"error": "No price data available"}

    returns = prices.pct_change().dropna()
    port_ret = _portfolio_returns(returns, weights)

    var_threshold = np.percentile(port_ret, (1 - confidence) * 100)
    tail_losses = port_ret[port_ret <= var_threshold]
    cvar = float(tail_losses.mean()) if len(tail_losses) > 0 else 0.0

    return {
        "cvar_95_daily": cvar,
        "var_95_daily": float(var_threshold),
        "tail_events_count": len(tail_losses),
        "total_observations": len(port_ret),
        "interpretation": f"When losses exceed VaR, the average loss is {abs(cvar)*100:.2f}%",
    }


def calc_tail_risk_metrics(prices: pd.DataFrame, weights: dict[str, float]) -> dict:
    """Combined tail risk summary: skewness, kurtosis, worst days."""
    if prices.empty:
        return {"error": "No price data available"}

    returns = prices.pct_change().dropna()
    port_ret = _portfolio_returns(returns, weights)

    skew = float(port_ret.skew())
    kurt = float(port_ret.kurtosis())
    worst_days = port_ret.nsmallest(5)

    return {
        "skewness": skew,
        "excess_kurtosis": kurt,
        "worst_5_days": {str(d.date()): float(v) for d, v in worst_days.items()},
        "best_5_days": {str(d.date()): float(v) for d, v in port_ret.nlargest(5).items()},
        "skew_interpretation": "Left-skewed (more extreme losses)" if skew < -0.5 else "Right-skewed (more extreme gains)" if skew > 0.5 else "Roughly symmetric",
        "kurtosis_interpretation": "Fat tails (extreme events more likely)" if kurt > 1 else "Normal tails" if kurt > -1 else "Thin tails",
    }
