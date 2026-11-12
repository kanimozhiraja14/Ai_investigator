# Runbook: Redis Cache Stampede & Cache Eviction Avalanche

**Service:** catalog-service  
**Severity:** P1  
**Category:** CACHE_STAMPEDE  

## Symptoms
- Alert: `CacheHitRatioCriticalDrop` (hit ratio dropping from 98% to < 20%).
- Backend Postgres CPU utilization spiking to 100%.
- Latency surge on catalog listing endpoints.

## Diagnostic Steps
1. Query `redis_cache_hit_ratio` and `redis_connected_clients` metrics.
2. Query database metrics `pg_stat_activity_count` and CPU usage.
3. Search logs for simultaneous key expiration events and subsequent DB query storm for single hot key.
4. Verify if cache keys lacked probabilistic jitter in TTL.

## Root Cause Patterns
- Single high-cardinality hot key expired synchronously without mutex locking or background refresh.
- Sudden Redis memory eviction under load purged critical cache keys.

## Mitigation
1. Pre-warm hot cache key manually with default payload.
2. Apply random jitter to cache expiration: `TTL = base_ttl + rand(0, 300)`.
3. Enable Singleflight / Mutex locking to ensure only 1 thread fetches from DB on cache miss.
