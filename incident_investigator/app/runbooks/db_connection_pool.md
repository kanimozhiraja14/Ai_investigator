# Runbook: Database Connection Pool Exhaustion & Query Latency

**Service:** order-service  
**Severity:** P1  
**Category:** DATABASE_SLOWDOWN  

## Symptoms
- Alert: `DatabasePoolExhaustion` firing (active connections > 95%).
- High P99 latency on `/orders` endpoints (> 5000ms).
- HTTP 504 Gateway Timeout errors returned to API gateway.

## Diagnostic Steps
1. Query `db_pool_active_connections` and `db_pool_waiting_threads` metrics for `order-service`.
2. Inspect logs for `TimeoutException: Connection acquisition timed out after 30000ms`.
3. Check database slow query logs for queries exceeding 1000ms execution time.
4. Check if unindexed filters or missing composite indexes were executed (e.g. `WHERE status = 'pending'`).
5. Verify whether replica read traffic was accidentally routed to the primary DB instance.

## Root Cause Patterns
- Unindexed full-table scan triggered by batch report or non-selective filter holding connection lock.
- Connection leak where acquired DB connections are not returned to pool in exception handler block.

## Mitigation
1. Terminate long-running blocking query: `SELECT pg_cancel_backend(pid) FROM pg_stat_activity WHERE query LIKE '%orders%'`.
2. Temporarily increase pool max size from 50 to 100 if DB host memory permits.
3. Deploy index patch or hotfix query to utilize primary key / indexed column.
