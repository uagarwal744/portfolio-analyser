import asyncio
from mcp.client.streamable_http import streamable_http_client
from mcp import ClientSession
from contextlib import AsyncExitStack
import httpx

async def main():
    headers = {"Authorization": "Bearer tpt_rt_eb965978426e2bb58c7e3448f5b5e78fc8d1aee9885ea690b9c3ad0d"}
    url = "https://mcp.tapetide.com/mcp"
    print(f"Trying {url}")
    try:
        async with AsyncExitStack() as stack:
            client = httpx.AsyncClient(headers=headers)
            stream = await stack.enter_async_context(streamable_http_client(url, http_client=client))
            session = await stack.enter_async_context(ClientSession(stream[0], stream[1]))
            await session.initialize()
            print("Session initialized successfully!")
            result = await session.call_tool("search_stocks", arguments={"query": "RELIANCE"})
            print(f"Success! {result}")
    except Exception as e:
        print(f"Failed: {repr(e)}")

asyncio.run(main())
