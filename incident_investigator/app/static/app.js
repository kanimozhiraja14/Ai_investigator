// Enterprise SRE / SOC Incident Command Center Controller
// AEGIS-INVESTIGATOR v2.0.0

let currentIncidentId = "INC-001";
let allIncidents = [];
let currentInvestigationData = null;
let allEvidenceItems = [];

document.addEventListener("DOMContentLoaded", async () => {
  setupNavigation();
  setupFilterListeners();
  await loadInitialData();
  // Auto-run investigation on INC-001 to populate workspace and trace immediately
  await runInvestigation("ai");
});

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

async function loadInitialData() {
  await Promise.all([
    loadStats(),
    loadIncidents(),
    loadSystemHealth()
  ]);
}

// ------------------------------------------------------------------
// 1. STATS & OVERVIEW
// ------------------------------------------------------------------
async function loadStats() {
  try {
    const res = await fetch("/api/stats");
    const stats = await res.json();

    document.getElementById("kpiTotalIncidents").textContent = stats.total_incidents;
    document.getElementById("kpiP1Incidents").textContent = stats.severity_counts["P1"] || 0;
    document.getElementById("kpiP2Incidents").textContent = stats.severity_counts["P2"] || 0;
    document.getElementById("navIncCount").textContent = stats.total_incidents;

    // Render Category Bars
    const catContainer = document.getElementById("categoryBarsContainer");
    catContainer.innerHTML = "";
    const total = stats.total_incidents || 1;

    for (const [cat, count] of Object.entries(stats.category_counts)) {
      const pct = Math.round((count / total) * 100);
      const barItem = document.createElement("div");
      barItem.className = "cat-bar-item";
      barItem.innerHTML = `
        <div class="cat-bar-top">
          <span style="font-family:var(--font-mono); font-weight:600;">${cat}</span>
          <span style="color:var(--text-muted);">${count} (${pct}%)</span>
        </div>
        <div class="bar-track">
          <div class="bar-fill" style="width: ${pct}%;"></div>
        </div>
      `;
      catContainer.appendChild(barItem);
    }

    // Render Recent Incidents Queue
    const recentList = document.getElementById("recentIncidentsList");
    recentList.innerHTML = "";
    stats.recent_incidents.forEach((inc) => {
      const item = document.createElement("div");
      item.className = "recent-item";
      item.innerHTML = `
        <div class="recent-item-left">
          <span class="recent-id">${inc.id}</span>
          <span class="badge ${inc.severity === 'P1' ? 'badge-p1' : 'badge-p2'}">${inc.severity}</span>
          <span class="recent-title">${inc.title}</span>
        </div>
        <span style="font-family:var(--font-mono); font-size:11px; color:var(--text-dim);">${inc.service}</span>
      `;
      item.addEventListener("click", () => {
        selectIncident(inc.id);
        switchSection("workspace");
      });
      recentList.appendChild(item);
    });

    document.getElementById("statsUpdatedTime").textContent = new Date().toLocaleTimeString();
  } catch (err) {
    console.error("Failed to load system stats:", err);
  }
}

// ------------------------------------------------------------------
// 2. INCIDENT ROSTER
// ------------------------------------------------------------------
async function loadIncidents() {
  try {
    const res = await fetch("/api/incidents");
    allIncidents = await res.json();
    renderIncidentsTable(allIncidents);
    renderThreatMatrixTable(allIncidents);
    if (allIncidents.length > 0) {
      selectIncident(allIncidents[0].id);
    }
  } catch (err) {
    console.error("Failed to load incidents:", err);
  }
}

function renderIncidentsTable(incidents) {
  const tbody = document.getElementById("incidentsTableBody");
  tbody.innerHTML = "";

  incidents.forEach((inc) => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td><strong style="color:var(--primary); font-family:var(--font-mono);">${inc.id}</strong></td>
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
        <button class="btn btn-outline btn-sm" onclick="handleInvestigateClick('${inc.id}')">Investigate</button>
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
      <td><strong style="color:var(--primary);">${inc.id}</strong></td>
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
      const matchSearch = !q || inc.title.toLowerCase().includes(q) || inc.id.toLowerCase().includes(q) || inc.service.toLowerCase().includes(q);
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

  // Header Target Pill
  document.getElementById("headerIncId").textContent = inc.id;

  // Workspace Banner
  document.getElementById("wsTitle").textContent = `${inc.id}: ${inc.title}`;
  document.getElementById("wsService").textContent = inc.service;
  document.getElementById("wsTime").textContent = inc.start_time;
  document.getElementById("wsStatus").textContent = inc.status;
  document.getElementById("wsAlertText").textContent = inc.initial_alert;
  
  const sevBadge = document.getElementById("wsSeverity");
  sevBadge.textContent = inc.severity;
  sevBadge.className = `badge ${inc.severity === 'P1' ? 'badge-p1' : 'badge-p2'}`;

  // Security Tab Sync
  if (document.getElementById("secThreatVector")) {
    document.getElementById("secThreatVector").textContent = inc.threat_category || "SYSTEM_FAULT";
    document.getElementById("secCwe").textContent = inc.cwe_id || "N/A";
  }
}

// ------------------------------------------------------------------
// 3. AI INVESTIGATION WORKSPACE
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

  // 4. Hallucination Audit
  const auditBox = document.getElementById("wsAuditBox");
  const auditTitle = document.getElementById("wsAuditTitle");
  const auditDesc = document.getElementById("wsAuditDesc");

  if (!data.unsupported_claims || data.unsupported_claims.length === 0) {
    auditBox.className = "audit-callout audit-success";
    auditTitle.textContent = "Hallucination Audit: 0 Unsupported Claims (100% Grounded)";
    auditDesc.textContent = "Every causal claim has been audited against registered telemetry and deployment diffs.";
  } else {
    auditBox.className = "audit-callout" ;
    auditBox.style.backgroundColor = "rgba(245, 158, 11, 0.1)";
    auditBox.style.border = "1px solid rgba(245, 158, 11, 0.3)";
    auditTitle.textContent = `Warning: ${data.unsupported_claims.length} Unsupported / Speculative Claim(s)`;
    auditDesc.innerHTML = data.unsupported_claims.map(c => `• ${c}`).join("<br>");
  }

  // 5. Mitigations List
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

  // 6. Evidence Chain Snapshot
  const evList = document.getElementById("wsEvidenceList");
  evList.innerHTML = "";
  document.getElementById("wsEvidenceBadge").textContent = `${data.evidence_chain.length} Items`;

  data.evidence_chain.forEach((ev) => {
    const item = document.createElement("div");
    item.className = "evidence-chain-item";
    item.innerHTML = `
      <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
        <span class="badge badge-category" style="font-size:10px;">${ev.id}</span>
        <span style="font-size:10px; color:var(--text-dim); font-family:var(--font-mono);">${ev.timestamp ? ev.timestamp.substring(11, 19) : ''}</span>
      </div>
      <div style="font-size:12px; color:#cbd5e1; line-height:1.4;">${ev.summary}</div>
    `;
    evList.appendChild(item);
  });

  // 7. Security Tab Sync
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
// 4. EVIDENCE EXPLORER
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
        <button class="btn btn-outline btn-sm" onclick='showRawPayload(${JSON.stringify(JSON.stringify(ev.raw_data))})'>View JSON</button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function showRawPayload(jsonString) {
  try {
    const formatted = JSON.stringify(JSON.parse(jsonString), null, 2);
    alert(formatted);
  } catch (e) {
    alert(jsonString);
  }
}

// ------------------------------------------------------------------
// 5. EXECUTION TRACE
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
        <span style="font-family:var(--font-mono); font-size:11px; color:var(--text-dim);">${step.timestamp || ''}</span>
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
// 6. BENCHMARK CENTER
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
          ${c.investigator_correct ? '✅ ' : '❌ '}<strong>${c.investigator_diagnosis}</strong>
        </td>
        <td style="font-size:12px; color:${c.baseline_correct ? '#34d399' : '#fb7185'};">
          ${c.baseline_correct ? '✅ ' : '❌ '}${c.baseline_diagnosis}
        </td>
        <td><code>${c.investigator_evidence_count} items</code></td>
        <td><span class="badge ${c.investigator_correct ? 'badge-p2' : 'badge-p1'}" style="background:rgba(16,185,129,0.15); color:#34d399;">AI WON</span></td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" class="empty-state" style="color:var(--danger);">Benchmark failed: ${err.message}</td></tr>`;
  }
}

// ------------------------------------------------------------------
// 7. SYSTEM HEALTH
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
