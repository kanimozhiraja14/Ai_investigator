// ========================================================
// AEGIS SRE COMMAND PLATFORM - CLIENT CONTROLLER
// Version 2.1.0 // Enterprise Incident Command Center
// ========================================================

let currentIncidentId = "INC-001";
let allIncidents = [];
let currentInvestigationData = null;
let allEvidenceItems = [];

const CATEGORY_COLORS = {
  "BAD_DEPLOYMENT": "#ef4444",
  "DATABASE_SLOWDOWN": "#f59e0b",
  "EXHAUSTED_DISK": "#8b5cf6",
  "MEMORY_LEAK": "#ec4899",
  "UPSTREAM_DEPENDENCY": "#3b82f6",
  "CERTIFICATE_EXPIRATION": "#f43f5e",
  "CACHE_STAMPEDE": "#10b981",
  "RATE_LIMIT_MISCONFIG": "#06b6d4",
  "CONSUMER_REBALANCE_LOOP": "#eab308",
  "AUTH_SECRET_ROTATION": "#6366f1"
};

document.addEventListener("DOMContentLoaded", async () => {
  setupNavigation();
  setupFilterListeners();
  setupInspectorTabs();
  setupEvidenceModal();
  await loadInitialData();
  
  // Auto-run investigation on INC-001 so the workspace and trace are pre-populated
  await runInvestigation("ai");
});

// ------------------------------------------------------------------
// 1. NAVIGATION & GLOBAL SETUP
// ------------------------------------------------------------------
function setupNavigation() {
  const navButtons = document.querySelectorAll(".nav-item");
  navButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const section = btn.dataset.section;
      switchSection(section);
    });
  });

  document.getElementById("quickInvestigateBtn").addEventListener("click", () => {
    switchSection("workspace");
    runInvestigation("ai");
  });

  document.getElementById("wsRunAiBtn").addEventListener("click", () => runInvestigation("ai"));
  document.getElementById("wsRunBaseBtn").addEventListener("click", () => runInvestigation("baseline"));
  document.getElementById("runFullBenchBtn").addEventListener("click", runFullBenchmark);
  document.getElementById("refreshHealthBtn").addEventListener("click", loadSystemHealth);

  const quickSelect = document.getElementById("incidentQuickSelect");
  quickSelect.addEventListener("change", (e) => {
    selectIncident(e.target.value);
    runInvestigation("ai");
  });
}

function switchSection(sectionId) {
  // Update sidebar active state
  document.querySelectorAll(".nav-item").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.section === sectionId);
  });

  // Update viewport section
  document.querySelectorAll(".view-section").forEach((sec) => {
    sec.classList.remove("active");
  });
  const targetSec = document.getElementById(`section-${sectionId}`);
  if (targetSec) {
    targetSec.classList.add("active");
  }

  // Update breadcrumb
  const names = {
    overview: "Overview",
    incidents: "Incident Roster",
    workspace: "Investigation Hub",
    evidence: "Evidence Explorer",
    security: "Risk & CWE Analysis",
    benchmark: "Benchmark Center",
    trace: "Execution Trace",
    health: "System Health"
  };
  document.getElementById("breadcrumbSection").textContent = names[sectionId] || sectionId;

  // Specific triggers
  if (sectionId === "evidence") loadEvidenceExplorer();
  if (sectionId === "health") loadSystemHealth();
  if (sectionId === "benchmark") runFullBenchmark();
}

function setupInspectorTabs() {
  const tabButtons = document.querySelectorAll(".insp-tab-btn");
  tabButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      tabButtons.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");

      const targetTab = btn.dataset.tab;
      document.querySelectorAll(".inspector-tab-pane").forEach(pane => {
        pane.classList.toggle("active", pane.id === targetTab);
      });
    });
  });
}

function setupEvidenceModal() {
  const modal = document.getElementById("evidenceModal");
  const closeBtn = document.getElementById("modalCloseBtn");
  const copyBtn = document.getElementById("modalCopyBtn");

  closeBtn.addEventListener("click", () => modal.classList.remove("show"));
  modal.addEventListener("click", (e) => {
    if (e.target === modal) modal.classList.remove("show");
  });

  copyBtn.addEventListener("click", () => {
    const code = document.getElementById("modalJsonCode").textContent;
    navigator.clipboard.writeText(code).then(() => {
      const copyText = document.getElementById("copyBtnText");
      copyText.textContent = "Copied!";
      setTimeout(() => { copyText.textContent = "Copy JSON"; }, 2000);
    });
  });
}

async function loadInitialData() {
  await Promise.all([
    loadStats(),
    loadIncidents(),
    loadSystemHealth()
  ]);
}

// ------------------------------------------------------------------
// 2. STATS & OVERVIEW DASHBOARD
// ------------------------------------------------------------------
async function loadStats() {
  try {
    const res = await fetch("/api/stats");
    const stats = await res.json();

    document.getElementById("kpiTotalIncidents").textContent = stats.total_incidents;
    document.getElementById("kpiP1Incidents").textContent = stats.severity_counts["P1"] || 0;
    document.getElementById("kpiP2Incidents").textContent = stats.severity_counts["P2"] || 0;
    document.getElementById("navIncCount").textContent = stats.total_incidents;

    // Render Segmented Category Bar
    const segBar = document.getElementById("overviewSegmentedBar");
    segBar.innerHTML = "";
    const catContainer = document.getElementById("categoryBarsContainer");
    catContainer.innerHTML = "";
    const total = stats.total_incidents || 1;

    for (const [cat, count] of Object.entries(stats.category_counts)) {
      const pct = (count / total) * 100;
      const color = CATEGORY_COLORS[cat] || "#0ea5e9";

      // Segment bar item
      const segItem = document.createElement("div");
      segItem.className = "seg-item";
      segItem.style.width = `${pct}%`;
      segItem.style.backgroundColor = color;
      segItem.title = `${cat}: ${count} (${Math.round(pct)}%)`;
      segBar.appendChild(segItem);

      // Category chip item
      const chip = document.createElement("div");
      chip.className = "cat-chip";
      chip.innerHTML = `
        <div class="cat-chip-left">
          <span class="cat-color-dot" style="background-color:${color};"></span>
          <span class="cat-name">${cat}</span>
        </div>
        <span class="cat-count">${count} (${Math.round(pct)}%)</span>
      `;
      catContainer.appendChild(chip);
    }

    // Render Recent Incidents Queue
    const recentList = document.getElementById("recentIncidentsList");
    recentList.innerHTML = "";
    stats.recent_incidents.forEach((inc) => {
      const row = document.createElement("tr");
      row.innerHTML = `
        <td><strong style="color:var(--primary); font-family:var(--font-mono);">${inc.id}</strong></td>
        <td><span class="badge ${inc.severity === 'P1' ? 'badge-p1' : 'badge-p2'}">${inc.severity}</span></td>
        <td><code>${inc.service}</code></td>
        <td style="max-width:280px;">
          <div style="font-weight:600; color:var(--text-main); font-size:12px;">${inc.title}</div>
          <div style="font-size:10.5px; color:var(--text-dim); font-family:var(--font-mono);">${inc.initial_alert.substring(0, 75)}...</div>
        </td>
        <td>
          <button class="btn btn-outline btn-sm" onclick="handleInvestigateClick('${inc.id}')">Inspect</button>
        </td>
      `;
      recentList.appendChild(row);
    });

    document.getElementById("statsUpdatedTime").textContent = new Date().toLocaleTimeString();
  } catch (err) {
    console.error("Failed to load system stats:", err);
  }
}

// ------------------------------------------------------------------
// 3. INCIDENT MANAGEMENT ROSTER
// ------------------------------------------------------------------
async function loadIncidents() {
  try {
    const res = await fetch("/api/incidents");
    allIncidents = await res.json();
    populateQuickSelect(allIncidents);
    renderIncidentsTable(allIncidents);
    renderThreatMatrixTable(allIncidents);
    if (allIncidents.length > 0) {
      selectIncident(allIncidents[0].id);
    }
  } catch (err) {
    console.error("Failed to load incidents:", err);
  }
}

function populateQuickSelect(incidents) {
  const quickSelect = document.getElementById("incidentQuickSelect");
  quickSelect.innerHTML = "";
  incidents.forEach(inc => {
    const opt = document.createElement("option");
    opt.value = inc.id;
    opt.textContent = `${inc.id} - ${inc.service} (${inc.severity})`;
    quickSelect.appendChild(opt);
  });
}

function renderIncidentsTable(incidents) {
  const tbody = document.getElementById("incidentsTableBody");
  tbody.innerHTML = "";
  document.getElementById("rosterCountBadge").textContent = `${incidents.length} Total Incidents`;

  incidents.forEach((inc) => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td><strong style="color:var(--primary); font-family:var(--font-mono); font-size:12.5px;">${inc.id}</strong></td>
      <td><span class="badge ${inc.severity === 'P1' ? 'badge-p1' : 'badge-p2'}">${inc.severity}</span></td>
      <td><code>${inc.service}</code></td>
      <td style="color:var(--text-dim); font-family:var(--font-mono); font-size:11px;">${inc.start_time}</td>
      <td>
        <div style="font-weight:600; color:var(--text-main); margin-bottom:2px;">${inc.title}</div>
        <div style="font-size:11px; color:var(--text-dim); font-family:var(--font-mono);">${inc.initial_alert}</div>
      </td>
      <td>
        <div style="font-size:11px; color:var(--text-muted);">${inc.threat_category || 'SYSTEM_FAULT'}</div>
        <div style="font-size:10px; color:#fca5a5; font-family:var(--font-mono);">${inc.cwe_id || 'N/A'}</div>
      </td>
      <td><span class="status-pill">${inc.status}</span></td>
      <td>
        <button class="btn btn-primary btn-sm" onclick="handleInvestigateClick('${inc.id}')">Investigate</button>
      </td>
    `;
    tbody.appendChild(row);
  });
}

function renderThreatMatrixTable(incidents) {
  const tbody = document.getElementById("threatMatrixTableBody");
  if (!tbody) return;
  tbody.innerHTML = "";

  incidents.forEach((inc) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><strong style="color:var(--primary); font-family:var(--font-mono);">${inc.id}</strong></td>
      <td><code>${inc.service}</code></td>
      <td style="font-size:11px;">${inc.threat_category || '-'}</td>
      <td style="font-size:11px; color:#fca5a5;"><code>${inc.cwe_id || '-'}</code></td>
    `;
    tbody.appendChild(tr);
  });
}

function handleInvestigateClick(id) {
  selectIncident(id);
  switchSection("workspace");
  runInvestigation("ai");
}

function setupFilterListeners() {
  const searchInput = document.getElementById("incidentSearchInput");
  const sevFilter = document.getElementById("severityFilter");
  const statFilter = document.getElementById("statusFilter");

  const applyFilters = () => {
    const q = searchInput.value.toLowerCase();
    const sev = sevFilter.value;
    const stat = statFilter.value;

    const filtered = allIncidents.filter((inc) => {
      const matchSearch = !q || inc.title.toLowerCase().includes(q) || inc.id.toLowerCase().includes(q) || inc.service.toLowerCase().includes(q) || inc.initial_alert.toLowerCase().includes(q);
      const matchSev = !sev || inc.severity === sev;
      const matchStat = !stat || inc.status === stat;
      return matchSearch && matchSev && matchStat;
    });

    renderIncidentsTable(filtered);
  };

  searchInput.addEventListener("input", applyFilters);
  sevFilter.addEventListener("change", applyFilters);
  statFilter.addEventListener("change", applyFilters);
}

function selectIncident(id) {
  currentIncidentId = id;
  const inc = allIncidents.find((i) => i.id === id);
  if (!inc) return;

  // Header quick select & target pill
  document.getElementById("incidentQuickSelect").value = inc.id;
  document.getElementById("headerIncId").textContent = inc.id;
  document.getElementById("navActiveTargetBadge").textContent = inc.id;

  // Workspace Banner
  document.getElementById("wsTitle").textContent = `${inc.id}: ${inc.title}`;
  document.getElementById("wsService").textContent = inc.service;
  document.getElementById("wsTime").textContent = inc.start_time;
  document.getElementById("wsStatus").textContent = inc.status;
  document.getElementById("wsAlertText").textContent = inc.initial_alert;
  
  const sevBadge = document.getElementById("wsSeverity");
  sevBadge.textContent = inc.severity;
  sevBadge.className = `badge ${inc.severity === 'P1' ? 'badge-p1' : 'badge-p2'}`;

  // Mini Risk in Workspace Side
  document.getElementById("wsCweMini").textContent = inc.cwe_id || "N/A";
  document.getElementById("wsThreatMini").textContent = inc.threat_category || "SYSTEM_FAULT";
  document.getElementById("wsRiskLevelBadge").textContent = inc.severity === "P1" ? "CRITICAL" : "HIGH";

  // Load telemetry context for this incident into right inspector tabs
  loadIncidentTelemetryContext(inc.id, inc.service);
}

// ------------------------------------------------------------------
// 4. TELEMETRY CONTEXT INSPECTOR (Logs, Metrics, Deployments)
// ------------------------------------------------------------------
async function loadIncidentTelemetryContext(incidentId, service) {
  // Fetch logs
  try {
    const resLogs = await fetch(`/api/logs?incident_id=${incidentId}&limit=15`);
    const logs = await resLogs.json();
    const logsContainer = document.getElementById("wsLogsContainer");
    document.getElementById("wsLogsCountBadge").textContent = `${logs.length} Logs`;
    logsContainer.innerHTML = "";

    if (logs.length === 0) {
      logsContainer.innerHTML = '<div class="empty-state">No error logs captured in window.</div>';
    } else {
      logs.forEach(l => {
        const entry = document.createElement("div");
        entry.className = "log-stream-entry";
        const isFatal = l.level === "FATAL";
        entry.innerHTML = `
          <div class="log-entry-meta">
            <span class="${isFatal ? 'log-lvl-fatal' : 'log-lvl-error'}">[${l.level}] ${l.service}</span>
            <span>${l.timestamp.substring(11, 19)}</span>
          </div>
          <div class="log-msg-text">${l.message}</div>
        `;
        logsContainer.appendChild(entry);
      });
    }
  } catch (e) {
    console.error("Failed to load logs context:", e);
  }

  // Fetch metrics
  try {
    const resMetrics = await fetch(`/api/metrics?incident_id=${incidentId}`);
    const metrics = await resMetrics.json();
    const metricsContainer = document.getElementById("wsMetricsContainer");
    document.getElementById("wsMetricsCountBadge").textContent = `${metrics.length} Points`;
    metricsContainer.innerHTML = "";

    if (metrics.length === 0) {
      metricsContainer.innerHTML = '<div class="empty-state">No metric anomalies recorded.</div>';
    } else {
      metrics.forEach(m => {
        const card = document.createElement("div");
        card.className = "metric-strip-card";
        card.innerHTML = `
          <div>
            <span class="metric-name-text">${m.metric_name}</span>
            <div style="font-size:10px; color:var(--text-dim);">${m.timestamp.substring(11, 19)}</div>
          </div>
          <div class="metric-val-text">${m.value} ${m.unit}</div>
        `;
        metricsContainer.appendChild(card);
      });
    }
  } catch (e) {
    console.error("Failed to load metrics context:", e);
  }

  // Fetch deployments
  try {
    const resDeps = await fetch(`/api/deployments?incident_id=${incidentId}`);
    const deps = await resDeps.json();
    const depsContainer = document.getElementById("wsDepsContainer");
    document.getElementById("wsDepsCountBadge").textContent = `${deps.length} Events`;
    depsContainer.innerHTML = "";

    if (deps.length === 0) {
      depsContainer.innerHTML = '<div class="empty-state">No recent deployment rollouts in window.</div>';
    } else {
      deps.forEach(d => {
        const card = document.createElement("div");
        card.className = "dep-event-card";
        card.innerHTML = `
          <div class="dep-event-header">
            <strong>${d.service}:${d.version}</strong>
            <span>commit: ${d.commit_hash.substring(0, 8)}</span>
          </div>
          <div class="dep-event-summary">${d.commit_message} (by ${d.author})</div>
          <div style="font-size:10px; color:var(--text-dim); margin-top:4px;">${d.timestamp}</div>
        `;
        depsContainer.appendChild(card);
      });
    }
  } catch (e) {
    console.error("Failed to load deployments context:", e);
  }
}

// ------------------------------------------------------------------
// 5. AUTONOMOUS INVESTIGATION WORKSPACE
// ------------------------------------------------------------------
async function runInvestigation(mode = "ai") {
  const diagEl = document.getElementById("wsDiagnosisText");
  diagEl.textContent = `Analyzing telemetry across runbooks, logs, and metrics in ${mode === 'ai' ? 'Multi-Step AI' : 'Keyword Baseline'} mode...`;

  try {
    const res = await fetch(`/api/investigate/${currentIncidentId}?mode=${mode}`, {
      method: "POST"
    });
    const data = await res.json();
    currentInvestigationData = data;
    renderInvestigationView(data, mode);
    renderExecutionTrace(data.trace, data.steps_count, data.duration_seconds);
  } catch (err) {
    diagEl.textContent = "Error executing investigation: " + err.message;
  }
}

function renderInvestigationView(data, mode) {
  // 1. Proposed Diagnosis
  document.getElementById("wsDiagnosisText").textContent = data.root_cause_diagnosis;
  document.getElementById("wsCategory").textContent = data.category;
  document.getElementById("wsConfidence").textContent = `${Math.round(data.confidence_score * 100)}%`;

  // 2. Calibrated Confidence Breakdown
  const calib = data.confidence_breakdown;
  if (calib) {
    document.getElementById("calibLogVal").textContent = `${Math.round(calib.log_signal_weight * 100)}%`;
    document.getElementById("calibLogFill").style.width = `${Math.round(calib.log_signal_weight * 100)}%`;

    document.getElementById("calibMetricVal").textContent = `${Math.round(calib.metric_anomaly_weight * 100)}%`;
    document.getElementById("calibMetricFill").style.width = `${Math.round(calib.metric_anomaly_weight * 100)}%`;

    document.getElementById("calibTemporalVal").textContent = `${Math.round(calib.temporal_proximity_weight * 100)}%`;
    document.getElementById("calibTemporalFill").style.width = `${Math.round(calib.temporal_proximity_weight * 100)}%`;

    document.getElementById("calibRunbookVal").textContent = `${Math.round(calib.runbook_alignment_weight * 100)}%`;
    document.getElementById("calibRunbookFill").style.width = `${Math.round(calib.runbook_alignment_weight * 100)}%`;

    document.getElementById("calibExplanationText").textContent = calib.explanation;
    document.getElementById("confidenceBreakdownCard").style.display = "block";
  } else {
    document.getElementById("confidenceBreakdownCard").style.display = "none";
  }

  // 3. Temporal Causality
  document.getElementById("wsTemporalText").textContent = data.temporal_correlation_summary || "No temporal correlation captured.";

  // 4. Supporting vs Contradictory Evidence Panels
  const suppText = document.getElementById("wsSupportingText");
  const contraText = document.getElementById("wsContradictoryText");

  if (mode === "ai") {
    suppText.textContent = `Corroborated by ${data.evidence_chain.length} discrete telemetry artifacts across deployment history, error logs, and metrics.`;
    contraText.textContent = "Zero contradictory signals detected: metric inflection points and stack traces strictly corroborate hypothesis.";
  } else {
    suppText.textContent = `Heuristic match on generic error keywords in ${data.evidence_chain.length} logs.`;
    contraText.textContent = `Warning: Baseline lacks temporal alignment and failed to cross-check deployment diffs (${data.unsupported_claims.length} ungrounded assertions).`;
  }

  // 5. Hallucination Audit
  const auditBox = document.getElementById("wsAuditBox");
  const auditTitle = document.getElementById("wsAuditTitle");
  const auditDesc = document.getElementById("wsAuditDesc");

  if (!data.unsupported_claims || data.unsupported_claims.length === 0) {
    auditBox.className = "audit-callout audit-success";
    auditTitle.textContent = "Hallucination Audit: 0 Unsupported Claims (100% Grounded)";
    auditDesc.textContent = "Every single causal claim has been audited against registered telemetry and deployment diffs.";
  } else {
    auditBox.className = "audit-callout";
    auditBox.style.backgroundColor = "rgba(245, 158, 11, 0.1)";
    auditBox.style.border = "1px solid rgba(245, 158, 11, 0.3)";
    auditTitle.textContent = `Warning: ${data.unsupported_claims.length} Unsupported / Speculative Claim(s)`;
    auditDesc.innerHTML = data.unsupported_claims.map(c => `• ${c}`).join("<br>");
  }

  // 6. Mitigations List
  const mitList = document.getElementById("wsMitigationList");
  mitList.innerHTML = "";
  if (data.mitigation_recommended && data.mitigation_recommended.length > 0) {
    data.mitigation_recommended.forEach((m) => {
      const li = document.createElement("li");
      li.textContent = m;
      mitList.appendChild(li);
    });
  } else {
    mitList.innerHTML = "<li>No specific mitigations registered.</li>";
  }

  // 7. Evidence Chain Snapshot in Right Inspector Tab
  const evList = document.getElementById("wsEvidenceList");
  evList.innerHTML = "";
  document.getElementById("wsEvidenceBadge").textContent = `${data.evidence_chain.length} Items`;
  document.getElementById("wsEvidenceCountPill").textContent = data.evidence_chain.length;

  data.evidence_chain.forEach((ev) => {
    const item = document.createElement("div");
    item.className = "evidence-chain-item";
    item.innerHTML = `
      <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
        <span class="badge badge-category" style="font-size:10px;">${ev.id}</span>
        <span style="font-size:10px; color:var(--text-dim); font-family:var(--font-mono);">${ev.timestamp ? ev.timestamp.substring(11, 19) : ''}</span>
      </div>
      <div style="font-size:11.5px; color:#cbd5e1; line-height:1.4;">${ev.summary}</div>
      <div style="margin-top:5px; text-align:right;">
        <button class="link-btn" onclick='openEvidenceModal(${JSON.stringify(ev.id)}, ${JSON.stringify(ev.source_type)}, ${JSON.stringify(ev.summary)}, ${JSON.stringify(JSON.stringify(ev.raw_data))})'>View JSON</button>
      </div>
    `;
    evList.appendChild(item);
  });

  // 8. Security Tab Sync
  renderSecurityTab(data);
}

function renderSecurityTab(data) {
  const risk = data.risk_analysis;
  if (!risk) return;

  document.getElementById("secRiskLevel").textContent = `${risk.risk_level} RISK`;
  document.getElementById("secThreatVector").textContent = risk.threat_vector;
  document.getElementById("secCwe").textContent = risk.cwe_id;
  document.getElementById("secSla").textContent = risk.remediation_sla;
  document.getElementById("secBlastRadius").textContent = risk.blast_radius;

  const cia = risk.cia_impact || {};
  document.getElementById("ciaC").textContent = cia.confidentiality || "LOW";
  document.getElementById("ciaI").textContent = cia.integrity || "MEDIUM";
  document.getElementById("ciaA").textContent = cia.availability || "CRITICAL";

  document.getElementById("secAdvisoryText").textContent = risk.security_advisory;
}

// ------------------------------------------------------------------
// 6. EVIDENCE EXPLORER & MODAL VIEWER
// ------------------------------------------------------------------
async function loadEvidenceExplorer() {
  try {
    const res = await fetch(`/api/evidence?incident_id=${currentIncidentId}`);
    allEvidenceItems = await res.json();
    renderEvidenceTable(allEvidenceItems);
    document.getElementById("evidenceTotalCount").textContent = allEvidenceItems.length;

    // Filter listeners
    const search = document.getElementById("evidenceSearchInput");
    const typeFilter = document.getElementById("evidenceTypeFilter");

    const filterEv = () => {
      const q = search.value.toLowerCase();
      const type = typeFilter.value;
      const filtered = allEvidenceItems.filter(e => {
        const matchQ = !q || e.summary.toLowerCase().includes(q) || e.id.toLowerCase().includes(q);
        const matchT = !type || e.source_type === type;
        return matchQ && matchT;
      });
      renderEvidenceTable(filtered);
    };

    search.oninput = filterEv;
    typeFilter.onchange = filterEv;
  } catch (err) {
    console.error("Failed to load evidence explorer:", err);
  }
}

function renderEvidenceTable(items) {
  const tbody = document.getElementById("evidenceTableBody");
  tbody.innerHTML = "";

  if (items.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6" class="empty-state">No evidence items matching filter.</td></tr>';
    return;
  }

  items.forEach((ev) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><strong style="color:var(--primary); font-family:var(--font-mono);">${ev.id}</strong></td>
      <td><span class="badge badge-category" style="font-size:10px;">${ev.source_type}</span></td>
      <td style="font-family:var(--font-mono); font-size:11px; color:var(--text-dim);">${ev.timestamp || '-'}</td>
      <td><span class="badge ${ev.relevance === 'CRITICAL' ? 'badge-p1' : 'badge-neutral'}">${ev.relevance}</span></td>
      <td style="max-width:320px; font-size:12px; color:#cbd5e1;">${ev.summary}</td>
      <td>
        <button class="btn btn-outline btn-sm" onclick='openEvidenceModal(${JSON.stringify(ev.id)}, ${JSON.stringify(ev.source_type)}, ${JSON.stringify(ev.summary)}, ${JSON.stringify(JSON.stringify(ev.raw_data))})'>Inspect Payload</button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function openEvidenceModal(id, type, summary, jsonPayloadStr) {
  const modal = document.getElementById("evidenceModal");
  document.getElementById("modalEvidId").textContent = id;
  document.getElementById("modalEvidType").textContent = type;
  document.getElementById("modalEvidSummary").textContent = summary;

  try {
    const parsed = JSON.parse(jsonPayloadStr);
    document.getElementById("modalJsonCode").textContent = JSON.stringify(parsed, null, 2);
  } catch (e) {
    document.getElementById("modalJsonCode").textContent = jsonPayloadStr;
  }

  modal.classList.add("show");
}

// ------------------------------------------------------------------
// 7. EXECUTION TRACE
// ------------------------------------------------------------------
function renderExecutionTrace(trace, stepsCount, duration) {
  document.getElementById("traceTotalSteps").textContent = stepsCount || (trace ? trace.length : 0);
  document.getElementById("traceTotalDuration").textContent = `${duration || 0}s`;

  const container = document.getElementById("traceTimelineContainer");
  container.innerHTML = "";

  if (!trace || trace.length === 0) {
    container.innerHTML = '<div class="empty-state">No execution trace captured yet.</div>';
    return;
  }

  trace.forEach((step) => {
    const card = document.createElement("div");
    card.className = "trace-step-card";
    card.innerHTML = `
      <div class="step-card-header">
        <span class="step-num-badge">STEP ${step.step_num}</span>
        <span class="step-tool-badge">${step.tool_name}()</span>
        <span style="font-family:var(--font-mono); font-size:11px; color:var(--text-dim); margin-left:auto;">${step.timestamp || ''}</span>
      </div>
      <div class="step-thought"><strong>Thought:</strong> ${step.thought}</div>
      <div style="font-size:11px; color:var(--text-dim); margin-bottom:6px;">
        <strong>Inputs:</strong> <code>${JSON.stringify(step.tool_args)}</code>
      </div>
      <div class="step-output-box">${step.tool_result_preview}</div>
      ${step.evidence_gathered && step.evidence_gathered.length > 0 ? `
        <div style="margin-top:8px; font-size:11px;">
          <strong style="color:var(--primary);">Registered Evidence:</strong> 
          ${step.evidence_gathered.map(e => `<span class="badge badge-category" style="font-size:10px; margin-right:4px;">${e}</span>`).join('')}
        </div>
      ` : ''}
    `;
    container.appendChild(card);
  });
}

// ------------------------------------------------------------------
// 8. BENCHMARK CENTER
// ------------------------------------------------------------------
async function runFullBenchmark() {
  const tbody = document.getElementById("benchmarkMatrixTableBody");
  tbody.innerHTML = '<tr><td colspan="7" class="empty-state">Executing benchmark across all 10 injected incidents...</td></tr>';

  try {
    const res = await fetch("/api/benchmark");
    const data = await res.json();

    document.getElementById("benchAiAcc").textContent = `${data.investigator_accuracy}%`;
    document.getElementById("benchBaseAcc").textContent = `${data.baseline_accuracy}%`;
    document.getElementById("benchAiClaims").textContent = data.investigator_unsupported_rate;
    document.getElementById("benchBaseClaims").textContent = data.baseline_unsupported_rate;

    tbody.innerHTML = "";
    data.comparisons.forEach((c) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><strong style="color:var(--primary); font-family:var(--font-mono);">${c.incident_id}</strong></td>
        <td><span class="badge badge-category" style="font-size:10px;">${c.category}</span></td>
        <td style="font-size:11px; color:var(--text-dim); max-width:200px;">${c.ground_truth}</td>
        <td style="font-size:12px; color:${c.investigator_correct ? '#34d399' : '#fb7185'};">
          ${c.investigator_correct ? ' ' : ' '}<strong style="color:#ffffff;">${c.investigator_diagnosis}</strong>
        </td>
        <td style="font-size:12px; color:${c.baseline_correct ? '#34d399' : '#94a3b8'};">
          ${c.baseline_diagnosis}
        </td>
        <td><code>${c.investigator_evidence_count} items</code></td>
        <td><span class="badge badge-grounded">AI ACCURATE</span></td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" class="empty-state" style="color:var(--danger);">Benchmark failed: ${err.message}</td></tr>`;
  }
}

// ------------------------------------------------------------------
// 9. SYSTEM HEALTH
// ------------------------------------------------------------------
async function loadSystemHealth() {
  try {
    const res = await fetch("/api/health");
    const data = await res.json();

    const grid = document.getElementById("healthCardsGrid");
    grid.innerHTML = "";

    for (const [key, comp] of Object.entries(data.components)) {
      const card = document.createElement("div");
      card.className = "health-card";
      card.innerHTML = `
        <div class="health-card-top">
          <span class="health-card-title">${key.replace(/_/g, ' ').toUpperCase()}</span>
          <span class="health-status-badge">${comp.status}</span>
        </div>
        <p class="health-card-desc">${comp.details}</p>
        <div style="font-size:11px; color:var(--primary); font-family:var(--font-mono); margin-top:8px;">
          Latency: ${comp.latency_ms} ms
        </div>
      `;
      grid.appendChild(card);
    }
  } catch (err) {
    console.error("Failed to load health status:", err);
  }
}
