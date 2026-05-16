"use client";

import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { FileSearch, BarChart3, Sparkles, Zap, Clock, AlertCircle } from "lucide-react";

// Loading skeleton for summary cards
export function SummaryCardSkeleton() {
  return (
    <Card className="border-border">
      <CardContent className="p-5">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <Skeleton className="mb-2 h-3 w-20" />
            <Skeleton className="mb-2 h-7 w-16" />
            <Skeleton className="h-3 w-24" />
          </div>
          <Skeleton className="h-10 w-10 rounded-lg" />
        </div>
      </CardContent>
    </Card>
  );
}

// Loading skeleton for charts
export function ChartSkeleton() {
  return (
    <Card className="border-border">
      <CardHeader className="pb-2 pt-4 px-4">
        <Skeleton className="h-3 w-20" />
      </CardHeader>
      <CardContent className="px-4 pb-4">
        <div className="h-[180px] flex items-center justify-center">
          <div className="space-y-3 w-full">
            <Skeleton className="h-6 w-full" />
            <Skeleton className="h-6 w-4/5" />
            <Skeleton className="h-6 w-3/5" />
            <Skeleton className="h-6 w-2/5" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// Loading skeleton for prospect cards
export function ProspectCardSkeleton() {
  return (
    <Card className="border-border">
      <CardContent className="p-4">
        <div className="mb-3 flex items-start justify-between">
          <div className="flex items-center gap-2.5">
            <Skeleton className="h-10 w-10 rounded-lg" />
            <div>
              <Skeleton className="mb-1 h-4 w-32" />
              <Skeleton className="h-2.5 w-24" />
            </div>
          </div>
        </div>
        <div className="mb-3 flex items-center gap-1.5">
          <Skeleton className="h-4 w-8 rounded-full" />
          <Skeleton className="h-4 w-16 rounded-full" />
          <Skeleton className="h-4 w-14 rounded-full" />
        </div>
        <div className="mb-3">
          <Skeleton className="mb-1 h-2 w-full" />
          <Skeleton className="h-1.5 w-full rounded-full" />
        </div>
        <Skeleton className="mb-3 h-6 w-full" />
        <div className="flex gap-1">
          <Skeleton className="h-4 w-16 rounded-full" />
          <Skeleton className="h-4 w-20 rounded-full" />
        </div>
      </CardContent>
    </Card>
  );
}

// Loading skeleton for prospect table rows
export function ProspectRowSkeleton() {
  return (
    <tr className="border-b border-border">
      <td className="py-3 px-3">
        <div className="flex items-center gap-2">
          <Skeleton className="h-8 w-8 rounded" />
          <div>
            <Skeleton className="mb-1 h-3.5 w-28" />
            <Skeleton className="h-2.5 w-20" />
          </div>
        </div>
      </td>
      <td className="py-3 px-3">
        <Skeleton className="h-4 w-6 rounded-full" />
      </td>
      <td className="py-3 px-3">
        <Skeleton className="h-3 w-16" />
      </td>
      <td className="py-3 px-3">
        <Skeleton className="h-3 w-14" />
      </td>
      <td className="py-3 px-3">
        <div className="flex gap-1">
          <Skeleton className="h-4 w-12 rounded-full" />
          <Skeleton className="h-4 w-14 rounded-full" />
        </div>
      </td>
      <td className="py-3 px-3">
        <Skeleton className="h-3 w-24" />
      </td>
      <td className="py-3 px-3">
        <Skeleton className="h-5 w-5" />
      </td>
    </tr>
  );
}

// Loading skeleton for detail page sections
export function DetailSectionSkeleton() {
  return (
    <Card className="border-border">
      <CardHeader className="pb-2 pt-4 px-4">
        <Skeleton className="h-4 w-28" />
      </CardHeader>
      <CardContent className="px-4 pb-4">
        <div className="space-y-2">
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-4/5" />
          <Skeleton className="h-3 w-3/5" />
        </div>
      </CardContent>
    </Card>
  );
}

// Empty state component - configurable
interface EmptyStateProps {
  icon?: "search" | "chart" | "ai" | "signal" | "timeline" | "alert";
  title: string;
  description?: string;
  action?: React.ReactNode;
}

const emptyStateIcons = {
  search: FileSearch,
  chart: BarChart3,
  ai: Sparkles,
  signal: Zap,
  timeline: Clock,
  alert: AlertCircle,
};

export function EmptyState({ icon = "search", title, description, action }: EmptyStateProps) {
  // Safely get the icon component with a fallback to FileSearch
  const IconComponent = emptyStateIcons[icon] || FileSearch;

  return (
    <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
      <div className="mb-4 rounded-full bg-muted p-3">
        <IconComponent className="h-6 w-6 text-muted-foreground" />
      </div>
      <h3 className="mb-1 text-sm font-medium text-foreground">{title}</h3>
      {description && (
        <p className="mb-4 max-w-sm text-xs text-muted-foreground">{description}</p>
      )}
      {action}
    </div>
  );
}

// Placeholder value component - shows when data is unavailable
interface PlaceholderValueProps {
  value: string | number | null | undefined;
  fallback?: string;
  className?: string;
}

export function PlaceholderValue({ value, fallback = "—", className = "" }: PlaceholderValueProps) {
  if (value === null || value === undefined || value === "") {
    return <span className={`text-muted-foreground ${className}`}>{fallback}</span>;
  }
  return <span className={className}>{value}</span>;
}

// Optional section wrapper - hides section when no content
interface OptionalSectionProps {
  show: boolean;
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

export function OptionalSection({ show, children, fallback }: OptionalSectionProps) {
  if (!show) {
    return fallback || null;
  }
  return <>{children}</>;
}
