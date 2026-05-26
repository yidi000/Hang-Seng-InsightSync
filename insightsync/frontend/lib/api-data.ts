"use client";

import { useEffect, useState } from "react";
import { getJson, putJson } from "@/lib/api-client";
import {
  dashboardStats as mockDashboardStats,
  marketOverview as mockMarketOverview,
  prospects as mockProspects,
  triggerSignals as mockTriggerSignals,
  type Prospect,
  type TriggerSignal,
} from "@/lib/mock-data";

type DashboardStats = typeof mockDashboardStats;
type MarketOverview = typeof mockMarketOverview;

export interface BackendWorkflowState {
  prospect_id: string;
  company_id: string;
  owner?: string | null;
  stage?: string | null;
  status?: string | null;
  review_status?: string | null;
  last_action?: string | null;
  next_action?: string | null;
  notes?: string | null;
  updated_at?: string | null;
}

interface BackendLinkageQuality {
  linked_evidence_count?: number;
  scoreable_evidence_count?: number;
  direct_evidence_count?: number;
  strong_linkage_count?: number;
  context_only_count?: number;
  direct_evidence_ratio?: number;
  scoreable_evidence_ratio?: number;
  context_only_evidence_count?: number;
  linkage_type_counts?: Record<string, number>;
}

interface BackendScoreBreakdown {
  scorecard_version?: string;
  scoring_method?: string;
  calibration_status?: string;
  llm_score_assignment?: string;
  priority_formula?: string;
  score_inputs?: Record<string, number>;
  opportunity_components?: {
    name: string;
    category: string;
    points: number;
    detail: string;
  }[];
  risk_components?: {
    name: string;
    category: string;
    points: number;
    detail: string;
  }[];
  priority_components?: {
    name: string;
    category: string;
    points: number;
    detail: string;
  }[];
  linkage_quality?: BackendLinkageQuality;
  governance_flags?: {
    flag_key: string;
    severity: string;
    area: string;
    message: string;
    suggested_action: string;
  }[];
}

export interface BackendProspectSummary {
  prospect_id: string;
  company_id: string;
  canonical_name: string;
  display_name?: string | null;
  city?: string | null;
  priority_level: "high" | "medium" | "monitor" | string;
  priority_score: number;
  opportunity_score?: number;
  risk_score?: number;
  evidence_confidence_score?: number;
  region?: string | null;
  industries?: string[];
  segments?: string[];
  focus_tags?: string[];
  why_prioritized?: string[];
  recommended_next_step?: string | null;
  recommended_product_themes?: string[];
  recommended_entry_angles?: string[];
  decision_answers?: {
    question_key: string;
    question: string;
    answer: string;
    supporting_evidence?: string[];
  }[];
  score_breakdown?: BackendScoreBreakdown;
  workflow_state?: BackendWorkflowState;
}

export interface BackendSignal {
  id: string | number;
  signal_id?: string | number;
  company_id?: string | null;
  prospect_id?: string | null;
  signal_type?: string;
  source?: string;
  dataset?: string;
  title?: string;
  event_time?: string;
  entity?: string;
  signal_text?: string;
  value_text?: string;
  signal_level?: string;
  evidence_refs?: string[];
}

interface BackendDashboardSummary {
  lead_pool?: number;
  high_priority?: number;
  cross_border?: number;
  financing_signals?: number;
}

interface BackendMarketOverview {
  industry_breakdown?: { name: string; count: number }[];
  region_breakdown?: { name: string; count: number }[];
  company_size_breakdown?: { name: string; count: number }[];
}

interface InsightSyncData {
  prospects: Prospect[];
  triggerSignals: TriggerSignal[];
  marketOverview: MarketOverview;
  dashboardStats: DashboardStats;
  loading: boolean;
  backendOnline: boolean;
  error: string | null;
}

export interface WorkflowUpdateInput {
  owner?: string | null;
  stage?: string;
  status?: string;
  last_action?: string | null;
  next_action?: string | null;
  review_status?: string;
  notes?: string | null;
}

const defaultData: InsightSyncData = {
  prospects: mockProspects,
  triggerSignals: mockTriggerSignals,
  marketOverview: mockMarketOverview,
  dashboardStats: mockDashboardStats,
  loading: true,
  backendOnline: false,
  error: null,
};

function tierFromPriority(priority: BackendProspectSummary["priority_level"]): Prospect["tier"] {
  if (priority === "high") return "A";
  if (priority === "medium") return "B";
  return "C";
}

function parseRawIndicatorText(value?: string | null) {
  const match = (value || "").trim().match(/^([a-z0-9_]+):\s*([+-]?\d+(?:\.\d+)?)$/i);
  if (!match) return null;
  return {
    key: match[1].toLowerCase(),
    value: match[2],
  };
}

function indicatorLabel(key: string) {
  const labels: Record<string, string> = {
    neeri_2020_trade_wgt: "NEERI trade-weighted index",
    neeri_2020_import_wgt: "NEERI import-weighted index",
    neeri_2020_export_wgt: "NEERI export-weighted index",
    zar: "South African rand FX reference",
    idr: "Indonesian rupiah FX reference",
    inr: "Indian rupee FX reference",
    usd: "US dollar FX reference",
    eur: "Euro FX reference",
    cny: "Renminbi FX reference",
    jpy: "Japanese yen FX reference",
    gbp: "British pound FX reference",
    aud: "Australian dollar FX reference",
    cad: "Canadian dollar FX reference",
    sgd: "Singapore dollar FX reference",
  };
  return labels[key] || titleCase(key);
}

function signalType(type?: string, item?: BackendSignal): TriggerSignal["type"] {
  const rawIndicator = parseRawIndicatorText(item?.title || item?.signal_text || item?.value_text);
  if (rawIndicator && normalizeSource(item?.source) === "hkma") return "crossborder";
  if (type === "financing" || type === "funding") return "funding";
  if (type === "policy") return "policy";
  if (type === "cross_border" || type === "crossborder") return "crossborder";
  return "expansion";
}

function isOperationalCompanyProfile(name: string) {
  const normalized = name.toLowerCase();
  return ![
    "portfolio",
    "intelligence profile",
    "cluster",
    "sector",
    "national accounts",
  ].some((term) => normalized.includes(term));
}

function titleCase(value: string) {
  return value
    .replace(/[_-]/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function normalizeSource(source: string | undefined) {
  return (source || "").toLowerCase().replace(/[^a-z0-9]/g, "");
}

function signalDisplayText(item: BackendSignal) {
  const rawText = item.title || item.signal_text || item.value_text;
  const rawIndicator = parseRawIndicatorText(rawText);
  if (rawIndicator) {
    const label = indicatorLabel(rawIndicator.key);
    const isMarketIndicator = normalizeSource(item.source) === "hkma";
    return {
      title: `${label} updated`,
      summary: isMarketIndicator
        ? `HKMA reported ${label} at ${rawIndicator.value}. Use this as market context for clients with relevant FX or cross-border exposure.`
        : `${label}: ${rawIndicator.value}`,
    };
  }

  return {
    title: item.title || item.signal_text || "Backend signal",
    summary:
      item.signal_text ||
      item.value_text ||
      `${item.source || "InsightSync"} ${item.signal_level || "signal"}`,
  };
}

function businessBackgroundFallback(item: BackendProspectSummary, companyName: string) {
  const industry = titleCase(item.industries?.[0] || "commercial banking");
  const region = item.region || "Hong Kong / GBA";
  const themes = item.recommended_product_themes?.slice(0, 3).join(", ");
  return `${companyName} is a ${industry.toLowerCase()} company operating in ${region}. The brief highlights current client conversation themes and likely banking needs${themes ? ` around ${themes}` : ""}.`;
}

function meaningfulRecommendedStep(value?: string | null) {
  const text = (value || "").trim();
  if (!text) return undefined;
  const normalized = text.toLowerCase().replace(/\.$/, "");
  if (/^review .+ angle and validate the linked evidence$/.test(normalized)) {
    return undefined;
  }
  if (
    [
      "review linked evidence",
      "review linked evidence before outreach",
      "review linked evidence and prepare rm follow-up",
    ].includes(normalized)
  ) {
    return undefined;
  }
  return text;
}

function mapWorkflowState(item?: BackendWorkflowState): Prospect["workflowState"] {
  if (!item) return undefined;
  return {
    owner: item.owner,
    stage: item.stage,
    status: item.status,
    reviewStatus: item.review_status,
    lastAction: item.last_action,
    nextAction: item.next_action,
    notes: item.notes,
  };
}

export function mapProspect(item: BackendProspectSummary): Prospect {
  const companyName = item.display_name || item.canonical_name || item.company_id;
  const industry = item.industries?.[0] || "Market Intelligence";
  const scoreInputs = item.score_breakdown?.score_inputs;
  const linkageQuality = item.score_breakdown?.linkage_quality;
  const recommendedNextStep = meaningfulRecommendedStep(item.recommended_next_step);

  return {
    id: item.prospect_id,
    name: companyName,
    nameZh: item.canonical_name || item.company_id,
    score: item.priority_score || 0,
    tier: tierFromPriority(item.priority_level),
    priorityLevel: item.priority_level,
    opportunityScore: item.opportunity_score,
    riskScore: item.risk_score,
    evidenceConfidenceScore: item.evidence_confidence_score,
    scorecardVersion: item.score_breakdown?.scorecard_version,
    calibrationStatus: item.score_breakdown?.calibration_status,
    industry: titleCase(industry),
    region: item.region || "Hong Kong / GBA",
    focusTags: item.focus_tags,
    engagementAngles: item.recommended_entry_angles?.map((label, index) => ({
      label,
      tag: item.focus_tags?.[index] || "signal",
      recommendedTalkTrack: recommendedNextStep || label,
    })),
    whyPrioritized: item.why_prioritized,
    recommendedNextStep,
    scoreBreakdown: scoreInputs,
    linkageQuality: linkageQuality
      ? {
          directEvidenceRatio: linkageQuality.direct_evidence_ratio,
          scoreableEvidenceRatio: linkageQuality.scoreable_evidence_ratio,
          contextOnlyEvidenceCount:
            linkageQuality.context_only_evidence_count ??
            linkageQuality.context_only_count,
          linkageTypeCounts: linkageQuality.linkage_type_counts,
        }
      : undefined,
    workflowState: mapWorkflowState(item.workflow_state),
    productFit: item.recommended_product_themes?.length
      ? item.recommended_product_themes
      : ["Corporate Banking", "Cross-border Banking"],
    entryAngle:
      recommendedNextStep ||
      item.why_prioritized?.join("; ") ||
      "Review evidence and prepare outreach note.",
    revenue: `Opportunity ${item.opportunity_score ?? "--"}`,
    employees: "Signals available",
    founded: "2026",
    description: businessBackgroundFallback(item, companyName),
    businessModel: scoreInputs
      ? Object.entries(scoreInputs)
          .map(([key, value]) => `${titleCase(key)}: ${value}`)
          .join("; ")
      : "Backend scorecard fields are available for audit.",
    expansionSignals: item.why_prioritized?.length
      ? item.why_prioritized
      : ["Backend evidence profile available"],
    crossBorderFootprint: [item.region || "Hong Kong / GBA"],
    news: [],
    bankingNeeds: item.recommended_product_themes?.length
      ? item.recommended_product_themes
      : ["Review financing and liquidity needs"],
    opportunities: (item.recommended_product_themes?.length
      ? item.recommended_product_themes
      : ["Corporate Banking"]
    ).map((product) => ({
      product,
      potential: `Score ${item.opportunity_score ?? item.priority_score}`,
      rationale:
        recommendedNextStep ||
        "Recommended by backend prioritization and evidence linkage.",
    })),
  };
}

function mapSignal(item: BackendSignal, prospectById: Map<string, Prospect>): TriggerSignal {
  const prospect = item.prospect_id ? prospectById.get(item.prospect_id) : undefined;
  const displayText = signalDisplayText(item);
  return {
    id: String(item.signal_id || item.id),
    type: signalType(item.signal_type, item),
    title: displayText.title,
    company: prospect?.name || item.entity || item.company_id || "Market portfolio",
    date: item.event_time || new Date().toISOString(),
    summary: displayText.summary,
    source: item.source,
    dataset: item.dataset,
    signalLevel: item.signal_level,
    prospectId: item.prospect_id || undefined,
    evidenceRefs: item.evidence_refs,
  };
}

function mapMarketOverview(data: BackendMarketOverview): MarketOverview {
  return {
    industryDistribution:
      data.industry_breakdown?.map((item) => ({
        name: titleCase(item.name),
        value: item.count,
      })) || mockMarketOverview.industryDistribution,
    regionDistribution:
      data.region_breakdown?.map((item) => ({
        name: item.name,
        value: item.count,
      })) || mockMarketOverview.regionDistribution,
    companySizeDistribution:
      data.company_size_breakdown?.map((item) => ({
        name: item.name,
        value: item.count,
      })) || mockMarketOverview.companySizeDistribution,
  };
}

function mapDashboardStats(data: BackendDashboardSummary): DashboardStats {
  return {
    leadPoolSize: data.lead_pool ?? mockDashboardStats.leadPoolSize,
    highPriorityProspects:
      data.high_priority ?? mockDashboardStats.highPriorityProspects,
    crossBorderOpportunities:
      data.cross_border ?? mockDashboardStats.crossBorderOpportunities,
    financingSignals: data.financing_signals ?? mockDashboardStats.financingSignals,
  };
}

export function updateProspectWorkflow(prospectId: string, body: WorkflowUpdateInput) {
  return putJson<BackendWorkflowState, WorkflowUpdateInput>(
    `/api/prospects/${encodeURIComponent(prospectId)}/workflow`,
    body
  );
}

export function useInsightSyncData(): InsightSyncData {
  const [data, setData] = useState<InsightSyncData>(defaultData);

  useEffect(() => {
    let isMounted = true;

    async function load() {
      try {
        const [prospectsResponse, signalsResponse, summary, market] = await Promise.all([
          getJson<{ items: BackendProspectSummary[] }>("/api/prospects?limit=100"),
          getJson<{ items: BackendSignal[] }>("/api/signals?limit=100"),
          getJson<BackendDashboardSummary>("/api/dashboard/summary"),
          getJson<BackendMarketOverview>("/api/dashboard/market-overview"),
        ]);

        const prospects = prospectsResponse.items
          .map(mapProspect)
          .filter((prospect) => isOperationalCompanyProfile(prospect.name));
        const prospectById = new Map(prospects.map((prospect) => [prospect.id, prospect]));
        const triggerSignals = signalsResponse.items
          .map((signal) => mapSignal(signal, prospectById))
          .slice(0, 100);

        if (isMounted) {
          setData({
            prospects,
            triggerSignals,
            marketOverview: mapMarketOverview(market),
            dashboardStats: mapDashboardStats(summary),
            loading: false,
            backendOnline: true,
            error: null,
          });
        }
      } catch (error) {
        if (isMounted) {
          setData({
            ...defaultData,
            loading: false,
            error:
              error instanceof Error
                ? error.message
                : "Unable to load InsightSync backend",
          });
        }
      }
    }

    load();

    return () => {
      isMounted = false;
    };
  }, []);

  return data;
}
