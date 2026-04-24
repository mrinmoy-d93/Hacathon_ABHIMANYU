import Link from "next/link";
import { ArrowRight, Sparkles, Users, Shield, FileSearch } from "lucide-react";

import { AppShell } from "@/components/AppShell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { HealthCheck } from "@/components/HealthCheck";

export default function LandingPage() {
  return (
    <AppShell>
      <section className="flex flex-col gap-5 py-6">
        <p className="inline-flex items-center gap-2 text-sm font-semibold uppercase tracking-widest text-accent">
          <Sparkles className="h-4 w-4" aria-hidden="true" />
          Amnex Hackathon 2026 · UC34 · Social Impact
        </p>
        <h1 className="text-3xl font-bold tracking-tight text-primary sm:text-5xl">
          KHOJO — Find the missing, faster.
        </h1>
        <p className="max-w-2xl text-base text-muted-foreground sm:text-lg">
          Artificial Intelligence (AI) that predicts how a missing person looks today and matches
          that prediction against a growing database of sightings — verified by trained officers
          before any family is informed.
        </p>
        <p className="text-sm italic text-muted-foreground">
          &ldquo;AI suggests, the human decides.&rdquo;
        </p>
        <div className="flex flex-wrap gap-3 pt-2">
          <Button asChild size="lg">
            <Link href="/register">
              Get started <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
          <Button asChild variant="outline" size="lg">
            <Link href="#roles">Explore roles</Link>
          </Button>
        </div>
      </section>

      <section id="roles" className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <RoleCard
          icon={<Users className="h-5 w-5" />}
          href="/register"
          title="Community Member"
          description="Register a missing person case, upload photos, track the search in real time."
        />
        <RoleCard
          icon={<FileSearch className="h-5 w-5" />}
          href="/register"
          title="Field Worker"
          description="Verify AI-generated matches in person. Every Confirm or Not-a-Match improves the model."
        />
        <RoleCard
          icon={<Shield className="h-5 w-5" />}
          href="/register"
          title="Administrator"
          description="Oversee cases, tune AI thresholds with zero code, audit every decision."
        />
      </section>

      <section className="mt-10">
        <Card>
          <CardHeader>
            <CardTitle>Backend connectivity</CardTitle>
            <CardDescription>Live status from the KHOJO API.</CardDescription>
          </CardHeader>
          <CardContent>
            <HealthCheck />
          </CardContent>
        </Card>
      </section>

      <footer className="mt-10 text-center text-sm text-muted-foreground">
        FRS v1.1 · Team KHOJO · 24 April 2026
      </footer>
    </AppShell>
  );
}

function RoleCard({
  icon,
  href,
  title,
  description,
}: {
  icon: React.ReactNode;
  href: string;
  title: string;
  description: string;
}) {
  return (
    <Link href={href} className="group">
      <Card className="h-full transition-colors group-hover:border-accent">
        <CardHeader>
          <div className="flex items-center gap-2 text-accent">
            {icon}
            <CardTitle className="text-lg">{title}</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">{description}</p>
        </CardContent>
      </Card>
    </Link>
  );
}
