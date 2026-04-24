"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import { LogOut, Menu, Search, X } from "lucide-react";

import { useAuthStore } from "@/lib/authStore";
import { useLogout } from "@/lib/hooks/useAuth";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

/**
 * App-wide chrome: logo left, role badge + logout right, hamburger on phones.
 * Intentionally lightweight — individual screens handle their own content.
 */
export function AppShell({
  children,
  hideNav = false,
}: {
  children: React.ReactNode;
  hideNav?: boolean;
}) {
  const user = useAuthStore((s) => s.user);
  const isAuth = useAuthStore((s) => s.isAuthenticated());
  const logout = useLogout();
  const router = useRouter();
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);

  const roleLinks = user
    ? roleLinksFor(user.role)
    : ([] as { href: string; label: string }[]);

  const handleLogout = () => {
    logout();
    setMenuOpen(false);
    router.push("/");
  };

  return (
    <div className="min-h-screen bg-background">
      {!hideNav && (
        <header className="sticky top-0 z-40 border-b bg-background/95 backdrop-blur">
          <div className="mx-auto flex h-14 max-w-6xl items-center gap-4 px-4 sm:h-16">
            <Link href="/" className="flex items-center gap-2 font-bold text-primary">
              <Search className="h-5 w-5 text-accent" aria-hidden="true" />
              <span className="text-lg tracking-wide">KHOJO</span>
            </Link>

            {/* Desktop nav */}
            <nav className="ml-6 hidden items-center gap-1 md:flex" aria-label="Main navigation">
              {roleLinks.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  className={cn(
                    "rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                    pathname.startsWith(link.href)
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:bg-secondary hover:text-foreground"
                  )}
                >
                  {link.label}
                </Link>
              ))}
            </nav>

            <div className="ml-auto flex items-center gap-2">
              {user ? (
                <>
                  <span
                    className="hidden rounded-full border border-accent/40 bg-accent/10 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-accent sm:inline-flex"
                    aria-label={`Logged in as ${user.role}`}
                  >
                    {user.role.replace("_", " ")}
                  </span>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleLogout}
                    className="hidden sm:inline-flex"
                  >
                    <LogOut className="h-4 w-4" /> Sign out
                  </Button>
                </>
              ) : (
                isAuth === false && (
                  <Button asChild variant="outline" size="sm">
                    <Link href="/register">Sign in</Link>
                  </Button>
                )
              )}
              <Button
                variant="ghost"
                size="icon"
                className="md:hidden"
                onClick={() => setMenuOpen((o) => !o)}
                aria-label="Toggle menu"
                aria-expanded={menuOpen}
              >
                {menuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
              </Button>
            </div>
          </div>

          {/* Mobile menu */}
          {menuOpen && (
            <nav
              className="border-t bg-background md:hidden"
              aria-label="Mobile navigation"
            >
              <div className="mx-auto flex max-w-6xl flex-col gap-1 px-4 py-3">
                {roleLinks.map((link) => (
                  <Link
                    key={link.href}
                    href={link.href}
                    onClick={() => setMenuOpen(false)}
                    className={cn(
                      "rounded-md px-3 py-2 text-sm font-medium",
                      pathname.startsWith(link.href)
                        ? "bg-primary text-primary-foreground"
                        : "hover:bg-secondary"
                    )}
                  >
                    {link.label}
                  </Link>
                ))}
                {user && (
                  <>
                    <div className="mt-2 border-t pt-2 text-xs text-muted-foreground">
                      Signed in as <strong>{user.name}</strong> · {user.role.replace("_", " ")}
                    </div>
                    <Button variant="ghost" size="sm" onClick={handleLogout} className="justify-start">
                      <LogOut className="h-4 w-4" /> Sign out
                    </Button>
                  </>
                )}
              </div>
            </nav>
          )}
        </header>
      )}
      <main className="mx-auto max-w-6xl px-4 py-6 sm:py-8">{children}</main>
    </div>
  );
}

function roleLinksFor(role: string): { href: string; label: string }[] {
  switch (role) {
    case "family":
      return [
        { href: "/cases/new/details", label: "New case" },
        { href: "/cases", label: "My cases" },
      ];
    case "field_worker":
      return [{ href: "/field-worker/alerts", label: "Alerts" }];
    case "admin":
      return [
        { href: "/admin/overview", label: "Overview" },
        { href: "/admin/cases", label: "Cases" },
        { href: "/admin/field-workers", label: "Field Workers" },
        { href: "/admin/ai-settings", label: "Artificial Intelligence (AI) Settings" },
        { href: "/admin/audit-log", label: "Audit Log" },
      ];
    default:
      return [];
  }
}
