"use client";

import Link from "next/link";
import { FilePlus2 } from "lucide-react";

import { AppShell } from "@/components/AppShell";
import { AuthHydrationGuard } from "@/components/AuthHydrationGuard";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

/**
 * Community Member landing — shortcut to start a new case.
 *
 * A per-user "my cases" listing endpoint doesn't exist in Phase 4, so we
 * direct users to the case-reference view once they have an identifier.
 */
export default function CasesPage() {
  return (
    <AppShell>
      <AuthHydrationGuard requiredRole={["family", "field_worker", "admin"]}>
        <div className="mx-auto max-w-xl">
          <Card>
            <CardHeader>
              <CardTitle className="text-primary">Your cases</CardTitle>
              <CardDescription>
                Register a new missing person case, or open an existing one by its reference.
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              <Button asChild size="lg">
                <Link href="/cases/new/details">
                  <FilePlus2 className="h-4 w-4" /> Register a new case
                </Link>
              </Button>
              <p className="text-xs text-muted-foreground">
                Tip: keep your <code className="font-mono">KHJ-YYYY-XXXXX</code> case reference
                handy — you can share it with a field worker to check status.
              </p>
            </CardContent>
          </Card>
        </div>
      </AuthHydrationGuard>
    </AppShell>
  );
}
