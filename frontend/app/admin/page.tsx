const TABS = [
  { id: "overview", label: "Overview Dashboard" },
  { id: "cases", label: "Case Management" },
  { id: "field-workers", label: "Field Worker Management" },
  { id: "ai-settings", label: "AI Settings" },
  { id: "audit-log", label: "Audit Log" },
] as const;

export default function AdminPage() {
  return (
    <main className="mx-auto max-w-6xl px-6 py-16">
      <h1 className="text-3xl font-bold">Admin Console</h1>
      <p className="mt-2 text-slate-400">
        Five administrator tabs per FRS §6.6.
      </p>
      <nav className="mt-6 flex flex-wrap gap-2">
        {TABS.map((t) => (
          <span
            key={t.id}
            className="rounded-full border border-slate-700 bg-slate-900/60 px-4 py-1.5 text-sm text-slate-300"
          >
            {t.label}
          </span>
        ))}
      </nav>
      <p className="mt-6 rounded-lg border border-slate-800 bg-slate-900/60 p-4 text-sm text-slate-400">
        Scaffolded — each tab to be implemented.
      </p>
    </main>
  );
}
