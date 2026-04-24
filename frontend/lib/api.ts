/**
 * Typed HTTP client for the KHOJO backend.
 *
 * * Base URL from `NEXT_PUBLIC_API_URL` (falls back to legacy
 *   `NEXT_PUBLIC_API_BASE_URL` then `http://localhost:8000`).
 * * JWT attached automatically from the Zustand auth store.
 * * Throws `ApiError` with `{status, message, requestId}` for non-2xx.
 * * `FormData` helper for multipart uploads.
 *
 * Every exported call is typed against `lib/types.ts` which mirrors the
 * FastAPI Pydantic schemas.
 */
import { getAccessToken, useAuthStore } from "./authStore";
import type {
  AdminCasesPage,
  AdminDashboard,
  AuditLogPage,
  CaseCreate,
  CaseCreateResponse,
  CaseDetail,
  CaseResult,
  ConfirmMatchResponse,
  FieldWorkerAssign,
  FieldWorkerRow,
  FieldWorkerUpdate,
  HealthResponse,
  NotMatchResponse,
  PendingMatch,
  PhotoUploadResponse,
  ProcessResponse,
  RegisterRequest,
  RegisterResponse,
  SendOtpRequest,
  SendOtpResponse,
  Settings,
  SettingsUpdate,
  VerifyOtpRequest,
  VerifyOtpResponse,
} from "./types";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ??
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "http://localhost:8000";

export class ApiError extends Error {
  readonly status: number;
  readonly requestId: string | null;
  readonly details?: unknown;

  constructor(status: number, message: string, requestId: string | null, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.requestId = requestId;
    this.details = details;
  }
}

type ErrorBody = {
  error?: string;
  detail?: string | unknown;
  details?: unknown;
  request_id?: string;
};

async function parseError(res: Response): Promise<ApiError> {
  let body: ErrorBody | null = null;
  try {
    body = (await res.json()) as ErrorBody;
  } catch {
    body = null;
  }
  const requestId = res.headers.get("x-request-id") ?? body?.request_id ?? null;
  const message =
    (typeof body?.error === "string" && body.error) ||
    (typeof body?.detail === "string" && body.detail) ||
    `Request failed with status ${res.status}`;
  return new ApiError(res.status, message, requestId, body?.details ?? body?.detail);
}

function authHeader(): HeadersInit {
  const token = getAccessToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(
  path: string,
  init: RequestInit = {},
  opts: { isFormData?: boolean; expectJson?: boolean } = {}
): Promise<T> {
  const headers: HeadersInit = {
    ...(opts.isFormData ? {} : { "Content-Type": "application/json" }),
    Accept: "application/json",
    ...authHeader(),
    ...(init.headers ?? {}),
  };

  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
    cache: "no-store",
  });

  if (res.status === 401) {
    // Expire the session so the UI can redirect to sign-in.
    useAuthStore.getState().clearSession();
  }

  if (!res.ok) {
    throw await parseError(res);
  }
  if (res.status === 204 || opts.expectJson === false) {
    return undefined as T;
  }
  return (await res.json()) as T;
}

function buildFormData(
  fields: Record<string, string | number | boolean>,
  files: Record<string, File | Blob>
): FormData {
  const body = new FormData();
  for (const [k, v] of Object.entries(fields)) {
    body.append(k, String(v));
  }
  for (const [k, v] of Object.entries(files)) {
    body.append(k, v);
  }
  return body;
}

// ─── Auth ──────────────────────────────────────────────────────────────
export const authApi = {
  register: (body: RegisterRequest) =>
    request<RegisterResponse>("/api/auth/register", { method: "POST", body: JSON.stringify(body) }),

  sendOtp: (body: SendOtpRequest) =>
    request<SendOtpResponse>("/api/auth/send-otp", { method: "POST", body: JSON.stringify(body) }),

  verifyOtp: (body: VerifyOtpRequest) =>
    request<VerifyOtpResponse>("/api/auth/verify-otp", { method: "POST", body: JSON.stringify(body) }),
};

// ─── Cases ─────────────────────────────────────────────────────────────
export const casesApi = {
  create: (body: CaseCreate) =>
    request<CaseCreateResponse>("/api/cases", { method: "POST", body: JSON.stringify(body) }),

  get: (caseId: string) => request<CaseDetail>(`/api/cases/${encodeURIComponent(caseId)}`),

  uploadPhoto: (caseId: string, file: File, ageAtPhoto: number) =>
    request<PhotoUploadResponse>(
      `/api/cases/${encodeURIComponent(caseId)}/photos`,
      {
        method: "POST",
        body: buildFormData({ age_at_photo: ageAtPhoto }, { file }),
      },
      { isFormData: true }
    ),

  process: (caseId: string) =>
    request<ProcessResponse>(`/api/cases/${encodeURIComponent(caseId)}/process`, {
      method: "POST",
    }),

  result: (caseId: string) =>
    request<CaseResult>(`/api/cases/${encodeURIComponent(caseId)}/result`),
};

// ─── Matches ───────────────────────────────────────────────────────────
export const matchesApi = {
  pending: () => request<PendingMatch[]>("/api/matches/pending"),

  confirm: (matchId: string) =>
    request<ConfirmMatchResponse>(`/api/matches/${encodeURIComponent(matchId)}/confirm`, {
      method: "POST",
    }),

  notMatch: (matchId: string, realPhoto: File) =>
    request<NotMatchResponse>(
      `/api/matches/${encodeURIComponent(matchId)}/not-match`,
      {
        method: "POST",
        body: buildFormData({}, { real_photo: realPhoto }),
      },
      { isFormData: true }
    ),
};

// ─── Admin ─────────────────────────────────────────────────────────────
export const adminApi = {
  dashboard: () => request<AdminDashboard>("/api/admin/dashboard"),

  cases: (params: { status?: string; page?: number; page_size?: number } = {}) => {
    const qs = new URLSearchParams();
    if (params.status) qs.set("status", params.status);
    if (params.page) qs.set("page", String(params.page));
    if (params.page_size) qs.set("page_size", String(params.page_size));
    const suffix = qs.toString() ? `?${qs}` : "";
    return request<AdminCasesPage>(`/api/admin/cases${suffix}`);
  },

  approveCase: (caseId: string) =>
    request<{ case_id: string; action: string; status: string }>(
      `/api/admin/cases/${encodeURIComponent(caseId)}/approve`,
      { method: "POST" }
    ),

  rejectCase: (caseId: string, reason: string) =>
    request<{ case_id: string; action: string; status: string }>(
      `/api/admin/cases/${encodeURIComponent(caseId)}/reject`,
      { method: "POST", body: JSON.stringify({ reason }) }
    ),

  fieldWorkers: () => request<FieldWorkerRow[]>("/api/admin/field-workers"),

  assignFieldWorker: (body: FieldWorkerAssign) =>
    request<FieldWorkerRow>("/api/admin/field-workers", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  updateFieldWorker: (id: string, body: FieldWorkerUpdate) =>
    request<FieldWorkerRow>(`/api/admin/field-workers/${encodeURIComponent(id)}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  settings: () => request<Settings>("/api/admin/settings"),

  updateSettings: (body: SettingsUpdate) =>
    request<Settings>("/api/admin/settings", { method: "PATCH", body: JSON.stringify(body) }),

  auditLog: (params: { from?: string; to?: string; page?: number; page_size?: number } = {}) => {
    const qs = new URLSearchParams();
    if (params.from) qs.set("from", params.from);
    if (params.to) qs.set("to", params.to);
    if (params.page) qs.set("page", String(params.page));
    if (params.page_size) qs.set("page_size", String(params.page_size));
    const suffix = qs.toString() ? `?${qs}` : "";
    return request<AuditLogPage>(`/api/admin/audit-log${suffix}`);
  },

  /**
   * Audit-log export streams a CSV file. We return the raw Response so the
   * caller can stream it to a download without buffering in memory.
   */
  exportAuditLog: async (params: { from?: string; to?: string } = {}): Promise<Response> => {
    const qs = new URLSearchParams({ format: "csv" });
    if (params.from) qs.set("from", params.from);
    if (params.to) qs.set("to", params.to);
    const res = await fetch(`${API_BASE_URL}/api/admin/audit-log/export?${qs}`, {
      headers: { ...authHeader() },
      cache: "no-store",
    });
    if (!res.ok) throw await parseError(res);
    return res;
  },
};

// ─── Health ────────────────────────────────────────────────────────────
export const healthApi = {
  get: () => request<HealthResponse>("/health"),
};

// Legacy export kept for components imported before Phase 4.
export function getHealth(): Promise<HealthResponse> {
  return healthApi.get();
}
