# KHOJO — Deployment Guide (Vercel + Railway + Supabase)

End-to-end deploy of the cloud-native web-only edition. Estimated time: ~30 minutes.

---

## Prerequisites

- GitHub account with this repository pushed.
- Accounts (free tier works for demo): [Vercel](https://vercel.com), [Railway](https://railway.app), [Supabase](https://supabase.com), [OpenAI](https://platform.openai.com), [Replicate](https://replicate.com).
- Node.js 20+ and Python 3.11+ locally (optional, for smoke testing).

---

## Step 1 — Provision Supabase (Postgres + pgvector + Storage + Auth)

1. Go to https://supabase.com/dashboard and click **New project**.
2. Pick a region close to your users (e.g. `ap-south-1` for India). Set a strong DB password.
3. When provisioned, open **SQL Editor → New query** and run:
   ```sql
   create extension if not exists vector;
   ```
4. Open **Project Settings → API** and copy:
   - `Project URL` → becomes `SUPABASE_URL`
   - `service_role` key → becomes `SUPABASE_KEY`
5. Open **Project Settings → Database → Connection string → URI** and copy it as `DATABASE_URL` (prefer the `pgbouncer` pooler URL on port 6543 for serverless).
6. Open **Storage → New bucket** and create a private bucket named `khojo-media`.
7. Open **Authentication → Providers** and enable **Phone** (OTP via your chosen SMS provider).

---

## Step 2 — Create API keys for Replicate and OpenAI

1. Replicate → **Account → API tokens → Create token** → copy as `REPLICATE_API_TOKEN`.
2. OpenAI → **API keys → Create new secret key** → copy as `OPENAI_API_KEY`.

---

## Step 3 — Deploy backend to Railway

1. Go to https://railway.app/new and choose **Deploy from GitHub repo**; select this repository.
2. Railway auto-detects `railway.json` and builds `backend/Dockerfile`.
3. Open the new service → **Variables** tab → add:
   ```
   DATABASE_URL        = <from Supabase step 1.5>
   SUPABASE_URL        = <from Supabase step 1.4>
   SUPABASE_KEY        = <from Supabase step 1.4>
   OPENAI_API_KEY      = <from step 2.2>
   REPLICATE_API_TOKEN = <from step 2.1>
   JWT_SECRET          = <openssl rand -hex 32>
   CORS_ORIGINS        = https://<your-vercel-domain>.vercel.app
   ENVIRONMENT         = production
   ```
4. Open **Settings → Networking → Generate Domain**. Copy the public URL (e.g. `https://khojo-backend.up.railway.app`).
5. Hit `https://<your-railway-url>/health` — you should get `{"status":"ok", …}`.

---

## Step 4 — Deploy frontend to Vercel

1. Go to https://vercel.com/new and import this repository.
2. Under **Root Directory**, leave as the repo root (the included `vercel.json` points the build at `frontend/`).
3. Under **Environment Variables**, add:
   ```
   NEXT_PUBLIC_API_BASE_URL = https://<your-railway-url>
   ```
4. Click **Deploy**. Vercel builds `frontend/` and serves the site at `https://<project>.vercel.app`.
5. Back on Railway, update `CORS_ORIGINS` to include the new Vercel URL; redeploy.

---

## Step 5 — Apply database schema

From the Supabase **SQL Editor**, run the minimal schema (adjust column types as the implementation grows):

```sql
create table if not exists cases (
  id bigserial primary key,
  khj_id text unique not null,
  name text not null,
  age_at_disappearance int not null,
  missing_year int not null,
  last_location text not null,
  status text not null default 'active',
  created_at timestamptz default now()
);

create table if not exists photos (
  id bigserial primary key,
  case_id bigint references cases(id) on delete cascade,
  storage_key text not null,
  age_at_capture int not null,
  embedding vector(512),
  created_at timestamptz default now()
);

create index if not exists photos_embedding_ivfflat
  on photos using ivfflat (embedding vector_cosine_ops) with (lists = 100);

create table if not exists audit_log (
  id bigserial primary key,
  ts timestamptz default now(),
  action text not null,
  case_id bigint,
  model_version text,
  input_hash text,
  output_hash text,
  confidence double precision,
  prev_checksum text,
  checksum text not null
);
```

---

## Step 6 — Smoke test

1. Visit `https://<your-vercel-url>/` — you should see **KHOJO — AI Missing Person Finder** with a green **Online** badge next to the backend health check.
2. `curl https://<your-railway-url>/health` → `200 OK`.
3. Open `/cases`, `/field-worker`, `/admin` — all four scaffolded pages render.

---

## Step 7 — Continuous deployment

- Vercel auto-deploys every push to `main` and opens a preview URL per pull request.
- Railway auto-deploys pushes to `main` by default; toggle **Settings → Automatic Deploys** if you prefer manual.

---

## Troubleshooting

| Symptom                          | Fix                                                                            |
|----------------------------------|--------------------------------------------------------------------------------|
| Frontend shows "Offline" badge   | Check `NEXT_PUBLIC_API_BASE_URL` is set on Vercel and `CORS_ORIGINS` on Railway contains your Vercel URL. |
| Railway build fails on Dockerfile| Confirm `railway.json`'s `buildContext` is `backend` and `dockerfilePath` is `backend/Dockerfile`. |
| 500 from `/cases`                | Not implemented in scaffold — routes return `501`. Fill in per FRS §6.2.       |
| `extension "vector" does not exist` | Run `create extension vector;` in Supabase SQL editor (Step 1.3).           |

---

## Local smoke test (optional)

```bash
cp .env.example .env
cp frontend/.env.example frontend/.env.local
docker compose up --build
# frontend: http://localhost:3000
# backend:  http://localhost:8000/health
```
