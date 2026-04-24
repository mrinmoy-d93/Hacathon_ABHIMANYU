"use client";

import { useEffect } from "react";
import {
  AlertTriangle,
  Clock,
  FileCheck2,
  Files,
  Search,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Acronym } from "@/components/Acronym";
import { AIBadge } from "@/components/AIBadge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useAdminDashboard } from "@/lib/hooks/useAdmin";
import type { AdminDashboard } from "@/lib/types";

const STAT_META: Array<{
  key: keyof Pick<AdminDashboard, "total_cases" | "active_searches" | "matches_found" | "review_pending">;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  accent: string;
}> = [
  { key: "total_cases", label: "Total Cases", icon: Files, accent: "text-primary" },
  { key: "active_searches", label: "Active Searches", icon: Search, accent: "text-khojo-warning" },
  { key: "matches_found", label: "Matches Found", icon: FileCheck2, accent: "text-khojo-success" },
  { key: "review_pending", label: "Review Pending", icon: AlertTriangle, accent: "text-khojo-danger" },
];

export default function OverviewPage() {
  const { data, isLoading, error, refetch, isFetching } = useAdminDashboard();

  // Auto-refresh every 10 s.
  useEffect(() => {
    const id = window.setInterval(() => {
      refetch();
    }, 10_000);
    return () => window.clearInterval(id);
  }, [refetch]);

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h2 className="text-xl font-semibold text-primary">Overview</h2>
          <p className="text-sm text-muted-foreground">
            Live operations summary — auto-refreshes every 10 seconds.
            {isFetching && <span className="ml-2 text-xs">Refreshing…</span>}
          </p>
        </div>
        <AIBadge compact />
      </header>

      {error && (
        <Alert variant="destructive">
          <AlertTitle>Could not load dashboard</AlertTitle>
          <AlertDescription>{error.message}</AlertDescription>
        </Alert>
      )}

      {/* Stat cards */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {STAT_META.map(({ key, label, icon: Icon, accent }) => (
          <Card key={key}>
            <CardContent className="flex items-center justify-between p-5">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  {label}
                </p>
                <p className="mt-1 text-3xl font-bold text-primary">
                  {isLoading ? <Skeleton className="h-8 w-14" /> : data ? data[key] : "—"}
                </p>
              </div>
              <Icon className={`h-8 w-8 ${accent}`} aria-hidden="true" />
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-primary">Confidence distribution</CardTitle>
            <CardDescription>
              <Acronym short="AI" /> confidence buckets — High ≥ 80%, Medium 60–80%, Low &lt; 60%.
            </CardDescription>
          </CardHeader>
          <CardContent className="h-72">
            {isLoading ? (
              <Skeleton className="h-full w-full" />
            ) : data ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={[
                    { tier: "High", count: data.confidence_distribution.high, fill: "#15803d" },
                    { tier: "Medium", count: data.confidence_distribution.medium, fill: "#b45309" },
                    { tier: "Low", count: data.confidence_distribution.low, fill: "#b91c1c" },
                  ]}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="tier" stroke="hsl(var(--muted-foreground))" fontSize={12} />
                  <YAxis allowDecimals={false} stroke="hsl(var(--muted-foreground))" fontSize={12} />
                  <Tooltip
                    contentStyle={{
                      background: "hsl(var(--popover))",
                      borderColor: "hsl(var(--border))",
                      borderRadius: 8,
                    }}
                    labelStyle={{ color: "hsl(var(--foreground))" }}
                  />
                  <Bar dataKey="count" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center text-muted-foreground">
                No data yet
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-primary">Recent activity</CardTitle>
            <CardDescription>
              Last 10 audit entries — every <Acronym short="AI" /> decision is cryptographically
              signed.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="flex flex-col gap-2">
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-10 w-full" />
              </div>
            ) : data && data.recent_activity.length > 0 ? (
              <ul className="flex flex-col gap-2">
                {data.recent_activity.slice(0, 10).map((entry) => (
                  <li
                    key={entry.id}
                    className="flex items-start gap-3 rounded-md border bg-secondary/30 p-2 text-sm"
                  >
                    <Clock
                      className="mt-0.5 h-4 w-4 text-muted-foreground"
                      aria-hidden="true"
                    />
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-medium">{humanise(entry.action)}</p>
                      <p className="text-xs text-muted-foreground">
                        {new Date(entry.timestamp).toLocaleString()}
                        {entry.confidence_score !== null && (
                          <>
                            {" · "}
                            <span>
                              confidence {Math.round(entry.confidence_score * 100)}%
                            </span>
                          </>
                        )}
                      </p>
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="rounded-md border border-dashed p-6 text-center text-sm text-muted-foreground">
                No activity yet.
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function humanise(action: string): string {
  return action
    .replace(/_/g, " ")
    .replace(/\./g, " — ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}
