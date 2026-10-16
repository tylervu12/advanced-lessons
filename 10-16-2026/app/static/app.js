const $ = (id) => document.getElementById(id);
const state = {
  view: "predictions",
  version: "all",
  data: null,
  batch: null,
  feature: "credit_score",
  rows: [],
  offset: 0,
  decision: "all",
  outcome: "all",
  busy: false,
};
const colors = {
  blue: "#6377df",
  teal: "#36ad9b",
  red: "#df7b84",
  amber: "#e7af62",
  grey: "#dfe5ef",
};
const titles = {
  predictions: ["Predictions", "Loan decisions and their model versions."],
  drift: [
    "Drift",
    "How current inputs and predictions compare with the reference.",
  ],
  outcomes: ["Outcomes", "What happened to the loans we approved."],
};
const esc = (v) =>
  String(v ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const num = (v) => (v == null ? "—" : Number(v).toLocaleString("en-US"));
const pct = (v) => (v == null ? "—" : `${(v * 100).toFixed(1)}%`);
const dec = (v, n = 3) => (v == null ? "—" : Number(v).toFixed(n));
const date = (v) =>
  new Date(v).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  });
function pill(text, type = "") {
  return `<span class="pill ${type}">${esc(text)}</span>`;
}
function card(title, subtitle, body, tag = "") {
  return `<article class="card"><div class="card-head"><div><h2>${title}</h2><p>${subtitle}</p></div>${tag}</div><div class="card-body">${body}</div></article>`;
}
function legend(items) {
  return `<div class="legend">${items.map(([name, color]) => `<span><i style="background:${color}"></i>${name}</span>`).join("")}</div>`;
}
function empty(text) {
  return `<div class="empty">${text}</div>`;
}
function chartStart(title, w, h) {
  return `<svg class="chart" role="img" aria-label="${esc(title)}" viewBox="0 0 ${w} ${h}"><title>${esc(title)}</title>`;
}
function bars(
  names,
  series,
  { percent = false, title = "Distribution", floor = 1, alert = null } = {},
) {
  if (!names.length) return empty("No data in this view yet.");
  const w = 620,
    h = 240,
    left = 44,
    top = 16,
    bottom = 39,
    pw = w - left - 12,
    ph = h - top - bottom;
  const max = percent
    ? Math.max(0.1, ...series.flatMap((s) => s.values)) * 1.12
    : Math.max(floor, ...series.flatMap((s) => s.values)) * 1.18;
  let svg = chartStart(title, w, h);
  for (let i = 0; i <= 4; i++) {
    let value = (max * i) / 4,
      y = top + ph - (ph * i) / 4;
    svg += `<line x1="${left}" x2="${w - 10}" y1="${y}" y2="${y}" stroke="#edf0f5"/><text x="${left - 9}" y="${y + 3}" text-anchor="end">${percent ? Math.round(value * 100) + "%" : max < 2 ? value.toFixed(2) : Math.round(value)}</text>`;
  }
  if (alert !== null) {
    const y = top + ph - (ph * alert) / max;
    svg += `<line x1="${left}" x2="${w - 10}" y1="${y}" y2="${y}" stroke="#e7af62" stroke-dasharray="5 4"/><text x="${w - 12}" y="${y - 5}" text-anchor="end">Investigate ≥ ${alert}</text>`;
  }
  const group = pw / names.length,
    bw = Math.min(28, (group * 0.64) / series.length);
  names.forEach((name, i) => {
    series.forEach((s, j) => {
      let value = s.values[i] || 0,
        height = (ph * value) / max,
        x = left + group * i + group / 2 + (j - series.length / 2) * bw;
      svg += `<rect x="${x}" y="${top + ph - height}" width="${Math.max(2, bw - 3)}" height="${height}" rx="3" fill="${s.color}"><title>${esc(name)} · ${esc(s.name)}: ${percent ? pct(value) : num(value)}</title></rect>`;
    });
    svg += `<text x="${left + group * (i + 0.5)}" y="${h - 15}" text-anchor="middle">${esc(name)}</text>`;
  });
  return svg + "</svg>" + legend(series.map((s) => [s.name, s.color]));
}
function lines(names, series, { percent = true, title = "Trend" } = {}) {
  if (!names.length) return empty("Join matured outcomes to see the trend.");
  const w = 620,
    h = 240,
    left = 42,
    top = 18,
    ph = 180,
    pw = 560;
  let max = percent
    ? 1
    : Math.max(1, ...series.flatMap((s) => s.values.filter((v) => v != null))) *
      1.15;
  let svg = chartStart(title, w, h);
  for (let i = 0; i <= 4; i++) {
    let y = top + ph - (ph * i) / 4;
    svg += `<line x1="${left}" x2="610" y1="${y}" y2="${y}" stroke="#edf0f5"/><text x="${left - 9}" y="${y + 3}" text-anchor="end">${percent ? i * 25 + "%" : dec((max * i) / 4, 1)}</text>`;
  }
  const x = (i) =>
    left + (names.length === 1 ? pw / 2 : (pw * i) / (names.length - 1));
  series.forEach((s) => {
    let path = "",
      previous = false;
    s.values.forEach((v, i) => {
      if (v == null) {
        previous = false;
        return;
      }
      path += `${previous ? "L" : "M"}${x(i)},${top + ph - (v / max) * ph} `;
      previous = true;
    });
    svg += `<path d="${path}" fill="none" stroke="${s.color}" stroke-width="2.5"/>`;
    s.values.forEach((v, i) => {
      if (v != null)
        svg += `<circle cx="${x(i)}" cy="${top + ph - (v / max) * ph}" r="4" fill="${s.color}" stroke="white" stroke-width="2"><title>${esc(names[i])} · ${s.name}: ${percent ? pct(v) : dec(v, 2)}</title></circle>`;
    });
  });
  names.forEach((name, i) => {
    if (names.length <= 8 || i % Math.ceil(names.length / 8) === 0)
      svg += `<text x="${x(i)}" y="226" text-anchor="middle">${esc(name)}</text>`;
  });
  return svg + "</svg>" + legend(series.map((s) => [s.name, s.color]));
}
function donut(counts) {
  const names = ["On time", "Late payment", "Defaulted"],
    palette = [colors.teal, colors.amber, colors.red],
    values = [counts.on_time, counts.late, counts.defaulted],
    total = values.reduce((a, b) => a + b, 0);
  if (!total) return empty("No approved loans have joined outcomes yet.");
  let start = 0,
    svg = `<svg class="donut" viewBox="0 0 180 180" role="img" aria-label="Approved loan outcomes"><circle cx="90" cy="90" r="66" fill="none" stroke="#f0f3f7" stroke-width="18"/>`;
  values.forEach((v, i) => {
    let length = (v / total) * 414.69;
    svg += `<circle cx="90" cy="90" r="66" fill="none" stroke="${palette[i]}" stroke-width="18" stroke-dasharray="${length} ${414.69 - length}" stroke-dashoffset="${-start}" transform="rotate(-90 90 90)"><title>${names[i]}: ${v}</title></circle>`;
    start += length;
  });
  svg += `<text x="90" y="89" text-anchor="middle" class="big">${num(total)}</text><text x="90" y="108" text-anchor="middle" class="small">MATURED LOANS</text></svg>`;
  return `<div class="donut-wrap">${svg}<div>${values.map((v, i) => `<div class="donut-label"><i style="background:${palette[i]}"></i>${names[i]}<b>${num(v)}</b></div>`).join("")}<div class="footer-note">Approved + joined only</div></div></div>`;
}
async function api(path, body) {
  const r = await fetch(
    path,
    body === undefined
      ? {}
      : {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
  );
  if (!r.ok) {
    let detail;
    try {
      detail = (await r.json()).detail;
    } catch {
      detail = r.statusText;
    }
    throw new Error(
      typeof detail === "string" ? detail : JSON.stringify(detail),
    );
  }
  return r.json();
}
async function action(label, fn) {
  if (state.busy) return;
  state.busy = true;
  $("content").setAttribute("aria-busy", "true");
  $("error-banner").hidden = true;
  document
    .querySelectorAll("button,select,input")
    .forEach((e) => (e.disabled = true));
  try {
    await fn();
  } catch (e) {
    $("error-banner").textContent = e.message;
    $("error-banner").hidden = false;
  } finally {
    state.busy = false;
    document
      .querySelectorAll("button,select,input")
      .forEach((e) => (e.disabled = false));
    $("content").setAttribute("aria-busy", "false");
    updatePager();
  }
}
async function refresh() {
  state.data = await api(`/api/dashboard?version=${state.version}`);
  $("clock").textContent = "As of " + date(state.data.clock);
  await render();
}
function outcomeView() {
  const e = state.data.evaluation,
    trend = e.trend.slice(-8);
  return `<div class="grid equal">${card("Repayment outcomes", `${num(e.funded.n)} approved loans with available outcomes`, donut(e.funded_outcomes))}${card(
    "Repayment over time",
    "Approved loans, grouped by origination date",
    lines(
      trend.map((t) => date(t.timestamp).replace(", 2026", "")),
      [
        {
          name: "Default rate",
          color: colors.red,
          values: trend.map((t) => t.funded.default_rate),
        },
        {
          name: "Late payment rate",
          color: colors.amber,
          values: trend.map((t) => t.funded.late_rate),
        },
      ],
      { title: "Approved loan repayment rates" },
    ),
  )}</div>
  <details class="more-details"><summary>Model performance by borrower segment</summary>
  <p class="footer-note">Precision and recall use all labeled synthetic loans, including hypothetical outcomes for declined loans. Pending loans are excluded; late payments count as non-defaults.</p>
  <div class="table-wrap"><table><thead><tr><th>SEGMENT</th><th>LOANS</th><th>PRECISION</th><th>RECALL</th></tr></thead><tbody>
  ${[{ name: "All borrowers", oracle: e.oracle }, ...e.segments].map((s) => `<tr><td>${esc(s.name)}</td><td>${s.oracle.n}</td><td>${pct(s.oracle.precision)}</td><td>${pct(s.oracle.recall)}</td></tr>`).join("")}
  </tbody></table></div></details>`;
}
async function driftView() {
  const batches = state.data.batches;
  if (!batches.length) return empty("No batches available.");
  if (!batches.some((b) => b.id === state.batch))
    state.batch = batches.at(-1).id;
  const report = await api("/api/monitoring/" + state.batch);
  const selector = `<div class="toolbar"><label>Batch <select id="batch-select">${batches
    .slice()
    .reverse()
    .map(
      (b) =>
        `<option value="${b.id}" ${b.id === state.batch ? "selected" : ""}>${date(b.created_at)} · ${b.model_version}</option>`,
    )
    .join("")}</select></label></div>`;
  if (!report)
    return selector + empty("No drift report is available for this batch.");
  return (
    selector +
    `<div class="grid equal">${card(
      "Input drift",
      "Larger PSI means a greater change in applicant profiles.",
      bars(
        report.features.map(
          (f) =>
            ({
              income: "Income",
              credit_score: "Credit",
              debt_ratio: "Debt ratio",
              loan_amount: "Amount",
              employment_years: "Tenure",
            })[f.feature],
        ),
        [
          {
            name: "Input PSI",
            color: colors.blue,
            values: report.features.map((f) => f.psi),
          },
        ],
        { title: "Input drift by feature", floor: 0.2, alert: 0.2 },
      ),
    )}${card(
      "Prediction drift",
      "Distribution of predicted default probabilities.",
      bars(
        report.scores.labels,
        [
          {
            name: "Reference",
            color: colors.grey,
            values: report.scores.reference,
          },
          {
            name: "Current",
            color: colors.blue,
            values: report.scores.current,
          },
        ],
        { percent: true, title: "Prediction drift" },
      ),
    )}</div>
  <p class="footer-note">${report.current_count} current loans · ${report.reference_count} reference loans · ${report.model_version}. PSI ≥ 0.20 is a signal to investigate, not proof the model is wrong.${report.small_sample ? " Small sample: interpret cautiously." : ""}</p>`
  );
}
async function predictionsView() {
  const query = new URLSearchParams({
    version: state.version,
    decision: state.decision,
    outcome: state.outcome,
    limit: 10,
    offset: state.offset,
  });
  const data = await api("/api/predictions?" + query);
  state.rows = data.rows;
  state.totalRows = data.total;
  const options = (items, value) =>
    items
      .map(
        ([v, label]) =>
          `<option value="${v}" ${value === v ? "selected" : ""}>${label}</option>`,
      )
      .join("");
  const batches = state.data.batches.slice(-8);
  return `<div class="prediction-chart">${card(
    "Loan decisions",
    "Approved and declined loans by origination date.",
    bars(
      batches.map((b) => date(b.created_at).replace(", 2026", "")),
      [
        {
          name: "Approved",
          color: colors.blue,
          values: batches.map((b) => b.approved),
        },
        {
          name: "Declined",
          color: colors.grey,
          values: batches.map((b) => b.declined),
        },
      ],
      { title: "Loan decisions over time" },
    ),
  )}</div>
  <div class="toolbar"><h2>Loans</h2><div class="ledger-filters"><label>Decision <select id="decision-filter">${options(
    [
      ["all", "All"],
      ["approved", "Approved"],
      ["declined", "Declined"],
      ["error", "Errors"],
    ],
    state.decision,
  )}</select></label><label>Outcome <select id="outcome-filter">${options(
    [
      ["all", "All"],
      ["pending", "Pending"],
      ["on_time", "On time"],
      ["late", "Late"],
      ["defaulted", "Defaulted"],
    ],
    state.outcome,
  )}</select></label></div></div>
  <div class="card"><div class="table-wrap"><table><thead><tr><th>LOAN</th><th>MODEL</th><th>DEFAULT RISK</th><th>DECISION</th><th>OUTCOME</th></tr></thead><tbody>${data.rows.map((r, i) => `<tr><td><button class="row-link" data-detail="${i}">${esc(r.input_id)}</button></td><td>${pill(r.model_version, "blue")}</td><td>${pct(r.score)}</td><td>${pill(r.status === "error" ? "Error" : r.decision, r.status === "error" ? "red" : r.decision === "approved" ? "green" : "blue")}</td><td>${r.status === "error" ? "—" : pill(r.outcome === "on_time" ? "On time" : r.outcome === "late" ? "Late payment" : r.outcome === "defaulted" ? "Defaulted" : "Pending", r.outcome === "defaulted" ? "red" : r.outcome === "late" ? "amber" : r.outcome === "on_time" ? "green" : "")}${r.evidence === "hypothetical" ? '<span class="hypothetical">Hypothetical</span>' : ""}</td></tr>`).join("")}</tbody></table>${!data.rows.length ? empty("No loans match these filters.") : ""}</div>
  <div class="pager"><span>${data.total ? `${state.offset + 1}–${Math.min(state.offset + 10, data.total)}` : "0"} of ${num(data.total)} · select a loan for details</span><div><button class="button" id="prev" aria-label="Previous loans">←</button><button class="button" id="next" aria-label="Next loans">→</button></div></div></div>
  <details class="more-details"><summary>Model versions</summary><div class="table-wrap"><table><thead><tr><th>VERSION</th><th>TRAINING LOANS</th><th>TEST AUC</th><th>TEST BRIER SCORE</th></tr></thead><tbody>${state.data.models
    .filter((m) => state.version === "all" || m.version === state.version)
    .map(
      (m) =>
        `<tr><td>${esc(m.version)}</td><td>${num(m.training_rows)}</td><td>${dec(m.test_auc)}</td><td>${dec(m.test_brier)}</td></tr>`,
    )
    .join("")}</tbody></table></div></details>`;
}
async function render() {
  document
    .querySelectorAll(".nav")
    .forEach((b) =>
      b.classList.toggle("active", b.dataset.view === state.view),
    );
  $("crumb").textContent = document
    .querySelector(`.nav[data-view="${state.view}"]`)
    .textContent.trim();
  $("page-title").textContent = titles[state.view][0];
  $("page-subtitle").textContent = titles[state.view][1];
  const html =
    state.view === "outcomes"
      ? outcomeView()
      : state.view === "drift"
        ? await driftView()
        : await predictionsView();
  $("content").innerHTML = html;
  updatePager();
}
function updatePager() {
  if ($("prev")) $("prev").disabled = state.busy || state.offset === 0;
  if ($("next"))
    $("next").disabled = state.busy || state.offset + 10 >= state.totalRows;
}
function showDetail(index) {
  const r = state.rows[index];
  const values = [
    ["Prediction ID", r.id],
    ["Input record", r.input_id],
    ["Batch", r.batch_id],
    ["Timestamp (UTC)", r.timestamp],
    ["Model", r.model_version],
    ["Artifact SHA-256", r.artifact_sha256],
    ["Predicted class", r.predicted_class || "Not scored"],
    ["Default probability", pct(r.score)],
    ["Decision threshold", pct(r.threshold)],
    ["Status", r.status],
    ["Error", r.error || "None"],
    ["Latency", `${dec(r.latency_ms, 3)} ms`],
    ["Joined outcome", r.outcome || "No outcome joined"],
    [
      "Outcome evidence",
      r.evidence === "hypothetical"
        ? "Hypothetical declined-loan repayment"
        : r.evidence === "funded"
          ? "Funded loan in simulation"
          : "None",
    ],
  ];
  $("detail-content").innerHTML =
    `<dl class="trace">${values.map(([k, v]) => `<dt>${k}</dt><dd>${esc(v)}</dd>`).join("")}</dl><h3>Original input snapshot</h3><pre class="trace-json">${esc(JSON.stringify(r.input, null, 2))}</pre><button class="button primary" id="replay" data-id="${r.id}">Reproduce decision</button><span id="replay-result" role="status"></span>`;
  $("details").showModal();
}
$("close-detail").onclick = () => $("details").close();
$("version").onchange = () =>
  action("Loading model view…", async () => {
    state.version = $("version").value;
    state.offset = 0;
    state.batch = null;
    await refresh();
  });
document.querySelectorAll(".nav").forEach(
  (b) =>
    (b.onclick = () =>
      action("Loading view…", async () => {
        state.view = b.dataset.view;
        await render();
        window.scrollTo(0, 0);
      })),
);
$("content").addEventListener("change", (e) =>
  action("Loading filtered records…", async () => {
    if (e.target.id === "batch-select") state.batch = e.target.value;
    if (e.target.id === "decision-filter") {
      state.decision = e.target.value;
      state.offset = 0;
    }
    if (e.target.id === "outcome-filter") {
      state.outcome = e.target.value;
      state.offset = 0;
    }
    await render();
  }),
);
$("content").addEventListener("click", (e) => {
  const detail = e.target.closest("[data-detail]");
  if (detail) {
    showDetail(Number(detail.dataset.detail));
    return;
  }
  const id = e.target.closest("button")?.id;
  if (!["prev", "next"].includes(id)) return;
  action("Loading loans…", async () => {
    state.offset += id === "next" ? 10 : -10;
    await render();
  });
});
$("details").addEventListener("click", (e) => {
  if (e.target.id === "replay")
    action("Reproducing recorded prediction…", async () => {
      const r = await api(
        `/api/predictions/${e.target.dataset.id}/reproduce`,
        {},
      );
      $("replay-result").textContent = r.reproducible
        ? "Exact score and decision reproduced."
        : r.reason || "Reproduction mismatch.";
    });
});
action("Loading loan data…", refresh);
