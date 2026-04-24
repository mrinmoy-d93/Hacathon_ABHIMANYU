# KHOJO API — Endpoint Catalogue

> Phase 4 of the KHOJO backend. All routes are thin HTTP wrappers over the
> services introduced in Phase 3. Every state-changing endpoint writes an
> audit entry via `app.services.audit_service.write_audit`.

All `/api/*` endpoints return JSON. Non-2xx responses have the shape
`{"error": "...", "request_id": "..."}`. Validation failures additionally
carry `details` listing the offending fields.

| Request header | Behaviour |
|---|---|
| `Authorization: Bearer <jwt>` | Required for every `/api/*` route except `/api/auth/*`. 401 if missing or invalid. |
| `x-request-id` | Optional. Echoed back on the response; auto-generated (UUID) if not supplied. |

Rate limits (slowapi, per IP for anonymous, per token for authenticated):
`RATE_LIMIT_ANON` (default 60/min), `RATE_LIMIT_AUTH` (default 300/min).

---

## `/health` — liveness

| Method | Path | Description | FRS |
|---|---|---|---|
| GET | `/health` | DB + provider signals. Returns `status: ok \| degraded`, `providers: {openai, groq, hf, replicate}`, `version`, `uptime_seconds`. Target <200 ms. | NFR-2, NFR-8 |

## `/api/auth` — registration + OTP sign-in

| Method | Path | Auth | Description | FRS |
|---|---|---|---|---|
| POST | `/api/auth/register` | none | Body `{name, phone, location, role}` → `{user_id}`. `role ∈ {family, field_worker, admin}`. | FR-1.1 |
| POST | `/api/auth/send-otp` | none | Body `{phone}` → `{otp_sent, demo_mode}`. When `DEMO_MODE=true` the OTP is always `123456` and SMS is skipped (see `docs/DEMO_MODE.md`). | FR-1.2, FR-1.5 |
| POST | `/api/auth/verify-otp` | none | Body `{phone, otp, police_id?}` → `{access_token, expires_in, user}`. Admin users MUST supply `police_id` (demo value `KHOJO-ADMIN-2026`). | FR-1.2, AC-11 |

JWT shape: `{sub: user_id, role, iat, exp}`. Signed with `JWT_SECRET`, algorithm `HS256`, 24-hour expiry by default.

## `/api/cases` — case lifecycle

| Method | Path | Auth | Description | FRS |
|---|---|---|---|---|
| POST | `/api/cases` | family / admin | Body `{person_name, year_missing, age_at_disappearance, last_seen_location, identifying_marks?}` → `{case_id, predicted_current_age}`. Computes the FR-2.2 age formula. | FR-2.1, FR-2.2 |
| GET | `/api/cases/{case_id}` | creator / assigned field worker / admin | Full case detail including photos and match summaries. | §6.2 |
| POST | `/api/cases/{case_id}/photos` | case creator / admin | Multipart `file` + `age_at_photo`. Validates 10 MB upload cap, delegates storage to `supabase_service.upload_photo`. | FR-2.3, FR-2.4 |
| POST | `/api/cases/{case_id}/process` | case creator / admin | Triggers `pipeline_service.process_case` as a FastAPI `BackgroundTask`. Returns `202 {status: "processing", job_id}`. 400 if the case has <2 source photos (FR-2.3). | FR-3.1 – FR-3.8 |
| GET | `/api/cases/{case_id}/result` | viewer | `{status, aged_photo_url, matches, summary, confidence_distribution, providers_used, processing_time_seconds, explanation, confidence_score}`. Every match carries a plain-language `explanation` per FR-4.2 / FR-4.4. | §6.4 |

## `/api/matches` — field-worker verification

| Method | Path | Auth | Description | FRS |
|---|---|---|---|---|
| GET | `/api/matches/pending` | field_worker | Matches assigned to the caller, sorted by `confidence_score` desc. | FR-5.1 |
| POST | `/api/matches/{match_id}/confirm` | field_worker / admin | Marks confirmed, sets case status to `found`, calls `llm_service.generate_family_alert`. Returns `{confirmed, family_notified, provider_used, …}`. | FR-5.2, FR-5.3 |
| POST | `/api/matches/{match_id}/not-match` | field_worker / admin | Multipart **mandatory** `real_photo` (400 if empty). Uploads to `not-match-photos` bucket, computes a 5-group error vector, appends to `training_pool`, reopens the case. Fine-tune triggered at pool size = 50. | FR-5.4, FR-5.5 |

## `/api/admin` — administrator console (all require admin JWT)

| Method | Path | Description | FRS |
|---|---|---|---|
| GET | `/api/admin/dashboard` | Total / active / matched / review-pending counts, confidence distribution, last 10 audit entries. | §6.6 Tab 1 |
| GET | `/api/admin/cases?status=&page=&page_size=` | Paginated case list with optional status filter. | §6.6 Tab 2 |
| POST | `/api/admin/cases/{case_id}/approve` | Dispatches field-worker alert; writes audit. | §6.6 Tab 2 |
| POST | `/api/admin/cases/{case_id}/reject` | Body `{reason}` — closes case; writes audit. | §6.6 Tab 2 |
| GET | `/api/admin/field-workers` | Listing with zone + verification_count + accuracy_score. | §6.6 Tab 3 |
| POST | `/api/admin/field-workers` | Body `{user_id, zone}` — promotes to field worker. | §6.6 Tab 3 |
| PATCH | `/api/admin/field-workers/{worker_id}` | Body `{zone?, leave_status?}` — leave reassigns open matches. | §6.6 Tab 3 |
| GET | `/api/admin/settings` | Thresholds + toggles + current model version. | §6.6 Tab 4 |
| PATCH | `/api/admin/settings` | Body subset of `{confidence_threshold (0.40–0.90), auto_alert_threshold (0.60–0.99), gpt4o_enabled, geo_clustering_enabled}`. Takes effect on the next request (60 s `cachetools.TTLCache`); no redeploy. | §6.6 Tab 4 |
| GET | `/api/admin/audit-log?from=&to=&page=&page_size=` | Paginated, PII-redacted audit listing. | §6.6 Tab 5, §10.3 |
| GET | `/api/admin/audit-log/export?from=&to=&format=csv` | Streams `text/csv` with `Content-Disposition: attachment; filename=…`. PII redacted per §10.2. | §6.6 Tab 5, AL-3 |

---

## Error codes

| Code | Meaning | Typical payload |
|---|---|---|
| 400 | Client-visible input problem (future year, missing mandatory field, conflicting settings). | `{error, request_id}` |
| 401 | Missing / invalid / expired JWT, or OTP mismatch. | `{error, request_id}` |
| 403 | Role / ownership check failed. | `{error, request_id}` |
| 404 | Case / match / worker does not exist. | `{error, request_id}` |
| 409 | Conflict — duplicate phone, already-verified match, etc. | `{error, request_id}` |
| 413 | Photo exceeded 10 MB. | `{error, request_id}` |
| 422 | Pydantic schema validation. | `{error, details, request_id}` |
| 429 | Rate limit tripped. | `{error, request_id}` |
| 502 | Supabase (or another external upload) unavailable. | `{error, request_id}` |
| 500 | Unhandled. Never leaks a stack trace (FRS NFR-3). | `{error, request_id}` |

---

## Audit-log invariants (FRS §10.3)

Every state-changing endpoint above writes an `AuditLog` row with:

* `action` — e.g. `case.create`, `match.confirm`, `admin.settings.update`.
* `actor_id` — the authenticated user.
* `input_hash` / `output_hash` — SHA-256 over PII-redacted canonical JSON.
* `hmac_signature` — HMAC-SHA-256 using `AUDIT_SIGNING_SECRET`.

`AuditLog` rows are append-only — `UPDATE` and `DELETE` raise
`AuditLogImmutableError` at the SQLAlchemy `before_flush` hook. The admin
console verifies the chain on every CSV export.
