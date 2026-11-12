"""
Telemetry database containing logs, metrics, deployment events, and incident definitions
for 10 realistic production incident scenarios.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from .models import Incident, LogEntry, MetricPoint, DeploymentEvent

INCIDENTS: Dict[str, Incident] = {
    "INC-001": Incident(
        id="INC-001",
        title="Payment Service 500 Spike after Canary Rollout",
        service="payment-service",
        start_time="2026-11-12T14:02:00Z",
        end_time="2026-11-12T14:35:00Z",
        initial_alert="PaymentServiceHighErrorRate: 5xx error rate exceeded 12% in us-east-1",
        severity="P1",
        ground_truth_cause="Missing STRIPE_WEBHOOK_SECRET environment variable in v2.4.1 deployment manifest caused NullPointerException in WebhookHandler on /pay",
        ground_truth_category="BAD_DEPLOYMENT",
        threat_category="SUPPLY_CHAIN_CONFIG_DEFECT",
        cwe_id="CWE-312 / CWE-347",
        key_signals=["v2.4.1 deployment at 14:00:00Z", "NullPointerException on WebhookHandler", "Missing STRIPE_WEBHOOK_SECRET env variable", "HTTP 500 spike to 18%"]
    ),
    "INC-002": Incident(
        id="INC-002",
        title="Order Service Database Connection Pool Starvation & Timeout Cascade",
        service="order-service",
        start_time="2026-11-12T10:15:00Z",
        end_time="2026-11-12T10:55:00Z",
        initial_alert="DatabasePoolExhaustion: Active connections at 100%, P99 latency > 8500ms",
        severity="P1",
        ground_truth_cause="Unindexed query 'SELECT * FROM orders WHERE status = pending' executed by analytics worker acquired and held all 50 connection pool slots",
        ground_truth_category="DATABASE_SLOWDOWN",
        threat_category="RESOURCE_EXHAUSTION_DOS",
        cwe_id="CWE-400",
        key_signals=["db_pool_active_connections=50/50", "P99 latency jumped from 80ms to 8500ms", "TimeoutException: Connection acquisition timed out", "Unindexed table scan on orders"]
    ),
    "INC-003": Incident(
        id="INC-003",
        title="Auth Service Host Node Disk Exhaustion (/var/log at 100%)",
        service="auth-service",
        start_time="2026-11-12T08:00:00Z",
        end_time="2026-11-12T08:45:00Z",
        initial_alert="DiskSpaceRunningCriticallyLow: Node worker-node-04 /var/log at 100% capacity",
        severity="P2",
        ground_truth_cause="Logrotate failure due to invalid permissions (chmod 777 error) combined with debug logging left active filled 50GB partition to 100%",
        ground_truth_category="EXHAUSTED_DISK",
        threat_category="INSECURE_PERMISSIONS_TAMPERING",
        cwe_id="CWE-732",
        key_signals=["node_filesystem_free_bytes drops to 0", "Errno 28: No space left on device", "logrotate.service exit code 1", "Session token writes failing"]
    ),
    "INC-004": Incident(
        id="INC-004",
        title="Inventory Service Memory Leak and OOMKilled Container Cascade",
        service="inventory-service",
        start_time="2026-11-12T11:30:00Z",
        end_time="2026-11-12T12:20:00Z",
        initial_alert="PodCrashLoopingOOM: inventory-service pods restarted 8 times with exit code 137",
        severity="P1",
        ground_truth_cause="Commit 4a7ef1 introduced static unbounded LRU cache holding SKU reservation payloads without TTL or eviction limit",
        ground_truth_category="MEMORY_LEAK",
        threat_category="UNCONTROLLED_MEMORY_ALLOCATION",
        cwe_id="CWE-770",
        key_signals=["Sawtooth container_memory_working_set_bytes reaching 2Gi limit", "OOMKilled: true (exit code 137)", "OutOfMemoryError: Java heap space", "Cache size 1,450,000 items"]
    ),
    "INC-005": Incident(
        id="INC-005",
        title="Notification Worker Threadpool Starvation via Upstream SendGrid Socket Hang",
        service="notification-service",
        start_time="2026-11-12T13:10:00Z",
        end_time="2026-11-12T13:50:00Z",
        initial_alert="NotificationQueueLagHigh: 45,000 unsent emails, worker queue latency > 120s",
        severity="P2",
        ground_truth_cause="Upstream SendGrid API endpoint experiencing 30s TCP packet drop without client socket timeout or circuit breaker configured",
        ground_truth_category="UPSTREAM_DEPENDENCY",
        threat_category="EXTERNAL_DEPENDENCY_STARVATION",
        cwe_id="CWE-400",
        key_signals=["SocketTimeoutException: Read timed out to api.sendgrid.com", "Active worker threads 64/64 blocked in socketRead0", "Queue lag climbing to 45k items", "No circuit breaker fallback"]
    ),
    "INC-006": Incident(
        id="INC-006",
        title="Ingress Gateway Edge SSL Certificate Expiration & Handshake Failures",
        service="ingress-gateway",
        start_time="2026-11-12T00:05:00Z",
        end_time="2026-11-12T00:40:00Z",
        initial_alert="SSLCertificateExpired: edge.production.net returned x509 expiration error",
        severity="P1",
        ground_truth_cause="cert-manager ACME DNS-01 challenge failed because Cloudflare API token expired 3 days ago, preventing automated renewal before certificate expiry",
        ground_truth_category="CERTIFICATE_EXPIRATION",
        threat_category="CRYPTOGRAPHIC_EXPIRATION_OUTAGE",
        cwe_id="CWE-295",
        key_signals=["x509: certificate has expired or is not yet valid", "cert-manager error 401 Unauthorized for DNS token", "Valid until 2026-11-12T00:00:00Z", "Handshake failure spike 100%"]
    ),
    "INC-007": Incident(
        id="INC-007",
        title="Catalog Service Redis Cache Stampede on Black Friday Hot Key",
        service="catalog-service",
        start_time="2026-11-12T15:00:00Z",
        end_time="2026-11-12T15:35:00Z",
        initial_alert="CacheHitRatioCriticalDrop: Redis hit ratio dropped from 98% to 11%, DB CPU at 99%",
        severity="P1",
        ground_truth_cause="Key 'catalog:deals:flash-sale' expired at 15:00:00Z without mutex locking or TTL jitter, causing 12,000 concurrent requests to stampede Postgres DB",
        ground_truth_category="CACHE_STAMPEDE",
        threat_category="THUNDERING_HERD_ALGORITHMIC_DOS",
        cwe_id="CWE-400",
        key_signals=["redis_cache_hit_ratio drops from 0.98 to 0.11", "Postgres CPU at 99.4%", "12,000 simultaneous queries for single key catalog:deals:flash-sale", "No mutex/singleflight enabled"]
    ),
    "INC-008": Incident(
        id="INC-008",
        title="API Gateway False-Positive 429 Rate Limiting via Internal Node IP Flattening",
        service="api-gateway",
        start_time="2026-11-12T16:20:00Z",
        end_time="2026-11-12T17:00:00Z",
        initial_alert="RateLimitExceededSurge: HTTP 429 response rate spiked to 32% across all users",
        severity="P2",
        ground_truth_cause="Reverse proxy config update omitted 'real_ip_header X-Forwarded-For', causing rate limiter to bucket all users under internal node IP 10.244.0.1",
        ground_truth_category="RATE_LIMIT_MISCONFIG",
        threat_category="SECURITY_CONTROL_MISCONFIG_DOS",
        cwe_id="CWE-284",
        key_signals=["HTTP 429 spike to 32%", "Rate limiter bucket key evaluated as 10.244.0.1 for 100% of requests", "Config commit removed real_ip_header directive", "Individual user RPS was low"]
    ),
    "INC-009": Incident(
        id="INC-009",
        title="Billing Consumer Partition Rebalance Loop triggered by Poison Pill Message",
        service="billing-consumer",
        start_time="2026-11-12T09:10:00Z",
        end_time="2026-11-12T09:50:00Z",
        initial_alert="KafkaConsumerLagCritical: Consumer lag on billing-events topic exceeded 2.2M messages",
        severity="P1",
        ground_truth_cause="Poison pill message with negative currency decimal caused regex hang exceeding max.poll.interval.ms (300s), triggering continuous consumer group rebalances",
        ground_truth_category="CONSUMER_REBALANCE_LOOP",
        threat_category="INPUT_VALIDATION_POISON_PILL",
        cwe_id="CWE-20 / CWE-1333",
        key_signals=["Consumer lag 2,240,000 messages", "CommitFailedException: max.poll.interval.ms exceeded", "Consumer rebalances occurring every 310s", "Malformed message offset 8492048 in partition 2"]
    ),
    "INC-010": Incident(
        id="INC-010",
        title="User Profile Service Inter-Service RPC 401s after Vault Key Auto-Rotation",
        service="user-profile-service",
        start_time="2026-11-12T12:00:00Z",
        end_time="2026-11-12T12:40:00Z",
        initial_alert="ServiceAuth401Spike: 401 Unauthorized responses between web-frontend and user-profile",
        severity="P1",
        ground_truth_cause="Vault auto-rotated JWT private signing key, but user-profile-service had hardcoded 24h JWKS in-memory cache with no fallback to re-fetch on unknown kid",
        ground_truth_category="AUTH_SECRET_ROTATION",
        threat_category="AUTHENTICATION_KEY_ROTATION_FAILURE",
        cwe_id="CWE-287 / CWE-347",
        key_signals=["SignatureVerificationException: Key ID (kid) 'key-2026-11-b' not found in cache", "Vault audit log: secret rotated at 12:00:00Z", "HTTP 401 spike to 40%", "Cache TTL 86400s"]
    )
}

# In-memory store of logs, metrics, deployments
INCIDENT_LOGS: Dict[str, List[LogEntry]] = {}
INCIDENT_METRICS: Dict[str, List[MetricPoint]] = {}
INCIDENT_DEPLOYMENTS: Dict[str, List[DeploymentEvent]] = {}


def _generate_telemetry():
    """Populate synthetic high-fidelity logs, metrics, and deployments for each incident."""
    
    # ------------------ INC-001: Bad Deployment ------------------
    INCIDENT_DEPLOYMENTS["INC-001"] = [
        DeploymentEvent(
            id="DEP-101",
            timestamp="2026-11-12T14:00:00Z",
            service="payment-service",
            version="v2.4.1",
            previous_version="v2.4.0",
            author="dev-alice@company.internal",
            commit_hash="7f3c91a",
            commit_message="feat(checkout): add webhook validation logic and signature check",
            config_changes={
                "image": "registry.corp/payment-service:v2.4.1",
                "replicas": 4,
                "env_added": ["ENABLE_NEW_CHECKOUT=true"],
                "env_missing": ["STRIPE_WEBHOOK_SECRET"]
            },
            status="SUCCESS"
        )
    ]
    INCIDENT_LOGS["INC-001"] = [
        LogEntry(id="LOG-1001", timestamp="2026-11-12T13:55:10Z", service="payment-service", level="INFO", message="Payment service health check OK - version v2.4.0", trace_id="tr-001"),
        LogEntry(id="LOG-1002", timestamp="2026-11-12T14:00:05Z", service="payment-service", level="INFO", message="Deployment canary v2.4.1 container started on pod payment-service-78bf-x291", trace_id="tr-002"),
        LogEntry(id="LOG-1003", timestamp="2026-11-12T14:02:15Z", service="payment-service", level="ERROR", message="NullPointerException: Cannot invoke 'String.getBytes(java.nio.charset.Charset)' because 'secret' is null at com.company.payment.WebhookHandler.verifySignature(WebhookHandler.java:42)", trace_id="tr-101", attributes={"endpoint": "/pay/webhook", "status": 500}),
        LogEntry(id="LOG-1004", timestamp="2026-11-12T14:02:16Z", service="payment-service", level="ERROR", message="Configuration missing: Environment variable 'STRIPE_WEBHOOK_SECRET' is not defined in container environment", trace_id="tr-102", attributes={"env_var": "STRIPE_WEBHOOK_SECRET"}),
        LogEntry(id="LOG-1005", timestamp="2026-11-12T14:03:00Z", service="payment-service", level="FATAL", message="Handler execution failed on POST /pay/process: HTTP 500 Internal Server Error returned to client", trace_id="tr-103", attributes={"status": 500, "client_ip": "198.51.100.22"}),
        LogEntry(id="LOG-1006", timestamp="2026-11-12T14:05:30Z", service="payment-service", level="ERROR", message="Repeated crash in payment processing thread: NullPointerException in WebhookHandler.verifySignature", trace_id="tr-104", attributes={"error_count": 450}),
    ]
    INCIDENT_METRICS["INC-001"] = [
        MetricPoint(timestamp="2026-11-12T13:55:00Z", metric_name="http_5xx_rate", service="payment-service", value=0.001, unit="ratio"),
        MetricPoint(timestamp="2026-11-12T14:00:00Z", metric_name="http_5xx_rate", service="payment-service", value=0.002, unit="ratio"),
        MetricPoint(timestamp="2026-11-12T14:02:30Z", metric_name="http_5xx_rate", service="payment-service", value=0.185, unit="ratio"),
        MetricPoint(timestamp="2026-11-12T14:05:00Z", metric_name="http_5xx_rate", service="payment-service", value=0.240, unit="ratio"),
        MetricPoint(timestamp="2026-11-12T14:10:00Z", metric_name="http_5xx_rate", service="payment-service", value=0.252, unit="ratio"),
        MetricPoint(timestamp="2026-11-12T14:00:00Z", metric_name="http_requests_total", service="payment-service", value=1420.0, unit="rps"),
        MetricPoint(timestamp="2026-11-12T14:05:00Z", metric_name="http_requests_total", service="payment-service", value=1390.0, unit="rps"),
    ]

    # ------------------ INC-002: DB Slowdown ------------------
    INCIDENT_DEPLOYMENTS["INC-002"] = [
        DeploymentEvent(
            id="DEP-201",
            timestamp="2026-11-12T06:00:00Z",
            service="order-service",
            version="v1.18.2",
            previous_version="v1.18.1",
            author="dev-bob@company.internal",
            commit_hash="991a0c4",
            commit_message="chore: bump minor internal dependencies",
            config_changes={},
            status="SUCCESS"
        )
    ]
    INCIDENT_LOGS["INC-002"] = [
        LogEntry(id="LOG-2001", timestamp="2026-11-12T10:12:00Z", service="order-service", level="INFO", message="Order service healthy. Connection pool utilization 12%", trace_id="tr-201"),
        LogEntry(id="LOG-2002", timestamp="2026-11-12T10:14:50Z", service="order-service", level="WARN", message="Slow query detected (duration=14200ms): SELECT * FROM orders WHERE status = 'pending' AND created_at > NOW() - INTERVAL '30 days'", trace_id="tr-202", attributes={"query_time_ms": 14200}),
        LogEntry(id="LOG-2003", timestamp="2026-11-12T10:15:30Z", service="order-service", level="ERROR", message="HikariPool-1 - Connection is not available, request timed out after 30000ms. Active=50, Idle=0, Waiting=84", trace_id="tr-203", attributes={"pool": "HikariPool-1", "active": 50, "waiting": 84}),
        LogEntry(id="LOG-2004", timestamp="2026-11-12T10:16:00Z", service="order-service", level="ERROR", message="org.postgresql.util.PSQLException: FATAL: remaining connection slots are reserved for non-replication superuser connections", trace_id="tr-204"),
        LogEntry(id="LOG-2005", timestamp="2026-11-12T10:18:00Z", service="order-service", level="ERROR", message="HTTP 504 Gateway Timeout while processing POST /api/v1/orders/create: DB pool acquisition failed", trace_id="tr-205", attributes={"status": 504}),
    ]
    INCIDENT_METRICS["INC-002"] = [
        MetricPoint(timestamp="2026-11-12T10:10:00Z", metric_name="db_pool_active_connections", service="order-service", value=6.0, unit="connections"),
        MetricPoint(timestamp="2026-11-12T10:15:00Z", metric_name="db_pool_active_connections", service="order-service", value=50.0, unit="connections"),
        MetricPoint(timestamp="2026-11-12T10:16:00Z", metric_name="db_pool_waiting_threads", service="order-service", value=92.0, unit="threads"),
        MetricPoint(timestamp="2026-11-12T10:10:00Z", metric_name="http_latency_p99_ms", service="order-service", value=82.0, unit="ms"),
        MetricPoint(timestamp="2026-11-12T10:16:00Z", metric_name="http_latency_p99_ms", service="order-service", value=8950.0, unit="ms"),
    ]

    # ------------------ INC-003: Exhausted Disk ------------------
    INCIDENT_DEPLOYMENTS["INC-003"] = []  # No deployment
    INCIDENT_LOGS["INC-003"] = [
        LogEntry(id="LOG-3001", timestamp="2026-11-12T07:50:00Z", service="auth-service", level="INFO", message="Cron job /etc/cron.daily/logrotate started", trace_id="tr-301"),
        LogEntry(id="LOG-3002", timestamp="2026-11-12T07:50:02Z", service="auth-service", level="ERROR", message="logrotate: error running logrotate on /etc/logrotate.d/auth: line 4 bad file permissions (must be 0644, found 0777), skipping rotation", trace_id="tr-302"),
        LogEntry(id="LOG-3003", timestamp="2026-11-12T07:58:00Z", service="auth-service", level="WARN", message="High disk usage on mount /var/log: 98% capacity utilized (free: 350MB)", trace_id="tr-303"),
        LogEntry(id="LOG-3004", timestamp="2026-11-12T08:00:15Z", service="auth-service", level="FATAL", message="IOError: [Errno 28] No space left on device: '/var/log/auth/auth_audit.log'", trace_id="tr-304", attributes={"errno": 28, "mount": "/var/log"}),
        LogEntry(id="LOG-3005", timestamp="2026-11-12T08:01:00Z", service="auth-service", level="ERROR", message="Failed to persist session token for user: disk full write failure on /var/lib/auth/sessions", trace_id="tr-305"),
    ]
    INCIDENT_METRICS["INC-003"] = [
        MetricPoint(timestamp="2026-11-12T07:30:00Z", metric_name="node_filesystem_free_bytes", service="auth-service", value=8500000000.0, unit="bytes"),
        MetricPoint(timestamp="2026-11-12T07:50:00Z", metric_name="node_filesystem_free_bytes", service="auth-service", value=1200000000.0, unit="bytes"),
        MetricPoint(timestamp="2026-11-12T08:00:00Z", metric_name="node_filesystem_free_bytes", service="auth-service", value=0.0, unit="bytes"),
        MetricPoint(timestamp="2026-11-12T08:00:00Z", metric_name="disk_usage_percent", service="auth-service", value=100.0, unit="percent"),
    ]

    # ------------------ INC-004: Memory Leak ------------------
    INCIDENT_DEPLOYMENTS["INC-004"] = [
        DeploymentEvent(
            id="DEP-401",
            timestamp="2026-11-12T10:45:00Z",
            service="inventory-service",
            version="v3.1.0",
            previous_version="v3.0.9",
            author="dev-carol@company.internal",
            commit_hash="4a7ef1b",
            commit_message="perf: cache inventory reservation locks in memory for fast lookup",
            config_changes={"memory_limit": "2Gi"},
            status="SUCCESS"
        )
    ]
    INCIDENT_LOGS["INC-004"] = [
        LogEntry(id="LOG-4001", timestamp="2026-11-12T11:20:00Z", service="inventory-service", level="INFO", message="In-memory reservation cache initialized: 250,000 entries stored", trace_id="tr-401"),
        LogEntry(id="LOG-4002", timestamp="2026-11-12T11:28:00Z", service="inventory-service", level="WARN", message="JVM Garbage Collector overhead limit warning: GC paused for 2400ms", trace_id="tr-402"),
        LogEntry(id="LOG-4003", timestamp="2026-11-12T11:30:10Z", service="inventory-service", level="FATAL", message="java.lang.OutOfMemoryError: Java heap space at java.base/java.util.concurrent.ConcurrentHashMap.resize(ConcurrentHashMap.java:1240)", trace_id="tr-403"),
        LogEntry(id="LOG-4004", timestamp="2026-11-12T11:30:15Z", service="inventory-service", level="FATAL", message="Container inventory-service-pod-1 terminated by Linux OOM killer: exitCode=137, OOMKilled=true", trace_id="tr-404", attributes={"exit_code": 137, "reason": "OOMKilled"}),
        LogEntry(id="LOG-4005", timestamp="2026-11-12T11:32:00Z", service="inventory-service", level="ERROR", message="Kubelet: pod inventory-service entered CrashLoopBackOff state", trace_id="tr-405"),
    ]
    INCIDENT_METRICS["INC-004"] = [
        MetricPoint(timestamp="2026-11-12T11:00:00Z", metric_name="container_memory_working_set_bytes", service="inventory-service", value=512000000.0, unit="bytes"),
        MetricPoint(timestamp="2026-11-12T11:15:00Z", metric_name="container_memory_working_set_bytes", service="inventory-service", value=1200000000.0, unit="bytes"),
        MetricPoint(timestamp="2026-11-12T11:29:00Z", metric_name="container_memory_working_set_bytes", service="inventory-service", value=2140000000.0, unit="bytes"),
        MetricPoint(timestamp="2026-11-12T11:30:15Z", metric_name="pod_restart_count", service="inventory-service", value=8.0, unit="count"),
    ]

    # ------------------ INC-005: Upstream Dependency ------------------
    INCIDENT_DEPLOYMENTS["INC-005"] = []
    INCIDENT_LOGS["INC-005"] = [
        LogEntry(id="LOG-5001", timestamp="2026-11-12T13:05:00Z", service="notification-service", level="INFO", message="Notification worker pool active with 64 threads, throughput 150 emails/sec", trace_id="tr-501"),
        LogEntry(id="LOG-5002", timestamp="2026-11-12T13:09:40Z", service="notification-service", level="WARN", message="Outbound HTTP POST to https://api.sendgrid.com/v3/mail/send experiencing slow TCP ACK", trace_id="tr-502"),
        LogEntry(id="LOG-5003", timestamp="2026-11-12T13:10:15Z", service="notification-service", level="ERROR", message="java.net.SocketTimeoutException: Read timed out after 30000ms connecting to api.sendgrid.com:443", trace_id="tr-503", attributes={"remote_host": "api.sendgrid.com", "timeout_ms": 30000}),
        LogEntry(id="LOG-5004", timestamp="2026-11-12T13:12:00Z", service="notification-service", level="ERROR", message="ThreadPoolExecutor capacity exhausted: 64 of 64 threads in TIMED_WAITING state on socketRead0", trace_id="tr-504"),
        LogEntry(id="LOG-5005", timestamp="2026-11-12T13:15:00Z", service="notification-service", level="ERROR", message="Email dispatch queue backlog exceeded 45,000 pending jobs. Downstream SLAs breached", trace_id="tr-505"),
    ]
    INCIDENT_METRICS["INC-005"] = [
        MetricPoint(timestamp="2026-11-12T13:00:00Z", metric_name="external_http_request_duration_seconds", service="notification-service", value=0.22, unit="seconds"),
        MetricPoint(timestamp="2026-11-12T13:10:00Z", metric_name="external_http_request_duration_seconds", service="notification-service", value=30.0, unit="seconds"),
        MetricPoint(timestamp="2026-11-12T13:15:00Z", metric_name="notification_queue_lag", service="notification-service", value=45200.0, unit="messages"),
        MetricPoint(timestamp="2026-11-12T13:15:00Z", metric_name="active_worker_threads", service="notification-service", value=64.0, unit="threads"),
    ]

    # ------------------ INC-006: SSL Certificate Expiry ------------------
    INCIDENT_DEPLOYMENTS["INC-006"] = []
    INCIDENT_LOGS["INC-006"] = [
        LogEntry(id="LOG-6001", timestamp="2026-11-11T23:58:00Z", service="ingress-gateway", level="INFO", message="TLS handshake successful for client 203.0.113.19 - cert subject CN=edge.production.net", trace_id="tr-601"),
        LogEntry(id="LOG-6002", timestamp="2026-11-12T00:00:01Z", service="ingress-gateway", level="ERROR", message="cert-manager-controller: Failed to renew certificate 'edge-production-tls': Cloudflare API returned HTTP 401 Unauthorized (Invalid API token)", trace_id="tr-602", attributes={"cert": "edge-production-tls", "issuer": "letsencrypt-prod"}),
        LogEntry(id="LOG-6003", timestamp="2026-11-12T00:05:10Z", service="ingress-gateway", level="FATAL", message="TLS handshake error from client 198.51.100.82: remote error: tls: bad certificate (x509: certificate has expired or is not yet valid: current time 2026-11-12T00:05:10Z is after 2026-11-12T00:00:00Z)", trace_id="tr-603"),
        LogEntry(id="LOG-6004", timestamp="2026-11-12T00:06:00Z", service="ingress-gateway", level="ERROR", message="Handshake failure rate reached 100% on port 443; HTTPS traffic rejected", trace_id="tr-604"),
    ]
    INCIDENT_METRICS["INC-006"] = [
        MetricPoint(timestamp="2026-11-11T23:50:00Z", metric_name="ssl_cert_seconds_to_expiry", service="ingress-gateway", value=600.0, unit="seconds"),
        MetricPoint(timestamp="2026-11-12T00:00:00Z", metric_name="ssl_cert_seconds_to_expiry", service="ingress-gateway", value=0.0, unit="seconds"),
        MetricPoint(timestamp="2026-11-12T00:05:00Z", metric_name="ssl_handshake_failure_rate", service="ingress-gateway", value=1.0, unit="ratio"),
    ]

    # ------------------ INC-007: Redis Cache Stampede ------------------
    INCIDENT_DEPLOYMENTS["INC-007"] = []
    INCIDENT_LOGS["INC-007"] = [
        LogEntry(id="LOG-7001", timestamp="2026-11-12T14:55:00Z", service="catalog-service", level="INFO", message="Redis cache status healthy. Hit ratio 0.98, memory used 1.2GB", trace_id="tr-701"),
        LogEntry(id="LOG-7002", timestamp="2026-11-12T15:00:01Z", service="catalog-service", level="INFO", message="Redis key 'catalog:deals:flash-sale' expired after TTL=3600s reached", trace_id="tr-702"),
        LogEntry(id="LOG-7003", timestamp="2026-11-12T15:00:03Z", service="catalog-service", level="WARN", message="Cache miss surge: 12,400 concurrent requests querying backend Postgres for key 'catalog:deals:flash-sale'", trace_id="tr-703"),
        LogEntry(id="LOG-7004", timestamp="2026-11-12T15:00:15Z", service="catalog-service", level="ERROR", message="Database CPU pegged at 99.4%: Postgres process query backlog exceeded 400 active queries without mutex lock", trace_id="tr-704"),
        LogEntry(id="LOG-7005", timestamp="2026-11-12T15:02:00Z", service="catalog-service", level="ERROR", message="HTTP 504 Gateway Timeout returned on GET /api/v1/deals/flash-sale: Postgres connection query timeout", trace_id="tr-705"),
    ]
    INCIDENT_METRICS["INC-007"] = [
        MetricPoint(timestamp="2026-11-12T14:55:00Z", metric_name="redis_cache_hit_ratio", service="catalog-service", value=0.98, unit="ratio"),
        MetricPoint(timestamp="2026-11-12T15:00:30Z", metric_name="redis_cache_hit_ratio", service="catalog-service", value=0.11, unit="ratio"),
        MetricPoint(timestamp="2026-11-12T15:01:00Z", metric_name="postgres_cpu_utilization", service="catalog-service", value=99.4, unit="percent"),
        MetricPoint(timestamp="2026-11-12T15:02:00Z", metric_name="catalog_latency_p99_ms", service="catalog-service", value=6400.0, unit="ms"),
    ]

    # ------------------ INC-008: Rate Limiting Misconfiguration ------------------
    INCIDENT_DEPLOYMENTS["INC-008"] = [
        DeploymentEvent(
            id="DEP-801",
            timestamp="2026-11-12T16:15:00Z",
            service="api-gateway",
            version="v4.2.0",
            previous_version="v4.1.9",
            author="dev-dan@company.internal",
            commit_hash="3c11e9a",
            commit_message="refactor: streamline nginx ingress template and header forwarding",
            config_changes={"diff": "- real_ip_header X-Forwarded-For;"},
            status="SUCCESS"
        )
    ]
    INCIDENT_LOGS["INC-008"] = [
        LogEntry(id="LOG-8001", timestamp="2026-11-12T16:18:00Z", service="api-gateway", level="INFO", message="API Gateway reloaded nginx configuration successfully", trace_id="tr-801"),
        LogEntry(id="LOG-8002", timestamp="2026-11-12T16:20:10Z", service="api-gateway", level="WARN", message="Rate limiter key evaluation: client_ip resolved to internal node IP 10.244.0.1 (missing real_ip_header directive)", trace_id="tr-802"),
        LogEntry(id="LOG-8003", timestamp="2026-11-12T16:20:45Z", service="api-gateway", level="ERROR", message="Rate limit exceeded for key 'ip:10.244.0.1': 5,200 req/sec exceeds limit 100 req/sec; returning HTTP 429", trace_id="tr-803", attributes={"status": 429, "bucket_key": "10.244.0.1"}),
        LogEntry(id="LOG-8004", timestamp="2026-11-12T16:22:00Z", service="api-gateway", level="ERROR", message="Widespread 429 rejections: 32% of all legitimate customer ingress traffic throttled falsely under node IP", trace_id="tr-804"),
    ]
    INCIDENT_METRICS["INC-008"] = [
        MetricPoint(timestamp="2026-11-12T16:10:00Z", metric_name="http_429_rate", service="api-gateway", value=0.0001, unit="ratio"),
        MetricPoint(timestamp="2026-11-12T16:20:30Z", metric_name="http_429_rate", service="api-gateway", value=0.324, unit="ratio"),
        MetricPoint(timestamp="2026-11-12T16:22:00Z", metric_name="rate_limit_bucket_hits_per_sec", service="api-gateway", value=5200.0, unit="hits/sec"),
    ]

    # ------------------ INC-009: Kafka Consumer Lag ------------------
    INCIDENT_DEPLOYMENTS["INC-009"] = []
    INCIDENT_LOGS["INC-009"] = [
        LogEntry(id="LOG-9001", timestamp="2026-11-12T09:05:00Z", service="billing-consumer", level="INFO", message="Kafka consumer group 'billing-processors' healthy, 12 partitions assigned", trace_id="tr-901"),
        LogEntry(id="LOG-9002", timestamp="2026-11-12T09:08:12Z", service="billing-consumer", level="WARN", message="Processing message offset 8492048 on partition 2: malformed payload with negative currency exponent triggering catastrophic backtracking in regex validator", trace_id="tr-902"),
        LogEntry(id="LOG-9003", timestamp="2026-11-12T09:13:15Z", service="billing-consumer", level="ERROR", message="org.apache.kafka.clients.consumer.CommitFailedException: Commit cannot be completed since max.poll.interval.ms (300000ms) has elapsed between calls to poll(). Member evicted", trace_id="tr-903"),
        LogEntry(id="LOG-9004", timestamp="2026-11-12T09:14:00Z", service="billing-consumer", level="WARN", message="Consumer group 'billing-processors' rebalance triggered (reason: member failed heartbeat/poll timeout)", trace_id="tr-904"),
        LogEntry(id="LOG-9005", timestamp="2026-11-12T09:19:15Z", service="billing-consumer", level="ERROR", message="Partition 2 reassigned to consumer-02; re-processing offset 8492048 again hangs for 300s, triggering secondary rebalance loop", trace_id="tr-905"),
    ]
    INCIDENT_METRICS["INC-009"] = [
        MetricPoint(timestamp="2026-11-12T09:00:00Z", metric_name="kafka_consumer_lag", service="billing-consumer", value=120.0, unit="messages"),
        MetricPoint(timestamp="2026-11-12T09:15:00Z", metric_name="kafka_consumer_lag", service="billing-consumer", value=850000.0, unit="messages"),
        MetricPoint(timestamp="2026-11-12T09:30:00Z", metric_name="kafka_consumer_lag", service="billing-consumer", value=2240000.0, unit="messages"),
        MetricPoint(timestamp="2026-11-12T09:20:00Z", metric_name="consumer_group_rebalances_total", service="billing-consumer", value=6.0, unit="count"),
    ]

    # ------------------ INC-010: JWT Secret Rotation Failure ------------------
    INCIDENT_DEPLOYMENTS["INC-010"] = []
    INCIDENT_LOGS["INC-010"] = [
        LogEntry(id="LOG-10001", timestamp="2026-11-12T11:58:00Z", service="user-profile-service", level="INFO", message="User profile service operational, RPC authentication success 99.98%", trace_id="tr-10001"),
        LogEntry(id="LOG-10002", timestamp="2026-11-12T12:00:00Z", service="user-profile-service", level="INFO", message="Vault audit: automated key rotation executed for /secret/jwt-keys; new active kid='key-2026-11-b'", trace_id="tr-10002", attributes={"rotated_kid": "key-2026-11-b"}),
        LogEntry(id="LOG-10003", timestamp="2026-11-12T12:01:10Z", service="user-profile-service", level="ERROR", message="io.jsonwebtoken.security.SignatureException: Key ID (kid) 'key-2026-11-b' not found in local JWKS cache. Token verification failed", trace_id="tr-10003", attributes={"kid": "key-2026-11-b"}),
        LogEntry(id="LOG-10004", timestamp="2026-11-12T12:02:00Z", service="user-profile-service", level="ERROR", message="HTTP 401 Unauthorized returned to upstream caller 'web-frontend' on GET /api/v1/users/me: cached JWKS has TTL=86400s and does not auto-refresh on unknown kid", trace_id="tr-10004", attributes={"status": 401}),
        LogEntry(id="LOG-10005", timestamp="2026-11-12T12:05:00Z", service="user-profile-service", level="FATAL", message="Authentication failure surge: 40% of all user profile RPC requests failing with 401 Unauthorized", trace_id="tr-10005"),
    ]
    INCIDENT_METRICS["INC-010"] = [
        MetricPoint(timestamp="2026-11-12T11:50:00Z", metric_name="auth_401_error_rate", service="user-profile-service", value=0.0002, unit="ratio"),
        MetricPoint(timestamp="2026-11-12T12:02:00Z", metric_name="auth_401_error_rate", service="user-profile-service", value=0.405, unit="ratio"),
        MetricPoint(timestamp="2026-11-12T12:05:00Z", metric_name="jwks_cache_miss_rate", service="user-profile-service", value=0.412, unit="ratio"),
    ]

_generate_telemetry()


def get_all_incidents() -> List[Incident]:
    return list(INCIDENTS.values())


def get_incident(incident_id: str) -> Optional[Incident]:
    return INCIDENTS.get(incident_id)


def query_logs(
    incident_id: str,
    service: Optional[str] = None,
    level: Optional[str] = None,
    search: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    limit: int = 50
) -> List[LogEntry]:
    logs = INCIDENT_LOGS.get(incident_id, [])
    filtered = []
    
    for log in logs:
        if service and log.service.lower() != service.lower():
            continue
        if level and log.level.upper() != level.upper():
            continue
        if start_time and log.timestamp < start_time:
            continue
        if end_time and log.timestamp > end_time:
            continue
        if search:
            q = search.lower()
            text = f"{log.message} {str(log.attributes)}".lower()
            if q not in text:
                continue
        filtered.append(log)
        if len(filtered) >= limit:
            break
            
    return filtered


def query_metrics(
    incident_id: str,
    service: Optional[str] = None,
    metric_name: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None
) -> List[MetricPoint]:
    points = INCIDENT_METRICS.get(incident_id, [])
    filtered = []
    for pt in points:
        if service and pt.service.lower() != service.lower():
            continue
        if metric_name and pt.metric_name.lower() != metric_name.lower():
            continue
        if start_time and pt.timestamp < start_time:
            continue
        if end_time and pt.timestamp > end_time:
            continue
        filtered.append(pt)
    return filtered


def query_deployments(
    incident_id: str,
    service: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None
) -> List[DeploymentEvent]:
    deps = INCIDENT_DEPLOYMENTS.get(incident_id, [])
    filtered = []
    for d in deps:
        if service and d.service.lower() != service.lower():
            continue
        if start_time and d.timestamp < start_time:
            continue
        if end_time and d.timestamp > end_time:
            continue
        filtered.append(d)
    return filtered
