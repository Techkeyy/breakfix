const API = (window.BREAKFIX_CONFIG && window.BREAKFIX_CONFIG.apiUrl) || "";
const form = document.querySelector("#job-form");
const demo = document.querySelector("#demo");
const changeFields = document.querySelector("#change-fields");
const result = document.querySelector("#result");
const message = document.querySelector("#message");
const ACTIVE_STATUSES = new Set(["QUEUED", "RUNNING", "PROPOSAL_RUNNING", "APPLYING", "VERIFYING"]);
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
    return `<div class="progress-step ${state}" aria-current="${state === "current" ? "step" : "false"}"><span class="progress-index">${number}</span><span class="progress-label">${label}</span></div>`;
  }).join("");
}

function statusMessage(status) {
  return {
    QUEUED: "The job is queued for the bounded engine run.",
    RUNNING: "The remote engine is reading the change and executing selected probes.",
    PROPOSAL_RUNNING: "The existing fix proposal flow is preparing a candidate for review.",
    APPLYING: "The approved candidate is being applied in the isolated verification flow.",
    VERIFYING: "The approved change is being rerun through verification.",
  }[status] || "Evidence is ready. The result below is from the remote job.";
}

demo.addEventListener("change", () => changeFields.classList.toggle("hidden", demo.checked));
document.querySelector("#demo-button").addEventListener("click", () => {
  demo.checked = true;
  changeFields.classList.add("hidden");
  document.querySelector("#repository-url").value = "https://github.com/Techkeyy/breakfix";
});

document.querySelectorAll('a[href="#analyze"]').forEach((link) => link.addEventListener("click", () => {
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
  pill.className = `status-pill ${["COMPLETED", "APPROVED", "REJECTED"].includes(job.status) ? "good" : job.status === "FAILED" ? "bad" : ""}`;
  renderProgress(job.status);
  const outcome = evidence.outcome || job.outcome || "Waiting";
  const regression = evidence.regression;
  document.querySelector("#summary").innerHTML = [
    ["Outcome", outcome],
    ["Provider", evidence.provider_status || job.provider_status || "Waiting"],
    ["Experiments", evidence.experiments_run ?? job.experiments_run ?? "Waiting"],
    ["Regression", regression ? (regression.valid ? "Valid" : "Failed") : "Waiting"],
  ].map(([label, value]) => `<div class="stat"><small>${esc(label)}</small><strong>${esc(value)}</strong></div>`).join("");
  renderAssumptions(evidence);
  renderExperiments(evidence);
  renderFix(evidence, job);
}

function renderAssumptions(evidence) {
  const target = document.querySelector("#assumptions");
  const assumptions = Array.isArray(evidence.assumptions) ? evidence.assumptions : [];
  target.innerHTML = `<h3>Assumptions</h3>${assumptions.length ? `<div class="cards">${assumptions.map((item) => `<article class="card"><h4>${esc(display(item.id, "Assumption"))}</h4><p>${esc(display(item.statement))}</p>${item.surface ? `<span class="tag">${esc(item.surface)}</span>` : ""}${item.risk ? `<span class="tag">${esc(item.risk)}</span>` : ""}</article>`).join("")}</div>` : `<p class="evidence-note">The planner has not returned an assumption yet.</p>`}`;
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
  if (fix.status === "PROPOSED" && !decision) buttons = `<div class="action-row"><button class="action" id="reject" type="button">Reject</button><button class="action approve" id="approve" type="button">Approve &amp; verify</button></div><p class="evidence-note">Approval applies the candidate in an isolated snapshot. Verification remains a separate, explicit step.</p>`;
  else if (job.status === "APPROVED") buttons = `<div class="action-row"><button class="action approve" id="verify" type="button">Run verification</button></div>`;
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
  document.querySelector("#summary").innerHTML = `<article class="notice-card"><h4>Hosted request failed</h4><p>${esc(text)}</p><p>Nothing was changed. Check the repository URL and try the bounded run again.</p></article>`;
  document.querySelector("#assumptions").innerHTML = "";
  document.querySelector("#experiments").innerHTML = "";
  document.querySelector("#fix").innerHTML = "";
}
