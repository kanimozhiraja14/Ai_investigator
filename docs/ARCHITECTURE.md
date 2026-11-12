# AI Incident Investigator - System Architecture & Engineering Specification

## 1. Executive Summary & Architectural Overview

The **AI Incident Investigator** is an enterprise-grade autonomous Site Reliability Engineering (SRE) and Security Operations Center (SOC) investigation platform. It automates root-cause analysis (RCA), telemetry correlation, runbook retrieval, risk categorization (CWE / CIA triad), and mitigation synthesis for complex distributed cloud outages and security incidents.

The system is architected around six core tenets:
1. **Strict Read-Only Execution:** Every investigation tool operates under a deterministic security policy preventing state mutation or data modification.
2. **Evidence-Grounded Reasoning:** Every finding, claim, and hypothesis must link directly to an immutable Evidence Ledger entry with unique `EVID-xxx` identifiers.
3. **Temporal Correlation:** Cross-telemetry event sequencing links deployment markers, error spikes, and infrastructure saturation within calibrated time windows.
4. **Information Retrieval Grounding:** Algorithmic BM25 runbook retrieval grounds investigative queries in institutional knowledge rather than hallucinatory heuristics.
5. **Calibrated Confidence Modeling:** Probabilistic confidence scores derived from signal corroboration, symptom overlap, and contradiction absence.
6. **Defense-in-Depth Observability:** Structured logging, request tracking (`X-Request-ID`), and audit trails for all tool invocations.

---

## 2. System Component Topology

```
+-----------------------------------------------------------------------------------------+
|                                    User Interface                                       |
|                    Enterprise Incident Command Dashboard (SPA)                          |
|         (Overview, Incident Catalog, Investigation Workspace, Telemetry, Benchmarks)     |
+--------------------------------------------+--------------------------------------------+
                                             | HTTP / REST (JSON)
                                             v
+-----------------------------------------------------------------------------------------+
|                               FastAPI Application Gateway                              |
|                     (CORS, Request ID Middleware, Exception Handlers)                  |
+--------------------------------------------+--------------------------------------------+
                                             |
                   +-------------------------+-------------------------+
                   |                                                   |
                   v                                                   v
+--------------------------------------+             +------------------------------------+
|        API Routing Layer             |             |        Static Assets & UI          |
|  - /api/v1/incidents                 |             |  - HTML5 SRE Command Center        |
|  - /api/v1/investigate               |             |  - Modern Dark Enterprise CSS      |
|  - /api/v1/telemetry                 |             |  - Vanilla ES6+ State & Charts     |
|  - /api/v1/runbooks                  |             +------------------------------------+
|  - /api/v1/benchmark                 |
|  - /api/v1/health                    |
+------------------+-------------------+
                   |
                   v
+-----------------------------------------------------------------------------------------+
|                               Core Orchestration Layer                                  |
|                                                                                         |
|   +------------------------------------+    +---------------------------------------+   |
|   |   Autonomous Investigation Engine  |    |     Keyword Baseline Engine           |   |
|   |   - Multi-step hypothesis cycle    |    |     - Unweighted string matching      |   |
|   |   - Calibrated confidence scoring  |    |     - Naive symptom-runbook lookup    |   |
|   |   - Contradiction detection        |    |     - Control benchmark baseline      |   |
|   +-----------------+------------------+    +-------------------+-------------------+   |
|                     |                                           |                       |
+---------------------|-------------------------------------------|-----------------------+
                      |                                           |
                      v                                           v
+-----------------------------------------------------------------------------------------+
|                                  Tool Execution Mesh                                    |
|                                                                                         |
|   +---------------------------------------------------------------------------------+   |
|   |                       Read-Only Security Interceptor                            |   |
|   |   - Regex mutation rejection (DROP, UPDATE, DELETE, POST, PUT, EXEC, WRITE)     |   |
|   |   - Immutable telemetry read boundary                                           |   |
|   +----------------------------------------+----------------------------------------+   |
|                                            |                                            |
|        +-------------------+---------------+-------------------+                        |
|        v                   v                                   v                        |
|  +---------------+  +---------------------+             +--------------------+          |
|  | Runbook RAG   |  | Temporal Correlator |             | Risk Assessor      |          |
|  | - BM25 Engine |  | - Cross-telemetry   |             | - CWE Taxonomy     |          |
|  | - Markdown DB |  | - Rolling windows   |             | - CIA Triad Impact |          |
|  +---------------+  | - Sequence matching |             | - Severity Matrix  |          |
|                     +---------------------+             +--------------------+          |
+--------------------------------------------+--------------------------------------------+
                                             |
                                             v
+-----------------------------------------------------------------------------------------+
|                              Evidence Ledger & Storage                                  |
|  - Immutable EVID registry with cryptographic hashes                                    |
|  - Incident telemetry repository (10 realistic scenarios)                               |
|  - Runbook knowledge base (10 markdown runbooks)                                       |
+-----------------------------------------------------------------------------------------+
```

---

## 3. Telemetry Ingestion & Correlation Flow

When an incident is investigated, telemetry from three disparate data streams is analyzed:
1. **Structured Logs:** Timestamped application and system events (`timestamp`, `service`, `level`, `message`, `attributes`).
2. **Time-Series Metrics:** Numeric infrastructure and application indicators (`timestamp`, `service`, `metric_name`, `value`, `unit`, `threshold`).
3. **Deployment Events:** Change-management audit trail (`timestamp`, `service`, `version`, `author`, `commit`, `status`, `diff_summary`).

### Temporal Correlation Logic:
- A rolling temporal window ($\Delta t \in [-30\text{ min}, +15\text{ min}]$ around detection) filters related anomalies.
- Chronological alignment tracks the sequence:
  $$\text{Deployment Event } (t_0) \longrightarrow \text{Metric Degradation } (t_1) \longrightarrow \text{Error Log Cascade } (t_2)$$
- The correlation engine calculates an **Anomaly Magnitude Score** ($0.0 \to 1.0$) based on metric deviations beyond normal baseline thresholds ($z \ge 2.5$) and error rate concentration.

---

## 4. Algorithmic BM25 Runbook Retrieval (RAG)

Runbook retrieval uses the BM25 (Best Matching 25) probabilistic relevance model over structured Markdown documents.

### Scoring Formula:
$$\text{Score}(D, Q) = \sum_{i=1}^{N} \text{IDF}(q_i) \cdot \frac{f(q_i, D) \cdot (k_1 + 1)}{f(q_i, D) + k_1 \cdot \left(1 - b + b \cdot \frac{|D|}{\text{avgdl}}\right)}$$

Where:
- $k_1 = 1.5$ (term frequency saturation parameter)
- $b = 0.75$ (document length normalization parameter)
- $\text{avgdl}$ is the average token length across the runbook corpus.
- $\text{IDF}(q_i) = \ln\left(\frac{N - n(q_i) + 0.5}{n(q_i) + 0.5} + 1\right)$

Tokens are extracted from Runbook sections (Title, Symptoms, Root Causes, Remediation, Diagnostic Queries), weighted with higher relevance given to verified symptom terms.

---

## 5. Investigation State Machine & Reasoning Cycle

The autonomous investigation engine executes a five-stage deterministic state machine:

```
[1. INGESTION] ---> [2. HYPOTHESIS GENERATION] ---> [3. EVIDENCE VERIFICATION]
                            |                                 |
                            v                                 v
               [5. REMEDIATION SYNTHESIS] <--- [4. ROOT CAUSE DETERMINATION]
```

1. **Ingestion & Baseline Assessment:** Extract incident scope, service name, detected symptom, and initial alerts.
2. **Hypothesis Generation:** Retrieve candidate runbooks via BM25 and correlate temporal signals to form initial hypotheses.
3. **Evidence Verification:** Query targeted telemetry streams to validate hypothesis assertions. Every verified observation is committed to the **Evidence Ledger** with an `EVID-xxx` ID. Contradictory evidence (e.g. normal CPU during suspected runaway process) invalidates candidate hypotheses.
4. **Root Cause Determination:** Synthesize corroborating evidence. Calculate calibrated confidence:
   $$\text{Confidence} = \min\left(0.98, \frac{|\text{EVID}_{\text{corroborating}}|}{|\text{EVID}_{\text{total}}| + 1} \times (1.0 - \text{ContradictionPenalty})\right)$$
5. **Remediation & Risk Assessment:** Map to Common Weakness Enumeration (CWE), evaluate Confidentiality, Integrity, and Availability (CIA) impact, and synthesize immediate rollback and long-term hardening actions.

---

## 6. Read-Only Security Architecture

To guarantee safe deployment in mission-critical environments:
- **Sandbox Boundary:** Tool execution is mediated by `ReadOnlyGuard`.
- **Lexical Filter:** Inspects tool names, query parameters, and arguments. Rejects mutation keywords (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `PUT`, `POST`, `PATCH`, `EXEC`, `SYSTEM`, `WRITE`).
- **Data Immutability:** Injected telemetry datasets and runbook documents are frozen; query methods return deep copies of filtered records.

---

## 7. Comparative Benchmark Architecture

The platform evaluates its investigative accuracy against a **Keyword Baseline Investigator**:
- **Baseline Model:** Naive regex/keyword pattern matching across logs and runbooks without temporal alignment, multi-step tool loops, or evidence verification.
- **Evaluation Metrics:**
  - **Root-Cause Accuracy (%):** Percentage of incidents where the primary cause is correctly diagnosed.
  - **Time to Diagnosis (ms):** Wall-clock execution time to generate findings.
  - **Unsupported Claims Rate (%):** Frequency of claims made without an underlying `EVID` entry.
  - **Corroborating Evidence Ratio:** Average number of verified evidence artifacts per investigation.
