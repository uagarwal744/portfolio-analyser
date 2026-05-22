"""Sector and asset-class breakdown with hidden concentration detection."""

from typing import Optional


def calc_sector_breakdown(holdings_data: list[dict]) -> dict:
    """Calculate sector-wise portfolio breakdown.

    Args:
        holdings_data: List of dicts with keys: ticker, sector, investment_value, current_value.

    Returns:
        Dict with sector breakdown and weights.
    """
    if not holdings_data:
        return {"error": "No holdings data"}

    sector_invested: dict[str, float] = {}
    sector_tickers: dict[str, list[str]] = {}

    total = sum(h.get("investment_value", 0) for h in holdings_data)

    for h in holdings_data:
        sector = h.get("sector") or "Unknown"
        val = h.get("investment_value", 0)
        sector_invested[sector] = sector_invested.get(sector, 0) + val
        sector_tickers.setdefault(sector, []).append(h.get("ticker", "?"))

    breakdown = []
    for sector, value in sorted(sector_invested.items(), key=lambda x: x[1], reverse=True):
        weight = value / total if total > 0 else 0
        breakdown.append({
            "sector": sector,
            "invested_value": value,
            "weight": round(weight, 4),
            "tickers": sector_tickers[sector],
            "num_stocks": len(sector_tickers[sector]),
        })

    return {
        "sector_breakdown": breakdown,
        "total_sectors": len(breakdown),
        "total_invested": total,
    }


def calc_sector_concentration(holdings_data: list[dict]) -> dict:
    """Calculate sector-level HHI and concentration metrics."""
    breakdown = calc_sector_breakdown(holdings_data)
    if "error" in breakdown:
        return breakdown

    weights = [s["weight"] for s in breakdown["sector_breakdown"]]
    hhi = sum(w ** 2 for w in weights)
    top_sector = breakdown["sector_breakdown"][0] if breakdown["sector_breakdown"] else None

    return {
        "sector_hhi": hhi,
        "effective_sectors": 1.0 / hhi if hhi > 0 else 0,
        "top_sector": top_sector,
        "is_concentrated": hhi > 0.25,
    }


def identify_hidden_concentration(
    holdings_data: list[dict],
    correlation_data: Optional[dict] = None,
) -> dict:
    """Detect hidden concentration risks.

    Checks if the portfolio *appears* diversified by ticker count
    but is actually concentrated by sector, industry, or correlated returns.

    Args:
        holdings_data: List of holding dicts with sector/industry info.
        correlation_data: Optional correlation matrix results.

    Returns:
        Dict with hidden concentration warnings.
    """
    warnings = []
    risk_level = "low"

    # 1. Sector concentration check
    sector_conc = calc_sector_concentration(holdings_data)
    if sector_conc.get("is_concentrated") and sector_conc.get("top_sector"):
        top = sector_conc["top_sector"]
        warnings.append({
            "type": "sector_concentration",
            "severity": "high",
            "message": f"{top['weight']*100:.0f}% of portfolio is in {top['sector']} ({', '.join(top['tickers'])})",
            "detail": f"Top sector holds {top['num_stocks']} of your stocks",
        })
        risk_level = "high"

    # 2. Single sector > 40% check
    breakdown = calc_sector_breakdown(holdings_data)
    for sector in breakdown.get("sector_breakdown", []):
        if sector["weight"] > 0.40:
            if not any(w["type"] == "sector_concentration" for w in warnings):
                warnings.append({
                    "type": "sector_overweight",
                    "severity": "high",
                    "message": f"Over 40% allocated to {sector['sector']}",
                })
                risk_level = "high"

    # 3. Too few sectors
    total_sectors = breakdown.get("total_sectors", 0)
    total_stocks = sum(s["num_stocks"] for s in breakdown.get("sector_breakdown", []))
    if total_stocks >= 5 and total_sectors <= 2:
        warnings.append({
            "type": "low_sector_diversity",
            "severity": "medium",
            "message": f"{total_stocks} stocks but only {total_sectors} sectors — diversification is illusory",
        })
        if risk_level == "low":
            risk_level = "medium"

    # 4. High average correlation (if available)
    if correlation_data and "avg_correlation" in correlation_data:
        avg_corr = correlation_data["avg_correlation"]
        if avg_corr > 0.7:
            warnings.append({
                "type": "high_correlation",
                "severity": "high",
                "message": f"Average pairwise correlation is {avg_corr:.2f} — stocks move together",
            })
            risk_level = "high"
        elif avg_corr > 0.5:
            warnings.append({
                "type": "moderate_correlation",
                "severity": "medium",
                "message": f"Average pairwise correlation is {avg_corr:.2f} — moderate co-movement",
            })
            if risk_level == "low":
                risk_level = "medium"

    # 5. Single stock dominance (> 30%)
    for h in holdings_data:
        total = sum(hh.get("investment_value", 0) for hh in holdings_data)
        if total > 0 and h.get("investment_value", 0) / total > 0.30:
            warnings.append({
                "type": "single_stock_dominance",
                "severity": "high",
                "message": f"{h['ticker']} alone is {h['investment_value']/total*100:.0f}% of your portfolio",
            })
            risk_level = "high"

    return {
        "hidden_concentration_detected": len(warnings) > 0,
        "risk_level": risk_level,
        "warnings": warnings,
        "summary": f"Found {len(warnings)} concentration risk(s)" if warnings else "No hidden concentration detected",
    }
