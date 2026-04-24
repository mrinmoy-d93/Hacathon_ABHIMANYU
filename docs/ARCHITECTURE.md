# KHOJO — Cloud-Native Architecture

> **Web-only, zero-install edition.** Derived from FRS v1.1 and adapted for a serverless/managed-service deployment across Vercel, Railway, and Supabase.

---

## 1. Topology

```
┌──────────────────────────┐         ┌──────────────────────────┐
│   Vercel (Frontend)      │  HTTPS  │   Railway (Backend)      │
│   Next.js 14 App Router  │────────▶│   FastAPI + Uvicorn      │
│   Tailwind CSS           │         │   Python 3.11-slim       │
└──────────────────────────┘         └──────────┬───────────────┘
                                                │
                ┌───────────────────────────────┼────────────────────────────┐
                │                               │                            │
                ▼                               ▼                            ▼
      ┌──────────────────┐         ┌────────────────────┐      ┌─────────────────────┐
      │   Supabase       │         │   Replicate        │      │   OpenAI GPT-4o     │
      │   Postgres +     │         │   InsightFace /    │      │   Summaries +       │
      │   pgvector +     │         │   ArcFace /        │      │   Community alerts  │
      │   Storage + Auth │         │   SAM / HRFAE GAN  │      │   (optional)        │
      └──────────────────┘         └────────────────────┘      └─────────────────────┘
```

## 2. Mapping FRS v1.1 to cloud services

| FRS layer              | Local-first v1.1        | Cloud-native edition              |
|------------------------|-------------------------|-----------------------------------|
| Presentation           | React Native + Web      | Next.js 14 web (Vercel)           |
| API                    | FastAPI on Nginx        | FastAPI on Railway                |
| Task queue             | Celery + Redis          | Replicate async predictions       |
| Face detection / embed | InsightFace / ArcFace   | Replicate-hosted model endpoints  |
| Face aging GAN         | SAM / HRFAE (GPU)       | Replicate SAM / HRFAE models      |
| Vector DB              | pgvector (self-hosted)  | Supabase Postgres + pgvector      |
| Object storage         | MinIO                   | Supabase Storage (S3-compatible)  |
| Auth                   | OTP + JWT               | Supabase Auth (phone OTP) + JWT   |
| Summaries              | OpenAI GPT-4o           | OpenAI GPT-4o (unchanged)         |
| Geocoding              | GeoPy + local Nominatim | GeoPy + public Nominatim (cached) |

## 3. Request lifecycle

1. User hits `khojo.vercel.app` — Next.js SSR page renders.
2. Client calls `NEXT_PUBLIC_API_BASE_URL` (Railway) — hits FastAPI.
3. FastAPI authenticates via Supabase JWT, then:
   - Writes case metadata to Supabase Postgres.
   - Uploads photos to Supabase Storage.
   - Dispatches InsightFace + SAM to Replicate.
   - Stores 512-d embeddings in the `photos.embedding` pgvector column.
4. Top-K cosine-similarity search runs inside Postgres via `vector_cosine_ops`.
5. Confidence tier + audit record written; field worker notified.

## 4. Privacy posture shift

The v1.1 "all CV is local" guarantee is softened in this edition: biometric
tensors transit to Replicate over TLS. Operators must:

- Use Replicate private models where available.
- Set short-lived signed URLs (≤ 1 hour) for any media shared with Replicate.
- Redact PII from Replicate webhook payloads before logging.

See `DEPLOYMENT.md` for step-by-step setup.
