# Portfolio Analyzer — Next Steps & Roadmap

This document outlines planned improvements across five key areas, focusing on medium and long-term goals.

---

## 1. UI/UX

- [ ] **Multi-tab dashboard** — Separate dashboard tabs for Risk, Returns, Sector, and a unified Overview tab.
- [ ] **Export functionality** — Download analysis as PDF report or share via link.
- [ ] **React/Next.js frontend** — Migrate to a custom React frontend for richer interactivity and state management.
- [ ] **Multi-lingual support** — Add support for multiple languages in the user interface.

---

## 2. Data Ingestion

- [ ] **Broker API integration** — Direct OAuth-based import from Zerodha Kite, Groww, etc. to fetch live holdings.
- [ ] **Mutual fund & ETF support** — Parse and analyze MF/ETF holdings alongside equities.
- [ ] **Transaction history** — Accept buy/sell transaction logs to compute realized P&L and XIRR.
- [ ] **Real-time price feeds** — WebSocket-based live price updates for current portfolio value.
- [ ] **S3/GCS upload** — Cloud storage support for production deployments.

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
