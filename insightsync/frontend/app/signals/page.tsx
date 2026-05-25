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
  X,
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

function formatEntityLabel(value: string | undefined) {
  const normalized = (value || "").toUpperCase();
  if (normalized === "HKG" || normalized === "HK") return "Scope: Hong Kong market";
  if (normalized === "CN" || normalized === "CHN") return "Scope: Mainland China market";
  if (!value || value === "Market portfolio") return "Scope: Market-wide signal";
  return `Scope: ${value}`;
}

function formatSignalBadge(signal: { type: string; source?: string }) {
  const source = normalizeSource(signal.source);
  if (source === "hkma") return "Market indicator";
  if (source.includes("szse") || source.includes("cninfo")) return "Exchange filing";
  return formatSignalType(signal.type);
}

export default function SignalsPage() {
  const { triggerSignals, prospects, backendOnline } = useInsightSyncData();
  const metadataFilters = useMetadataFilters(prospects, triggerSignals);
  const [copilotOpen, setCopilotOpen] = useState(false);
  const [copilotPrompt, setCopilotPrompt] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState("All");
  const [sourceFilter, setSourceFilter] = useState("All");
  const [selectedSignalId, setSelectedSignalId] = useState<string | null>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const query = params.get("search");
    const signalId = params.get("signal");

    const frame = window.requestAnimationFrame(() => {
      if (query) setSearchQuery(query);
      if (signalId) setSelectedSignalId(signalId);
    });
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
  const selectedSignal = selectedSignalId
    ? triggerSignals.find((signal) => signal.id === selectedSignalId)
    : undefined;

  const openSignalDetail = (signal: (typeof triggerSignals)[number]) => {
    const params = new URLSearchParams(window.location.search);
    params.set("signal", signal.id);
    window.history.replaceState(null, "", `${window.location.pathname}?${params.toString()}`);
    setSelectedSignalId(signal.id);
  };

  const closeSignalDetail = () => {
    const params = new URLSearchParams(window.location.search);
    params.delete("signal");
    const query = params.toString();
    window.history.replaceState(null, "", query ? `${window.location.pathname}?${query}` : window.location.pathname);
    setSelectedSignalId(null);
  };

  const explainSignal = (signal: (typeof triggerSignals)[number]) => {
    setCopilotPrompt(
      [
        `Explain this trigger signal for an RM.`,
        `Signal: ${signal.title}`,
        `Signal scope: ${formatEntityLabel(signal.company)}`,
        `Record type: ${formatSignalBadge(signal)}`,
        `Date: ${formatDate(signal.date)}`,
        `Summary: ${signal.summary}`,
        `Please explain why it matters, what market or filing context it provides, and what an RM should check before using it in client outreach.`,
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
                  RM-readable market, filing, and policy intelligence
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
              {filteredSignals.length} signal records -{" "}
              {backendOnline ? "live intelligence" : "sample data"}
            </div>
          </div>

          {/* Signals List */}
          <div className="space-y-3">
            {filteredSignals.map((signal) => {
              const Icon = signalTypeIcons[signal.type] || Zap;
              const colorClass = signalTypeColors[signal.type] || "bg-muted/50 text-muted-foreground";
              
              const showSummary = shouldShowSummary(signal.title, signal.summary);

              return (
                <Card
                  key={signal.id}
                  className="cursor-pointer border-border transition-all hover:shadow-sm"
                  onClick={() => openSignalDetail(signal)}
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
                              {formatEntityLabel(signal.company)}
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
                          </div>
                          <div className="flex items-center gap-2">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={(event) => {
                                event.stopPropagation();
                                explainSignal(signal);
                              }}
                              className="h-7 px-2 text-xs"
                            >
                              <Sparkles className="mr-1 h-3 w-3" />
                              Explain
                            </Button>
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

      {selectedSignal && (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/35">
          <aside className="h-full w-full max-w-xl overflow-y-auto border-l border-border bg-background shadow-xl">
            <div className="flex items-start justify-between border-b border-border p-5">
              <div className="min-w-0">
                <Badge variant="outline" className="mb-3 text-[10px]">
                  {formatSignalBadge(selectedSignal)}
                </Badge>
                <h2 className="text-lg font-semibold leading-snug text-foreground">
                  {selectedSignal.title}
                </h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  {formatEntityLabel(selectedSignal.company)}
                </p>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={closeSignalDetail}
                className="h-8 w-8 shrink-0"
                aria-label="Close signal detail"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>

            <div className="space-y-4 p-5">
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-lg border border-border p-3">
                  <p className="text-[10px] uppercase tracking-wider text-muted-foreground">
                    Source
                  </p>
                  <p className="mt-1 text-sm font-medium text-foreground">
                    {formatSource(selectedSignal.source)}
                  </p>
                </div>
                <div className="rounded-lg border border-border p-3">
                  <p className="text-[10px] uppercase tracking-wider text-muted-foreground">
                    Signal date
                  </p>
                  <p className="mt-1 text-sm font-medium text-foreground">
                    {formatDate(selectedSignal.date)}
                  </p>
                </div>
                <div className="rounded-lg border border-border p-3">
                  <p className="text-[10px] uppercase tracking-wider text-muted-foreground">
                    Signal type
                  </p>
                  <p className="mt-1 text-sm font-medium text-foreground">
                    {formatSignalType(selectedSignal.type)}
                  </p>
                </div>
                <div className="rounded-lg border border-border p-3">
                  <p className="text-[10px] uppercase tracking-wider text-muted-foreground">
                    Level
                  </p>
                  <p className="mt-1 text-sm font-medium text-foreground">
                    {selectedSignal.signalLevel || "Not specified"}
                  </p>
                </div>
              </div>

              <div className="rounded-lg border border-border bg-muted/30 p-4">
                <p className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Signal Summary
                </p>
                <p className="text-sm leading-6 text-foreground">
                  {selectedSignal.summary || "No additional summary is available for this signal."}
                </p>
              </div>

              <div className="rounded-lg border border-border p-4">
                <p className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Evidence References
                </p>
                {selectedSignal.evidenceRefs?.length ? (
                  <div className="flex flex-wrap gap-2">
                    {selectedSignal.evidenceRefs.map((reference) => (
                      <Badge key={reference} variant="outline" className="bg-muted/50 text-[10px]">
                        {reference}
                      </Badge>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    No explicit evidence references are attached to this signal.
                  </p>
                )}
              </div>

              <div className="flex flex-wrap gap-2 border-t border-border pt-4">
                <Button
                  onClick={() => explainSignal(selectedSignal)}
                  className="bg-primary hover:bg-primary/90"
                >
                  <Sparkles className="mr-2 h-4 w-4" />
                  Explain with Copilot
                </Button>
              </div>
            </div>
          </aside>
        </div>
      )}

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
