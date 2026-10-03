"""Layer 2: reject unsafe SQL before it reaches the database."""
import sqlglot
from sqlglot import exp

ALLOWED_TABLES = {"users", "products", "purchases"}
ALLOWED_SCHEMAS = {"", "analytics"}
BLOCKED_FUNCTIONS = {
    "pg_sleep", "pg_read_file", "pg_read_binary_file", "pg_ls_dir", "pg_stat_file",
    "lo_import", "lo_export", "dblink", "dblink_exec", "set_config", "current_setting",
    "pg_terminate_backend", "pg_cancel_backend", "query_to_xml", "pg_reload_conf",
}
MAX_ROWS = 200


class UnsafeQuery(ValueError):
    pass


def check(sql: str) -> str:
    """Return a safe, row-capped version of `sql`, or raise UnsafeQuery."""
    try:
        statements = [s for s in sqlglot.parse(sql, read="postgres") if s is not None]
    except sqlglot.errors.ParseError as e:
        raise UnsafeQuery(f"could not parse SQL: {e}") from None
    if len(statements) != 1:
        raise UnsafeQuery("exactly one statement is allowed")
    tree = statements[0]
    if not isinstance(tree, (exp.Select, exp.Union, exp.Intersect, exp.Except)):
        raise UnsafeQuery(f"only SELECT is allowed, got {tree.key.upper()}")
    for node in tree.walk():
        if isinstance(node, (exp.Insert, exp.Update, exp.Delete, exp.Merge, exp.Create,
                             exp.Drop, exp.Alter, exp.Command, exp.Into)):
            raise UnsafeQuery(f"{node.key.upper()} is not allowed inside a query")
    cte_names = {cte.alias_or_name.lower() for cte in tree.find_all(exp.CTE)}
    for table in tree.find_all(exp.Table):
        name, schema = table.name.lower(), (table.db or "").lower()
        if not schema and name in cte_names:
            continue
        if schema not in ALLOWED_SCHEMAS or name not in ALLOWED_TABLES:
            raise UnsafeQuery(f"table {table.sql()} is not on the allow-list")
    for func in tree.find_all(exp.Func):
        fname = (func.sql_name() if not isinstance(func, exp.Anonymous) else func.name).lower()
        if fname in BLOCKED_FUNCTIONS:
            raise UnsafeQuery(f"function {fname} is not allowed")
    inner = tree.sql(dialect="postgres")
    return f"SELECT * FROM ({inner}) AS agent_query LIMIT {MAX_ROWS}"
