# KHOJO — Demo Mode

Demo mode lets judges and reviewers exercise the full KHOJO flow without an SMS
provider account or live GPU. It is controlled by two environment variables:

```
DEMO_MODE=true   # enables the bypass paths below
DEMO_OTP=123456  # the fixed six-digit code accepted for every phone number
```

> **Never enable `DEMO_MODE` in production.** It short-circuits OTP delivery
> and is not rate-limited at the SMS layer.

## What changes when `DEMO_MODE=true`

| Subsystem | Production behaviour | Demo-mode behaviour |
|---|---|---|
| `POST /api/auth/send-otp` | Generates a six-digit OTP, stores it in the per-process dict with a 5-minute TTL, and (when a provider is wired) dispatches an SMS. | SMS dispatch is skipped entirely. A log line confirms the fixed OTP `123456` is active for that phone. |
| `POST /api/auth/verify-otp` | Accepts only OTPs issued by `send-otp`. | Additionally accepts the fixed `DEMO_OTP` (default `123456`) for any phone number. Admin 2FA still requires the correct `police_id` (`KHOJO-ADMIN-2026` in the demo). |
| AI pipeline | Real providers (Hugging Face aging, OpenAI LLM, etc.). | Set `USE_MOCK_AI=true` alongside `DEMO_MODE` to force every AI service to its deterministic stub (see `app/services/_mock_ai.py`). |
| Rate limiting | Per-IP `RATE_LIMIT_ANON` and per-token `RATE_LIMIT_AUTH`. | Unchanged — demo mode does **not** loosen rate limiting. |

## Recommended local setup

```bash
# backend/.env
DEMO_MODE=true
DEMO_OTP=123456
USE_MOCK_AI=true
JWT_SECRET=$(openssl rand -hex 32)
AUDIT_SIGNING_SECRET=$(openssl rand -hex 32)
DATABASE_URL=sqlite:///./khojo.db
```

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

In another terminal:

```bash
cd frontend
cp .env.example .env.local         # edits NEXT_PUBLIC_API_URL if needed
npm install
npm run dev
```

Open <http://localhost:3000>, register with any phone, and sign in with OTP
`123456`. The typed API client (see `frontend/lib/api.ts`) will attach the JWT
automatically on subsequent calls.

## Admin sign-in

1. `POST /api/auth/register` with `role=admin`.
2. `POST /api/auth/send-otp` — receives `{demo_mode: true}`.
3. `POST /api/auth/verify-otp` with `{phone, otp: "123456", police_id: "KHOJO-ADMIN-2026"}`.
4. Use the returned access token against the `/api/admin/*` routes.

## Turning demo mode off

Unset `DEMO_MODE` (or set it to `false`) and restart the backend. `send-otp`
will now require a configured SMS provider; `verify-otp` will only accept
codes that were actually issued.
