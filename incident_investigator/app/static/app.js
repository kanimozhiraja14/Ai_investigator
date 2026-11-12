// AI Incident Investigator Web App Controller

let currentIncidentId = "INC-001";
let allIncidents = [];

document.addEventListener("DOMContentLoaded", async () => {
  await loadIncidents();
  setupEventListeners();
  // Auto-investigate first incident to show live proof immediately
  runInvestigation("ai");
});

async function loadIncidents() {
  try {
    const res = await fetch("/api/incidents");
    allIncidents = await res.json();
    renderIncidentList(allIncidents);
    if (allIncidents.length > 0) {
      selectIncident(allIncidents[0].id);
    }
  } catch (err) {
    console.error("Failed to load incidents:", err);
  }
}

function renderIncidentList(incidents) {
  const container = document.getElementById("incidentList");
  container.innerHTML = "";
  document.getElementById("incidentCount").textContent = incidents.length;

  incidents.forEach((inc) => {
    const item = document.createElement("div");
    item.className = `incident-item ${inc.id === currentIncidentId ? "active" : ""}`;
    item.dataset.id = inc.id;
    item.innerHTML = `
      <div class="item-top">
        <span class="item-id">${inc.id}</span>
        <span class="badge ${inc.severity === 'P1' ? 'badge-p1' : 'badge-p2'}">${inc.severity}</span>
      </div>
      <div class="item-title">${inc.title}</div>
      <div class="item-service">⚙ ${inc.service}</div>
    `;
    item.addEventListener("click", () => selectIncident(inc.id));
    container.appendChild(item);
  });
}

function selectIncident(id) {
  currentIncidentId = id;
  const inc = allIncidents.find((i) => i.id === id);
  if (!inc) return;

  // Update active state in sidebar
  document.querySelectorAll(".incident-item").forEach((el) => {
    el.classList.toggle("active", el.dataset.id === id);
  });

  // Update banner
  document.getElementById("bannerTitle").textContent = `${inc.id}: ${inc.title}`;
  document.getElementById("bannerService").textContent = inc.service;
  document.getElementById("bannerTime").textContent = inc.start_time;
  document.getElementById("bannerAlert").textContent = inc.initial_alert;
  
  const sevEl = document.getElementById("bannerSeverity");
  sevEl.textContent = inc.severity;
  sevEl.className = `badge ${inc.severity === 'P1' ? 'badge-p1' : 'badge-p2'}`;

  // Reset results pane
  document.getElementById("diagText").textContent = "Click 'Investigate with AI Agent' or 'Keyword Search Baseline' to begin.";
  document.getElementById("causalityText").textContent = "Awaiting investigation run...";
  document.getElementById("traceStepsContainer").innerHTML = '<div class="empty-state">No trace generated yet.</div>';
  document.getElementById("evidenceListContainer").innerHTML = '<div class="empty-state">No evidence items registered yet.</div>';
  document.getElementById("mitigationList").innerHTML = '<li>Awaiting runbook retrieval...</li>';
}

function setupEventListeners() {
  document.getElementById("investigateAiBtn").addEventListener("click", () => runInvestigation("ai"));
  document.getElementById("investigateBaseBtn").addEventListener("click", () => runInvestigation("baseline"));
  document.getElementById("runBenchmarkBtn").addEventListener("click", runBenchmarkProof);
  document.getElementById("closeBenchmarkBtn").addEventListener("click", () => {
    document.getElementById("benchmarkCard").style.display = "none";
  });
}

async function runInvestigation(mode = "ai") {
  const diagText = document.getElementById("diagText");
  diagText.textContent = `Analyzing telemetry in ${mode === 'ai' ? 'Multi-Step AI' : 'Keyword Baseline'} mode...`;

  try {
    const res = await fetch(`/api/investigate/${currentIncidentId}?mode=${mode}`, {
      method: "POST"
    });
    const data = await res.json();
    renderInvestigationResult(data, mode);
  } catch (err) {
    diagText.textContent = "Error running investigation: " + err.message;
  }
}

function renderInvestigationResult(data, mode) {
  // 1. Diagnosis & Metadata
  document.getElementById("diagText").textContent = data.root_cause_diagnosis;
  document.getElementById("diagCategory").textContent = data.category;
  document.getElementById("diagConfidence").textContent = `${Math.round(data.confidence_score * 100)}% Confidence`;
  
  // 2. Causality / Correlation
  document.getElementById("causalityText").textContent = data.temporal_correlation_summary || "No temporal correlation captured.";

  // 3. Unsupported Claims Audit
  const auditBox = document.getElementById("auditBox");
  const auditTitle = document.getElementById("auditTitle");
  const auditDesc = document.getElementById("auditDesc");

  if (!data.unsupported_claims || data.unsupported_claims.length === 0) {
    auditBox.className = "audit-box";
    auditTitle.innerHTML = "🛡️ Evidence Verification Audit: 0 Unsupported Claims (100% Verified)";
    auditDesc.textContent = "Every single assertion is backed by verifiable log lines, metrics, or deployment artifacts.";
  } else {
    auditBox.className = "audit-box warning";
    auditTitle.innerHTML = `⚠️ Evidence Verification Audit: ${data.unsupported_claims.length} Unsupported / Speculative Claim(s)`;
    auditDesc.innerHTML = data.unsupported_claims.map(c => `• ${c}`).join("<br>");
  }

  // 3b. Cybersecurity Risk & Threat Assessment
  const risk = data.risk_analysis;
  if (risk) {
    document.getElementById("riskLevelBadge").textContent = `${risk.risk_level} RISK`;
    document.getElementById("riskLevelBadge").className = `badge ${risk.risk_level === 'CRITICAL' ? 'badge-p1' : 'badge-p2'}`;
    document.getElementById("riskVector").textContent = risk.threat_vector;
    document.getElementById("riskCwe").textContent = risk.cwe_id;
    document.getElementById("riskSla").textContent = risk.remediation_sla;
    const cia = risk.cia_impact || {};
    document.getElementById("riskCia").textContent = `C:${cia.confidentiality || 'L'} | I:${cia.integrity || 'M'} | A:${cia.availability || 'H'}`;
    document.getElementById("riskAdvisory").textContent = risk.security_advisory;
    document.getElementById("riskCard").style.display = "block";
  } else {
    document.getElementById("riskCard").style.display = "none";
  }

  // 4. Trace Steps
  const traceContainer = document.getElementById("traceStepsContainer");
  traceContainer.innerHTML = "";
  document.getElementById("traceStepCount").textContent = `${data.steps_count} Steps (${data.duration_seconds}s)`;

  data.trace.forEach((step) => {
    const stepEl = document.createElement("div");
    stepEl.className = "trace-step-item";
    stepEl.innerHTML = `
      <div class="step-meta">
        <span>STEP ${step.step_num}</span>
        <span class="step-tool">${step.tool_name}</span>
      </div>
      <div class="step-thought"><strong>Thought:</strong> ${step.thought}</div>
      <div class="step-preview">${step.tool_result_preview}</div>
    `;
    traceContainer.appendChild(stepEl);
  });

  // 5. Mitigations
  const mitContainer = document.getElementById("mitigationList");
  mitContainer.innerHTML = "";
  if (data.mitigation_recommended && data.mitigation_recommended.length > 0) {
    data.mitigation_recommended.forEach((m) => {
      const li = document.createElement("li");
      li.textContent = m;
      mitContainer.appendChild(li);
    });
  } else {
    mitContainer.innerHTML = "<li>No specific runbook mitigations found.</li>";
  }

  // 6. Evidence Chain
  const evidContainer = document.getElementById("evidenceListContainer");
  evidContainer.innerHTML = "";
  document.getElementById("evidenceCountBadge").textContent = data.evidence_chain.length;

  data.evidence_chain.forEach((ev) => {
    const card = document.createElement("div");
    card.className = "evidence-item-card";
    card.innerHTML = `
      <span class="evidence-tag tag-${ev.source_type}">${ev.id}</span>
      <div class="evidence-summary">${ev.summary}</div>
    `;
    evidContainer.appendChild(card);
  });
}

async function runBenchmarkProof() {
  const benchCard = document.getElementById("benchmarkCard");
  benchCard.style.display = "block";
  benchCard.scrollIntoView({ behavior: "smooth" });

  const tableBody = document.getElementById("benchmarkTableBody");
  tableBody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding: 20px;">Running benchmark across all 10 injected incidents...</td></tr>';

  try {
    const res = await fetch("/api/benchmark");
    const data = await res.json();

    // Summary numbers
    document.getElementById("benchAiAccuracy").textContent = `${data.investigator_accuracy}%`;
    document.getElementById("benchBaseAccuracy").textContent = `${data.baseline_accuracy}%`;
    document.getElementById("benchAiClaims").textContent = data.investigator_unsupported_rate;
    document.getElementById("benchBaseClaims").textContent = data.baseline_unsupported_rate;

    // Render table
    tableBody.innerHTML = "";
    data.comparisons.forEach((c) => {
      const row = document.createElement("tr");
      row.innerHTML = `
        <td><strong>${c.incident_id}</strong></td>
        <td><code>${c.incident_title.split(' ')[0]}</code></td>
        <td style="color:#94a3b8; font-size:11px;">${c.ground_truth}</td>
        <td style="color:${c.investigator_correct ? '#34d399' : '#f87171'}">
          ${c.investigator_correct ? '✅ ' : '❌ '}<strong>${c.investigator_diagnosis}</strong>
        </td>
        <td style="color:${c.baseline_correct ? '#34d399' : '#f87171'}">
          ${c.baseline_correct ? '✅ ' : '❌ '}${c.baseline_diagnosis}
        </td>
        <td><code>${c.investigator_evidence_count} items</code></td>
        <td>
          <span class="badge ${c.investigator_correct ? 'badge-status' : 'badge-p1'}">
            ${c.investigator_correct ? 'AI WON' : 'FAIL'}
          </span>
        </td>
      `;
      tableBody.appendChild(row);
    });
  } catch (err) {
    tableBody.innerHTML = `<tr><td colspan="7" style="color:red; text-align:center;">Failed to run benchmark: ${err.message}</td></tr>`;
  }
}
