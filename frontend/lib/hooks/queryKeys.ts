/** Centralised TanStack Query keys (prevents typos in invalidation calls). */
export const queryKeys = {
  health: ["health"] as const,
  case: (id: string) => ["case", id] as const,
  caseResult: (id: string) => ["case", id, "result"] as const,
  pendingMatches: ["matches", "pending"] as const,
  adminDashboard: ["admin", "dashboard"] as const,
  adminCases: (params: object) => ["admin", "cases", params] as const,
  adminSettings: ["admin", "settings"] as const,
  adminFieldWorkers: ["admin", "field-workers"] as const,
  auditLog: (params: object) => ["admin", "audit-log", params] as const,
};
