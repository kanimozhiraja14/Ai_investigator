# Runbook: Container Out-Of-Memory (OOMKilled) & Memory Leak

**Service:** inventory-service  
**Severity:** P1  
**Category:** MEMORY_LEAK  

## Symptoms
- Alert: `PodCrashLoopingOOM` firing on `inventory-service` pods.
- Pods terminating with exit code `137` (SIGKILL by Linux OOM killer).
- Linear saw-tooth growth pattern in memory consumption until hard limit threshold.

## Diagnostic Steps
1. Query `container_memory_working_set_bytes` metric over last 2 hours.
2. Search container event logs for `OOMKilled: true` and `lastState: Terminated (exit code 137)`.
3. Check application logs for heap metrics or `java.lang.OutOfMemoryError: Java heap space`.
4. Inspect recent code changes touching cache layers or static collection buffers.

## Root Cause Patterns
- Unbounded in-memory cache without eviction policy or time-to-live (TTL).
- Unclosed streaming responses or leaky event listeners retaining references to payload objects.

## Mitigation
1. Temporarily increase memory request/limit in Kubernetes deployment spec by 2x.
2. Revert recent commit introducing unbounded cache collection.
3. Add memory limit clamp with TTL eviction on cache entries.
