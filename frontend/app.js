const API = (window.BREAKFIX_CONFIG && window.BREAKFIX_CONFIG.apiUrl) || "";
const form = document.querySelector("#job-form");
const demo = document.querySelector("#demo");
const changeFields = document.querySelector("#change-fields");
const result = document.querySelector("#result");
const message = document.querySelector("#message");
const ACTIVE_STATUSES = new Set(["QUEUED", "RUNNING", "PROPOSAL_RUNNING", "APPLYING", "VERIFYING"]);
const modeTabs = [...document.querySelectorAll("[data-analysis-mode]")];
const modePanels = [...document.querySelectorAll("[data-analysis-panel]")];
let currentJob = null;

const esc = (value) => String(value ?? "").replace(/[&<>\"']/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;", "'":"&#39;"}[char]));
const display = (value, fallback = "Not returned") => value === null || value === undefined || value === "" ? fallback : value;
const api = async (path, options = {}) => {
  const response = await fetch(`${API}${path}`, { headers: { "Content-Type": "application/json" }, ...options });
  const data = await response.json().catch(() => ({ error: "The API returned an invalid response." }));
  if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
  return data;
};

const stages = [
  ["01", "Reading change"],
  ["02", "Finding assumptions"],
  ["03", "Selecting experiments"],
  ["04", "Executing"],
  ["05", "Building evidence"],
];

function stageIndex(status) {
  return { QUEUED: 0, RUNNING: 2, PROPOSAL_RUNNING: 4, APPLYING: 4, VERIFYING: 4 }[status] ?? 4;
}

function renderProgress(status) {
  const current = stageIndex(status);
  const finished = !ACTIVE_STATUSES.has(status);
  document.querySelector("#analysis-progress").innerHTML = stages.map(([number, label], index) => {
    const state = finished || index < current ? "complete" : index === current ? "current" : "";
    const stateLabel = state === "current" ? "active" : state === "complete" ? "complete" : "waiting";
    return `<div class="progress-step ${state}" aria-current="${state === "current" ? "step" : "false"}"><span class="progress-index">${number}</span><span class="progress-label">${label}</span><span class="progress-state">${stateLabel}</span></div>`;
  }).join("");
}

function statusMessage(status) {
  return {
    QUEUED: "Queued: waiting for the bounded worker to start.",
    RUNNING: "Running: the remote engine is reading the change and executing selected probes.",
    PROPOSAL_RUNNING: "Preparing fix: the existing proposal flow is preparing a candidate for review.",
    APPLYING: "Applying approved fix: the candidate is being applied in the isolated verification flow.",
    VERIFYING: "Verifying: the approved change is being rerun through verification.",
  }[status] || "Evidence is ready. The result below is from the remote job.";
}

function runState(status, evidence, job) {
  if (status === "QUEUED") return { tone: "active", label: "QUEUED", title: "WAITING FOR THE BOUNDED WORKER", detail: "No percentage estimate · actual job status", copy: statusMessage(status) };
  if (status === "RUNNING") return { tone: "active", label: "RUNNING", title: "RUNNING THE BOUNDED ENGINE", detail: "Reading change · selecting probes · building evidence", copy: statusMessage(status) };
  if (status === "PROPOSAL_RUNNING") return { tone: "active", label: "PROPOSAL RUNNING", title: "PREPARING FIX", detail: "Existing approval-gated proposal flow", copy: statusMessage(status) };
  if (status === "APPLYING") return { tone: "active", label: "APPLYING", title: "APPLYING APPROVED FIX", detail: "Isolated snapshot", copy: statusMessage(status) };
  if (status === "VERIFYING") return { tone: "active", label: "VERIFYING", title: "VERIFYING APPROVED CHANGE", detail: "Existing verification flow", copy: statusMessage(status) };
  if (job?.error) return { tone: "error", label: status || "ERROR", title: "ANALYSIS STOPPED", detail: "Backend returned an error", copy: job.error };
  if (evidence?.verification?.status === "VERIFIED") return { tone: "terminal", label: "VERIFIED", title: "VERIFIED", detail: "Approval and verification complete", copy: "The approved change was rerun through the existing verification flow." };
  if (status === "APPROVED") return { tone: "waiting", label: "APPROVED", title: "READY FOR VERIFICATION", detail: "Execution is stopped until you start verification", copy: "The approved candidate is ready for the existing verification step." };
  if (evidence?.fix?.status === "PROPOSED" && !evidence?.fix_decision) return { tone: "waiting", label: "WAITING", title: "WAITING FOR YOUR APPROVAL", detail: "Execution is stopped until you choose an action", copy: "Review the proposal below. Approval applies the candidate in an isolated snapshot." };
  if (evidence?.outcome === "CONFIRMED BREAK") return { tone: "terminal", label: "CONFIRMED BREAK", title: "CONFIRMED BREAK", detail: "Evidence is ready for the approval-gated fix loop", copy: "A targeted experiment reproduced the expected failure." };
  if (evidence?.outcome === "NO BREAK CONFIRMED") return { tone: "terminal", label: "NO BREAK CONFIRMED", title: "NO BREAK CONFIRMED", detail: "Evidence is ready", copy: "The bounded run did not reproduce a failure." };
  return { tone: "terminal", label: status || "COMPLETED", title: "EVIDENCE READY", detail: "Bounded run complete", copy: statusMessage(status) };
}

function renderRunState(job, evidence) {
  const target = document.querySelector("#run-state");
  const state = runState(job.status, evidence, job);
  const active = ACTIVE_STATUSES.has(job.status);
  result.setAttribute("aria-busy", String(active));
  target.className = `run-state ${state.tone}`;
  target.innerHTML = `<div class="run-state-head"><span class="run-state-indicator" aria-hidden="true"></span><span>${esc(state.label)}</span></div><strong class="run-state-title">${esc(state.title)}</strong><p class="run-state-copy">${esc(state.copy)}</p><div class="run-state-detail">${esc(state.detail)}</div>`;
}

function setAnalysisMode(mode, { focus = false } = {}) {
  modeTabs.forEach((tab) => {
    const selected = tab.dataset.analysisMode === mode;
    tab.setAttribute("aria-selected", String(selected));
    tab.classList.toggle("active", selected);
    tab.tabIndex = selected ? 0 : -1;
  });
  modePanels.forEach((panel) => {
    panel.hidden = panel.dataset.analysisPanel !== mode;
  });
  if (focus) document.querySelector(`#${mode}-mode-tab`)?.focus();
}

modeTabs.forEach((tab, index) => {
  tab.addEventListener("click", () => setAnalysisMode(tab.dataset.analysisMode));
  tab.addEventListener("keydown", (event) => {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    const nextIndex = event.key === "Home" ? 0 : event.key === "End" ? modeTabs.length - 1 : (index + (event.key === "ArrowRight" ? 1 : -1) + modeTabs.length) % modeTabs.length;
    setAnalysisMode(modeTabs[nextIndex].dataset.analysisMode, { focus: true });
  });
});

document.querySelectorAll("[data-copy-target]").forEach((button) => {
  button.addEventListener("click", async () => {
    const target = document.querySelector(`#${button.dataset.copyTarget}`);
    const command = target?.textContent.trim();
    if (!command) return;
    try {
      await navigator.clipboard.writeText(command);
    } catch {
      const fallback = document.createElement("textarea");
      fallback.value = command;
      fallback.setAttribute("readonly", "");
      fallback.style.position = "fixed";
      fallback.style.opacity = "0";
      document.body.appendChild(fallback);
      fallback.select();
      const copied = document.execCommand("copy");
      fallback.remove();
      if (!copied) throw new Error("copy failed");
    }
    const original = button.dataset.originalLabel || button.textContent;
    button.dataset.originalLabel = original;
    button.textContent = "Copied";
    window.setTimeout(() => { button.textContent = original; }, 1600);
  });
});

demo.addEventListener("change", () => changeFields.classList.toggle("hidden", demo.checked));
document.querySelector("#demo-button").addEventListener("click", () => {
  demo.checked = true;
  changeFields.classList.add("hidden");
  document.querySelector("#repository-url").value = "https://github.com/Techkeyy/breakfix";
});

document.querySelectorAll('a[href="#analyze"]').forEach((link) => link.addEventListener("click", () => {
  setAnalysisMode("public");
  window.setTimeout(() => document.querySelector("#repository-url").focus(), 350);
}));

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  message.textContent = "Submitting a bounded job...";
  result.classList.remove("hidden");
  result.scrollIntoView({ behavior: "smooth", block: "start" });
  try {
    const body = { repository_url: document.querySelector("#repository-url").value.trim(), demo: demo.checked };
    const task = document.querySelector("#task").value.trim();
    if (task) body.task = task;
    if (!demo.checked) body.change = { kind: "commit", reference: document.querySelector("#reference").value.trim() };
    const job = await api("/api/jobs", { method: "POST", body: JSON.stringify(body) });
    currentJob = job.job_id;
    renderJob(job, {});
    message.textContent = statusMessage(job.status);
    await poll();
  } catch (error) {
    message.textContent = error.message;
    renderError(error.message);
  }
});

async function poll() {
  for (;;) {
    const job = await api(`/api/jobs/${currentJob}`);
    const evidence = job.result || {};
    renderJob(job, evidence);
    message.textContent = job.error || statusMessage(job.status);
    if (!ACTIVE_STATUSES.has(job.status)) return;
    await new Promise((resolve) => setTimeout(resolve, 1800));
  }
}

function renderJob(job, evidence) {
  document.querySelector("#result-title").textContent = `Job ${job.job_id ? job.job_id.slice(0, 8) : ""}`;
  const pill = document.querySelector("#status-pill");
  pill.textContent = job.status || "QUEUED";
  const pillTone = job.status === "FAILED" ? "error" : job.status === "VERIFYING" || ACTIVE_STATUSES.has(job.status) ? "active" : evidence.verification?.status === "VERIFIED" ? "verified" : evidence.fix?.status === "PROPOSED" && !evidence.fix_decision ? "waiting" : evidence.outcome === "CONFIRMED BREAK" ? "break" : ["COMPLETED", "APPROVED", "REJECTED"].includes(job.status) ? "good" : "";
  pill.className = `status-pill ${pillTone}`;
  renderProgress(job.status);
  const outcome = evidence.outcome || job.outcome || "Waiting";
  const regression = evidence.regression;
  document.querySelector("#summary").innerHTML = [
    ["Outcome", outcome],
    ["Provider", evidence.provider_status || job.provider_status || "Waiting"],
    ["Experiments", evidence.experiments_run ?? job.experiments_run ?? "Waiting"],
    ["Regression", regression ? (regression.valid ? "Valid" : "Failed") : "Waiting"],
  ].map(([label, value]) => `<div class="stat"><small>${esc(label)}</small><strong>${esc(value)}</strong></div>`).join("");
  renderRunState(job, evidence);
  renderAssumptions(evidence);
  renderExperiments(evidence);
  renderFix(evidence, job);
}

function renderAssumptions(evidence) {
  const target = document.querySelector("#assumptions");
  const assumptions = Array.isArray(evidence.assumptions) ? evidence.assumptions : [];
  target.innerHTML = `<h3>Assumptions</h3>${assumptions.length ? `<div class="cards">${assumptions.map((item, index) => { const risk = String(item.risk || "").toLowerCase(); const riskTone = risk.includes("high") ? "risk-high" : risk.includes("medium") ? "risk-medium" : ""; const selected = item.selected === true || item.status === "SELECTED" ? "selected" : ""; return `<article class="card assumption-card ${riskTone} ${selected}"><h4><span class="assumption-marker">A${String(index + 1).padStart(2, "0")}</span>${esc(display(item.id, "Assumption"))}</h4><p>${esc(display(item.statement))}</p>${item.surface ? `<span class="tag">${esc(item.surface)}</span>` : ""}${item.risk ? `<span class="tag">${esc(item.risk)}</span>` : ""}${item.experiment_id ? `<span class="tag">${esc(item.experiment_id)}</span>` : ""}</article>`; }).join("")}</div>` : `<p class="evidence-note">The planner has not returned an assumption yet.</p>`}`;
}

function renderExperiments(evidence) {
  const target = document.querySelector("#experiments");
  const experiments = Array.isArray(evidence.experiments) ? evidence.experiments : [];
  target.innerHTML = `<h3>Targeted evidence</h3>${experiments.length ? `<div class="cards">${experiments.map((item) => {
    const actual = item.actual_behavior || {};
    const output = actual.output === undefined ? "" : `<pre>${esc(JSON.stringify(actual.output, null, 2))}</pre>`;
    return `<article class="card"><h4>${esc(display(item.experiment_id, "Experiment"))}</h4><p>${esc(display(item.description))}</p><dl class="detail-grid"><div><dt>Expected</dt><dd>${esc(display(item.expected_behavior))}</dd></div><div><dt>Evidence state</dt><dd>${esc(display(item.evidence_state))}</dd></div><div><dt>Actual process</dt><dd>${actual.process_failed ? "Process failed" : "Process completed"}</dd></div></dl>${output}</article>`;
  }).join("")}</div>` : `<p class="evidence-note">Targeted experiments will appear here after the planner responds.</p>`}`;
}

function renderFix(evidence, job) {
  const target = document.querySelector("#fix");
  const fix = evidence.fix;
  const verification = evidence.verification;
  if (verification) {
    const verificationState = verification.status || "Verification returned";
    target.innerHTML = `<h3>Verification</h3><article class="card"><h4>${esc(verificationState)}</h4><p>The approved change was rerun through the existing verification flow.</p><dl class="detail-grid"><div><dt>Visible tests</dt><dd>${esc(display(verification.visible_tests && verification.visible_tests.exit_code === 0 ? "Passed" : "Returned evidence"))}</dd></div><div><dt>Regression</dt><dd>${esc(display(verification.regression && verification.regression.exit_code === 0 ? "Passed" : "Returned evidence"))}</dd></div></dl></article>`;
    return;
  }
  if (!fix && evidence.outcome === "CONFIRMED BREAK") {
    target.innerHTML = `<h3>Fix loop</h3><article class="card"><p>A confirmed break is available. Generate the existing approval-gated proposal.</p><div class="action-row"><button class="action" id="propose" type="button">Propose fix</button></div></article>`;
    document.querySelector("#propose").onclick = () => operation("propose-fix");
    return;
  }
  if (!fix) { target.innerHTML = ""; return; }
  const decision = evidence.fix_decision && evidence.fix_decision.status;
  let buttons = "";
  if (job.status === "APPROVED") buttons = `<div class="action-row"><button class="action approve" id="verify" type="button">Run verification</button></div>`;
  else if (fix.status === "PROPOSED" && !decision) buttons = `<div class="action-row"><button class="action" id="reject" type="button">Reject</button><button class="action approve" id="approve" type="button">Approve &amp; verify</button></div><p class="evidence-note">Approval applies the candidate in an isolated snapshot. Verification remains a separate, explicit step.</p>`;
  else if (decision) buttons = `<p class="evidence-note">Human decision: ${esc(decision)}.</p>`;
  target.innerHTML = `<h3>Fix proposal</h3><article class="card"><h4>${esc(display(fix.summary, fix.status))}</h4><p>${esc(Array.isArray(fix.files_changed) ? fix.files_changed.join(", ") : display(fix.files_changed, "No files listed"))}</p>${Array.isArray(fix.tests_to_run) && fix.tests_to_run.length ? `<p>Tests: ${esc(fix.tests_to_run.join(", "))}</p>` : ""}${fix.patch ? `<pre>${esc(fix.patch)}</pre>` : ""}${buttons}</article>`;
  if (document.querySelector("#approve")) document.querySelector("#approve").onclick = () => operation("approve-fix");
  if (document.querySelector("#reject")) document.querySelector("#reject").onclick = () => operation("reject-fix");
  if (document.querySelector("#verify")) document.querySelector("#verify").onclick = () => operation("verify");
}

async function operation(name) {
  try {
    message.textContent = "Running the approval-gated operation remotely...";
    await api(`/api/jobs/${currentJob}/${name}`, { method: "POST", body: "{}" });
    await poll();
  } catch (error) {
    message.textContent = error.message;
  }
}

function renderError(text) {
  result.classList.remove("hidden");
  document.querySelector("#status-pill").textContent = "ERROR";
  document.querySelector("#status-pill").className = "status-pill bad";
  document.querySelector("#analysis-progress").innerHTML = "";
  result.setAttribute("aria-busy", "false");
  const runStateTarget = document.querySelector("#run-state");
  runStateTarget.className = "run-state error";
  runStateTarget.innerHTML = `<div class="run-state-head"><span class="run-state-indicator" aria-hidden="true"></span><span>ERROR</span></div><strong class="run-state-title">ANALYSIS STOPPED</strong><p class="run-state-copy">${esc(text)}</p><div class="run-state-detail">No active job remains</div>`;
  document.querySelector("#summary").innerHTML = `<article class="notice-card"><h4>Hosted request failed</h4><p>${esc(text)}</p><p>Nothing was changed. Check the repository URL and try the bounded run again.</p></article>`;
  document.querySelector("#assumptions").innerHTML = "";
  document.querySelector("#experiments").innerHTML = "";
  document.querySelector("#fix").innerHTML = "";
}
