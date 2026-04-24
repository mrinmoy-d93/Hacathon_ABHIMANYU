"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { AppShell } from "@/components/AppShell";
import { AcronymProvider } from "@/components/Acronym";
import { AuthHydrationGuard } from "@/components/AuthHydrationGuard";
import { cn } from "@/lib/utils";

const TABS = [
  { href: "/admin/overview", label: "Overview" },
  { href: "/admin/cases", label: "Cases" },
  { href: "/admin/field-workers", label: "Field Workers" },
  { href: "/admin/ai-settings", label: "AI Settings" },
  { href: "/admin/audit-log", label: "Audit Log" },
];

/**
 * Admin console shell — five tabs per FRS §6.6.
 * Role-guarded; non-admins are redirected to the landing page by
 * AuthHydrationGuard.
 */
export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <AppShell>
      <AuthHydrationGuard requiredRole="admin">
        <AcronymProvider>
          <div className="mb-5">
            <h1 className="text-2xl font-bold tracking-tight text-primary">Administrator console</h1>
            <p className="text-sm text-muted-foreground">
              Five-tab operations console — FRS §6.6.
            </p>
          </div>
          <nav
            className="mb-6 -mx-4 overflow-x-auto px-4 sm:mx-0 sm:px-0"
            aria-label="Admin tabs"
          >
            <ul className="flex min-w-max gap-1 rounded-md bg-muted p-1">
              {TABS.map((tab) => {
                const active = pathname.startsWith(tab.href);
                return (
                  <li key={tab.href}>
                    <Link
                      href={tab.href}
                      className={cn(
                        "inline-flex items-center whitespace-nowrap rounded-sm px-3 py-1.5 text-sm font-medium transition-colors",
                        active
                          ? "bg-background text-foreground shadow-sm"
                          : "text-muted-foreground hover:text-foreground"
                      )}
                      aria-current={active ? "page" : undefined}
                    >
                      {tab.label}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </nav>
          {children}
        </AcronymProvider>
      </AuthHydrationGuard>
    </AppShell>
  );
}
