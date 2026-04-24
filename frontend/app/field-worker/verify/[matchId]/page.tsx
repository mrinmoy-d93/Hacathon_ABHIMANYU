"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import {
  ArrowLeft,
  BellRing,
  Calendar,
  CheckCircle2,
  Loader2,
  MapPin,
  PartyPopper,
  Sparkles,
  XCircle,
} from "lucide-react";

import { AppShell } from "@/components/AppShell";
import { Acronym, AcronymProvider } from "@/components/Acronym";
import { AIBadge } from "@/components/AIBadge";
import { AuthHydrationGuard } from "@/components/AuthHydrationGuard";
import { ConfidenceBar } from "@/components/ConfidenceBar";
import { NotMatchModal } from "@/components/NotMatchModal";
import { PhotoCompare } from "@/components/PhotoCompare";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "@/components/ui/toast";
import { useConfirmMatch, usePendingMatches } from "@/lib/hooks/useMatches";
import type { ConfirmMatchResponse, NotMatchResponse, PendingMatch } from "@/lib/types";
import { useCase } from "@/lib/hooks/useCases";

export default function VerifyPage() {
  return (
    <AppShell>
      <AcronymProvider>
        <AuthHydrationGuard requiredRole={["field_worker", "admin"]}>
          <VerifyInner />
        </AuthHydrationGuard>
      </AcronymProvider>
    </AppShell>
  );
}

function VerifyInner() {
  const { matchId: rawId } = useParams<{ matchId: string }>();
  const matchId = typeof rawId === "string" ? decodeURIComponent(rawId) : "";

  const { data: pending, isLoading, error } = usePendingMatches();
  const match = useMemo<PendingMatch | undefined>(
    () => pending?.find((m) => m.id === matchId),
    [pending, matchId]
  );
  const caseDetail = useCase(match?.case_id);

  const confirm = useConfirmMatch();
  const [confirmResult, setConfirmResult] = useState<ConfirmMatchResponse | null>(null);
  const [notMatchResult, setNotMatchResult] = useState<NotMatchResponse | null>(null);
  const [modalOpen, setModalOpen] = useState(false);

  if (isLoading) {
    return (
      <div className="mx-auto max-w-3xl flex flex-col gap-4">
        <Skeleton className="h-10 w-40" />
        <Skeleton className="h-72 w-full" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-xl">
        <Alert variant="destructive">
          <AlertTitle>Could not load match</AlertTitle>
          <AlertDescription>{error.message}</AlertDescription>
        </Alert>
      </div>
    );
  }

  if (!match && !confirmResult && !notMatchResult) {
    return (
      <div className="mx-auto max-w-xl">
        <Alert variant="warning">
          <AlertTitle>This match is no longer pending</AlertTitle>
          <AlertDescription>
            It may have been resolved by another officer. Return to your alerts list.
          </AlertDescription>
        </Alert>
        <Button asChild className="mt-4">
          <Link href="/field-worker/alerts">
            <ArrowLeft className="h-4 w-4" /> Back to alerts
          </Link>
        </Button>
      </div>
    );
  }

  if (confirmResult) {
    return <ConfirmedView result={confirmResult} />;
  }
  if (notMatchResult) {
    return <NotMatchView result={notMatchResult} />;
  }
  if (!match) return null;

  const onConfirm = async () => {
    try {
      const res = await confirm.mutateAsync({ matchId: match.id });
      setConfirmResult(res);
      toast.success("Match confirmed. Family notification dispatched.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not confirm match.");
    }
  };

  return (
    <div className="mx-auto max-w-3xl flex flex-col gap-4">
      <Button variant="ghost" size="sm" asChild className="self-start">
        <Link href="/field-worker/alerts">
          <ArrowLeft className="h-4 w-4" /> Alerts
        </Link>
      </Button>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-primary">
            <BellRing className="h-5 w-5 text-accent" aria-hidden="true" />
            Verify match — {match.person_name}
          </CardTitle>
          <CardDescription>
            Compare the <Acronym short="AI" />-predicted photo with the candidate sighting, then
            confirm or reject after a physical check.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-5">
          <PhotoCompare
            left={{
              src: caseDetail.data?.photos.find((p) => p.is_predicted_aged)?.supabase_url ?? null,
              label: "AI-aged prediction",
              caption: caseDetail.data?.predicted_current_age
                ? `Predicted at age ${caseDetail.data.predicted_current_age}`
                : undefined,
            }}
            right={{
              src: match.candidate_photo_url,
              label: "Candidate sighting",
              caption: match.explanation,
            }}
          />

          <dl className="grid gap-3 rounded-lg border bg-secondary/40 p-3 text-sm sm:grid-cols-2">
            <DetailItem
              icon={<Calendar className="h-4 w-4" />}
              label="Age at disappearance"
              value={caseDetail.data?.age_at_disappearance?.toString() ?? "—"}
            />
            <DetailItem
              icon={<Calendar className="h-4 w-4" />}
              label="Year missing"
              value={caseDetail.data?.year_missing?.toString() ?? "—"}
            />
            <DetailItem
              icon={<MapPin className="h-4 w-4" />}
              label="Last seen"
              value={caseDetail.data?.last_seen_location ?? "—"}
            />
            <DetailItem
              icon={<Sparkles className="h-4 w-4" />}
              label="Tier"
              value={
                <Badge
                  variant={
                    match.tier === "high"
                      ? "success"
                      : match.tier === "medium"
                        ? "warning"
                        : "destructive"
                  }
                >
                  {match.tier}
                </Badge>
              }
            />
          </dl>

          <ConfidenceBar score={match.confidence_score} tier={match.tier} />

          <AIBadge />

          <div className="grid gap-2 sm:grid-cols-2">
            <Button
              variant="success"
              size="xl"
              onClick={onConfirm}
              disabled={confirm.isPending}
            >
              {confirm.isPending ? (
                <Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" />
              ) : (
                <CheckCircle2 className="h-5 w-5" aria-hidden="true" />
              )}
              Confirm Match
            </Button>
            <Button
              variant="warning"
              size="xl"
              onClick={() => setModalOpen(true)}
              disabled={confirm.isPending}
            >
              <XCircle className="h-5 w-5" aria-hidden="true" />
              Not a Match
            </Button>
          </div>
        </CardContent>
      </Card>

      <NotMatchModal
        matchId={match.id}
        open={modalOpen}
        onOpenChange={setModalOpen}
        onSuccess={(res) => setNotMatchResult(res)}
      />
    </div>
  );
}

function DetailItem({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div>
      <dt className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        {icon} {label}
      </dt>
      <dd className="mt-0.5 text-sm font-medium">{value}</dd>
    </div>
  );
}

function ConfirmedView({ result }: { result: ConfirmMatchResponse }) {
  return (
    <div className="mx-auto max-w-xl flex flex-col gap-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-khojo-success">
            <CheckCircle2 className="h-6 w-6" aria-hidden="true" />
            Match confirmed
          </CardTitle>
          <CardDescription>The family has been notified and the case is now marked as found.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 text-sm">
          <Alert variant="success">
            <AlertTitle>Family notification dispatched</AlertTitle>
            <AlertDescription>
              Message composed via <strong>{result.provider_used}</strong>.
            </AlertDescription>
          </Alert>
          <p className="text-muted-foreground">{result.explanation}</p>
          <Button asChild>
            <Link href="/field-worker/alerts">
              <ArrowLeft className="h-4 w-4" /> Return to alerts
            </Link>
          </Button>
        </CardContent>
      </Card>
      <AIBadge compact />
    </div>
  );
}

function NotMatchView({ result }: { result: NotMatchResponse }) {
  const pct = Math.min(
    100,
    Math.round((result.feedback_pool_size / 50) * 100)
  );
  return (
    <div className="mx-auto max-w-xl flex flex-col gap-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-primary">
            <Sparkles className="h-5 w-5 text-accent" aria-hidden="true" />
            Error vector captured
          </CardTitle>
          <CardDescription>
            Our <Acronym short="AI" /> will learn from this mismatch. Thank you for the feedback.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 text-sm">
          <div className="rounded-lg border bg-secondary/40 p-3">
            <div className="mb-2 flex items-center justify-between text-xs text-muted-foreground">
              <span>Feedback pool</span>
              <span>
                <strong>{result.feedback_pool_size}</strong> of 50 samples
              </span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-secondary">
              <div
                className="h-full bg-accent transition-[width]"
                style={{ width: `${pct}%` }}
                aria-hidden="true"
              />
            </div>
          </div>
          {result.training_cycle_triggered ? (
            <Alert variant="success">
              <PartyPopper className="h-4 w-4" />
              <AlertTitle>You just triggered a model update!</AlertTitle>
              <AlertDescription>
                Fine-tuning is running with the new examples. The next KHOJO release will be a
                little bit smarter thanks to you.
              </AlertDescription>
            </Alert>
          ) : (
            <p className="text-muted-foreground">
              {50 - result.feedback_pool_size} more samples until the next automatic model update.
            </p>
          )}
          <p className="text-muted-foreground">{result.explanation}</p>
          <Button asChild>
            <Link href="/field-worker/alerts">
              <ArrowLeft className="h-4 w-4" /> Return to alerts
            </Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
