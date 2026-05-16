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
  priorityFilter: "all",
  chat: [],
  copilotOpen: false,
  sampleToastShown: false,
};

const $ = (selector) => document.querySelector(selector);
const content = $("#content");
const copilotRoot = $("#copilot-root");

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "\"": "&quot;",
    "'": "&#039;",
  })[char]);
}

function icon(name, className = "") {
  const icons = {
    users: `<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M22 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path>`,
    zap: `<path d="M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z"></path>`,
    globe: `<circle cx="12" cy="12" r="10"></circle><path d="M2 12h20"></path><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>`,
    trending: `<path d="M16 7h6v6"></path><path d="m22 7-8.5 8.5-5-5L2 17"></path>`,
    building: `<path d="M3 21h18"></path><path d="M5 21V7l8-4v18"></path><path d="M19 21V11l-6-4"></path><path d="M9 9v.01"></path><path d="M9 12v.01"></path><path d="M9 15v.01"></path><path d="M9 18v.01"></path>`,
    file: `<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7z"></path><path d="M14 2v4a2 2 0 0 0 2 2h4"></path><path d="M10 9H8"></path><path d="M16 13H8"></path><path d="M16 17H8"></path>`,
    clock: `<circle cx="12" cy="12" r="10"></circle><path d="M12 6v6l4 2"></path>`,
    search: `<circle cx="11" cy="11" r="8"></circle><path d="m21 21-4.35-4.35"></path>`,
    sparkles: `<path d="M11.02 2.81a1 1 0 0 1 1.96 0l1.05 5.56a2 2 0 0 0 1.6 1.6l5.56 1.05a1 1 0 0 1 0 1.96l-5.56 1.05a2 2 0 0 0-1.6 1.6l-1.05 5.56a1 1 0 0 1-1.96 0l-1.05-5.56a2 2 0 0 0-1.6-1.6l-5.56-1.05a1 1 0 0 1 0-1.96l5.56-1.05a2 2 0 0 0 1.6-1.6z"></path>`,
    external: `<path d="M15 3h6v6"></path><path d="M10 14 21 3"></path><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>`,
    chevron: `<path d="m9 18 6-6-6-6"></path>`,
    filter: `<path d="M3 6h18"></path><path d="M7 12h10"></path><path d="M10 18h4"></path>`,
    x: `<path d="M18 6 6 18"></path><path d="m6 6 12 12"></path>`,
    send: `<path d="m22 2-7 20-4-9-9-4Z"></path><path d="M22 2 11 13"></path>`,
    arrowLeft: `<path d="m12 19-7-7 7-7"></path><path d="M19 12H5"></path>`,
    edit: `<path d="M12 20h9"></path><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"></path>`,
    target: `<circle cx="12" cy="12" r="10"></circle><circle cx="12" cy="12" r="6"></circle><circle cx="12" cy="12" r="2"></circle>`,
    check: `<path d="M20 6 9 17l-5-5"></path>`,
    calendar: `<path d="M8 2v4"></path><path d="M16 2v4"></path><rect x="3" y="4" width="18" height="18" rx="2"></rect><path d="M3 10h18"></path>`,
  };
  return `<svg class="${escapeHtml(className)}" viewBox="0 0 24 24" aria-hidden="true">${icons[name] || icons.file}</svg>`;
}

function routeFromHash() {
  const raw = (window.location.hash || "#overview").replace(/^#/, "");
  if (raw.startsWith("prospect/")) {
    return { route: "detail", id: decodeURIComponent(raw.slice("prospect/".length)) };
  }
  if (raw === "copilot") {
    return { route: "overview", id: null };
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

function formatShortDate(value) {
  if (!value) return "To schedule";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value).slice(0, 10);
  return date.toLocaleDateString("en-HK", { month: "short", day: "numeric" });
}

function formatLabel(value) {
  const label = String(value || "").replace(/[_-]/g, " ").trim();
  if (!label) return "Not set";
  return label.replace(/\b\w/g, (char) => char.toUpperCase());
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
      const products = (item.recommended_product_themes || []).join(" ").toLowerCase();
      if (q && !`${name} ${industries} ${region} ${tags}`.includes(q)) return false;
      if (state.priorityFilter === "high" && priorityClass(item.priority_level) !== "high") return false;
      if (state.industryFilter !== "all" && !(item.industries || []).includes(state.industryFilter)) return false;
      if (state.regionFilter !== "all" && item.region !== state.regionFilter) return false;
      if (
        state.signalTypeFilter !== "all" &&
        !`${tags} ${products}`.includes(String(state.signalTypeFilter).toLowerCase()) &&
        !linkedSignalsForProspect(item).some((signal) => signalMatchesFilter(signal, state.signalTypeFilter))
      ) {
        return false;
      }
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

function metricCard(label, value, detail, options = {}) {
  const tone = options.tone || "";
  const route = options.route ? ` data-route="${escapeHtml(options.route)}"` : "";
  const filter = options.filter ? ` data-summary-filter="${escapeHtml(options.filter)}"` : "";
  const tag = options.route ? "button" : "div";
  return `
    <${tag} class="metric-card ${escapeHtml(tone)}"${route}${filter}>
      <div class="metric-top">
        <span class="metric-icon">${icon(options.icon || "users")}</span>
        ${options.route ? icon("chevron", "chevron-icon") : ""}
      </div>
      <div class="metric-value">${escapeHtml(value ?? 0)}</div>
      <small>${escapeHtml(label)}</small>
      <small>${escapeHtml(detail || "")}</small>
    </${tag}>
  `;
}

function bars(items = [], options = {}) {
  const max = Math.max(1, ...items.map((item) => item.count || item.value || 0));
  if (!items.length) return `<div class="empty-state">No distribution data available yet.</div>`;
  return items.map((item, index) => {
    const count = item.count ?? item.value ?? 0;
    const width = Math.max(3, Math.round((count / max) * 100));
    const label = item[options.labelKey || "name"] || item.name || item.value || "Unknown";
    const isActive = options.activeValue && label === options.activeValue;
    const dataAttrs = options.filterType
      ? ` data-chart-filter="${escapeHtml(options.filterType)}" data-filter-value="${escapeHtml(label)}"`
      : "";
    return `
      <button class="bar-row ${isActive ? "active" : ""}"${dataAttrs} type="button">
        <span>${escapeHtml(label)}</span>
        <span class="bar-track"><span class="bar-fill" style="width:${width}%"></span></span>
        <strong>${escapeHtml(count)}</strong>
      </button>
    `;
  }).join("");
}

function polarToCartesian(cx, cy, radius, angleInDegrees) {
  const angleInRadians = (angleInDegrees - 90) * Math.PI / 180;
  return {
    x: cx + (radius * Math.cos(angleInRadians)),
    y: cy + (radius * Math.sin(angleInRadians)),
  };
}

function donutSegmentPath(cx, cy, radius, startAngle, endAngle) {
  const start = polarToCartesian(cx, cy, radius, endAngle);
  const end = polarToCartesian(cx, cy, radius, startAngle);
  const largeArcFlag = endAngle - startAngle <= 180 ? "0" : "1";
  return [
    "M", start.x, start.y,
    "A", radius, radius, 0, largeArcFlag, 0, end.x, end.y,
  ].join(" ");
}

function renderDonut(items = [], activeValue = "all") {
  const total = items.reduce((sum, item) => sum + (item.count || item.value || 0), 0);
  if (!items.length || total <= 0) return `<div class="empty-state">No region data available.</div>`;
  const colors = ["#44803f", "#c85731", "#3d7f9d", "#a27b22", "#7862a8"];
  let angle = 0;
  const segments = items.map((item, index) => {
    const value = item.count ?? item.value ?? 0;
    const sweep = Math.min((value / total) * 360, 359.99);
    const start = angle;
    const end = angle + sweep;
    angle = end;
    const label = item.name || item.value || "Unknown";
    return `
      <path
        class="donut-segment ${activeValue === label ? "active" : ""}"
        d="${donutSegmentPath(80, 80, 58, start, end)}"
        stroke="${colors[index % colors.length]}"
        data-chart-filter="region"
        data-filter-value="${escapeHtml(label)}"
      ></path>
    `;
  }).join("");

  const legend = items.slice(0, 4).map((item, index) => {
    const label = item.name || item.value || "Unknown";
    return `
      <button class="donut-legend ${activeValue === label ? "active" : ""}" data-chart-filter="region" data-filter-value="${escapeHtml(label)}" type="button">
        <span style="background:${colors[index % colors.length]}"></span>
        ${escapeHtml(label)}
      </button>
    `;
  }).join("");

  return `
    <div class="donut-wrap">
      <svg class="donut-chart" viewBox="0 0 160 160" role="img" aria-label="Region distribution">
        <circle cx="80" cy="80" r="58"></circle>
        ${segments}
      </svg>
      <div class="donut-legend-row">${legend}</div>
    </div>
  `;
}

function distribution(items, getter) {
  const counts = new Map();
  items.forEach((item) => {
    const key = getter(item) || "Unknown";
    counts.set(key, (counts.get(key) || 0) + 1);
  });
  return Array.from(counts.entries())
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count);
}

function signalTypeLabel(value) {
  const normalized = String(value || "signal").toLowerCase().replace(/[_-]/g, " ");
  if (normalized.includes("cross")) return "Cross-border";
  if (normalized.includes("fund") || normalized.includes("financ")) return "Financing";
  if (normalized.includes("policy") || normalized.includes("macro")) return "Policy/Macro";
  if (normalized.includes("expansion")) return "Expansion";
  return normalized.replace(/\b\w/g, (char) => char.toUpperCase());
}

function signalTypeClass(value) {
  const normalized = String(value || "").toLowerCase();
  if (normalized.includes("cross")) return "cross_border";
  if (normalized.includes("fund") || normalized.includes("financ")) return "financing";
  if (normalized.includes("policy") || normalized.includes("macro")) return "policy";
  if (normalized.includes("expansion") || normalized.includes("growth")) return "expansion";
  return "signal";
}

function signalMatchesFilter(signal, filterValue) {
  if (!filterValue || filterValue === "all") return true;
  const filter = String(filterValue).toLowerCase().replace(/[^a-z0-9]/g, "");
  const raw = String(signal.signal_type || "").toLowerCase().replace(/[^a-z0-9]/g, "");
  const label = signalTypeLabel(signal.signal_type).toLowerCase().replace(/[^a-z0-9]/g, "");
  return raw === filter || label === filter || raw.includes(filter) || label.includes(filter);
}

function priorityTier(value) {
  const normalized = priorityClass(value);
  if (normalized === "high") return "A";
  if (normalized === "medium") return "B";
  return "C";
}

function signalBelongsToProspect(signal, prospect) {
  const prospectIds = [prospectId(prospect), companyId(prospect), prospectName(prospect)]
    .filter(Boolean)
    .map((value) => String(value).toLowerCase().replace(/[^a-z0-9]/g, ""));
  const signalIds = [signal.prospect_id, signal.company_id, signal.entity, signal.company]
    .filter(Boolean)
    .map((value) => String(value).toLowerCase().replace(/[^a-z0-9]/g, ""));
  return signalIds.some((value) => prospectIds.includes(value));
}

function linkedSignalsForProspect(prospect) {
  return asList(state.data.signals).filter((signal) => signalBelongsToProspect(signal, prospect));
}

function setOverviewFilter(type, value) {
  if (type === "priority") {
    state.priorityFilter = value || "all";
    state.industryFilter = "all";
    state.regionFilter = "all";
    state.signalTypeFilter = "all";
  }
  if (type === "industry") {
    state.industryFilter = value || "all";
    state.priorityFilter = "all";
  }
  if (type === "region") {
    state.regionFilter = value || "all";
    state.priorityFilter = "all";
  }
  if (type === "signal") {
    state.signalTypeFilter = value || "all";
    state.priorityFilter = "all";
  }
}

function hasOverviewFilters() {
  return (
    state.priorityFilter !== "all" ||
    state.industryFilter !== "all" ||
    state.regionFilter !== "all" ||
    state.signalTypeFilter !== "all"
  );
}

function renderActiveFilters() {
  if (!hasOverviewFilters()) return "";
  const filters = [
    state.priorityFilter !== "all" ? { type: "priority", label: "Priority: High", tone: "risk" } : null,
    state.industryFilter !== "all" ? { type: "industry", label: `Industry: ${state.industryFilter}`, tone: "high" } : null,
    state.regionFilter !== "all" ? { type: "region", label: `Region: ${state.regionFilter}`, tone: "blue" } : null,
    state.signalTypeFilter !== "all" ? { type: "signal", label: `Signal: ${signalTypeLabel(state.signalTypeFilter)}`, tone: "medium" } : null,
  ].filter(Boolean);

  return `
    <div class="active-filters" id="prospect-filter-anchor">
      ${icon("filter")}
      <span>Active filters:</span>
      <div class="wrap">
        ${filters.map((filter) => `
          <button class="badge ${escapeHtml(filter.tone)} removable" data-clear-filter="${escapeHtml(filter.type)}">
            ${escapeHtml(filter.label)}
            <span aria-hidden="true">x</span>
          </button>
        `).join("")}
      </div>
      <button class="button ghost small" id="clear-filters">Clear all</button>
    </div>
  `;
}

function filteredOverviewProspects(items) {
  return items
    .filter((item) => {
      if (state.priorityFilter === "high" && priorityClass(item.priority_level) !== "high") return false;
      if (state.industryFilter !== "all" && !(item.industries || []).includes(state.industryFilter)) return false;
      if (state.regionFilter !== "all" && item.region !== state.regionFilter) return false;
      if (
        state.signalTypeFilter !== "all" &&
        !(item.focus_tags || []).some((tag) => String(tag).toLowerCase().includes(String(state.signalTypeFilter).toLowerCase())) &&
        !(item.recommended_product_themes || []).some((tag) => String(tag).toLowerCase().includes(String(state.signalTypeFilter).toLowerCase())) &&
        !linkedSignalsForProspect(item).some((signal) => signalMatchesFilter(signal, state.signalTypeFilter))
      ) {
        return false;
      }
      return true;
    })
    .sort((a, b) => (b.priority_score || 0) - (a.priority_score || 0));
}

function renderOverview() {
  const summary = state.data.summary || mockData.summary;
  const market = state.data.marketOverview || mockData.marketOverview;
  const allProspects = asList(state.data.prospects);
  const allSignals = asList(state.data.signals);
  const unfilteredTopProspects = asList(state.data.priorityProspects).length
    ? asList(state.data.priorityProspects)
    : getFilteredProspects().slice(0, 5);
  const filteredProspects = filteredOverviewProspects(allProspects);
  const topProspects = hasOverviewFilters() ? filteredProspects.slice(0, 8) : unfilteredTopProspects.slice(0, 8);
  const triggerSignals = asList(state.data.triggerSignals).length
    ? asList(state.data.triggerSignals)
    : asList(state.data.signals).slice(0, 5);
  const signalBreakdown = distribution(allSignals, (item) => signalTypeLabel(item.signal_type));
  const focusScore = Math.round(
    (topProspects.slice(0, 5).reduce((sum, item) => sum + (item.priority_score || 0), 0) || 0) /
      Math.max(1, topProspects.slice(0, 5).length)
  );
  const primaryTheme = (summary.cross_border || 0) >= (summary.financing_signals || 0)
    ? "cross-border activity"
    : "financing-linked signals";

  return `
    <section class="section">
      <div class="section-header">
        <h2 class="section-title">Portfolio Summary</h2>
        <span class="section-note">${icon("clock")} ${state.backendOnline ? "Live intelligence" : "Sample data"}</span>
      </div>
      <div class="grid metrics">
        ${metricCard("Company profiles", summary.lead_pool ?? allProspects.length, "Current prospect universe", { icon: "users", route: "overview", filter: "all" })}
        ${metricCard("High-priority companies", summary.high_priority, "Prospects requiring RM review", { icon: "zap", tone: "danger", route: "overview", filter: "high" })}
        ${metricCard("Cross-border opportunities", summary.cross_border, "Signals and focus tags", { icon: "globe", tone: "blue", route: "overview", filter: "crossborder" })}
        ${metricCard("Financing-linked signals", summary.financing_signals, "Liquidity and funding themes", { icon: "trending", tone: "orange", route: "overview", filter: "financing" })}
      </div>
    </section>

    <section class="brief-panel section">
      <div>
        <span class="badge high">Morning Brief</span>
        <h2>${escapeHtml(topProspects.length)} client relationships need RM review</h2>
        <p>
          Portfolio activity is led by ${escapeHtml(primaryTheme)}. Start with high-priority
          company profiles, then open the supporting evidence before outreach.
        </p>
        <div class="wrap mt">
          <button class="button primary" data-route="prospects">Review RM Actions</button>
          <button class="button" data-route="signals">Open Evidence</button>
          <button class="button" data-open-copilot>Ask Copilot</button>
        </div>
      </div>
      <button class="focus-score" data-route="prospects">
        <span>Focus score</span>
        <strong>${escapeHtml(focusScore)}</strong>
        <small>${escapeHtml(summary.high_priority || 0)} priority clients</small>
      </button>
    </section>

    <section class="section">
      <div class="section-header">
        <h2 class="section-title">Market Opportunity Overview</h2>
        <span class="section-note">Click into prospects or signals to inspect evidence</span>
      </div>
      <div class="grid three">
        <article class="panel chart-card">
          <div class="panel-header">
            <h3 class="panel-title">By Industry</h3>
          </div>
          <div class="panel-body">${bars(market.industry_breakdown, { filterType: "industry", activeValue: state.industryFilter !== "all" ? state.industryFilter : "" })}</div>
        </article>
        <article class="panel chart-card">
          <div class="panel-header">
            <h3 class="panel-title">By Region</h3>
          </div>
          <div class="panel-body">
            ${renderDonut(market.region_breakdown, state.regionFilter)}
            ${bars(market.region_breakdown, { filterType: "region", activeValue: state.regionFilter !== "all" ? state.regionFilter : "" })}
          </div>
        </article>
        <article class="panel chart-card">
          <div class="panel-header">
            <h3 class="panel-title">By Signal Type</h3>
          </div>
          <div class="panel-body">${bars(signalBreakdown, { filterType: "signal", activeValue: state.signalTypeFilter !== "all" ? state.signalTypeFilter : "" })}</div>
        </article>
      </div>
    </section>

    ${renderActiveFilters()}

    <section class="panel section">
      <div class="panel-header">
        <div>
          <h2 class="panel-title">Top Priority Company Profiles</h2>
          <p class="panel-subtitle">Showing top ${escapeHtml(Math.min(topProspects.length, 8))} of ${escapeHtml(filteredProspects.length)} matching companies.</p>
        </div>
        <button class="button small" data-route="prospects">View all</button>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Company</th>
              <th>Priority assessment</th>
              <th>Trigger evidence</th>
              <th>Recommended approach</th>
              <th>Relationship status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            ${topProspects.slice(0, 8).map((item) => `
              <tr>
                <td>
                  <div class="company-name">${escapeHtml(prospectName(item))}</div>
                  <div class="muted">${escapeHtml([item.region, (item.industries || [])[0], companyId(item)].filter(Boolean).join(" / "))}</div>
                </td>
                <td>
                  <span class="badge ${escapeHtml(priorityTier(item.priority_level).toLowerCase())}">Tier ${escapeHtml(priorityTier(item.priority_level))}</span>
                  <div class="muted">Priority score ${escapeHtml(item.priority_score ?? "N/A")}</div>
                  <div class="muted">Evidence ${escapeHtml(item.evidence_confidence_score ?? "N/A")}</div>
                </td>
                <td>${formatTags(item.focus_tags || [], 3)}</td>
                <td>${escapeHtml((item.why_prioritized || [])[0] || item.recommended_next_step || "Review linked evidence.")}</td>
                <td>
                  <div>${escapeHtml(item.workflow_state?.stage || "New prospect")}</div>
                  <div class="muted">Owner: ${escapeHtml(item.workflow_state?.owner || "Unassigned")}</div>
                  <div class="muted">${escapeHtml(item.recommended_next_step || "Prepare evidence-backed outreach.")}</div>
                </td>
                <td><button class="button small primary" data-open-prospect="${escapeHtml(prospectId(item))}">Open brief</button></td>
              </tr>
            `).join("") || `<tr><td colspan="6"><div class="empty-state">No company profiles match filters.</div></td></tr>`}
          </tbody>
        </table>
      </div>
    </section>

    <section class="section">
      <div class="section-header">
        <div>
          <h2 class="section-title">Recent Trigger Signals</h2>
        </div>
        <button class="button small" data-route="signals">Open signal explorer</button>
      </div>
      <div class="list">
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

function renderProspectCard(item) {
  const workflow = item.workflow_state || {};
  const linkedSignals = linkedSignalsForProspect(item);
  const latestSignal = linkedSignals[0];
  const tier = priorityTier(item.priority_level);
  const priority = priorityClass(item.priority_level);
  const reasons = item.why_prioritized || [];
  const products = item.recommended_product_themes || item.focus_tags || [];
  const focus = item.recommended_next_step || reasons[0] || "Review evidence and prepare an RM outreach brief.";

  return `
    <article class="prospect-card">
      <div class="prospect-rail ${escapeHtml(priority)}"></div>
      <div class="prospect-body">
        <div class="prospect-head">
          <div>
            <div class="prospect-title-row">
              <h3 class="company-name">${escapeHtml(prospectName(item))}</h3>
              <span class="badge ${escapeHtml(tier.toLowerCase())}">Tier ${escapeHtml(tier)}</span>
              <span class="muted">Score: ${escapeHtml(item.priority_score ?? "N/A")}</span>
            </div>
            <div class="prospect-meta">
              <span>${icon("building")}${escapeHtml((item.industries || [])[0] || "Unknown industry")}</span>
              <span>${icon("globe")}${escapeHtml(item.region || "Unknown region")}</span>
              <span>${icon("users")}Owner: ${escapeHtml(workflow.owner || "Unassigned")}</span>
            </div>
          </div>
          <div class="wrap">
            <button class="button ghost small" data-copilot-prospect="${escapeHtml(prospectId(item))}">${icon("sparkles", "button-icon")} Ask AI</button>
            <button class="button small" data-open-prospect="${escapeHtml(prospectId(item))}">Open brief ${icon("external", "button-icon")}</button>
          </div>
        </div>

        <div class="conversation-focus">
          <strong>RM Conversation Focus</strong>
          <p>${escapeHtml(focus)}</p>
          ${reasons.length ? `<div class="wrap mt">${reasons.slice(0, 3).map((reason) => `<span class="badge">${escapeHtml(reason)}</span>`).join("")}</div>` : ""}
        </div>

        <div class="prospect-meta">
          ${latestSignal ? `<span><span class="badge blue">Evidence: ${escapeHtml(signalTypeLabel(latestSignal.signal_type))}</span> ${escapeHtml(signalTitle(latestSignal))}</span>` : `<span class="muted">Evidence awaiting linked signal review</span>`}
          <span class="badge">Evidence: ${escapeHtml(linkedSignals.length)}</span>
          <span class="badge">Stage: ${escapeHtml(workflow.stage || "new")}</span>
          <span>${icon("clock")}Follow-up ${escapeHtml(workflow.next_action || "To schedule")}</span>
        </div>

        <div class="wrap mt">
          ${products.slice(0, 6).map((product) => `<span class="badge monitor">${escapeHtml(product)}</span>`).join("")}
        </div>
      </div>
    </article>
  `;
}

function renderProspects() {
  const items = getFilteredProspects();
  const allProspects = asList(state.data.prospects);
  const industries = unique(allProspects.flatMap((p) => p.industries || []));
  const regions = unique(allProspects.map((p) => p.region));

  return `
    ${renderModeBanner()}
    <div class="toolbar">
      <div class="search-wrap">
        ${icon("search")}
        <input id="prospect-search" value="${escapeHtml(state.search)}" placeholder="Search company profiles..." />
      </div>
      <select id="industry-filter">${optionList(industries, state.industryFilter)}</select>
      <select id="region-filter">${optionList(regions, state.regionFilter)}</select>
      <button class="button outline" id="clear-filters">${icon("filter", "button-icon")} Clear</button>
      <span class="toolbar-spacer"></span>
      <span class="section-note">${items.length} company profiles / ${state.backendOnline ? "live intelligence" : "sample data"}</span>
    </div>

    <div class="list">
      ${items.map(renderProspectCard).join("") || `<div class="empty-state">No prospects match the current filters.</div>`}
    </div>
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
      <div class="search-wrap">
        ${icon("search")}
        <input id="company-search" value="${escapeHtml(state.search)}" placeholder="Search company, source, region, industry, or profile text" />
      </div>
      <select id="industry-filter">${optionList(industries, state.industryFilter)}</select>
      <select id="region-filter">${optionList(regions, state.regionFilter)}</select>
      <button class="button outline" id="clear-filters">${icon("filter", "button-icon")} Clear</button>
      <span class="toolbar-spacer"></span>
      <span class="section-note">${items.length} of ${allCompanies.length} companies</span>
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
  const typeClass = signalTypeClass(item.signal_type);
  const levelClass = item.signal_level === "high" ? "risk" : "monitor";
  return `
    <article class="signal-card">
      <div class="signal-icon ${escapeHtml(typeClass)}">${icon(typeClass === "cross_border" ? "globe" : typeClass === "financing" ? "trending" : typeClass === "policy" ? "file" : "zap")}</div>
      <div class="signal-content">
        <div class="signal-head">
          <div>
            <h3>${escapeHtml(signalTitle(item))}</h3>
            <div class="muted">${escapeHtml(signalCompany(item))}</div>
          </div>
          <div class="wrap">
            <span class="badge ${escapeHtml(levelClass)}">${escapeHtml(signalTypeLabel(item.signal_type))}</span>
            <span class="badge">${escapeHtml(formatDate(item.event_time))}</span>
          </div>
        </div>
        <p>${escapeHtml(item.signal_text || item.value_text || item.detail || "")}</p>
        <div class="prospect-meta">
          <span class="badge monitor">Source: ${escapeHtml(item.source || "InsightSync")}</span>
          ${item.signal_level ? `<span class="badge ${escapeHtml(levelClass)}">Level: ${escapeHtml(item.signal_level)}</span>` : ""}
          ${item.prospect_id ? `<span class="badge high">Linked company profile</span>` : ""}
        </div>
        <div class="wrap mt">
          <button class="button ghost small" data-ask-signal="${escapeHtml(signalTitle(item))}">${icon("sparkles", "button-icon")} Explain</button>
          ${item.prospect_id ? `<button class="button small" data-open-prospect="${escapeHtml(item.prospect_id)}">Open Company Brief ${icon("external", "button-icon")}</button>` : ""}
        </div>
      </div>
    </article>
  `;
}

function renderSignals() {
  const items = getFilteredSignals();
  const allSignals = asList(state.data.signals);
  const types = unique(allSignals.map((signal) => signal.signal_type));
  const chipTypes = ["all"].concat(types);
  return `
    ${renderModeBanner()}
    <div class="chip-row">
      ${chipTypes.map((type) => `
        <button class="chip ${state.signalTypeFilter === type ? "active" : ""}" data-signal-chip="${escapeHtml(type)}">
          ${icon(type === "all" ? "zap" : signalTypeClass(type) === "cross_border" ? "globe" : signalTypeClass(type) === "financing" ? "trending" : signalTypeClass(type) === "policy" ? "file" : "zap")}
          ${escapeHtml(type === "all" ? "All Signals" : signalTypeLabel(type))}
        </button>
      `).join("")}
    </div>
    <div class="toolbar">
      <div class="search-wrap">
        ${icon("search")}
        <input id="signal-search" value="${escapeHtml(state.search)}" placeholder="Search signals..." />
      </div>
      <select id="signal-type-filter">${optionList(types, state.signalTypeFilter)}</select>
      <button class="button outline" id="clear-filters">${icon("filter", "button-icon")} Clear</button>
      <span class="toolbar-spacer"></span>
      <span class="section-note">${items.length} actionable signals / ${state.backendOnline ? "live intelligence" : "sample data"}</span>
    </div>
    <div class="list">
      ${items.map(renderSignalCard).join("") || `<div class="empty-state">No signals match the current filters.</div>`}
    </div>
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

function detailSignalsForProspect(p, detail = {}) {
  const detailSignals = detail.recent_signals || [];
  return detailSignals.length ? detailSignals : linkedSignalsForProspect(p);
}

function detailEvidenceCount(signals = [], evidence = {}, detail = {}) {
  return (
    signals.length +
    (evidence.recent_documents || detail.recent_documents || []).length +
    (evidence.key_metrics || detail.key_metrics || []).length +
    (evidence.key_risk_factors || detail.key_risk_factors || []).length +
    (evidence.key_business_events || detail.key_business_events || []).length
  );
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
  const signals = detailSignalsForProspect(p, detail);
  const documents = evidence.recent_documents || detail.recent_documents || [];
  const metrics = evidence.key_metrics || detail.key_metrics || [];
  const risks = evidence.key_risk_factors || detail.key_risk_factors || [];
  const events = evidence.key_business_events || detail.key_business_events || [];
  const products = brief.recommended_product_themes || p.recommended_product_themes || p.focus_tags || [];
  const opportunities = brief.top_opportunities || products;
  const topRisks = brief.top_risks || risks.map((risk) => risk.category || risk.description).filter(Boolean);
  const nextAction = workflow.next_action || brief.recommended_next_step || p.recommended_next_step || "Review linked evidence and prepare client outreach.";
  const primaryTopic = opportunities[0] || (p.focus_tags || [])[0] || "Evidence-backed client outreach";
  const primaryEvidence = signals[0] || documents[0];
  const evidenceCount = detailEvidenceCount(signals, evidence, detail);
  const currentStage = workflow.stage || "new";
  const reviewStatus = workflow.review_status || "not_reviewed";

  return `
    <section class="detail-topbar">
      <div>
        <button class="button ghost" data-route="prospects">${icon("arrowLeft", "button-icon")} Back</button>
      </div>
      <div class="detail-topbar-title">
        <h2>Client Action Brief</h2>
        <p>Pre-meeting summary for ${escapeHtml(prospectName(p))}</p>
      </div>
      <div class="detail-topbar-actions">
        <button class="button outline" data-scroll-target="workflow-section">${icon("edit", "button-icon")} Update RM Notes</button>
        <button class="button primary" data-copilot-prospect="${escapeHtml(prospectId(p))}">${icon("sparkles", "button-icon")} Ask AI Copilot</button>
      </div>
    </section>
    ${renderModeBanner()}

    <section class="detail-hero mt">
      <div>
        <div class="wrap">
          <span class="badge ${escapeHtml(priorityTier(p.priority_level).toLowerCase())}">Tier ${escapeHtml(priorityTier(p.priority_level))}</span>
          <span class="badge">Priority score ${escapeHtml(p.priority_score ?? "N/A")}</span>
          <span class="badge">${escapeHtml(formatLabel(reviewStatus))}</span>
        </div>
        <h2>${escapeHtml(prospectName(p))}</h2>
        <div class="detail-meta">
          <span>${icon("building")}${escapeHtml((p.industries || [])[0] || "Unknown industry")}</span>
          <span>${icon("globe")}${escapeHtml(p.region || "Unknown region")}</span>
          <span>${icon("users")}Owner: ${escapeHtml(workflow.owner || "Unassigned")}</span>
          <span>${icon("calendar")}Follow-up ${escapeHtml(formatShortDate(workflow.next_follow_up_at || workflow.next_follow_up || workflow.updated_at))}</span>
        </div>
        <div class="today-action">
          <p class="eyebrow">Today's RM action</p>
          <h3>${escapeHtml(nextAction)}</h3>
          <p>
            Start with <strong>${escapeHtml(primaryTopic)}</strong>.
            ${primaryEvidence ? ` Strongest current evidence: ${escapeHtml(signalTitle(primaryEvidence) || primaryEvidence.title || "linked record")}.` : " No direct evidence is linked yet, so review broader market context before outreach."}
          </p>
        </div>
      </div>
      <div class="detail-side-metrics">
        <div class="score-box wide"><span>Evidence confidence</span><strong>${escapeHtml(p.evidence_confidence_score ?? "N/A")}</strong><small>${escapeHtml(evidenceCount)} linked records</small></div>
        <div class="score-grid compact">
          <div class="score-box"><span>Opportunity</span><strong>${escapeHtml(p.opportunity_score ?? "N/A")}</strong></div>
          <div class="score-box"><span>Risk</span><strong>${escapeHtml(p.risk_score ?? "N/A")}</strong></div>
        </div>
        <button class="button primary full" data-scroll-target="workflow-section">${icon("check", "button-icon")} Mark review / add note</button>
      </div>
    </section>

    <div class="detail-layout mt">
      <div class="detail-main-stack">
        <section class="panel action-plan-panel">
          <div class="panel-header">
            <div>
              <h2 class="panel-title">${icon("target")} RM Action Plan</h2>
              <p class="panel-subtitle">What the RM should do next, why it matters, and how to open the conversation.</p>
            </div>
          </div>
          <div class="panel-body stack">
            <div class="grid three">
              <div class="mini-stat"><span>Primary topic</span><strong>${escapeHtml(primaryTopic)}</strong></div>
              <div class="mini-stat"><span>Why now</span><strong>${escapeHtml(evidenceCount)} linked evidence records</strong></div>
              <div class="mini-stat"><span>Next follow-up</span><strong>${escapeHtml(formatShortDate(workflow.next_follow_up_at || workflow.next_follow_up || workflow.updated_at))}</strong></div>
            </div>
            <div>
              <p class="section-kicker">Suggested client discussion points</p>
              <div class="list">
                ${(opportunities.length ? opportunities : [nextAction]).slice(0, 3).map((item) => `
                  <div class="action-point">
                    ${icon("trending")}
                    <div>
                      <h3>${escapeHtml(item)}</h3>
                      <p>${escapeHtml(brief.summary || (p.why_prioritized || [])[0] || "Use the linked evidence before committing to outreach.")}</p>
                    </div>
                  </div>
                `).join("")}
              </div>
            </div>
            <div>
              <p class="section-kicker">Product angle to prepare</p>
              <div class="wrap">${formatTags(products, 6)}</div>
            </div>
          </div>
        </section>

        <section class="panel">
          <div class="panel-header">
            <div>
              <h2 class="panel-title">${icon("file")} Evidence Supporting This Action</h2>
              <p class="panel-subtitle">Signals, parsed reports, metrics, risk factors, and events linked to this company brief.</p>
            </div>
            <span class="badge">Evidence layer</span>
          </div>
          <div class="panel-body stack">
            <div class="list">
              ${signals.slice(0, 5).map((signal) => `
                <div class="evidence-row">
                  <div>
                    <div class="wrap">
                      <span class="badge ${escapeHtml(signalTypeClass(signal.signal_type))}">${escapeHtml(signalTypeLabel(signal.signal_type))}</span>
                      <span class="badge">${escapeHtml(formatDate(signal.event_time || signal.date))}</span>
                      <span class="badge monitor">${escapeHtml(signal.source || "InsightSync")}</span>
                    </div>
                    <h3>${escapeHtml(signalTitle(signal))}</h3>
                    <p>${escapeHtml(signal.signal_text || signal.value_text || signal.detail || "")}</p>
                  </div>
                  <button class="button ghost small" data-ask-signal="${escapeHtml(signalTitle(signal))}">${icon("sparkles", "button-icon")} Explain</button>
                </div>
              `).join("")}
              ${documents.slice(0, 3).map((doc) => `
                <div class="evidence-row">
                  <div>
                    <div class="wrap">
                      <span class="badge">${escapeHtml(doc.parse_status || "parsed")}</span>
                      <span class="badge">${escapeHtml(doc.lang || "unknown language")}</span>
                      <span class="badge monitor">${escapeHtml(doc.source || "source")}</span>
                    </div>
                    <h3>${escapeHtml(doc.title || "Parsed document")}</h3>
                    <p>${escapeHtml(doc.summary || doc.management_discussion_summary || "")}</p>
                  </div>
                </div>
              `).join("")}
              ${!signals.length && !documents.length ? `<div class="empty-state">No RM-readable evidence is linked to this company yet.</div>` : ""}
            </div>
            <div class="grid two">
              <div class="list">
                <h3 class="panel-title">Extracted metrics</h3>
                ${metrics.slice(0, 4).map((item) => `<div class="list-card compact-card"><h3>${escapeHtml(item.name)}</h3><p>${escapeHtml([item.value, item.unit, item.period].filter(Boolean).join(" "))}</p><p class="muted">${escapeHtml(item.context || "")}</p></div>`).join("") || `<div class="empty-state">No structured metrics.</div>`}
              </div>
              <div class="list">
                <h3 class="panel-title">Risks and events</h3>
                ${risks.slice(0, 3).map((item) => `<div class="list-card compact-card"><span class="badge risk">${escapeHtml(item.severity || "risk")}</span><h3>${escapeHtml(item.category || "Risk factor")}</h3><p>${escapeHtml(item.description || "")}</p></div>`).join("")}
                ${events.slice(0, 3).map((item) => `<div class="list-card compact-card"><span class="badge">${escapeHtml(item.event_type || "event")}</span><h3>${escapeHtml(item.title || item.event_type || "Business event")}</h3><p>${escapeHtml(item.summary || "")}</p></div>`).join("")}
                ${!risks.length && !events.length ? `<div class="empty-state">No structured risks or events.</div>` : ""}
              </div>
            </div>
          </div>
        </section>

        <section class="panel">
          <div class="panel-header">
            <div>
              <h2 class="panel-title">Score Audit</h2>
              <p class="panel-subtitle">${escapeHtml(score.scoring_method || "Transparent scorecard with evidence-quality checks")}</p>
            </div>
            <span class="badge">${escapeHtml(score.calibration_status || "calibration pending")}</span>
          </div>
          <div class="panel-body stack">
            <div class="list-card compact-card">
              <h3>Formula</h3>
              <p>${escapeHtml(score.priority_formula || "Backend formula not returned.")}</p>
            </div>
            <div class="grid three">
              <div class="score-box"><span>Direct evidence ratio</span><strong>${escapeHtml(linkage.direct_evidence_ratio ?? "N/A")}</strong></div>
              <div class="score-box"><span>Scoreable ratio</span><strong>${escapeHtml(linkage.scoreable_evidence_ratio ?? "N/A")}</strong></div>
              <div class="score-box"><span>Context-only</span><strong>${escapeHtml(linkage.context_only_count ?? linkage.context_only_evidence_count ?? "N/A")}</strong></div>
            </div>
            <div class="grid two">
              <div class="list">
                <h3 class="panel-title">Opportunity components</h3>
                ${scoreComponentRows(score.opportunity_components)}
              </div>
              <div class="list">
                <h3 class="panel-title">Risk components</h3>
                ${scoreComponentRows(score.risk_components)}
              </div>
            </div>
          </div>
        </section>

        <section class="panel">
          <div class="panel-header">
            <div>
              <h2 class="panel-title">LLM Review</h2>
              <p class="panel-subtitle">Quality review for linkage strength, evidence gaps, and decision risk.</p>
            </div>
            <span class="badge">${escapeHtml(review.status || "not loaded")}</span>
          </div>
          <div class="panel-body stack">
            <div class="list-card compact-card">
              <h3>Summary</h3>
              <p>${escapeHtml(review.review_summary || "No LLM review returned yet.")}</p>
              <p class="muted">${escapeHtml(review.model_name || "")}</p>
            </div>
            <div class="grid two">
              <div class="list">
                <h3 class="panel-title">Audit findings</h3>
                ${(review.audit_findings || []).map((item) => `<div class="list-card compact-card"><span class="badge risk">${escapeHtml(item.severity || "finding")}</span><h3>${escapeHtml(item.area || "Finding")}</h3><p>${escapeHtml(item.issue || item.reason || "")}</p><p class="muted">${escapeHtml(item.suggested_action || "")}</p></div>`).join("") || `<div class="empty-state">No audit findings.</div>`}
              </div>
              <div class="list">
                <h3 class="panel-title">Extraction opportunities</h3>
                ${(review.extraction_opportunities || []).map((item) => `<div class="list-card compact-card"><h3>${escapeHtml(item.area || "Opportunity")}</h3><p>${escapeHtml(item.why || "")}</p><p class="muted">${escapeHtml(item.suggested_output || "")}</p></div>`).join("") || `<div class="empty-state">No extraction opportunities.</div>`}
              </div>
            </div>
          </div>
        </section>
      </div>

      <aside class="detail-side-stack">
        <section class="panel">
          <div class="panel-header">
            <div>
              <h2 class="panel-title">Relationship Context</h2>
              <p class="panel-subtitle">RM ownership and current working state.</p>
            </div>
          </div>
          <div class="panel-body stack">
            <div class="context-row"><span>Owner</span><strong>${escapeHtml(workflow.owner || "Unassigned")}</strong></div>
            <div class="context-row"><span>Stage</span><strong>${escapeHtml(formatLabel(currentStage))}</strong></div>
            <div class="context-row"><span>Status</span><strong>${escapeHtml(formatLabel(workflow.status || "open"))}</strong></div>
            <div class="context-row"><span>Review</span><strong>${escapeHtml(formatLabel(reviewStatus))}</strong></div>
            <div class="context-row"><span>Products</span><strong>${escapeHtml(products.length)} suggested</strong></div>
          </div>
        </section>

        <section class="panel">
          <div class="panel-header"><h2 class="panel-title">Product Angles</h2></div>
          <div class="panel-body">
            <div class="wrap">${formatTags(products, 8)}</div>
            <div class="mt">
              ${(topRisks.length ? topRisks : ["No major risk summary returned yet."]).slice(0, 4).map((risk) => `<div class="risk-note">${escapeHtml(risk)}</div>`).join("")}
            </div>
          </div>
        </section>

        <section class="panel" id="workflow-section">
          <div class="panel-header">
            <div>
              <h2 class="panel-title">Update RM Notes</h2>
              <p class="panel-subtitle">Saved to the backend workflow endpoint when available.</p>
            </div>
          </div>
          <div class="panel-body">
            ${renderWorkflowForm(id, workflow)}
          </div>
        </section>
      </aside>
    </div>
  `;
}

function renderWorkflowForm(id, workflow) {
  return `
    <form class="workflow-form" id="workflow-form" data-prospect-id="${escapeHtml(id)}">
      <label>Owner <input name="owner" value="${escapeHtml(workflow.owner || "")}" placeholder="RM owner" /></label>
      <label>Stage
        <select name="stage">
          ${["new", "qualification", "discovery", "proposal", "active", "monitoring"].map((value) => `<option value="${value}" ${workflow.stage === value ? "selected" : ""}>${value}</option>`).join("")}
        </select>
      </label>
      <label>Status <input name="status" value="${escapeHtml(workflow.status || "open")}" /></label>
      <label>Review status <input name="review_status" value="${escapeHtml(workflow.review_status || "not_reviewed")}" /></label>
      <label>Next action <input name="next_action" value="${escapeHtml(workflow.next_action || "")}" /></label>
      <label>Notes <textarea name="notes">${escapeHtml(workflow.notes || "")}</textarea></label>
      <button class="button primary full" type="submit">Save workflow</button>
    </form>
  `;
}

function renderCopilotPanel() {
  const prospects = asList(state.data.prospects);
  $("#floating-copilot")?.classList.toggle("hidden", state.copilotOpen);
  const promptCards = [
    { icon: "sparkles", label: "Priority explanation", prompt: "Why is this company high priority?" },
    { icon: "trending", label: "Recent changes", prompt: "What changed recently?" },
    { icon: "users", label: "Meeting prep", prompt: "What should I say in the first meeting?" },
    { icon: "file", label: "Product recommendations", prompt: "What products should I pitch first?" },
    { icon: "globe", label: "Signal summary", prompt: "Summarize the most relevant signals" },
  ];

  copilotRoot.innerHTML = `
    <div class="copilot-backdrop ${state.copilotOpen ? "open" : ""}" data-close-copilot></div>
    <aside class="copilot-panel ${state.copilotOpen ? "open" : ""}" aria-hidden="${state.copilotOpen ? "false" : "true"}">
      <div class="copilot-panel-header">
        <div class="copilot-title-mark">${icon("sparkles")}</div>
        <div>
          <h2>AI Copilot</h2>
          <p>Intelligence assistant</p>
        </div>
        <button class="icon-button" data-close-copilot aria-label="Close AI Copilot">${icon("x")}</button>
      </div>
      <div class="copilot-panel-body">
        ${state.chat.length ? `
          <div class="copilot-messages">
            ${state.chat.map((msg) => `
              <div class="message ${msg.role}">
                ${msg.role === "assistant" ? `<div class="message-label">${icon("sparkles")} <span>AI Copilot</span></div>` : ""}
                ${escapeHtml(msg.content)}
              </div>
            `).join("")}
          </div>
        ` : `
          <div class="copilot-empty">
            <div class="copilot-empty-icon">${icon("sparkles")}</div>
            <h3>Ask AI Copilot</h3>
            <p>Get insights based on the signals and prospects shown on your dashboard.</p>
            <div class="copilot-prompt-list">
              ${promptCards.map((item) => `
                <button class="copilot-prompt-card" data-quick-prompt="${escapeHtml(item.prompt)}">
                  <span>${icon(item.icon)}</span>
                  ${escapeHtml(item.label)}
                </button>
              `).join("")}
            </div>
          </div>
        `}
      </div>
      <div class="copilot-panel-footer">
        <form class="copilot-inline-form" id="copilot-form">
          <select id="copilot-prospect" aria-label="Copilot prospect scope">
            <option value="">General portfolio question</option>
            ${prospects.map((p) => `<option value="${escapeHtml(prospectId(p))}" ${state.selectedProspectId === prospectId(p) ? "selected" : ""}>${escapeHtml(prospectName(p))}</option>`).join("")}
          </select>
          <div class="copilot-input-row">
            <input id="copilot-question" placeholder="Ask about signals, prospects, or meeting prep..." autocomplete="off" />
            <button class="button primary" type="submit" aria-label="Send Copilot question">${icon("send", "button-icon")}</button>
          </div>
        </form>
        <p>Responses are evidence-grounded where the backend returns citations. Verify before use.</p>
      </div>
    </aside>
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
    overview: ["Prospecting Intelligence", "Company-first intelligence with engagement angles"],
    prospects: ["Priority Prospects", "Evidence-backed company opportunities for RM review."],
    signals: ["Trigger Signals", "Market, policy, financing, and risk signals linked to companies."],
    companies: ["Companies", "Company fact layer, profile coverage, and linked activity."],
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
  else if (state.route === "detail") content.innerHTML = renderDetail();
  else content.innerHTML = renderOverview();

  renderCopilotPanel();
}

function renderModeBanner() {
  if (state.backendOnline) {
    return `<div class="mode-banner"><span class="badge high">Live API</span><span class="muted">Connected to ${escapeHtml(cleanBase(state.apiBase))}</span></div>`;
  }
  return `<div class="mode-banner"><span class="badge medium">Sample data</span><span class="muted">Start the FastAPI backend or set a shared API base URL to connect live data.</span></div>`;
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
  state.copilotOpen = true;
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
  if (event.target.closest("[data-open-copilot]")) {
    state.copilotOpen = true;
    render();
    return;
  }

  if (event.target.closest("[data-close-copilot]")) {
    state.copilotOpen = false;
    render();
    return;
  }

  const summaryFilter = event.target.closest("[data-summary-filter]");
  if (summaryFilter) {
    const value = summaryFilter.dataset.summaryFilter;
    state.route = "overview";
    state.search = "";
    if (value === "all") {
      state.priorityFilter = "all";
      state.industryFilter = "all";
      state.regionFilter = "all";
      state.signalTypeFilter = "all";
    } else if (value === "high") {
      setOverviewFilter("priority", "high");
    } else if (value === "crossborder") {
      setOverviewFilter("signal", "Cross-border");
    } else if (value === "financing") {
      setOverviewFilter("signal", "Financing");
    }
    setHash("overview");
    render();
    document.querySelector("#prospect-filter-anchor")?.scrollIntoView({ behavior: "smooth", block: "start" });
    return;
  }

  const chartFilter = event.target.closest("[data-chart-filter]");
  if (chartFilter) {
    const type = chartFilter.dataset.chartFilter;
    const value = chartFilter.dataset.filterValue;
    const current = type === "industry"
      ? state.industryFilter
      : type === "region"
        ? state.regionFilter
        : state.signalTypeFilter;
    setOverviewFilter(type, current === value ? "all" : value);
    render();
    document.querySelector("#prospect-filter-anchor")?.scrollIntoView({ behavior: "smooth", block: "start" });
    return;
  }

  const clearFilter = event.target.closest("[data-clear-filter]");
  if (clearFilter) {
    setOverviewFilter(clearFilter.dataset.clearFilter, "all");
    render();
    return;
  }

  const routeButton = event.target.closest("[data-route]");
  if (routeButton) {
    state.route = routeButton.dataset.route;
    state.selectedProspectId = null;
    state.search = "";
    if (state.route !== "overview") {
      state.priorityFilter = "all";
    }
    setHash(state.route);
    render();
    return;
  }

  const signalChip = event.target.closest("[data-signal-chip]");
  if (signalChip) {
    state.signalTypeFilter = signalChip.dataset.signalChip;
    render();
    return;
  }

  const openButton = event.target.closest("[data-open-prospect]");
  if (openButton) {
    openProspect(openButton.dataset.openProspect);
    return;
  }

  const signalAsk = event.target.closest("[data-ask-signal]");
  if (signalAsk) {
    state.copilotOpen = true;
    state.chat = [];
    askCopilot(`Explain this signal for an RM and suggest the next action: ${signalAsk.dataset.askSignal}`, state.selectedProspectId);
    return;
  }

  const prospectAsk = event.target.closest("[data-copilot-prospect]");
  if (prospectAsk) {
    state.selectedProspectId = prospectAsk.dataset.copilotProspect;
    state.copilotOpen = true;
    render();
    return;
  }

  const scrollTarget = event.target.closest("[data-scroll-target]");
  if (scrollTarget) {
    document.getElementById(scrollTarget.dataset.scrollTarget)?.scrollIntoView({ behavior: "smooth", block: "start" });
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
    state.priorityFilter = "all";
    render();
  }
});

loadData();
