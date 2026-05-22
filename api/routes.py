"""FastAPI routes for the portfolio analyzer."""

import logging
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from langchain_core.messages import HumanMessage

from api.schemas import (
    ChatRequest,
    ChatResponse,
    HoldingResponse,
    PortfolioResponse,
    PortfolioUploadResponse,
    PortfolioUploadTextRequest,
    SessionResponse,
)
from portfolio_analyzer.graph import get_graph
from portfolio_analyzer.state import PortfolioData, PortfolioState

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["portfolio"])


def _extract_portfolio_summary(state: PortfolioState) -> PortfolioResponse | None:
    """Extract a safe PortfolioResponse from the LangGraph state."""
    portfolio: PortfolioData | None = state.get("portfolio")
    if not portfolio or not portfolio.holdings:
        return None

    weights = portfolio.weights
    holdings = []
    sectors = set()
    total_current = 0.0

    for h in portfolio.holdings:
        if h.sector:
            sectors.add(h.sector)
        if h.current_value:
            total_current += h.current_value

        holdings.append(
            HoldingResponse(
                ticker=h.ticker,
                quantity=h.quantity,
                buy_price=h.buy_price,
                buy_date=h.buy_date,
                sector=h.sector,
                industry=h.industry,
                current_price=h.current_price,
                investment_value=h.investment_value,
                current_value=h.current_value,
                weight=weights.get(h.ticker, 0.0),
            )
        )

    return PortfolioResponse(
        holdings=holdings,
        total_invested=portfolio.total_invested,
        total_current=total_current if total_current > 0 else None,
        num_holdings=len(holdings),
        sectors=list(sectors),
    )


@router.post("/portfolio/upload/file", response_model=PortfolioUploadResponse)
async def upload_portfolio_file(
    session_id: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
):
    """Upload a portfolio CSV file."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    content = await file.read()
    text_content = content.decode("utf-8")

    return await _process_upload(session_id, text_content)


@router.post("/portfolio/upload/text", response_model=PortfolioUploadResponse)
async def upload_portfolio_text(request: PortfolioUploadTextRequest):
    """Upload a portfolio as raw CSV text."""
    return await _process_upload(request.session_id, request.content)


async def _process_upload(session_id: str, csv_content: str) -> PortfolioUploadResponse:
    """Process a portfolio upload (file or text) through the graph."""
    graph = get_graph()
    config = {"configurable": {"thread_id": session_id}}

    try:
        result = await graph.ainvoke(
            {
                "messages": [HumanMessage(content=csv_content)],
                "has_csv": True,
            },
            config=config,
        )

        error = result.get("error")
        if error:
            return PortfolioUploadResponse(
                session_id=session_id,
                success=False,
                message="Failed to parse portfolio",
                error=error,
            )

        portfolio_res = _extract_portfolio_summary(result)
        ai_message = result["messages"][-1].content if result.get("messages") else "Portfolio loaded."

        return PortfolioUploadResponse(
            session_id=session_id,
            success=True,
            message=ai_message,
            portfolio=portfolio_res,
        )

    except Exception as e:
        logger.error(f"Portfolio upload failed: {e}")
        return PortfolioUploadResponse(
            session_id=session_id,
            success=False,
            message="Internal server error during processing",
            error=str(e),
        )


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Process a user query against their portfolio."""
    graph = get_graph()
    config = {"configurable": {"thread_id": request.session_id}}

    try:
        # Check if portfolio is loaded
        state = await graph.aget_state(config)
        portfolio_loaded = state.values.get("portfolio") is not None if state and hasattr(state, "values") else False

        result = await graph.ainvoke(
            {
                "messages": [HumanMessage(content=request.message)],
                "has_csv": False,
            },
            config=config,
        )

        error = result.get("error")
        messages = result.get("messages", [])
        ai_response = messages[-1].content if messages else "No response generated."

        return ChatResponse(
            session_id=request.session_id,
            message=ai_response,
            dashboard_signals=result.get("dashboard_signals", []),
            suggested_questions=result.get("suggested_questions", []),
            portfolio_loaded=portfolio_loaded,
            error=error,
        )

    except Exception as e:
        logger.error(f"Chat failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """Get the current state of a session."""
    graph = get_graph()
    config = {"configurable": {"thread_id": session_id}}

    state = await graph.aget_state(config)
    if not state or not hasattr(state, "values"):
        return SessionResponse(session_id=session_id, has_portfolio=False)

    values = state.values
    has_portfolio = values.get("portfolio") is not None
    portfolio_res = _extract_portfolio_summary(values)
    msg_count = len([m for m in values.get("messages", []) if isinstance(m, HumanMessage)])

    return SessionResponse(
        session_id=session_id,
        has_portfolio=has_portfolio,
        portfolio=portfolio_res,
        message_count=msg_count,
    )
