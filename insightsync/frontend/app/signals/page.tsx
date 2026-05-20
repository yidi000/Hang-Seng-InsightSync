"use client";

import { useEffect, useState } from "react";
import {
  Zap,
  Search,
  Building2,
  TrendingUp,
  Globe,
  FileText,
  ChevronDown,
  Clock,
  Sparkles,
  ExternalLink,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { AppSidebar } from "@/components/app-sidebar";
import {
  AICopilotPanel,
  AICopilotButton,
} from "@/components/ai-copilot-panel";
import { useInsightSyncData } from "@/lib/api-data";
import { useMetadataFilters } from "@/lib/metadata-data";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import Link from "next/link";

const signalTypeIcons: Record<string, typeof Building2> = {
  expansion: Building2,
  funding: TrendingUp,
  policy: FileText,
  crossborder: Globe,
};

const signalTypeColors: Record<string, string> = {
  expansion: "bg-primary/10 text-primary border-primary/20",
  funding: "bg-chart-2/10 text-chart-2 border-chart-2/20",
  policy: "bg-chart-4/10 text-chart-4 border-chart-4/20",
  crossborder: "bg-chart-3/10 text-chart-3 border-chart-3/20",
};

function formatSignalType(type: string) {
  if (type === "All") return "All Signals";
  if (type === "crossborder") return "Cross-border";
  return type.charAt(0).toUpperCase() + type.slice(1);
}

function formatSource(source: string | undefined) {
  if (!source) return "InsightSync";
  if (source.toLowerCase() === "hkma") return "HKMA";
  return source
    .replace(/[_-]/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function normalizeSource(source: string | undefined) {
  return (source || "").toLowerCase().replace(/[^a-z0-9]/g, "");
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-HK", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function formatTimeAgo(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays} days ago`;
  return formatDate(dateStr);
}

function normalizeEntityName(value: string | undefined) {
  return (value || "").toLowerCase().replace(/[^a-z0-9]/g, "");
}

function normalizeDisplayText(value: string | undefined) {
  return (value || "").toLowerCase().replace(/[^a-z0-9]/g, "");
}

function shouldShowSummary(title: string, summary: string | undefined) {
  const normalizedTitle = normalizeDisplayText(title);
  const normalizedSummary = normalizeDisplayText(summary);
  return Boolean(
    normalizedSummary &&
      normalizedSummary !== normalizedTitle &&
      !normalizedSummary.includes(normalizedTitle)
  );
}

function formatEntityLabel(value: string | undefined, linkedCompany?: string) {
  if (linkedCompany) return `Linked company: ${linkedCompany}`;
  const normalized = (value || "").toUpperCase();
  if (normalized === "HKG" || normalized === "HK") return "Market context: Hong Kong";
  if (normalized === "CN" || normalized === "CHN") return "Market context: Mainland China";
  if (!value || value === "Market portfolio") return "Market context";
  return `Market context: ${value}`;
}

function formatSignalBadge(signal: { type: string; source?: string }) {
  const source = normalizeSource(signal.source);
  if (source === "hkma") return "Market indicator";
  if (source.includes("szse")) return "Company filing";
  return formatSignalType(signal.type);
}

function isOperationalCompany(name: string) {
  const normalized = name.toLowerCase();
  return ![
    "portfolio",
    "intelligence profile",
    "cluster",
    "sector",
    "national accounts",
  ].some((term) => normalized.includes(term));
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

export default function SignalsPage() {
  const { triggerSignals, prospects, backendOnline } = useInsightSyncData();
  const metadataFilters = useMetadataFilters(prospects, triggerSignals);
  const [copilotOpen, setCopilotOpen] = useState(false);
  const [copilotPrompt, setCopilotPrompt] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState("All");
  const [sourceFilter, setSourceFilter] = useState("All");
  const companyProspects = prospects.filter((prospect) =>
    isOperationalCompany(prospect.name)
  );

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const query = params.get("search");
    if (!query) return;

    const frame = window.requestAnimationFrame(() => setSearchQuery(query));
    return () => window.cancelAnimationFrame(frame);
  }, []);
  const typeOptions = metadataFilters.signalTypes;
  const sourceOptions = metadataFilters.sources;

  // Filter signals
  const filteredSignals = triggerSignals.filter((s) => {
    const searchText = `${s.title} ${s.company} ${s.summary}`.toLowerCase();
    if (searchQuery && !searchText.includes(searchQuery.toLowerCase())) return false;
    if (typeFilter !== "All" && s.type !== typeFilter) return false;
    if (
      sourceFilter !== "All" &&
      normalizeSource(s.source) !== normalizeSource(sourceFilter)
    )
      return false;
    return true;
  });

  const explainSignal = (
    signal: (typeof triggerSignals)[number],
    relatedProspect?: (typeof prospects)[number]
  ) => {
    setCopilotPrompt(
      [
        `Explain this trigger signal for an RM.`,
        `Signal: ${signal.title}`,
        `Entity context: ${formatEntityLabel(signal.company, relatedProspect?.name)}`,
        `Record type: ${formatSignalBadge(signal)}`,
        `Date: ${formatDate(signal.date)}`,
        `Summary: ${signal.summary}`,
        relatedProspect
          ? `Linked company profile: ${relatedProspect.name}. Primary engagement angle: ${
              relatedProspect.engagementAngles?.[0]?.label || "not available"
            }.`
          : `No linked company profile was found.`,
        `Please explain why it matters, which engagement angle it supports, and what the RM should do next.`,
      ].join("\n")
    );
    setCopilotOpen(true);
  };

  return (
    <div className="min-h-screen bg-background">
      <AppSidebar />

      <main className="pl-64">
        {/* Header */}
        <header className="sticky top-0 z-40 border-b border-border bg-card">
          <div className="flex h-14 items-center justify-between px-6">
            <div className="flex items-center gap-3">
              <Zap className="h-5 w-5 text-destructive" />
              <div>
                <h1 className="text-lg font-semibold text-foreground">
                  Trigger Signals
                </h1>
                <p className="text-xs text-muted-foreground">
                  RM-readable company filings, market indicators, and policy context
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
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
          {/* Signal Type Chips */}
          <div className="mb-4 flex flex-wrap gap-2">
            {typeOptions.map((type) => {
              const Icon = type !== "All" ? signalTypeIcons[type] || Zap : Zap;
              const isActive = typeFilter === type;
              return (
                <button
                  key={type}
                  onClick={() => setTypeFilter(type)}
                  className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition-all capitalize ${
                    isActive
                      ? "border-primary bg-primary/10 text-primary"
                      : "border-border bg-card text-muted-foreground hover:bg-muted/50 hover:text-foreground"
                  }`}
                >
                  <Icon className="h-3 w-3" />
                  <span>{formatSignalType(type)}</span>
                </button>
              );
            })}
          </div>

          {/* Filters */}
          <div className="mb-6 flex flex-wrap items-center gap-3">
            {/* Search */}
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search signals..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full rounded-lg border border-input bg-background py-2 pl-9 pr-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>

            {/* Source Filter */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm" className="h-9">
                  <FileText className="mr-2 h-3.5 w-3.5" />
                  Source: {sourceFilter}
                  <ChevronDown className="ml-2 h-3.5 w-3.5" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent>
                {sourceOptions.map((source) => (
                  <DropdownMenuItem
                    key={source}
                    onClick={() => setSourceFilter(source)}
                  >
                    {source}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>

            <div className="ml-auto text-xs text-muted-foreground">
              {filteredSignals.length} signal records ·{" "}
              {backendOnline ? "live intelligence" : "sample data"}
            </div>
          </div>

          {/* Signals List */}
          <div className="space-y-3">
            {filteredSignals.map((signal) => {
              const Icon = signalTypeIcons[signal.type] || Zap;
              const colorClass = signalTypeColors[signal.type] || "bg-muted/50 text-muted-foreground";
              
              const relatedProspect = companyProspects.find((prospect) =>
                signalBelongsToProspect(signal, prospect)
              );
              const showSummary = shouldShowSummary(signal.title, signal.summary);

              return (
                <Card
                  key={signal.id}
                  className="border-border transition-all hover:shadow-sm"
                >
                  <CardContent className="p-4">
                    <div className="flex items-start gap-4">
                      {/* Icon */}
                      <div className={`shrink-0 rounded-lg p-2.5 ${colorClass}`}>
                        <Icon className="h-5 w-5" />
                      </div>

                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-4">
                          <div>
                            <h3 className="text-sm font-semibold text-foreground">
                              {signal.title}
                            </h3>
                            <p className="mt-0.5 text-xs text-muted-foreground">
                              {formatEntityLabel(signal.company, relatedProspect?.name)}
                            </p>
                          </div>
                          <div className="flex items-center gap-2 shrink-0">
                            <Badge variant="outline" className="text-[10px] capitalize">
                              {formatSignalBadge(signal)}
                            </Badge>
                            <span className="flex items-center gap-1 text-[10px] text-muted-foreground">
                              <Clock className="h-3 w-3" />
                              {formatTimeAgo(signal.date)}
                            </span>
                          </div>
                        </div>

                        {showSummary && (
                          <p className="mt-2 max-w-3xl text-sm leading-6 text-foreground">
                            {signal.summary}
                          </p>
                        )}

                        {/* Evidence and Actions */}
                        <div className="mt-3 flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <Badge variant="outline" className="bg-muted/50 text-[10px]">
                              Source: {formatSource(signal.source)}
                            </Badge>
                            {signal.signalLevel && (
                              <Badge variant="outline" className="bg-muted/50 text-[10px]">
                                Level: {signal.signalLevel}
                              </Badge>
                            )}
                            <Badge variant="outline" className="bg-muted/50 text-[10px]">
                              Freshness: {formatDate(signal.date)}
                            </Badge>
                            {relatedProspect && (
                              <Badge className="bg-primary/10 text-primary border-primary/20 text-[10px]">
                                Linked company profile
                              </Badge>
                            )}
                          </div>
                          <div className="flex items-center gap-2">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => explainSignal(signal, relatedProspect)}
                              className="h-7 px-2 text-xs"
                            >
                              <Sparkles className="mr-1 h-3 w-3" />
                              Explain
                            </Button>
                            {relatedProspect && (
                              <Button
                                variant="outline"
                                size="sm"
                                asChild
                                className="h-7 px-2 text-xs"
                              >
                                <Link href={`/prospects/${relatedProspect.id}`}>
                                  Open Company Brief
                                  <ExternalLink className="ml-1 h-3 w-3" />
                                </Link>
                              </Button>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>

          {filteredSignals.length === 0 && (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <Zap className="mb-4 h-12 w-12 text-muted-foreground" />
              <h3 className="mb-1 text-lg font-semibold text-foreground">
                No signals found
              </h3>
              <p className="text-sm text-muted-foreground">
                Try adjusting your search or filter criteria
              </p>
            </div>
          )}
        </div>
      </main>

      {/* AI Copilot Panel */}
      <AICopilotPanel
        isOpen={copilotOpen}
        onClose={() => setCopilotOpen(false)}
        autoPrompt={copilotPrompt}
      />

      {/* Floating Copilot Button */}
      {!copilotOpen && <AICopilotButton onClick={() => setCopilotOpen(true)} />}
    </div>
  );
}
