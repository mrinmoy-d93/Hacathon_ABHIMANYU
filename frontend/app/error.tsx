"use client";

import { useEffect } from "react";
import Link from "next/link";
import { AlertTriangle, ArrowLeft, MessageSquare, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";

/**
 * Root error boundary per FRS NFR-3 (graceful degradation).
 * Catches any unhandled render error in the app and shows a friendly message
 * with a recovery path and a "Send feedback" escape hatch.
 */
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Surface the error in the browser console so engineers can triage.
    console.error("Unhandled render error:", error);
  }, [error]);

  const feedbackHref =
    "mailto:support@khojo.example?subject=" +
    encodeURIComponent("KHOJO feedback — render error") +
    "&body=" +
    encodeURIComponent(
      `Digest: ${error.digest ?? "n/a"}\nMessage: ${error.message}\n\nPlease describe what you were doing when this happened:`
    );

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-6">
      <div className="max-w-md text-center">
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-destructive/10">
          <AlertTriangle className="h-7 w-7 text-destructive" aria-hidden="true" />
        </div>
        <h1 className="text-2xl font-bold text-primary">Something went wrong</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Please try again. Your work is saved — this is only a display hiccup.
          {error.digest && (
            <>
              {" "}
              Reference <code className="font-mono">{error.digest}</code>.
            </>
          )}
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-2">
          <Button onClick={reset}>
            <RefreshCw className="h-4 w-4" /> Try again
          </Button>
          <Button asChild variant="outline">
            <Link href="/">
              <ArrowLeft className="h-4 w-4" /> Home
            </Link>
          </Button>
          <Button asChild variant="ghost">
            <a href={feedbackHref}>
              <MessageSquare className="h-4 w-4" /> Send feedback
            </a>
          </Button>
        </div>
      </div>
    </div>
  );
}
