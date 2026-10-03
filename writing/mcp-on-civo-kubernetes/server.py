"""A read-only MCP server over an Airbyte-loaded Postgres warehouse."""
import os

import psycopg
from mcp.server.mcpserver import MCPServer

from guard import ALLOWED_TABLES, UnsafeQuery, check

DSN = os.environ["WAREHOUSE_DSN"]  # postgresql://agent_ro:...@host/db
server = MCPServer("warehouse", instructions="Read-only access to the analytics warehouse.")


def _run(sql: str, params=None) -> list[dict]:
    # Layer 3: every call is its own read-only transaction with a hard timeout.
    with psycopg.connect(DSN, autocommit=False) as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        conn.execute("SET LOCAL statement_timeout = '5s'")
        cur = conn.execute(sql, params)
        cols = [c.name for c in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        conn.rollback()
        return rows


@server.tool()
def list_tables() -> list[str]:
    """List the tables you are allowed to query."""
    return sorted(ALLOWED_TABLES)


@server.tool()
def describe_table(table: str) -> list[dict]:
    """Show the columns and types of one allowed table."""
    if table not in ALLOWED_TABLES:
        raise ValueError(f"unknown table {table!r}; call list_tables first")
    return _run(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_schema = 'analytics' AND table_name = %s ORDER BY ordinal_position",
        (table,),
    )


@server.tool()
def run_query(sql: str) -> list[dict]:
    """Run one read-only SELECT against the allowed tables. Results are capped at 200 rows."""
    try:
        safe = check(sql)
    except UnsafeQuery as e:
        return [{"error": str(e)}]
    return _run(safe)


if __name__ == "__main__":
    server.run()
