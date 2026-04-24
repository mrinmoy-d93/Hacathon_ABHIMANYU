import Link from "next/link";

import { HealthCheck } from "@/components/HealthCheck";

export default function LandingPage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-5xl flex-col gap-12 px-6 py-16">
      <header className="flex flex-col gap-4">
        <p className="text-sm uppercase tracking-widest text-khojo-accent">
          Amnex Hackathon 2026 · UC34 · Social Impact
        </p>
        <h1 className="text-5xl font-bold tracking-tight">
          KHOJO — AI Missing Person Finder
        </h1>
        <p className="max-w-2xl text-lg text-slate-300">
          Artificial Intelligence (AI) that predicts how a missing person appears today
          and matches that prediction against a growing database of sighted individuals.
        </p>
        <p className="text-sm italic text-slate-400">
          &ldquo;AI suggests, the human decides.&rdquo;
        </p>
      </header>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <NavCard
          href="/register"
          title="Register"
          description="Create an account — community member, field worker, or administrator."
        />
        <NavCard
          href="/cases"
          title="Cases"
          description="Register a missing person case and view AI-generated match results."
        />
        <NavCard
          href="/field-worker"
          title="Field Worker"
          description="Verify matches in the field and submit Confirm / Not-a-Match feedback."
        />
        <NavCard
          href="/admin"
          title="Admin Console"
          description="Overview, case management, field workers, AI settings, audit log."
        />
      </section>

      <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
        <h2 className="mb-3 text-xl font-semibold">Backend connectivity</h2>
        <HealthCheck />
      </section>

      <footer className="pt-8 text-sm text-slate-500">
        FRS v1.1 · Team KHOJO · 24 April 2026
      </footer>
    </main>
  );
}

function NavCard({
  href,
  title,
  description,
}: {
  href: "/register" | "/cases" | "/field-worker" | "/admin";
  title: string;
  description: string;
}) {
  return (
    <Link
      href={href}
      className="group rounded-2xl border border-slate-800 bg-slate-900/60 p-5 transition hover:border-khojo-accent hover:bg-slate-900"
    >
      <h3 className="mb-1 text-lg font-semibold group-hover:text-khojo-accent">{title}</h3>
      <p className="text-sm text-slate-400">{description}</p>
    </Link>
  );
}
