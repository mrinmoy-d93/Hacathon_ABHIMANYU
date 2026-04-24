import Link from "next/link";
import { FileQuestion } from "lucide-react";

import { AppShell } from "@/components/AppShell";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <AppShell>
      <div className="mx-auto max-w-md py-12 text-center">
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-secondary">
          <FileQuestion className="h-7 w-7 text-accent" aria-hidden="true" />
        </div>
        <h1 className="text-2xl font-bold text-primary">Page not found</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          The page you tried to open doesn&apos;t exist or has moved.
        </p>
        <div className="mt-6">
          <Button asChild>
            <Link href="/">Back to home</Link>
          </Button>
        </div>
      </div>
    </AppShell>
  );
}
