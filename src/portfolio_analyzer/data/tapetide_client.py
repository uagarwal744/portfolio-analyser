"""Tapetide MCP client for Indian stock market data.

Uses the Tapetide MCP server (https://mcp.tapetide.com/mcp) via the official
MCP python SDK (HTTP stateless transport) with Bearer token authentication.
"""

import json
import logging
import os
from contextlib import AsyncExitStack
from typing import Any, Optional

import httpx
from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.types import TextContent

load_dotenv()

logger = logging.getLogger(__name__)


class TapetideError(Exception):
    """Error from Tapetide MCP server."""
    pass


class TapetideClient:
    """HTTP-based MCP client for the Tapetide stock data server."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_token: Optional[str] = None,
        timeout: float = 30.0,
    ):
        self.base_url = base_url or os.getenv(
            "TAPETIDE_MCP_URL", "https://mcp.tapetide.com/mcp"
        )
        self.api_token = api_token or os.getenv("TAPETIDE_API_TOKEN", "")
        self.timeout = timeout

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Call a Tapetide MCP tool and return the result.

        Connects via HTTP stateless transport, initializes the session, and calls the tool.
        
        Args:
            tool_name: Name of the MCP tool (e.g., 'search_stocks').
            arguments: Tool-specific arguments.

        Returns:
            The parsed tool result content.

        Raises:
            TapetideError: If the server returns an error.
        """
        logger.debug(f"Tapetide MCP call: {tool_name}({arguments})")
        
        headers = {}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"

        try:
            async with AsyncExitStack() as stack:
                http_client = httpx.AsyncClient(headers=headers, timeout=self.timeout)
                # Ensure the client is closed properly if not handled by the context
                stack.push_async_callback(http_client.aclose)
                
                stream_transport = await stack.enter_async_context(
                    streamable_http_client(self.base_url, http_client=http_client)
                )
                
                # streamable_http_client returns (read_transport, write_transport)
                read_t, write_t = stream_transport[0], stream_transport[1]
                
                session = await stack.enter_async_context(
                    ClientSession(read_t, write_t)
                )
                await session.initialize()
                
                result = await session.call_tool(tool_name, arguments=arguments)
                
                if result.isError:
                    error_msgs = [c.text for c in result.content if isinstance(c, TextContent)]
                    err = " | ".join(error_msgs) if error_msgs else "Unknown tool error"
                    raise TapetideError(f"{tool_name}: {err}")
                
                if result.content:
                    first = result.content[0]
                    if isinstance(first, TextContent):
                        try:
                            return json.loads(first.text)
                        except (json.JSONDecodeError, TypeError):
                            return first.text
                    return first
                
                return {}
                
        except Exception as e:
            logger.error(f"Tapetide error for {tool_name}: {e}")
            if isinstance(e, TapetideError):
                raise
            raise TapetideError(f"{tool_name} connection failed: {e}")

    # ── Convenience methods ──

    async def search_stock(self, query: str) -> list[dict]:
        """Search for a stock by name, symbol, or ISIN."""
        result = await self.call_tool("search_stocks", {"query": query})
        if isinstance(result, list):
            return result
        if isinstance(result, dict) and "stocks" in result:
            return result["stocks"]
        return [result] if result else []

    async def get_company_profile(
        self, symbol: str, include_technicals: bool = False
    ) -> dict:
        """Get comprehensive company profile including sector, fundamentals."""
        args: dict[str, Any] = {"symbol": symbol}
        if include_technicals:
            args["include_technicals"] = True
        return await self.call_tool("get_company_profile", args)

    async def get_stock_quote(self, symbol: str) -> dict:
        """Get current price, change, volume, market cap, PE, PB, 52W range."""
        return await self.call_tool("get_stock_quote", {"symbol": symbol})

    async def get_batch_quotes(self, symbols: list[str]) -> list[dict]:
        """Get quotes for up to 20 stocks in one call."""
        result = await self.call_tool("get_batch_quotes", {"symbols": symbols})
        if isinstance(result, list):
            return result
        if isinstance(result, dict) and "quotes" in result:
            return result["quotes"]
        return []

    async def get_price_history(
        self, symbol: str, days: int = 365, interval: str = "daily"
    ) -> dict:
        """Get historical OHLCV data."""
        return await self.call_tool(
            "get_price_history",
            {"symbol": symbol, "days": min(days, 2000), "interval": interval},
        )

    async def get_financials(self, symbol: str, period: str = "annual") -> dict:
        """Get P&L, balance sheet, cash flow, ratios."""
        return await self.call_tool(
            "get_financials", {"symbol": symbol, "period": period}
        )

    async def get_shareholding(self, symbol: str) -> dict:
        """Get promoter, FII, DII, and public holdings over time."""
        return await self.call_tool("get_shareholding", {"symbol": symbol})

    async def get_market_valuations(self, index: str = "nifty50") -> dict:
        """Get PE/PB/DY over time for major indices."""
        return await self.call_tool("market_valuations", {"index": index})

    async def get_fii_dii_detail(self, period: str = "monthly") -> dict:
        """Get institutional flows with F&O participant positioning."""
        return await self.call_tool("get_fii_dii_detail", {"period": period})

    async def get_fpi_sectors(self) -> dict:
        """Get FPI sector-wise AUM and flows."""
        return await self.call_tool("get_fpi_sectors", {})
