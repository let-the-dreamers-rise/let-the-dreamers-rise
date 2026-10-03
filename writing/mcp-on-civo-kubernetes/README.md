# Deploy a production MCP server on Civo Kubernetes

*Ashwin Goyal ([let-the-dreamers-rise](https://github.com/let-the-dreamers-rise)), October 2026*

The [Model Context Protocol](https://modelcontextprotocol.io) is how AI agents like Claude Code and Cursor reach tools and data. Almost every MCP tutorial ends with a server on `localhost` talking to one person's editor over stdio. That's fine for a demo. It's not fine once a team shares the server, it sits next to real data, and it has to stay up.

This tutorial takes an MCP server to a Civo K3s cluster with the pieces production needs:

- streamable HTTP transport, so any MCP client can connect over the network
- a bearer token on every request
- per-tool rate limits, so a looping agent can't hammer your database
- a health check, a non-root read-only container, and two replicas
- HTTPS through Traefik and cert-manager

The server is a read-only gateway to a Postgres warehouse, built in [a companion tutorial](../agent-safe-warehouse-mcp/). The same steps apply to any MCP server you write.

## 1. Expose the server over HTTP

Locally, an MCP server usually talks over stdio. In a cluster it has to listen on a port. The MCP Python SDK can serve any server as an ASGI app, and [`http_app.py`](http_app.py) wraps that app in three things.

**A bearer token, compared in constant time.** Every request except the health check needs the token:

```python
async def app(scope, receive, send):
    if scope["type"] == "http" and scope["path"] != "/healthz":
        auth = dict(scope["headers"]).get(b"authorization", b"")
        if not hmac.compare_digest(auth, b"Bearer " + TOKEN):
            await JSONResponse({"error": "unauthorized"}, status_code=401)(scope, receive, send)
            return
    await mcp_app(scope, receive, send)
```

**Rate limits per tool.** An agent stuck in a loop will call the same tool hundreds of times a minute. A token bucket in front of `call_tool` caps the expensive tool (`run_query`, 20 a minute) harder than the cheap ones. The limit is per pod, so with two replicas the effective ceiling is roughly double. If you need a strict global limit, move the buckets to Redis.

**Stateless HTTP.** `streamable_http_app(stateless_http=True, json_response=True)` means any replica can answer any request. You don't need sticky sessions, and scaling is just changing a number.

## 2. Build a small, locked-down image

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY guard.py server.py http_app.py ./
RUN useradd --uid 10001 app
USER 10001
EXPOSE 8000
CMD ["python", "http_app.py"]
```

Build it and push it to any registry your cluster can pull from:

```bash
docker build -t ghcr.io/YOUR_USER/warehouse-mcp:1.0.0 .
docker push ghcr.io/YOUR_USER/warehouse-mcp:1.0.0
```

Before going near Kubernetes, run it with the same restrictions the cluster will apply. This step catches most "works locally, crashes in the pod" surprises:

```bash
docker run --rm --read-only --cap-drop ALL --security-opt no-new-privileges \
  -p 8000:8000 -e MCP_TOKEN=dev-token \
  -e WAREHOUSE_DSN="postgresql://agent_ro:...@host.docker.internal:5432/shop" \
  ghcr.io/YOUR_USER/warehouse-mcp:1.0.0

MCP_TOKEN=dev-token python smoke_test.py http://localhost:8000/mcp
```

[`smoke_test.py`](smoke_test.py) connects with the official MCP client and checks four things: it can list tools, a real query works, the allow-list blocks a forbidden table, and the rate limit kicks in. Expected output:

```
tools: ['list_tables', 'describe_table', 'run_query']
query: {   "n": 5000 }
payroll: {   "error": "table payroll is not on the allow-list" }
rate-limited calls out of 25: 7
```

(Two `run_query` calls came before the loop, so 18 of the 25 fit under the limit of 20 and 7 are refused.)

## 3. Create the cluster

With the [Civo CLI](https://www.civo.com/docs/overview/civo-cli):

```bash
civo kubernetes create mcp-demo --nodes 2 --size g4s.kube.small \
  --applications cert-manager --wait --save --merge --switch
```

Civo's K3s clusters come with Traefik as the ingress controller, and `--applications cert-manager` installs cert-manager from the Civo marketplace in the same step. Point a DNS record (say `mcp.example.com`) at the cluster's public IP from `civo kubernetes show mcp-demo`.

## 4. Deploy

Put the secrets in a Secret, not in the manifest:

```bash
kubectl create secret generic warehouse-mcp \
  --from-literal=MCP_TOKEN="$(openssl rand -hex 32)" \
  --from-literal=WAREHOUSE_DSN="postgresql://agent_ro:...@your-db:5432/shop"
```

[`k8s/deployment.yaml`](k8s/deployment.yaml) runs two replicas with readiness and liveness probes on `/healthz`, CPU and memory limits, and a container security context that matches the `docker run` flags above (non-root, read-only root filesystem, all capabilities dropped). [`k8s/ingress.yaml`](k8s/ingress.yaml) adds a Let's Encrypt `ClusterIssuer` and an Ingress for your hostname. Edit the image, email and host, then apply:

```bash
kubectl apply -f k8s/
kubectl rollout status deploy/warehouse-mcp
kubectl get certificate   # READY becomes True once Let's Encrypt has issued it
```

Run the smoke test against the real endpoint:

```bash
MCP_TOKEN=$(kubectl get secret warehouse-mcp -o jsonpath='{.data.MCP_TOKEN}' | base64 -d) \
  python smoke_test.py https://mcp.example.com/mcp
```

## 5. Connect an agent

```bash
claude mcp add --transport http warehouse https://mcp.example.com/mcp \
  --header "Authorization: Bearer $MCP_TOKEN"
```

Everyone on the team now points their agent at the same server, with the same guardrails, and you only have to patch it in one place.

## What to check before calling it production

- **Rotate the token.** Update the Secret, then run `kubectl rollout restart deploy/warehouse-mcp`. Better still, give each client its own token so you can revoke one without breaking everyone.
- **Logs.** Uvicorn logs every request. Ship them somewhere with retention, because "what did the agent run?" is the first question after any incident.
- **Network policy.** Allow egress from these pods only to the database.
- **Scale on purpose.** The limits are per pod. Raise replicas for availability, not to let one agent run more queries.

Taking an MCP server from a laptop to a cluster comes down to three changes: HTTP instead of stdio, a token instead of trust, and limits instead of hope.
