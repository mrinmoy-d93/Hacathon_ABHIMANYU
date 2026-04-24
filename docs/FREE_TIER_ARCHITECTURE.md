# KHOJO on $0 — free-tier architecture

One page for a judge: what every service is, what it costs, what happens if
it goes down, and how to recover. Target deployment is Hugging Face Spaces
(backend) + Vercel (frontend), no credit card required.

## Cost per case processed

| Line item                  | Provider              | Cost per case | Notes |
|----------------------------|-----------------------|---------------|-------|
| Frontend hosting            | Vercel Hobby          | **$0.00**     | 100 GB-hrs bandwidth/mo free |
| Backend hosting             | Hugging Face Spaces   | **$0.00**     | CPU Basic tier, 16 GB RAM |
| Postgres + Storage + Auth   | Supabase Free         | **$0.00**     | 500 MB DB, 1 GB storage |
| Face detect + embed         | InsightFace on CPU    | **$0.00**     | runs inside the Space |
| Face aging (primary)        | HF Inference API      | **$0.00**     | free rate limit, cold-start delay OK |
| Face aging (secondary)      | Colab + ngrok         | **$0.00**     | started at demo time |
| LLM summaries (primary)     | OpenAI GPT-4o         | **$0.00**     | hackathon credits |
| LLM summaries (secondary)   | Groq Llama 3.3 70B    | **$0.00**     | OpenAI-compatible, free tier |
| LLM summaries (tertiary)    | Deterministic template| **$0.00**     | no network call |
| Geocoding                   | Nominatim (free)      | **$0.00**     | 1 req/sec, cached |
| **Total per case**          |                       | **$0.00**     |       |

## Pipeline at a glance

```
Vercel → HF Spaces (FastAPI)
            │
            ├─ face_detector  ────── InsightFace CPU
            ├─ embedding_service ─── InsightFace (same instance)
            ├─ trajectory_service ── NumPy polyfit
            ├─ aging_service  ───── ① HF Inference API
            │                       ② Colab + ngrok (if set)
            │                       ③ Mock placeholder
            ├─ recognition_service ─ Postgres full scan (→ pgvector at scale)
            ├─ scoring_service  ─── app_settings thresholds
            ├─ alert_router ─────── Nominatim geocoding, Match row
            └─ llm_service ──────── ① OpenAI GPT-4o
                                    ② Groq Llama 3.3 70B
                                    ③ Deterministic template
```

Every sub-step writes an `audit_log` entry via `audit_service.write_audit`,
including `model_version=<provider>/<model>`, SHA-256 hashes of
PII-redacted input/output, and an HMAC-SHA256 signature chained per FRS
§10.3. The pipeline's final return value includes a `providers_used` field
so judges can see exactly which free-tier provider served each sub-step on
that request.

## What happens if each service fails

| Failure                                | Effect                                             | Recovery                                    |
|----------------------------------------|----------------------------------------------------|---------------------------------------------|
| Vercel outage                          | Frontend unreachable                               | Rare; no action needed, users retry          |
| HF Spaces container OOM                | 502 from backend                                   | Space auto-restarts; health check notices   |
| Supabase DB down                       | API returns 503 with clear message                 | Supabase SLA; no code change needed         |
| HF Inference API 5xx or slow           | Retry ×3, then circuit opens for 60 s              | Fall through to Colab, then mock             |
| Colab endpoint asleep / ngrok URL stale| Retry ×3, circuit opens                            | Mock takes over with `aging_unavailable=true` banner |
| OpenAI quota exhausted / 429           | Retry ×3, circuit opens                            | Groq takes over transparently                |
| Groq rate-limited                      | Retry ×3, circuit opens                            | Template takes over — no text loss          |
| Nominatim rate-limited                 | `_geocode` returns `None`                          | Field worker auto-assignment falls back to round-robin by pending-match count |

## Toggles a judge can flip

- `USE_MOCK_AI=true` — every AI sub-step uses deterministic mocks. Free, fast, offline, reproducible.
- `GPT4O_ENABLED=false` — skip OpenAI entirely; pipeline goes OpenAI → Groq → template → starts at Groq.
- `HF_AGING_MODEL=<any public HF model>` — swap the aging model without a redeploy.
- Admin console → AI Settings tab — confidence thresholds, auto-alert threshold, geo-clustering params (FRS §6.6 Tab 4, §7.6.4).

## Proof it stays free

Run `pytest backend/tests/ -v` with `USE_MOCK_AI=true` — all 50 tests pass
without network access. The mock is not just a test shim: it is the tertiary
fallback in production, so the free-tier guarantee holds end-to-end.
