"use client";

import { useEffect, useMemo, useState } from "react";
import { getJson } from "@/lib/api-client";
import type { Prospect, TriggerSignal } from "@/lib/mock-data";

interface MetadataOption {
  name: string;
  count: number;
}

interface BackendMetadataFilters {
  regions: MetadataOption[];
  segments: MetadataOption[];
  industries: MetadataOption[];
  signal_types: MetadataOption[];
  sources: MetadataOption[];
  datasets: MetadataOption[];
}

interface MetadataFilterOptions {
  industries: string[];
  regions: string[];
  sources: string[];
  signalTypes: string[];
  backendOnline: boolean;
}

function titleCase(value: string) {
  return value
    .replace(/[_-]/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatSource(value: string) {
  if (value.toLowerCase() === "hkma") return "HKMA";
  return titleCase(value);
}

function normalizeSignalType(value: string): TriggerSignal["type"] {
  const normalized = value.toLowerCase().replace(/[^a-z0-9]/g, "");
  if (normalized === "financing" || normalized === "funding") return "funding";
  if (normalized === "policy" || normalized === "macro") return "policy";
  if (normalized === "crossborder") return "crossborder";
  return "expansion";
}

function uniqueSorted(values: (string | undefined | null)[]) {
  return Array.from(
    new Set(values.filter((value): value is string => Boolean(value?.trim())))
  ).sort((a, b) => a.localeCompare(b));
}

function optionNames(options: MetadataOption[] | undefined) {
  return options?.map((option) => option.name).filter(Boolean) || [];
}

export function useMetadataFilters(
  prospects: Prospect[],
  triggerSignals: TriggerSignal[]
): MetadataFilterOptions {
  const [metadata, setMetadata] = useState<BackendMetadataFilters | null>(null);
  const [backendOnline, setBackendOnline] = useState(false);

  useEffect(() => {
    let isMounted = true;

    async function load() {
      try {
        const data = await getJson<BackendMetadataFilters>("/api/metadata/filters");
        if (isMounted) {
          setMetadata(data);
          setBackendOnline(true);
        }
      } catch {
        if (isMounted) {
          setMetadata(null);
          setBackendOnline(false);
        }
      }
    }

    load();

    return () => {
      isMounted = false;
    };
  }, []);

  return useMemo(() => {
    const industries = uniqueSorted(
      metadata?.industries?.length
        ? optionNames(metadata.industries).map(titleCase)
        : prospects.map((prospect) => prospect.industry)
    );
    const regions = uniqueSorted(
      metadata?.regions?.length
        ? optionNames(metadata.regions)
        : prospects.map((prospect) => prospect.region)
    );
    const sources = uniqueSorted(
      metadata?.sources?.length
        ? optionNames(metadata.sources).map(formatSource)
        : triggerSignals.map((signal) => signal.source)
    );
    const signalTypes = uniqueSorted(
      metadata?.signal_types?.length
        ? optionNames(metadata.signal_types).map(normalizeSignalType)
        : triggerSignals.map((signal) => signal.type)
    );

    return {
      industries: ["All", ...industries],
      regions: ["All", ...regions],
      sources: ["All", ...sources],
      signalTypes: ["All", ...signalTypes],
      backendOnline,
    };
  }, [backendOnline, metadata, prospects, triggerSignals]);
}
