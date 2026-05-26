"use client";

import { useEffect, useState } from "react";
import { getJson } from "@/lib/api-client";
import {
  mapProspect,
  type BackendProspectSummary,
  type BackendSignal,
  type BackendWorkflowState,
} from "@/lib/api-data";
import type { Prospect } from "@/lib/mock-data";

export interface BackendCompanyProfile {
  source: string;
  company_id: string;
  canonical_name: string;
  display_name?: string | null;
  country?: string | null;
  region?: string | null;
  city?: string | null;
  segments?: string[];
  industries?: string[];
  website_url?: string | null;
  profile_summary?: string | null;
  description?: string | null;
  updated_at?: string;
}

export interface BackendCoverageFlags {
  has_recent_signals?: boolean;
  has_recent_timeline?: boolean;
  has_generated_insights?: boolean;
  has_parsed_reports?: boolean;
  has_management_discussion?: boolean;
  has_structured_metrics?: boolean;
  has_risk_factors?: boolean;
  has_business_events?: boolean;
  has_ocr_support?: boolean;
  has_xbrl_support?: boolean;
}

export interface BackendEvidenceSummary {
  parsed_document_count?: number;
  parsed_document_success_count?: number;
  parsed_document_partial_count?: number;
  parsed_document_failed_count?: number;
  ocr_hit_count?: number;
  xbrl_hit_count?: number;
  management_discussion_count?: number;
  metric_count?: number;
  risk_factor_count?: number;
  business_event_count?: number;
  last_parsed_at?: string | null;
}

export interface BackendDecisionAnswer {
  question_key: string;
  question: string;
  answer: string;
  supporting_evidence?: string[];
}

export interface BackendParsedDocument {
  id: number;
  source: string;
  dataset?: string | null;
  title?: string | null;
  summary?: string | null;
  media_type?: string | null;
  lang?: string | null;
  parser_name: string;
  backend_name?: string | null;
  parse_status: string;
  management_discussion_summary?: string | null;
  section_count?: number;
  table_count?: number;
  metric_count?: number;
  risk_factor_count?: number;
  business_event_count?: number;
  evidence_url?: string | null;
  genai_extraction?: {
    status?: string | null;
    prompt_version?: string | null;
    candidate_count?: number;
    accepted_count?: number;
    rejected_count?: number;
    scoring_eligible_counts?: Record<string, number>;
    context_only_count?: number;
    rejected_reason_counts?: Record<string, number>;
  } | null;
  parsed_at: string;
}

export interface BackendMetric {
  document_id: number;
  title?: string | null;
  name: string;
  value: string;
  unit?: string | null;
  period?: string | null;
  context?: string | null;
  confidence?: number | null;
  parsed_at: string;
}

export interface BackendRiskFactor {
  document_id: number;
  title?: string | null;
  category: string;
  description: string;
  severity: string;
  confidence?: number | null;
  parsed_at: string;
}

export interface BackendBusinessEvent {
  document_id: number;
  title?: string | null;
  event_type: string;
  summary: string;
  event_date?: string | null;
  confidence?: number | null;
  parsed_at: string;
}

export interface BackendTimelineEvent {
  id: number;
  source: string;
  company_id?: string | null;
  entity?: string | null;
  event_time?: string | null;
  event_type: string;
  headline: string;
  detail?: string | null;
  evidence_url?: string | null;
  payload?: Record<string, unknown> | null;
}

export interface BackendGeneratedInsight {
  id: number;
  source: string;
  insight_type: string;
  title: string;
  summary: string;
  confidence?: number | null;
  model_name?: string | null;
  prompt_version?: string | null;
  generated_at: string;
}

export interface BackendProductFit {
  product_name: string;
  fit_score: number;
  rationale: string;
  supporting_signals?: string[];
}

export interface BackendLatestState {
  activity_at?: string | null;
  status: string;
  state_summary?: string | null;
  why_now?: string | null;
  fusion?: {
    summary?: string | null;
    why_now?: string | null;
    primary_opportunity?: string | null;
    key_risk?: string | null;
    decision_answers?: BackendDecisionAnswer[];
  } | null;
  fusion_summary?: string | null;
  recommended_next_step?: string | null;
  commercial_attractiveness_score?: number;
  immediacy_score?: number;
  product_fit_score?: number;
  risk_penalty_score?: number;
  evidence_confidence_score?: number;
  focus_tags?: string[];
  signal_highlights?: string[];
  product_fit?: BackendProductFit[];
  recommended_entry_angles?: string[];
  decision_answers?: BackendDecisionAnswer[];
  coverage_flags: BackendCoverageFlags;
  evidence_summary: BackendEvidenceSummary;
}

export interface BackendProspectDetail {
  prospect: BackendProspectSummary;
  workflow_state: BackendWorkflowState;
  company: BackendCompanyProfile;
  latest_state: BackendLatestState;
  recent_signals?: BackendSignal[];
  recent_timeline?: BackendTimelineEvent[];
  recent_insights?: BackendGeneratedInsight[];
  recent_documents?: BackendParsedDocument[];
  key_metrics?: BackendMetric[];
  key_risk_factors?: BackendRiskFactor[];
  key_business_events?: BackendBusinessEvent[];
}

export interface BackendProspectBrief {
  prospect_id: string;
  company_id: string;
  title: string;
  summary: string;
  priority_level: string;
  recommended_next_step?: string | null;
  recommended_product_themes?: string[];
  recommended_entry_angles?: string[];
  top_opportunities?: string[];
  top_risks?: string[];
  evidence_highlights?: string[];
  fusion_explanation?: Record<string, unknown> | null;
  decision_answers?: BackendDecisionAnswer[];
}

export interface BackendProspectEvidence {
  prospect_id: string;
  company_id: string;
  coverage_flags: BackendCoverageFlags;
  evidence_summary: BackendEvidenceSummary;
  recent_documents?: BackendParsedDocument[];
  key_metrics?: BackendMetric[];
  key_risk_factors?: BackendRiskFactor[];
  key_business_events?: BackendBusinessEvent[];
}

export interface BackendProspectCopilot {
  suggested_questions?: string[];
}

interface ProspectDetailState {
  mappedProspect?: Prospect;
  detail?: BackendProspectDetail;
  brief?: BackendProspectBrief;
  evidence?: BackendProspectEvidence;
  copilot?: BackendProspectCopilot;
  loading: boolean;
  error: string | null;
  partialErrors: Record<string, string>;
}

const initialState: ProspectDetailState = {
  loading: true,
  error: null,
  partialErrors: {},
};

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Request failed";
}

export function useProspectDetail(prospectId: string | null): ProspectDetailState {
  const [state, setState] = useState<ProspectDetailState>(initialState);

  useEffect(() => {
    if (!prospectId) {
      return;
    }

    let isMounted = true;
    if (/^p\d+$/i.test(prospectId)) {
      const timer = window.setTimeout(() => {
        setState({
          ...initialState,
          loading: false,
          error: null,
        });
      }, 0);
      return () => window.clearTimeout(timer);
    }

    const encodedId = encodeURIComponent(prospectId);

    async function load() {
      setState((current) => ({ ...current, loading: true, error: null }));

      const [detailResult, briefResult, evidenceResult] =
        await Promise.allSettled([
          getJson<BackendProspectDetail>(`/api/prospects/${encodedId}`),
          getJson<BackendProspectBrief>(`/api/prospects/${encodedId}/brief`),
          getJson<BackendProspectEvidence>(`/api/prospects/${encodedId}/evidence`),
        ]);

      if (!isMounted) return;

      const partialErrors: Record<string, string> = {};
      const detail =
        detailResult.status === "fulfilled"
          ? detailResult.value
          : (partialErrors.detail = errorMessage(detailResult.reason), undefined);
      const brief =
        briefResult.status === "fulfilled"
          ? briefResult.value
          : (partialErrors.brief = errorMessage(briefResult.reason), undefined);
      const evidence =
        evidenceResult.status === "fulfilled"
          ? evidenceResult.value
          : (partialErrors.evidence = errorMessage(evidenceResult.reason), undefined);

      setState({
        mappedProspect: detail?.prospect ? mapProspect(detail.prospect) : undefined,
        detail,
        brief,
        evidence,
        loading: false,
        error: detail ? null : partialErrors.detail || "Unable to load prospect detail",
        partialErrors,
      });
    }

    load();

    return () => {
      isMounted = false;
    };
  }, [prospectId]);

  return state;
}
