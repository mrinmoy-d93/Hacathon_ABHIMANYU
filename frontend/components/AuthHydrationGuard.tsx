"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Search } from "lucide-react";

import { useAuthStore } from "@/lib/authStore";
import type { UserRole } from "@/lib/types";

/**
 * Gates a subtree on Zustand hydration so SSR/CSR markup don't diverge
 * (the persist middleware uses `skipHydration: true`).
 *
 * Shows a splash while rehydrating; redirects home if authentication or the
 * required role fails once the store is ready.
 */
export function AuthHydrationGuard({
  children,
  requiredRole,
  redirectTo = "/",
}: {
  children: React.ReactNode;
  requiredRole?: UserRole | UserRole[];
  redirectTo?: string;
}) {
  const hydrated = useAuthStore((s) => s.isHydrated);
  const user = useAuthStore((s) => s.user);
  const isAuth = useAuthStore((s) => s.isAuthenticated());
  const router = useRouter();

  useEffect(() => {
    if (!hydrated || requiredRole === undefined) return;
    if (!isAuth || !user) {
      router.replace(redirectTo);
      return;
    }
    const roles = Array.isArray(requiredRole) ? requiredRole : [requiredRole];
    if (!roles.includes(user.role)) {
      router.replace(redirectTo);
    }
  }, [hydrated, isAuth, user, requiredRole, redirectTo, router]);

  if (!hydrated) {
    return <Splash />;
  }

  if (requiredRole !== undefined) {
    const roles = Array.isArray(requiredRole) ? requiredRole : [requiredRole];
    if (!isAuth || !user || !roles.includes(user.role)) {
      return <Splash />;
    }
  }

  return <>{children}</>;
}

function Splash() {
  return (
    <div className="flex min-h-screen items-center justify-center" aria-busy="true">
      <div className="flex flex-col items-center gap-3 text-muted-foreground">
        <Search className="h-8 w-8 animate-pulse text-accent" aria-hidden="true" />
        <p className="text-sm">Loading KHOJO…</p>
      </div>
    </div>
  );
}
