"""Tapetide MCP client for Indian stock market data.

Uses the Tapetide MCP server (https://mcp.tapetide.com/mcp) via JSON-RPC
over HTTP with Bearer token authentication.
"""

import logging
import os
from typing import Any, Optional

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# MCP JSON-RPC constants
JSONRPC_VERSION = "2.0"
MCP_CALL_TOOL_METHOD = "tools/call"


class TapetideError(Exception):
    """Error from Tapetide MCP server."""
    pass


class TapetideClient:
    """HTTP-based MCP client for the Tapetide stock data server.

    Communicates via JSON-RPC 2.0 over HTTP POST requests.
    All tool calls go through the standard MCP `tools/call` method.
    """

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
        self._request_id = 0

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        return headers

    def _build_request(self, tool_name: str, arguments: dict[str, Any]) -> dict:
        """Build a JSON-RPC 2.0 request for MCP tools/call."""
        return {
            "jsonrpc": JSONRPC_VERSION,
            "id": self._next_id(),
            "method": MCP_CALL_TOOL_METHOD,
            "params": {
                "name": tool_name,
                "arguments": arguments,
            },
        }

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Call a Tapetide MCP tool and return the result.

        Args:
            tool_name: Name of the MCP tool (e.g., 'search_stocks').
            arguments: Tool-specific arguments.

        Returns:
            The tool result content.

        Raises:
            TapetideError: If the server returns an error.
        """
        payload = self._build_request(tool_name, arguments)
        logger.debug(f"Tapetide MCP call: {tool_name}({arguments})")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                self.base_url,
                json=payload,
                headers=self._headers(),
            )
            response.raise_for_status()
            data = response.json()

        if "error" in data:
            error = data["error"]
            msg = error.get("message", str(error))
            logger.error(f"Tapetide error for {tool_name}: {msg}")
            raise TapetideError(f"{tool_name}: {msg}")

        result = data.get("result", {})
        # MCP tool results come in a 'content' array
        content = result.get("content", [])
        if content and isinstance(content, list):
            # Return the text content of the first content block
            first = content[0]
            if isinstance(first, dict) and first.get("type") == "text":
                import json
                try:
                    return json.loads(first["text"])
                except (json.JSONDecodeError, TypeError):
                    return first["text"]
            return first
        return result

    # ── Convenience methods ──

    async def search_stock(self, query: str) -> list[dict]:
        """Search for a stock by name, symbol, or ISIN.

        Returns a list of matching stocks with symbol, name, exchange info.
        """
        result = await self.call_tool("search_stocks", {"query": query})
        if isinstance(result, list):
            return result
        if isinstance(result, dict) and "stocks" in result:
            return result["stocks"]
        return [result] if result else []

    async def get_company_profile(
        self, symbol: str, include_technicals: bool = False
    ) -> dict:
        """Get comprehensive company profile including sector, fundamentals.

        Args:
            symbol: NSE symbol (e.g., 'RELIANCE').
            include_technicals: Whether to include technical indicators.
        """
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
        """Get historical OHLCV data.

        Args:
            symbol: NSE symbol.
            days: Number of trading days of history (max 2000).
            interval: 'daily' or 'weekly'.
        """
        return await self.call_tool(
            "get_price_history",
            {"symbol": symbol, "days": min(days, 2000), "interval": interval},
        )

    async def get_financials(self, symbol: str, period: str = "annual") -> dict:
        """Get P&L, balance sheet, cash flow, ratios.

        Args:
            symbol: NSE symbol.
            period: 'quarterly' or 'annual'.
        """
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
