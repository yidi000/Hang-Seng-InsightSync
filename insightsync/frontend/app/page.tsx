"use client";

import { useMemo, useRef, useState } from "react";
import {
  Zap,
  Sparkles,
  ChevronRight,
  ExternalLink,
  TrendingUp,
  Globe,
  FileText,
  Building2,
  Users,
  Clock,
  Filter,
  X,
} from "lucide-react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { AppSidebar } from "@/components/app-sidebar";
import {
  AICopilotPanel,
  AICopilotButton,
} from "@/components/ai-copilot-panel";
import { useInsightSyncData } from "@/lib/api-data";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  PieChart,
  Pie,
} from "recharts";

const CHART_COLORS = [
  "var(--primary)",
  "var(--chart-2)",
  "var(--chart-3)",
  "var(--chart-4)",
  "var(--chart-5)",
  "var(--muted-foreground)",
];

const tierColors: Record<string, string> = {
  A: "bg-primary text-primary-foreground",
  B: "bg-chart-2 text-white",
  C: "bg-muted text-muted-foreground",
};

const signalTypeIcons: Record<string, typeof Building2> = {
  expansion: Building2,
  funding: TrendingUp,
  policy: FileText,
  crossborder: Globe,
};

const aggregateProfileTerms = [
  "portfolio",
  "intelligence profile",
  "cluster",
  "sector",
  "national accounts",
];

function normalizeFilterValue(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]/g, "");
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-HK", {
    month: "short",
    day: "numeric",
  });
}

function valueMatchesFilter(value: string | undefined, filter: string | null) {
  if (!value || !filter) return false;
  const normalizedValue = normalizeFilterValue(value);
  const normalizedFilter = normalizeFilterValue(filter);
  return (
    normalizedValue.includes(normalizedFilter) ||
    normalizedFilter.includes(normalizedValue)
  );
}

function normalizeEntityName(value: string | undefined) {
  return normalizeFilterValue(value || "");
}

function signalBelongsToProspect(
  signal: { prospectId?: string; company: string },
  prospect: { id: string; name: string; nameZh?: string }
) {
  const signalCompany = normalizeEntityName(signal.company);
  return (
    signal.prospectId === prospect.id ||
    signalCompany === normalizeEntityName(prospect.name) ||
    signalCompany === normalizeEntityName(prospect.nameZh)
  );
}

function preferredByFilter<T>(
  items: T[],
  filter: string | null,
  getSearchText: (item: T) => string
) {
  if (!filter) return items;
  return [...items].sort((a, b) => {
    const aMatches = valueMatchesFilter(getSearchText(a), filter);
    const bMatches = valueMatchesFilter(getSearchText(b), filter);
    return Number(bMatches) - Number(aMatches);
  });
}

function isOperationalCompanyProfile(prospect: { name: string }) {
  const normalizedName = prospect.name.toLowerCase();
  return !aggregateProfileTerms.some((term) => normalizedName.includes(term));
}

function formatEvidenceConfidence(value?: number) {
  if (typeof value !== "number") return "Evidence linked";
  const level = value >= 85 ? "High" : value >= 70 ? "Moderate" : "Review";
  return `Evidence confidence: ${level} (${value}/100)`;
}

function formatStage(value?: string | null) {
  if (!value) return "New prospect";
  return value.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatRelationshipContext(prospect: {
  workflowState?: {
    stage?: string | null;
    reviewStatus?: string | null;
    nextAction?: string | null;
  };
  productFit: string[];
  recommendedNextStep?: string;
}) {
  const reviewStatus =
    prospect.workflowState?.reviewStatus?.replace(/_/g, " ") || "not reviewed";
  const productLabel = `Suggested products: ${prospect.productFit.length}`;
  const nextAction =
    prospect.workflowState?.nextAction ||
    prospect.recommendedNextStep ||
    "Review linked evidence";

  return { reviewStatus, productLabel, nextAction };
}

export default function OverviewPage() {
  const {
    prospects,
    triggerSignals,
    marketOverview,
    backendOnline,
  } = useInsightSyncData();
  const [copilotOpen, setCopilotOpen] = useState(false);
  const [industryFilter, setIndustryFilter] = useState<string | null>(null);
  const [regionFilter, setRegionFilter] = useState<string | null>(null);
  const [signalTypeFilter, setSignalTypeFilter] = useState<string | null>(null);
  const [priorityFilter, setPriorityFilter] = useState<"high" | null>(null);
  const prospectListRef = useRef<HTMLDivElement>(null);
  const companyProspects = useMemo(
    () => prospects.filter(isOperationalCompanyProfile),
    [prospects]
  );
  const signalTypeData = useMemo(() => {
    const counts = triggerSignals.reduce<Record<string, number>>((acc, signal) => {
      const label =
        signal.type === "funding"
          ? "Financing"
          : signal.type === "crossborder"
          ? "Cross-border"
          : signal.type === "policy"
          ? "Policy/Macro"
          : "Market/News";
      acc[label] = (acc[label] || 0) + 1;
      return acc;
    }, {});

    return Object.entries(counts).map(([name, value]) => ({ name, value }));
  }, [triggerSignals]);

  const portfolioStats = useMemo(() => {
    const financingCompanyCount = companyProspects.filter((prospect) =>
      prospect.focusTags?.some((tag) => normalizeFilterValue(tag).includes("financing"))
    ).length;
    const financingSignalCount = triggerSignals.filter(
      (signal) => signal.type === "funding"
    ).length;

    return {
      companyProfiles: companyProspects.length,
      highPriorityCompanies: companyProspects.filter(
        (prospect) => prospect.priorityLevel === "high" || prospect.tier === "A"
      ).length,
      crossBorderOpportunities: companyProspects.filter((prospect) =>
        prospect.focusTags?.some((tag) =>
          normalizeFilterValue(tag).includes("crossborder")
        )
      ).length,
      financingLinkedSignals: financingSignalCount || financingCompanyCount,
    };
  }, [companyProspects, triggerSignals]);

  const scrollToProspects = () => {
    prospectListRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // Filter prospects based on selected filters
  const filteredProspects = companyProspects.filter((p) => {
    if (priorityFilter === "high" && p.priorityLevel !== "high" && p.tier !== "A") {
      return false;
    }
    if (industryFilter && p.industry !== industryFilter) return false;
    if (regionFilter && p.region !== regionFilter) return false;
    if (signalTypeFilter) {
      const searchableValues = [
        ...(p.focusTags || []),
        ...(p.engagementAngles?.map((angle) => `${angle.label} ${angle.tag}`) || []),
        ...p.productFit,
        ...p.bankingNeeds,
      ];

      if (!searchableValues.some((value) => valueMatchesFilter(value, signalTypeFilter))) {
        return false;
      }
    }
    return true;
  });
  const topProspects = [...filteredProspects].sort((a, b) => b.score - a.score);

  const hasActiveFilters = industryFilter || regionFilter || signalTypeFilter || priorityFilter;
  const morningReviewItems = useMemo(
    () =>
      companyProspects.filter(
        (prospect) =>
          prospect.priorityLevel === "high" ||
          prospect.tier === "A" ||
          prospect.focusTags?.some((tag) =>
            ["crossborder", "financing"].some((theme) =>
              normalizeFilterValue(tag).includes(theme)
            )
          )
      ),
    [companyProspects]
  );
  const focusScore = morningReviewItems.length
    ? Math.round(
        morningReviewItems
          .slice(0, 8)
          .reduce((total, prospect) => total + prospect.score, 0) /
          Math.min(morningReviewItems.length, 8)
      )
    : 0;
  const primaryMorningTheme =
    portfolioStats.crossBorderOpportunities >= portfolioStats.financingLinkedSignals
      ? "cross-border activity"
      : "financing signals";

  const clearFilters = () => {
    setIndustryFilter(null);
    setRegionFilter(null);
    setSignalTypeFilter(null);
    setPriorityFilter(null);
  };

  const applySummaryFilter = (filter: "all" | "high" | "crossborder" | "financing") => {
    clearFilters();
    if (filter === "high") setPriorityFilter("high");
    if (filter === "crossborder") setSignalTypeFilter("Cross-border");
    if (filter === "financing") setSignalTypeFilter("Financing");
    scrollToProspects();
  };

  const reviewMorningActions = () => {
    clearFilters();
    setPriorityFilter("high");
    scrollToProspects();
  };

  // Handle chart clicks
  const handleIndustryClick = (data: { name: string }) => {
    setPriorityFilter(null);
    setIndustryFilter(data.name);
    scrollToProspects();
  };

  const handleRegionClick = (data: { name: string }) => {
    setPriorityFilter(null);
    setRegionFilter(data.name);
    scrollToProspects();
  };

  const handleSignalTypeClick = (data: { name: string }) => {
    setPriorityFilter(null);
    setSignalTypeFilter(data.name);
    scrollToProspects();
  };

  return (
    <div className="min-h-screen bg-background">
      <AppSidebar />

      <main className="pl-64">
        {/* Header */}
        <header className="sticky top-0 z-40 border-b border-border bg-card">
          <div className="flex h-14 items-center justify-between px-6">
            <div>
              <h1 className="text-lg font-semibold text-foreground">
                Prospecting Intelligence
              </h1>
              <p className="text-xs text-muted-foreground">
                Company-first intelligence with engagement angles
              </p>
            </div>
            <div className="flex items-center gap-3">
              {/* AI Copilot Header Button */}
              <Button
                onClick={() => setCopilotOpen(true)}
                className="bg-primary hover:bg-primary/90"
              >
                <Sparkles className="mr-2 h-4 w-4" />
                Ask AI Copilot
              </Button>
            </div>
          </div>
        </header>

        <div className="p-6">
          {/* A. Summary Stats */}
          <section className="mb-6">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-foreground">
                Portfolio Summary
              </h2>
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <Clock className="h-3 w-3" />
                {backendOnline ? "Live intelligence" : "Sample data"}
              </div>
            </div>

            <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
              <Card
                className="group cursor-pointer border-border transition-all hover:border-primary/40 hover:bg-primary/5 hover:shadow-sm"
                onClick={() => applySummaryFilter("all")}
              >
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div className="rounded-md bg-primary/10 p-2">
                      <Users className="h-4 w-4 text-primary" />
                    </div>
                    <ChevronRight className="h-4 w-4 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
                  </div>
                  <p className="mt-3 text-2xl font-semibold text-foreground">
                    {portfolioStats.companyProfiles.toLocaleString()}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Company profiles
                  </p>
                </CardContent>
              </Card>

              <Card
                className="group cursor-pointer border-destructive/30 transition-all hover:border-destructive/50 hover:bg-destructive/5 hover:shadow-sm"
                onClick={() => applySummaryFilter("high")}
              >
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div className="rounded-md bg-destructive/10 p-2">
                      <Zap className="h-4 w-4 text-destructive" />
                    </div>
                    <ChevronRight className="h-4 w-4 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
                  </div>
                  <p className="mt-3 text-2xl font-semibold text-destructive">
                    {portfolioStats.highPriorityCompanies}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    High-priority companies
                  </p>
                </CardContent>
              </Card>

              <Card
                className="group cursor-pointer border-border transition-all hover:border-chart-3/40 hover:bg-chart-3/5 hover:shadow-sm"
                onClick={() => applySummaryFilter("crossborder")}
              >
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div className="rounded-md bg-chart-3/10 p-2">
                      <Globe className="h-4 w-4 text-chart-3" />
                    </div>
                    <ChevronRight className="h-4 w-4 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
                  </div>
                  <p className="mt-3 text-2xl font-semibold text-foreground">
                    {portfolioStats.crossBorderOpportunities}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Cross-border opportunities
                  </p>
                </CardContent>
              </Card>

              <Card
                className="group cursor-pointer border-border transition-all hover:border-chart-2/40 hover:bg-chart-2/5 hover:shadow-sm"
                onClick={() => applySummaryFilter("financing")}
              >
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div className="rounded-md bg-chart-2/10 p-2">
                      <TrendingUp className="h-4 w-4 text-chart-2" />
                    </div>
                    <ChevronRight className="h-4 w-4 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
                  </div>
                  <p className="mt-3 text-2xl font-semibold text-foreground">
                    {portfolioStats.financingLinkedSignals}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Financing-linked signals
                  </p>
                </CardContent>
              </Card>
            </div>
          </section>

          {/* B. Morning Brief */}
          <section className="mb-6">
            <Card className="border-primary/20 bg-gradient-to-r from-primary/5 to-card">
              <CardContent className="flex items-center justify-between gap-6 p-6">
                <div className="min-w-0 flex-1">
                  <Badge className="mb-4 bg-primary/10 text-primary hover:bg-primary/10">
                    Morning Brief
                  </Badge>
                  <h2 className="text-2xl font-semibold leading-tight text-foreground">
                    {morningReviewItems.length} client relationships need RM review
                  </h2>
                  <p className="mt-3 max-w-3xl text-sm leading-6 text-muted-foreground">
                    Portfolio activity is led by {primaryMorningTheme}. Start with
                    high-priority client relationships, then open the supporting
                    evidence before outreach.
                  </p>
                  <div className="mt-5 flex flex-wrap gap-3">
                    <Button onClick={reviewMorningActions} className="bg-primary hover:bg-primary/90">
                      Review RM Actions
                      <ChevronRight className="ml-2 h-4 w-4" />
                    </Button>
                    <Link href="/signals">
                      <Button variant="outline">Open Evidence</Button>
                    </Link>
                    <Button variant="outline" onClick={() => setCopilotOpen(true)}>
                      Ask Copilot
                    </Button>
                  </div>
                </div>
                <button
                  onClick={reviewMorningActions}
                  className="hidden min-w-[190px] rounded-xl bg-sidebar px-8 py-7 text-center text-sidebar-foreground transition-colors hover:bg-sidebar/90 lg:block"
                >
                  <p className="text-sm text-sidebar-foreground/70">Focus score</p>
                  <p className="mt-2 text-5xl font-semibold">{focusScore}</p>
                  <p className="mt-2 text-sm text-sidebar-foreground/70">
                    {portfolioStats.highPriorityCompanies} priority clients
                  </p>
                  <p className="mt-1 text-xs text-sidebar-foreground/50">
                    Click to review
                  </p>
                </button>
              </CardContent>
            </Card>
          </section>

          {/* C. Market Opportunity Overview */}
          <section className="mb-6">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-foreground">
                Market Opportunity Overview
              </h2>
              <p className="text-xs text-muted-foreground">
                Click chart elements to filter prospects
              </p>
            </div>

            <div className="grid gap-4 lg:grid-cols-3">
              {/* By Industry */}
              <Card className="border-border">
                <CardHeader className="pb-2 pt-4 px-4">
                  <CardTitle className="text-xs font-medium text-muted-foreground">
                    By Industry
                  </CardTitle>
                </CardHeader>
                <CardContent className="px-4 pb-4">
                  <div className="h-[180px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={marketOverview.industryDistribution}
                        layout="vertical"
                        margin={{ top: 0, right: 0, bottom: 0, left: 0 }}
                      >
                        <CartesianGrid
                          strokeDasharray="3 3"
                          horizontal={true}
                          vertical={false}
                          stroke="var(--border)"
                        />
                        <XAxis
                          type="number"
                          tick={{ fill: "var(--muted-foreground)", fontSize: 10 }}
                          axisLine={false}
                          tickLine={false}
                        />
                        <YAxis
                          type="category"
                          dataKey="name"
                          width={80}
                          tick={{ fill: "var(--muted-foreground)", fontSize: 10 }}
                          axisLine={false}
                          tickLine={false}
                        />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: "var(--card)",
                            border: "1px solid var(--border)",
                            borderRadius: "6px",
                            fontSize: "11px",
                          }}
                        />
                        <Bar
                          dataKey="value"
                          radius={[0, 4, 4, 0]}
                          cursor="pointer"
                          onClick={(data) => handleIndustryClick(data)}
                        >
                          {marketOverview.industryDistribution.map(
                            (entry, index) => (
                              <Cell
                                key={`cell-${index}`}
                                fill={
                                  industryFilter === entry.name
                                    ? "var(--primary)"
                                    : CHART_COLORS[index % CHART_COLORS.length]
                                }
                                className="transition-all hover:opacity-80"
                              />
                            )
                          )}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>

              {/* By Region */}
              <Card className="border-border">
                <CardHeader className="pb-2 pt-4 px-4">
                  <CardTitle className="text-xs font-medium text-muted-foreground">
                    By Region
                  </CardTitle>
                </CardHeader>
                <CardContent className="px-4 pb-4">
                  <div className="h-[180px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={marketOverview.regionDistribution}
                          cx="50%"
                          cy="50%"
                          innerRadius={40}
                          outerRadius={70}
                          paddingAngle={2}
                          dataKey="value"
                          cursor="pointer"
                          onClick={(data) => handleRegionClick(data)}
                        >
                          {marketOverview.regionDistribution.map(
                            (entry, index) => (
                              <Cell
                                key={`cell-${index}`}
                                fill={
                                  regionFilter === entry.name
                                    ? "var(--primary)"
                                    : CHART_COLORS[index % CHART_COLORS.length]
                                }
                                className="transition-all hover:opacity-80"
                              />
                            )
                          )}
                        </Pie>
                        <Tooltip
                          contentStyle={{
                            backgroundColor: "var(--card)",
                            border: "1px solid var(--border)",
                            borderRadius: "6px",
                            fontSize: "11px",
                          }}
                        />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="mt-2 flex flex-wrap justify-center gap-2">
                    {marketOverview.regionDistribution.slice(0, 4).map(
                      (item, index) => (
                        <button
                          key={item.name}
                          onClick={() => handleRegionClick(item)}
                          className={`flex items-center gap-1.5 rounded px-1.5 py-0.5 text-[10px] transition-colors ${
                            regionFilter === item.name
                              ? "bg-primary/10 text-primary"
                              : "hover:bg-muted"
                          }`}
                        >
                          <span
                            className="h-2 w-2 rounded-full"
                            style={{
                              backgroundColor:
                                CHART_COLORS[index % CHART_COLORS.length],
                            }}
                          />
                          {item.name}
                        </button>
                      )
                    )}
                  </div>
                </CardContent>
              </Card>

              {/* By Signal Type (NEW - replaces Company Size) */}
              <Card className="border-border">
                <CardHeader className="pb-2 pt-4 px-4">
                  <CardTitle className="text-xs font-medium text-muted-foreground">
                    By Signal Type
                  </CardTitle>
                </CardHeader>
                <CardContent className="px-4 pb-4">
                  <div className="h-[180px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={signalTypeData}
                        layout="vertical"
                        margin={{ top: 0, right: 0, bottom: 0, left: 0 }}
                      >
                        <CartesianGrid
                          strokeDasharray="3 3"
                          horizontal={true}
                          vertical={false}
                          stroke="var(--border)"
                        />
                        <XAxis
                          type="number"
                          tick={{ fill: "var(--muted-foreground)", fontSize: 10 }}
                          axisLine={false}
                          tickLine={false}
                        />
                        <YAxis
                          type="category"
                          dataKey="name"
                          width={80}
                          tick={{ fill: "var(--muted-foreground)", fontSize: 10 }}
                          axisLine={false}
                          tickLine={false}
                        />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: "var(--card)",
                            border: "1px solid var(--border)",
                            borderRadius: "6px",
                            fontSize: "11px",
                          }}
                        />
                        <Bar
                          dataKey="value"
                          radius={[0, 4, 4, 0]}
                          cursor="pointer"
                          onClick={(data) => handleSignalTypeClick(data)}
                        >
                          {signalTypeData.map((entry, index) => (
                            <Cell
                              key={`cell-${index}`}
                              fill={
                                signalTypeFilter === entry.name
                                  ? "var(--primary)"
                                  : CHART_COLORS[index % CHART_COLORS.length]
                              }
                              className="transition-all hover:opacity-80"
                            />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>
            </div>
          </section>

          {/* Active Filters */}
          {hasActiveFilters && (
            <div
              ref={prospectListRef}
              className="mb-4 flex items-center gap-3 rounded-lg border border-primary/20 bg-primary/5 px-4 py-3"
            >
              <Filter className="h-4 w-4 text-primary" />
              <span className="text-sm font-medium text-foreground">
                Active filters:
              </span>
              <div className="flex flex-wrap gap-2">
                {priorityFilter && (
                  <Badge className="bg-destructive/10 text-destructive border-destructive/20">
                    Priority: High
                    <button
                      onClick={() => setPriorityFilter(null)}
                      className="ml-1.5 hover:text-destructive/70"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                )}
                {industryFilter && (
                  <Badge className="bg-primary/10 text-primary border-primary/20">
                    Industry: {industryFilter}
                    <button
                      onClick={() => setIndustryFilter(null)}
                      className="ml-1.5 hover:text-primary/70"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                )}
                {regionFilter && (
                  <Badge className="bg-chart-3/10 text-chart-3 border-chart-3/20">
                    Region: {regionFilter}
                    <button
                      onClick={() => setRegionFilter(null)}
                      className="ml-1.5 hover:text-chart-3/70"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                )}
                {signalTypeFilter && (
                  <Badge className="bg-chart-2/10 text-chart-2 border-chart-2/20">
                    Signal: {signalTypeFilter}
                    <button
                      onClick={() => setSignalTypeFilter(null)}
                      className="ml-1.5 hover:text-chart-2/70"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                )}
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={clearFilters}
                className="ml-auto text-xs text-muted-foreground hover:text-foreground"
              >
                Clear all
              </Button>
            </div>
          )}

          {/* D. Top Priority Company Profiles */}
          <section ref={!hasActiveFilters ? prospectListRef : undefined}>
            <div className="mb-3 flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold text-foreground">
                  Top Priority Company Profiles
                </h2>
                <p className="text-xs text-muted-foreground">
                  Showing top {Math.min(topProspects.length, 8)} of{" "}
                  {filteredProspects.length} matching companies
                </p>
              </div>
              <Link href="/prospects">
                <Button variant="outline" size="sm" className="h-8 text-xs">
                  View All {companyProspects.length}
                  <ExternalLink className="ml-1.5 h-3 w-3" />
                </Button>
              </Link>
            </div>

            <Card className="border-border">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-border bg-muted/30">
                      <th className="w-[22%] px-4 py-3 text-left text-xs font-medium text-muted-foreground">
                        Company
                      </th>
                      <th className="w-[14%] px-4 py-3 text-left text-xs font-medium text-muted-foreground">
                        Priority assessment
                      </th>
                      <th className="w-[24%] px-4 py-3 text-left text-xs font-medium text-muted-foreground">
                        Trigger evidence
                      </th>
                      <th className="w-[22%] px-4 py-3 text-left text-xs font-medium text-muted-foreground">
                        Recommended approach
                      </th>
                      <th className="w-[14%] px-4 py-3 text-left text-xs font-medium text-muted-foreground">
                        Relationship status
                      </th>
                      <th className="w-[10%] px-4 py-3 text-right text-xs font-medium text-muted-foreground">
                        Action
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {topProspects.slice(0, 8).map((prospect) => {
                      const preferredAngles = preferredByFilter(
                        prospect.engagementAngles || [],
                        signalTypeFilter,
                        (angle) => `${angle.label} ${angle.tag}`
                      );
                      const preferredProducts = preferredByFilter(
                        prospect.productFit,
                        signalTypeFilter,
                        (product) => product
                      );
                      const matchingAngle = preferredAngles.find((angle) =>
                        valueMatchesFilter(`${angle.label} ${angle.tag}`, signalTypeFilter)
                      );
                      const matchingProduct = preferredProducts.find((product) =>
                        valueMatchesFilter(product, signalTypeFilter)
                      );
                      const displayAngle =
                        matchingAngle?.label ||
                        matchingProduct ||
                        preferredAngles[0]?.label ||
                        prospect.recommendedNextStep ||
                        prospect.entryAngle;
                      const primaryReason =
                        prospect.whyPrioritized?.[0] ||
                        prospect.expansionSignals?.[0] ||
                        prospect.entryAngle;
                      const visibleProducts = preferredProducts.slice(0, 2);
                      const remainingProductCount = Math.max(
                        preferredProducts.length - visibleProducts.length,
                        0
                      );
                      const latestSignal = triggerSignals.find((signal) =>
                        signalTypeFilter
                          ? valueMatchesFilter(signal.type, signalTypeFilter) &&
                            signalBelongsToProspect(signal, prospect)
                          : signalBelongsToProspect(signal, prospect)
                      );
                      const evidencePreview = latestSignal || prospect.news[0];
                      const relationshipContext =
                        formatRelationshipContext(prospect);
                      return (
                        <tr
                          key={prospect.id}
                          className="border-b border-border transition-colors hover:bg-muted/30"
                        >
                          <td className="px-4 py-4 align-top">
                            <div className="space-y-1">
                              <p className="text-sm font-semibold leading-snug text-foreground">
                                {prospect.name}
                              </p>
                              <p className="text-xs text-muted-foreground">
                                {prospect.nameZh}
                              </p>
                              <div className="flex flex-wrap gap-1.5 pt-1">
                                <Badge variant="outline" className="text-[10px]">
                                  {prospect.industry}
                                </Badge>
                                <Badge variant="outline" className="text-[10px]">
                                  {prospect.region}
                                </Badge>
                              </div>
                            </div>
                          </td>
                          <td className="px-4 py-4 align-top">
                            <div className="space-y-1.5">
                              <Badge className={tierColors[prospect.tier]}>
                                Tier {prospect.tier}
                              </Badge>
                              <p className="text-xs text-foreground">
                                Priority score {prospect.score}
                              </p>
                              <p className="text-[11px] text-muted-foreground">
                                {formatEvidenceConfidence(
                                  prospect.evidenceConfidenceScore
                                )}
                              </p>
                            </div>
                          </td>
                          <td className="px-4 py-4 align-top">
                            {evidencePreview ? (
                              <div className="space-y-1.5">
                                <Badge
                                  variant="outline"
                                  className="text-[10px] capitalize"
                                >
                                  {"type" in evidencePreview
                                    ? `${evidencePreview.type} signal`
                                    : "evidence record"}
                                </Badge>
                                <p className="line-clamp-2 text-xs text-foreground">
                                  {evidencePreview.title}
                                </p>
                                <p className="text-[11px] text-muted-foreground">
                                  {evidencePreview.source || "InsightSync"} ·{" "}
                                  {formatDate(evidencePreview.date)}
                                </p>
                              </div>
                            ) : (
                              <div className="space-y-1.5">
                                <p className="line-clamp-3 text-xs text-foreground">
                                  {primaryReason}
                                </p>
                              </div>
                            )}
                          </td>
                          <td className="px-4 py-4 align-top">
                            <p className="text-sm font-medium leading-snug text-foreground">
                              {displayAngle}
                            </p>
                            <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">
                              {prospect.recommendedNextStep || primaryReason}
                            </p>
                            <div className="mt-2 flex flex-wrap gap-1">
                              {visibleProducts.map((product) => (
                                <Badge
                                  key={product}
                                  variant="secondary"
                                  className="text-[9px]"
                                >
                                  {product}
                                </Badge>
                              ))}
                              {remainingProductCount > 0 && (
                                <Badge variant="secondary" className="text-[9px]">
                                  View {remainingProductCount} more
                                </Badge>
                              )}
                            </div>
                          </td>
                          <td className="px-4 py-4 align-top">
                            <div className="space-y-1.5 text-xs">
                              <p className="font-medium text-foreground">
                                {formatStage(prospect.workflowState?.stage)}
                              </p>
                              <p className="text-muted-foreground">
                                Review: {relationshipContext.reviewStatus}
                              </p>
                              <p className="text-muted-foreground">
                                {relationshipContext.productLabel}
                              </p>
                              <p className="text-muted-foreground">
                                Next: {relationshipContext.nextAction}
                              </p>
                            </div>
                          </td>
                          <td className="px-4 py-4 text-right align-top">
                            <Link href={`/prospects/${prospect.id}`}>
                              <Button variant="outline" size="sm" className="h-8 text-xs">
                                Open brief
                                <ExternalLink className="ml-1.5 h-3 w-3" />
                              </Button>
                            </Link>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              {filteredProspects.length === 0 && (
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <Users className="mb-3 h-8 w-8 text-muted-foreground" />
                  <p className="text-sm font-medium text-foreground">
                    No company profiles match filters
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Try adjusting your filter criteria
                  </p>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={clearFilters}
                    className="mt-3"
                  >
                    Clear filters
                  </Button>
                </div>
              )}
            </Card>
          </section>

          {/* E. Recent Trigger Signals */}
          <section className="mt-6">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="flex items-center gap-2 text-sm font-semibold text-foreground">
                <Zap className="h-4 w-4 text-destructive" />
                Recent Trigger Signals
              </h2>
              <Link href="/signals">
                <Button variant="outline" size="sm" className="h-8 text-xs">
                  View All
                  <ExternalLink className="ml-1.5 h-3 w-3" />
                </Button>
              </Link>
            </div>

            <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
              {triggerSignals.slice(0, 4).map((signal) => {
                const Icon = signalTypeIcons[signal.type] || Zap;
                return (
                  <Card
                    key={signal.id}
                    className="border-border transition-all hover:shadow-sm"
                  >
                    <CardContent className="p-4">
                      <div className="mb-2 flex items-center justify-between">
                        <Badge variant="outline" className="text-[10px] capitalize">
                          <Icon className="h-3 w-3" />
                          {signal.type}
                        </Badge>
                        <span className="text-[10px] text-muted-foreground">
                          {formatDate(signal.date)}
                        </span>
                      </div>
                      <p className="mb-1 text-sm font-medium text-foreground line-clamp-2">
                        {signal.title}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {signal.company}
                      </p>
                      <div className="mt-3 flex items-center justify-between">
                        <Badge
                          variant="outline"
                          className="bg-muted/50 text-[9px]"
                        >
                          {signal.source ? `Source: ${signal.source}` : "Evidence linked"}
                        </Badge>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-6 px-2 text-[10px]"
                          onClick={() => setCopilotOpen(true)}
                        >
                          <Sparkles className="mr-1 h-3 w-3" />
                          Ask AI
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          </section>
        </div>
      </main>

      {/* AI Copilot Panel */}
      <AICopilotPanel isOpen={copilotOpen} onClose={() => setCopilotOpen(false)} />

      {/* Floating Copilot Button */}
      {!copilotOpen && <AICopilotButton onClick={() => setCopilotOpen(true)} />}
    </div>
  );
}
