"""Execute deterministic financial analysis based on classified intent.

This node calls pure Python metric functions — NO LLM calls.
The intent determines which metric modules to invoke.
"""

import logging
from typing import Any

import pandas as pd

from portfolio_analyzer.metrics import returns, risk, drawdown, var, correlation, benchmark, sector
from portfolio_analyzer.models.intent import IntentClassification
from portfolio_analyzer.state import PortfolioState

logger = logging.getLogger(__name__)

# Metric module dispatch table
METRIC_RUNNERS = {
    "returns": lambda prices, weights, bench: {
        "historical_returns": returns.calc_historical_returns(prices, weights),
        "cagr": returns.calc_cagr(prices, weights),
        "period_returns": returns.calc_period_returns(prices, weights),
        "rolling_returns": returns.calc_rolling_returns(prices, weights),
    },
    "risk": lambda prices, weights, bench: {
        "volatility": risk.calc_volatility(prices, weights),
        "sharpe_ratio": risk.calc_sharpe_ratio(prices, weights),
        "sortino_ratio": risk.calc_sortino_ratio(prices, weights),
        **({"beta": risk.calc_beta(prices, bench, weights)} if bench is not None else {}),
    },
    "drawdown": lambda prices, weights, bench: {
        "max_drawdown": drawdown.calc_max_drawdown(prices, weights),
        "drawdown_series": drawdown.calc_drawdown_series(prices, weights),
        "drawdown_duration": drawdown.calc_drawdown_duration(prices, weights),
    },
    "var": lambda prices, weights, bench: {
        "var_historical": var.calc_var_historical(prices, weights),
        "var_parametric": var.calc_var_parametric(prices, weights),
        "cvar": var.calc_cvar(prices, weights),
        "tail_risk": var.calc_tail_risk_metrics(prices, weights),
    },
    "correlation": lambda prices, weights, bench: {
        "correlation_matrix": correlation.calc_correlation_matrix(prices),
        "portfolio_concentration": correlation.calc_portfolio_concentration(weights),
    },
    "benchmark": lambda prices, weights, bench: {
        **({"benchmark_comparison": benchmark.calc_benchmark_comparison(prices, bench, weights)} if bench is not None else {}),
        **({"alpha": benchmark.calc_alpha(prices, bench, weights)} if bench is not None else {}),
        **({"tracking_error": benchmark.calc_tracking_error(prices, bench, weights)} if bench is not None else {}),
        **({"excess_returns": benchmark.calc_excess_returns(prices, bench, weights)} if bench is not None else {}),
    },
    "sector": lambda prices, weights, bench: {},  # Handled separately (needs holding data, not prices)
}


def execute_analysis_node(state: PortfolioState) -> dict[str, Any]:
    """Run all required metric functions based on the classified intent.

    This is a PURE COMPUTATION node — no LLM calls.
    """
    portfolio = state.get("portfolio")
    intent_dict = state.get("intent", {})
    market_data = state.get("market_data", {})

    if not portfolio or not intent_dict or not market_data:
        return {"analysis_results": {"error": "Missing portfolio, intent, or market data"}}

    intent = IntentClassification(**intent_dict)
    required_metrics = intent.required_metrics

    logger.info(f"Running metrics: {required_metrics}")

    # Deserialize price data
    close_prices_json = market_data.get("close_prices")
    if not close_prices_json:
        return {"analysis_results": {"error": "No price data available"}}

    close_prices = pd.read_json(close_prices_json)
    close_prices.index = pd.to_datetime(close_prices.index)
    close_prices = close_prices.sort_index()

    # Deserialize benchmark data
    nifty_json = market_data.get("nifty50")
    bench_series = None
    if nifty_json:
        bench_series = pd.read_json(nifty_json, typ="series")
        bench_series.index = pd.to_datetime(bench_series.index)
        bench_series = bench_series.sort_index()

    # Portfolio weights
    weights = portfolio.weights

    # Run each required metric module
    all_results: dict[str, Any] = {}

    for metric_name in required_metrics:
        if metric_name == "sector":
            # Sector analysis uses holding data, not prices
            holdings_data = [
                {
                    "ticker": h.ticker,
                    "sector": h.sector,
                    "industry": h.industry,
                    "investment_value": h.investment_value,
                    "current_value": h.current_value,
                }
                for h in portfolio.holdings
            ]
            sector_breakdown = sector.calc_sector_breakdown(holdings_data)
            sector_conc = sector.calc_sector_concentration(holdings_data)

            # Include correlation data for hidden concentration check
            corr_data = all_results.get("correlation_matrix")
            hidden = sector.identify_hidden_concentration(holdings_data, corr_data)

            all_results["sector"] = {
                "sector_breakdown": sector_breakdown,
                "sector_concentration": sector_conc,
                "hidden_concentration": hidden,
            }
        elif metric_name in METRIC_RUNNERS:
            try:
                results = METRIC_RUNNERS[metric_name](close_prices, weights, bench_series)
                all_results[metric_name] = results
            except Exception as e:
                logger.error(f"Metric {metric_name} failed: {e}")
                all_results[metric_name] = {"error": str(e)}
        else:
            logger.warning(f"Unknown metric module: {metric_name}")

    logger.info(f"Analysis complete: {list(all_results.keys())}")
    return {"analysis_results": all_results}
