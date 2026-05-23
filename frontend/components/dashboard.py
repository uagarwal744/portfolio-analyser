"""Dashboard component for rendering Plotly charts from signals."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Map string alerts to Streamlit functions
ALERT_MAP = {
    "info": st.info,
    "warning": st.warning,
    "critical": st.error,
}


def render_dashboard(signals: list[dict]):
    """Render a vertical dashboard from a list of DashboardSignal dicts."""
    if not signals:
        return

    st.markdown("### 📈 Analysis Dashboard")

    for signal in signals:
        st.markdown("---")
        _render_signal(signal)


def _render_signal(signal: dict):
    """Dispatch to the correct rendering function based on signal_type."""
    sig_type = signal.get("signal_type")
    title = signal.get("title", "")
    data = signal.get("data", {})
    alert_level = signal.get("alert_level")
    desc = signal.get("description")

    st.markdown(f"#### {title}")

    if alert_level and alert_level in ALERT_MAP:
        ALERT_MAP[alert_level](desc or title)
        # If it's just a text alert (like concentration alert), we might not need a chart
        if sig_type == "concentration_alert":
            st.json(data)
            return

    # Render specific chart types
    if sig_type == "risk_gauge":
        _render_risk_gauge(data)
    elif sig_type == "sector_pie":
        _render_sector_pie(data)
    elif sig_type == "drawdown_chart":
        _render_drawdown_chart(data)
    elif sig_type == "correlation_heatmap":
        _render_correlation_heatmap(data)
    elif sig_type == "returns_chart":
        _render_returns_chart(data)
    elif sig_type == "cumulative_returns_chart":
        _render_cumulative_returns_chart(data)
    elif sig_type == "benchmark_comparison":
        _render_benchmark_comparison(data)
    elif sig_type == "var_summary":
        _render_var_summary(data)
    else:
        # Fallback for unknown signals
        st.write("Data payload:")
        st.json(data)

    if desc and not alert_level:
        st.caption(desc)


def _render_cumulative_returns_chart(data: dict):
    """Render a cumulative returns timeseries vs benchmark."""
    dates = data.get("dates", [])
    port_cumulative = data.get("portfolio_cumulative", [])
    bench_cumulative = data.get("benchmark_cumulative", [])
    
    if not dates or not port_cumulative:
        return

    # Convert to %
    port_cumulative = [v * 100 for v in port_cumulative]
    
    df_data = {"Date": pd.to_datetime(dates), "Portfolio": port_cumulative}
    
    if bench_cumulative:
        bench_cumulative = [v * 100 if v is not None else None for v in bench_cumulative]
        df_data["Benchmark"] = bench_cumulative
        
    df = pd.DataFrame(df_data)
    
    fig = px.line(df, x="Date", y=df.columns[1:])
    fig.update_layout(
        height=300,
        margin=dict(l=10, r=10, t=10, b=10),
        yaxis=dict(title="Cumulative Return (%)"),
        legend_title_text=""
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_risk_gauge(data: dict):
    """Render a Sharpe ratio gauge."""
    sharpe = data.get("sharpe_ratio", 0)
    vol = data.get("volatility")

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=sharpe,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Sharpe Ratio"},
        gauge={
            'axis': {'range': [-1, 3]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [-1, 0], 'color': "lightcoral"},
                {'range': [0, 1], 'color': "lightyellow"},
                {'range': [1, 2], 'color': "lightgreen"},
                {'range': [2, 3], 'color': "forestgreen"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': sharpe
            }
        }
    ))
    fig.update_layout(height=250, margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig, use_container_width=True)

    if vol:
        st.metric("Annualized Volatility", f"{vol*100:.1f}%")


def _render_sector_pie(data: dict):
    """Render a sector allocation donut chart."""
    breakdown = data.get("sector_breakdown", [])
    if not breakdown:
        return

    df = pd.DataFrame(breakdown)
    fig = px.pie(
        df,
        values='weight',
        names='sector',
        hole=0.4,
        hover_data=['num_stocks']
    )
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(height=350, margin=dict(l=10, r=10, t=10, b=10), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)


def _render_drawdown_chart(data: dict):
    """Render an area chart for drawdown history."""
    dates = data.get("dates", [])
    values = data.get("drawdown_values", [])

    if not dates or not values:
        # Might be a simple alert payload instead of series
        if "max_drawdown" in data:
            st.metric("Max Drawdown", f"{data['max_drawdown']*100:.1f}%")
        return

    df = pd.DataFrame({"Date": pd.to_datetime(dates), "Drawdown": values})
    
    fig = px.area(df, x="Date", y="Drawdown")
    fig.update_traces(line_color="red", fillcolor="rgba(255,0,0,0.2)")
    fig.update_layout(
        height=300,
        margin=dict(l=10, r=10, t=10, b=10),
        yaxis=dict(tickformat=".1%", title="Drawdown")
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_correlation_heatmap(data: dict):
    """Render a correlation heatmap."""
    matrix_dict = data.get("correlation_matrix", {})
    if not matrix_dict:
        return

    # Convert back to DataFrame
    df = pd.DataFrame(matrix_dict)
    
    fig = px.imshow(
        df,
        text_auto=".2f",
        aspect="auto",
        color_continuous_scale="RdBu_r",
        zmin=-1, zmax=1
    )
    fig.update_layout(height=400, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)


def _render_returns_chart(data: dict):
    """Render period returns as a bar chart."""
    period_returns = data.get("period_returns", {})
    cagr = data.get("portfolio_cagr")

    if cagr is not None:
        st.metric("CAGR (Annualized Return)", f"{cagr*100:.2f}%")

    if period_returns:
        periods = []
        returns = []
        for p, v in period_returns.items():
            if v is not None:
                periods.append(p)
                returns.append(v * 100)  # Convert to %
        
        df = pd.DataFrame({"Period": periods, "Return (%)": returns})
        
        # Color red if negative, green if positive
        colors = ['red' if r < 0 else 'green' for r in returns]
        
        fig = px.bar(df, x="Period", y="Return (%)")
        fig.update_traces(marker_color=colors)
        fig.update_layout(height=250, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)


def _render_benchmark_comparison(data: dict):
    """Render grouped bar chart for portfolio vs benchmark."""
    port_ret = data.get("portfolio_total_return", 0) * 100
    bench_ret = data.get("benchmark_total_return", 0) * 100
    
    df = pd.DataFrame({
        "Entity": ["Portfolio", "Nifty 50"],
        "Total Return (%)": [port_ret, bench_ret]
    })
    
    fig = px.bar(
        df, 
        x="Entity", 
        y="Total Return (%)", 
        color="Entity",
        color_discrete_map={"Portfolio": "#1f77b4", "Nifty 50": "#ff7f0e"}
    )
    fig.update_layout(height=250, margin=dict(l=10, r=10, t=10, b=10), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)


def _render_var_summary(data: dict):
    """Render Value at Risk metrics."""
    col1, col2 = st.columns(2)
    
    if "var_95_daily" in data:
        col1.metric("Daily VaR (95%)", f"{data['var_95_daily']*100:.2f}%", delta="Max expected loss", delta_color="inverse")
    
    if "cvar_95_daily" in data:
        col2.metric("Daily CVaR (95%)", f"{data['cvar_95_daily']*100:.2f}%", delta="Expected shortfall", delta_color="inverse")
