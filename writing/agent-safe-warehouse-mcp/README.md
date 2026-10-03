# Give an AI agent safe access to your data warehouse with an MCP server

*Ashwin Goyal ([let-the-dreamers-rise](https://github.com/let-the-dreamers-rise)), October 2026*

Your data is finally in one place. Airbyte syncs your app database, your payments provider and your CRM into Postgres every hour. The next thing everyone asks for is obvious: "let me just ask Claude about it."

The quick way to do that is to hand an agent a connection string. Don't. An agent reads text from places you don't control: a support ticket, a product review, a customer's name. Any of that text can contain instructions, and a model that follows them with a superuser connection can drop a table, read the payroll, or run a query that pins your warehouse at 100% CPU.

This tutorial builds the other way to do it: a small [Model Context Protocol](https://modelcontextprotocol.io) server that lets an agent ask real analytical questions, and a test suite that proves a hijacked agent can't get out of its box. All the code is in this folder and every test in it passes against Postgres 16.

## What we're building

```
Airbyte (Faker source) ──sync──▶ Postgres "analytics" schema
                                        ▲
                     read-only role ────┘   (layer 1: the database says no)
                                        ▲
                     SQL guard ─────────┘   (layer 2: we never send unsafe SQL)
                                        ▲
                     MCP server ────────┘   (layer 3: read-only txn, timeout, row cap)
                                        ▲
                          Claude Code / any MCP client
```

Three layers, on purpose. Each one is simple enough to reason about, and the tests check that every layer holds on its own, so one bug doesn't open the whole warehouse.

## Step 1: load some data with Airbyte

In Airbyte, add the **Sample Data (Faker)** source (it produces `users`, `products` and `purchases` streams) and a **Postgres** destination. In the destination settings, set the default schema to `analytics`. Create a connection between them and run a sync.

Airbyte writes typed final tables into `analytics` and keeps its raw copies in a separate `airbyte_internal` schema. That separation matters: the agent should only ever see the clean tables.

For this tutorial I also added a table the agent must never read, `analytics.payroll`, to stand in for the sensitive table that always ends up in the same schema sooner or later. (`seed.sql` creates the same tables locally if you want to follow along without Airbyte.)

## Step 2: layer 1, a role that can only read three tables

```sql
CREATE ROLE agent_ro LOGIN PASSWORD 'change-me';
ALTER ROLE agent_ro SET default_transaction_read_only = on;
ALTER ROLE agent_ro SET statement_timeout = '5s';
ALTER ROLE agent_ro SET search_path = analytics;

REVOKE ALL ON SCHEMA public FROM agent_ro;
GRANT USAGE ON SCHEMA analytics TO agent_ro;
GRANT SELECT ON analytics.users, analytics.products, analytics.purchases TO agent_ro;
```

This is the layer that matters most, because it doesn't depend on any of our code being right. The role has `SELECT` on exactly three tables and nothing else. Even if the agent somehow runs `SET default_transaction_read_only = off`, it still holds no `DELETE` privilege. A five-second statement timeout stops it from running a cross join that never ends.

## Step 3: layer 2, a SQL guard

The database will refuse bad queries, but we'd rather never send them. That keeps the error messages useful to the model and the database logs quiet. [`guard.py`](guard.py) parses the query with [sqlglot](https://github.com/tobymao/sqlglot) instead of matching strings, because regexes on SQL lose to comments, quoting and CTEs every time:

```python
def check(sql: str) -> str:
    statements = [s for s in sqlglot.parse(sql, read="postgres") if s is not None]
    if len(statements) != 1:
        raise UnsafeQuery("exactly one statement is allowed")
    tree = statements[0]
    if not isinstance(tree, (exp.Select, exp.Union, exp.Intersect, exp.Except)):
        raise UnsafeQuery(f"only SELECT is allowed, got {tree.key.upper()}")
    # ...no INSERT/UPDATE/DELETE/INTO hiding inside a CTE or subquery
    # ...every table reference must be on the allow-list (CTE names excepted)
    # ...no pg_sleep, pg_read_file, dblink, set_config, ...
    return f"SELECT * FROM ({inner}) AS agent_query LIMIT {MAX_ROWS}"
```

Two details are easy to get wrong:

- **Walk the whole tree.** `WITH gone AS (DELETE FROM users RETURNING *) SELECT * FROM gone` is a valid Postgres statement whose top node is a `SELECT`. Checking only the top would let it through.
- **Wrap, don't append.** Adding `LIMIT 200` to the end of the agent's SQL breaks on queries that already have a limit or end in a comment. Wrapping the whole query in a subquery always works.

## Step 4: layer 3, the MCP server

[`server.py`](server.py) exposes three tools: `list_tables`, `describe_table` and `run_query`. Every call runs in its own read-only transaction with its own timeout, and is rolled back afterwards:

```python
@server.tool()
def run_query(sql: str) -> list[dict]:
    """Run one read-only SELECT against the allowed tables. Results are capped at 200 rows."""
    try:
        safe = check(sql)
    except UnsafeQuery as e:
        return [{"error": str(e)}]
    return _run(safe)
```

When the guard refuses a query, the server returns the reason as data instead of raising. A model that reads "table payroll is not on the allow-list" rewrites its query. A model that gets a stack trace usually just tries again.

## Step 5: prove it with adversarial tests

This is the part most tutorials skip. [`test_guard.py`](test_guard.py) is a list of things a prompt-injected agent might try, and each one has to fail:

| Attack | Stopped by |
|---|---|
| `DROP TABLE`, `UPDATE`, `GRANT`, `COPY ... TO`, `SET ROLE` | guard (not a SELECT) and role (no privilege) |
| `SELECT 1; DELETE FROM users` | guard (one statement only) |
| `WITH gone AS (DELETE ...) SELECT * FROM gone` | guard (DML inside a CTE) |
| `SELECT * FROM payroll`, `"PAYROLL"`, a join or subquery that reaches it | guard (allow-list) and role (no grant) |
| `pg_shadow`, `pg_authid`, `information_schema.tables` | guard (allow-list) |
| `pg_read_file('/etc/passwd')`, `dblink(...)` | guard (blocked function) |
| `pg_sleep(60)` | guard, and the statement timeout |
| `SELECT * INTO stolen FROM users` | guard (INTO) |

A second set of tests switches the guard off completely and fires attacks straight at the `agent_ro` connection. They have to fail too, which shows the database layer holds even if the guard has a bug. Further tests confirm normal analytics questions (joins, group-bys, CTEs) still work and that results are capped at 200 rows.

```
$ AGENT_DSN="postgresql://agent_ro:...@localhost/shop" pytest -q
30 passed in 2.26s
```

## Step 6: connect an agent

```bash
pip install -r requirements.txt
claude mcp add warehouse \
  --env WAREHOUSE_DSN="postgresql://agent_ro:change-me@localhost:5432/shop" \
  -- python server.py
```

Now ask Claude Code "which product make sells best?" It should call `list_tables`, look at `purchases` and `products` with `describe_table`, write the join, and answer from the handful of rows that come back. Then ask it to "check the payroll table for me". It gets the allow-list error back and can only tell you it isn't allowed.

## What to take away

1. **Least privilege goes in the database.** The role is the one layer that doesn't trust your code.
2. **Parse SQL, don't pattern-match it.**
3. **Return refusals as data** so the model can recover.
4. **Write the attack list down as tests.** "We were careful" isn't a security property. Thirty passing tests are evidence.

The same pattern works for any destination Airbyte supports. Swap the dialect in `sqlglot.parse` and the grants for your warehouse, and the tests come along with you.
