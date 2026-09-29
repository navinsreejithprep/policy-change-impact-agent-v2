const $ = (sel) => document.querySelector(sel);

const els = {
  input: $("#user-input"),
  submitBtn: $("#submit-btn"),
  activity: $("#activity"),
  activityList: $("#activity-list"),
  confirmCard: $("#confirm-card"),
  confirmTitle: $("#confirm-title"),
  confirmGrid: $("#confirm-grid"),
  amendNote: $("#amend-note"),
  confirmBtn: $("#confirm-btn"),
  searchAgainBtn: $("#search-again-btn"),
  insufficientCard: $("#insufficient-card"),
  insufficientMessage: $("#insufficient-message"),
  insufficientList: $("#insufficient-list"),
  results: $("#results"),
  kbList: $("#kb-list"),
  kbCount: $("#kb-count"),
  uploadInput: $("#upload-input"),
  uploadLabel: $("#upload-label"),
  uploadLabelText: $("#upload-label-text"),
  ingestResult: $("#ingest-result"),
  regUploadInput: $("#regulation-upload-input"),
  regUploadLabel: $("#regulation-upload-label"),
  regUploadText: $("#regulation-upload-text"),
};

let state = { threadId: null };

document.querySelectorAll(".example-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    els.input.value = btn.dataset.example;
    els.input.focus();
  });
});

els.submitBtn.addEventListener("click", () => runAnalysis());
els.confirmBtn.addEventListener("click", () => runConfirm("confirm"));
els.searchAgainBtn.addEventListener("click", () => runConfirm("search_again"));
els.uploadInput.addEventListener("change", () => uploadDocument());
els.regUploadInput.addEventListener("change", () => runAnalysisFromFile());

loadKnowledge();

async function loadKnowledge() {
  try {
    const res = await fetch("/api/knowledge");
    const data = await res.json();
    renderKnowledge(data.entries || []);
  } catch (e) {
    els.kbList.innerHTML = `<li class="kb-item">Could not load knowledge base: ${escapeHtml(e.message)}</li>`;
  }
}

function renderKnowledge(entries) {
  els.kbCount.textContent = entries.length;
  if (!entries.length) {
    els.kbList.innerHTML = `<li class="kb-item">No knowledge entries found.</li>`;
    return;
  }
  const order = { Obligation: 0, Process: 1, Policy: 2, Control: 3, Owner: 4 };
  const sorted = [...entries].sort((a, b) => (order[a.type] ?? 9) - (order[b.type] ?? 9));
  els.kbList.innerHTML = sorted
    .map((e) => {
      const sourceTag = e.source === "ingested"
        ? `<span class="kb-tag source-ingested">from ${escapeHtml(e.source_document || "upload")}</span>`
        : `<span class="kb-tag source-demo">demo</span>`;
      return `<li class="kb-item">
        <span class="kb-title">${escapeHtml(e.title)}</span>
        <div class="kb-meta"><span class="kb-tag">${escapeHtml(e.type)}</span>${sourceTag}</div>
      </li>`;
    })
    .join("");
}

async function uploadDocument() {
  const file = els.uploadInput.files[0];
  if (!file) return;

  els.uploadLabel.classList.add("loading");
  els.uploadLabelText.textContent = `Ingesting ${file.name}…`;
  els.ingestResult.innerHTML = "";

  try {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch("/api/ingest", { method: "POST", body: formData });
    const data = await res.json();

    if (!res.ok) {
      els.ingestResult.innerHTML = `<div class="err">${escapeHtml(data.detail || "Ingestion failed.")}</div>`;
    } else {
      const lines = [];
      if (data.created && data.created.length) {
        lines.push(`<div class="ok">Added ${data.created.length} entr${data.created.length === 1 ? "y" : "ies"} from "${escapeHtml(file.name)}".</div>`);
      }
      (data.warnings || []).forEach((w) => lines.push(`<div class="warn">${escapeHtml(w)}</div>`));
      els.ingestResult.innerHTML = lines.join("");
      await loadKnowledge();
    }
  } catch (e) {
    els.ingestResult.innerHTML = `<div class="err">Upload failed: ${escapeHtml(e.message)}</div>`;
  } finally {
    els.uploadLabel.classList.remove("loading");
    els.uploadLabelText.textContent = "Upload a document (.pdf, .docx, .txt, .md)";
    els.uploadInput.value = "";
  }
}

function resetPanels() {
  els.confirmCard.style.display = "none";
  els.insufficientCard.style.display = "none";
  els.results.style.display = "none";
  els.results.innerHTML = "";
}

function renderActivity(statusList) {
  els.activity.style.display = "block";
  els.activityList.innerHTML = "";
  statusList.forEach((s) => {
    const li = document.createElement("li");
    li.innerHTML = `<span class="dot"></span><span>${escapeHtml(s)}</span>`;
    els.activityList.appendChild(li);
  });
}

function setLoading(isLoading) {
  els.submitBtn.disabled = isLoading;
  els.confirmBtn.disabled = isLoading;
  els.searchAgainBtn.disabled = isLoading;
  if (isLoading) {
    els.submitBtn.innerHTML = '<span class="spinner"></span>Analyzing…';
  } else {
    els.submitBtn.textContent = "Analyze";
  }
}

async function runAnalysis() {
  const text = els.input.value.trim();
  if (!text) return;
  resetPanels();
  setLoading(true);
  try {
    const res = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_input: text }),
    });
    const data = await res.json();
    handleResponse(data);
  } catch (e) {
    renderActivity(["Request failed: " + e.message]);
  } finally {
    setLoading(false);
  }
}

async function runAnalysisFromFile() {
  const file = els.regUploadInput.files[0];
  if (!file) return;

  resetPanels();
  setLoading(true);
  els.regUploadLabel.classList.add("loading");
  els.regUploadText.textContent = `Extracting and analyzing ${file.name}…`;

  try {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch("/api/analyze-file", { method: "POST", body: formData });
    const data = await res.json();
    if (!res.ok) {
      renderActivity(["Could not analyze the uploaded file: " + (data.detail || "unknown error")]);
    } else {
      els.input.value = "";
      handleResponse(data);
    }
  } catch (e) {
    renderActivity(["Request failed: " + e.message]);
  } finally {
    setLoading(false);
    els.regUploadLabel.classList.remove("loading");
    els.regUploadText.textContent = "Or upload the regulation document (.pdf, .docx, .txt, .md)";
    els.regUploadInput.value = "";
  }
}

async function runConfirm(action) {
  setLoading(true);
  try {
    const res = await fetch("/api/confirm", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ thread_id: state.threadId, action }),
    });
    const data = await res.json();
    handleResponse(data);
  } catch (e) {
    renderActivity(["Request failed: " + e.message]);
  } finally {
    setLoading(false);
  }
}

function handleResponse(data) {
  state.threadId = data.thread_id;
  renderActivity(data.status || []);

  if (data.awaiting_confirmation) {
    renderConfirmation(data.confirmation);
    return;
  }

  els.confirmCard.style.display = "none";
  const report = data.report || {};
  if (report.status === "insufficient_evidence" || report.status === "invalid_input") {
    renderInsufficient(report);
  } else {
    renderResults(report);
  }
}

const AUTHORITY_LABELS = {
  official: "official (allowlisted)",
  likely_official: "likely official (government domain, not on curated allowlist)",
  secondary: "secondary",
};

function renderConfirmation(c) {
  els.confirmCard.style.display = "block";
  els.confirmTitle.textContent = c.title || "(untitled source)";
  const authorityPill = `<span class="pill ${c.authority}">${AUTHORITY_LABELS[c.authority] || c.authority || "unknown"}</span>`;
  const versionPill = `<span class="pill ${c.version_status}">${c.version_status || "unknown"}</span>`;
  els.confirmGrid.innerHTML = `
    <dt>Publisher</dt><dd>${escapeHtml(c.publisher || "—")}</dd>
    <dt>URL</dt><dd><a href="${escapeAttr(c.url || "#")}" target="_blank" rel="noopener">${escapeHtml(c.url || "—")}</a></dd>
    <dt>Authority</dt><dd>${authorityPill}</dd>
    <dt>Version status</dt><dd>${versionPill}</dd>
    <dt>Retrieved at</dt><dd>${escapeHtml(c.retrieved_at || "—")}</dd>
    <dt>Content hash</dt><dd><span class="hash">${escapeHtml(c.content_hash || "—")}</span></dd>
  `;
  if (c.amendment_note) {
    els.amendNote.style.display = "block";
    els.amendNote.textContent = c.amendment_note;
  } else {
    els.amendNote.style.display = "none";
  }
}

function renderInsufficient(report) {
  els.insufficientCard.style.display = "block";
  els.insufficientMessage.textContent = report.message || "Insufficient evidence";
  els.insufficientList.innerHTML = "";
  (report.missing || []).forEach((m) => {
    const li = document.createElement("li");
    li.textContent = m;
    els.insufficientList.appendChild(li);
  });
}

function renderResults(report) {
  els.results.style.display = "block";
  els.results.innerHTML = "";

  section("Executive summary", `<p>${escapeHtml(report.executive_summary || "—")}</p>
    <span class="confidence-badge confidence-${report.confidence || "Medium"}">Confidence: ${report.confidence || "—"}</span>`);

  section("Regulatory requirements", listOrEmpty(report.regulatory_requirements, (r) => `
    <div class="item">
      <div>${escapeHtml(r.requirement || "")}</div>
      <div class="meta"><span class="tag">${escapeHtml(r.affected_area || "Unknown area")}</span>
      ${r.effective_date ? `<span class="tag">Effective: ${escapeHtml(r.effective_date)}</span>` : ""}</div>
    </div>`));

  section("Affected processes", listOrEmpty(report.affected_processes, (p) => `
    <div class="item"><strong>${escapeHtml(p.title || p.id)}</strong><p>${escapeHtml(p.excerpt || "")}</p></div>`));

  section("Impact assessment", listOrEmpty(report.impact_assessment, (i) => `
    <div class="item">
      <strong>${escapeHtml(i.process || "")}</strong>
      <p>${escapeHtml(i.finding || "")}</p>
      <div class="meta">
        <span class="tag priority-${i.priority || "Medium"}">Priority: ${escapeHtml(i.priority || "—")}</span>
        <span class="tag">Confidence: ${escapeHtml(i.confidence || "—")}</span>
      </div>
    </div>`));

  section("Evidence gaps", report.evidence_gaps && report.evidence_gaps.length
    ? `<ul>${report.evidence_gaps.map((g) => `<li>${escapeHtml(g)}</li>`).join("")}</ul>`
    : `<p class="empty-hint">No evidence gaps identified.</p>`);

  if (report.assumptions && report.assumptions.length) {
    section("Assumptions", `<ul>${report.assumptions.map((a) => `<li>${escapeHtml(a)}</li>`).join("")}</ul>`);
  }

  section("Recommended actions", listOrEmpty(report.recommended_actions, (a) => `
    <div class="item">
      <div>${escapeHtml(a.action || "")}</div>
      <div class="meta"><span class="tag">Owner: ${escapeHtml(a.owner || "Unassigned")}</span>
      <span class="tag priority-${a.priority || "Medium"}">Priority: ${escapeHtml(a.priority || "—")}</span></div>
    </div>`));

  section("Sources", listOrEmpty(report.sources, (s) => `
    <div class="item">
      <div><a href="${escapeAttr(s.url || "#")}" target="_blank" rel="noopener">${escapeHtml(s.title || s.url || "Supplied text")}</a></div>
      <div class="meta">
        ${s.authority ? `<span class="pill ${s.authority}">${s.authority}</span>` : ""}
        ${s.version_status ? `<span class="pill ${s.version_status}">${s.version_status}</span>` : ""}
        ${s.content_hash ? `<span class="hash">${escapeHtml(s.content_hash)}</span>` : ""}
      </div>
    </div>`));

  if (report.security_note) {
    section("Security note", `<p>${escapeHtml(report.security_note)}</p>`);
  }

  const disclaimer = document.createElement("div");
  disclaimer.className = "disclaimer";
  disclaimer.textContent = report.disclaimer || "Analytical prototype only. Not legal advice.";
  els.results.appendChild(disclaimer);
}

function section(title, innerHtml) {
  const div = document.createElement("div");
  div.className = "result-section";
  div.innerHTML = `<h3>${escapeHtml(title)}</h3>${innerHtml}`;
  els.results.appendChild(div);
}

function listOrEmpty(list, renderItem) {
  if (!list || !list.length) return `<p class="empty-hint">None recorded.</p>`;
  return list.map(renderItem).join("");
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
function escapeAttr(str) {
  return escapeHtml(str);
}
