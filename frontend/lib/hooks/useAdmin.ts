"use client";
/** TanStack Query hooks for /api/admin (FRS §6.6 five tabs). */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { adminApi } from "../api";
import type {
  AdminCasesPage,
  AdminDashboard,
  AuditLogPage,
  CaseStatus,
  FieldWorkerRow,
  Settings,
  SettingsUpdate,
} from "../types";
import { queryKeys } from "./queryKeys";

export function useAdminDashboard() {
  return useQuery<AdminDashboard, Error>({
    queryKey: queryKeys.adminDashboard,
    queryFn: () => adminApi.dashboard(),
  });
}

export function useAdminCases(params: { status?: CaseStatus; page?: number; page_size?: number } = {}) {
  return useQuery<AdminCasesPage, Error>({
    queryKey: queryKeys.adminCases(params),
    queryFn: () => adminApi.cases(params),
    placeholderData: (prev) => prev,
  });
}

export function useApproveCase() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (caseId: string) => adminApi.approveCase(caseId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "cases"] }),
  });
}

export function useRejectCase() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ caseId, reason }: { caseId: string; reason: string }) =>
      adminApi.rejectCase(caseId, reason),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "cases"] }),
  });
}

export function useAdminFieldWorkers() {
  return useQuery<FieldWorkerRow[], Error>({
    queryKey: queryKeys.adminFieldWorkers,
    queryFn: () => adminApi.fieldWorkers(),
  });
}

export function useAdminSettings() {
  return useQuery<Settings, Error>({
    queryKey: queryKeys.adminSettings,
    queryFn: () => adminApi.settings(),
  });
}

export function useUpdateSettings() {
  const qc = useQueryClient();
  return useMutation<Settings, Error, SettingsUpdate>({
    mutationFn: (body) => adminApi.updateSettings(body),
    onSuccess: (data) => {
      qc.setQueryData(queryKeys.adminSettings, data);
    },
  });
}

export function useAuditLog(
  params: { from?: string; to?: string; page?: number; page_size?: number } = {}
) {
  return useQuery<AuditLogPage, Error>({
    queryKey: queryKeys.auditLog(params),
    queryFn: () => adminApi.auditLog(params),
    placeholderData: (prev) => prev,
  });
}

/**
 * Returns a mutator that triggers the audit-log CSV export and pushes the
 * download through the browser. The response is streamed from the backend —
 * see adminApi.exportAuditLog for the raw Response handling.
 */
export function useExportAuditLog() {
  return useMutation<void, Error, { from?: string; to?: string }>({
    mutationFn: async (params) => {
      const res = await adminApi.exportAuditLog(params);
      const blob = await res.blob();
      const disposition = res.headers.get("content-disposition") ?? "";
      const match = /filename="?([^"]+)"?/.exec(disposition);
      const filename = match?.[1] ?? `khojo-audit-${Date.now()}.csv`;
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    },
  });
}
