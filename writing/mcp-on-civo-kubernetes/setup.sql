-- Run once as an admin after Airbyte has synced into the "analytics" schema.
-- Layer 1: the database itself refuses anything but reads on approved tables.
CREATE ROLE agent_ro LOGIN PASSWORD 'change-me';
ALTER ROLE agent_ro SET default_transaction_read_only = on;
ALTER ROLE agent_ro SET statement_timeout = '5s';
ALTER ROLE agent_ro SET search_path = analytics;

REVOKE ALL ON SCHEMA public FROM agent_ro;
GRANT USAGE ON SCHEMA analytics TO agent_ro;
GRANT SELECT ON analytics.users, analytics.products, analytics.purchases TO agent_ro;
-- Anything else in analytics (payroll, api_keys, ...) stays invisible to the agent.
