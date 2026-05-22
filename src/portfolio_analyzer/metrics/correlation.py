"""Correlation and concentration analysis."""

import numpy as np
import pandas as pd


def calc_correlation_matrix(prices: pd.DataFrame) -> dict:
    """Calculate pairwise correlation matrix of holdings."""
    if prices.empty or prices.shape[1] < 2:
        return {"error": "Need at least 2 stocks for correlation analysis"}

    returns = prices.pct_change().dropna()
    corr = returns.corr()

    # Find highest and lowest correlations (excluding self-correlations)
    pairs = []
    cols = corr.columns.tolist()
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            pairs.append({"pair": f"{cols[i]} — {cols[j]}", "correlation": float(corr.iloc[i, j])})

    pairs.sort(key=lambda x: x["correlation"], reverse=True)

    return {
        "correlation_matrix": {col: {c: float(corr.loc[col, c]) for c in cols} for col in cols},
        "highest_correlations": pairs[:5],
        "lowest_correlations": pairs[-5:][::-1],
        "avg_correlation": float(np.mean([p["correlation"] for p in pairs])) if pairs else 0.0,
    }


def calc_portfolio_concentration(weights: dict[str, float]) -> dict:
    """Calculate portfolio concentration metrics."""
    if not weights:
        return {"error": "No portfolio weights available"}

    sorted_w = sorted(weights.items(), key=lambda x: x[1], reverse=True)
    values = [w for _, w in sorted_w]

    top1 = values[0] if values else 0
    top3 = sum(values[:3])
    top5 = sum(values[:5])
    hhi = sum(w ** 2 for w in values)

    if hhi > 0.25:
        interp = "Highly concentrated — significant single-stock risk"
    elif hhi > 0.15:
        interp = "Moderately concentrated"
    else:
        interp = "Well diversified across holdings"

    return {
        "holdings_count": len(weights),
        "top_holding": {"ticker": sorted_w[0][0], "weight": top1} if sorted_w else None,
        "top_3_weight": top3,
        "top_5_weight": top5,
        "herfindahl_index": hhi,
        "effective_holdings": 1.0 / hhi if hhi > 0 else 0,
        "weight_distribution": [{"ticker": t, "weight": round(w, 4)} for t, w in sorted_w],
        "interpretation": interp,
    }


def calc_herfindahl_index(weights: dict[str, float]) -> dict:
    """Calculate Herfindahl-Hirschman Index for concentration."""
    if not weights:
        return {"error": "No weights"}

    values = list(weights.values())
    hhi = sum(w ** 2 for w in values)

    return {
        "hhi": hhi,
        "effective_n": 1.0 / hhi if hhi > 0 else 0,
        "max_possible_hhi": 1.0,
        "equal_weight_hhi": 1.0 / len(values) if values else 0,
    }
