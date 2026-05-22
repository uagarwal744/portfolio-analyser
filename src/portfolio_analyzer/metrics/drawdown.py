"""Drawdown analysis — max drawdown, drawdown series, duration."""

import numpy as np
import pandas as pd


def _portfolio_cumulative(
    prices: pd.DataFrame, weights: dict[str, float]
) -> pd.Series:
    """Compute portfolio cumulative value series."""
    returns = prices.pct_change().dropna()
    weight_arr = np.array([weights.get(col, 0) for col in returns.columns])
    if weight_arr.sum() > 0:
        weight_arr = weight_arr / weight_arr.sum()
    portfolio_daily = pd.Series(returns.values @ weight_arr, index=returns.index)
    return (1 + portfolio_daily).cumprod()


def calc_max_drawdown(prices: pd.DataFrame, weights: dict[str, float]) -> dict:
    """Calculate maximum drawdown for portfolio and individual holdings."""
    if prices.empty:
        return {"error": "No price data available"}

    individual_mdd = {}
    for col in prices.columns:
        cummax = prices[col].cummax()
        dd = (prices[col] - cummax) / cummax
        individual_mdd[col] = {"max_drawdown": float(dd.min()), "date": str(dd.idxmin().date())}

    cumulative = _portfolio_cumulative(prices, weights)
    peak = cumulative.cummax()
    drawdown = (cumulative - peak) / peak
    portfolio_mdd = float(drawdown.min())
    mdd_date = str(drawdown.idxmin().date())

    mdd_idx = drawdown.idxmin()
    recovery = drawdown.loc[mdd_idx:]
    recovered = recovery[recovery >= 0]
    recovery_date = str(recovered.index[0].date()) if not recovered.empty else "Not recovered"

    if portfolio_mdd > -0.10:
        interp = "Low drawdown — portfolio has been relatively stable"
    elif portfolio_mdd > -0.20:
        interp = "Moderate drawdown — some significant dips occurred"
    elif portfolio_mdd > -0.35:
        interp = "High drawdown — portfolio experienced substantial losses"
    else:
        interp = "Severe drawdown — portfolio faced extreme losses"

    return {
        "individual_max_drawdown": individual_mdd,
        "portfolio_max_drawdown": portfolio_mdd,
        "max_drawdown_date": mdd_date,
        "recovery_date": recovery_date,
        "interpretation": interp,
    }


def calc_drawdown_series(prices: pd.DataFrame, weights: dict[str, float]) -> dict:
    """Calculate the full drawdown time series for charting."""
    if prices.empty:
        return {"error": "No price data available"}

    cumulative = _portfolio_cumulative(prices, weights)
    peak = cumulative.cummax()
    drawdown = (cumulative - peak) / peak
    step = max(1, len(drawdown) // 500)
    sampled = drawdown.iloc[::step]

    return {
        "dates": [str(d.date()) for d in sampled.index],
        "drawdown_values": [float(v) for v in sampled.values],
        "current_drawdown": float(drawdown.iloc[-1]),
        "max_drawdown": float(drawdown.min()),
    }


def calc_drawdown_duration(prices: pd.DataFrame, weights: dict[str, float]) -> dict:
    """Calculate drawdown duration statistics."""
    if prices.empty:
        return {"error": "No price data available"}

    cumulative = _portfolio_cumulative(prices, weights)
    peak = cumulative.cummax()
    drawdown = (cumulative - peak) / peak
    in_dd = drawdown < -0.001

    periods = []
    start = None
    for date, is_dd in in_dd.items():
        if is_dd and start is None:
            start = date
        elif not is_dd and start is not None:
            periods.append((date - start).days)
            start = None
    if start is not None:
        periods.append((drawdown.index[-1] - start).days)

    if not periods:
        return {"total_drawdown_periods": 0, "avg_duration_days": 0, "max_duration_days": 0, "currently_in_drawdown": False}

    return {
        "total_drawdown_periods": len(periods),
        "avg_duration_days": int(np.mean(periods)),
        "max_duration_days": int(max(periods)),
        "min_duration_days": int(min(periods)),
        "currently_in_drawdown": bool(in_dd.iloc[-1]),
        "current_drawdown_depth": float(drawdown.iloc[-1]),
    }
