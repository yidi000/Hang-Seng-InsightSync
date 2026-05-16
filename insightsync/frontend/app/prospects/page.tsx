"use client";

import { useState } from "react";
import {
  ArrowUpDown,
  Building2,
  ChevronDown,
  Clock,
  ExternalLink,
  FileText,
  Filter,
  Globe,
  Search,
  Sparkles,
  Users,
} from "lucide-react";
import Link from "next/link";
import {
  AICopilotButton,
  AICopilotPanel,
} from "@/components/ai-copilot-panel";
import { AppSidebar } from "@/components/app-sidebar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useInsightSyncData } from "@/lib/api-data";
import { useMetadataFilters } from "@/lib/metadata-data";

const tierColors: Record<string, string> = {
  A: "bg-primary text-primary-foreground",
  B: "bg-chart-2 text-white",
  C: "bg-muted text-muted-foreground",
};

function normalizeEntityName(value: string | undefined) {
  return (value || "").toLowerCase().replace(/[^a-z0-9]/g, "");
}

function normalizeSource(value: string | undefined) {
  return (value || "").toLowerCase().replace(/[^a-z0-9]/g, "");
}

function formatLabel(value: string | undefined | null) {
  if (!value) return "Unassigned";
  return value.replace(/[_-]/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
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

export default function ProspectsPage() {
  const { prospects, triggerSignals, backendOnline } = useInsightSyncData();
  const metadataFilters = useMetadataFilters(prospects, triggerSignals);
  const [copilotOpen, setCopilotOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [industryFilter, setIndustryFilter] = useState("All");
  const [regionFilter, setRegionFilter] = useState("All");
  const [sourceFilter, setSourceFilter] = useState("All");
  const [sortBy, setSortBy] = useState<"score" | "name" | "industry">("score");

  const filteredProspects = prospects
    .filter((prospect) => {
      const searchText = `${prospect.name} ${prospect.nameZh}`.toLowerCase();
      if (searchQuery && !searchText.includes(searchQuery.toLowerCase())) {
        return false;
      }
      if (industryFilter !== "All" && prospect.industry !== industryFilter) {
        return false;
      }
      if (regionFilter !== "All" && prospect.region !== regionFilter) {
        return false;
      }
      if (sourceFilter !== "All") {
        const hasSourceEvidence =
          prospect.news.some(
            (item) => normalizeSource(item.source) === normalizeSource(sourceFilter)
          ) ||
          triggerSignals.some(
            (signal) =>
              signalBelongsToProspect(signal, prospect) &&
              normalizeSource(signal.source) === normalizeSource(sourceFilter)
          );
        if (!hasSourceEvidence) return false;
      }
      return true;
    })
    .sort((a, b) => {
      if (sortBy === "score") return b.score - a.score;
      if (sortBy === "name") return a.name.localeCompare(b.name);
      if (sortBy === "industry") return a.industry.localeCompare(b.industry);
      return 0;
    });

  return (
    <div className="min-h-screen bg-background">
      <AppSidebar />

      <main className="pl-64">
        <header className="sticky top-0 z-40 border-b border-border bg-card">
          <div className="flex h-14 items-center justify-between px-6">
            <div className="flex items-center gap-3">
              <Users className="h-5 w-5 text-primary" />
              <div>
                <h1 className="text-lg font-semibold text-foreground">
                  Priority Company Profiles
                </h1>
                <p className="text-xs text-muted-foreground">
                  Company-first intelligence with RM action briefs
                </p>
              </div>
            </div>
            <Button
              onClick={() => setCopilotOpen(true)}
              className="bg-primary hover:bg-primary/90"
            >
              <Sparkles className="mr-2 h-4 w-4" />
              Ask AI Copilot
            </Button>
          </div>
        </header>

        <div className="p-6">
          <div className="mb-6 flex flex-wrap items-center gap-3">
            <div className="relative max-w-sm flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search company profiles..."
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
                className="w-full rounded-lg border border-input bg-background py-2 pl-9 pr-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm" className="h-9">
                  <Filter className="mr-2 h-3.5 w-3.5" />
                  Industry: {industryFilter}
                  <ChevronDown className="ml-2 h-3.5 w-3.5" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent>
                {metadataFilters.industries.map((industry) => (
                  <DropdownMenuItem
                    key={industry}
                    onClick={() => setIndustryFilter(industry)}
                  >
                    {industry}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm" className="h-9">
                  <Globe className="mr-2 h-3.5 w-3.5" />
                  Region: {regionFilter}
                  <ChevronDown className="ml-2 h-3.5 w-3.5" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent>
                {metadataFilters.regions.map((region) => (
                  <DropdownMenuItem
                    key={region}
                    onClick={() => setRegionFilter(region)}
                  >
                    {region}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm" className="h-9">
                  <FileText className="mr-2 h-3.5 w-3.5" />
                  Source: {sourceFilter}
                  <ChevronDown className="ml-2 h-3.5 w-3.5" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent>
                {metadataFilters.sources.map((source) => (
                  <DropdownMenuItem
                    key={source}
                    onClick={() => setSourceFilter(source)}
                  >
                    {source}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm" className="h-9">
                  <ArrowUpDown className="mr-2 h-3.5 w-3.5" />
                  Sort by:{" "}
                  {sortBy === "score" ? "Priority" : sortBy === "name" ? "Name" : "Industry"}
                  <ChevronDown className="ml-2 h-3.5 w-3.5" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent>
                <DropdownMenuItem onClick={() => setSortBy("score")}>
                  Priority Score
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setSortBy("name")}>
                  Company Name
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setSortBy("industry")}>
                  Industry
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>

            <div className="ml-auto text-xs text-muted-foreground">
              {filteredProspects.length} company profiles -{" "}
              {backendOnline ? "live intelligence" : "sample data"}
            </div>
          </div>

          <div className="space-y-4">
            {filteredProspects.map((prospect) => {
              const latestSignal = triggerSignals.find((signal) =>
                signalBelongsToProspect(signal, prospect)
              );
              const linkedEvidenceCount =
                triggerSignals.filter((signal) =>
                  signalBelongsToProspect(signal, prospect)
                ).length + prospect.news.length;

              return (
                <Card
                  key={prospect.id}
                  className="border-border transition-all hover:shadow-md"
                >
                  <CardContent className="p-0">
                    <div className="flex">
                      <div
                        className={`w-1.5 shrink-0 rounded-l-lg ${
                          prospect.tier === "A"
                            ? "bg-primary"
                            : prospect.tier === "B"
                            ? "bg-chart-2"
                            : "bg-muted"
                        }`}
                      />

                      <div className="flex-1 p-4">
                        <div className="flex items-start justify-between gap-4">
                          <div className="min-w-0 flex-1">
                            <div className="flex flex-wrap items-center gap-3">
                              <h3 className="text-base font-semibold text-foreground">
                                {prospect.name}
                              </h3>
                              <Badge className={tierColors[prospect.tier]}>
                                Tier {prospect.tier}
                              </Badge>
                              <span className="text-sm text-muted-foreground">
                                Score: {prospect.score}
                              </span>
                            </div>
                            <p className="mt-0.5 text-sm text-muted-foreground">
                              {prospect.nameZh}
                            </p>

                            <div className="mt-3 flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
                              <span className="flex items-center gap-1">
                                <Building2 className="h-3.5 w-3.5" />
                                {prospect.industry}
                              </span>
                              <span className="flex items-center gap-1">
                                <Globe className="h-3.5 w-3.5" />
                                {prospect.region}
                              </span>
                              <span className="flex items-center gap-1">
                                <Users className="h-3.5 w-3.5" />
                                Workflow: {formatLabel(prospect.workflowState?.stage)}
                              </span>
                            </div>
                          </div>

                          <div className="flex shrink-0 items-center gap-2">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => setCopilotOpen(true)}
                              className="h-8"
                            >
                              <Sparkles className="mr-1.5 h-3.5 w-3.5" />
                              Ask AI
                            </Button>
                            <Button variant="outline" size="sm" asChild className="h-8">
                              <Link href={`/prospects/${prospect.id}`}>
                                Open brief
                                <ExternalLink className="ml-1.5 h-3 w-3" />
                              </Link>
                            </Button>
                          </div>
                        </div>

                        <div className="mt-4 rounded-lg border border-primary/20 bg-primary/5 p-3">
                          <p className="mb-1 text-xs font-medium text-primary">
                            RM Conversation Focus
                          </p>
                          <p className="text-sm text-foreground">
                            {prospect.engagementAngles?.[0]?.label ||
                              prospect.recommendedNextStep ||
                              prospect.entryAngle}
                          </p>
                          {prospect.engagementAngles?.[0]?.recommendedTalkTrack && (
                            <p className="mt-1 text-xs text-muted-foreground">
                              {prospect.engagementAngles[0].recommendedTalkTrack}
                            </p>
                          )}
                          {prospect.whyPrioritized?.length ? (
                            <div className="mt-2 flex flex-wrap gap-1.5">
                              {prospect.whyPrioritized.slice(0, 3).map((reason) => (
                                <Badge
                                  key={reason}
                                  variant="outline"
                                  className="bg-card text-[10px]"
                                >
                                  {reason}
                                </Badge>
                              ))}
                            </div>
                          ) : null}
                        </div>

                        <div className="mt-3 flex items-center justify-between gap-3">
                          <div className="flex min-w-0 items-center gap-3">
                            {latestSignal && (
                              <div className="flex min-w-0 items-center gap-2">
                                <Badge
                                  variant="outline"
                                  className="text-[10px] capitalize"
                                >
                                  Evidence: {latestSignal.type}
                                </Badge>
                                <span className="truncate text-xs text-muted-foreground">
                                  {latestSignal.title}
                                </span>
                              </div>
                            )}
                          </div>
                          <div className="flex shrink-0 items-center gap-2">
                            <Badge variant="outline" className="bg-muted/50 text-[10px]">
                              Evidence: {linkedEvidenceCount}
                            </Badge>
                            <Badge variant="outline" className="bg-muted/50 text-[10px]">
                              Owner: {prospect.workflowState?.owner || "Unassigned"}
                            </Badge>
                            <span className="flex max-w-56 items-center gap-1 truncate text-[10px] text-muted-foreground">
                              <Clock className="h-3 w-3 shrink-0" />
                              {prospect.workflowState?.nextAction || "Review evidence"}
                            </span>
                          </div>
                        </div>

                        <div className="mt-3 flex flex-wrap gap-1.5">
                          {prospect.productFit.map((product) => (
                            <Badge
                              key={product}
                              variant="secondary"
                              className="text-[10px]"
                            >
                              {product}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>

          {filteredProspects.length === 0 && (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <Users className="mb-4 h-12 w-12 text-muted-foreground" />
              <h3 className="mb-1 text-lg font-semibold text-foreground">
                No prospects found
              </h3>
              <p className="text-sm text-muted-foreground">
                Try adjusting your search or filter criteria
              </p>
            </div>
          )}
        </div>
      </main>

      <AICopilotPanel isOpen={copilotOpen} onClose={() => setCopilotOpen(false)} />

      {!copilotOpen && <AICopilotButton onClick={() => setCopilotOpen(true)} />}
    </div>
  );
}
