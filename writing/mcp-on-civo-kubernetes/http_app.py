"""Serve the warehouse MCP server over streamable HTTP, with a bearer token,
per-tool rate limits and a health check, ready for Kubernetes."""
import hmac
import os
import time
from collections import defaultdict

import uvicorn
from starlette.responses import JSONResponse, PlainTextResponse

from server import server

TOKEN = os.environ["MCP_TOKEN"].encode()
# calls allowed per tool per minute, per pod
LIMITS = {"run_query": 20, "describe_table": 60, "list_tables": 60}


class TokenBucket:
    def __init__(self):
        self.state = defaultdict(lambda: (0.0, 0.0))  # key -> (tokens, last_refill)

    def allow(self, key: str, per_minute: int) -> bool:
        tokens, last = self.state[key]
        now = time.monotonic()
        tokens = min(per_minute, tokens + (now - last) * per_minute / 60) if last else per_minute
        if tokens < 1:
            self.state[key] = (tokens, now)
            return False
        self.state[key] = (tokens - 1, now)
        return True


buckets = TokenBucket()
_call_tool = server.call_tool


async def limited_call_tool(name, arguments, context=None):
    if not buckets.allow(name, LIMITS.get(name, 30)):
        raise RuntimeError(f"rate limit: at most {LIMITS.get(name, 30)} {name} calls per minute")
    return await _call_tool(name, arguments, context)


server.call_tool = limited_call_tool


@server.custom_route("/healthz", methods=["GET"])
async def healthz(request):
    return PlainTextResponse("ok")


mcp_app = server.streamable_http_app(stateless_http=True, json_response=True, host="0.0.0.0")


async def app(scope, receive, send):
    """Reject anything without the right bearer token, except the health check."""
    if scope["type"] == "http" and scope["path"] != "/healthz":
        auth = dict(scope["headers"]).get(b"authorization", b"")
        if not hmac.compare_digest(auth, b"Bearer " + TOKEN):
            await JSONResponse({"error": "unauthorized"}, status_code=401)(scope, receive, send)
            return
    await mcp_app(scope, receive, send)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
