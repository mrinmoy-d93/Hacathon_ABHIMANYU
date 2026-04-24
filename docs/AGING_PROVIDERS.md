# Aging providers — setup and fallback behaviour

KHOJO's face-aging step runs through three providers in order. The first one
that returns a valid image is used; later providers are only invoked if every
preceding one has failed. A per-provider circuit breaker (5 consecutive
failures → 60-second cooldown, FRS NFR-5) short-circuits a flapping provider
so the system stays responsive.

| Order | Provider              | Env var(s)              | Free? | Typical latency |
|-------|-----------------------|-------------------------|-------|-----------------|
| 1     | Hugging Face Inference| `HF_TOKEN`, `HF_AGING_MODEL` | Yes | 3–8 s |
| 2     | Colab + ngrok         | `COLAB_AGING_URL`       | Yes   | 5–15 s |
| 3     | Deterministic mock    | —                       | Yes   | <10 ms |

---

## 1. Hugging Face Inference API (primary)

1. Create a free account at https://huggingface.co.
2. **Settings → Access Tokens → Create token** (read scope).
3. Set in your `.env` or Railway/HF Spaces environment:
   ```
   HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   HF_AGING_MODEL=nateraw/sam
   ```
4. The backend calls `InferenceClient(token=HF_TOKEN).post(model=HF_AGING_MODEL, data=image_bytes, json={"parameters": {"target_age": ...}})`.

**Notes**
- `nateraw/sam` is a placeholder. The hackathon team should validate their
  preferred public face-aging model and pin its ID here. Any model that
  accepts image bytes + a `target_age` integer parameter will work.
- The free Hugging Face Inference API has a cold-start delay and rate limit.
  Retries with exponential backoff absorb transient 503s; the circuit breaker
  prevents thundering-herd when the endpoint is actually down.

**Recovery** If HF is down (503/504/429, or network error), the service logs
`aging.huggingface unavailable: …`, records a failure in the breaker, and
falls through to provider 2.

---

## 2. Self-hosted Colab endpoint (secondary)

Useful for demo day when HF is cold or rate-limited.

1. Open a free Google Colab notebook and install InsightFace + SAM or HRFAE.
2. Start a Flask/FastAPI endpoint accepting
   `POST /age` with multipart form fields `image` (file) and `target_age` (int),
   returning the aged PNG bytes.
3. Expose it with `ngrok http 8000` (or Cloudflare Tunnel) and set:
   ```
   COLAB_AGING_URL=https://<your-ngrok>.ngrok-free.app/age
   ```
4. Leave the var blank to skip this provider entirely — skipping is free and
   the fallback chain simply advances to the mock.

**Recovery** Network error or non-2xx response logs `aging.colab unavailable`
and falls through to the mock provider.

---

## 3. Deterministic mock (tertiary)

Always returns
`https://placehold.co/512x512?text=Aged+to+{target_age}` and sets
`aging_unavailable: true` in the response so the UI can show a clear banner
explaining why no aged image is available.

The mock is the same code path as `USE_MOCK_AI=true` — enabling that env var
globally routes every sub-step (detection, embedding, aging, LLM) to its
deterministic mock. Useful for:

- Local dev on laptops without InsightFace installed.
- CI / pytest (the sandbox runs every test in `USE_MOCK_AI=true`).
- Judge demos when API keys are not available.

---

## Implementation notes

- Retries: 3 attempts per provider with `tenacity`, exponential waits (0.5 →
  4.0 s). Only `ProviderUnavailableError` and `httpx.TransportError` trigger a
  retry; a `200 OK` with unexpected body does **not**.
- Circuit breaker state is per-process (see
  `app.services.ai_common.CircuitBreaker`). For multi-worker deployments the
  failures reset when Uvicorn restarts.
- On success the aged image is re-uploaded to the Supabase
  `case-photos` bucket via `supabase_service.upload_photo` so downstream code
  always sees a canonical public URL regardless of the upstream provider.
