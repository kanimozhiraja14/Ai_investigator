# AI Incident Investigator - Master Implementation & Upgrade Plan

## Overview
This document outlines the detailed roadmap for transforming the **AI Incident Investigator** into an industry-grade, enterprise-ready portfolio project.

---

## Phase Matrix & Milestone Roadmap

| Phase | Milestone Name | Status | Key Deliverables |
|:------|:---------------|:-------|:-----------------|
| **Phase 1** | Architecture & Codebase Audit | In Progress | `docs/ARCHITECTURE.md`, `docs/IMPLEMENTATION_PLAN.md`, `docs/SECURITY_REVIEW.md` |
| **Phase 2** | Enterprise Dashboard Redesign | Planned | Dark enterprise UI (`index.html`, `style.css`, `app.js`), responsive SRE command center, real-time charts |
| **Phase 3** | AI Investigation Engine Elevation | Planned | Calibrated confidence, verified vs hypothesis classification, contradiction detection, structured report generator |
| **Phase 4** | Modular Backend Refactoring | Planned | Clean separation into `app/api`, `app/core`, `app/models`, `app/services`, `app/tools`, `app/retrieval`, `app/correlation` |
| **Phase 5** | Security Hardening & Read-Only Sandbox | Planned | `ReadOnlyGuard` interceptor, input validation, EVID tamper-evident hashing, sanitized error handling |
| **Phase 6** | Rigorous Testing & Benchmarking | Planned | Pytest/Unittest suite (`tests/`), 100% scenario coverage, reproducible benchmark comparison output |
| **Phase 7** | Comprehensive Documentation Suite | Planned | Enterprise `README.md`, `docs/API_REFERENCE.md`, `docs/TESTING.md`, `docs/BENCHMARKS.md`, `docs/DEPLOYMENT.md`, `Dockerfile` |
| **Phase 8** | Final QA & Portfolio Verification | Planned | Clean startup verification, zero deprecations, full automated test run, execution documentation in `TASK_DOCUMENTATION.md` |

---

## Phase 1: Architecture & Codebase Audit (In Progress)
- **Objective:** Establish formal engineering specifications, security policies, and technical plans.
- **Actions:**
  - Audit existing FastAPI endpoints, BM25 retrieval, temporal correlation, tool calling, and telemetry data.
  - Formulate component architecture in `docs/ARCHITECTURE.md`.
  - Author formal risk mitigation & security review in `docs/SECURITY_REVIEW.md`.

## Phase 2: Enterprise Dashboard Redesign
- **Objective:** Upgrade the static frontend into an SRE / SOC incident command center.
- **Design Philosophy:**
  - Professional deep navy / slate dark theme (`#0b0f19`, `#0f172a`, `#1e293b`).
  - Subtle cyan/blue accents (`#0ea5e9`, `#06b6d4`, `#3b82f6`) and calibrated severity colors (Critical: `#ef4444`, High: `#f97316`, Medium: `#eab308`, Low: `#10b981`).
  - Strict layout hierarchy: Header, KPI Summary, Tab Navigation, Interactive Panels, Modal Overlays.
- **Key Modules in UI:**
  1. *Executive KPI Bar:* Total incidents, critical ratio, mean investigation duration, read-only security indicator.
  2. *Incident Catalog:* Multi-filter table with live search, severity pills, service tag, and one-click investigation launch.
  3. *Investigation Workspace:* Step-by-step tool invocation feed, visual temporal timeline, evidence card gallery, root cause analysis banner, and actionable remediation checklists.
  4. *Telemetry Inspector:* Dual-pane log search and interactive metric charts.
  5. *Runbook Knowledge Base:* BM25 interactive query sandbox and markdown viewer.
  6. *Benchmark & Metrics:* Comparative charts (AI vs. Baseline) displaying root-cause accuracy, diagnosis latency, and unsupported claims rate.

## Phase 3: AI Investigation Engine Elevation
- **Objective:** Modernize reasoning algorithms to eliminate hallucinations, enforce evidence linking, and detect contradictions.
- **Enhancements:**
  - **Calibrated Confidence Scoring:** Multi-factor formula factoring in corroborating evidence count, telemetry alignment with runbook indicators, and penalty for ambiguous or conflicting metrics.
  - **Verified Observations vs. Hypotheses:** Explicit typing where observations are immutable facts extracted from telemetry, while hypotheses are probabilistic root cause interpretations.
  - **Contradiction Detection:** Active heuristic check for contradictory indicators (e.g. database alert but pool usage is 5%).
  - **Clean Output Separation:** Internal tool traces are stored for auditability, but final public report contains clean, structured markdown with explicit `[EVID-xxx]` citations.

## Phase 4: Modular Backend Refactoring
- **Objective:** Restructure codebase into a clean, maintainable, domain-driven architecture while preserving 100% backward compatibility.
- **Directory Layout:**
  - `incident_investigator/app/core/`: Application settings, logging configuration, custom exceptions.
  - `incident_investigator/app/models/`: Pydantic V2 schemas for incidents, telemetry, runbooks, evidence, reports, benchmarks.
  - `incident_investigator/app/retrieval/`: BM25 runbook retrieval engine.
  - `incident_investigator/app/correlation/`: Temporal telemetry correlation engine.
  - `incident_investigator/app/tools/`: Read-only tool definitions, registry, security guard, risk assessment.
  - `incident_investigator/app/services/`: Investigation service, baseline service, benchmark runner.
  - `incident_investigator/app/api/`: Modular FastAPI route handlers.
  - `incident_investigator/app/main.py`: Application factory, middleware, route mounting.

## Phase 5: Security Hardening & Read-Only Sandbox
- **Objective:** Ensure zero unauthorized data modification or arbitrary command execution.
- **Actions:**
  - Implement `ReadOnlyGuard` checking all tool parameters against SQL/CLI mutation verbs.
  - Validate all input parameters with Pydantic V2 strict validation.
  - Implement request ID propagation (`X-Request-ID`) across logs and API responses.
  - Verify that no credentials, tokens, or private endpoints are exposed.

## Phase 6: Rigorous Testing & Benchmarking
- **Objective:** Provide automated verification across all 10 incident scenarios.
- **Test Matrix:**
  - Unit tests for BM25 retrieval, temporal correlation, tool registry, and security guard.
  - Integration tests for all REST API endpoints.
  - Benchmark evaluation comparing AI Investigator against Keyword Baseline across 10 scenarios.
  - Produce real benchmark results saved to `benchmark_results.json` and documented in `docs/BENCHMARKS.md`.

## Phase 7: Documentation Suite & Containerization
- **Objective:** Create complete portfolio-grade documentation.
- **Files to Generate:**
  - `README.md`: Complete guide with architecture diagrams, quickstart, benchmark comparisons, API overview, and screenshots.
  - `docs/API_REFERENCE.md`: Complete OpenAPI / REST specification.
  - `docs/TESTING.md`: Test execution guide, test matrix, code coverage.
  - `docs/BENCHMARKS.md`: Mathematical methodology and benchmark results.
  - `docs/DEPLOYMENT.md`: Production deployment guide (Docker, Kubernetes, Bare Metal).
  - `Dockerfile` and `docker-compose.yml`.

## Phase 8: Final QA Verification
- **Objective:** Execute full suite and ensure zero regressions.
- **Checklist:**
  - Verify API endpoints return 200 OK.
  - Verify frontend renders cleanly with all interactive tabs functioning.
  - Verify all test suites pass with 0 failures.
  - Verify all 10 incident scenarios are correctly diagnosed by the AI investigator.
  - Record complete results in `TASK_DOCUMENTATION.md`.
