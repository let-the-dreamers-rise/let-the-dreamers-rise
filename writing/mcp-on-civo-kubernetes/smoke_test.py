"""End-to-end check against a running server: auth, a real query, the allow-list, the rate limit."""
import asyncio
import os
import sys

import httpx2 as httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000/mcp"
TOKEN = os.environ["MCP_TOKEN"]


async def main():
    async with httpx.AsyncClient(headers={"Authorization": f"Bearer {TOKEN}"}, timeout=30) as http:
        async with streamable_http_client(URL, http_client=http) as (read, write, *_):
            async with ClientSession(read, write) as s:
                await s.initialize()
                print("tools:", [t.name for t in (await s.list_tools()).tools])
                r = await s.call_tool("run_query", {"sql": "select count(*) as n from purchases"})
                print("query:", r.content[0].text.replace("\n", " "))
                r = await s.call_tool("run_query", {"sql": "select * from payroll"})
                print("payroll:", r.content[0].text.replace("\n", " "))
                limited = 0
                for _ in range(25):
                    r = await s.call_tool("run_query", {"sql": "select 1 as one from users limit 1"})
                    limited += bool(r.is_error)
                print("rate-limited calls out of 25:", limited)


asyncio.run(main())
