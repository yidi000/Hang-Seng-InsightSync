const DEFAULT_API_BASE = "http://127.0.0.1:8000";

const mockData = {
  summary: {
    lead_pool: 4,
    high_priority: 2,
    cross_border: 3,
    financing_signals: 2,
    last_updated: "2026-05-16T08:00:00Z",
  },
  marketOverview: {
    industry_breakdown: [
      { name: "Payments", count: 2 },
      { name: "Logistics", count: 1 },
      { name: "Clean Energy", count: 1 },
    ],
    region_breakdown: [
      { name: "Hong Kong", count: 2 },
      { name: "Shenzhen", count: 1 },
      { name: "Guangzhou", count: 1 },
    ],
    company_size_breakdown: [],
  },
  prospects: {
    items: [
      {
        prospect_id: "prospect:hkg-alpha-fintech",
        company_id: "hkg-alpha-fintech",
        canonical_name: "Alpha Fintech Holdings",
        display_name: "Alpha Fintech Holdings",
        region: "Hong Kong",
        industries: ["Payments"],
        segments: ["fintech", "commercial_banking"],
        priority_level: "high",
        priority_score: 86,
        opportunity_score: 78,
        risk_score: 24,
        evidence_confidence_score: 82,
        focus_tags: ["growth", "cross_border", "financing"],
        why_prioritized: ["Expansion signals", "Treasury needs", "Strong evidence linkage"],
        recommended_next_step: "Review cross-border treasury needs and prepare an RM outreach brief.",
        recommended_product_themes: ["Cash Management", "Cross-border RMB", "FX Services"],
        score_breakdown: {
          scorecard_version: "mock-front-end-v0",
          calibration_status: "sample_only",
          linkage_quality: {
            direct_evidence_ratio: 0.7,
            scoreable_evidence_ratio: 0.62,
            context_only_count: 1,
          },
          governance_flags: [],
          opportunity_components: [
            { name: "Expansion", points: 18, detail: "Recent expansion evidence." },
          ],
          risk_components: [
            { name: "Regulatory", points: 8, detail: "Licensing requires review." },
          ],
        },
        workflow_state: {
          owner: "Unassigned",
          stage: "new",
          status: "open",
          review_status: "not_reviewed",
          next_action: "Prepare evidence-backed outreach.",
          notes: null,
        },
      },
      {
        prospect_id: "prospect:sz-green-mobility",
        company_id: "sz-green-mobility",
        canonical_name: "Shenzhen Green Mobility",
        display_name: "Shenzhen Green Mobility",
        region: "Shenzhen",
        industries: ["Clean Energy"],
        segments: ["gba"],
        priority_level: "high",
        priority_score: 83,
        opportunity_score: 75,
        risk_score: 28,
        evidence_confidence_score: 74,
        focus_tags: ["cross_border", "policy"],
        why_prioritized: ["GBA policy tailwind", "Expansion into Hong Kong"],
        recommended_next_step: "Validate Hong Kong expansion timeline and financing need.",
        recommended_product_themes: ["Green Finance", "Trade Finance"],
        workflow_state: {
          owner: "Unassigned",
          stage: "new",
          status: "open",
          review_status: "not_reviewed",
          next_action: "Validate expansion evidence.",
          notes: null,
        },
      },
      {
        prospect_id: "prospect:gz-healthcare-supply",
        company_id: "gz-healthcare-supply",
        canonical_name: "Guangzhou Healthcare Supply",
        display_name: "Guangzhou Healthcare Supply",
        region: "Guangzhou",
        industries: ["Healthcare"],
        segments: ["commercial_banking"],
        priority_level: "medium",
        priority_score: 72,
        opportunity_score: 69,
        risk_score: 35,
        evidence_confidence_score: 66,
        focus_tags: ["financing", "market"],
        why_prioritized: ["Working capital signal", "Supply-chain activity"],
        recommended_next_step: "Check working capital requirement and supplier-payment cycle.",
        recommended_product_themes: ["Working Capital", "Supplier Payments"],
        workflow_state: {
          owner: "Unassigned",
          stage: "new",
          status: "open",
          review_status: "not_reviewed",
          next_action: "Review financing evidence.",
          notes: null,
        },
      },
      {
        prospect_id: "prospect:hk-logistics-orion",
        company_id: "hk-logistics-orion",
        canonical_name: "Orion Logistics",
        display_name: "Orion Logistics",
        region: "Hong Kong",
        industries: ["Logistics"],
        segments: ["trade"],
        priority_level: "monitor",
        priority_score: 61,
        opportunity_score: 58,
        risk_score: 42,
        evidence_confidence_score: 59,
        focus_tags: ["cross_border", "risk"],
        why_prioritized: ["Trade route changes", "Risk evidence needs review"],
        recommended_next_step: "Monitor route changes and inspect risk evidence before outreach.",
        recommended_product_themes: ["Trade Finance", "FX Services"],
        workflow_state: {
          owner: "Unassigned",
          stage: "monitoring",
          status: "open",
          review_status: "not_reviewed",
          next_action: "Monitor new signals.",
          notes: null,
        },
      },
    ],
    total: 4,
    limit: 100,
    offset: 0,
  },
  signals: {
    items: [
      {
        id: 1,
        signal_id: 1,
        company_id: "hkg-alpha-fintech",
        prospect_id: "prospect:hkg-alpha-fintech",
        signal_type: "cross_border",
        source: "sample",
        title: "Alpha Fintech expands settlement corridor",
        event_time: "2026-05-10T09:00:00Z",
        signal_text: "Expansion suggests cross-border treasury and FX needs.",
        signal_level: "high",
        evidence_refs: ["sample-evidence-1"],
      },
      {
        id: 2,
        signal_id: 2,
        company_id: "sz-green-mobility",
        prospect_id: "prospect:sz-green-mobility",
        signal_type: "policy",
        source: "sample",
        title: "GBA green finance incentives noted",
        event_time: "2026-05-08T09:00:00Z",
        signal_text: "Policy context supports green financing conversation.",
        signal_level: "medium",
        evidence_refs: ["sample-evidence-2"],
      },
      {
        id: 3,
        signal_id: 3,
        company_id: "gz-healthcare-supply",
        prospect_id: "prospect:gz-healthcare-supply",
        signal_type: "financing",
        source: "sample",
        title: "Healthcare supplier shows working-capital pressure",
        event_time: "2026-05-04T09:00:00Z",
        signal_text: "Supply-chain terms may create working-capital needs.",
        signal_level: "medium",
        evidence_refs: ["sample-evidence-3"],
      },
    ],
    total: 3,
    limit: 100,
    offset: 0,
  },
  filters: {
    regions: [{ value: "Hong Kong", count: 2 }, { value: "Shenzhen", count: 1 }],
    industries: [{ value: "Payments", count: 2 }, { value: "Logistics", count: 1 }],
    segments: [],
    signal_types: [{ value: "cross_border", count: 1 }, { value: "financing", count: 1 }],
    sources: [{ value: "sample", count: 3 }],
    datasets: [],
  },
};

mockData.companies = {
  items: mockData.prospects.items.map((item) => ({
    source: "sample",
    company_id: item.company_id,
    canonical_name: item.canonical_name,
    display_name: item.display_name,
    country: item.region === "Hong Kong" ? "Hong Kong SAR" : "China",
    region: item.region,
    city: item.region,
    segments: item.segments || [],
    industries: item.industries || [],
    profile_summary: item.recommended_next_step,
    description: item.why_prioritized?.join(" "),
    signal_count: item.focus_tags?.length || 0,
    timeline_event_count: item.why_prioritized?.length || 0,
    generated_insight_count: 0,
    activity_at: "2026-05-16T08:00:00Z",
    updated_at: "2026-05-16T08:00:00Z",
  })),
  total: mockData.prospects.items.length,
  limit: 100,
  offset: 0,
};

const state = {
  apiBase: localStorage.getItem("INSIGHTSYNC_API_BASE") || DEFAULT_API_BASE,
  apiKey: localStorage.getItem("INSIGHTSYNC_API_KEY") || "",
  route: routeFromHash().route,
  selectedProspectId: routeFromHash().id,
  activeDetailTab: "brief",
  loading: true,
  backendOnline: false,
  backendError: null,
  data: {
    summary: null,
    marketOverview: null,
    prospects: null,
    signals: null,
    companies: null,
    priorityProspects: null,
    triggerSignals: null,
    filters: null,
  },
  detailCache: {},
  search: "",
  industryFilter: "all",
  regionFilter: "all",
  signalTypeFilter: "all",
  chat: [],
  sampleToastShown: false,
};

const $ = (selector) => document.querySelector(selector);
const content = $("#content");

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "\"": "&quot;",
    "'": "&#039;",
  })[char]);
}

function routeFromHash() {
  const raw = (window.location.hash || "#overview").replace(/^#/, "");
  if (raw.startsWith("prospect/")) {
    return { route: "detail", id: decodeURIComponent(raw.slice("prospect/".length)) };
  }
  return { route: raw || "overview", id: null };
}

function setHash(route, id) {
  window.location.hash = id ? `prospect/${encodeURIComponent(id)}` : route;
}

function cleanBase(url) {
  return String(url || DEFAULT_API_BASE).replace(/\/$/, "");
}

function headers(extra = {}) {
  const output = { ...extra };
  if (state.apiKey) output["X-API-Key"] = state.apiKey;
  return output;
}

async function apiFetch(path, options = {}) {
  const response = await fetch(`${cleanBase(state.apiBase)}${path}`, {
    ...options,
    headers: headers(options.headers || {}),
  });
  if (!response.ok) {
    const detail = await response.text().catch(() => "");
    throw new Error(`${path} returned ${response.status}${detail ? `: ${detail.slice(0, 120)}` : ""}`);
  }
  return response.json();
}

async function safeGet(path) {
  try {
    return await apiFetch(path);
  } catch (error) {
    return null;
  }
}

function showToast(message) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.remove("hidden");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => toast.classList.add("hidden"), 3600);
}

function setBackendStatus(online, detail) {
  state.backendOnline = online;
  const dot = $("#sidebar-status-dot");
  dot.classList.toggle("online", online);
  dot.classList.toggle("offline", !online);
  $("#sidebar-status").textContent = online ? "Backend online" : "Sample data mode";
  $("#sidebar-status-detail").textContent = detail || (online ? cleanBase(state.apiBase) : "FastAPI unavailable");
}

async function loadData() {
  state.loading = true;
  render();

  const health = await safeGet("/healthz");
  const [
    summary,
    marketOverview,
    priorityProspects,
    triggerSignals,
    prospects,
    companies,
    signals,
    filters,
  ] = await Promise.all([
    safeGet("/api/dashboard/summary"),
    safeGet("/api/dashboard/market-overview"),
    safeGet("/api/dashboard/priority-prospects"),
    safeGet("/api/dashboard/trigger-signals"),
    safeGet("/api/prospects?limit=100"),
    safeGet("/api/companies?limit=100"),
    safeGet("/api/signals?limit=100"),
    safeGet("/api/metadata/filters"),
  ]);

  const online = Boolean(health && prospects && prospects.items);
  state.data.summary = summary || mockData.summary;
  state.data.marketOverview = marketOverview || mockData.marketOverview;
  state.data.priorityProspects = priorityProspects || { items: mockData.prospects.items.slice(0, 3) };
  state.data.triggerSignals = triggerSignals || { items: mockData.signals.items.slice(0, 3) };
  state.data.prospects = prospects || mockData.prospects;
  state.data.companies = companies || mockData.companies;
  state.data.signals = signals || mockData.signals;
  state.data.filters = filters || mockData.filters;
  state.backendError = online ? null : "Backend is unavailable or not initialized.";
  state.sampleToastShown = false;
  state.loading = false;
  setBackendStatus(online, online ? cleanBase(state.apiBase) : "Using bundled sample data");
  render();
}

function prospectName(item) {
  const p = item.prospect || item;
  return p.display_name || p.canonical_name || p.company_id || p.prospect_id || "Unknown company";
}

function prospectId(item) {
  const p = item.prospect || item;
  return p.prospect_id;
}

function companyId(item) {
  const p = item.prospect || item;
  return p.company_id || "";
}

function asList(payload) {
  return payload?.items || [];
}

function priorityClass(value) {
  const normalized = String(value || "").toLowerCase();
  if (normalized === "high") return "high";
  if (normalized === "medium") return "medium";
  return "monitor";
}

function badge(value, extra = "") {
  return `<span class="badge ${escapeHtml(priorityClass(value))} ${extra}">${escapeHtml(value || "monitor")}</span>`;
}

function formatDate(value) {
  if (!value) return "No date";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value).slice(0, 10);
  return date.toLocaleDateString("en-HK", { year: "numeric", month: "short", day: "numeric" });
}

function formatTags(tags = [], limit = 4) {
  if (!tags.length) return `<span class="muted">No tags</span>`;
  return `<span class="wrap">${tags.slice(0, limit).map((tag) => `<span class="badge">${escapeHtml(tag)}</span>`).join("")}</span>`;
}

function getFilteredProspects() {
  const q = state.search.trim().toLowerCase();
  return asList(state.data.prospects)
    .filter((item) => {
      const name = prospectName(item).toLowerCase();
      const industries = (item.industries || []).join(" ").toLowerCase();
      const region = String(item.region || "").toLowerCase();
      const tags = (item.focus_tags || []).join(" ").toLowerCase();
      if (q && !`${name} ${industries} ${region} ${tags}`.includes(q)) return false;
      if (state.industryFilter !== "all" && !(item.industries || []).includes(state.industryFilter)) return false;
      if (state.regionFilter !== "all" && item.region !== state.regionFilter) return false;
      return true;
    })
    .sort((a, b) => (b.priority_score || 0) - (a.priority_score || 0));
}

function getFilteredSignals() {
  const q = state.search.trim().toLowerCase();
  return asList(state.data.signals)
    .filter((item) => {
      const text = [
        item.title,
        item.signal_text,
        item.value_text,
        item.company_id,
        item.entity,
        item.source,
        item.signal_type,
      ].join(" ").toLowerCase();
      if (q && !text.includes(q)) return false;
      if (state.signalTypeFilter !== "all" && item.signal_type !== state.signalTypeFilter) return false;
      return true;
    })
    .sort((a, b) => new Date(b.event_time || 0) - new Date(a.event_time || 0));
}

function metricCard(label, value, detail, accent = false) {
  return `
    <div class="metric-card ${accent ? "accent" : ""}">
      <div class="metric-label"><span>${escapeHtml(label)}</span></div>
      <div class="metric-value">${escapeHtml(value ?? 0)}</div>
      <small>${escapeHtml(detail || "")}</small>
    </div>
  `;
}

function bars(items = []) {
  const max = Math.max(1, ...items.map((item) => item.count || item.value || 0));
  if (!items.length) return `<div class="empty-state">No distribution data available yet.</div>`;
  return items.map((item) => {
    const count = item.count ?? item.value ?? 0;
    const width = Math.max(3, Math.round((count / max) * 100));
    return `
      <div class="bar-row">
        <span>${escapeHtml(item.name || item.value || "Unknown")}</span>
        <span class="bar-track"><span class="bar-fill" style="width:${width}%"></span></span>
        <strong>${escapeHtml(count)}</strong>
      </div>
    `;
  }).join("");
}

function renderOverview() {
  const summary = state.data.summary || mockData.summary;
  const market = state.data.marketOverview || mockData.marketOverview;
  const topProspects = asList(state.data.priorityProspects).length
    ? asList(state.data.priorityProspects)
    : getFilteredProspects().slice(0, 5);
  const triggerSignals = asList(state.data.triggerSignals).length
    ? asList(state.data.triggerSignals)
    : asList(state.data.signals).slice(0, 5);

  return `
    ${renderModeBanner()}
    <div class="grid metrics">
      ${metricCard("Lead pool", summary.lead_pool, "Current prospect universe")}
      ${metricCard("High priority", summary.high_priority, "Prospects requiring review", true)}
      ${metricCard("Cross-border", summary.cross_border, "Signals and focus tags")}
      ${metricCard("Financing signals", summary.financing_signals, "Liquidity and funding themes")}
    </div>

    <section class="brief-panel mt">
      <div>
        <span class="badge high">Morning Brief</span>
        <h2>${escapeHtml(topProspects.length)} client relationships need RM review</h2>
        <p>
          Portfolio activity is led by cross-border and financing signals. Start with
          high-priority relationships, then open supporting evidence before outreach.
        </p>
        <div class="wrap">
          <button class="button primary" data-route="prospects">Review RM Actions</button>
          <button class="button" data-route="signals">Open Evidence</button>
          <button class="button" data-route="copilot">Ask Copilot</button>
        </div>
      </div>
      <button class="focus-score" data-route="prospects">
        <span>Focus score</span>
        <strong>${escapeHtml(Math.round((topProspects.slice(0, 5).reduce((sum, item) => sum + (item.priority_score || 0), 0) || 0) / Math.max(1, topProspects.slice(0, 5).length)))}</strong>
        <small>${escapeHtml(summary.high_priority || 0)} priority clients</small>
      </button>
    </section>

    <div class="grid two mt">
      <section class="panel">
        <div class="panel-header">
          <div>
            <h2 class="panel-title">Priority Prospects</h2>
            <p class="panel-subtitle">Companies with the clearest evidence-backed conversation path.</p>
          </div>
          <button class="button small" data-route="prospects">View all</button>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Company</th>
                <th>Priority</th>
                <th>Evidence</th>
                <th>Recommended next step</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              ${topProspects.map((item) => `
                <tr>
                  <td>
                    <div class="company-name">${escapeHtml(prospectName(item))}</div>
                    <div class="muted">${escapeHtml(companyId(item))}</div>
                  </td>
                  <td>
                    ${badge(item.priority_level)}
                    <div class="muted">Score ${escapeHtml(item.priority_score ?? "N/A")}</div>
                  </td>
                  <td>${formatTags(item.focus_tags || [], 3)}</td>
                  <td>${escapeHtml(item.recommended_next_step || "Review linked evidence.")}</td>
                  <td><button class="button small primary" data-open-prospect="${escapeHtml(prospectId(item))}">Open</button></td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </div>
      </section>

      <section class="panel">
        <div class="panel-header">
          <div>
            <h2 class="panel-title">Market Overview</h2>
            <p class="panel-subtitle">Industry and region distribution from current data.</p>
          </div>
        </div>
        <div class="panel-body">
          <h3 class="panel-title">By industry</h3>
          ${bars(market.industry_breakdown)}
          <h3 class="panel-title mt">By region</h3>
          ${bars(market.region_breakdown)}
        </div>
      </section>
    </div>

    <section class="panel mt">
      <div class="panel-header">
        <div>
          <h2 class="panel-title">Recent Trigger Signals</h2>
          <p class="panel-subtitle">Signals link market changes to companies and prospect actions.</p>
        </div>
        <button class="button small" data-route="signals">Open signal explorer</button>
      </div>
      <div class="panel-body list">
        ${triggerSignals.map(renderSignalCard).join("") || `<div class="empty-state">No signals available.</div>`}
      </div>
    </section>
  `;
}

function optionList(values, selected) {
  return [`<option value="all">All</option>`].concat(
    values.map((value) => `<option value="${escapeHtml(value)}" ${value === selected ? "selected" : ""}>${escapeHtml(value)}</option>`)
  ).join("");
}

function unique(values) {
  return Array.from(new Set(values.filter(Boolean))).sort();
}

function renderProspects() {
  const items = getFilteredProspects();
  const allProspects = asList(state.data.prospects);
  const industries = unique(allProspects.flatMap((p) => p.industries || []));
  const regions = unique(allProspects.map((p) => p.region));

  return `
    ${renderModeBanner()}
    <div class="toolbar">
      <input id="prospect-search" value="${escapeHtml(state.search)}" placeholder="Search company, region, industry, or tag" />
      <select id="industry-filter">${optionList(industries, state.industryFilter)}</select>
      <select id="region-filter">${optionList(regions, state.regionFilter)}</select>
      <button class="button" id="clear-filters">Clear</button>
      <span class="muted">${items.length} of ${allProspects.length} prospects</span>
    </div>

    <section class="panel">
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Company</th>
              <th>Score</th>
              <th>Fit</th>
              <th>Why prioritized</th>
              <th>Workflow</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            ${items.map((item) => {
              const workflow = item.workflow_state || {};
              return `
                <tr>
                  <td>
                    <div class="company-name">${escapeHtml(prospectName(item))}</div>
                    <div class="muted">${escapeHtml([item.region, (item.industries || [])[0]].filter(Boolean).join(" / "))}</div>
                  </td>
                  <td>
                    ${badge(item.priority_level)}
                    <div class="muted">Priority ${escapeHtml(item.priority_score ?? "N/A")}</div>
                    <div class="muted">Opportunity ${escapeHtml(item.opportunity_score ?? "N/A")} / Risk ${escapeHtml(item.risk_score ?? "N/A")}</div>
                  </td>
                  <td>${formatTags(item.recommended_product_themes || item.focus_tags || [], 4)}</td>
                  <td>${(item.why_prioritized || []).slice(0, 3).map((reason) => `<div>${escapeHtml(reason)}</div>`).join("") || escapeHtml(item.recommended_next_step || "")}</td>
                  <td>
                    <div>${escapeHtml(workflow.stage || "new")}</div>
                    <div class="muted">${escapeHtml(workflow.owner || "Unassigned")}</div>
                  </td>
                  <td><button class="button small primary" data-open-prospect="${escapeHtml(prospectId(item))}">Open brief</button></td>
                </tr>
              `;
            }).join("") || `<tr><td colspan="6"><div class="empty-state">No prospects match the current filters.</div></td></tr>`}
          </tbody>
        </table>
      </div>
    </section>
  `;
}

function getFilteredCompanies() {
  const q = state.search.trim().toLowerCase();
  return asList(state.data.companies)
    .filter((item) => {
      const text = [
        item.display_name,
        item.canonical_name,
        item.company_id,
        item.region,
        item.city,
        ...(item.industries || []),
        ...(item.segments || []),
        item.profile_summary,
        item.description,
      ].join(" ").toLowerCase();
      if (q && !text.includes(q)) return false;
      if (state.industryFilter !== "all" && !(item.industries || []).includes(state.industryFilter)) return false;
      if (state.regionFilter !== "all" && item.region !== state.regionFilter) return false;
      return true;
    })
    .sort((a, b) => new Date(b.activity_at || b.updated_at || 0) - new Date(a.activity_at || a.updated_at || 0));
}

function renderCompanies() {
  const items = getFilteredCompanies();
  const allCompanies = asList(state.data.companies);
  const industries = unique(allCompanies.flatMap((company) => company.industries || []));
  const regions = unique(allCompanies.map((company) => company.region));
  const prospectByCompany = new Map(asList(state.data.prospects).map((p) => [p.company_id, p]));

  return `
    ${renderModeBanner()}
    <div class="toolbar">
      <input id="company-search" value="${escapeHtml(state.search)}" placeholder="Search company, source, region, industry, or profile text" />
      <select id="industry-filter">${optionList(industries, state.industryFilter)}</select>
      <select id="region-filter">${optionList(regions, state.regionFilter)}</select>
      <button class="button" id="clear-filters">Clear</button>
      <span class="muted">${items.length} of ${allCompanies.length} companies</span>
    </div>

    <section class="panel">
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Company</th>
              <th>Profile</th>
              <th>Activity</th>
              <th>Segments</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            ${items.map((item) => {
              const linkedProspect = prospectByCompany.get(item.company_id);
              return `
                <tr>
                  <td>
                    <div class="company-name">${escapeHtml(item.display_name || item.canonical_name || item.company_id)}</div>
                    <div class="muted">${escapeHtml([item.company_id, item.region, item.city].filter(Boolean).join(" / "))}</div>
                  </td>
                  <td>
                    <div>${escapeHtml(item.profile_summary || item.description || "No profile summary yet.")}</div>
                    <div class="muted">${formatTags(item.industries || [], 3)}</div>
                  </td>
                  <td>
                    <div>${escapeHtml(item.signal_count || 0)} signals</div>
                    <div class="muted">${escapeHtml(item.timeline_event_count || 0)} timeline events</div>
                    <div class="muted">Updated ${escapeHtml(formatDate(item.activity_at || item.updated_at))}</div>
                  </td>
                  <td>${formatTags(item.segments || [], 4)}</td>
                  <td>
                    ${linkedProspect ? `<button class="button small primary" data-open-prospect="${escapeHtml(prospectId(linkedProspect))}">Open prospect</button>` : `<span class="muted">No prospect view</span>`}
                  </td>
                </tr>
              `;
            }).join("") || `<tr><td colspan="5"><div class="empty-state">No companies match the current filters.</div></td></tr>`}
          </tbody>
        </table>
      </div>
    </section>
  `;
}

function signalTitle(item) {
  return item.title || item.signal_text || item.value_text || item.signal_key || "Untitled signal";
}

function signalCompany(item) {
  return item.company_id || item.entity || "Market signal";
}

function renderSignalCard(item) {
  return `
    <article class="list-card">
      <div class="wrap">
        <span class="badge ${item.signal_level === "high" ? "risk" : ""}">${escapeHtml(item.signal_type || "signal")}</span>
        <span class="badge">${escapeHtml(item.source || "InsightSync")}</span>
        <span class="badge">${escapeHtml(formatDate(item.event_time))}</span>
      </div>
      <h3>${escapeHtml(signalTitle(item))}</h3>
      <p>${escapeHtml(item.signal_text || item.value_text || item.detail || "")}</p>
      <p><strong>${escapeHtml(signalCompany(item))}</strong></p>
      <div class="wrap mt">
        ${item.prospect_id ? `<button class="button small primary" data-open-prospect="${escapeHtml(item.prospect_id)}">Open linked prospect</button>` : ""}
        <button class="button small" data-ask-signal="${escapeHtml(signalTitle(item))}">Ask Copilot</button>
      </div>
    </article>
  `;
}

function renderSignals() {
  const items = getFilteredSignals();
  const allSignals = asList(state.data.signals);
  const types = unique(allSignals.map((signal) => signal.signal_type));
  return `
    ${renderModeBanner()}
    <div class="toolbar">
      <input id="signal-search" value="${escapeHtml(state.search)}" placeholder="Search title, company, source, or signal text" />
      <select id="signal-type-filter">${optionList(types, state.signalTypeFilter)}</select>
      <button class="button" id="clear-filters">Clear</button>
      <span class="muted">${items.length} of ${allSignals.length} signals</span>
    </div>
    <section class="panel">
      <div class="panel-body list">
        ${items.map(renderSignalCard).join("") || `<div class="empty-state">No signals match the current filters.</div>`}
      </div>
    </section>
  `;
}

async function openProspect(id) {
  state.selectedProspectId = id;
  state.route = "detail";
  setHash("detail", id);
  render();
  if (!state.detailCache[id]) {
    await loadProspectDetail(id);
  }
  render();
}

async function loadProspectDetail(id) {
  const encoded = encodeURIComponent(id);
  const [detail, evidence, brief, review, workflow] = await Promise.all([
    safeGet(`/api/prospects/${encoded}`),
    safeGet(`/api/prospects/${encoded}/evidence`),
    safeGet(`/api/prospects/${encoded}/brief`),
    safeGet(`/api/prospects/${encoded}/review`),
    safeGet(`/api/prospects/${encoded}/workflow`),
  ]);
  const summary = asList(state.data.prospects).find((item) => prospectId(item) === id);
  state.detailCache[id] = {
    detail: detail || (summary ? { prospect: summary, workflow_state: summary.workflow_state } : null),
    evidence,
    brief,
    review,
    workflow: workflow || summary?.workflow_state || null,
  };
}

function scoreComponentRows(components = []) {
  if (!components.length) return `<div class="empty-state">No score components returned yet.</div>`;
  return components.map((item) => `
    <div class="list-card">
      <div class="wrap">
        <span class="badge">${escapeHtml(item.category || "component")}</span>
        <span class="badge">${escapeHtml(item.points ?? 0)} points</span>
      </div>
      <h3>${escapeHtml(item.name || "Score component")}</h3>
      <p>${escapeHtml(item.detail || "")}</p>
    </div>
  `).join("");
}

function renderDetail() {
  const id = state.selectedProspectId;
  const cached = state.detailCache[id];
  if (!cached) {
    loadProspectDetail(id).then(render);
    return `<div class="loading-card">Loading prospect detail for ${escapeHtml(id)}...</div>`;
  }

  const detail = cached.detail || {};
  const p = detail.prospect || asList(state.data.prospects).find((item) => prospectId(item) === id) || {};
  const brief = cached.brief || {};
  const evidence = cached.evidence || {};
  const review = cached.review || {};
  const workflow = cached.workflow || detail.workflow_state || p.workflow_state || {};
  const score = p.score_breakdown || {};
  const linkage = score.linkage_quality || {};

  return `
    ${renderModeBanner()}
    <button class="button ghost" data-route="prospects">Back to prospects</button>
    <section class="detail-hero mt">
      <div>
        <div class="wrap">
          ${badge(p.priority_level)}
          <span class="badge">Evidence ${escapeHtml(p.evidence_confidence_score ?? "N/A")}</span>
          <span class="badge">Scorecard ${escapeHtml(score.scorecard_version || "N/A")}</span>
        </div>
        <h2>${escapeHtml(prospectName(p))}</h2>
        <p class="muted">${escapeHtml([p.region, (p.industries || [])[0], p.company_id].filter(Boolean).join(" / "))}</p>
        <p>${escapeHtml(brief.summary || p.recommended_next_step || "Review linked evidence and prepare outreach.")}</p>
        <div class="wrap">${formatTags(p.recommended_product_themes || p.focus_tags || [], 6)}</div>
      </div>
      <div class="score-grid">
        <div class="score-box"><span class="muted">Priority</span><strong>${escapeHtml(p.priority_score ?? "N/A")}</strong></div>
        <div class="score-box"><span class="muted">Opportunity</span><strong>${escapeHtml(p.opportunity_score ?? "N/A")}</strong></div>
        <div class="score-box"><span class="muted">Risk</span><strong>${escapeHtml(p.risk_score ?? "N/A")}</strong></div>
      </div>
    </section>

    <div class="tabs">
      ${["brief", "evidence", "score", "review", "workflow"].map((tab) => `
        <button class="tab ${state.activeDetailTab === tab ? "active" : ""}" data-detail-tab="${tab}">${escapeHtml(tab)}</button>
      `).join("")}
    </div>

    <div class="mt">
      ${state.activeDetailTab === "brief" ? renderBriefTab(p, brief, detail) : ""}
      ${state.activeDetailTab === "evidence" ? renderEvidenceTab(evidence, detail) : ""}
      ${state.activeDetailTab === "score" ? renderScoreTab(score, linkage) : ""}
      ${state.activeDetailTab === "review" ? renderReviewTab(review) : ""}
      ${state.activeDetailTab === "workflow" ? renderWorkflowTab(id, workflow) : ""}
    </div>
  `;
}

function renderBriefTab(p, brief, detail) {
  const signals = detail.recent_signals || [];
  return `
    <div class="grid two">
      <section class="panel">
        <div class="panel-header">
          <div>
            <h2 class="panel-title">${escapeHtml(brief.title || "RM action brief")}</h2>
          <p class="panel-subtitle">Prepared for relationship managers before outreach.</p>
          </div>
          <button class="button small primary" data-copilot-prospect="${escapeHtml(prospectId(p))}">Ask about this prospect</button>
        </div>
        <div class="panel-body stack">
          <div class="list-card">
            <h3>Recommended next step</h3>
            <p>${escapeHtml(brief.recommended_next_step || p.recommended_next_step || "Review linked evidence.")}</p>
          </div>
          <div class="list-card">
            <h3>Top opportunities</h3>
            <p>${escapeHtml((brief.top_opportunities || p.recommended_product_themes || []).join("; ") || "No opportunity summary returned yet.")}</p>
          </div>
          <div class="list-card">
            <h3>Top risks</h3>
            <p>${escapeHtml((brief.top_risks || []).join("; ") || "No risk summary returned yet.")}</p>
          </div>
        </div>
      </section>
      <section class="panel">
        <div class="panel-header">
          <div>
            <h2 class="panel-title">Recent linked signals</h2>
            <p class="panel-subtitle">Company-linked evidence surfaced for the RM.</p>
          </div>
        </div>
        <div class="panel-body list">
          ${signals.slice(0, 6).map(renderSignalCard).join("") || `<div class="empty-state">No linked signals returned yet.</div>`}
        </div>
      </section>
    </div>
  `;
}

function renderEvidenceTab(evidence, detail) {
  const documents = evidence.recent_documents || detail.recent_documents || [];
  const metrics = evidence.key_metrics || detail.key_metrics || [];
  const risks = evidence.key_risk_factors || detail.key_risk_factors || [];
  const events = evidence.key_business_events || detail.key_business_events || [];
  return `
    <div class="grid two">
      <section class="panel">
        <div class="panel-header">
          <div>
            <h2 class="panel-title">Parsed documents</h2>
          <p class="panel-subtitle">Report evidence, extracted metrics, risks, events, and model audit trail.</p>
          </div>
        </div>
        <div class="panel-body list">
          ${documents.map((doc) => `
            <article class="list-card">
              <div class="wrap">
                <span class="badge">${escapeHtml(doc.parse_status || "parsed")}</span>
                <span class="badge">${escapeHtml(doc.lang || "unknown language")}</span>
                <span class="badge">${escapeHtml(doc.source || "source")}</span>
              </div>
              <h3>${escapeHtml(doc.title || "Parsed document")}</h3>
              <p>${escapeHtml(doc.summary || doc.management_discussion_summary || "")}</p>
              <p class="muted">Metrics ${escapeHtml(doc.metric_count || 0)} / Risks ${escapeHtml(doc.risk_factor_count || 0)} / Events ${escapeHtml(doc.business_event_count || 0)}</p>
              ${doc.genai_extraction ? `<p class="muted">GenAI extraction: ${escapeHtml(doc.genai_extraction.status)} / accepted ${escapeHtml(doc.genai_extraction.accepted_count || 0)} / rejected ${escapeHtml(doc.genai_extraction.rejected_count || 0)}</p>` : ""}
            </article>
          `).join("") || `<div class="empty-state">No parsed documents returned yet.</div>`}
        </div>
      </section>
      <section class="stack">
        <section class="panel">
          <div class="panel-header"><h2 class="panel-title">Metrics</h2></div>
          <div class="panel-body list">
            ${metrics.map((item) => `<div class="list-card"><h3>${escapeHtml(item.name)}</h3><p>${escapeHtml([item.value, item.unit, item.period].filter(Boolean).join(" "))}</p><p class="muted">${escapeHtml(item.context || "")}</p></div>`).join("") || `<div class="empty-state">No structured metrics.</div>`}
          </div>
        </section>
        <section class="panel">
          <div class="panel-header"><h2 class="panel-title">Risks and events</h2></div>
          <div class="panel-body list">
            ${risks.map((item) => `<div class="list-card"><span class="badge risk">${escapeHtml(item.severity)}</span><h3>${escapeHtml(item.category)}</h3><p>${escapeHtml(item.description)}</p></div>`).join("")}
            ${events.map((item) => `<div class="list-card"><span class="badge">${escapeHtml(item.event_type)}</span><h3>${escapeHtml(item.title || item.event_type)}</h3><p>${escapeHtml(item.summary)}</p></div>`).join("")}
            ${!risks.length && !events.length ? `<div class="empty-state">No structured risks or events.</div>` : ""}
          </div>
        </section>
      </section>
    </div>
  `;
}

function renderScoreTab(score, linkage) {
  return `
    <div class="grid two">
      <section class="panel">
        <div class="panel-header">
          <div>
            <h2 class="panel-title">Score audit</h2>
          <p class="panel-subtitle">${escapeHtml(score.scoring_method || "Transparent scorecard with evidence-quality checks")}</p>
          </div>
          <span class="badge">${escapeHtml(score.calibration_status || "calibration pending")}</span>
        </div>
        <div class="panel-body stack">
          <div class="list-card">
            <h3>Formula</h3>
            <p>${escapeHtml(score.priority_formula || "Backend formula not returned.")}</p>
          </div>
          <div class="grid three">
            <div class="score-box"><span class="muted">Direct evidence ratio</span><strong>${escapeHtml(linkage.direct_evidence_ratio ?? "N/A")}</strong></div>
            <div class="score-box"><span class="muted">Scoreable ratio</span><strong>${escapeHtml(linkage.scoreable_evidence_ratio ?? "N/A")}</strong></div>
            <div class="score-box"><span class="muted">Context-only</span><strong>${escapeHtml(linkage.context_only_count ?? linkage.context_only_evidence_count ?? "N/A")}</strong></div>
          </div>
          <h3 class="panel-title">Opportunity components</h3>
          ${scoreComponentRows(score.opportunity_components)}
          <h3 class="panel-title">Risk components</h3>
          ${scoreComponentRows(score.risk_components)}
        </div>
      </section>
      <section class="panel">
        <div class="panel-header">
          <div>
            <h2 class="panel-title">Governance flags</h2>
            <p class="panel-subtitle">Caution indicators for weak evidence or scoring risk.</p>
          </div>
        </div>
        <div class="panel-body list">
          ${(score.governance_flags || []).map((flag) => `
            <div class="list-card">
              <span class="badge risk">${escapeHtml(flag.severity)}</span>
              <h3>${escapeHtml(flag.area || flag.flag_key)}</h3>
              <p>${escapeHtml(flag.message || flag.suggested_action || "")}</p>
            </div>
          `).join("") || `<div class="empty-state">No governance flags returned.</div>`}
        </div>
      </section>
    </div>
  `;
}

function renderReviewTab(review) {
  return `
    <section class="panel">
      <div class="panel-header">
        <div>
          <h2 class="panel-title">LLM review</h2>
          <p class="panel-subtitle">Quality review for linkage strength, evidence gaps, and decision risk.</p>
        </div>
        <span class="badge">${escapeHtml(review.status || "not loaded")}</span>
      </div>
      <div class="panel-body stack">
        <div class="list-card">
          <h3>Summary</h3>
          <p>${escapeHtml(review.review_summary || "No LLM review returned yet.")}</p>
          <p class="muted">${escapeHtml(review.model_name || "")}</p>
        </div>
        <div class="grid two">
          <div class="list">
            <h3 class="panel-title">Audit findings</h3>
            ${(review.audit_findings || []).map((item) => `<div class="list-card"><span class="badge risk">${escapeHtml(item.severity)}</span><h3>${escapeHtml(item.area)}</h3><p>${escapeHtml(item.issue || item.reason)}</p><p class="muted">${escapeHtml(item.suggested_action || "")}</p></div>`).join("") || `<div class="empty-state">No audit findings.</div>`}
          </div>
          <div class="list">
            <h3 class="panel-title">Extraction opportunities</h3>
            ${(review.extraction_opportunities || []).map((item) => `<div class="list-card"><h3>${escapeHtml(item.area)}</h3><p>${escapeHtml(item.why)}</p><p class="muted">${escapeHtml(item.suggested_output)}</p></div>`).join("") || `<div class="empty-state">No extraction opportunities.</div>`}
          </div>
        </div>
      </div>
    </section>
  `;
}

function renderWorkflowTab(id, workflow) {
  return `
    <section class="panel">
      <div class="panel-header">
        <div>
          <h2 class="panel-title">RM workflow state</h2>
          <p class="panel-subtitle">RM-owned follow-up state for the selected opportunity.</p>
        </div>
      </div>
      <div class="panel-body">
        <form class="workflow-form" id="workflow-form" data-prospect-id="${escapeHtml(id)}">
          <label>Owner <input name="owner" value="${escapeHtml(workflow.owner || "")}" placeholder="RM owner" /></label>
          <label>Stage
            <select name="stage">
              ${["new", "qualification", "discovery", "proposal", "active", "monitoring"].map((value) => `<option value="${value}" ${workflow.stage === value ? "selected" : ""}>${value}</option>`).join("")}
            </select>
          </label>
          <label>Status <input name="status" value="${escapeHtml(workflow.status || "open")}" /></label>
          <label>Review status <input name="review_status" value="${escapeHtml(workflow.review_status || "not_reviewed")}" /></label>
          <label>Last action <input name="last_action" value="${escapeHtml(workflow.last_action || "")}" /></label>
          <label>Next action <input name="next_action" value="${escapeHtml(workflow.next_action || "")}" /></label>
          <label>Notes <textarea name="notes">${escapeHtml(workflow.notes || "")}</textarea></label>
          <button class="button primary" type="submit">Save workflow</button>
        </form>
      </div>
    </section>
  `;
}

function renderCopilot() {
  const prospects = asList(state.data.prospects);
  return `
    ${renderModeBanner()}
    <div class="copilot-layout">
      <section class="panel">
        <div class="panel-header">
          <div>
            <h2 class="panel-title">Evidence-grounded Copilot</h2>
            <p class="panel-subtitle">Ask questions grounded in linked documents, signals, and citations.</p>
          </div>
        </div>
        <div class="chat-thread" id="chat-thread">
          ${state.chat.map((msg) => `<div class="message ${msg.role}">${escapeHtml(msg.content)}</div>`).join("") || `<div class="empty-state">Ask a question about prospects, signals, evidence, or RM next actions.</div>`}
        </div>
        <div class="panel-body">
          <form class="copilot-composer" id="copilot-form">
            <select id="copilot-prospect">
              <option value="">General portfolio question</option>
              ${prospects.map((p) => `<option value="${escapeHtml(prospectId(p))}" ${state.selectedProspectId === prospectId(p) ? "selected" : ""}>${escapeHtml(prospectName(p))}</option>`).join("")}
            </select>
            <textarea id="copilot-question" placeholder="Example: Why is this company high priority, and what evidence supports the next step?"></textarea>
            <button class="button primary" type="submit">Ask Copilot</button>
          </form>
        </div>
      </section>
      <aside class="panel">
        <div class="panel-header">
          <div>
            <h2 class="panel-title">Useful prompts</h2>
            <p class="panel-subtitle">Designed for the current backend API.</p>
          </div>
        </div>
        <div class="panel-body quick-prompts">
          ${[
            "Which prospects should an RM review first today?",
            "Explain the score drivers and evidence quality for the selected prospect.",
            "What cross-border opportunities are visible in the current signals?",
            "What risks should be checked before outreach?",
          ].map((prompt) => `<button class="button" data-quick-prompt="${escapeHtml(prompt)}">${escapeHtml(prompt)}</button>`).join("")}
        </div>
      </aside>
    </div>
  `;
}

function render() {
  $("#api-base-input").value = state.apiBase;
  $("#api-key-input").value = state.apiKey;
  document.querySelectorAll(".nav-item").forEach((item) => {
    item.classList.toggle("active", item.dataset.route === (state.route === "detail" ? "prospects" : state.route));
  });

  if (state.loading) {
    content.innerHTML = `<div class="loading-card">Loading InsightSync data...</div>`;
    return;
  }

  const titleMap = {
    overview: ["Dashboard", "Actionable intelligence from reports, signals, and market data."],
    prospects: ["Priority Prospects", "Evidence-backed company opportunities for RM review."],
    signals: ["Trigger Signals", "Market, policy, financing, and risk signals linked to companies."],
    companies: ["Companies", "Company fact layer, profile coverage, and linked activity."],
    copilot: ["Copilot", "Evidence-grounded Q&A over current backend data."],
    detail: ["Prospect Detail", "Brief, evidence, score audit, review, and workflow state."],
  };
  const [title, subtitle] = titleMap[state.route] || titleMap.overview;
  $("#page-title").textContent = title;
  $("#page-subtitle").textContent = subtitle;

  if (!state.backendOnline && state.backendError && !state.sampleToastShown) {
    showToast("Backend not available. Showing sample data.");
    state.sampleToastShown = true;
    state.backendError = null;
  }

  if (state.route === "overview") content.innerHTML = renderOverview();
  else if (state.route === "prospects") content.innerHTML = renderProspects();
  else if (state.route === "signals") content.innerHTML = renderSignals();
  else if (state.route === "companies") content.innerHTML = renderCompanies();
  else if (state.route === "copilot") content.innerHTML = renderCopilot();
  else if (state.route === "detail") content.innerHTML = renderDetail();
  else content.innerHTML = renderOverview();
}

function renderModeBanner() {
  if (state.backendOnline) {
    return `<div class="list-card" style="margin-bottom:14px"><span class="badge high">Live API</span> <span class="muted">Connected to ${escapeHtml(cleanBase(state.apiBase))}</span></div>`;
  }
  return `<div class="list-card" style="margin-bottom:14px"><span class="badge medium">Sample data</span> <span class="muted">Start the FastAPI backend or set a shared API base URL to connect live data.</span></div>`;
}

async function saveWorkflow(form) {
  const id = form.dataset.prospectId;
  const payload = Object.fromEntries(new FormData(form).entries());
  try {
    const result = await apiFetch(`/api/prospects/${encodeURIComponent(id)}/workflow`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (state.detailCache[id]) state.detailCache[id].workflow = result;
    showToast("Workflow saved.");
    render();
  } catch (error) {
    showToast(`Workflow save failed: ${error.message}`);
  }
}

async function askCopilot(question, prospectId) {
  const prompt = String(question || "").trim();
  if (!prompt) return;
  state.chat.push({ role: "user", content: prompt });
  state.chat.push({ role: "assistant", content: "Thinking against the evidence layer..." });
  render();

  try {
    const path = prospectId
      ? `/api/prospects/${encodeURIComponent(prospectId)}/question`
      : "/api/rag/query";
    const body = prospectId
      ? { question: prompt, include_chunks: false, top_k: 8 }
      : { question: prompt, include_chunks: false, top_k: 8, filters: {} };
    const result = await apiFetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const citationText = (result.citations || [])
      .slice(0, 4)
      .map((c, index) => `${index + 1}. ${c.source || "source"} ${c.dataset || ""} ${c.record_key || c.signal_key || ""}`.trim())
      .join("\n");
    state.chat[state.chat.length - 1] = {
      role: "assistant",
      content: `${result.answer || "No answer returned."}${citationText ? `\n\nCitations:\n${citationText}` : ""}`,
    };
  } catch (error) {
    state.chat[state.chat.length - 1] = {
      role: "assistant",
      content: state.backendOnline
        ? `Copilot request failed: ${error.message}`
        : "Backend is offline, so Copilot is unavailable. Start the FastAPI backend to use evidence-grounded Q&A.",
    };
  }
  render();
}

document.addEventListener("click", (event) => {
  const routeButton = event.target.closest("[data-route]");
  if (routeButton) {
    state.route = routeButton.dataset.route;
    state.selectedProspectId = null;
    state.search = "";
    setHash(state.route);
    render();
    return;
  }

  const openButton = event.target.closest("[data-open-prospect]");
  if (openButton) {
    openProspect(openButton.dataset.openProspect);
    return;
  }

  const tabButton = event.target.closest("[data-detail-tab]");
  if (tabButton) {
    state.activeDetailTab = tabButton.dataset.detailTab;
    render();
    return;
  }

  const signalAsk = event.target.closest("[data-ask-signal]");
  if (signalAsk) {
    state.route = "copilot";
    state.chat = [];
    setHash("copilot");
    askCopilot(`Explain this signal for an RM and suggest the next action: ${signalAsk.dataset.askSignal}`, state.selectedProspectId);
    return;
  }

  const prospectAsk = event.target.closest("[data-copilot-prospect]");
  if (prospectAsk) {
    state.selectedProspectId = prospectAsk.dataset.copilotProspect;
    state.route = "copilot";
    setHash("copilot");
    render();
    return;
  }

  const quickPrompt = event.target.closest("[data-quick-prompt]");
  if (quickPrompt) {
    askCopilot(quickPrompt.dataset.quickPrompt, $("#copilot-prospect")?.value || state.selectedProspectId);
  }
});

document.addEventListener("input", (event) => {
  if (event.target.id === "prospect-search" || event.target.id === "signal-search" || event.target.id === "company-search") {
    const inputId = event.target.id;
    const cursor = event.target.selectionStart;
    state.search = event.target.value;
    render();
    const nextInput = $(`#${inputId}`);
    if (nextInput) {
      nextInput.focus();
      nextInput.setSelectionRange(cursor, cursor);
    }
  }
});

document.addEventListener("change", (event) => {
  if (event.target.id === "industry-filter") {
    state.industryFilter = event.target.value;
    render();
  }
  if (event.target.id === "region-filter") {
    state.regionFilter = event.target.value;
    render();
  }
  if (event.target.id === "signal-type-filter") {
    state.signalTypeFilter = event.target.value;
    render();
  }
});

document.addEventListener("submit", (event) => {
  if (event.target.id === "workflow-form") {
    event.preventDefault();
    saveWorkflow(event.target);
  }
  if (event.target.id === "copilot-form") {
    event.preventDefault();
    askCopilot($("#copilot-question").value, $("#copilot-prospect").value);
    $("#copilot-question").value = "";
  }
});

$("#save-api-settings").addEventListener("click", () => {
  state.apiBase = cleanBase($("#api-base-input").value);
  state.apiKey = $("#api-key-input").value.trim();
  localStorage.setItem("INSIGHTSYNC_API_BASE", state.apiBase);
  if (state.apiKey) localStorage.setItem("INSIGHTSYNC_API_KEY", state.apiKey);
  else localStorage.removeItem("INSIGHTSYNC_API_KEY");
  state.detailCache = {};
  state.sampleToastShown = false;
  showToast("API settings saved.");
  loadData();
});

$("#refresh-data").addEventListener("click", () => {
  state.detailCache = {};
  state.sampleToastShown = false;
  loadData();
});

window.addEventListener("hashchange", () => {
  const parsed = routeFromHash();
  state.route = parsed.route;
  state.selectedProspectId = parsed.id;
  render();
});

document.addEventListener("click", (event) => {
  if (event.target.id === "clear-filters") {
    state.search = "";
    state.industryFilter = "all";
    state.regionFilter = "all";
    state.signalTypeFilter = "all";
    render();
  }
});

loadData();
