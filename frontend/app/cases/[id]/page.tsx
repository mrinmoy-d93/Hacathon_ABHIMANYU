"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, Calendar, MapPin } from "lucide-react";

import { AppShell } from "@/components/AppShell";
import { Acronym, AcronymProvider } from "@/components/Acronym";
import { AIBadge } from "@/components/AIBadge";
import { AuthHydrationGuard } from "@/components/AuthHydrationGuard";
import { ConfidenceBar } from "@/components/ConfidenceBar";
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
import { useCase } from "@/lib/hooks/useCases";
import type { CaseStatus } from "@/lib/types";

const STATUS_META: Record<CaseStatus, { label: string; variant: "success" | "warning" | "destructive" | "secondary" }> = {
  active: { label: "Active", variant: "warning" },
  under_review: { label: "Under review", variant: "warning" },
  found: { label: "Found", variant: "success" },
  closed: { label: "Closed", variant: "secondary" },
};

export default function CaseDetailPage() {
  return (
    <AppShell>
      <AcronymProvider>
        <AuthHydrationGuard requiredRole={["family", "field_worker", "admin"]}>
          <Inner />
        </AuthHydrationGuard>
      </AcronymProvider>
    </AppShell>
  );
}

function Inner() {
  const { id } = useParams<{ id: string }>();
  const caseId = typeof id === "string" ? decodeURIComponent(id) : "";
  const { data, isLoading, error } = useCase(caseId);

  if (isLoading) {
    return (
      <div className="mx-auto max-w-3xl flex flex-col gap-4">
        <Skeleton className="h-10 w-48" />
        <Skeleton className="h-60 w-full" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="mx-auto max-w-xl">
        <Alert variant="destructive">
          <AlertTitle>Case not found</AlertTitle>
          <AlertDescription>
            {error?.message ?? "This case reference could not be loaded."}
          </AlertDescription>
        </Alert>
        <Button className="mt-4" variant="outline" asChild>
          <Link href="/cases">
            <ArrowLeft className="h-4 w-4" /> Back to cases
          </Link>
        </Button>
      </div>
    );
  }

  const statusMeta = STATUS_META[data.status];
  const originalPhotos = data.photos.filter((p) => !p.is_predicted_aged);

  return (
    <div className="mx-auto max-w-3xl flex flex-col gap-4">
      <Button variant="ghost" size="sm" asChild className="self-start">
        <Link href="/cases">
          <ArrowLeft className="h-4 w-4" /> Back
        </Link>
      </Button>

      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <CardTitle className="text-primary">{data.person_name}</CardTitle>
              <CardDescription>
                Case reference <code className="font-mono">{data.case_id}</code>
              </CardDescription>
            </div>
            <Badge variant={statusMeta.variant}>{statusMeta.label}</Badge>
          </div>
        </CardHeader>
        <CardContent className="grid gap-4 text-sm sm:grid-cols-2">
          <DetailRow
            icon={<Calendar className="h-4 w-4" />}
            label="Year missing"
            value={String(data.year_missing)}
          />
          <DetailRow
            icon={<Calendar className="h-4 w-4" />}
            label="Age at disappearance"
            value={String(data.age_at_disappearance)}
          />
          <DetailRow
            icon={<Calendar className="h-4 w-4" />}
            label="Predicted present-day age"
            value={String(data.predicted_current_age)}
          />
          <DetailRow
            icon={<MapPin className="h-4 w-4" />}
            label="Last seen"
            value={data.last_seen_location}
          />
          {data.identifying_marks && (
            <div className="sm:col-span-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Identifying marks
              </p>
              <p className="mt-1 whitespace-pre-line">{data.identifying_marks}</p>
            </div>
          )}
        </CardContent>
      </Card>

      {originalPhotos.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-primary">Uploaded photos</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="grid gap-3 sm:grid-cols-3">
              {originalPhotos.map((p) => (
                <li key={p.id} className="flex flex-col gap-1">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={p.supabase_url}
                    alt={`Age ${p.age_at_photo}`}
                    className="aspect-square w-full rounded-md border object-cover"
                  />
                  <p className="text-center text-xs text-muted-foreground">
                    Age {p.age_at_photo}
                  </p>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-primary">
            <Acronym short="AI" /> matches
          </CardTitle>
          <CardDescription>
            Top candidates ranked by confidence. Matches are verified by trained officers before
            families are informed.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {data.matches.length === 0 ? (
            <p className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
              No matches yet. The system keeps searching — we&apos;ll notify you when something
              promising comes up.
            </p>
          ) : (
            <ul className="flex flex-col gap-3">
              {data.matches.map((m) => (
                <li
                  key={m.id}
                  className="flex items-start gap-3 rounded-lg border bg-card p-3"
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={m.candidate_photo_url}
                    alt="Candidate"
                    className="h-20 w-20 shrink-0 rounded-md border object-cover"
                  />
                  <div className="flex-1">
                    <div className="flex items-center gap-2 text-sm">
                      <Badge variant={m.status === "confirmed" ? "success" : m.status === "not_match" ? "destructive" : "secondary"}>
                        {m.status.replace("_", " ")}
                      </Badge>
                    </div>
                    <div className="mt-2">
                      <ConfidenceBar score={m.confidence_score} tier={m.tier} />
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <AIBadge compact />
    </div>
  );
}

function DetailRow({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div>
      <p className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        {icon} {label}
      </p>
      <p className="mt-0.5 text-base font-medium">{value}</p>
    </div>
  );
}
