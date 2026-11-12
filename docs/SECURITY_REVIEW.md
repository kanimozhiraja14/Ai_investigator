# Security Architecture, Threat Model & Read-Only Governance

## 1. Threat Modeling Overview

As an automated SRE/SOC tool, the **AI Incident Investigator** ingests sensitive telemetry (logs, metrics, deployment commits) and executes diagnostic queries. If improperly secured, an incident investigation tool could become an attack vector for unauthorized data mutation, privilege escalation, or lateral movement.

This document formalizes the threat landscape, the read-only defense mechanism, and vulnerability mitigation strategies.

---

## 2. Threat Matrix (STRIDE Analysis)

| Threat Category | Potential Attack Vector | System Defense / Mitigation | Severity |
|:----------------|:------------------------|:----------------------------|:---------|
| **Spoofing** | Attacker impersonates service or injects fake logs | Telemetry repository is immutable during runtime; structured fields validated with Pydantic schemas. | Medium |
| **Tampering** | AI tool attempts to mutate state (e.g., dropping DB table, altering config) | **Strict Read-Only Enforcement**: Every tool execution is filtered by `ReadOnlyGuard`. Any command with mutation verbs (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `WRITE`) triggers an immediate `ReadOnlyViolationError`. | **Critical** |
| **Repudiation** | Actions taken during investigation cannot be audited | Every investigation produces an immutable **Investigation Trace** and **Evidence Ledger** with unique `EVID-xxx` identifiers, execution timestamps, and parameter hashes. | Low |
| **Information Disclosure** | Telemetry or error messages leak secrets/credentials | Automated sanitization regex strips tokens, passwords, and API keys (`Bearer`, `PRIVATE_KEY`, `secret=`). | High |
| **Denial of Service** | Deep or cyclic query requests exhaust memory or CPU | Query limits enforced: log retrieval capped at 100 entries; sliding correlation window limited to $t \pm 30\text{ min}$; BM25 token corpus bounded. | Medium |
| **Elevation of Privilege** | Attacker leverages tool-calling to execute arbitrary code | Zero arbitrary shell execution; only explicit, pre-registered, read-only Python callables are registered in `ToolRegistry`. | **Critical** |

---

## 3. Read-Only Sandbox & Enforcement Guard

The system implements a multi-layer read-only security boundary:

```
+-----------------------------------------------------------+
|                  AI Investigator Agent                    |
+-----------------------------+-----------------------------+
                              | Tool Call Request
                              v
+-----------------------------------------------------------+
|                   ReadOnlyGuard Layer                     |
|                                                           |
| 1. Whitelist Verification: Tool name in registered safe set|
| 2. Parameter Introspection: Deep inspection of all string  |
|    values against forbidden mutation patterns.            |
| 3. ReadOnlyViolation Exception Trigger on violation        |
+-----------------------------+-----------------------------+
                              | Approved Read-Only Call
                              v
+-----------------------------------------------------------+
|                Immutable Data Repository                  |
| (Deep copies returned; zero in-place mutating operations)  |
+-----------------------------------------------------------+
```

### Prohibited Lexical Patterns:
Any query parameter containing the following regular expression patterns is blocked immediately:
- Database Mutation: `\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|REPLACE)\b`
- System/Process Mutation: `\b(EXEC|SYSTEM|SHUTDOWN|KILL|REBOOT|WRITE|RM|DEL)\b`
- REST Mutation Verbs: `\b(POST|PUT|PATCH|DELETE)\b`

---

## 4. CWE Classification & Risk Assessment Engine

The investigator automatically maps diagnosed root causes to industry-standard **Common Weakness Enumerations (CWE)** and quantifies **CIA Triad** impact:

| Incident Root Cause | Primary CWE | Confidentiality | Integrity | Availability | Default Severity |
|:-------------------|:------------|:---------------:|:---------:|:------------:|:----------------:|
| Deployment Config Drift | CWE-15: External Control of System Config | None | High | High | CRITICAL |
| DB Connection Pool Exhaustion | CWE-400: Uncontrolled Resource Consumption | None | None | High | CRITICAL |
| Disk Storage Saturation | CWE-400: Uncontrolled Resource Consumption | None | Low | High | CRITICAL |
| Memory Leak (OOM) | CWE-401: Missing Release of Memory | None | None | High | HIGH |
| External API Latency / Hang | CWE-821: High Latency Timeout Failure | None | None | Medium | MEDIUM |
| SSL / TLS Certificate Expiration | CWE-298: Impopert Validation of Certificate Expiration | Low | Low | High | HIGH |
| Cache Stampede / Thundering Herd | CWE-400: Uncontrolled Resource Consumption | None | None | High | HIGH |
| WAF / Rate Limiter Misconfig | CWE-284: Improper Access Control | None | High | High | HIGH |
| Kafka Consumer Lag Backpressure | CWE-400: Uncontrolled Resource Consumption | None | Low | High | MEDIUM |
| JWT Public Key Rotation Failure | CWE-287: Improper Authentication | High | High | High | CRITICAL |

---

## 5. Secret Hygiene & Data Protection Policy

1. **No Hardcoded Secrets:** All secrets, keys, and tokens are read strictly from environment variables (`.env.example` provides non-sensitive defaults).
2. **Repository Sanitization:** `.gitignore` excludes `.env`, `*.pyc`, `__pycache__`, virtual environments, and scratch files.
3. **Redacted Telemetry Logs:** Simulated logs use synthetic names and sanitized credentials (e.g. `user_id="usr_synthetic_***"`).
