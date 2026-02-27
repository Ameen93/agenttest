const STORAGE_KEY = "agenttest_ops_v1";
const TOKEN_KEY = "agenttest_ops_token";

const pipelineStages = ["Lead", "Contacted", "Discovery", "Proposal", "Won", "Lost"];
const taskStages = ["Todo", "In Progress", "Blocked", "Done"];

const seed = {
  leads: [
    { id: crypto.randomUUID(), company: "Example AI Agency", contact: "Founder", channel: "LinkedIn", value: 18500, notes: "Pitch Setup Sprint", stage: "Lead" }
  ],
  tasks: [
    { id: crypto.randomUUID(), title: "Finalize landing page copy", owner: "Ameen", priority: "High", dueDate: "", notes: "Use pain-first headline", stage: "Todo" }
  ]
};

const state = { leads: [], tasks: [] };
let mode = "local";
let token = localStorage.getItem(TOKEN_KEY) || "";

async function api(path, opts = {}) {
  const headers = { "Content-Type": "application/json", ...(opts.headers || {}) };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(path, { ...opts, headers });
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json();
}

async function detectMode() {
  try {
    const r = await fetch("/api/health");
    if (r.ok) mode = "server";
  } catch {
    mode = "local";
  }
}

async function ensureLogin() {
  if (mode !== "server") return;
  if (token) return;
  const username = prompt("Ops username:", "ameen") || "";
  const password = prompt("Ops password:", "") || "";
  if (!username || !password) {
    alert("Login required for server mode.");
    return;
  }
  try {
    const res = await api("/api/login", { method: "POST", body: JSON.stringify({ username, password }) });
    token = res.token;
    localStorage.setItem(TOKEN_KEY, token);
  } catch (e) {
    alert("Login failed. Refresh and try again.");
  }
}

function loadLocal() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : structuredClone(seed);
  } catch {
    return structuredClone(seed);
  }
}

function saveLocal() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

async function loadState() {
  if (mode === "server" && token) {
    const remote = await api("/api/state");
    state.leads = remote.leads || [];
    state.tasks = (remote.tasks || []).map(t => ({ ...t, dueDate: t.due_date ?? t.dueDate ?? "" }));
    return;
  }
  const local = loadLocal();
  state.leads = local.leads || [];
  state.tasks = local.tasks || [];
}

function metric(label, value) {
  return `<div class="metric"><div class="value">${value}</div><div class="label">${label}</div></div>`;
}

function renderMetrics() {
  const won = state.leads.filter(l => l.stage === "Won");
  const pipelineValue = state.leads.filter(l => !["Won", "Lost"].includes(l.stage)).reduce((a, l) => a + (Number(l.value) || 0), 0);
  const wonValue = won.reduce((a, l) => a + (Number(l.value) || 0), 0);
  document.getElementById("metrics").innerHTML = [
    metric("Mode", mode === "server" ? "Server" : "Local"),
    metric("Open Leads", state.leads.filter(l => !["Won", "Lost"].includes(l.stage)).length),
    metric("Pipeline Value", `R ${pipelineValue.toLocaleString()}`),
    metric("Won Deals", won.length),
    metric("Won Value", `R ${wonValue.toLocaleString()}`),
    metric("Open Tasks", state.tasks.filter(t => t.stage !== "Done").length)
  ].join("");
}

function cardHTML(kind, item) {
  if (kind === "lead") {
    return `<article class="card" draggable="true" data-kind="lead" data-id="${item.id}">
      <h4>${item.company}</h4>
      <p>${item.contact || "No contact"}\n${item.channel} · R ${(Number(item.value)||0).toLocaleString()}</p>
      <span class="tag">${item.stage}</span>
    </article>`;
  }
  return `<article class="card" draggable="true" data-kind="task" data-id="${item.id}">
    <h4>${item.title}</h4>
    <p>${item.owner} · ${item.priority}${item.dueDate ? ` · due ${item.dueDate}` : ""}</p>
    <span class="tag">${item.stage}</span>
  </article>`;
}

function renderBoard(containerId, stages, items, kind) {
  const board = document.getElementById(containerId);
  board.innerHTML = stages.map(stage => {
    const cards = items.filter(i => i.stage === stage).map(i => cardHTML(kind, i)).join("");
    return `<section class="column" data-stage="${stage}" data-kind="${kind}">
      <h3>${stage}</h3>
      <div class="dropzone">${cards}</div>
    </section>`;
  }).join("");
}

function render() {
  renderMetrics();
  renderBoard("pipelineBoard", pipelineStages, state.leads, "lead");
  renderBoard("taskBoard", taskStages, state.tasks, "task");
  wireDnD();
}

function persist() {
  if (mode === "local") saveLocal();
}

function wireDnD() {
  let drag = null;
  document.querySelectorAll(".card").forEach(el => {
    el.addEventListener("dragstart", e => {
      drag = { id: el.dataset.id, kind: el.dataset.kind };
      e.dataTransfer.effectAllowed = "move";
    });
  });
  document.querySelectorAll(".column").forEach(col => {
    col.addEventListener("dragover", e => e.preventDefault());
    col.addEventListener("drop", async e => {
      e.preventDefault();
      if (!drag || drag.kind !== col.dataset.kind) return;
      const list = drag.kind === "lead" ? state.leads : state.tasks;
      const item = list.find(x => x.id === drag.id);
      if (!item) return;
      item.stage = col.dataset.stage;
      if (mode === "server") {
        const base = drag.kind === "lead" ? "leads" : "tasks";
        await api(`/api/${base}/${item.id}/stage`, { method: "PATCH", body: JSON.stringify({ stage: item.stage }) });
      }
      persist();
      render();
    });
  });
}

function setupDialogs() {
  const leadDialog = document.getElementById("leadDialog");
  const taskDialog = document.getElementById("taskDialog");

  document.getElementById("addLeadBtn").onclick = () => leadDialog.showModal();
  document.getElementById("addTaskBtn").onclick = () => taskDialog.showModal();

  document.getElementById("leadForm").addEventListener("submit", async e => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const lead = {
      id: crypto.randomUUID(),
      company: String(fd.get("company") || "").trim(),
      contact: String(fd.get("contact") || "").trim(),
      channel: String(fd.get("channel") || "Other"),
      value: Number(fd.get("value") || 0),
      notes: String(fd.get("notes") || "").trim(),
      stage: "Lead"
    };

    if (mode === "server") {
      await api("/api/leads", { method: "POST", body: JSON.stringify(lead) });
      await loadState();
    } else {
      state.leads.push(lead);
      persist();
    }

    leadDialog.close();
    e.target.reset();
    render();
  });

  document.getElementById("taskForm").addEventListener("submit", async e => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const task = {
      id: crypto.randomUUID(),
      title: String(fd.get("title") || "").trim(),
      owner: String(fd.get("owner") || "").trim(),
      priority: String(fd.get("priority") || "Medium"),
      dueDate: String(fd.get("dueDate") || ""),
      notes: String(fd.get("notes") || "").trim(),
      stage: "Todo"
    };

    if (mode === "server") {
      await api("/api/tasks", { method: "POST", body: JSON.stringify(task) });
      await loadState();
    } else {
      state.tasks.push(task);
      persist();
    }

    taskDialog.close();
    e.target.reset();
    render();
  });
}

function setupDataOps() {
  document.getElementById("exportBtn").onclick = () => {
    const blob = new Blob([JSON.stringify(state, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `agenttest-ops-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  document.getElementById("importInput").addEventListener("change", async e => {
    if (mode === "server") {
      alert("Import is local-only in this version. Use local mode or add API bulk import next.");
      return;
    }
    const f = e.target.files?.[0];
    if (!f) return;
    const imported = JSON.parse(await f.text());
    state.leads = imported.leads || [];
    state.tasks = imported.tasks || [];
    persist();
    render();
  });

  document.getElementById("resetBtn").onclick = () => {
    if (mode === "server") {
      alert("Reset disabled in server mode.");
      return;
    }
    if (!confirm("Reset all data?")) return;
    state.leads = [];
    state.tasks = [];
    persist();
    render();
  };
}

async function boot() {
  await detectMode();
  await ensureLogin();
  await loadState();
  setupDialogs();
  setupDataOps();
  render();
}

boot();
