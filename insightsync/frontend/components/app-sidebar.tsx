"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Zap,
  Users,
  Sparkles,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navigation = [
  {
    name: "Overview",
    href: "/",
    icon: LayoutDashboard,
    description: "Intelligence highlights",
    status: "live" as const,
  },
  {
    name: "Priority Prospects",
    href: "/prospects",
    icon: Users,
    description: "High-potential companies",
    status: "live" as const,
  },
  {
    name: "Trigger Signals",
    href: "/signals",
    icon: Zap,
    description: "Market & news signals",
    status: "live" as const,
  },
];

export function AppSidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed inset-y-0 left-0 z-50 flex w-64 flex-col bg-sidebar text-sidebar-foreground">
      {/* Logo */}
      <div className="flex h-16 items-center gap-3 border-b border-sidebar-border px-6">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
          <Sparkles className="h-4 w-4 text-primary-foreground" />
        </div>
        <div className="flex flex-col">
          <span className="text-sm font-semibold text-sidebar-foreground">
            InsightSync
          </span>
          <span className="text-xs text-sidebar-foreground/60">
            Hang Seng Bank
          </span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 px-3 py-4">
        <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-wider text-sidebar-foreground/40">
          Prospecting Intelligence
        </p>
        {navigation.map((item) => {
          const isActive =
            pathname === item.href ||
            (item.href !== "/" && pathname.startsWith(item.href));
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                "group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                isActive
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground"
              )}
            >
              <item.icon
                className={cn(
                  "h-5 w-5 shrink-0",
                  isActive
                    ? "text-sidebar-primary"
                    : "text-sidebar-foreground/50 group-hover:text-sidebar-foreground/70"
                )}
              />
              <div className="flex flex-col">
                <span>{item.name}</span>
                <span
                  className={cn(
                    "text-xs",
                    isActive
                      ? "text-sidebar-foreground/60"
                      : "text-sidebar-foreground/40"
                  )}
                >
                  {item.description}
                </span>
              </div>
            </Link>
          );
        })}

      </nav>

      {/* User info */}
      <div className="border-t border-sidebar-border p-4">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-sidebar-accent text-sm font-medium text-sidebar-accent-foreground">
            MC
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-medium text-sidebar-foreground">
              Michael Chan
            </span>
            <span className="text-xs text-sidebar-foreground/60">
              Senior RM, Commercial Banking
            </span>
          </div>
        </div>
      </div>
    </aside>
  );
}
