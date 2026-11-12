# Runbook: Disk Space Exhaustion on Host or Container Partition

**Service:** auth-service  
**Severity:** P2  
**Category:** EXHAUSTED_DISK  

## Symptoms
- Alert: `DiskSpaceRunningCriticallyLow` (mount `/var/log` or root partition > 98%).
- `auth-service` failing liveness and readiness probes due to inability to write session files.
- `No space left on device (Errno 28)` appearing in system and container logs.

## Diagnostic Steps
1. Query `node_filesystem_free_bytes` and `node_filesystem_usage_percent` metrics for the host.
2. Query logs for `write failed: No space left on device` or `IOError: ENOSPC`.
3. Check `logrotate` service status and crontab permissions on host nodes.
4. Verify if DEBUG level logging was accidentally left enabled in production config.

## Root Cause Patterns
- Log rotation daemon failed due to permission denial on config file (`/etc/logrotate.d/*`).
- High-volume debug logs generated during load testing filled local disk space.

## Mitigation
1. Clear old uncompressed rotated log archives: `find /var/log/auth -type f -name "*.log.1*" -delete`.
2. Fix logrotate permissions: `chmod 644 /etc/logrotate.d/auth`.
3. Re-point application logging to remote syslog/vector collector instead of local disk.
