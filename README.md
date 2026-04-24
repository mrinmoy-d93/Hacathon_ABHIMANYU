# KHOJO — AI-Powered Missing Person Finder

> *Finding the lost, even after the years have changed their face.*

**Team ABHIMANYU · Amnex Hackathon 2026 · Use Case UC34 (Social Impact)**

---

## The Problem

India records more than **100,000 missing person cases every year**. Many are children who go missing young and, when eventually sighted or found years later, are no longer visually recognisable — their faces have aged, softened, sharpened, and changed in ways no family photograph anticipated.

Families hold on to photographs from a decade ago. Shelter homes and police stations see hundreds of unidentified children. The two rarely meet, because no one knows what the missing child looks like **today**.

## Our Solution — KHOJO

**KHOJO** (खोजो — "Search" in Hindi) uses Artificial Intelligence (AI) to close this gap.

Given one or more old photographs of a missing person, KHOJO:

1. **Predicts** how the person most likely looks today, using a face-aging Generative Adversarial Network (GAN).
2. **Searches** a growing database of sighted and registered individuals using age-invariant face recognition.
3. **Alerts** the nearest field worker for physical verification when a high-confidence match is found.
4. **Learns** from every wrong match through a "Not a Match" feedback loop — getting smarter the more it is used.

Every result carries a confidence score. Every match is verified by a human on the ground before a family is informed.

> **"AI suggests, the human decides."** — the foundational principle of the entire system.

---

## Key Features

| Feature | What it does |
|---|---|
| **Multi-photo aging trajectory** | Requires at least 2 age-tagged photos; learns the person's unique aging pattern and extrapolates to the present day — far more accurate than single-photo aging. |
| **Three-tier confidence routing** | High (≥80%) auto-alerts a field worker. Medium (60–80%) queues for human review. Low (<60%) is flagged inconclusive. |
| **"Not a Match" feedback loop** | When a field worker rejects a false match, the real photograph is uploaded. The AI learns from the difference. After 50 such examples, the model is fine-tuned — turning a generic global model into an Indian-subcontinent-specific one without any bespoke training dataset. |
| **No-code admin controls** | Thresholds, alerts, and toggles adjustable by the administrator without redeployment. |
| **Tamper-evident audit log** | Every AI decision cryptographically signed; PII redacted; exportable as CSV. |
| **Plain-language transparency** | Every screen explains, in plain words, how the result was derived and carries a disclaimer that the result is an AI estimate. |

---

## How It Works — The AI Pipeline

| Step | Operation | Technology |
|---|---|---|
| 1 | Face detection with 68-point landmarking | InsightFace |
| 2 | 512-dimensional face embedding | ArcFace |
| 3 | Aging trajectory calculation | Custom module |
| 4 | Age-progressed face generation | SAM / HRFAE GAN |
| 5 | Age-invariant recognition | ArcFace cosine similarity |
| 6 | Confidence scoring (0.0 – 1.0) | ArcFace |
| 7 | Alert routing / human review | FastAPI backend |
| 8 | Case summaries & community alerts (optional) | GPT-4o |
| 9 | Tamper-evident audit logging | PostgreSQL |

---

## Technology Stack

- **Mobile App:** React Native (Android + iOS)
- **Backend:** Python FastAPI
- **Database:** PostgreSQL
- **Face Recognition:** InsightFace / ArcFace (~500 MB)
- **Face Aging:** SAM / HRFAE GAN (~1–2 GB, GPU recommended)
- **AI Summaries:** OpenAI GPT-4o (optional)
- **Geocoding:** GeoPy
- **Deployment:** Docker Compose (`docker-compose.prod.yml`)

---

## Users and Roles

| User | Who they are | What they do |
|---|---|---|
| **Community Member / Family** | Anyone with a missing relative | Registers cases, uploads photographs, views results. |
| **Field Worker** | NGO worker or police officer | Physically verifies sightings, uploads photographs, gives feedback. |
| **Administrator** | Government officer or senior police | Approves cases, tunes thresholds, manages workers, exports audit logs. |

---

## Documentation

The complete **Functional Requirements Specification (FRS)** — including all functional requirements, user flows, acceptance criteria, risk register, and glossary — is available here:

📄 **[KHOJO_FRS.md](./KHOJO_FRS.md)** — full specification in Markdown (recommended for GitHub viewing)

📑 **[KHOJO_FRS.pdf](./KHOJO_FRS.pdf)** — print-ready PDF version

---

## Project Status

This is a hackathon submission for **Amnex Hackathon 2026**, Use Case UC34, Team ABHIMANYU. The FRS is final (v1.0) and the implementation is in progress.

---

## Acceptance Criteria (Summary)

The solution meets all ten hackathon acceptance criteria defined in the use case specification:

1. End-to-end flow completes without external instructions.
2. Face-aging produces output within 3 seconds on representative input.
3. Every AI decision displays a confidence score.
4. Sub-threshold confidence triggers the human-review fallback.
5. Every AI invocation is written to the audit log.
6. Backend runs a 15-minute demo without crashes or leaks.
7. All acronyms expanded at first occurrence.
8. External API failures degrade gracefully.
9. "Not a Match" feedback loop operates as specified.
10. Age formula computes correctly: `Age at Disappearance + (Current Year − Year of Disappearance)`.

---

## Team

**Team ABHIMANYU** — Amnex Hackathon 2026.

---

## License

Built for the Amnex Hackathon 2026. All rights reserved by the team pending hackathon outcome.

---

*"Har saal lakhon ghar me intezaar karte hain. KHOJO unki madad karne ke liye hai."*
*(Every year, lakhs of people wait at home. KHOJO is here to help them.)*
