"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { useAuthStore } from "@/lib/authStore";

/**
 * Wraps the app in a TanStack Query client and triggers the Zustand auth
 * store's deferred hydration on mount so SSR markup stays deterministic
 * (see `skipHydration: true` in lib/authStore.ts).
 */
export function QueryProvider({ children }: { children: React.ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 10_000,
            retry: (failureCount, error) => {
              const message = error instanceof Error ? error.message : "";
              if (message.includes("401") || message.includes("403")) return false;
              return failureCount < 2;
            },
          },
        },
      })
  );

  useEffect(() => {
    void useAuthStore.persist.rehydrate();
  }, []);

  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
