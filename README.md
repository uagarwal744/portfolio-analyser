# Portfolio Analyzer

A full-stack, AI-powered stock portfolio analyzer built for the Indian stock market. It uses an agentic **LangGraph** pipeline orchestrated by a **FastAPI** backend, and a modern, responsive **Streamlit** frontend with interactive **Plotly** visualizations.

## Key Features

*   **Agentic Pipeline (LangGraph)**: Uses Gemini models to understand natural language intent, routing conversations logically to deterministic metric engines.
*   **Tapetide MCP Integration**: Connects to the [Tapetide MCP Server](https://mcp.tapetide.com/mcp) via the official stateless HTTP transport to fetch comprehensive Indian stock market data (company profiles, quotes, sector mappings, etc).
*   **Deterministic Financial Metrics**: Performs deep mathematical analysis using `pandas` and `numpy`—bypassing LLM hallucinations for strict numerical accuracy.
    *   **Returns Analysis**: Historical returns, CAGR, and rolling returns.
    *   **Risk Metrics**: Annualized Volatility, Sharpe Ratio, Sortino Ratio, Beta.
    *   **Drawdowns**: Max drawdown, recovery periods, and historical drawdown series.
    *   **Value at Risk (VaR)**: Historical and CVaR calculations.
    *   **Benchmark Comparisons**: Live tracking against the Nifty 50, computing Jensen's Alpha and Tracking Error.
    *   **Sector & Concentration**: Identifies hidden risk concentrations and calculates the Herfindahl index.
    *   **Gold Analysis**: Comparative analysis against gold prices.
*   **Dynamic Dashboard**: Generates structured `DashboardSignal`s mapped to Plotly graphs (Heatmaps, Pie Charts, Gauges, Area Charts) rendered seamlessly in the Streamlit UI alongside an interactive chat interface.
*   **Smart Follow-ups**: Generates context-aware follow-up questions to drive deeper analysis.

## Tech Stack

*   **Backend**: FastAPI, LangGraph, Pydantic
*   **LLM Integration**: LangChain Google GenAI
*   **Market Data**: Official MCP Python SDK (Stateless HTTP), `yfinance`
*   **Frontend**: Streamlit, Plotly Express/Graph Objects
*   **Data Science**: Pandas, NumPy

## Setup & Installation

1. **Environment Setup**:
   Create a `.env` file in the root directory and add the following keys:
   ```env
   GEMINI_API_KEY=your_gemini_api_key
   TAPETIDE_MCP_URL=https://mcp.tapetide.com/mcp
   TAPETIDE_API_TOKEN=your_tapetide_bearer_token
   RISK_FREE_RATE=0.07
   ```

2. **Install Dependencies**:
   Ensure you have Python 3.10+ installed, then install the dependencies (preferably within a virtual environment):
   ```bash
   pip install -r requirements.txt
   # OR if using poetry/pyproject.toml:
   pip install .
   ```

3. **Run the Application**:
   Use the unified launcher to concurrently start both the FastAPI backend and Streamlit frontend.
   ```bash
   python run.py
   ```
   *   The FastAPI server will run on `http://localhost:8000`
   *   The Streamlit frontend will open automatically at `http://localhost:8501`

## Usage

1. **Upload your Portfolio**: Paste a comma-separated text snippet or upload a CSV containing `ticker`, `quantity`, and `buy_price` headers (e.g., `RELIANCE, 50, 2450`).
2. **Analyze**: Ask questions like:
   *   *"What's my overall risk profile?"*
   *   *"Show me my sector exposure and concentration."*
   *   *"How does my portfolio compare to Nifty 50 over the last year?"*
3. **Explore**: View the dynamic Plotly charts generated alongside the AI's natural language summary.
