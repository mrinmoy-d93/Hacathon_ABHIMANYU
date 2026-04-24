"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Loader2,
  ScanFace,
  Sparkles,
  TrendingUp,
  Wand2,
} from "lucide-react";

import { AppShell } from "@/components/AppShell";
import { Acronym, AcronymProvider } from "@/components/Acronym";
import { AuthHydrationGuard } from "@/components/AuthHydrationGuard";
import { StepIndicator } from "@/components/StepIndicator";
import { AIBadge } from "@/components/AIBadge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { useCaseResult, useProcessCase } from "@/lib/hooks/useCases";
import { cn } from "@/lib/utils";

const STEPS = [
  { icon: ScanFace, label: "Detecting faces", t: 0 },
  { icon: TrendingUp, label: "Computing aging trajectory", t: 3 },
  { icon: Wand2, label: "Aging to predicted present-day age", t: 7 },
  { icon: Sparkles, label: "Searching database", t: 12 },
  { icon: CheckCircle2, label: "Almost ready", t: 18 },
] as const;

export default function ProcessingPage() {
  return (
    <AppShell>
      <AcronymProvider>
        <AuthHydrationGuard requiredRole={["family", "field_worker", "admin"]}>
          <Suspense
            fallback={
              <div className="flex justify-center py-12 text-muted-foreground">
                <Loader2 className="h-6 w-6 animate-spin" aria-hidden="true" />
              </div>
            }
          >
            <ProcessingInner />
          </Suspense>
        </AuthHydrationGuard>
      </AcronymProvider>
    </AppShell>
  );
}

function ProcessingInner() {
  const router = useRouter();
  const params = useSearchParams();
  const caseId = params.get("case_id") ?? "";
  const result = useCaseResult(caseId || undefined);
  const reprocess = useProcessCase(caseId);

  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const id = window.setInterval(() => setElapsed((e) => e + 1), 1000);
    return () => window.clearInterval(id);
  }, []);

  useEffect(() => {
    if (result.data?.status === "complete") {
      router.replace(`/cases/new/result?case_id=${encodeURIComponent(caseId)}`);
    }
  }, [result.data?.status, caseId, router]);

  if (!caseId) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Missing case reference</AlertTitle>
        <AlertDescription>Please start a new case from the beginning.</AlertDescription>
      </Alert>
    );
  }

  const activeStep = STEPS.reduce(
    (acc, s, i) => (elapsed >= s.t ? i : acc),
    0
  );
  const status = result.data?.status ?? "processing";
  const progressPct = Math.min(95, Math.round((activeStep / (STEPS.length - 1)) * 100) + 5);

  if (status === "error" || result.isError) {
    return (
      <div className="mx-auto max-w-xl">
        <StepIndicator step={3} />
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-destructive">
              <AlertTriangle className="h-5 w-5" aria-hidden="true" />
              Something went wrong
            </CardTitle>
            <CardDescription>
              Our <Acronym short="AI" /> service is temporarily unreachable. Please try again in a
              moment — your photos and details are saved.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <Alert variant="destructive">
              <AlertTitle>Pipeline failed</AlertTitle>
              <AlertDescription>
                {result.error?.message ?? "Unknown error from the processing server."}
              </AlertDescription>
            </Alert>
            <div className="flex gap-2">
              <Button
                onClick={() => reprocess.mutate()}
                disabled={reprocess.isPending}
              >
                {reprocess.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                Retry processing
              </Button>
              <Button variant="outline" onClick={() => router.push("/cases")}>
                Back to my cases
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-xl">
      <StepIndicator step={3} />
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-primary">
            <Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" />
            Running the <Acronym short="AI" /> pipeline
          </CardTitle>
          <CardDescription>
            This usually takes under 30 seconds. We&apos;ll open your result screen automatically
            when it&apos;s ready.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <Progress value={progressPct} aria-label="Processing progress" />
          <ol className="flex flex-col gap-2" aria-live="polite">
            {STEPS.map((step, i) => {
              const Icon = step.icon;
              const state = i < activeStep ? "done" : i === activeStep ? "active" : "todo";
              return (
                <li
                  key={step.label}
                  className={cn(
                    "flex items-center gap-3 rounded-md border p-3 text-sm transition-colors",
                    state === "done" && "border-khojo-success/40 bg-khojo-success/5",
                    state === "active" && "border-accent bg-accent/5",
                    state === "todo" && "border-border bg-background text-muted-foreground"
                  )}
                >
                  {state === "done" ? (
                    <CheckCircle2 className="h-4 w-4 text-khojo-success" aria-hidden="true" />
                  ) : state === "active" ? (
                    <Loader2 className="h-4 w-4 animate-spin text-accent" aria-hidden="true" />
                  ) : (
                    <Icon className="h-4 w-4" aria-hidden="true" />
                  )}
                  <span
                    className={cn(
                      state === "active" && "font-semibold text-primary",
                      state === "done" && "text-khojo-success"
                    )}
                  >
                    {step.label}…
                  </span>
                </li>
              );
            })}
          </ol>
          <AIBadge compact />
          <p className="text-center text-xs text-muted-foreground">
            Case reference <code className="font-mono">{caseId}</code> · elapsed {elapsed}s
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
