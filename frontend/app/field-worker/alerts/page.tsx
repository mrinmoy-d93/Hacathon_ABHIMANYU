"use client";

import Link from "next/link";
import { BellRing, CheckCircle2, Clock } from "lucide-react";

import { AppShell } from "@/components/AppShell";
import { Acronym, AcronymProvider } from "@/components/Acronym";
import { AuthHydrationGuard } from "@/components/AuthHydrationGuard";
import { ConfidenceBar } from "@/components/ConfidenceBar";
import { AIBadge } from "@/components/AIBadge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { usePendingMatches } from "@/lib/hooks/useMatches";
import type { PendingMatch } from "@/lib/types";

export default function AlertsPage() {
  return (
    <AppShell>
      <AcronymProvider>
        <AuthHydrationGuard requiredRole={["field_worker", "admin"]}>
          <AlertsInner />
        </AuthHydrationGuard>
      </AcronymProvider>
    </AppShell>
  );
}

function AlertsInner() {
  const { data, isLoading, error } = usePendingMatches();

  return (
    <div className="mx-auto max-w-3xl flex flex-col gap-4">
      <header className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold text-primary">
            <BellRing className="h-6 w-6 text-accent" aria-hidden="true" />
            Alerts
          </h1>
          <p className="text-sm text-muted-foreground">
            Every pending match is waiting for a physical verification. Tap a card to begin.
          </p>
        </div>
        <AIBadge compact />
      </header>

      {isLoading && (
        <div className="flex flex-col gap-3">
          <Skeleton className="h-28 w-full" />
          <Skeleton className="h-28 w-full" />
          <Skeleton className="h-28 w-full" />
        </div>
      )}

      {error && (
        <Alert variant="destructive">
          <AlertTitle>Could not load alerts</AlertTitle>
          <AlertDescription>{error.message}</AlertDescription>
        </Alert>
      )}

      {!isLoading && data && data.length === 0 && (
        <EmptyState />
      )}

      {data && data.length > 0 && (
        <ul className="flex flex-col gap-3">
          {[...data]
            .sort((a, b) => b.confidence_score - a.confidence_score)
            .map((m) => (
              <MatchCard key={m.id} match={m} />
            ))}
        </ul>
      )}
    </div>
  );
}

function MatchCard({ match }: { match: PendingMatch }) {
  return (
    <li>
      <Card className="transition-colors hover:border-accent">
        <CardContent className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={match.candidate_photo_url}
            alt={match.person_name}
            className="h-24 w-24 shrink-0 rounded-md border object-cover"
          />
          <div className="min-w-0 flex-1 flex flex-col gap-1.5">
            <p className="flex items-center gap-2 text-sm font-semibold text-primary">
              {match.person_name}
            </p>
            <p className="flex items-center gap-1 text-xs text-muted-foreground">
              <Clock className="h-3 w-3" aria-hidden="true" /> Opened{" "}
              {new Date(match.created_at).toLocaleString()}
            </p>
            <ConfidenceBar score={match.confidence_score} tier={match.tier} />
          </div>
          <Button asChild className="sm:self-center">
            <Link href={`/field-worker/verify/${encodeURIComponent(match.id)}`}>
              Verify <CheckCircle2 className="h-4 w-4" />
            </Link>
          </Button>
        </CardContent>
      </Card>
    </li>
  );
}

function EmptyState() {
  return (
    <Card>
      <CardContent className="flex flex-col items-center gap-2 py-10 text-center text-muted-foreground">
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-secondary">
          <BellRing className="h-7 w-7 text-accent" aria-hidden="true" />
        </div>
        <p className="font-semibold text-foreground">No alerts yet</p>
        <p className="max-w-sm text-sm">
          You&apos;ll get notified here when the <Acronym short="AI" /> finds a possible match in
          your assigned zone.
        </p>
      </CardContent>
    </Card>
  );
}
