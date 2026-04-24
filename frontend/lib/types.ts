/**
 * TypeScript mirrors of backend Pydantic schemas.
 * Each group is linked to its FRS section below.
 */

// ─── Auth ─── FRS §7.1, FR-1.1–FR-1.6 ─────────────────────────────────────
export type UserRole = "family" | "field_worker" | "admin";

/** @see FRS §5 Users and Roles */
export interface User {
  id: string;
  name: string;
  phone: string;
  location: string | null;
  role: UserRole;
}

/** @see FRS FR-1.1 */
export interface RegisterRequest {
  name: string;
  phone: string;
  location: string;
  role: UserRole;
}

export interface RegisterResponse {
  user_id: string;
}

/** @see FRS FR-1.2, FR-1.5 (5-minute OTP, rate limited) */
export interface SendOtpRequest {
  phone: string;
}

export interface SendOtpResponse {
  otp_sent: boolean;
  demo_mode: boolean;
}

/** @see FRS AC-11 (admins require police_id) */
export interface VerifyOtpRequest {
  phone: string;
  otp: string;
  police_id?: string;
}

export interface VerifyOtpResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

// ─── Cases ─── FRS §6.2, §6.3, §6.4 ───────────────────────────────────────
export type CaseStatus = "active" | "under_review" | "found" | "closed";

export interface Photo {
  id: string;
  supabase_url: string;
  age_at_photo: number;
  is_predicted_aged: boolean;
}

/** @see FRS FR-2.1 */
export interface CaseCreate {
  person_name: string;
  year_missing: number;
  age_at_disappearance: number;
  last_seen_location: string;
  identifying_marks?: string | null;
}

/** @see FRS FR-2.2 age formula */
export interface CaseCreateResponse {
  case_id: string;
  predicted_current_age: number;
}

export type MatchTier = "high" | "medium" | "low";
export type MatchStatus = "pending" | "confirmed" | "not_match";

export interface MatchSummary {
  id: string;
  candidate_photo_url: string;
  confidence_score: number;
  tier: MatchTier;
  status: MatchStatus;
}

export interface CaseDetail {
  case_id: string;
  person_name: string;
  year_missing: number;
  age_at_disappearance: number;
  predicted_current_age: number;
  last_seen_location: string;
  identifying_marks: string | null;
  status: CaseStatus;
  created_at: string;
  photos: Photo[];
  matches: MatchSummary[];
}

export interface PhotoUploadResponse {
  photo_id: string;
  supabase_url: string;
}

export interface ProcessResponse {
  status: "processing";
  job_id: string;
}

/** @see FRS FR-4.2 colour-coded confidence bar */
export interface ConfidenceDistribution {
  high: number;
  medium: number;
  low: number;
}

export interface CaseResultMatch {
  match_id: string | null;
  candidate_photo_url: string;
  confidence_score: number;
  tier: MatchTier;
  /** Plain-language explanation — FRS FR-4.2, FR-4.4. */
  explanation: string;
}

/** @see FRS §9 GET /cases/{id}/result */
export interface CaseResult {
  status: "processing" | "complete" | "error" | "unknown";
  aged_photo_url: string | null;
  matches: CaseResultMatch[];
  summary: string | null;
  confidence_distribution: ConfidenceDistribution;
  providers_used: Record<string, string>;
  processing_time_seconds: number | null;
  explanation: string;
  confidence_score: number | null;
}

// ─── Matches ─── FRS §6.5 field-worker workflow ───────────────────────────
/** @see FRS FR-5.1 */
export interface PendingMatch {
  id: string;
  case_id: string;
  person_name: string;
  candidate_photo_url: string;
  confidence_score: number;
  tier: MatchTier;
  created_at: string;
  explanation: string;
}

/** @see FRS FR-5.3 */
export interface ConfirmMatchResponse {
  confirmed: boolean;
  family_notified: boolean;
  provider_used: string;
  confidence_score: number;
  explanation: string;
}

/** @see FRS FR-5.4, FR-5.5 (pool reaches 50 → fine-tune) */
export interface NotMatchResponse {
  error_vector_captured: boolean;
  case_reopened: boolean;
  feedback_pool_size: number;
  training_cycle_triggered: boolean;
  confidence_score: number;
  explanation: string;
}

// ─── Admin console ─── FRS §6.6 five tabs ─────────────────────────────────
export interface RecentActivityItem {
  id: number;
  action: string;
  timestamp: string;
  confidence_score: number | null;
}

/** @see FRS §6.6 Tab 1 */
export interface AdminDashboard {
  total_cases: number;
  active_searches: number;
  matches_found: number;
  review_pending: number;
  confidence_distribution: ConfidenceDistribution;
  recent_activity: RecentActivityItem[];
}

/** @see FRS §6.6 Tab 2 */
export interface AdminCaseRow {
  case_id: string;
  person_name: string;
  status: CaseStatus;
  predicted_current_age: number;
  last_seen_location: string;
  confidence_score: number | null;
  assigned_field_worker_id: string | null;
}

export interface AdminCasesPage {
  items: AdminCaseRow[];
  page: number;
  page_size: number;
  total: number;
}

/** @see FRS §6.6 Tab 3 */
export interface FieldWorkerRow {
  id: string;
  name: string;
  zone: string | null;
  verification_count: number;
  accuracy_score: number;
}

export interface FieldWorkerAssign {
  user_id: string;
  zone: string;
}

export interface FieldWorkerUpdate {
  zone?: string;
  leave_status?: "active" | "on_leave";
}

/** @see FRS §6.6 Tab 4 — ranges: confidence 0.40–0.90, auto-alert 0.60–0.99 */
export interface Settings {
  confidence_threshold: number;
  auto_alert_threshold: number;
  gpt4o_enabled: boolean;
  geo_clustering_enabled: boolean;
  current_model_version: string;
}

export type SettingsUpdate = Partial<
  Pick<
    Settings,
    | "confidence_threshold"
    | "auto_alert_threshold"
    | "gpt4o_enabled"
    | "geo_clustering_enabled"
  >
>;

/** @see FRS §6.6 Tab 5 + §10.3 tamper-evident chain */
export interface AuditEntry {
  id: number;
  timestamp: string;
  actor_id: string | null;
  action: string;
  model_version: string | null;
  confidence_score: number | null;
  input_hash: string;
  output_hash: string;
}

export interface AuditLogPage {
  items: AuditEntry[];
  page: number;
  page_size: number;
  total: number;
}

// ─── Health ─── FRS NFR-2, NFR-8 ──────────────────────────────────────────
export interface ProviderHealth {
  openai: boolean;
  groq: boolean;
  hf: boolean;
  replicate: boolean;
}

export interface HealthResponse {
  status: "ok" | "degraded";
  db: boolean;
  providers: ProviderHealth;
  version: string;
  uptime_seconds: number;
}
