"""Dashboard signal models for frontend consumption."""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class DashboardSignalType(str, Enum):
    """Types of dashboard widgets/charts the frontend can render."""

    RISK_GAUGE = "risk_gauge"
    CORRELATION_HEATMAP = "correlation_heatmap"
    SECTOR_PIE = "sector_pie"
    DRAWDOWN_CHART = "drawdown_chart"
    RETURNS_CHART = "returns_chart"
    CUMULATIVE_RETURNS_CHART = "cumulative_returns_chart"
    BENCHMARK_COMPARISON = "benchmark_comparison"
    CONCENTRATION_ALERT = "concentration_alert"
    VAR_SUMMARY = "var_summary"
    PORTFOLIO_SUMMARY = "portfolio_summary"
    HOLDINGS_TABLE = "holdings_table"


class AlertLevel(str, Enum):
    """Severity levels for dashboard alerts."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class DashboardSignal(BaseModel):
    """A structured signal that the frontend can use to render/update a dashboard widget."""

    signal_type: DashboardSignalType = Field(
        description="The type of dashboard widget this signal targets."
    )
    title: str = Field(
        description="Human-readable title for the widget."
    )
    data: dict[str, Any] = Field(
        description="Chart-ready data payload. Structure depends on signal_type."
    )
    priority: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Display priority (1 = highest, 10 = lowest).",
    )
    alert_level: Optional[AlertLevel] = Field(
        default=None,
        description="If set, indicates this signal carries an alert.",
    )
    description: Optional[str] = Field(
        default=None,
        description="Optional description or insight text for the widget.",
    )
