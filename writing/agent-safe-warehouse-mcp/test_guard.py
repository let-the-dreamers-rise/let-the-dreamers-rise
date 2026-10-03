"""Adversarial tests: what a prompt-injected agent might try, and which layer stops it."""
import os

import psycopg
import pytest

from guard import MAX_ROWS, UnsafeQuery, check

ATTACKS = [
    "DROP TABLE analytics.users",
    "SELECT 1; DELETE FROM analytics.users",
    "WITH gone AS (DELETE FROM analytics.users RETURNING *) SELECT * FROM gone",
    "SELECT * FROM analytics.payroll",
    "SELECT * FROM payroll",
    'SELECT * FROM "PAYROLL"',
    "SELECT * FROM users JOIN payroll ON true",
    "SELECT * FROM users WHERE id IN (SELECT 1 FROM payroll)",
    "SELECT * FROM pg_catalog.pg_authid",
    "SELECT * FROM pg_shadow",
    "SELECT * FROM information_schema.tables",
    "SELECT pg_read_file('/etc/passwd')",
    "SELECT pg_sleep(60)",
    "SELECT set_config('default_transaction_read_only', 'off', false)",
    "SELECT * INTO stolen FROM users",
    "COPY users TO '/tmp/out.csv'",
    "SET ROLE postgres",
    "UPDATE users SET email = 'x'",
    "GRANT SELECT ON payroll TO agent_ro",
    "SELECT * FROM dblink('host=evil', 'select 1') AS t(x int)",
]


@pytest.mark.parametrize("sql", ATTACKS)
def test_guard_rejects(sql):
    with pytest.raises(UnsafeQuery):
        check(sql)


@pytest.mark.parametrize("sql", [
    "SELECT count(*) FROM purchases",
    "select u.name, count(*) from users u join purchases p on p.user_id = u.id group by u.name order by 2 desc",
    "WITH top AS (SELECT product_id, count(*) n FROM purchases GROUP BY 1) SELECT * FROM top ORDER BY n DESC",
    "SELECT * FROM analytics.products WHERE price > 30",
])
def test_guard_allows_analytics(sql):
    assert check(sql).endswith(f"LIMIT {MAX_ROWS}")


AGENT_DSN = os.environ.get("AGENT_DSN")


@pytest.mark.skipif(not AGENT_DSN, reason="needs AGENT_DSN for the database layer")
@pytest.mark.parametrize("sql", [
    "DROP TABLE analytics.users",
    "DELETE FROM analytics.users",
    "SELECT * FROM analytics.payroll",
    "SET default_transaction_read_only = off; DELETE FROM analytics.users",
    "SELECT pg_sleep(10)",
])
def test_database_layer_holds_even_without_the_guard(sql):
    """Pretend the guard has a bug: the role and settings must still stop the attack."""
    with psycopg.connect(AGENT_DSN) as conn:
        with pytest.raises(psycopg.Error):
            conn.execute(sql)
    with psycopg.connect(AGENT_DSN) as conn:
        assert conn.execute("SELECT count(*) FROM analytics.users").fetchone()[0] == 1000


@pytest.mark.skipif(not AGENT_DSN, reason="needs AGENT_DSN")
def test_row_cap_end_to_end():
    with psycopg.connect(AGENT_DSN) as conn:
        rows = conn.execute(check("SELECT * FROM purchases")).fetchall()
    assert len(rows) == MAX_ROWS
