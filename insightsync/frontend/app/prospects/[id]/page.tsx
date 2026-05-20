"use client";

import { use, useState } from "react";
import {
  ArrowLeft,
  Building2,
  Calendar,
  CheckCircle2,
  ClipboardCheck,
  Edit3,
  ExternalLink,
  FileText,
  Globe,
  MapPin,
  Sparkles,
  Target,
  TrendingUp,
  Users,
  X,
} from "lucide-react";
import Link from "next/link";
import { AppSidebar } from "@/components/app-sidebar";
import {
  AICopilotButton,
  AICopilotPanel,
} from "@/components/ai-copilot-panel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  updateProspectWorkflow,
  useInsightSyncData,
  type BackendWorkflowState,
} from "@/lib/api-data";
import { useProspectDetail } from "@/lib/prospect-detail-data";

const priorityBandColors: Record<string, string> = {
  A: "bg-primary text-primary-foreground",
  B: "bg-chart-2 text-white",
  C: "bg-muted text-muted-foreground",
};

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-HK", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function formatShortDate(dateStr?: string | null): string {
  if (!dateStr) return "To schedule";
  return new Date(dateStr).toLocaleDateString("en-HK", {
    month: "short",
    day: "numeric",
  });
}

function formatLabel(value: string): string {
  return value
    .replace(/[_-]/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatSource(source: string | undefined) {
  if (!source) return "InsightSync";
  if (source.toLowerCase() === "hkma") return "HKMA";
  return source
    .replace(/[_-]/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function normalizeEntityName(value: string | undefined) {
  return (value || "").toLowerCase().replace(/[^a-z0-9]/g, "");
}

function isReadableEvidenceTitle(value: string | undefined) {
  const title = (value || "").trim();
  if (!title) return false;
  if (/^-?\d+(\.\d+)?$/.test(title)) return false;
  if (/^[a-z]{2,}[_-]\d|[_-](wgt|rate|ratio|index|idr|inr|zar)/i.test(title)) {
    return false;
  }
  return true;
}

function cleanEvidenceSummary(summary: string | undefined, title: string) {
  const cleaned = (summary || "").replace(/^title:\s*/i, "").trim();
  if (!cleaned || cleaned === title) return "";
  return cleaned;
}

function isRawFilingCategoryCode(value?: string | null) {
  return /^\d{6,}(\|\|\d{3,})+$/.test((value || "").trim());
}

function cleanDocumentSummary(
  summary?: string | null,
  title?: string | null,
  managementSummary?: string | null
) {
  const candidates = [summary, managementSummary]
    .map((value) => (value || "").replace(/^title:\s*/i, "").trim())
    .filter(Boolean);
  const normalizedTitle = (title || "").trim();
  const meaningful = candidates.find(
    (value) => value !== normalizedTitle && !isRawFilingCategoryCode(value)
  );
  return meaningful || "";
}

function formatEvidenceSource(source?: string | null) {
  const normalized = (source || "").toLowerCase();
  if (normalized === "szse_cninfo") return "SZSE filing";
  if (normalized === "hkma") return "HKMA";
  return formatSource(source || undefined);
}

function formatEvidenceLanguage(lang?: string | null) {
  const normalized = (lang || "").toLowerCase();
  if (["zh", "zho", "cn", "zh-cn"].includes(normalized)) return "Chinese";
  if (["zh-hk", "zh-tw", "tc", "traditional_chinese"].includes(normalized)) {
    return "Traditional Chinese";
  }
  if (["yue", "cantonese"].includes(normalized)) return "Cantonese";
  if (normalized === "en") return "English";
  return lang || "Language unknown";
}

function evidenceExplorerHref(title: string) {
  return `/signals?search=${encodeURIComponent(title)}`;
}

function formatNumber(value?: number | null): string {
  if (typeof value !== "number") return "0";
  return value.toLocaleString("en-HK");
}

function formatRatio(value?: number | null): string {
  if (typeof value !== "number") return "N/A";
  return `${Math.round(value * 100)}%`;
}

function scoreSeverityClass(severity?: string | null) {
  if (severity === "high") return "border-destructive/30 bg-destructive/10 text-destructive";
  if (severity === "medium") return "border-chart-4/30 bg-chart-4/10 text-chart-4";
  return "border-border bg-muted/40 text-muted-foreground";
}

function priorityBandLabel(prospect: { priorityLevel?: string; tier: string }) {
  if (prospect.priorityLevel === "high" || prospect.tier === "A") return "High";
  if (prospect.priorityLevel === "medium" || prospect.tier === "B") return "Medium";
  return "Low";
}

function scoreBand(score: number, kind: "opportunity" | "risk" | "confidence" | "priority") {
  if (kind === "risk") {
    if (score <= 10) return "Low friction";
    if (score <= 35) return "Manageable risk";
    return "Elevated risk";
  }
  if (kind === "priority") {
    if (score >= 50) return "High";
    if (score >= 38) return "Medium";
    return "Low";
  }
  if (score >= 70) return "Strong";
  if (score >= 40) return "Moderate";
  if (score > 0) return "Early signal";
  return "No clear signal";
}

function scoreNarrative(
  kind: "opportunity" | "risk" | "confidence" | "priority",
  score: number
) {
  if (kind === "opportunity") {
    if (score >= 70) {
      return "Strong business opening supported by multiple commercial signals.";
    }
    if (score >= 40) {
      return "Meaningful business opening, but more evidence or a sharper product angle would strengthen prioritization.";
    }
    if (score > 0) {
      return "Early opportunity signal. The company is visible, but the business angle is still developing.";
    }
    return "No clear opportunity signal has been detected from linked evidence yet.";
  }

  if (kind === "risk") {
    if (score <= 10) {
      return "No material risk friction is visible in the linked evidence. This does not by itself make the lead high priority.";
    }
    if (score <= 35) {
      return "Some risk friction is present, so RM outreach should include a focused review of the flagged issues.";
    }
    return "Risk evidence may constrain outreach and should be reviewed before prioritizing this company.";
  }

  if (kind === "confidence") {
    if (score >= 70) {
      return "Evidence is strong enough to support confident triage and follow-up planning.";
    }
    if (score >= 40) {
      return "Evidence is usable, but more diverse or structured support would make the recommendation stronger.";
    }
    if (score > 0) {
      return "Evidence support is thin. Treat the recommendation as a lead to inspect, not a firm conclusion.";
    }
    return "No reliable evidence support is available for scoring yet.";
  }

  if (score >= 50) {
    return "Ranked High because business opportunity and evidence support are strong enough after risk adjustment.";
  }
  if (score >= 38) {
    return "Ranked Medium. Worth preparing for outreach, but not yet a top-priority RM action.";
  }
  return "Ranked Low. The current score does not yet justify high-priority outreach.";
}

function priorityComponentLabel(name: string) {
  const labels: Record<string, string> = {
    opportunity_weighted: "Opportunity contribution",
    evidence_confidence_weighted: "Evidence confidence contribution",
    risk_buffer: "Low-risk buffer",
    actionable_status_gate: "Actionability gate",
  };
  return labels[name] || formatLabel(name);
}

function priorityComponentNarrative(name: string, fallback: string) {
  const narratives: Record<string, string> = {
    opportunity_weighted:
      "Business opportunity carries the largest weight in final RM ordering.",
    evidence_confidence_weighted:
      "Evidence quality contributes so weakly supported leads do not rank too high.",
    risk_buffer:
      "Adds limited points when linked risk evidence is low. Low risk alone cannot make a company high priority.",
    actionable_status_gate:
      "Confirms the company can qualify for RM action; it does not add points by itself.",
  };
  return narratives[name] || fallback;
}

function signedPoints(points: number) {
  return points > 0 ? `+${points}` : `${points}`;
}

export default function ProspectDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const decodedId = decodeURIComponent(id);
  const { prospects, triggerSignals, loading } = useInsightSyncData();
  const detailState = useProspectDetail(decodedId);
  const [copilotOpen, setCopilotOpen] = useState(false);
  const [copilotPrompt, setCopilotPrompt] = useState<string | null>(null);
  const [updateOpen, setUpdateOpen] = useState(false);
  const [draftOwner, setDraftOwner] = useState("");
  const [draftStage, setDraftStage] = useState("");
  const [draftStatus, setDraftStatus] = useState("not_reviewed");
  const [draftLastAction, setDraftLastAction] = useState("");
  const [draftNextAction, setDraftNextAction] = useState("");
  const [draftNote, setDraftNote] = useState("");
  const [savedWorkflow, setSavedWorkflow] = useState<BackendWorkflowState | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [savingWorkflow, setSavingWorkflow] = useState(false);

  const summaryProspect = prospects.find((p) => p.id === decodedId);
  const prospect = detailState.mappedProspect || summaryProspect;

  if (!prospect && (loading || detailState.loading)) {
    return (
      <div className="min-h-screen bg-background">
        <AppSidebar />
        <main className="pl-64">
          <div className="flex min-h-screen items-center justify-center">
            <p className="text-sm text-muted-foreground">Loading prospect...</p>
          </div>
        </main>
      </div>
    );
  }

  if (!prospect) {
    return (
      <div className="min-h-screen bg-background">
        <AppSidebar />
        <main className="pl-64">
          <div className="flex min-h-screen items-center justify-center">
            <div className="text-center">
              <h1 className="text-xl font-semibold text-foreground">
                Prospect not found
              </h1>
              <Link href="/prospects">
                <Button className="mt-4">
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  Back to Prospects
                </Button>
              </Link>
            </div>
          </div>
        </main>
      </div>
    );
  }

  const detail = detailState.detail;
  const brief = detailState.brief;
  const evidence = detailState.evidence;
  const backendProspect = detail?.prospect;
  const backendWorkflow = savedWorkflow || detail?.workflow_state;
  const company = detail?.company;
  const scoreBreakdown = backendProspect?.score_breakdown;
  const linkageQuality = scoreBreakdown?.linkage_quality;
  const governanceFlags = scoreBreakdown?.governance_flags || [];
  const coverageFlags = evidence?.coverage_flags || detail?.latest_state.coverage_flags;
  const evidenceSummary = evidence?.evidence_summary || detail?.latest_state.evidence_summary;
  const parsedDocuments = evidence?.recent_documents || detail?.recent_documents || [];
  const keyMetrics = evidence?.key_metrics || detail?.key_metrics || [];
  const keyRiskFactors = evidence?.key_risk_factors || detail?.key_risk_factors || [];
  const keyBusinessEvents = evidence?.key_business_events || detail?.key_business_events || [];
  const productFits = detail?.latest_state.product_fit || [];
  const scoreInputs = scoreBreakdown?.score_inputs || {};
  const auditOpportunityScore =
    scoreInputs.opportunity_score ?? backendProspect?.opportunity_score ?? prospect.opportunityScore ?? 0;
  const auditRiskScore =
    scoreInputs.risk_score ?? backendProspect?.risk_score ?? prospect.riskScore ?? 0;
  const auditEvidenceConfidenceScore =
    scoreInputs.evidence_confidence_score ??
    backendProspect?.evidence_confidence_score ??
    prospect.evidenceConfidenceScore ??
    0;
  const auditPriorityScore =
    scoreInputs.priority_score ?? backendProspect?.priority_score ?? prospect.score ?? 0;
  const auditPriorityBand = scoreBand(auditPriorityScore, "priority");
  const scoreAuditCards = [
    {
      title: "Business Opportunity",
      value: auditOpportunityScore,
      kind: "opportunity" as const,
      description: scoreNarrative("opportunity", auditOpportunityScore),
    },
    {
      title: "Risk Friction",
      value: auditRiskScore,
      kind: "risk" as const,
      description: scoreNarrative("risk", auditRiskScore),
    },
    {
      title: "Evidence Confidence",
      value: auditEvidenceConfidenceScore,
      kind: "confidence" as const,
      description: scoreNarrative("confidence", auditEvidenceConfidenceScore),
    },
    {
      title: "RM Priority",
      value: auditPriorityScore,
      kind: "priority" as const,
      description: scoreNarrative("priority", auditPriorityScore),
    },
  ];
  const scoreDrivers = [
    ...(scoreBreakdown?.opportunity_components || []),
    ...(scoreBreakdown?.risk_components || []),
  ];
  const companyDescription =
    company?.profile_summary ||
    company?.description ||
    detail?.latest_state.state_summary ||
    prospect.description;

  const relatedSignals = triggerSignals
    .filter((signal) => {
      const signalCompany = normalizeEntityName(signal.company);
      return (
        (signal.prospectId === prospect.id ||
          signalCompany === normalizeEntityName(prospect.name) ||
          signalCompany === normalizeEntityName(prospect.nameZh)) &&
        isReadableEvidenceTitle(signal.title)
      );
    })
    .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
  const readableNews = prospect.news
    .filter((item) => isReadableEvidenceTitle(item.title))
    .filter(
      (item) =>
        !relatedSignals.some(
          (signal) =>
            normalizeEntityName(signal.title) === normalizeEntityName(item.title)
        )
    )
    .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
  const viewableEvidenceCount = relatedSignals.length + readableNews.length;
  const primaryConversationFocus =
    prospect.engagementAngles?.[0]?.label ||
    prospect.recommendedNextStep ||
    prospect.entryAngle;
  const currentStage =
    draftStage ||
    backendWorkflow?.stage ||
    prospect.workflowState?.stage ||
    "new";
  const workflowUpdatedAt =
    backendWorkflow?.updated_at || detail?.latest_state.activity_at || null;
  const currentActionStatus =
    draftStatus !== "not_reviewed"
      ? draftStatus
      : backendWorkflow?.review_status ||
        prospect.workflowState?.reviewStatus ||
        "not_reviewed";
  const topDiscussionPoints = (
    prospect.engagementAngles?.length
      ? prospect.engagementAngles
      : prospect.expansionSignals.map((signal) => ({
          label: signal,
          tag: "signal",
          recommendedTalkTrack: signal,
        }))
  ).slice(0, 3);
  const primaryEvidence = relatedSignals[0] || readableNews[0];

  const latestWorkflowNote = backendWorkflow?.notes || prospect.workflowState?.notes;

  const openUpdateDrawer = () => {
    setDraftOwner(backendWorkflow?.owner || prospect.workflowState?.owner || "");
    setDraftStage(backendWorkflow?.stage || prospect.workflowState?.stage || "new");
    setDraftStatus(
      backendWorkflow?.review_status ||
        prospect.workflowState?.reviewStatus ||
        "not_reviewed"
    );
    setDraftLastAction(
      backendWorkflow?.last_action || prospect.workflowState?.lastAction || ""
    );
    setDraftNextAction(
      backendWorkflow?.next_action || prospect.workflowState?.nextAction || ""
    );
    setDraftNote(backendWorkflow?.notes || prospect.workflowState?.notes || "");
    setSaveError(null);
    setUpdateOpen(true);
  };

  const saveRmUpdate = async () => {
    setSavingWorkflow(true);
    setSaveError(null);

    try {
      const workflow = await updateProspectWorkflow(prospect.id, {
        owner: draftOwner.trim() || null,
        stage: draftStage || currentStage,
        status: backendWorkflow?.status || prospect.workflowState?.status || "open",
        last_action: draftLastAction || null,
        next_action:
          draftNextAction ||
          backendWorkflow?.next_action ||
          prospect.workflowState?.nextAction ||
          prospect.recommendedNextStep ||
          null,
        review_status: draftStatus,
        notes: draftNote || null,
      });
      setSavedWorkflow(workflow);
      setUpdateOpen(false);
    } catch (error) {
      setSaveError(
        error instanceof Error ? error.message : "Unable to save workflow update"
      );
    } finally {
      setSavingWorkflow(false);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <AppSidebar />

      <main className="pl-64">
        <header className="sticky top-0 z-40 border-b border-border bg-card">
          <div className="flex h-14 items-center justify-between px-6">
            <div className="flex items-center gap-4">
              <Link href="/prospects">
                <Button variant="ghost" size="sm">
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  Back
                </Button>
              </Link>
              <div>
                <h1 className="text-lg font-semibold text-foreground">
                  Client Action Brief
                </h1>
                <p className="text-xs text-muted-foreground">
                  Pre-meeting summary for {prospect.name}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Button variant="outline" onClick={openUpdateDrawer}>
                <Edit3 className="mr-2 h-4 w-4" />
                Update RM Notes
              </Button>
              <Button
                onClick={() => {
                  setCopilotPrompt(null);
                  setCopilotOpen(true);
                }}
                className="bg-primary hover:bg-primary/90"
              >
                <Sparkles className="mr-2 h-4 w-4" />
                Ask AI Copilot
              </Button>
            </div>
          </div>
        </header>

        <div className="space-y-6 p-6">
          <Card className="border-primary/20 bg-gradient-to-r from-primary/5 via-card to-card">
            <CardContent className="p-6">
              <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
                <div>
                  <div className="mb-3 flex flex-wrap items-center gap-2">
                    <Badge className={priorityBandColors[prospect.tier]}>
                      {priorityBandLabel(prospect)}
                    </Badge>
                    <Badge asChild variant="outline">
                      <Link href="#score-audit">Priority score {prospect.score}</Link>
                    </Badge>
                    <Badge variant="outline" className="capitalize">
                      {formatLabel(currentActionStatus)}
                    </Badge>
                  </div>
                  <h2 className="text-2xl font-bold text-foreground">
                    {prospect.name}
                  </h2>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {prospect.nameZh}
                  </p>
                  <div className="mt-4 flex flex-wrap gap-3 text-sm text-muted-foreground">
                    <span className="flex items-center gap-1.5">
                      <Building2 className="h-4 w-4" />
                      {prospect.industry}
                    </span>
                    <span className="flex items-center gap-1.5">
                      <MapPin className="h-4 w-4" />
                      {prospect.region}
                    </span>
                    <span className="flex items-center gap-1.5">
                      <Users className="h-4 w-4" />
                      Workflow {formatLabel(currentStage)}
                    </span>
                    <span className="flex items-center gap-1.5">
                      <Calendar className="h-4 w-4" />
                      Updated {formatShortDate(workflowUpdatedAt)}
                    </span>
                  </div>
                  <div className="mt-6 rounded-lg border border-primary/20 bg-card p-4">
                    <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-primary">
                      Today&apos;s RM action
                    </p>
                    <p className="text-lg font-semibold text-foreground">
                      {backendWorkflow?.next_action ||
                        prospect.workflowState?.nextAction ||
                        brief?.recommended_next_step ||
                        prospect.recommendedNextStep ||
                        "Review linked evidence and prepare client outreach."}
                    </p>
                    <p className="mt-2 text-sm text-muted-foreground">
                      {brief?.summary ? (
                        brief.summary
                      ) : (
                        <>
                          Start with{" "}
                          <span className="font-medium text-foreground">
                            {primaryConversationFocus}
                          </span>
                          .
                          {primaryEvidence
                            ? ` The strongest current evidence is "${primaryEvidence.title}".`
                            : " No direct evidence is linked yet, so review broader signals before outreach."}
                        </>
                      )}
                    </p>
                  </div>
                </div>

                <div className="grid gap-3">
                  <div className="rounded-lg border border-border bg-card p-4">
                    <p className="text-xs text-muted-foreground">
                      Evidence confidence
                    </p>
                    <p className="mt-1 text-2xl font-semibold text-foreground">
                      {prospect.evidenceConfidenceScore ?? "N/A"}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {formatNumber(evidenceSummary?.parsed_document_count || viewableEvidenceCount)} linked records
                    </p>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="rounded-lg border border-border bg-card p-4">
                      <p className="text-xs text-muted-foreground">Opportunity</p>
                      <p className="mt-1 text-xl font-semibold text-foreground">
                        {backendProspect?.opportunity_score ?? prospect.opportunityScore ?? "N/A"}
                      </p>
                    </div>
                    <div className="rounded-lg border border-border bg-card p-4">
                      <p className="text-xs text-muted-foreground">Risk</p>
                      <p className="mt-1 text-xl font-semibold text-foreground">
                        {backendProspect?.risk_score ?? prospect.riskScore ?? "N/A"}
                      </p>
                    </div>
                  </div>
                  <Button onClick={openUpdateDrawer} className="w-full">
                    <CheckCircle2 className="mr-2 h-4 w-4" />
                    Mark review / add note
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
            <div className="space-y-6">
              {detailState.error && (
                <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
                  {detailState.error}
                </div>
              )}

              <Card
                id="engagement"
                className="border-primary/30 bg-gradient-to-r from-primary/5 to-transparent"
              >
                <CardHeader className="pb-3">
                  <CardTitle className="flex items-center gap-2 text-primary">
                    <Target className="h-5 w-5" />
                    RM Action Plan
                  </CardTitle>
                  <p className="text-xs text-muted-foreground">
                    What the RM should do next, why it matters, and how to open the conversation.
                  </p>
                </CardHeader>
                <CardContent className="space-y-5">
                  <div className="grid gap-3 md:grid-cols-3">
                    <div className="rounded-lg border border-border bg-card p-3">
                      <p className="text-xs font-medium text-muted-foreground">
                        Primary topic
                      </p>
                      <p className="mt-1 text-sm font-semibold text-foreground">
                        {brief?.recommended_entry_angles?.[0] || primaryConversationFocus}
                      </p>
                    </div>
                    <div className="rounded-lg border border-border bg-card p-3">
                      <p className="text-xs font-medium text-muted-foreground">
                        Why now
                      </p>
                      <p className="mt-1 text-sm font-semibold text-foreground">
                        {formatNumber(
                          evidenceSummary?.parsed_document_count || viewableEvidenceCount
                        )} linked evidence records
                      </p>
                    </div>
                    <div className="rounded-lg border border-border bg-card p-3">
                      <p className="text-xs font-medium text-muted-foreground">
                        Workflow updated
                      </p>
                      <p className="mt-1 text-sm font-semibold text-foreground">
                        {formatShortDate(workflowUpdatedAt)}
                      </p>
                    </div>
                  </div>

                  <div>
                    <p className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                      Suggested client discussion points
                    </p>
                    <div className="space-y-2">
                      {topDiscussionPoints.map((angle, index) => (
                        <div
                          key={`${angle.label}-${index}`}
                          className="flex items-start gap-2 rounded-lg border border-border bg-card p-3"
                        >
                          <TrendingUp className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                          <div>
                            <p className="text-sm font-medium text-foreground">
                              {angle.label}
                            </p>
                            <p className="mt-0.5 text-xs text-muted-foreground">
                              {angle.recommendedTalkTrack}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div>
                    <p className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                      Product angle to prepare
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {(brief?.recommended_product_themes?.length
                        ? brief.recommended_product_themes
                        : prospect.productFit
                      )
                        .slice(0, 4)
                        .map((product) => (
                        <Badge key={product} variant="secondary">
                          {product}
                        </Badge>
                      ))}
                    </div>
                  </div>

                </CardContent>
              </Card>

              <Card id="evidence" className="border-border">
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <CardTitle className="flex items-center gap-2">
                        <FileText className="h-5 w-5 text-chart-2" />
                        Evidence Supporting This Action
                      </CardTitle>
                      <p className="mt-1 text-xs text-muted-foreground">
                        Source reports and extracted facts used to support this brief. Raw exchange classification codes are hidden from RM view.
                      </p>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  {evidenceSummary && (
                    <div className="grid gap-2 md:grid-cols-4">
                      <div className="rounded-lg border border-border bg-muted/30 p-3">
                        <p className="text-[10px] text-muted-foreground">Source documents</p>
                        <p className="mt-1 text-lg font-semibold text-foreground">
                          {formatNumber(evidenceSummary.parsed_document_count)}
                        </p>
                        <p className="mt-1 text-[11px] text-muted-foreground">
                          Filings and reports available as source evidence.
                        </p>
                      </div>
                      <div className="rounded-lg border border-border bg-muted/30 p-3">
                        <p className="text-[10px] text-muted-foreground">Extracted metrics</p>
                        <p className="mt-1 text-lg font-semibold text-foreground">
                          {formatNumber(evidenceSummary.metric_count)}
                        </p>
                        <p className="mt-1 text-[11px] text-muted-foreground">
                          Structured financial figures found in reports.
                        </p>
                      </div>
                      <div className="rounded-lg border border-border bg-muted/30 p-3">
                        <p className="text-[10px] text-muted-foreground">Risk disclosures</p>
                        <p className="mt-1 text-lg font-semibold text-foreground">
                          {formatNumber(evidenceSummary.risk_factor_count)}
                        </p>
                        <p className="mt-1 text-[11px] text-muted-foreground">
                          Risk language extracted for RM review.
                        </p>
                      </div>
                      <div className="rounded-lg border border-border bg-muted/30 p-3">
                        <p className="text-[10px] text-muted-foreground">Business events</p>
                        <p className="mt-1 text-lg font-semibold text-foreground">
                          {formatNumber(evidenceSummary.business_event_count)}
                        </p>
                        <p className="mt-1 text-[11px] text-muted-foreground">
                          Events that may support outreach angles.
                        </p>
                      </div>
                    </div>
                  )}

                  {coverageFlags && (
                    <div className="flex flex-wrap gap-1.5">
                      {Object.entries(coverageFlags)
                        .filter(([, value]) => value)
                        .map(([key]) => (
                          <Badge key={key} variant="outline" className="bg-primary/5 text-[10px]">
                            {formatLabel(key.replace(/^has_/, ""))}
                          </Badge>
                        ))}
                    </div>
                  )}

                  {parsedDocuments.length > 0 && (
                    <div>
                      <p className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                        Source company documents
                      </p>
                      <div className="space-y-2">
                        {parsedDocuments.slice(0, 4).map((document) => {
                          const documentSummary = cleanDocumentSummary(
                            document.summary,
                            document.title,
                            document.management_discussion_summary
                          );
                          const parsedFacts =
                            (document.metric_count || 0) +
                            (document.risk_factor_count || 0) +
                            (document.business_event_count || 0);

                          return (
                            <div
                              key={document.id}
                              className="rounded-lg border border-border bg-card p-3"
                            >
                              <div className="flex items-start justify-between gap-3">
                                <div>
                                  <p className="text-sm font-medium text-foreground">
                                    {document.title || `${formatEvidenceSource(document.source)} document`}
                                  </p>
                                  <p className="mt-1 text-xs text-muted-foreground">
                                    {documentSummary ||
                                      "Source filing available. No narrative summary was extracted yet."}
                                  </p>
                                </div>
                                {document.evidence_url && (
                                  <Button
                                    asChild
                                    variant="ghost"
                                    size="icon"
                                    className="h-8 w-8 shrink-0"
                                    aria-label={`Open source evidence for ${document.title || document.id}`}
                                  >
                                    <Link href={document.evidence_url}>
                                      <ExternalLink className="h-4 w-4 text-muted-foreground" />
                                    </Link>
                                  </Button>
                                )}
                              </div>
                              <div className="mt-2 flex flex-wrap gap-1.5">
                                <Badge variant="outline" className="text-[10px]">
                                  {formatEvidenceSource(document.source)}
                                </Badge>
                                {document.lang && (
                                  <Badge variant="outline" className="text-[10px]">
                                    {formatEvidenceLanguage(document.lang)}
                                  </Badge>
                                )}
                                {parsedFacts > 0 && (
                                  <Badge variant="outline" className="text-[10px]">
                                    {parsedFacts} extracted facts
                                  </Badge>
                                )}
                                {document.parse_status !== "success" && (
                                  <Badge variant="outline" className="text-[10px]">
                                    Parser review needed
                                  </Badge>
                                )}
                                {document.genai_extraction?.accepted_count ? (
                                  <Badge className="bg-primary/10 text-primary text-[10px]">
                                    GenAI facts {document.genai_extraction.accepted_count}
                                  </Badge>
                                ) : null}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {(keyMetrics.length > 0 ||
                    keyRiskFactors.length > 0 ||
                    keyBusinessEvents.length > 0) && (
                    <div className="grid gap-3 lg:grid-cols-3">
                      <div className="rounded-lg border border-border p-3">
                        <p className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                          Metrics
                        </p>
                        <div className="space-y-2">
                          {keyMetrics.slice(0, 3).map((metric) => (
                            <div key={`${metric.document_id}-${metric.name}`}>
                              <p className="text-sm font-medium text-foreground">
                                {metric.name}: {metric.value}
                                {metric.unit ? ` ${metric.unit}` : ""}
                              </p>
                              <p className="text-[11px] text-muted-foreground">
                                {metric.period || metric.title || "Parsed metric"}
                              </p>
                            </div>
                          ))}
                          {keyMetrics.length === 0 && (
                            <p className="text-xs text-muted-foreground">No metrics parsed.</p>
                          )}
                        </div>
                      </div>
                      <div className="rounded-lg border border-border p-3">
                        <p className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                          Risks
                        </p>
                        <div className="space-y-2">
                          {keyRiskFactors.slice(0, 3).map((risk) => (
                            <div key={`${risk.document_id}-${risk.category}`}>
                              <div className="flex items-center gap-2">
                                <Badge variant="outline" className="text-[10px]">
                                  {risk.severity}
                                </Badge>
                                <p className="text-sm font-medium text-foreground">
                                  {risk.category}
                                </p>
                              </div>
                              <p className="mt-1 line-clamp-2 text-[11px] text-muted-foreground">
                                {risk.description}
                              </p>
                            </div>
                          ))}
                          {keyRiskFactors.length === 0 && (
                            <p className="text-xs text-muted-foreground">No risk factors parsed.</p>
                          )}
                        </div>
                      </div>
                      <div className="rounded-lg border border-border p-3">
                        <p className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                          Events
                        </p>
                        <div className="space-y-2">
                          {keyBusinessEvents.slice(0, 3).map((event) => (
                            <div key={`${event.document_id}-${event.summary}`}>
                              <Badge variant="outline" className="mb-1 text-[10px]">
                                {formatLabel(event.event_type)}
                              </Badge>
                              <p className="line-clamp-2 text-sm text-foreground">
                                {event.summary}
                              </p>
                            </div>
                          ))}
                          {keyBusinessEvents.length === 0 && (
                            <p className="text-xs text-muted-foreground">No business events parsed.</p>
                          )}
                        </div>
                      </div>
                    </div>
                  )}

                  {relatedSignals.length > 0 && (
                    <div>
                      <p className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                        Company trigger evidence
                      </p>
                      <div className="space-y-2">
                        {relatedSignals.map((signal) => (
                          <div
                            key={signal.id}
                            className="flex items-start justify-between rounded-lg border border-border bg-muted/30 p-3"
                          >
                            <div className="flex-1">
                              <div className="flex items-center gap-2">
                                <Badge variant="outline" className="text-[10px] capitalize">
                                  {signal.type}
                                </Badge>
                                <span className="text-xs text-muted-foreground">
                                  {formatDate(signal.date)}
                                </span>
                                {signal.source && (
                                  <Badge variant="outline" className="bg-muted/50 text-[10px]">
                                    {formatSource(signal.source)}
                                  </Badge>
                                )}
                              </div>
                              <p className="mt-1 text-sm font-medium text-foreground">
                                {signal.title}
                              </p>
                              {cleanEvidenceSummary(signal.summary, signal.title) && (
                                <p className="mt-0.5 text-xs text-muted-foreground">
                                  {cleanEvidenceSummary(signal.summary, signal.title)}
                                </p>
                              )}
                            </div>
                            <Button
                              asChild
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8 shrink-0"
                              aria-label={`Open signal evidence for ${signal.title}`}
                            >
                              <Link href={evidenceExplorerHref(signal.title)}>
                                <ExternalLink className="h-4 w-4 text-muted-foreground" />
                              </Link>
                            </Button>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {readableNews.length > 0 && (
                    <div>
                      <p className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                        Evidence records
                      </p>
                      <div className="space-y-2">
                        {readableNews.map((item, index) => (
                          <div
                            key={`${item.title}-${index}`}
                            className="flex items-start justify-between rounded-lg border border-border p-3"
                          >
                            <div className="flex-1">
                              <p className="text-sm font-medium text-foreground">
                                {item.title}
                              </p>
                              <div className="mt-1 flex items-center gap-2">
                                <Badge variant="outline" className="bg-muted/50 text-[10px]">
                                  {formatSource(item.source)}
                                </Badge>
                                <span className="text-[10px] text-muted-foreground">
                                  {formatDate(item.date)}
                                </span>
                              </div>
                            </div>
                            <Button
                              asChild
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8 shrink-0"
                              aria-label={`Open evidence record for ${item.title}`}
                            >
                              <Link href={evidenceExplorerHref(item.title)}>
                                <ExternalLink className="h-4 w-4 text-muted-foreground" />
                              </Link>
                            </Button>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {parsedDocuments.length === 0 &&
                    keyMetrics.length === 0 &&
                    keyRiskFactors.length === 0 &&
                    keyBusinessEvents.length === 0 &&
                    viewableEvidenceCount === 0 && (
                    <div className="rounded-lg border border-border bg-muted/30 p-4 text-sm text-muted-foreground">
                      No RM-readable evidence is linked to this company yet. Review the signal feed or ask Copilot to inspect broader market context.
                    </div>
                  )}
                </CardContent>
              </Card>

              {scoreBreakdown && (
                <Card id="score-audit" className="border-border">
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <CardTitle className="flex items-center gap-2">
                          <ClipboardCheck className="h-5 w-5 text-primary" />
                          Score Audit
                        </CardTitle>
                        <p className="mt-1 text-xs text-muted-foreground">
                          Transparent scoring inputs and evidence linkage controls from the backend scorecard.
                        </p>
                      </div>
                      <Badge variant="outline" className="bg-muted/50 text-[10px]">
                        {scoreBreakdown.scorecard_version || "scorecard"}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-5">
                    <div className="rounded-lg border border-primary/20 bg-primary/5 p-4">
                      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                        <div className="max-w-3xl">
                          <p className="text-xs font-medium uppercase tracking-wider text-primary">
                            Priority readout
                          </p>
                          <p className="mt-1 text-base font-semibold text-foreground">
                            {auditPriorityBand} for RM action
                          </p>
                          <p className="mt-2 text-sm text-muted-foreground">
                            Priority combines business opportunity, evidence confidence, and a limited
                            low-risk buffer. Low risk helps the ranking only when there is also a
                            credible opportunity signal; it is not a credit rating or sales prediction.
                          </p>
                        </div>
                        <div className="shrink-0 rounded-lg border border-primary/20 bg-background px-4 py-3 text-left md:text-right">
                          <p className="text-xs text-muted-foreground">RM priority score</p>
                          <p className="mt-1 text-2xl font-semibold text-foreground">
                            {auditPriorityScore}
                            <span className="text-sm font-normal text-muted-foreground"> / 100</span>
                          </p>
                        </div>
                      </div>
                    </div>

                    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                      {scoreAuditCards.map((card) => (
                        <div key={card.title} className="rounded-lg border border-border bg-muted/30 p-3">
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <p className="text-xs font-medium text-foreground">{card.title}</p>
                              <p className="mt-1 text-[11px] text-muted-foreground">
                                {scoreBand(card.value, card.kind)}
                              </p>
                            </div>
                            <p className="text-lg font-semibold text-foreground">
                              {card.value}
                              <span className="text-xs font-normal text-muted-foreground">/100</span>
                            </p>
                          </div>
                          <p className="mt-3 text-xs leading-relaxed text-muted-foreground">
                            {card.description}
                          </p>
                        </div>
                      ))}
                    </div>

                    {linkageQuality && (
                      <details className="rounded-lg border border-border bg-muted/20 p-3">
                        <summary className="cursor-pointer text-xs font-medium uppercase tracking-wider text-muted-foreground">
                          Evidence quality details
                        </summary>
                        <p className="mt-3 text-sm text-muted-foreground">
                          {formatNumber(linkageQuality.scoreable_evidence_count)} of{" "}
                          {formatNumber(linkageQuality.linked_evidence_count)} linked evidence records
                          are eligible for scoring; {formatRatio(linkageQuality.direct_evidence_ratio)} are
                          directly about this company.
                        </p>
                        <div className="mt-3 grid gap-3 md:grid-cols-4">
                          <div className="rounded-lg border border-border bg-background p-3">
                            <p className="text-[10px] text-muted-foreground">Evidence records found</p>
                            <p className="mt-1 text-lg font-semibold text-foreground">
                              {formatNumber(linkageQuality.linked_evidence_count)}
                            </p>
                          </div>
                          <div className="rounded-lg border border-border bg-background p-3">
                            <p className="text-[10px] text-muted-foreground">Used in scoring</p>
                            <p className="mt-1 text-lg font-semibold text-foreground">
                              {formatNumber(linkageQuality.scoreable_evidence_count)}
                            </p>
                          </div>
                          <div className="rounded-lg border border-border bg-background p-3">
                            <p className="text-[10px] text-muted-foreground">Directly about this company</p>
                            <p className="mt-1 text-lg font-semibold text-foreground">
                              {formatRatio(linkageQuality.direct_evidence_ratio)}
                            </p>
                          </div>
                          <div className="rounded-lg border border-border bg-background p-3">
                            <p className="text-[10px] text-muted-foreground">Eligible evidence coverage</p>
                            <p className="mt-1 text-lg font-semibold text-foreground">
                              {formatRatio(linkageQuality.scoreable_evidence_ratio)}
                            </p>
                          </div>
                        </div>
                        {scoreBreakdown.priority_formula && (
                          <p className="mt-3 text-[11px] text-muted-foreground">
                            Formula: {scoreBreakdown.priority_formula}
                          </p>
                        )}
                      </details>
                    )}

                    <div className="grid gap-3 lg:grid-cols-2">
                      <div className="rounded-lg border border-border p-3">
                        <p className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                          Main score drivers
                        </p>
                        <div className="space-y-3">
                          {scoreDrivers.slice(0, 5).map((component) => (
                            <div key={`${component.category}-${component.name}-${component.points}`}>
                              <div className="flex items-start justify-between gap-3 text-sm">
                                <span className="font-medium text-foreground">
                                  {formatLabel(component.name)}
                                </span>
                                <span className="font-semibold text-foreground">
                                  {signedPoints(component.points)}
                                </span>
                              </div>
                              <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">
                                {component.detail}
                              </p>
                            </div>
                          ))}
                          {scoreDrivers.length === 0 && (
                            <p className="text-xs text-muted-foreground">
                              No score drivers are linked yet. Review the evidence section before using this
                              company as an outreach target.
                            </p>
                          )}
                          {(scoreBreakdown.risk_components || []).length === 0 && (
                            <p className="rounded-md border border-border bg-muted/30 p-2 text-xs text-muted-foreground">
                              No material risk signal is detected in the linked evidence.
                            </p>
                          )}
                        </div>
                      </div>

                      <div className="rounded-lg border border-border p-3">
                        <p className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                          Priority calculation
                        </p>
                        <div className="space-y-3">
                          {(scoreBreakdown.priority_components || []).map((component) => (
                            <div key={`${component.name}-${component.points}`}>
                              <div className="flex items-start justify-between gap-3 text-sm">
                                <span className="font-medium text-foreground">
                                  {priorityComponentLabel(component.name)}
                                </span>
                                <span className="font-semibold text-foreground">
                                  {signedPoints(component.points)}
                                </span>
                              </div>
                              <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">
                                {priorityComponentNarrative(component.name, component.detail)}
                              </p>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>

                    {governanceFlags.length > 0 && (
                      <div>
                        <p className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                          Governance flags
                        </p>
                        <div className="space-y-2">
                          {governanceFlags.map((flag) => (
                            <div
                              key={flag.flag_key}
                              className={`rounded-lg border p-3 text-xs ${scoreSeverityClass(flag.severity)}`}
                            >
                              <div className="flex items-center justify-between gap-3">
                                <p className="font-semibold">{formatLabel(flag.area)}</p>
                                <Badge variant="outline" className="bg-background/70 text-[10px]">
                                  {flag.severity}
                                </Badge>
                              </div>
                              <p className="mt-1">{flag.message}</p>
                              <p className="mt-1 opacity-80">{flag.suggested_action}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}

            </div>

            <aside className="space-y-4">
              <Card id="workflow" className="border-border">
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between gap-3">
                    <CardTitle className="text-sm">Workflow State</CardTitle>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={openUpdateDrawer}
                      className="h-7 px-2 text-xs"
                    >
                      <Edit3 className="mr-1 h-3 w-3" />
                      Update
                    </Button>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Owner</span>
                    <span className="font-medium text-foreground">
                      {backendWorkflow?.owner || prospect.workflowState?.owner || "Unassigned"}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Stage</span>
                    <Badge variant="outline" className="capitalize">
                      {formatLabel(currentStage)}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Status</span>
                    <Badge variant="outline" className="capitalize">
                      {formatLabel(backendWorkflow?.status || prospect.workflowState?.status || "open")}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Review</span>
                    <Badge variant="outline" className="capitalize">
                      {formatLabel(currentActionStatus)}
                    </Badge>
                  </div>
                  <div className="rounded-lg border border-border bg-muted/30 p-3">
                    <p className="text-[10px] text-muted-foreground">Last action</p>
                    <p className="mt-1 text-xs text-foreground">
                      {backendWorkflow?.last_action ||
                        prospect.workflowState?.lastAction ||
                        "No RM action recorded yet."}
                    </p>
                  </div>
                  <div className="rounded-lg border border-border bg-muted/30 p-3">
                    <p className="text-[10px] text-muted-foreground">Next action</p>
                    <p className="mt-1 text-xs text-foreground">
                      {backendWorkflow?.next_action ||
                        prospect.workflowState?.nextAction ||
                        brief?.recommended_next_step ||
                        prospect.recommendedNextStep ||
                        "Review linked evidence."}
                    </p>
                  </div>
                  {latestWorkflowNote && (
                    <div className="rounded-lg border border-primary/20 bg-primary/5 p-3">
                      <p className="mb-1 text-xs font-medium text-primary">
                        Latest RM update
                      </p>
                      <p className="text-xs text-foreground">{latestWorkflowNote}</p>
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card id="products" className="border-border">
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm">Recommended Products</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {productFits.length > 0 ? (
                    <div className="space-y-2">
                      {productFits.slice(0, 4).map((product) => (
                        <div
                          key={product.product_name}
                          className="rounded-lg border border-border p-3"
                        >
                          <div className="flex items-center justify-between gap-2">
                            <p className="text-sm font-semibold text-foreground">
                              {product.product_name}
                            </p>
                            <Badge variant="outline" className="text-[10px]">
                              fit {product.fit_score}
                            </Badge>
                          </div>
                          <p className="mt-1 text-xs text-muted-foreground">
                            {product.rationale}
                          </p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {prospect.opportunities.slice(0, 4).map((opportunity) => (
                        <div
                          key={opportunity.product}
                          className="rounded-lg border border-border p-3"
                        >
                          <p className="text-sm font-semibold text-foreground">
                            {opportunity.product}
                          </p>
                          <p className="mt-1 text-xs text-muted-foreground">
                            {opportunity.rationale}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}
                  <div className="flex flex-wrap gap-1.5 border-t border-border pt-3">
                    {(brief?.recommended_product_themes?.length
                      ? brief.recommended_product_themes
                      : prospect.productFit
                    )
                      .slice(0, 5)
                      .map((product) => (
                        <Badge key={product} variant="secondary" className="text-[10px]">
                          {product}
                        </Badge>
                      ))}
                  </div>
                </CardContent>
              </Card>

              <Card className="border-border">
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm">Company Background</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <p className="text-sm text-foreground">{companyDescription}</p>
                  {company?.website_url && (
                    <Button
                      asChild
                      variant="outline"
                      size="sm"
                      className="h-8 w-full justify-start text-xs"
                    >
                      <Link href={company.website_url}>
                        <ExternalLink className="mr-2 h-3.5 w-3.5" />
                        Company website
                      </Link>
                    </Button>
                  )}
                  <div className="mt-3 flex flex-wrap gap-2">
                    {[
                      company?.city,
                      company?.region,
                      company?.country,
                      ...prospect.crossBorderFootprint,
                    ]
                      .filter((location): location is string => Boolean(location))
                      .slice(0, 6)
                      .map((location) => (
                      <Badge
                        key={location}
                        variant="outline"
                        className="border-chart-3/20 bg-chart-3/10 text-chart-3"
                      >
                        <Globe className="mr-1 h-3 w-3" />
                        {location}
                      </Badge>
                    ))}
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {[...(company?.industries || []), ...(company?.segments || [])]
                      .slice(0, 6)
                      .map((item) => (
                        <Badge key={item} variant="secondary" className="text-[10px]">
                          {formatLabel(item)}
                        </Badge>
                      ))}
                  </div>
                  {prospect.scoreBreakdown && (
                    <div className="mt-4 space-y-2 border-t border-border pt-3">
                      <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                        Score basis
                      </p>
                      {Object.entries(prospect.scoreBreakdown).map(([key, value]) => (
                        <div key={key} className="flex items-center justify-between text-xs">
                          <span className="text-muted-foreground">{formatLabel(key)}</span>
                          <span className="font-medium text-foreground">{value}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </aside>
          </div>
        </div>
      </main>

      {updateOpen && (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/35">
          <div className="h-full w-full max-w-md overflow-y-auto border-l border-border bg-background shadow-xl">
            <div className="flex items-start justify-between border-b border-border p-5">
              <div>
                <h2 className="text-lg font-semibold text-foreground">
                  Update RM Notes
                </h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  Capture RM-owned updates without changing system scores or source evidence.
                </p>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setUpdateOpen(false)}
                className="h-8 w-8 shrink-0"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>

            <div className="space-y-4 p-5">
              <label className="block space-y-1.5">
                <span className="text-sm font-medium text-foreground">
                  Owner
                </span>
                <input
                  value={draftOwner}
                  onChange={(event) => setDraftOwner(event.target.value)}
                  placeholder="e.g. Michael Chan"
                  className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                />
              </label>

              <label className="block space-y-1.5">
                <span className="text-sm font-medium text-foreground">
                  Relationship stage
                </span>
                <select
                  value={draftStage}
                  onChange={(event) => setDraftStage(event.target.value)}
                  className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                >
                  <option value="">Keep current: {formatLabel(currentStage)}</option>
                  <option value="new">New</option>
                  <option value="qualification">Qualification</option>
                  <option value="discovery">Discovery</option>
                  <option value="proposal">Proposal</option>
                  <option value="active">Active</option>
                  <option value="monitoring">Monitoring</option>
                </select>
              </label>

              <label className="block space-y-1.5">
                <span className="text-sm font-medium text-foreground">
                  Action status
                </span>
                <select
                  value={draftStatus}
                  onChange={(event) => setDraftStatus(event.target.value)}
                  className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                >
                  <option value="not_reviewed">Not reviewed</option>
                  <option value="in_progress">In progress</option>
                  <option value="completed">Completed</option>
                  <option value="dismissed">Dismissed</option>
                </select>
              </label>

              <label className="block space-y-1.5">
                <span className="text-sm font-medium text-foreground">
                  Last action
                </span>
                <input
                  value={draftLastAction}
                  onChange={(event) => setDraftLastAction(event.target.value)}
                  placeholder="e.g. Reviewed cross-border evidence with RM"
                  className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                />
              </label>

              <label className="block space-y-1.5">
                <span className="text-sm font-medium text-foreground">
                  Next action
                </span>
                <input
                  value={draftNextAction}
                  onChange={(event) => setDraftNextAction(event.target.value)}
                  placeholder="e.g. Prepare treasury outreach note"
                  className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                />
              </label>

              <label className="block space-y-1.5">
                <span className="text-sm font-medium text-foreground">
                  RM note
                </span>
                <textarea
                  value={draftNote}
                  onChange={(event) => setDraftNote(event.target.value)}
                  placeholder="Add context from the latest call, meeting, or client response."
                  className="min-h-28 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                />
              </label>

              <div className="rounded-lg border border-muted bg-muted/30 p-3 text-xs text-muted-foreground">
                RM can update workflow notes, relationship stage, and action status. Priority score and evidence confidence remain system-controlled.
              </div>

              {saveError && (
                <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-xs text-destructive">
                  {saveError}
                </div>
              )}
            </div>

            <div className="sticky bottom-0 flex gap-2 border-t border-border bg-background p-5">
              <Button
                variant="outline"
                onClick={() => setUpdateOpen(false)}
                className="flex-1"
              >
                Cancel
              </Button>
              <Button onClick={saveRmUpdate} className="flex-1" disabled={savingWorkflow}>
                {savingWorkflow ? "Saving..." : "Save update"}
              </Button>
            </div>
          </div>
        </div>
      )}

      <AICopilotPanel
        isOpen={copilotOpen}
        onClose={() => setCopilotOpen(false)}
        prospectId={prospect.id}
        autoPrompt={copilotPrompt}
      />

      {!copilotOpen && (
        <AICopilotButton
          onClick={() => {
            setCopilotPrompt(null);
            setCopilotOpen(true);
          }}
        />
      )}
    </div>
  );
}
