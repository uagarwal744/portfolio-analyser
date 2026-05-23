"""Emit structured dashboard signals from analysis results.

Maps analysis results to typed DashboardSignal objects that the frontend
can consume to render/update specific dashboard widgets.
"""

import logging
from typing import Any

from portfolio_analyzer.models.dashboard import AlertLevel, DashboardSignal, DashboardSignalType
from portfolio_analyzer.state import PortfolioState

logger = logging.getLogger(__name__)


def _emit_risk_signals(results: dict) -> list[DashboardSignal]:
    """Extract risk-related dashboard signals."""
    signals = []

    sharpe = results.get("sharpe_ratio", {})
    if sharpe and "portfolio_sharpe" in sharpe:
        signals.append(DashboardSignal(
            signal_type=DashboardSignalType.RISK_GAUGE,
            title="Risk-Adjusted Performance",
            data={
                "sharpe_ratio": sharpe["portfolio_sharpe"],
                "interpretation": sharpe.get("interpretation", ""),
                "individual": sharpe.get("individual_sharpe", {}),
            },
            priority=2,
        ))

    vol = results.get("volatility", {})
    if vol and "portfolio_volatility" in vol:
        signals[-1].data["volatility"] = vol["portfolio_volatility"] if signals else None
        if not signals:
            signals.append(DashboardSignal(
                signal_type=DashboardSignalType.RISK_GAUGE,
                title="Portfolio Volatility",
                data={"volatility": vol["portfolio_volatility"]},
                priority=3,
            ))

    return signals


def _emit_drawdown_signals(results: dict) -> list[DashboardSignal]:
    """Extract drawdown chart signals."""
    signals = []
    dd_series = results.get("drawdown_series", {})
    if dd_series and "dates" in dd_series:
        signals.append(DashboardSignal(
            signal_type=DashboardSignalType.DRAWDOWN_CHART,
            title="Portfolio Drawdown History",
            data=dd_series,
            priority=4,
        ))

    mdd = results.get("max_drawdown", {})
    if mdd and "portfolio_max_drawdown" in mdd:
        alert = None
        if mdd["portfolio_max_drawdown"] < -0.30:
            alert = AlertLevel.CRITICAL
        elif mdd["portfolio_max_drawdown"] < -0.15:
            alert = AlertLevel.WARNING

        signals.append(DashboardSignal(
            signal_type=DashboardSignalType.DRAWDOWN_CHART,
            title="Max Drawdown Alert",
            data={
                "max_drawdown": mdd["portfolio_max_drawdown"],
                "date": mdd.get("max_drawdown_date"),
                "recovery": mdd.get("recovery_date"),
            },
            priority=3,
            alert_level=alert,
            description=mdd.get("interpretation"),
        ))
    return signals


def _emit_var_signals(results: dict) -> list[DashboardSignal]:
    """Extract VaR summary signals."""
    signals = []
    var_hist = results.get("var_historical", {})
    cvar = results.get("cvar", {})

    if var_hist or cvar:
        data = {}
        if var_hist:
            data.update({k: v for k, v in var_hist.items() if k != "method"})
        if cvar:
            data["cvar_95_daily"] = cvar.get("cvar_95_daily")

        signals.append(DashboardSignal(
            signal_type=DashboardSignalType.VAR_SUMMARY,
            title="Value at Risk Summary",
            data=data,
            priority=3,
            description=var_hist.get("interpretation"),
        ))
    return signals


def _emit_correlation_signals(results: dict) -> list[DashboardSignal]:
    """Extract correlation heatmap signals."""
    signals = []
    corr = results.get("correlation_matrix", {})
    if corr and "correlation_matrix" in corr:
        signals.append(DashboardSignal(
            signal_type=DashboardSignalType.CORRELATION_HEATMAP,
            title="Holdings Correlation Matrix",
            data=corr,
            priority=4,
        ))

    conc = results.get("portfolio_concentration", {})
    if conc and conc.get("herfindahl_index", 0) > 0.20:
        signals.append(DashboardSignal(
            signal_type=DashboardSignalType.CONCENTRATION_ALERT,
            title="Portfolio Concentration Warning",
            data=conc,
            priority=1,
            alert_level=AlertLevel.WARNING,
            description=conc.get("interpretation"),
        ))
    return signals


def _emit_sector_signals(results: dict) -> list[DashboardSignal]:
    """Extract sector pie chart and concentration alert signals."""
    signals = []
    breakdown = results.get("sector_breakdown", {})
    if breakdown and "sector_breakdown" in breakdown:
        signals.append(DashboardSignal(
            signal_type=DashboardSignalType.SECTOR_PIE,
            title="Sector Allocation",
            data=breakdown,
            priority=3,
        ))

    hidden = results.get("hidden_concentration", {})
    if hidden and hidden.get("hidden_concentration_detected"):
        alert = AlertLevel.CRITICAL if hidden["risk_level"] == "high" else AlertLevel.WARNING
        signals.append(DashboardSignal(
            signal_type=DashboardSignalType.CONCENTRATION_ALERT,
            title="⚠️ Hidden Concentration Detected",
            data=hidden,
            priority=1,
            alert_level=alert,
            description=hidden.get("summary"),
        ))
    return signals


def _emit_benchmark_signals(results: dict) -> list[DashboardSignal]:
    """Extract benchmark comparison signals for each benchmark (Nifty 50, Gold, etc.)."""
    signals = []
    for key, comp in results.items():
        # Skip non-benchmark entries (alpha, tracking_error, excess_returns are nested)
        if key in ("alpha", "tracking_error", "excess_returns") or not isinstance(comp, dict):
            continue
        if "outperformance" in comp or "portfolio_return" in comp:
            bench_name = comp.get("benchmark_name", key)
            signals.append(DashboardSignal(
                signal_type=DashboardSignalType.BENCHMARK_COMPARISON,
                title=f"Portfolio vs {bench_name}",
                data=comp,
                priority=3,
                alert_level=AlertLevel.INFO if comp.get("status") == "underperforming" else None,
            ))
    return signals


def _emit_returns_signals(results: dict) -> list[DashboardSignal]:
    """Extract returns chart signals."""
    signals = []
    period = results.get("period_returns", {})
    cagr = results.get("cagr", {})
    cumulative = results.get("cumulative_returns", {})

    if period or cagr:
        data = {}
        if period:
            data["period_returns"] = period.get("period_returns", {})
        if cagr:
            data["portfolio_cagr"] = cagr.get("portfolio_cagr")
            data["individual_cagr"] = cagr.get("individual_cagr", {})

        signals.append(DashboardSignal(
            signal_type=DashboardSignalType.RETURNS_CHART,
            title="Portfolio Returns",
            data=data,
            priority=3,
        ))
        
    if cumulative and "dates" in cumulative and "portfolio_cumulative" in cumulative:
        signals.append(DashboardSignal(
            signal_type=DashboardSignalType.CUMULATIVE_RETURNS_CHART,
            title=f"Cumulative Return vs {cumulative.get('benchmark_name', 'Benchmark')}",
            data=cumulative,
            priority=4,
        ))

    return signals


# Dispatch table: metric module name → signal emitter
SIGNAL_EMITTERS = {
    "risk": _emit_risk_signals,
    "drawdown": _emit_drawdown_signals,
    "var": _emit_var_signals,
    "correlation": _emit_correlation_signals,
    "sector": _emit_sector_signals,
    "benchmark": _emit_benchmark_signals,
    "returns": _emit_returns_signals,
}


def emit_dashboard_node(state: PortfolioState) -> dict[str, Any]:
    """Extract dashboard signals from analysis results.

    Inspects analysis_results and emits typed DashboardSignal objects
    that the frontend can use to render dashboard widgets.
    """
    analysis_results = state.get("analysis_results", {})
    if not analysis_results:
        return {"dashboard_signals": []}

    all_signals: list[DashboardSignal] = []

    for metric_name, results in analysis_results.items():
        if metric_name in SIGNAL_EMITTERS and isinstance(results, dict):
            try:
                signals = SIGNAL_EMITTERS[metric_name](results)
                all_signals.extend(signals)
            except Exception as e:
                logger.error(f"Signal emission for {metric_name} failed: {e}")

    # Sort by priority (lower = higher priority)
    all_signals.sort(key=lambda s: s.priority)

    logger.info(f"Emitted {len(all_signals)} dashboard signals")

    return {"dashboard_signals": [s.model_dump() for s in all_signals]}
