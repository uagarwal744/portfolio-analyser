# Portfolio Analyzer — Next Steps & Roadmap

This document outlines planned improvements across five key areas, focusing on medium and long-term goals.

---

## 1. UI/UX

- [ ] **Multi-tab dashboard** — Separate dashboard tabs for Risk, Returns, Sector, and a unified Overview tab.
- [ ] **Export functionality** — Download analysis as PDF report or share via link.
- [ ] **React/Next.js frontend** — Migrate to a custom React frontend for richer interactivity and state management.
- [ ] **Multi-lingual support** — Add support for multiple languages in the user interface.

---

## 2. Data Ingestion and Caching

- [ ] **Broker API integration** — Direct OAuth-based import from Zerodha Kite, Groww, etc. to fetch live holdings.
- [ ] **Own MCP Server** — Build own MCP server to fetch data from NSE, BSE, and other Indian exchanges.
- [ ] **Mutual fund & ETF support** — Parse and analyze MF/ETF holdings alongside equities.
- [ ] **Real-time price feeds** — WebSocket-based live price updates for current portfolio value.

---

## 3. Performance & Risk Metrics

- [ ] **Monte Carlo simulation** — Simulate 10,000 portfolio paths to project future value distributions.
- [ ] **Stress testing** — Model impact of historical scenarios (2008 crisis, COVID crash) on current portfolio.
- [ ] **Options risk (Greeks)** — If F&O positions are included, compute delta, gamma, theta exposure.
- [ ] **Liquidity risk scoring** — Flag illiquid small-caps based on average daily volume vs position size.

---

## 4. AI Agentic Workflow

- [ ] **Planner node** — Add an explicit planning step where the agent outlines what it will compute before executing.
- [ ] **Multi-agent architecture** — Separate agents for data retrieval, quantitative analysis, and narrative synthesis.
- [ ] **RAG for financial knowledge** — Embed financial concepts and Indian market context for richer explanations.
- [ ] **News-aware analysis** — Integrate news/sentiment data to contextualize metric changes.
- [ ] **Voice interface** — Natural language voice input/output for hands-free portfolio queries.

---

## 5. Backend & Database Architecture

- [ ] **PostgreSQL** — Migrate to PostgreSQL for multi-user production deployment with proper session isolation.
- [ ] **Redis caching** — Cache Tapetide API responses and yfinance price data in Redis with TTL.
- [ ] **Dockerized deployment** — Multi-container setup (API + worker + Redis + Postgres) with docker-compose.
- [ ] **Multi-tenancy** — Isolated data partitioning for enterprise/white-label use cases.

---

## 6. Observability & Eval

- [ ] **LangSmith / LangFuse tracing** — Instrument every LangGraph run with end-to-end traces (latency per node, token usage, LLM inputs/outputs) for debugging and cost tracking.
- [ ] **Intent classification eval suite** — Build a labeled dataset of 100+ user queries with expected intents and run automated accuracy benchmarks on every prompt/model change.
- [ ] **Metric correctness tests** — Property-based tests (e.g., Hypothesis) that validate deterministic metric outputs (Sharpe, VaR, CAGR) against known reference portfolios.
- [ ] **Dashboard latency budgets** — Track and alert on P95 response times per graph path (analysis vs general vs unsupported) to catch regressions.
