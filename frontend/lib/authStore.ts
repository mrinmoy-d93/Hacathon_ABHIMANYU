/**
 * Zustand auth store persisted to localStorage.
 *
 * Next.js renders server-side initially, so every accessor is guarded against
 * `window === undefined`. The store hydrates on the client via the built-in
 * `persist` middleware (skipHydration keeps SSR HTML deterministic).
 */
import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

import type { User } from "./types";

interface AuthState {
  token: string | null;
  user: User | null;
  expiresAt: number | null; // epoch ms
  isHydrated: boolean;

  setSession: (input: { token: string; user: User; expiresIn: number }) => void;
  clearSession: () => void;
  isAuthenticated: () => boolean;
  markHydrated: () => void;
}

const safeStorage = () =>
  createJSONStorage(() =>
    typeof window !== "undefined"
      ? window.localStorage
      : {
          getItem: () => null,
          setItem: () => undefined,
          removeItem: () => undefined,
        }
  );

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      user: null,
      expiresAt: null,
      isHydrated: false,

      setSession: ({ token, user, expiresIn }) => {
        set({
          token,
          user,
          expiresAt: Date.now() + expiresIn * 1000,
        });
      },

      clearSession: () => {
        set({ token: null, user: null, expiresAt: null });
      },

      isAuthenticated: () => {
        const { token, expiresAt } = get();
        if (!token) return false;
        if (expiresAt && expiresAt <= Date.now()) return false;
        return true;
      },

      markHydrated: () => set({ isHydrated: true }),
    }),
    {
      name: "khojo.auth",
      storage: safeStorage(),
      skipHydration: true,
      partialize: ({ token, user, expiresAt }) => ({ token, user, expiresAt }),
      onRehydrateStorage: () => (state) => {
        state?.markHydrated();
      },
    }
  )
);

/**
 * Returns the current access token without triggering a React subscription.
 * Safe on the server: returns `null` outside the browser.
 */
export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return useAuthStore.getState().token;
}
