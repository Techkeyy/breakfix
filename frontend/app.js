const API = (window.BREAKFIX_CONFIG && window.BREAKFIX_CONFIG.apiUrl) || "";
const form = document.querySelector("#job-form");
const demo = document.querySelector("#demo");
const changeFields = document.querySelector("#change-fields");
const result = document.querySelector("#result");
const message = document.querySelector("#message");
let currentJob = null;

const esc = (value) => String(value ?? "").replace(/[&<>\"']/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;", "'":"&#39;"}[char]));
const api = async (path, options = {}) => {
  const response = await fetch(`${API}${path}`, { headers: { "Content-Type": "application/json" }, ...options });
  const data = await response.json().catch(() => ({ error: "The API returned an invalid response." }));
  if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
  return data;
};

demo.addEventListener("change", () => changeFields.classList.toggle("hidden", demo.checked));
document.querySelector("#demo-button").addEventListener("click", () => {
  demo.checked = true;
  changeFields.classList.add("hidden");
  document.querySelector("#repository-url").value = "https://github.com/Techkeyy/breakfix";
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  message.textContent = "Submitting a bounded job…";
  result.classList.remove("hidden");
  try {
    const body = { repository_url: document.querySelector("#repository-url").value.trim(), demo: demo.checked };
    if (demo.checked) body.task = document.querySelector("#task").value.trim() || undefined;
    else body.change = { kind: "commit", reference: document.querySelector("#reference").value.trim() }, body.task = document.querySelector("#task").value.trim() || undefined;
    const job = await api("/api/jobs", { method: "POST", body: JSON.stringify(body) });
    currentJob = job.job_id;
    message.textContent = "The VPS is cloning the public repository and running the existing BreakFix engine in a bounded container.";
    renderJob(job, {});
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
    if (!["QUEUED", "RUNNING", "PROPOSAL_RUNNING", "APPLYING", "VERIFYING"].includes(job.status)) {
      if (job.status === "COMPLETED" || job.status === "APPROVED" || job.status === "REJECTED") message.textContent = "Evidence is ready. The result below is from the remote job.";
      else message.textContent = job.error || "The hosted job did not complete.";
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 1800));
  }
}

function renderJob(job, evidence) {
  document.querySelector("#result-title").textContent = `Job ${job.job_id ? job.job_id.slice(0, 8) : ""}`;
  const pill = document.querySelector("#status-pill");
  pill.textContent = job.status || "QUEUED";
  pill.className = `pill ${["COMPLETED", "APPROVED", "REJECTED"].includes(job.status) ? "good" : job.status === "FAILED" ? "bad" : ""}`;
  const outcome = evidence.outcome || job.outcome || "Waiting";
  document.querySelector("#summary").innerHTML = [
    ["Outcome", outcome], ["Provider", evidence.provider_status || job.provider_status || "Waiting"],
    ["Experiments", evidence.experiments_run ?? job.experiments_run ?? "—"], ["Regression", evidence.regression ? (evidence.regression.valid ? "Valid" : "Failed") : "—"]
  ].map(([label, value]) => `<div class="stat"><small>${esc(label)}</small><strong>${esc(value)}</strong></div>`).join("");
  renderAssumptions(evidence);
  renderExperiments(evidence);
  renderFix(evidence, job);
}

function renderAssumptions(evidence) {
  const target = document.querySelector("#assumptions");
  const assumptions = evidence.assumptions || [];
  target.innerHTML = `<h3>Assumptions</h3>${assumptions.length ? `<div class="cards">${assumptions.map((item) => `<article class="card"><h4>${esc(item.id || "Assumption")}</h4><p>${esc(item.statement)}</p><span class="tag">${esc(item.surface)}</span><span class="tag">${esc(item.risk)}</span></article>`).join("")}</div>` : `<p class="card">The planner has not returned an assumption yet.</p>`}`;
}

function renderExperiments(evidence) {
  const target = document.querySelector("#experiments");
  const experiments = evidence.experiments || [];
  target.innerHTML = `<h3>Targeted evidence</h3>${experiments.length ? `<div class="cards">${experiments.map((item) => `<article class="card"><h4>${esc(item.experiment_id)} · ${esc(item.evidence_state)}</h4><p>${esc(item.description)}</p><p>${item.actual_behavior && item.actual_behavior.process_failed ? "The isolated process failed." : "The isolated process completed."}</p></article>`).join("")}</div>` : `<p class="card">Targeted experiments will appear here after the planner responds.</p>`}`;
}

function renderFix(evidence, job) {
  const target = document.querySelector("#fix");
  const fix = evidence.fix;
  const verification = evidence.verification;
  if (verification) {
    target.innerHTML = `<h3>Verification</h3><article class="card"><h4>${esc(verification.status)}</h4><p>The approved change was rerun through the existing verification flow.</p></article>`;
    return;
  }
  if (!fix && evidence.outcome === "CONFIRMED BREAK") {
    target.innerHTML = `<h3>Fix loop</h3><article class="card"><p>A confirmed break is available. Generate the existing approval-gated proposal.</p><div class="action-row"><button class="action" id="propose">Propose fix</button></div></article>`;
    document.querySelector("#propose").onclick = () => operation("propose-fix");
    return;
  }
  if (!fix) { target.innerHTML = ""; return; }
  const decision = evidence.fix_decision && evidence.fix_decision.status;
  const buttons = fix.status === "PROPOSED" && !decision ? `<div class="action-row"><button class="action approve" id="approve">Approve and apply</button><button class="action" id="reject">Reject</button></div>` : job.status === "APPROVED" ? `<div class="action-row"><button class="action approve" id="verify">Verify fix</button></div>` : "";
  target.innerHTML = `<h3>Fix proposal</h3><article class="card"><h4>${esc(fix.summary || fix.status)}</h4><p>${esc(fix.files_changed && fix.files_changed.join(", "))}</p>${fix.patch ? `<pre>${esc(fix.patch)}</pre>` : ""}${buttons}</article>`;
  if (document.querySelector("#approve")) document.querySelector("#approve").onclick = () => operation("approve-fix");
  if (document.querySelector("#reject")) document.querySelector("#reject").onclick = () => operation("reject-fix");
  if (document.querySelector("#verify")) document.querySelector("#verify").onclick = () => operation("verify");
}

async function operation(name) {
  try { message.textContent = "Running the approval-gated operation remotely…"; await api(`/api/jobs/${currentJob}/${name}`, { method: "POST", body: "{}" }); await poll(); }
  catch (error) { message.textContent = error.message; }
}

function renderError(text) {
  result.classList.remove("hidden");
  document.querySelector("#status-pill").textContent = "ERROR";
  document.querySelector("#status-pill").className = "pill bad";
  document.querySelector("#summary").innerHTML = `<article class="card"><h4>Hosted request failed</h4><p>${esc(text)}</p></article>`;
  document.querySelector("#assumptions").innerHTML = "";
  document.querySelector("#experiments").innerHTML = "";
  document.querySelector("#fix").innerHTML = "";
}
