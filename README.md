# KHOJO — AI Missing Person Finder

**Amnex Hackathon 2026 · UC34 · Social Impact · FRS v1.1**

> *"AI suggests, the human decides."*

An Artificial Intelligence (AI) powered web solution that predicts how a missing
person appears today (via facial aging) and matches that prediction against a
growing database of sighted individuals.

This repository contains the **cloud-native, zero-install web edition** —
frontend on Vercel, backend on Railway, data on Supabase.

---

## Repository layout

```
/
├── frontend/          Next.js 14 web app (Vercel)
│   ├── app/           App Router pages: landing, register, cases, field-worker, admin
│   ├── components/
│   └── lib/           API client, auth helpers
├── backend/           FastAPI (Railway via Docker)
│   ├── app/
│   │   ├── routers/   health, auth, cases (stubs)
│   │   ├── services/  face, llm, aging, audit, supabase wrappers
│   │   ├── models/    SQLAlchemy
│   │   └── schemas/   Pydantic
│   └── Dockerfile     Python 3.11-slim, CPU-only
├── docs/
│   ├── KHOJO_FRS.md
│   ├── KHOJO_FRS.pdf
│   ├── ARCHITECTURE.md
│   └── DEPLOYMENT.md  step-by-step Vercel + Railway + Supabase
├── docker-compose.yml Local-equivalent stack
├── railway.json       Railway build + healthcheck config
├── vercel.json        Vercel build config
└── .env.example       All required environment variables
```

---

## Quick start (local)

```bash
cp .env.example .env
cp frontend/.env.example frontend/.env.local
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend health: http://localhost:8000/health

## Deploy

See [`docs/DEPLOYMENT.md`](./docs/DEPLOYMENT.md) for end-to-end Vercel + Railway + Supabase setup.

## Architecture

See [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) for how the FRS v1.1 local
pipeline maps onto managed cloud services.

## Functional spec

Full requirements: [`docs/KHOJO_FRS.md`](./docs/KHOJO_FRS.md) · [`docs/KHOJO_FRS.pdf`](./docs/KHOJO_FRS.pdf)

---

## Technology stack — cloud edition

| Layer               | Technology                                    |
|---------------------|-----------------------------------------------|
| Frontend            | Next.js 14 (App Router) + Tailwind CSS        |
| Backend             | FastAPI on Python 3.11                        |
| Database + Vectors  | Supabase Postgres + `pgvector`                |
| Auth                | Supabase Auth (phone OTP) + JWT               |
| Object storage      | Supabase Storage (S3-compatible)              |
| Face detection/embed| Replicate-hosted InsightFace + ArcFace        |
| Face aging GAN      | Replicate-hosted SAM / HRFAE                  |
| Summaries           | OpenAI GPT-4o (optional, FRS §6.3.9)          |
| Deploy              | Vercel (frontend) · Railway (backend)         |

## Project info

| Field        | Detail                           |
|--------------|----------------------------------|
| Hackathon    | Amnex Hackathon 2026             |
| Use Case     | UC34 — Missing Person Finder     |
| Domain       | Social Impact                    |
| FRS Version  | 1.1 (Detailed)                   |
| Date         | 24 April 2026                    |
| Team         | KHOJO                            |
